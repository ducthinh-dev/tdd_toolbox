from mysql import connector
from mysql.connector import MySQLConnection
import pyodbc


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
        user: str = 'tools.Connector',
        do_debug: bool = False
    ) -> None:
        self.__DATABASE_HOST = host
        self.__DATABASE_USER = username
        self.__DATABASE_PASSWORD = password
        self.__DATABASE_SCHEMA = schema
        self.__connection = self.__establish_connection()
        self.__user = user
        self.type_dict.update(dict(zip([f'varchar({i})' for i in range(
            1, self.MAX_VARCHAR + 1)], ['str'] * self.MAX_VARCHAR)))
        self.__debug = do_debug

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

    def insert(self, table: str, columns: dict, values: list[tuple], new_col: bool = False, do_replace: bool = False):
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
        table_req = [row[0] for row in table_describe if row[2]
                     == 'NO' and 'auto_increment' not in row[5]]
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

        used_statement = 'replace' if do_replace else 'insert'
        statement = (
            f"/* {self.__user} */ "
            f"{used_statement} into {table} "
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

        table_req = [row[0] for row in table_describe if row[2]
                     == 'NO' and 'auto_increment' not in row[5]]
        cols_missing = [col for col in table_req if col not in columns]
        if self.__debug:
            print(table_describe)
            print(table_req)
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


class MSSQLConnector:
    type_dict = {
        'text': 'str',
        'date': 'str',
        'datetime': 'str',
        'datetime2': 'str',
        'timestamp': 'str',
        'float': 'float',
        'tinyint': 'int',
        'int': 'int',
        'bigint': 'int',
        'varchar': 'str',
        'nvarchar': 'str'
    }

    DESCR_NAME_IDX = 3
    DESCR_TYPE_IDX = 5
    DESCR_NULL_IDX = 10

    def __init__(self, server: str, username: str, password: str, database: str, driver: str = '{ODBC Driver 18 for SQL Server}') -> None:
        self.__driver = driver
        self.__server = server
        self.__username = username
        self.__password = password
        self.__database = database
        self.__establish_conn()

    def __establish_conn(self):
        self.__connection_string = 'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=no'.format(
            driver=self.__driver,
            server=self.__server,
            database=self.__database,
            username=self.__username,
            password=self.__password
        )
        self.__conn = pyodbc.connect(self.__connection_string)

    def refresh_conn(self):
        self.__conn.close()
        self.__establish_conn()

    def query(self, query: str, do_get: bool = True):
        try:
            with self.__conn.cursor() as cursor:
                cursor.execute(query)
                if do_get:
                    rows = cursor.fetchall()
                    columns = [col[0] for col in cursor.description]

        except Exception as err:
            self.refresh_conn()
            print(query)
            raise err

        if do_get:
            return columns, rows
        return 1

    def query_params(self, query: str, params: any, do_get: bool = True):
        try:
            with self.__conn.cursor() as cursor:
                cursor.execute(query, params)
                if do_get:
                    rows = cursor.fetchall()
                    columns = [col[0] for col in cursor.description]
        except Exception as err:
            self.refresh_conn()
            print(query)
            raise err
        return (columns, rows) if do_get else 1

    def query_many(self, query: str, params: list[any]):
        try:
            with self.__conn.cursor() as cursor:
                cursor.executemany(query, params)
        except Exception as err:
            self.refresh_conn()
            print(query)
            raise err
        return True

    def describe(self, table: str):
        stmt = 'exec sp_columns ?;'
        _, data = self.query_params(stmt, table)
        return_data = [(row[self.DESCR_NAME_IDX], row[self.DESCR_TYPE_IDX],
                        row[self.DESCR_NULL_IDX]) for row in data]
        return_cols = ['column_name', 'column_dtype', 'column_nullable']
        return (return_cols, return_data)

    @staticmethod
    def __handle_conditions(conditions: list[dict]):
        stmt = 'where'
        params_list = []
        ops = {
            "eq": "=",
            "gt": ">",
            "lt": "<",
            "gq": ">=",
            "lq": "<=",
            "ne": "!="
        }
        condition_string = ''
        for this_group in conditions:
            this_group_string = ''
            for condition in this_group:
                this_cond = f'{condition["column"]} {ops[condition["operator"]]} ?'
                params_list.append(condition["value"])
                this_cond = f'({this_cond})'
                this_group_string = f'{this_group_string} and {this_cond}' if this_group_string else this_cond

            this_group_string = f'({this_group_string})'
            condition_string = f'{condition_string} or {this_group_string}' if condition_string else this_group_string

        return (f'{stmt} {condition_string}', params_list)

    @staticmethod
    def __make_updates(cols):
        return ', '.join([f'{col} = ? ' for col in cols])

    def update(self, table: str, conditions: list[dict], update_values: list[tuple]):
        """
        conditions: [
            {
                "column": column_name,
                "operator": operator,
                "value": value
            }, ...
        ]
        operator list: eq: =, gt: >, lt: <, gq: >=, lq: <=, ne: !=
        """
        columns = [row[0] for row in update_values]
        values = [row[1] for row in update_values]
        _, table_info = self.describe(table=table)
        table_columns = [row[0] for row in table_info]
        table_requires = [row[0] for row in table_info if not row[2]]

        # CHECK IF ANY INVALID COLUMNS
        columns_invalid_error = list(
            set(columns).difference(set(table_columns)))
        if columns_invalid_error:
            raise ValueError(
                f'Invalid columns: {", ".join(columns_invalid_error)}.')

        # CHECK IF REQUIRED COLUMN IS NULL
        value_null_error = []
        for value in update_values:
            if value[0] in table_requires and value[1] == None:
                value_null_error.append(value[0])
        if value_null_error:
            raise ValueError(
                f'Columns cannot be null: {", ".join(value_null_error)}.')

        update_ph = self.__make_updates(cols=columns)
        condition_string, params_cond = self.__handle_conditions(conditions)
        stmt = (f'update {table} set {update_ph} {condition_string};')
        query_params = values + params_cond
        self.query_params(query=stmt, params=query_params, do_get=False)
        return 1

    @staticmethod
    def __check_require(cols, req_cols, values):
        for col, value in zip(cols, values):
            if col in req_cols and value == None:
                return False
        return True

    @staticmethod
    def __convert_type(types: list[str], values: tuple):
        results = []
        for this_type, this_value in zip(types, values):
            if this_value == None:
                results.append(this_value)
                continue

            match this_type:
                case 'str':
                    this_value = str(this_value)
                case 'float':
                    this_value = float(this_value)
                case 'int':
                    this_value = int(this_value)
            results.append(this_value)
        return tuple(results)

    def __adapt_type(self, types: list[str], values: list[tuple]):
        values_adapted = [self.__convert_type(
            types=types, values=row) for row in values]
        return values_adapted

    @staticmethod
    def __make_ph(num: int):
        return '(' + ', '.join(['?']*num) + ')'

    def insert(self, table: str, columns: list[str], insert_values: list[set]):
        _, table_info = self.describe(table=table)

        # CHECK IF VALUES' LENGTH MATCH WITH COLUMNS LENGTH
        length_insert = len(columns)
        row_length_error = [str(idx) for idx, row_value in enumerate(
            insert_values) if len(row_value) != length_insert]
        if row_length_error:
            raise ValueError(
                f'Row length does not match insert length {length_insert}: {", ".join(row_length_error)}')

        # CHECK IF REQUIRED VALUES ARE MISSING
        req_cols = [row[0] for row in table_info if row[2]]
        row_null_error = [str(idx) for idx, row in enumerate(insert_values) if not self.__check_require(
            cols=columns, req_cols=req_cols, values=insert_values)]
        if row_null_error:
            raise ValueError(
                f'Not nullable rows contain none value: {", ".join(row_null_error)}')

        table_dtype = dict([row[:2] for row in table_info])
        type_list = [self.type_dict[table_dtype[col_name]]
                     for col_name in columns]
        values_adapted = self.__adapt_type(
            types=type_list, values=insert_values)
        stmt = (
            f'insert into {table} ({", ".join(columns)}) '
            f'values {self.__make_ph(length_insert)};'
        )
        is_inserted = self.query_many(query=stmt, params=values_adapted)
        return len(values_adapted) if is_inserted else 0
