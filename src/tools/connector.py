import os
from mysql import connector
from mysql.connector import MySQLConnection


class Connector:
    def __init__(
        self,
        host,
        username,
        password,
        schema
    ) -> None:
        self.__DATABASE_HOST = host
        self.__DATABASE_USER = username
        self.__DATABASE_PASSWORD = password
        self.__DATABASE_SCHEMA = schema
        self.__connection = self.__establish_connection()

    def __establish_connection(self):
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
        self.__connection = self.__establish_connection()

    def close_connection(self):
        self.__connection.close()

    def return_connection_string(self):
        return f"mysql+mysqlconnector://{self.__DATABASE_USER}:{self.__DATABASE_PASSWORD}@{self.__DATABASE_HOST}/{self.__DATABASE_SCHEMA}"

    @staticmethod
    def handle_conditions(conditions: list = []):
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
                value = item["value"]
                item["value"] = f"'{value}'"

        con_str = " OR ".join(
            [f"{con['column']} {ops[con['operator']]} {con['value']}" for con in conditions])
        return "WHERE " + con_str

    def query_data(self, query: str):
        """
        Return: cols, data
        """
        try:
            with self.__connection.cursor(buffered=True) as cursor:
                cursor.execute(query)
                raw_data = cursor.fetchall()
                raw_columns = cursor.column_names
            return (raw_columns, raw_data)
        except connector.Error as error:
            # print(f"Oh no, {error}.")
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
        return result

    def insert_data_(self, table: str, data: list, column_names: list):
        try:
            columns = ", ".join(column_names)
            columns_len = len(column_names)
            values_marker = "%s"
            statement = (
                f"INSERT INTO {table} "
                f"({columns}) "
                f"VALUES ({', '.join([values_marker] * columns_len)})"
            )
            with self.__connection.cursor() as cursor:
                cursor.executemany(statement, data)
                self.__connection.commit()
        except connector.Error as error:
            print(error,
                  sep="\n")

    def update_data(
            self,
            table: str,
            column: str,
            row_value: any,
            data: list[tuple]
    ):
        try:
            for idx, item in enumerate(data):
                if type(item[1]) is str:
                    if "'" in item[1]:
                        data[idx] = (item[0], item[1].replace("'", ""))
                    data[idx] = (item[0], f"'{item[1]}'")

            update_value = [f"{item[0]} = {item[1]}" for item in data]
            statement = (
                f"UPDATE {table} "
                f"SET {', '.join(update_value)} "
                f"WHERE {column} = '{row_value}';"
            )
            with self.__connection.cursor() as cursor:
                cursor.execute(statement)
                self.__connection.commit()
            return True
        except connector.Error as error:
            print(error,
                  sep="\n")
            return statement

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
            statement = f"DELETE FROM {table} {con_str};"
            with self.__connection.cursor() as cursor:
                cursor.execute(statement)
                self.__connection.commit()
            return True
        except Exception as error:
            print(error, con_str, sep="\n")
            return False
