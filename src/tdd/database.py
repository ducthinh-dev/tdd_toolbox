from mysql import connector
from mysql.connector import MySQLConnection


class MysqlConnector:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306

    ) -> None:
        self.__DATABASE_HOST = host
        self.__DATABASE_USER = user
        self.__DATABASE_PASSWORD = password
        self.__DATABASE_SCHEMA = database
        self.__connection = self.__establish_connection()
        self.__PORT = port

    def __establish_connection(self):
        connection = MySQLConnection(user=self.__DATABASE_USER,
                                     password=self.__DATABASE_PASSWORD,
                                     host=self.__DATABASE_HOST,
                                     port=self.__PORT,
                                     database=self.__DATABASE_SCHEMA)
        return connection

    def refresh_connection(self):
        self.__connection = self.__establish_connection()

    def close_connection(self):
        self.__connection.close()

    def connection_string(self):
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

    def query(self, query: str):
        try:
            with self.__connection.cursor() as cursor:
                cursor.execute(query)
                raw_data = cursor.fetchall()
                raw_columns = cursor.column_names
            return (raw_columns, raw_data)
        except connector.Error as error:
            return (False, False)

    def insert(self, table: str, data: list, column_names: list):
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

    def update(self, table: str, row: str, row_value: any, data: list[set]):
        try:
            update_value = [f"{item[0]} = '{item[1]}'" for item in data]
            statement = (
                f"UPDATE {table} "
                f"SET {', '.join(update_value)} "
                f"WHERE {row} = '{row_value}';"
            )
            with self.__connection.cursor() as cursor:
                cursor.execute(statement)
                self.__connection.commit()
            return True
        except connector.Error as error:
            print(error,
                  sep="\n")
            return statement

    def delete(self, table: str, conditions: list[dict] = []):
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
