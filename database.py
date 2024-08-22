import mysql.connector
from mysql.connector import Error
import random
from datetime import datetime
from queue import Queue
import os
import threading
import tkinter as tk


class Logger:
    def __init__(self, name="log"):
        self.scrollbar = None
        self.text_widget = None
        # Create a log file with the current date and time
        now = datetime.now()
        log_filename = now.strftime(f"{name}/{name}_%y_%d_%H_%M.txt")
        self.log_filepath = os.path.join(os.getcwd(), log_filename)

        # Create the log file if it doesn't exist
        if not os.path.exists(self.log_filepath):
            with open(self.log_filepath, 'w') as file:
                file.write("Logger started: {}\n".format(now.strftime("%Y-%m-%d %H:%M:%S.%f")))

        # Create a queue to hold log messages
        self.log_queue = Queue()

        # Start a thread that will handle the actual logging
        self.log_thread = threading.Thread(target=self._process_logs)
        self.log_thread.daemon = True  # Daemonize the thread to ensure it closes when the main program exits
        self.log_thread.start()

    def message(self, message):
        # Add the log message to the queue
        self.log_queue.put(message)
        # todo create window info for user

    def _process_logs(self):
        while True:
            # Retrieve a message from the queue and write it to the log file
            message = self.log_queue.get()
            if message is None:
                break

            # Get the current time for the log entry
            now = datetime.now()
            timestamp = now.strftime("%H-%M-%S-%f")
            formatted_message = f"[{timestamp}] {message}\n"
            # Write the log message to the file
            with open(self.log_filepath, 'a') as file:
                file.write(formatted_message)

            # Mark the queue task as done
            self.log_queue.task_done()
            # print(self.text_widget)
            if self.text_widget is not None:
                self.text_widget.after(10, self._update_text_widget, formatted_message)
            else:
                print(message)

    def _update_text_widget(self, message):
        try:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, message)
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.see(tk.END)
        except Exception as e:
            print(f"Error updating text widget: {e}")

    def close(self):
        # Stop the logging thread by adding a None message to the queue
        self.log_queue.put(None)
        self.log_thread.join()


class Database:
    def __init__(self, database, logger, host="localhost", user="root", passwd="Aa123456"):
        self.logger = logger
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
                self.logger.message(f"Connected to MySQL Server version {db_info}")
                self.cursor = self.connection.cursor()
                self.cursor.execute("select database();")
                record = self.cursor.fetchone()
                self.logger.message(f"You're connected to database: {record}")
        except Error as e:
            self.logger.message(f"Error while connecting to MySQL: {e}")
            connection = mysql.connector.connect(
                host="your_host",
                user="your_user",
                passwd="your_password"
            )
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            self.connect()

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.message(f"Disconnected from {self.database}")

    def create_table(self, table_name, columns):
        try:
            cursor = self.connection.cursor()
            columns_str = ', '.join([f"{col_name} {data_type}" for col_name, data_type in columns.items()])
            cursor.execute(f"CREATE TABLE {table_name} ({columns_str})")
            self.connection.commit()
            self.logger.message(f"Table {table_name} created successfully with columns {columns_str}.")
        except Error as e:
            self.logger.message(f"Failed to create table {table_name}: {e}")

    def delete_table(self, table_name):
        try:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.logger.message(f"Table {table_name} deleted successfully.")
        except Error as e:
            self.logger.message(f"Failed to delete table {table_name}: {e}")

    def add_data_to_table(self, table_name, data):
        try:
            placeholders = ', '.join(['%s'] * len(data))
            columns = ', '.join(data.keys())
            sql = f"INSERT INTO {table_name} ( {columns} ) VALUES ( {placeholders} )"
            self.cursor.execute(sql, list(data.values()))
            self.connection.commit()
            self.logger.message(f"Data added to {table_name} successfully.")
        except Error as e:
            self.logger.message(f"Failed to add data to {table_name}: {e}")

    def get_all_table_names(self):
        try:
            # Execute the query to get all table names
            self.cursor.execute("SHOW TABLES")
            tables = self.cursor.fetchall()
            return [table[0] for table in tables]
        except Error as e:
            self.logger.message(f"Failed to get table names: {e}")
            return []

    def get_columns(self, table_name):
        self.cursor.execute(f"DESCRIBE {table_name}")
        temp_column_name_list = []
        for column_info in self.cursor.fetchall():
            temp_column_name_list.append(column_info[0])
        return temp_column_name_list

    def remove_data_by_id(self, id_value):
        try:
            # Get all table names
            table_names = self.get_all_table_names()
            for table_name in table_names:
                # Check if the table has a column named "ID"
                columns = self.get_columns(table_name)
                if "id" in columns:
                    # Execute the delete command
                    self.cursor.execute(f"DELETE FROM {table_name} WHERE ID = %s", (id_value,))
                    self.logger.message(f"Data with ID {id_value} removed from {table_name}.")
        except Error as e:
            self.logger.message(f"Failed to remove data: {e}")

    def find_data(self, table_name, num_id):
        try:
            sql = f"SELECT * FROM {table_name} WHERE id = {num_id}"
            self.cursor.execute(sql)
            columns = self.cursor.column_names
            records = self.cursor.fetchall()
            result = [dict(zip(columns, row)) for row in records]
            self.logger.message(f"Data found in {table_name}: {result}")

            return result
        except Error as e:
            self.logger.message(f"Failed to find data in {table_name}: {e}")

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
                    self.logger.message(f"No data found with ID {id_value} in {table_name}.")

                # Prepare the update statement
                update_columns = ', '.join([f"{key} = %s" for key in info if key != 'id'])
                update_values = [info[key] for key in info if key != 'id']

                # Execute the update command
                try:
                    self.cursor.execute(f"UPDATE {table_name} SET {update_columns} WHERE id = %s",
                                        update_values + [id_value])
                    self.connection.commit()
                    self.logger.message(f"Data with ID {id_value} updated in {table_name}.")
                except Exception as e:
                    self.logger.message(f"Failed to update data in {table_name}: {e}")
                    pass
        except Error as e:
            self.logger.message(f"Failed to update data in: {e}")

    def remove_element(self, num_id):
        self.logger.message(f"Remove element {num_id}")

    def add_element(self, values):
        table_names = self.get_all_table_names()
        values['id'] = int(1 + int(values["parent"]) / 10000) * 10000 + self.generate_unique_id()
        for table_name in table_names:
            temp_values = {}
            columns = self.get_columns(table_name)
            for column in columns:
                try:
                    temp_values[column] = values[column]
                except Exception as e:
                    self.logger.message(e)
                    temp_values = {}
                    break
            if temp_values:
                self.add_data_to_table(table_name, temp_values)
        return values['id']

    def get_info(self, id_num):
        tables = self.get_all_table_names()
        table_info = {}
        for table in tables:
            temp_table_info = self.find_data(table, id_num)
            if temp_table_info:
                for column, info in temp_table_info[0].items():
                    table_info[column] = info
        return table_info

    def get_by_feature(self, feature):
        tables = self.get_all_table_names()
        list_features = []
        for table in tables:
            query = f"SELECT * FROM {table} WHERE {feature} ORDER BY {feature} ASC"
            self.cursor.execute(query)

            results = self.cursor.fetchall()
            for result in results:
                if result not in list_features:
                    list_features.append(result[0])
        self.logger.message(f"list features {list_features}")
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
    db = Database(host="localhost", user="root", passwd="Aa123456", database=data_base_name, logger=Logger())
    db.connect()
    db.delete_table("label_param")
    db.delete_table("frs_info")
    db.delete_table("com_info")
    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "parent": "INT",
               "x": "INT",
               "y": "INT",
               "Width": "INT",
               "Height": "INT",
               "label_name": "VARCHAR(255)",
               "class": "VARCHAR(255)",
               "info_table": "VARCHAR(255)"}
    db.create_table("label_param", columns)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "maxByte": "INT",
               "minByte": "INT",
               "maxBit": "INT",
               "minBit": "INT"}

    db.create_table("frs_info", columns)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "Type": "VARCHAR(255)",
               "last_conn_info": "VARCHAR(255)",
               "func": "VARCHAR(255)"}

    db.create_table("com_info", columns)
    data_main = {
        "Width": "1250",
        "Height": "850",
        "label_name": "Main",
        "x": 0,
        "y": 0,
        "parent": "000000",
        "class": "<class '__main__.RightClickMenu'>",
        "id": "000001",
        "info_table": None

    }
    data_script = {
        "Width": "250",
        "Height": "100",
        "label_name": "Script",
        "x": 910,
        "y": 600,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000002",
        "info_table": "script"

    }
    data_info = {
        "Width": "900",
        "Height": "200",
        "label_name": "Information logger",
        "x": 0,
        "y": 600,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000003",
        "info_table": ""

    }
    data_scope = {
        "Width": "250",
        "Height": "100",
        "label_name": "Scope",
        "x": 910,
        "y": 700,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000004",
        "info_table": ""

    }
# id => id length = 6 , first 2 is depth, last 4 is id random generated by function
    db.add_data_to_table("label_param", data_main)
    db.add_data_to_table("label_param", data_script)
    db.add_data_to_table("label_param", data_info)
    db.add_data_to_table("label_param", data_scope)
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

# init_database()
