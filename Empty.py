import time
from tkinter import Menu, messagebox
import datetime
from DeviceManager import DeviceManager, extract_bits, ScopeUSB
from database import Database, Logger, init_database
from ReportsAndScriptRun import Script
from tkinter import filedialog
from BarLine import *
# import multiprocessing
import tkinter as tk
import threading
# from tkinter import simpledialog
#shira

def round_to_nearest_10(n):
    if n < 0:
        return 0
    """Round the number to the nearest multiple of 10, rounding up on ties."""
    return ((n + 5) // 10) * 10


class AddDataWindow:
    def __init__(self, frame, database, gui_name):
        self.gui_name = gui_name
        self.callback = None
        self.frame = frame
        self.database = database
        self.new_window = None
        self.labels = {}
        self.port_var = {}  # Initialize port_var as an empty dictionary
        self.addkey = False

    def open_new_window(self, labels=None, boxs=None, name="Add packet label", callback=None):
        self.callback = callback
        self.addkey = True
        if labels is None:
            return 0

        # Create a new window
        self.new_window = tk.Toplevel(self.frame)
        self.new_window.title(name)

        self.labels = labels

        # Count the number of blocks (OptionMenus and Entries)
        total_blocks = len(boxs) + len([label for label in labels if label != "location"])

        # Calculate the dynamic height of the window based on the number of blocks
        window_height = 60 + (total_blocks * 60)  # 50px per block
        self.new_window.geometry(f"300x{window_height}")

        # OptionMenu for scopes
        for box_name, box in boxs.items():
            if box is None:
                continue
            self.port_var[box_name] = tk.StringVar()
            self.port_var[box_name].set(box_name)
            if not len(box):
                box = ["None"]

            # Create an OptionMenu widget
            temp_box = tk.OptionMenu(self.new_window, self.port_var[box_name], *box)
            temp_box.pack(pady=(10, 0))

        # Create Entry widgets for each label except "location"
        for idx, (label, some_data) in enumerate(self.labels.items()):
            if some_data is None:
                continue
            if label == "location":
                continue

            # Label for the entry
            lbl = tk.Label(self.new_window, text=label)
            lbl.pack(pady=(10, 0))

            # Entry widget
            entry = tk.Entry(self.new_window)
            entry.pack(pady=(0, 10))

            # Save entry widget reference in the labels dict
            self.labels[label] = entry

        # OK button to close the window and save the data
        ok_button = tk.Button(self.new_window, text="OK", command=self.on_ok)
        ok_button.pack(pady=10)

    def on_ok(self):
        # Save the data from Entry widgets
        for label, widget in self.labels.items():
            if isinstance(widget, tk.Entry):
                self.labels[label] = widget.get()  # Get the text from the Entry widget

        # Save the selected option from OptionMenu (port_var)
        for name, var in self.port_var.items():
            self.labels[name] = var.get()  # Get the selected scope
        self.addkey = False
        self._update_database()
        self.new_window.destroy()

    def _update_database(self):
        if self.callback is not None:
            self.callback(self.labels)
        else:
            self.database.switch_database(f"{self.gui_name}_conf")
            self.database.add_element(self.labels)


class ScriptRunnerApp:
    def __init__(self, root, loger, database, gui_name):
        self.script = Script(loger, database, gui_name=gui_name)
        self.logger = loger
        self.load_button = None
        self.info_label = None
        self.start_button = None
        self.stop_button = None
        self.script_lines = None
        self.root = root

        self.filepath = ""
        self.running = False
        self.init()
        # Create Load Button

    def init(self):
        self.load_button = tk.Button(self.root, text="Load file", command=self.load_script)
        self.load_button.place(x=15, y=35, width=60, height=30)

        # Create Label
        self.info_label = tk.Label(self.root, text="----------------------------")
        self.info_label.place(x=5, y=5)

        # Create Start Button
        self.start_button = tk.Button(self.root, text="Start", command=self.start_script)
        self.start_button.place(x=85, y=35, width=60, height=30)
        self.start_button.config(state=tk.DISABLED)

        # Create Stop Button
        self.stop_button = tk.Button(self.root, text="Abort", command=self.stop_script)
        self.stop_button.place(x=155, y=35, width=60, height=30)
        self.stop_button.config(state=tk.DISABLED)

    def load_script(self):
        filetypes = (("Script files", "*.script"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.filepath = filepath.split("/")[-1]
            self.info_label.config(text=self.filepath)

            with open(filepath, 'r') as file:
                lines = file.readlines()
            self.script_lines = [line.strip() for line in lines]
            self.start_button.config(state=tk.NORMAL)

        else:
            self.info_label.config(text="No file selected")

    def start_script(self):
        self.script.report.script_name = f"{self.filepath[:-7]}{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        if self.filepath:
            self.running = True
            self.info_label.config(text="Start " + self.filepath)
            self.load_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            thread = threading.Thread(target=self.run_script)
            thread.daemon = True  # Daemonize the thread to ensure it closes when the main program exits
            thread.start()
        else:
            self.info_label.config(text="Please load a script first.")

    def run_script(self):
        if self.running:
            self.script.report.build()
            for line in self.script_lines:
                if not self.running:
                    break
                if len(line) <= 2:
                    continue

                self.logger.message(f"Run: {line}")
                self.root.update_idletasks()
                self.script.run(line)

        self.start_button.config(state=tk.NORMAL)
        self.load_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        # todo change it to Database save
        self.script.report.save_report()
        self.logger.message("Done!")

    def stop_script(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.load_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.info_label.config(text=f"Script {self.filepath} stopped!")


class RightClickMenu(tk.LabelFrame):
    """A label frame that shows a context menu on right-click."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000", width=0, height=0, text=None):
        """Initialize the RightClickMenu with a root, parent, label, width, height, and optional text."""
        self.scopes = None
        self.logger = log
        self.gui_name = main_root.gui_name
        self.element = values
        if "Type" not in values.keys():
            self.element["Type"] = None
        super().__init__(parent_info, text=text if text else values["label_name"])
        self.config(width=int(values['Width']), height=int(values['Height']))
        self.label_name = None
        self.menu = None
        self.x_start = None
        self.y_start = None
        self.add_window = AddDataWindow(main_root, database=db_gui, gui_name=self.gui_name)
        self.root = main_root  # Reference to the root window
        self.visaDevices = DeviceManager(logger=self.logger)
        self.root.com_list = self.visaDevices.find_devices()
        self.gen_id = gen_id
        self.parent_info = parent_info
        self.config(width=width, height=height, bg=parent_info['bg'])  # Match parent's background
        self.grid_propagate(False)
        self.db = Database(f"{self.gui_name}_conf", self.logger)
        self.bind("<Button-3>", self.show_menu)

    def show_menu(self, event):
        """Show the context menu at the event's location."""
        self.create_menu(event.x_root, event.y_root)  # Pass click location
        self.menu.tk_popup(event.x_root, event.y_root)

    def create_menu(self, x, y):
        """Create the cont
        11ext menu based on the current state."""
        self.menu = Menu(self, tearoff=0)
        if self.root.change_mode:
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Disable Change Mode', command=self.disable_change_mode)
            if self.gen_id not in [0, 1, 2, 3, 4]:
                self.menu.add_command(label='Remove', command=self.del_label)
            if self.gen_id not in [2, 3, 4] and self.element['Type'] is None:
                self.menu.add_cascade(label='New', menu=self.build_menu(x, y))  # Add the submenu to the main menu
            if 'ComTransmitRightClickMenu' in self.element["class"]:
                self.menu.add_command(label='Add Functions', command=self.add_functions)
        else:
            if self.gen_id == 4:
                self.menu.add_command(label='Add Scope', command=self.add_scope)
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Enable Change Mode', command=self.confirm_enable_change_mode)

    def del_label(self):
        """Delete the label and save the setup."""
        answer = messagebox.askyesno("Remove Element", "Are you sure you want to remove element?")
        if not answer:
            return
        try:
            temp = self.db.remove_element(self.gen_id)
            self.destroy()  # This destroys the widget
            self.logger.message(f"Removed '{temp}'")
        except Exception as e:
            self.logger.message(f"Error removing label: {e}", log_level="ERROR")

    def build_menu(self, x, y):
        """Build the submenu for creating new widgets."""
        data_rcm = DataDraggableRightClickMenu
        drag_rcm = DraggableRightClickMenu
        create_menu = Menu(self.menu, tearoff=0)  # Create a new submenu
        create_menu.add_command(label='Data Label', command=lambda: self.packet_label(x, y, data_rcm))
        create_menu.add_command(label='Label', command=lambda: self.open_creation_window(x, y, drag_rcm))
        create_menu.add_cascade(label='Comports',
                                menu=self.build_comports_menu(x, y, create_menu))  # Fixed: add_cascade
        create_menu.add_command(label='Entry window', command=lambda: self.open_creation_window(x, y, drag_rcm))
        return create_menu

    def build_comports_menu(self, x, y, menu):
        comp_rcm = ComPortRightClickMenu
        comt_rcm = ComTransmitRightClickMenu
        comb_rcm = ButtonTransmitRightClickMenu
        create_menu = Menu(menu, tearoff=0)  # Create a new submenu
        create_menu.add_command(label='Port Connection', command=lambda: self.open_com_box(x, y, comp_rcm))
        create_menu.add_command(label='Transmit box', command=lambda: self.open_transmit_box(x, y, comt_rcm))
        create_menu.add_command(label='Button Transmit', command=lambda: self.open_button(x, y, comb_rcm))
        return create_menu

    def add_scope(self):
        try:
            self.scopes = ScopeUSB(self.logger)
            scopes_list = [scope for scope in self.scopes.scopes.keys()]
            scopes_type = [scope["scope_type"] for scope in self.scopes.scopes.values()]
            self.logger.message(f"For KeySight Get scope name from,  Utility -> I/O -> VISA Address ")
            self.add_window.open_new_window({"scope_number": ""},
                                            {"scope_address": scopes_list, "scope_type": scopes_type},
                                            "Add new Scope")

        except Exception as e:
            self.logger.message(f"Can't Add label to scopes, {e}")

    def open_creation_window(self, x, y, cls):
        label = {'label_name': 'New Widget'}  # Set the default name
        boxs = {"Dimension": ['250x400', '520x400', '900x400', '300x600', '900x200', '250x200']}
        self.add_window.open_new_window(label, boxs, "Create New Widget",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls))

    def add_functions(self):
        self.add_window.open_new_window(name="Add Functions")

    def get_coms_data(self):
        dic_ids = {}
        ids_data = self.db.find_data("com_info", "com_list", "Type")
        for id_label in ids_data:
            name = self.db.find_data("label_param", id_label['id'])
            if name:
                dic_ids[name[0]['label_name']] = id_label['id']
        return dic_ids

    def packet_label(self, x, y, cls):
        dic_ids = self.get_coms_data()
        label = {'label_name': 'New Packet', 'maxByte': 0, 'minByte': 0, 'maxBit': 0, 'minBit': 0}
        boxs = {"Dimension": ['130x40', '300x40', '600x40'], 'info_table': list(dic_ids.keys())}

        self.add_window.open_new_window(label, boxs, "Create New Widget",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids))

    def open_com_box(self, x, y, cls):
        label = {'label_name': 'New combo', "last_conn_info": None, "baud_rate": "115200"}
        boxs = {"Dimension": ['250x70']}
        self.add_window.open_new_window(label, boxs, "Create New Com Communication",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls))

    def open_transmit_box(self, x, y, cls):
        dic_ids = self.get_coms_data()
        label = {'label_name': 'New combo', "last_conn_info": None, "func": None}
        boxs = {"Dimension": ['160x100', '260x100', '600x100'], 'info_table': list(dic_ids.keys())}
        self.add_window.open_new_window(label, boxs, "Create New Com transmit box",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids))

    def open_button(self, x, y, cls):
        dic_ids = self.get_coms_data()
        label = {'label_name': 'New combo', "on_state": "", "off_state": ""}
        boxs = {'info_table': list(dic_ids.keys()), "Dimension": ['50x60', '70x60', '90x60']}
        self.add_window.open_new_window(label, boxs, "Create New Button transmit box",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids))

    def create_new_widget_with_settings(self, values, x, y, cls, dict_ids=None):
        com_id = 0
        if dict_ids is not None:
            for key, val in values.items():
                if val in dict_ids:
                    values[key] = dict_ids[val]
                    com_id = dict_ids[val]
        try:
            if "Dimension" in values.keys():
                values['Width'], values['Height'] = values["Dimension"].split('x')
            if "info_table" not in values.keys():
                values['info_table'] = None
            values["x"] = round_to_nearest_10(x - self.winfo_rootx())
            values["y"] = round_to_nearest_10(y - self.winfo_rooty())
            values["parent"] = self.gen_id
            values["class"] = str(cls)
            if cls is ComPortRightClickMenu:
                values["Type"] = "com_list"
            elif cls is ComTransmitRightClickMenu:
                values["Type"] = "function"
            elif cls is DataDraggableRightClickMenu:
                values["Type"] = "Data"
            values["id"] = self.db.add_element(values, int(int(com_id)/10000) * 10000)
            frame = self.root.loader.create_frame(values, self)
            frame.place(x=values["x"], y=values["y"])

            self.logger.message(f"New widget '{values['label_name']}' created at ({x}, {y})")
        except KeyError as e:
            self.logger.message(f"Key error in widget settings: {e}", log_level="ERROR")
        except ValueError as e:
            self.logger.message(f"Value error in widget settings: {e}", log_level="ERROR")

    def confirm_enable_change_mode(self):
        """Confirm with the user before enabling change mode."""
        answer = messagebox.askyesno("Enable Change Mode", "Are you sure you want to enable change mode?")
        if answer:
            self.root.change_mode = True
            self.logger.message("Change mode enabled")
            self.update_menu()

    def disable_change_mode(self):
        """Disable change mode, save the setup, and update the menu."""
        self.root.change_mode = False
        self.logger.message("Change mode disabled")
        self.update_menu()

    def update_menu(self):
        """Update the context menu."""
        self.create_menu(self.winfo_rootx(), self.winfo_rooty())  # Recreate menu with the current root position

    def get_info(self):
        """Print the label's information."""
        element_info = self.db.get_info(self.gen_id)
        self.logger.message(element_info)  # Print the element information
        if element_info:
            self.logger.message(f"Label id '{self.gen_id}' location: ({self.winfo_x()}, {self.winfo_y()})")
        else:
            self.logger.message(f"No element found with id: {self.gen_id}")


class DraggableRightClickMenu(RightClickMenu):
    """A label frame that can be dragged and shows a context menu on right-click."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        """Initialize the DraggableRightClickMenu with a root, parent, and label."""
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id, text=values["label_name"])
        self.label_name = values["label_name"]
        self.rounded_x = 0
        self.rounded_y = 0
        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.stop_drag)

    def on_drag(self, event):
        """Drag the label to a new location, rounding the position to the nearest 10."""
        if self.root.change_mode:
            x = self.winfo_x() - self.x_start + event.x
            y = self.winfo_y() - self.y_start + event.y
            self.rounded_x = round_to_nearest_10(x)
            self.rounded_y = round_to_nearest_10(y)
            self.place(x=self.rounded_x, y=self.rounded_y)
            self.logger.message(f"Dragging '{self.cget('text')}' to ({self.rounded_x}, {self.rounded_y})")

    def start_drag(self, event):
        """Start dragging the label."""
        if self.root.change_mode:
            self.x_start = event.x
            self.y_start = event.y

    def stop_drag(self, event):
        """Stop dragging the label and save the setup."""
        if event and self.root.change_mode:
            try:
                new_element = {
                    "id": self.gen_id,
                    "x": self.rounded_x,
                    "y": self.rounded_y
                }
                self.db.update(new_element)
                self.logger.message(f"Stopped dragging '{self.cget('text')}' at ({self.rounded_x}, {self.rounded_y})")
            except Exception as e:
                self.logger.message(f"Error updating label position: {e}", log_level="ERROR")


class DataDraggableRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.reverse = 1
        self.data_info = None
        self.low_bit = values["minBit"]
        self.high_bit = values["maxBit"]
        self.low_byte = values["minByte"]
        self.high_byte = values["maxByte"]
        self.init()

    def init(self):
        self.data_info = tk.Label(self, text="")
        self.data_info.place(x=2, y=0)
        if self.low_byte > self.high_byte:
            temp = self.low_byte
            self.low_byte = self.high_byte
            self.high_byte = temp
            self.reverse = -1


class ComPortRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.data = None
        self.first_val = None
        self.main_root = main_root
        self.type = None
        self.port = None
        self.logger = log
        self.checkbox_var = None
        self.checkbox = None
        self.val_list = ["select or set"]
        self.top_frame = None
        self.label = None
        self.combobox = None
        self.button = None
        self.is_started = False
        self.data_list = []
        self.width = values.get('Width', 150)
        self.height = values.get('Height', 100)
        self.init_box(values)

    def init_box(self, values):
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.type = values["Type"]
        # Create a Label
        #self.label = tk.Label(self.top_frame, text=values["label_name"])
        #self.label.pack(side=tk.LEFT, padx=5, pady=5)

        # Retrieve the list from main_root based on the type specified in values
        self.combobox = ttk.Combobox(self.top_frame, values=list(self.val_list))
        self.combobox.pack(side=tk.RIGHT, padx=5, pady=5)
        self.combobox.set(self.val_list[0])

        # Bind the combobox selection event to a callback function
        self.combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        # Create a toggle Button under the combobox
        self.port = DeviceManager(self.logger)
        self.update_combo_com()
        self.button = tk.Button(self.top_frame, text="Start", command=self.on_com_click, font=("Arial", 10))
        com_info = self.db.find_data("com_info", self.gen_id)[0]
        if com_info["last_conn_info"] != "None" and com_info["last_conn_info"] in self.port.find_devices():
            self.port.device_name = com_info["last_conn_info"]
            self.port.baud_rate = int(com_info["baud_rate"])
            self.on_com_click()
            self.combobox.set(self.port.device_name)
        self.button.pack(side=tk.LEFT, padx=5, pady=5)
        self.config(width=self.width, height=self.height)

        # Force the size change by using place geometry manager
        self.place_configure(width=self.width, height=self.height)

    def update_combo_com(self):
        self.val_list = self.port.find_devices()
        self.val_list.insert(0, "select or set")
        self.combobox.config(values=self.val_list)

    def on_combobox_select(self, event):
        """Callback function when a combobox item is selected."""
        if self.type == "com_list":
            self.update_combo_com()
        print(event)
        selected_value = self.combobox.get()
        self.port.device_name = selected_value
        self.logger.message(f"Selected value: {selected_value}")
        # Add any additional functionality you need on selection

    def update_all_data_label(self, packet):
        for data_label in self.data_list:
            data_label.data_info.config(text=packet)

    def on_com_click(self):
        """Callback function when the button is clicked."""

        if self.is_started:
            self.button.config(text="Start", fg="black", font=("Arial", 10))
            self.combobox.config(state="normal")  # Enable the combobox
            self.is_started = False
            self.port.disconnect()
            self.update_all_data_label("")
        else:
            answer = self.port.connect()
            if not answer:
                self.logger.message("Port in use")
                messagebox.showerror("Connection Error!", f"Port in use")
                return False
            self.db.switch_database(f"{self.gui_name}_conf")
            com_info = self.db.find_data("com_info", self.gen_id)[0]
            com_info["last_conn_info"] = self.port.device_name
            self.db.update(com_info)
            self.button.config(text="Stop", fg="red", font=("Arial", 10))
            self.combobox.config(state="disabled")  # Disable the combobox
            self.is_started = True
            # self.update_all_data_label("------")

            process = threading.Thread(target=self.update_data_labels)
            process.start()

        # Send data if type is function
        if self.val_list and callable(self.combobox.get()):
            selected_function = self.combobox.get()
            self.logger.message(f"Button clicked! Current combobox selection: {selected_function}")
            selected_function()  # Call the function
        else:
            selected_value = self.combobox.get()
            self.logger.message(f"Button clicked! Current combobox selection: {selected_value}")
            # Add any additional functionality you need on button click

    def update_data_labels(self, data=None):
        threads = []
        while self.port.device and self.main_root.winfo_exists() and self.data_list:
            time.sleep(0.1)
            self.data = self.port.continuous_read()
            # start = time.time_ns()
            if self.data is None:
                continue
            for data_label in self.data_list:
                if self.data is None:
                    break
                try:
                    threads.append(threading.Thread(target=self._update_data_label, args=(data_label,)))
                    threads[-1].start()
                except Exception as e:
                    pass
            for thread in threads:
                thread.join()
            threads = []
            # stop = time.time_ns()
            # print(f"all thread finished in {stop-start} ns")
            self.data = None

    def _update_data_label(self, data_label):
        time.sleep(0.001)
        list_bytes = [self.data[i] for i in range(len(self.data))]

        data = extract_bits(list_bytes[data_label.low_byte:1+data_label.high_byte:data_label.reverse], data_label.low_bit, data_label.high_bit)
        data_label.data_info.config(text=data)


class ComTransmitRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.data = None
        self.first_val = None
        self.main_root = main_root
        self.type = None
        self.port = None
        self.logger = log
        self.checkbox_var = None
        self.checkbox = None
        self.val_list = {"select or set": "",
                         "RELAY 0&1 OFF": "RELAY, 0&0, 1&0, 10",
                         "RELAY 0&1 ON": "RELAY, 0&1, 1&1, 10"}
        self.top_frame = None
        self.label = None
        self.combobox = None
        self.button = None
        self.is_started = False
        self.uut = None
        self.data_list = []
        self.width = values.get('Width', 150)
        self.height = values.get('Height', 100)
        self.init_box(values, main_root)

    def init_box(self, values, main_root):
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        # self.type = values["Type"]
        # Create a Label
        # self.label = tk.Label(self.top_frame, text=values["label_name"])
        # self.label.pack(side=tk.LEFT, padx=5, pady=5)

        # Retrieve the list from main_root based on the type specified in values
        self.combobox = ttk.Combobox(self.top_frame, values=list(self.val_list.keys()))
        self.combobox.pack(side=tk.LEFT, padx=5, pady=5)
        self.combobox.set(list(self.val_list.keys())[0])

        # Bind the combobox selection event to a callback function
        self.combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        self.button = tk.Button(self, text="Send", command=self.on_fun_click, font=("Arial", 10))
        self.checkbox_var = tk.IntVar()
        self.checkbox = tk.Checkbutton(self, text="AUTO RUN", variable=self.checkbox_var)
        self.checkbox.pack(side=tk.LEFT, padx=5, pady=5)
        self.button.pack(side=tk.TOP, padx=5, pady=5)

        self.config(width=self.width, height=self.height)

        # Force the size change by using place geometry manager
        self.place_configure(width=self.width, height=self.height)

    def update_combo_com(self):
        self.combobox.config(values=self.val_list)

    def on_combobox_select(self, event):
        selected_value = self.combobox.get()
        self.logger.message(f"Selected value: {selected_value}")
        # Add any additional functionality you need on selection

    def on_fun_click(self):
        self.uut.write(self.val_list[self.combobox.get()])

    def update_data_labels(self):
        threads = []
        while self.uut.device and self.main_root.winfo_exists():
            time.sleep(0.1)
            # print("run process")
            self.data = self.uut.query_read()
            # start = time.time_ns()
            for data_label in self.data_list:
                if self.data is None:
                    break
                try:
                    threads.append(threading.Thread(target=self._update_data_label, args=(data_label,)))
                    threads[-1].start()
                except Exception as e:
                    print(e)
                    pass
            for thread in threads:
                thread.join()
            threads = []
            # stop = time.time_ns()
            # print(f"all thread finished in {stop-start} ns")
            self.data = None

    def _update_data_label(self, data_label):
        time.sleep(0.001)



class ButtonTransmitRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""
    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.data = None
        self.first_val = None
        self.main_root = main_root
        self.type = None
        self.port = None
        self.logger = log
        self.checkbox_var = None
        self.checkbox = None
        self.val_list = ["select or set"]
        self.top_frame = None
        self.label = None
        self.combobox = None
        self.button = None
        self.is_started = False
        self.function = None
        self.uut = None
        self.data_list = []
        self.width = values.get('Width', 180)
        self.height = values.get('Height', 100)
        self.init_box(values)

    def init_box(self, values):
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.type = values["Type"]
        self.button = tk.Button(self, text="  ON  ", command=self.on_fun_click, font=("Arial", 10))
        self.button.pack(padx=0, pady=0)
        self.is_started = False  # Default state is 'Off'
        self.config(width=self.width, height=self.height)
        self.place_configure(width=self.width, height=self.height)

    def on_fun_click(self):
        # Toggle state and button text
        if not self.is_started:
            self.button.config(text="  OFF  ")  # Change text to 'Stop'
            self.is_started = True
            self.uut.write(self.element['on_state'])
            print(self.function)
        else:
            self.button.config(text="  ON  ")  # Change text to 'Start'
            self.is_started = False
            self.uut.write(self.element['off_state'])
            print(self.function)

    def _update_data_label(self, data_label):
        time.sleep(0.001)



class SetupLoader:
    def __init__(self, root, database, log, gui_name):
        self.script = None
        self.db = database
        self.root = root
        self.logger_setup = Logger(f'{gui_name}_setup')
        self.logger = log
        self.gui_name = gui_name
        self.elements_dict = {}
        self.created_elements = {}
        self.waiting_list = []
        self.init()

    def init(self):
        num_ids = self.db.get_by_feature("id")
        for num_id in num_ids:
            self.elements_dict[num_id] = self.db.get_info(num_id)
        print(self.elements_dict)
        self.root.title("Project_test ver DD")

    def load_setup(self):
        """Create labels/frames based on the loaded JSON data."""
        self.root.loader.packet = None
        sorted_keys_desc = sorted(self.elements_dict.keys(), reverse=False)
        sorted_dict_desc = {key: self.elements_dict[key] for key in sorted_keys_desc}
        for element in sorted_dict_desc.values():
            print("try_to_create", element)
            self.create_element(element)
            print("created_el", self.created_elements)
        # Process waiting list until it's empty

    def create_info_label(self, frame):
        text_widget = tk.Text(frame, height=10, width=140, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.logger.text_widget = text_widget

    def create_info_scope(self, frame):
        self.scope_name = tk.Label(frame, text="----------------------------")
        self.scope_name.place(x=5, y=5)

    def create_script_label(self, frame):
        ScriptRunnerApp(frame, self.logger, self.db, self.gui_name)

    def create_element(self, element):
        element_id = element.get('id', '')
        parent_id = element.get('parent', 'root')

        if element_id in self.created_elements.keys():
            self.logger_setup.message(f"Element {element_id} already created on Parent - {parent_id}")
            return self.created_elements[element_id]

        if parent_id == 0:
            parent_info = self.root
            # Update the size of the root window to match the element's dimensions
            root_width = int(element.get('Width', 1250))
            root_height = int(element.get('Height', 850))
            self.logger_setup.message(f"Setting root size to - {root_width}x{root_height}")
            self.root.geometry(f"{root_width}x{root_height}")
        else:
            if parent_id not in self.created_elements:
                parent_element = self.elements_dict.get(parent_id)
                if not parent_element:
                    self.logger_setup.message(f"Warning: Parent element with ID {parent_id} not found.")
                    self.db.remove_element(element_id)
                    return None
            parent_info = self.created_elements[parent_id]

        # Create the frame
        frame = self.create_frame(element, parent_info)

        if frame:
            x = element.get('x')
            y = element.get('y')

            if x is None or y is None:
                self.logger_setup.message(f"Warning: {element_id} has no specified coordinates, placing skipped.")
            else:
                x = int(x)
                y = int(y)
                frame.place(x=x, y=y)
                self.logger_setup.message(f"Placed frame {frame} at position ({x},{y})")

            # Store the created element
            self.created_elements[element_id] = frame

        return frame

    def create_frame(self, element, parent_info):
        class_name = element.get('class', '').split(".")[-1]
        self.logger_setup.message(f"Create {class_name})")

        class_str = class_name.strip("<>").replace("class ", "").replace("'", "")
        self.logger_setup.message(f"Class String after cleaning: '{class_str}'")

        if "." in class_str:
            module_name, class_name = class_str.split(".")
        else:
            self.logger_setup.message("Class string does not contain a module name, assuming '__main__'.")
            module_name = "__main__"
            class_name = class_str

        if module_name == "__main__":
            cls = globals().get(class_name)
            if cls is None:
                raise ValueError(f"Class '{class_name}' not found in globals.")
        else:
            try:
                module = __import__(module_name)
                cls = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                raise ImportError(f"Could not import class '{class_name}' from module '{module_name}'.") from e
        frame_id = element.get('id', '')

        frame = cls(main_root=self.root,
                    parent_info=parent_info,
                    values=element,
                    gen_id=element.get('id', ''),
                    log=self.logger)

        try:
            self.db.switch_database(f"{self.gui_name}_conf")
            if "ComPortRightClickMenu" in class_name:
                self.root.comport_list[str(frame_id)] = frame
            elif "ComTransmitRightClickMenu" in class_name or "ButtonTransmitRightClickMenu" in class_name:
                frame.uut = self.root.comport_list[str(element["info_table"])].port
            elif "DataDraggableRightClickMenu" in class_name:
                self.root.comport_list[str(element["info_table"])].data_list.append(frame)
        except Exception as e:
            self.logger.message(f"Can't create element {element}, {e}", "ERROR")
            frame.destroy()
            return None

        if frame_id == 4:
            self.create_info_scope(frame)
        elif frame_id == 3:
            self.create_info_label(frame)
        elif frame_id == 2:
            self.create_script_label(frame)

        return frame


# Example usage
if __name__ == "__main__":
    root_main = tk.Tk()
    root_main.change_mode = False
    root_main.comport_list = {}
    root_main.gui_name = 'OLD'

    try:
        logger = Logger(f"{root_main.gui_name}_logs")
    except:
        init_database(root_main.gui_name)
        logger = Logger(f"{root_main.gui_name}_logs")

    db_gui = Database(f"{root_main.gui_name}_conf", logger)

    root_main.loader = SetupLoader(root_main, db_gui, logger, root_main.gui_name)
    root_main.loader.load_setup()
    db_gui.logger = root_main.loader.logger
    enu_bar = MenuBar(root_main, db_gui, root_main.gui_name)
    # root_main.attributes('-alpha', 0.95)
    root_main.mainloop()
