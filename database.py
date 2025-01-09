import mysql.connector
import time
from mysql.connector import Error
import random
from datetime import datetime
from queue import Queue
import threading
import tkinter as tk


# database
class PrintLoger:
    def __init__(self, loading_window=None):
        self.info = "logger"
        self.loading_window = loading_window

    def message(self, message, type=None):
        if self.loading_window is not None:
            self.loading_window.text_var.set(message)
            time.sleep(0.1)
        else:
            print(f"{self.info} - {message}")
            self.loading_window = None


class Logger:
    def __init__(self, name, loading_window=None):
        self.logger_running = True
        self.loading_window = loading_window
        self.db = Database(name)
        self.table_name = datetime.now().strftime(f"{name}%y%d%H%M")
        self.log_queue = Queue()
        self.text_widget = None

        # Ensure the log table exists
        self.create_log_table()

        # Start the thread that will handle the actual logging
        self.log_thread = threading.Thread(target=self._process_logs)
        self.log_thread.daemon = True
        self.log_thread.start()

    def create_log_table(self):
        columns = {
            "id": "INT AUTO_INCREMENT PRIMARY KEY",
            "timestamp": "DATETIME(6)",
            "log_level": "VARCHAR(10)",
            "message": "TEXT"
        }
        self.db.create_table(self.table_name, columns)

    def message(self, message, log_level="info", update_info_desk=True):
        # Convert the message to a string to handle exceptions and other non-string types
        message = str(message)

        try:
            if self.loading_window is not None:
                self.loading_window.text_var.set(message)
                #time.sleep(0.1)
        except Exception as e:
            print(e)
            self.loading_window = None
        print(message)        # Add the log message to the queue
        self.log_queue.put((message, log_level, update_info_desk))

    def _process_logs(self):
        while self.logger_running:
            message, log_level, update_info_desk = self.log_queue.get()
            print(message, log_level, update_info_desk)
            if message is None:
                time.sleep(0.1)
                break

            # Get the current time for the log entry
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")

            # Prepare the log data
            log_data = {
                "timestamp": timestamp,
                "log_level": log_level,
                "message": message
            }
            # Add the log entry to the database
            self.db.add_data_to_table(self.table_name, log_data)
            # Mark the queue task as done
            self.log_queue.task_done()
            try:
                # Optionally update a text widget or print the message
                if self.text_widget is not None and update_info_desk:
                    self.text_widget.after(0, self._update_text_widget, f"[{timestamp}] {log_level.upper()}: {message}\n")
                    time.sleep(0.01)
            except Exception as e:
                pass

    def _update_text_widget(self, formatted_message, max_lines=1000):
        try:
            # Make the widget editable
            self.text_widget.config(state=tk.NORMAL)

            # Insert the new log message at the end
            self.text_widget.insert(tk.END, formatted_message)

            # Determine the number of lines currently in the text widget
            line_count = int(float(self.text_widget.index('end')))

            # If the line count exceeds 'max_lines', remove the oldest lines
            if line_count > max_lines:
                # Calculate how many lines need to be removed
                lines_to_remove = line_count - max_lines

                # Delete from the first line up to the number of lines to remove
                self.text_widget.delete('1.0', f'{lines_to_remove}.0')

            # Re-disable the text widget to prevent user edits
            self.text_widget.config(state=tk.DISABLED)

            # Scroll to the bottom so the newest message is visible
            self.text_widget.see(tk.END)
        except Exception as e:
            print(f"Error updating text widget: {e}")

    def close(self):
        # Stop the logging thread by adding a None message to the queue
        self.logger_running = False
        self.log_queue.put(None)
        self.log_thread.join()


def create_schema(host, user, passwd, schema_name):
    try:
        # Connect to MySQL Server
        connection = mysql.connector.connect(
            host=host,
            user=user,
            passwd=passwd
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # Create the new schema (database)
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {schema_name}")
            print(f"Schema '{schema_name}' created successfully.")

    except Error as e:
        print(f"Failed to create schema '{schema_name}': {e}")


# Python database copy function with commit
def copy_schema(host, user, passwd, source_schema, target_schema):
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            passwd=passwd
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_schema}")
            cursor.execute(f"SHOW TABLES FROM {source_schema}")
            tables = cursor.fetchall()

            for (table,) in tables:
                print(f"Copying {table}...")
                cursor.execute(f"CREATE TABLE {target_schema}.{table} LIKE {source_schema}.{table}")
                cursor.execute(f"INSERT INTO {target_schema}.{table} SELECT * FROM {source_schema}.{table}")
                connection.commit()
                print(f"Table '{table}' copied.")

    except Error as e:
        print(f"Error: {e}")


class Database:
    def __init__(self, database, logger=None, loading_window=None, host="localhost", user="root", passwd="Aa123456"):
        if logger is not None:
            self.logger = logger
        self.logger = PrintLoger(loading_window)
        self.cursor = None
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
        self.connection = None
        self.connect()

    def switch_database(self, new_database_name=None):
        if new_database_name is None:
            new_database_name = self.database
        try:
            self.cursor.execute(f"USE {new_database_name}")
            self.logger.message(f"Switched to database: {new_database_name}")
        except Error as e:
            self.logger.message(f"Failed to switch to database {new_database_name}: {e}",)

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
        except Error as e:
            self.logger.message(f"Failed to add data to {table_name}: {e}")

    def add_missing_columns(self, table_name, columns):
        """
        Adds missing columns to a MySQL table if they don't exist.

        :param table_name: Name of the table
        :param columns: Dictionary with column names and SQL definitions
        """
        try:
            # Get existing columns
            self.cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = %s 
                  AND TABLE_SCHEMA = %s;
            """, (table_name, self.database))

            existing_columns = {row[0] for row in self.cursor.fetchall()}

            # Add missing columns
            for col_name, col_def in columns.items():
                if col_name not in existing_columns:
                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def};"
                    self.logger.message(f"Adding missing column: {alter_query}")
                    self.cursor.execute(alter_query)

            self.connection.commit()
            self.logger.message("Missing columns added successfully.")

        except mysql.connector.Error as err:
            self.logger.message(f"Error adding missing columns: {err}")

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
        self.switch_database(f"{self.database}")
        # Get all table names
        table_names = self.get_all_table_names()
        for table_name in table_names:
            # Check if the table has a column named "ID"
            columns = self.get_columns(table_name)
            try:
                if "id" in columns:
                    val1 = f"DELETE FROM {table_name} WHERE id = {id_value}"
                    print(val1)
                    self.cursor.execute(val1)
                    self.connection.commit()
                    self.logger.message(f"Data with ID {id_value} removed from {table_name}.")

            except Error as e:
                self.logger.message(f"Failed to remove data: {e}")

    def remove_data_feature(self, table_name, feature, value):
        # Check if the table has a column named "ID"
        try:
            val1 = f"DELETE FROM {table_name} WHERE {feature} = '{value}'"


            self.cursor.execute(val1)
            self.connection.commit()
            self.logger.message(f"Data with  {feature} {value} removed from {table_name}.")

        except Error as e:
            self.logger.message(f"Failed to remove data: {e}")

    def find_data(self, table_name, feature_info=None, feature='id'):
        try:
            if feature_info is None:
                sql = f"SELECT * FROM {table_name}"
            else:
                sql = f"SELECT * FROM {table_name} WHERE {feature} = '{feature_info}'"

            self.logger.message(f"Database {sql}")
            self.cursor.execute(sql)
            columns = self.cursor.column_names
            records = self.cursor.fetchall()
            result = [dict(zip(columns, row)) for row in records]
            self.logger.message(f"Data found in {table_name}: {result}")

            return result
        except Error as e:
            self.logger.message(f"Failed to find data in {table_name}: {e}")
            return None

    def update(self, info):
        print("Starting Update:", info)
        try:
            # Validate the 'id' parameter
            id_value = info.get('id')
            if id_value is None:
                raise ValueError("The 'id' parameter is required in the info dictionary.")

            # Retrieve the table list
            table_list = self.get_all_table_names()

            for table_name in table_list:
                if table_name == "transmit_com":
                    continue
                # Find the data based on the provided ID
                records = self.find_data(table_name, id_value)
                if not records:
                    self.logger.message(f"No data found with ID {id_value} in {table_name}.")
                    continue
                # Use the latest record from find_data
                records = records[-1]

                # Update records with values from info
                for column in records.keys():
                    if column in ['id', 'class']:
                        continue
                    if column in info:  # Only update columns present in info
                        if column in ["function_name","function_info"]:
                            continue
                        records[column] = info[column]

                # Prepare the SET clause and values for the SQL query
                update_columns = ', '.join([f"{key} = %s" for key in records if key != 'id'])
                update_values = [records[key] for key in records if key != 'id']

                # Execute the update command
                try:
                    update_query = f"UPDATE {table_name} SET {update_columns} WHERE id = %s"
                    self.cursor.execute(update_query, update_values + [id_value])
                    self.connection.commit()
                    self.logger.message(f"Data with ID {id_value} updated in {table_name}.")
                except mysql.connector.Error as e:
                    self.logger.message(f"Failed to update data in {table_name}: {e}")
                    continue  # Continue to the next table if there's an error in this one

        except mysql.connector.Error as e:
            self.logger.message(f"Database error during update: {e}")
        except ValueError as ve:
            self.logger.message(f"Value error: {ve}")
        except Exception as e:
            self.logger.message(f"Unexpected error during update: {e}")

    #def remove_element(self, num_id):
    #    self.logger.message(f"Remove element {num_id}")

    def remove_element(self, element_id):
        try:
            print(f"removing data by id ",element_id)
            self.remove_data_by_id(element_id)
        except Exception as e:
            print(f"can not removing data by id ", element_id)
            self.logger.message(e)
            pass
        return element_id

    def add_element(self, values, num_param=0):
        table_names = self.get_all_table_names()
        if "id" not in values.keys():
            values['id'] = int(1 + int(values["parent"]) / 10000) * 10000 + self.generate_unique_id() + num_param
        id_data = values['id']

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
        return id_data

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
            try:
                query = f"SELECT * FROM {table} WHERE {feature} ORDER BY {feature} ASC"
                self.cursor.execute(query)

                results = self.cursor.fetchall()
                for result in results:
                    if result not in list_features:
                        list_features.append(result[0])
            except:
                pass
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


def remove_database_info(db, data_base_name="gui"):
    db.switch_database(f"{data_base_name}_conf")
    for table in db.get_all_table_names():
        db.delete_table(table)

    db.switch_database(f"{data_base_name}_reports_list")
    for table in db.get_all_table_names():
        db.delete_table(table)

    db.switch_database(f"{data_base_name}_logs")
    for table in db.get_all_table_names():
        db.delete_table(table)


def init_loader(data_base_name='old', loading_window=None):
    create_schema("localhost", "root", "Aa123456", "loader_info")

    db = Database(host="localhost",loading_window=loading_window, user="root", passwd="Aa123456", database=f"loader_info")
    db.connect()

    columns = {"last_gui": "VARCHAR(255)"}
    db.create_table("main_gui", columns)

    if not db.find_data(table_name='main_gui', feature='last_gui'):
        data = {"last_gui": data_base_name}
        db.add_data_to_table("main_gui", data)

    columns = {"gui_names": "VARCHAR(255)"}
    db.create_table("all_gui", columns)
    if not db.find_data(table_name='all_gui', feature_info='OLD', feature='gui_names'):
        data_all = {"gui_names": data_base_name}
        db.add_data_to_table("all_gui", data_all)
    db.disconnect()
    init_database(data_base_name)


def init_database(data_base_name, copy=None):
    if copy is None:
        create_schema("localhost", "root", "Aa123456", f"{data_base_name}_conf")
    else:
        copy_schema("localhost", "root", "Aa123456",
                    f"{copy}_conf",
                    f"{data_base_name}_conf")

    create_schema("localhost", "root", "Aa123456", f"{data_base_name}_reports_list")
    create_schema("localhost", "root", "Aa123456", f"{data_base_name}_logs")
    create_schema("localhost", "root", "Aa123456", f"{data_base_name}_setup")
    db = Database(host="localhost", user="root", passwd="Aa123456", database=f"{data_base_name}_conf")
    db.connect()
    # remove_database_info(db, data_base_name)

    db.switch_database(f'{data_base_name}_conf')
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
               "on_state": "VARCHAR(255)",
               "off_state": "VARCHAR(255)"}

    db.create_table("buttons", columns)

    columns = {"id": "INT",
               "function_name": "VARCHAR(255)",
               "function_info": "VARCHAR(255)"}

    db.create_table("transmit_com", columns)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "maxByte": "INT",
               "minByte": "INT",
               "maxBit": "INT",
               "minBit": "INT"}

    db.create_table("frs_info", columns)

    columns_to_add = {
        'factor': 'FLOAT DEFAULT 1',
        'sign': 'BOOLEAN DEFAULT FALSE',
        'type_number': "VARCHAR(255) DEFAULT 'HEX'"
    }

    db.add_missing_columns('frs_info', columns_to_add)

    columns = {"id": "INT AUTO_INCREMENT PRIMARY KEY",
               "Type": "VARCHAR(255)",
               "last_conn_info": "VARCHAR(255)",
               "baud_rate": "VARCHAR(255)",
               "frame_rate": "VARCHAR(255)",
               "start_byte": "INT",
               "packet_size": "INT",
               "header": "VARCHAR(255)"}

    db.create_table("com_info", columns)

    data_main = {
        "Width": "1170",
        "Height": "830",
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
        "y": 100,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000002",
        "info_table": "script"
    }
    data_info = {
        "Width": "1160",
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
        "y": 0,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000004",
        "info_table": ""
    }
    data_frs = {
        "Width": "900",
        "Height": "400",
        "label_name": "FRS Info",
        "x": 260,
        "y": 200,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000011",
        "info_table": ""
    }
    data_coms = {
        "Width": "900",
        "Height": "200",
        "label_name": "ComPorts",
        "x": 0,
        "y": 0,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000012",
        "info_table": ""
    }
    data_tester = {
        "Width": "250",
        "Height": "400",
        "label_name": "Tester",
        "x": 0,
        "y": 200,
        "parent": "000001",
        "class": "<class '__main__.DraggableRightClickMenu'>",
        "id": "000013",
        "info_table": ""
    }

# id => id length = 6 , first 2 is depth, last 4 is id random generated by function
    db.add_data_to_table("label_param", data_main)
    db.add_data_to_table("label_param", data_script)
    db.add_data_to_table("label_param", data_info)
    db.add_data_to_table("label_param", data_scope)
    db.add_data_to_table("label_param", data_frs)
    db.add_data_to_table("label_param", data_coms)
    db.add_data_to_table("label_param", data_tester)
    columns_scope = {"scope_number": "VARCHAR(255)",
                     "scope_address": "VARCHAR(255)",
                     "scope_type": "VARCHAR(255)"}

    db.create_table("scopes", columns_scope)

    db.switch_database('reports_list')
    db.switch_database(f"{data_base_name}_reports_list")
    columns = {"ResultStatus": "INT",
               "project_name": "VARCHAR(255)",
               "test_name": "VARCHAR(255)",
               "workOrder": "VARCHAR(255)",
               "model": "VARCHAR(255)",
               "gui_type": "VARCHAR(255)",
               "gui_ver": "VARCHAR(255)",
               "StartTimeFormatted": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
               "GroupResults": "VARCHAR(255)"}
    db.create_table("init_report", columns)
    init_report = {
        "ResultStatus": 0,
        "project_name": "test_project",
        "test_name": "UART.SCRIPT",
        "workOrder": "12345",
        "model": "CARD1",
        "gui_type": "Test",
        "gui_ver": "1.0",
        "GroupResults": ""
    }
    db.add_data_to_table("init_report", init_report)

    columns = {
        "StepResults": "VARCHAR(255)",
        "GroupName": "VARCHAR(255)",
        "ResultStatus": "INT",
        "NumOfFail": "INT"}
    db.create_table("init_table", columns)
    init_table = {
        "StepResults": "",
        "GroupName": "",
        "ResultStatus": 2,
        "NumOfFail": 0
    }
    db.add_data_to_table("init_table", init_table)

    columns = {
        "StepName": "VARCHAR(255)",
        "Description": "VARCHAR(255)",
        "Min": "VARCHAR(255)",
        "Max": "VARCHAR(255)",
        "ResultStatus": "INT",
        "Message": "VARCHAR(255)",
        "TestStart": "VARCHAR(255)"}
    db.create_table("init_test", columns)
    init_test = {
        "StepName": "",
        "Description": "",
        "Min": "",
        "Max": "",
        "ResultStatus": 0,
        "Message": "",
        "TestStart": ""
    }
    db.add_data_to_table("init_test", init_test)
    db.disconnect()
    return data_base_name


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
