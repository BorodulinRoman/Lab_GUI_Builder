import mysql.connector
from mysql.connector import Error
import random


class Database:
    def __init__(self, database, host="localhost", user="root", passwd="Aa123456"):
        self.cursor = None
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                passwd=self.passwd,
                database=self.database
            )
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                print(f"Connected to MySQL Server version {db_info}")
                self.cursor = self.connection.cursor()
                self.cursor.execute("select database();")
                record = self.cursor.fetchone()
                print(f"You're connected to database: {record}")
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print(f"Disconnected from {self.database}")

    def create_table(self, table_name, columns):
        try:
            cursor = self.connection.cursor()
            columns_str = ', '.join([f"{col_name} {data_type}" for col_name, data_type in columns.items()])
            cursor.execute(f"CREATE TABLE {table_name} ({columns_str})")
            self.connection.commit()
            print(f"Table {table_name} created successfully with columns {columns_str}.")
        except Error as e:
            print(f"Failed to create table {table_name}: {e}")

    def delete_table(self, table_name):
        try:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"Table {table_name} deleted successfully.")
        except Error as e:
            print(f"Failed to delete table {table_name}: {e}")

    def add_data_to_table(self, table_name, data):
        try:
            placeholders = ', '.join(['%s'] * len(data))
            columns = ', '.join(data.keys())
            sql = f"INSERT INTO {table_name} ( {columns} ) VALUES ( {placeholders} )"
            self.cursor.execute(sql, list(data.values()))
            self.connection.commit()
            print(f"Data added to {table_name} successfully.")
        except Error as e:
            print(f"Failed to add data to {table_name}: {e}")

    def get_all_table_names(self):
        try:
            # Execute the query to get all table names
            self.cursor.execute("SHOW TABLES")
            tables = self.cursor.fetchall()
            return [table[0] for table in tables]
        except Error as e:
            print(f"Failed to get table names: {e}")
            return []

    def remove_data_by_id(self, id_value):
        try:
            # Get all table names
            table_names = self.get_all_table_names()
            for table_name in table_names:
                # Check if the table has a column named "ID"
                self.cursor.execute(f"DESCRIBE {table_name}")
                columns = self.cursor.fetchall()
                if any(column[0].lower() == "id" for column in columns):
                    # Execute the delete command
                    self.cursor.execute(f"DELETE FROM {table_name} WHERE ID = %s", (id_value,))
                    print(f"Data with ID {id_value} removed from {table_name}.")
        except Error as e:
            print(f"Failed to remove data: {e}")

    def find_data(self, table_name, num_id):
        try:
            sql = f"SELECT * FROM {table_name} WHERE id = {num_id}"
            self.cursor.execute(sql)
            columns = self.cursor.column_names
            records = self.cursor.fetchall()
            result = [dict(zip(columns, row)) for row in records]
            print(f"Data found in {table_name}: {result}")

            return result
        except Error as e:
            print(f"Failed to find data in {table_name}: {e}")

    def update(self, info):
        try:
            table_list = self.get_all_table_names()
            id_value = info.get('id')
            if id_value is None:
                raise ValueError("The 'id' parameter is required in the info dictionary.")
            for table_name in table_list:
                # Find the data based on the provided ID
                records = self.find_data(table_name, id_value)
                if not records:
                    print(f"No data found with ID {id_value} in {table_name}.")


                # Prepare the update statement
                update_columns = ', '.join([f"{key} = %s" for key in info if key != 'id'])
                update_values = [info[key] for key in info if key != 'id']

                # Execute the update command
                try:
                    self.cursor.execute(f"UPDATE {table_name} SET {update_columns} WHERE id = %s",
                                        update_values + [id_value])
                    self.connection.commit()
                    print(f"Data with ID {id_value} updated in {table_name}.")
                except Exception as e:
                    print(f"Failed to update data in {table_name}: {e}")
        except Error as e:
            print(f"Failed to update data in: {e}")

    def remove_element(self,id):
        print(f"Remove element {id}")

    def add_element(self,values):
        print(values["parent"], type(values["parent"]))
        values['id'] = int(1 + int(values["parent"])/1000)*1000 + self.generate_unique_id()
        self.add_data_to_table("label_param", values)
        return values['id']

    def get_info(self, id_num):
        tables = self.get_all_table_names()
        table_info = {}
        for table in tables:
            table_info[table] = self.find_data(table, id_num)
        return table_info

    def get_by_feature(self, feature):
        tables = self.get_all_table_names()
        list_features = []
        for table in tables:
            query = f"SELECT * FROM {table} WHERE {feature} ORDER BY {feature} ASC"
            self.cursor.execute(query)

            # קבלת התוצאות
            results = self.cursor.fetchall()
            print(results)
            for result in results:
                if result not in list_features:
                    list_features.append(result[0])
        print("list features ",list_features)
        return list_features

    def generate_unique_id(self):
        """Generate a unique ID between 0000 and 9999."""
        available_ids = []
        existing_ids = self.get_by_feature("id")

        for id_num in range(9999):
            if id_num not in existing_ids:
                available_ids.append(id_num)

        if not available_ids:
            raise ValueError("No available unique IDs left.")
        return random.choice(available_ids)








def init_database(data_base_name="gui_conf"):
    db = Database(host="localhost", user="root", passwd="Aa123456", database=data_base_name)
    db.connect()
    # db.delete_table("label_param")
    # db.delete_table("frs_info")
    # db.delete_table("com_info")
    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "parent": "INT",
               "x": "INT",
               "y": "INT",
               "width": "INT",
               "height": "INT",
               "label_name": "VARCHAR(255)",
               "class": "VARCHAR(255)",
               "info_table": "VARCHAR(255)"}
    db.create_table("label_param", columns)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "max_byte": "INT",
               "min_byte": "INT",
               "max_bit": "INT",
               "min_bit": "INT"}

    db.create_table("frs_info", columns)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "type": "VARCHAR(255)",
               "last_conn_info": "VARCHAR(255)",
               "func": "VARCHAR(255)"}

    db.create_table("com_info", columns)
    data = {
        "width": "1250",
        "height": "850",
        "label_name": "Main",
        "x": 0,
        "y": 0,
        "parent": None,
        "class": "<class '__main__.RightClickMenu'>",
        "id": "000001"

    }
# id => id length = 6 , first 2 is depth, last 4 is id random generated by function
    db.add_data_to_table("label_param", data)
    db.generate_unique_id()
    db.disconnect()


# Example usage
# db = Database(host="localhost", user="root", passwd="Aa123456", database="gui_conf")
# db.connect()

# db.delete_table("TestTable")
# db.create_table("TestTable", {"id": "INT AUTO_INCREMENT PRIMARY KEY", "name": "VARCHAR(255)", "age": "INT"})
# db.create_table("TestTable2", {"id": "INT AUTO_INCREMENT PRIMARY KEY", "work": "VARCHAR(255)", "vet": "INT"})
# db.add_data_to_table("TestTable", {"id": 1234, "name": "John", "age": 30})
# db.add_data_to_table("TestTable2", {"id": 1234, "work": "raf", "vet": 5})
# db.find_data(table_name="TestTable", num_id=1234)
# db.update_data({"id": 1234, "age": 35})
# # db.remove_data_by_id("1234")

#init_database()

