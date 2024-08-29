import tkinter as tk
from tkinter import ttk
import os
import subprocess


class FindReportWindow:
    def __init__(self, parent, database):
        self.results_tree = None
        self.search_entry = None
        self.report = 'reports_list'
        self.window = parent
        self.database = database
        self.search_type = tk.StringVar(value="Logs")
        self.sort_by = tk.StringVar(value="Name")
        self.sort_order = tk.BooleanVar(value=True)  # True for ascending, False for descending

        self.window.title("Find Report")

        self.create_widgets()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("Treeview.Heading",
                        background="gray",
                        foreground="black",
                        font=('Arial', 10, 'bold'),
                        padding=[5, 5, 5, 5],
                        relief="raised")

        style.configure("Treeview",
                        rowheight=25,
                        background="white",
                        foreground="black",
                        fieldbackground="white",
                        relief="flat")

        style.map('Treeview',
                  background=[('selected', 'lightblue')],
                  relief=[('selected', 'solid')])

        search_label = tk.Label(self.window, text="Search Type:")
        search_label.grid(row=0, column=0, padx=10, pady=10)

        search_type_menu = ttk.Combobox(
            self.window, textvariable=self.search_type, state="readonly"
        )
        search_type_menu['values'] = ("Logs", "Reports")
        search_type_menu.grid(row=0, column=1, padx=10, pady=10)
        search_type_menu.bind("<<ComboboxSelected>>", self.update_search_results)

        search_entry_label = tk.Label(self.window, text="Search:")
        search_entry_label.grid(row=1, column=0, padx=10, pady=10)

        self.search_entry = tk.Entry(self.window, width=50)
        self.search_entry.grid(row=1, column=1, padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", self.update_search_results)

        self.results_tree = ttk.Treeview(self.window, columns=("Name", "Date"), show="headings")
        self.results_tree.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.results_tree.heading("Name", text="Name", command=lambda: self.sort_column("Name"))
        self.results_tree.heading("Date", text="Date", command=lambda: self.sort_column("Date"))
        # Bind double-click event to open file
        self.results_tree.bind("<Double-1>", self.open_file)

        self.update_search_results()

    def update_search_results(self, event=None):
        search_query = self.search_entry.get()
        search_type = self.search_type.get()

        results = []

        # Clear the Treeview
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)

        # Fetch the appropriate data based on search type
        if search_type == "All" or search_type == "Reports":
            results.extend(self.search_reports(search_query))
        if search_type == "All" or search_type == "Logs":
            results.extend(self.search_logs(search_query))

        # Sort the results based on the selected column and order
        results = sorted(results, key=lambda x: x[self.sort_by.get()], reverse=not self.sort_order.get())

        # Populate the Treeview with the new results
        for result in results:
            self.results_tree.insert("", "end", values=(result["Name"], result["Date"]))

    def search_reports(self, query):
        self.database.switch_database(self.report)
        reports = self.database.find_data("init_report")
        # self.database.switch_database()
        results = []
        for name in reports:
            results.append({
                "Name": name["GroupResults"],
                "Date": name["StartTimeFormatted"],
            })
        return results

    def search_logs(self, query):
        self.database.switch_database('logs')  # Switch to the 'logs' database

        table_names = self.database.get_all_table_names()  # Get all table names
        results = []

        for name in table_names:
            # Search for the query in the table names
            if query.lower() in name.lower():
                # Fetch the timestamp of the first log entry in the table
                sql = f"SELECT timestamp FROM {name} WHERE id = 1"
                self.database.cursor.execute(sql)
                first_timestamp = self.database.cursor.fetchone()

                if first_timestamp:
                    results.append({
                        "Name": name,
                        "Date": first_timestamp[0].strftime("%Y-%m-%d %H:%M:%S"),  # Format the timestamp
                    })
        return results

    def sort_column(self, col):
        if self.sort_by.get() == col:
            self.sort_order.set(not self.sort_order.get())
        else:
            self.sort_by.set(col)
            self.sort_order.set(True)

        self.update_search_results()

    def open_file(self, event):
        selected_item = self.results_tree.selection()[0]  # Get selected item
        item_name = self.results_tree.item(selected_item, "values")[0]  # Get the item name from the selected item

        if self.search_type.get() == "Reports":
            # If it's a report (from the database), print the message
            print("This is a database routine")
        elif self.search_type.get() == "Logs":
            # Ensure the 'log' directory exists
            log_dir = os.path.join(os.getcwd(), "log")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)  # Create the directory if it doesn't exist

            # Set the file path using the table name as the filename
            temp_file_path = os.path.join(log_dir, f"{item_name}.txt")

            # Retrieve the log content from the database
            sql = f"SELECT * FROM {item_name}"
            self.database.cursor.execute(sql)
            log_entries = self.database.cursor.fetchall()

            # Write the log entries to the file
            with open(temp_file_path, 'w') as temp_file:
                for entry in log_entries:
                    log_time = entry[1].strftime('%H:%M:%S:%f')  # Formatting the datetime to the desired format
                    log_level = entry[2]
                    log_message = entry[3]

                    # Representing the log entry in the desired format
                    formatted_log_entry = f"{log_time}-{log_level}: {log_message}"
                    temp_file.write(f"{formatted_log_entry}\n")  # Write each log message as a line

            # Open the file with the default application
            if os.path.exists(temp_file_path):
                try:
                    subprocess.Popen(['open', temp_file_path])  # For macOS
                except FileNotFoundError:
                    try:
                        os.startfile(temp_file_path)  # For Windows
                    except AttributeError:
                        subprocess.call(['xdg-open', temp_file_path])  # For Linux
        else:
            # Handle other cases if necessary
            print("Unknown item type")


class MenuBar:
    def __init__(self, root, database):
        self.menubar = tk.Menu(root)
        root.config(menu=self.menubar)
        self.database = database
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.add_menu = tk.Menu(self.menubar, tearoff=0)
        self.info_menu = tk.Menu(self.menubar, tearoff=0)

        self.create_file_menu()
        self.create_view_menu()
        self.create_add_menu()
        self.create_info_menu()

    def create_file_menu(self):
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New Setup", command=self.new_setup)
        self.file_menu.add_command(label="Load Setup", command=self.load_setup)
        self.file_menu.add_command(label="Save Setup", command=self.save_setup)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)

    def create_view_menu(self):
        self.menubar.add_cascade(label="Tools", menu=self.view_menu)
        self.view_menu.add_command(label="Search", command=self.report)
        self.view_menu.add_command(label="Get Multi-Feature", command=self.features_info)

    def create_add_menu(self):
        self.menubar.add_cascade(label="Add", menu=self.add_menu)
        self.add_menu.add_command(label="Add Item", command=self.add_item)

    def create_info_menu(self):
        self.menubar.add_cascade(label="Info", menu=self.info_menu)
        self.info_menu.add_command(label="Version", command=self.show_version)

    def new_setup(self):
        print("New Setup")

    def load_setup(self):
        print("Load Setup")

    def save_setup(self):
        print("Save Setup")

    def exit_app(self):
        print("Exit App")
        quit()

    def report(self):
        root_report = tk.Toplevel(self.menubar)  # Use Toplevel instead of Tk
        root_report.title("Find Report")  # Set a different title for the new window
        find_report_window = FindReportWindow(root_report, self.database)
        print(find_report_window)

    def features_info(self):
        print("Change View")

    def add_item(self):
        print("Add Item")

    def show_version(self):
        print("Version Info")
