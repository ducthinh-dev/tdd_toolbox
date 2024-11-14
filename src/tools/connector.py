from mysql import connector
from mysql.connector import MySQLConnection


class Connector:
    MAX_VARCHAR = 1000

    type_dict = {
        'text': 'str',
        'datetime': 'str',
        'timestamp': 'str',
        'double': 'float',
        'tinyint': 'int',
        'int': 'int',
        'bigint': 'int',
    }

    def __init__(
        self,
        host,
        username,
        password,
        schema,
        user: str = 'tools.Connector'
    ) -> None:
        self.__DATABASE_HOST = host
        self.__DATABASE_USER = username
        self.__DATABASE_PASSWORD = password
        self.__DATABASE_SCHEMA = schema
        self.__connection = self.__establish_connection()
        self.__user = user
        self.type_dict.update(dict(zip([f'varchar({i})' for i in range(
            1, self.MAX_VARCHAR + 1)], ['str'] * self.MAX_VARCHAR)))

    def __establish_connection(self, is_init=True):
        if not is_init:
            self.__connection.close()
        connection = MySQLConnection(
            user=self.__DATABASE_USER,
            password=self.__DATABASE_PASSWORD,
            host=self.__DATABASE_HOST,
            port=3306,
            database=self.__DATABASE_SCHEMA,
            buffered=True
        )
        return connection

    def refresh_connection(self):
        self.__connection = self.__establish_connection(is_init=False)

    def close_connection(self):
        self.__connection.close()

    def return_connection_string(self):
        return f"mysql+mysqlconnector://{self.__DATABASE_USER}:{self.__DATABASE_PASSWORD}@{self.__DATABASE_HOST}/{self.__DATABASE_SCHEMA}"

    @staticmethod
    def handle_conditions(conditions: list = [], is_or: bool = True):
        """
        conditions: [
            {
                "column": column_name,
                "value": value,
                "operator": operator
            }, ...
        ]
        operator list: eq: =, gt: >, lt: <, gq: >=, lq: <=, ne: !=
        """
        ops = {
            "eq": "=",
            "gt": ">",
            "lt": "<",
            "gq": ">=",
            "lq": "<=",
            "ne": "!="
        }
        if not conditions:
            return "WHERE 1=1"

        for item in conditions:
            if type(item["value"]) is str:
                value = item["value"].replace("'", "\'")
                item["value"] = f"'{value}'"

        con_op = "OR" if is_or else "AND"
        con_str = f" {con_op} ".join(
            [f"{con['column']} {ops[con['operator']]} {con['value']}" for con in conditions])
        return "WHERE " + con_str

    def query_data(self, query: str, params: list = []):
        """
        #### Return: 
        `columns, data`
        """
        try:
            with self.__connection.cursor(buffered=True) as cursor:
                cursor.execute(f'/* {self.__user} */ ' + query, params=params)
                raw_data = cursor.fetchall()
                raw_columns = cursor.column_names
                self.__connection.commit()
            return (raw_columns, raw_data)
        except connector.Error as error:
            self.__connection.rollback()
            print(f"Oh no, {error}.")
            return (False, error)

    def call_proc(self, proc_name: str, args: list):
        """
        Call a stored procedure with the given name and arguments.

        Args:
            proc_name (str): The name of the stored procedure to call.
            args (list): The arguments to pass to the stored procedure.

        Returns:
            list: A list of tuples containing column names and fetched results.
            >>> [
            >>>     ( (cols), [(result), ...] ),
            >>>     ...
            >>> ]
        """
        with self.__connection.cursor() as cursor:
            cursor.callproc(procname=proc_name, args=args)
            result = []
            for item in cursor.stored_results():
                result.append((item.column_names, item.fetchall()))
            self.__connection.commit()
        self.refresh_connection()
        return result

    def update_data(
            self,
            table: str,
            column: str,
            row_value: any,
            data: list[tuple]
    ):
        try:
            update_cols = [update[0] for update in data]
            update_value = [update[1] for update in data]

            statement = (
                f"/* {self.__user} */ "
                f"UPDATE {table} "
                f"SET {self._make_update(update_cols)} "
                f"WHERE {column} = '{row_value}';"
            )
            with self.__connection.cursor() as cursor:
                cursor.execute(statement, update_value)
                self.__connection.commit()
            return True
        except connector.Error as error:
            self.__connection.rollback()
            print(error,
                  sep="\n")
            return statement

    @staticmethod
    def _make_update(col_list: list[str]):
        result = ' = %s , '.join(col_list) + ' = %s'
        return result

    def update_multiple(self, table: str, conditions: list[dict], updates: list[tuple]):
        """
        conditions:
        ```
        [
            {
                "column": column_name,
                "value": value,
                "operator": operator
            }, ...
        ]
        ```
        operator list: `eq`: `=`, `gt`: `>`, `lt`: `<`, `gq`: `>=`, `lq`: `<=`, `ne`: `!=`
        """
        try:
            update_cols = [update[0] for update in updates]
            update_value = [update[1] for update in updates]

            con_str = self.handle_conditions(conditions, is_or=False)
            statement = (
                f"/* {self.__user} */ "
                f"UPDATE {table} "
                f"SET {self._make_update(update_cols)} "
                f"{con_str};"
            )
            with self.__connection.cursor() as cursor:
                cursor.execute(statement, update_value)
                self.__connection.commit()
        except connector.Error as error:
            self.__connection.rollback()
            print(error,
                  sep="\n")
            return statement
        return

    def delete_data(self, table: str, conditions: list[dict] = []):
        """
        conditions:
        ```
        [
            {
                "column": column_name,
                "value": value,
                "operator": operator
            }, ...
        ]
        ```
        operator list: `eq`: `=`, `gt`: `>`, `lt`: `<`, `gq`: `>=`, `lq`: `<=`, `ne`: `!=`
        """
        try:
            con_str = self.handle_conditions(conditions)
            statement = f"/* {self.__user} */ DELETE FROM {table} {con_str};"
            with self.__connection.cursor() as cursor:
                cursor.execute(statement)
                self.__connection.commit()
            return True
        except Exception as error:
            self.__connection.rollback()
            print(error, con_str, sep="\n")
            return False

    @staticmethod
    def _convert_type(types: list[str], values: tuple):
        results = []
        for this_type, this_value in zip(types, values):
            if this_value == None:
                # this_value = 'null'
                results.append(this_value)
                continue

            match this_type:
                case 'str':
                    this_value = str(this_value)
                    # .replace("'", "&apos;")
                    # this_value = f"'{this_value}'"
                case 'float':
                    this_value = float(this_value)
                case 'int':
                    this_value = int(this_value)
            results.append(this_value)
        return tuple(results)

    def _adapt_type(self, types: list[str], values: list[tuple]):
        values_adapted = [self._convert_type(
            types=types, values=row) for row in values]
        return values_adapted

    def describe(self, table: str):
        statement = f"/* {self.__user} */ describe {table};"
        return self.query_data(statement)

    @staticmethod
    def _make_ph(num: int):
        return '(' + ', '.join(['%s']*num) + ')'

    def insert(self, table: str, columns: dict, values: list[tuple], new_col: bool = False):
        """
        Insert data into the specified table.

        Args:
            table (str): The name of the table to insert data into.
            columns (dict): A dictionary where keys are column names and values are data types.
            values (list[tuple]): A list of tuples where each tuple represents a row of data to be inserted.

        Returns:
            int: The number of rows inserted.

        Raises:
            KeyError: If columns in the data to be inserted do not match the table columns.
            ValueError: If length of a row does not match the length of column list.

        Example:
            ```
            cols = ['first_col', 'second_col']
            values = [('70', 2123.3), ('80', 123)]
            Connector.insert(
                table='TableName',
                columns=cols,
                values=values
            )
            >>> 2
            ```
        """
        if not values:
            return 0

        columns_len = len(columns)
        for idx, row in enumerate(values):
            if len(row) != columns_len:
                raise ValueError(
                    f'Index {idx}\'s length ({len(row)}) does not match length of columns ({columns_len}).')

        _, table_describe = self.describe(table=table)
        table_dtype = dict([row[:2] for row in table_describe])

        # CHECK REQUIRED COLUMN
        table_req = [row[0] for row in table_describe if row[2] == 'NO']
        cols_missing = [col for col in table_req if col not in columns]
        if cols_missing:
            raise KeyError(f'Missing not null columns: {cols_missing}.')

        # CHECK DIFFERENCE BETWEEN PROVIDED COLUMNS WITH TABLE COLUMNS
        cols_diff = list(set(columns).difference(set(table_dtype.keys())))
        if cols_diff:
            if not new_col:
                raise KeyError(f'Columns are not in {table}: {str(cols_diff)}')
            else:
                for col in cols_diff:
                    self.add_column(
                        table=table,
                        name=col,
                        ctype='text'
                    )
                _, table_describe = self.describe(table=table)
                table_dtype = dict([row[:2] for row in table_describe])

        type_list = [self.type_dict[table_dtype[col_name]]
                     for col_name in columns]
        values = self._adapt_type(types=type_list, values=values)

        statement = (
            f"/* {self.__user} */ "
            f"insert into {table} "
            f"({', '.join(columns)}) "
            f"values "
            f"{self._make_ph(len(columns))};"
        )
        try:
            with self.__connection.cursor() as cursor:
                cursor.executemany(statement, seq_params=values)
                self.__connection.commit()
        except Exception as error:
            self.__connection.rollback()
            print(error, statement, sep='\n')
        return len(values)

    def add_column(self, table: str, name: str, ctype: str):
        try:
            statement = (
                f"/* {self.__user} */ "
                f"alter table {table} "
                f"add {name} {ctype} null ;"
            )
            with self.__connection.cursor() as cursor:
                cursor.execute(statement)
                self.__connection.commit()
            return True
        except Exception as error:
            self.__connection.rollback()
            print(error, statement, sep="\n")
            return False

    def replace(self, table: str, columns: dict, values: list[tuple], new_col: bool = False):
        """
        Replace data into the specified table.

        Args:
            table (str): The name of the table to replace data into.
            columns (dict): A dictionary where keys are column names and values are data types.
            values (list[tuple]): A list of tuples where each tuple represents a row of data to be replaced.

        Returns:
            int: The number of rows replaced.

        Raises:
            KeyError: If columns in the data to be replaced do not match the table columns.
            ValueError: If length of a row does not match the length of column list.

        Example:
            ```
            cols = ['first_col', 'second_col']
            values = [('70', 2123.3), ('80', 123)]
            Connector.replace(
                table='TableName',
                columns=cols,
                values=values
            )
            >>> 2
            ```
        """
        if not values:
            return 0

        columns_len = len(columns)
        for idx, row in enumerate(values):
            if len(row) != columns_len:
                raise ValueError(
                    f'Index {idx}\'s length ({len(row)}) does not match length of columns ({columns_len}).')

        _, table_describe = self.describe(table=table)
        table_dtype = dict([row[:2] for row in table_describe])

        # CHECK REQUIRED COLUMN
        table_req = [row[0] for row in table_describe if row[2] == 'NO']
        cols_missing = [col for col in table_req if col not in columns]
        if cols_missing:
            raise KeyError(f'Missing not null columns: {cols_missing}.')

        # CHECK DIFFERENCE BETWEEN PROVIDED COLUMNS WITH TABLE COLUMNS
        cols_diff = list(set(columns).difference(set(table_dtype.keys())))
        if cols_diff:
            if not new_col:
                raise KeyError(f'Columns are not in {table}: {str(cols_diff)}')
            else:
                for col in cols_diff:
                    self.add_column(
                        table=table,
                        name=col,
                        ctype='text'
                    )
                _, table_describe = self.describe(table=table)
                table_dtype = dict([row[:2] for row in table_describe])

        type_list = [self.type_dict[table_dtype[col_name]]
                     for col_name in columns]
        values = self._adapt_type(types=type_list, values=values)

        statement = (
            f"/* {self.__user} */ "
            f"replace into {table} "
            f"({', '.join(columns)}) "
            f"values "
            f"{self._make_ph(len(columns))};"
        )
        try:
            with self.__connection.cursor() as cursor:
                cursor.executemany(statement, seq_params=values)
                self.__connection.commit()
        except Exception as error:
            self.__connection.rollback()
            print(error, statement, sep='\n')
        return len(values)
