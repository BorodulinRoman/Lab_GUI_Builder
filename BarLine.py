import tkinter as tk
from tkinter import ttk
import os
import subprocess
from ReportsAndScriptRun import Report
import pandas as pd
from database import init_database
#BarLine


class AddDataWindow:
    def __init__(self, frame, database, gui_name):
        self.function_combo = None
        self.name = None
        self.gui_name = gui_name
        self.callback = None
        self.frame = frame
        self.database = database
        self.new_window = None
        self.labels = {}
        self.port_var = {}
        self.addkey = False
        self.functions = {}  # Store functions added

    def open_new_window(self, labels=None, boxs=None, name="Add packet label", callback=None, add_functions=False):
        self.callback = callback
        self.name = name
        self.addkey = True
        if labels is None:
            labels = {}

        # Create a new window
        self.new_window = tk.Toplevel(self.frame)
        self.new_window.title(name)

        self.labels = labels
        if boxs is None:
            boxs = []

        # Count the number of blocks (OptionMenus and Entries)
        total_blocks = len(boxs) + len([label for label in labels if label != "location"])
        window_height = 60 + (total_blocks * 60)
        try:
            for box in boxs:
                # OptionMenu for scopes
                for box_name, box in box.items():
                    if box is None:
                        continue
                    self.port_var[box_name] = tk.StringVar()
                    self.port_var[box_name].set(box_name)
                    if not len(box):
                        box = ["None"]

                    temp_box = tk.OptionMenu(self.new_window, self.port_var[box_name], *box)
                    temp_box.pack(pady=(10, 0))
        except Exception as e:
            print(e)

        try:
            # Create Entry widgets for each label except "location"
            for idx, (label, some_data) in enumerate(self.labels.items()):
                if some_data is None or label in ["location", "id"]:
                    continue

                lbl = tk.Label(self.new_window, text=label)
                lbl.pack(pady=(10, 0))

                entry = tk.Entry(self.new_window)
                entry.insert(0, some_data)
                entry.pack(pady=(0, 10))

                self.labels[label] = entry
        except Exception as e:
            print(e)

        # Add "+" button if add_functions flag is True
        if add_functions:
            # Frame to hold "Add" and "Remove" buttons side by side
            window_height += 100
            button_frame = tk.Frame(self.new_window)
            button_frame.pack(pady=(10, 0))

            add_function_button = tk.Button(button_frame, text="Add", command=self.open_function_window)
            add_function_button.pack(side=tk.LEFT, padx=(0, 5))  # Left-align and add space between buttons

            remove_function_button = tk.Button(button_frame, text="Remove", command=self.remove_function)
            remove_function_button.pack(side=tk.LEFT)

            # ComboBox for functions added
            self.function_combo = ttk.Combobox(self.new_window, values=list(self.functions.keys()))
            self.function_combo.pack(pady=(10, 0))

        self.new_window.geometry(f"300x{window_height}")

        ok_button = tk.Button(self.new_window, text="OK", command=self.on_ok)
        ok_button.pack(pady=10)

    def open_function_window(self):
        function_window = tk.Toplevel(self.new_window)
        function_window.title("Add Function")

        function_name_label = tk.Label(function_window, text=f"{self.name} Name:")
        function_name_label.pack(pady=(10, 0))
        function_name_entry = tk.Entry(function_window)
        function_name_entry.pack(pady=(0, 10))

        function_data_label = tk.Label(function_window, text=f"{self.name} Data:")
        function_data_label.pack(pady=(10, 0))
        function_data_entry = tk.Entry(function_window)
        function_data_entry.pack(pady=(0, 10))

        save_button = tk.Button(function_window, text="Save", command=lambda: self.save_function(function_name_entry, function_data_entry, function_window))
        save_button.pack(pady=(10, 0))

    def save_function(self, function_name_entry, function_data_entry, function_window):
        function_name = function_name_entry.get()
        function_data = function_data_entry.get()

        if function_name and function_data:
            # Initialize lists if they don't exist in labels
            if "function_name" not in self.labels:
                self.labels["function_name"] = []
            if "function_info" not in self.labels:
                self.labels["function_info"] = []

            # Add the function name and data to labels
            self.labels["function_name"].append(str(function_name))
            self.labels["function_info"].append(str(function_data))

            # Update ComboBox values
            self.function_combo['values'] = self.labels["function_name"]

            # Close the function window
            function_window.destroy()

    def remove_function(self):
        selected_function = self.function_combo.get()
        if selected_function:
            # Find the index of the selected function in function_name list
            try:
                index = self.labels["function_name"].index(selected_function)

                # Remove function name and corresponding info by index
                self.labels["function_name"].pop(index)
                self.labels["function_info"].pop(index)

                # Update ComboBox values and clear selection
                self.function_combo['values'] = self.labels["function_name"]
                self.function_combo.set('')  # Clear ComboBox selection
            except ValueError:
                pass  # If the function is not found, do nothing

    def on_ok(self):
        for label, widget in self.labels.items():
            if isinstance(widget, tk.Entry):
                self.labels[label] = widget.get()

        for name, var in self.port_var.items():
            self.labels[name] = var.get()

        self.addkey = False
        self._update_database()
        self.new_window.destroy()

    def _update_database(self):
        if self.callback is not None:
            self.callback(self.labels)
        else:
            self.database.switch_database(f"{self.gui_name}_conf")

            self.database.add_element(self.labels)


class FindReportWindow:
    def __init__(self, parent, database, gui_name):
        self.results_tree = None
        self.search_entry = None
        self.gui_name = gui_name
        self.gui_ver = 'test'
        self.report = f'{gui_name}_reports_list'
        self.logs = f'{gui_name}_logs'
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
        if search_type == "Reports":
            results = self.search_reports(search_query)
        if search_type == "Logs":
            results = self.search_logs(search_query)


        # Sort the results based on the selected column and order
        results = sorted(results, key=lambda x: x[self.sort_by.get()], reverse=not self.sort_order.get())

        # Populate the Treeview with the new results
        for result in results:
            values = [val for val in result.values()]
            self.results_tree.insert("", "end", values=values)

    def search_reports(self, query):
        self.database.switch_database(self.report)
        reports = self.database.find_data("init_report")
        results = []
        for name in reports:
            if query.lower() in name["GroupResults"].lower():
                if name["GroupResults"]:
                    results.append({
                        "Name": name["GroupResults"],
                        "Date": name["StartTimeFormatted"],
                    })
        return results

    def search_logs(self, query):
        self.database.switch_database(self.logs)  # Switch to the 'logs' database

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
        item_name = self.results_tree.item(selected_item, "values")[0]

        if self.search_type.get() == "Reports":
            self._open_report(item_name)
        elif self.search_type.get() == "Logs":
            self._open_log_file(item_name)
        else:
            print("Unknown item type")



    def _open_log_file(self, item_name):
        # Ensure the 'log' directory exists
        log_dir = os.path.join(os.getcwd(), "info/log")
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

    def _open_report(self, item_name):
        name = self.database.database
        self.database.switch_database(self.report)
        report_builder = Report(self.database, self.gui_name, self.gui_ver)
        show_report = {}

        report_path = os.path.join(os.getcwd(), "info/reports")
        if not os.path.exists(report_path):
            os.makedirs(report_path)

        reports = self.database.find_data(table_name="init_report", feature="GroupResults")
        for report in reports:
            if item_name in report["GroupResults"]:
                show_report = report
                show_report["GroupResults"] = []
                break

        tests = self.database.find_data(table_name="init_test", feature="Description")
        show_tests = []
        for test in tests:
            if item_name in test['Description']:
                show_tests.append(test)

        tables = self.database.find_data(table_name="init_table", feature="StepResults")
        for table in tables:
            if item_name in table["StepResults"]:
                test_name = f"{table['GroupName']}_{item_name}"
                table["StepResults"] = []
                for test in show_tests:
                    if test_name in test['Description']:
                        table["StepResults"].append(test)
                show_report["GroupResults"].append(table)

        dt = show_report["StartTimeFormatted"]
        show_report["StartTimeFormatted"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        report_builder.report = show_report
        report_builder.build_report()
        self.database.switch_database(name)


class FeatureWindow:
    def __init__(self, parent, database, gui_name):
        self.search_var = None
        self.database = database
        self.ok_button = None
        self.combo = None
        self.gui_name = gui_name
        self.feature_vars = None
        self.tree = None
        self.top = None
        self.parent = parent
        self.features = []  # Store all features
        self.sorted_ascending = True  # Flag to track sorting order
        self.create_window()

    def create_window(self):
        # Create Toplevel window
        self.top = tk.Toplevel(self.parent)
        self.top.title("Multi-Features Statistic")

        # Search box for filtering features
        search_label = ttk.Label(self.top, text="Search Features:")
        search_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(self.top, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        search_entry.bind("<KeyRelease>", self.filter_features)

        # Create Treeview for feature selection with checkboxes
        self.tree = ttk.Treeview(self.top, columns=("Select", "Feature"), show="headings", height=10)
        self.tree.heading("Select", text="Select")
        self.tree.heading("Feature", text="Feature", command=self.sort_features)
        self.tree.column("Select", width=180, anchor='center')
        self.tree.column("Feature", width=150)
        self.tree.grid(row=2, column=0, padx=10, pady=10, columnspan=2)

        # Adding features with checkboxes in Treeview
        self.features = self._get_features()
        self.feature_vars = {feature: False for feature in self.features}  # Store checkbox states
        self.update_treeview(self.features)

        # Bind click event to toggle checkboxes
        self.tree.bind("<Button-1>", self.toggle_checkbox)

        # Add Combobox for function selection
        self.combo = ttk.Combobox(
            self.top, values=["Save as CSV", "Generate Graph"], state="readonly"
        )
        self.combo.grid(row=3, column=1, padx=10, pady=10)
        self.combo.set("Select Function")

        # OK button to trigger selected function
        self.ok_button = ttk.Button(self.top, text="OK", command=self.run_function)
        self.ok_button.grid(row=3, column=0, padx=10, pady=10)

    def _get_features(self):
        self.database.switch_database(f'{self.gui_name}_reports_list')  # Switch to the 'logs' database
        results = []
        steps = self.database.find_data(table_name="init_test", feature="StepName")  # Get all table names
        for step in steps:
            if not step["StepName"]:
                continue
            if step["StepName"] not in results:
                results.append(step["StepName"])
        return results

    def update_treeview(self, features):
        # Clear current items in Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Insert updated features
        for feature in features:
            self.tree.insert("", "end", values=("[ ]", feature))

    def toggle_checkbox(self, event):
        # Detect which item was clicked
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if column == "#1" and item_id:  # Check if the click was on the "Select" column
            current_value = self.tree.item(item_id, 'values')[0]
            feature_name = self.tree.item(item_id, 'values')[1]

            # Toggle checkbox state
            if current_value == "[ ]":
                self.tree.item(item_id, values=("[X]", feature_name))
                self.feature_vars[feature_name] = True
            else:
                self.tree.item(item_id, values=("[ ]", feature_name))
                self.feature_vars[feature_name] = False

    def filter_features(self, event):
        # Filter features based on search input
        search_text = self.search_var.get().lower()
        filtered_features = [feature for feature in self.features if search_text in feature.lower()]
        self.update_treeview(filtered_features)

    def sort_features(self):
        # Sort features alphabetically, toggling between ascending and descending
        self.features.sort(reverse=not self.sorted_ascending)
        self.sorted_ascending = not self.sorted_ascending
        self.update_treeview(self.features)

    def run_function(self):
        selected_function = self.combo.get()
        selected_features = [feature for feature, selected in self.feature_vars.items() if selected]

        # Call the appropriate function based on the ComboBox selection
        if selected_function == "Save as CSV":
            self.save_as_csv(selected_features)
        elif selected_function == "Generate Graph":
            self.generate_graph(selected_features)
        else:
            print("No function selected or invalid function chosen.")

    def save_as_csv(self, features):
        features_data = []
        for item_name in features:
            data = self.database.find_data(table_name="init_test", feature_info=item_name, feature="StepName")
            for d in data:
                features_data.append(d)
        df = pd.DataFrame(features_data)
        log_dir = os.path.join(os.getcwd(), "info/csv")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)  # Create the directory if it doesn't exist
        temp_file_path = os.path.join(log_dir, f"{'_'.join(features)}.csv")
        df.to_csv(temp_file_path, index=False)
        os.startfile(temp_file_path)

    def generate_graph(self, features):
        # Example function that simulates generating a graph for selected features
        print(f"Function: Generate Graph, Features: {features}")


class MenuBar:
    def __init__(self, root, database, gui_name):
        self.options = []
        self.logger = database.logger
        self.menubar = tk.Menu(root)
        self.root = root
        root.config(menu=self.menubar)
        self.add_window = AddDataWindow(frame=root,database=database, gui_name="loader_info")
        self.database = database
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.add_menu = tk.Menu(self.menubar, tearoff=0)
        self.info_menu = tk.Menu(self.menubar, tearoff=0)
        self.load_setup_menu = tk.Menu(self.file_menu, tearoff=0)  # Submenu for "Load Setup"
        self.gui_name = gui_name
        self.create_file_menu()
        self.create_view_menu()
        self.create_add_menu()
        self.create_info_menu()

    def create_file_menu(self):
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New Setup", command=self.new_setup)
        self.file_menu.add_command(label="Copy Setup", command=self.copy_setup)
        self.file_menu.add_cascade(label="Load Setup", menu=self.load_setup_menu)
        self.database.switch_database("loader_info")
        # List of options

        self.options = [option['gui_names'] for option in self.database.find_data(table_name='all_gui', feature='gui_names')]

        for option in self.options:
            self.load_setup_menu.add_command(
                label=option,
                command=lambda opt=option: self.load_setup_option(opt)
            )

        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)

    def load_setup_option(self, option_name):
        self.logger.message(f"Option {option_name} selected")
        self.open_gui({"gui_names":option_name})
        # Implement the logic based on the selected option

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
        self.logger.message("New Setup")
        self.database.switch_database("loader_info")
        self.add_window.open_new_window(labels={'gui_names': ""}, callback=lambda values: self._new_setup(values))

    def _new_setup(self, values):
        self.database.add_data_to_table('all_gui', values)
        init_database(values['gui_names'])
        self.open_gui(values)

    def open_gui(self, values):
        last_guis = self.database.find_data(table_name='main_gui', feature="last_gui")
        self.database.switch_database("loader_info")
        for last in last_guis:
            self.database.remove_data_feature(table_name="main_gui",
                                              feature="last_gui",
                                              value=last["last_gui"])
        self.database.add_data_to_table('main_gui', {"last_gui": values['gui_names']})

        from Empty import lab_runner
        lab_runner(gui_name=None, root_main=self.root)

    def copy_setup(self):
        self.logger.message("Copy Setup")
        self.database.switch_database("loader_info")
        self.add_window.open_new_window(labels={'gui_names': ""}, boxs=[{"Setup to Copy": self.options}],
                                        callback=lambda values: self._copy_setup(values))

    def _copy_setup(self, values):
        init_database(values['gui_names'], values["Setup to Copy"])
        self.database.add_data_to_table('all_gui', {"gui_names": values['gui_names']})
        self.open_gui({"gui_names": values['gui_names']})

    def load_setup(self):
        self.logger.message("Load Setup")

    def exit_app(self):
        self.logger.message("Exit App")
        quit()

    def report(self):
        root_report = tk.Toplevel(self.menubar)  # Use Toplevel instead of Tk
        root_report.title("Find Report")  # Set a different title for the new window
        find_report_window = FindReportWindow(root_report, self.database, self.gui_name)
        self.logger.message(find_report_window)

    def features_info(self):
        FeatureWindow(self.menubar, self.database, self.gui_name)

    def add_item(self):
        self.logger.message("Add Item")

    def show_version(self):
        self.logger.message("Version Info")
