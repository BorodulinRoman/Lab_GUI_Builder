from tkinter import Menu, messagebox
from DeviceManager import DeviceManager, extract_bits, ScopeUSB
from database import Database, Logger, init_loader
from ReportsAndScriptRun import ScriptRunnerApp
from BarLine import *
import tkinter as tk
from PIL import Image, ImageTk
from itertools import cycle
import threading
import time
import random

def round_to_nearest_10(n):
    if n < 0:
        return 0
    """Round the number to the nearest multiple of 10, rounding up on ties."""
    return ((n + 5) // 10) * 10


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
        self.db = Database(f"{self.gui_name}_conf", self.logger)
        self.add_window = AddDataWindow(main_root, database=self.db, gui_name=self.gui_name)
        self.root = main_root  # Reference to the root window
        self.visaDevices = DeviceManager(logger=self.logger)
        self.root.com_list = self.visaDevices.find_devices()
        self.gen_id = gen_id
        self.parent_info = parent_info
        self.config(width=width, height=height, bg=parent_info['bg'])  # Match parent's background
        self.grid_propagate(False)

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
            if 'DataDraggableRightClickMenu' in self.element["class"]:
                self.menu.add_command(label='Add State', command=self.state_builder_for_data)
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Disable Change Mode', command=self.disable_change_mode)
            if self.gen_id not in [0, 1, 2, 3, 4]:
                self.menu.add_command(label='Remove', command=self.del_label)
            if self.gen_id not in [0, 2, 3, 4]:
                self.menu.add_command(label='Update', command=self.update_object)
            if self.gen_id not in [2, 3, 4] and self.element['Type'] is None:
                self.menu.add_cascade(label='New', menu=self.build_menu(x, y))  # Add the submenu to the main menu
            if 'ComTransmitRightClickMenu' in self.element["class"]:
                self.menu.add_command(label='Add Functions', command=self.add_functions)
        else:
            if self.gen_id == 4:
                self.menu.add_command(label='Add Scope', command=self.add_scope)
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Enable Change Mode', command=self.confirm_enable_change_mode)

    def update_object(self):
        self.add_window.open_new_window(labels=self.element, name="Update Object", callback=self._update_element)

    def _update_element(self, info):
        self.db.update(info)
        self.destroy()
        frame = self.root.loader.create_frame(info, self.parent_info)
        frame.place(x=info["x"], y=info["y"])

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
        boxs = [{"Dimension": ['250x400', '520x400', '900x400', '300x600', '900x200', '250x200']}]
        self.add_window.open_new_window(label, boxs, "Create New Widget",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls))

    def add_functions(self):
        self.add_window.open_new_window(labels={"id": self.element["id"]}, name="Add Functions", add_functions=True,
                                        callback=lambda values: self._function(values))

    def state_builder_for_data(self):
        self.add_window.open_new_window(labels={"id": self.element["id"]}, name="Add State", add_functions=True,
                                        callback=lambda values: self._function(values))

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
        label = {'label_name': 'New Packet',
                 "factor": 1, "sign": 0,
                 'maxByte': 0, 'minByte': 0,
                 'maxBit': 0, 'minBit': 0}
        boxs = [{"Dimension": ['130x40', '300x40', '600x40'],
                 'info_table': list(dic_ids.keys()),
                 "type_number": {"HEX", "DEC", "BIN"}}]

        self.add_window.open_new_window(label, boxs, "Create New Widget",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids))

    def open_com_box(self, x, y, cls):
        label = {'label_name': 'New combo', "last_conn_info": None, "baud_rate": "115200", "frame_rate": "0.005",
                 "start_byte": '0', "packet_size": 36, "header": ""}
        boxs = [{"Dimension": ['220x70']}]
        self.add_window.open_new_window(label, boxs, "Create New Com Communication",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls))

    def open_transmit_box(self, x, y, cls):
        dic_ids = self.get_coms_data()
        label = {'label_name': 'New combo', "last_conn_info": None, "func": None}
        boxs = [{"Dimension": ['160x100', '260x100', '600x100'], 'info_table': list(dic_ids.keys())}]
        self.add_window.open_new_window(label, boxs, "Create New Com transmit box",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids),
                                        add_functions=True)

    def open_button(self, x, y, cls):
        dic_ids = self.get_coms_data()
        label = {'label_name': 'New combo', "on_state": "", "off_state": ""}
        boxs = [{'info_table': list(dic_ids.keys()), "Dimension": ['50x60', '70x60', '90x60']}]
        self.add_window.open_new_window(label, boxs, "Create New Button transmit box",
                                        lambda values: self.create_new_widget_with_settings(values, x, y, cls, dic_ids))

    def _function(self,  values, functions=None):
        if functions is None:
            functions = {}
            if "function_name" and "function_info" in values.keys():
                print(values)
                for i, val in enumerate(values["function_name"]):

                    functions[val] = values["function_info"][i]
                del values["function_name"]
                del values["function_info"]

        if functions:
            self.db.switch_database(f"{self.gui_name}_conf")
            for func_name, func_data in functions.items():
                self.db.add_element({"id": values["id"],
                                     "function_name": func_name,
                                     "function_info": func_data})

    def create_new_widget_with_settings(self, values, x, y, cls, dict_ids=None):
        com_id = 0
        functions = {}
        if dict_ids is not None:
            for key, val in values.items():
                try:
                    if val in dict_ids:
                        values[key] = dict_ids[val]
                        com_id = dict_ids[val]
                except:
                    pass
        try:
            if "type_number" in values.keys():
                if values["type_number"].upper() not in ["HEX", "BIN", "DEC"]:
                    values["type_number"] = "HEX"
            if "function_name" and "function_info" in values.keys():
                for i, val in enumerate(values["function_name"]):
                    functions[val] = values["function_info"][i]
                del values["function_name"]
                del values["function_info"]
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
            self._function(values,functions)
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
        self.logger.message(self.element)  # Print the element information
        if self.element:
            self.logger.message(f"Label id '{self.gen_id}' location: ({self.winfo_x()}, {self.winfo_y()})")
        else:
            self.logger.message(f"No element found with id: {self.gen_id}")


class DraggableRightClickMenu(RightClickMenu):
    """A label frame that can be dragged and resized, and shows a context menu on right-click."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        """Initialize the DraggableRightClickMenu with a root, parent, and label."""
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id, text=values["label_name"])

        self.label_name = values["label_name"]
        self.rounded_x = values['x']
        self.rounded_y = values['y']

        # Variables for moving and resizing
        self.resizing = False
        self.moving = False
        self.start_x = None
        self.start_y = None
        self.start_width = None
        self.start_height = None

        # Bind mouse events
        self.bind("<Button-1>", self.start_action)
        self.bind("<B1-Motion>", self.on_action)
        self.bind("<ButtonRelease-1>", self.stop_action)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def on_enter(self, event):
        """Change cursor when entering the widget."""
        if self.root.change_mode:
            self.config(cursor="arrow")

    def on_leave(self, event):
        """Reset cursor when leaving the widget."""
        if self.root.change_mode:
            self.config(cursor="")

    def start_action(self, event):
        """Determine whether to start moving or resizing."""
        if self.root.change_mode:
            self.start_x = event.x
            self.start_y = event.y
            self.start_width = self.winfo_width()
            self.start_height = self.winfo_height()

            border = 10  # Edge detection for resizing

            # Check if near the bottom-right corner for resizing
            if self.start_x >= self.start_width - border and self.start_y >= self.start_height - border:
                self.resizing = True
                self.config(cursor="size_nw_se")
            else:
                # Else, enable moving
                self.moving = True
                self.config(cursor="fleur")  # Move cursor

    def on_action(self, event):
        """Handle moving or resizing during mouse motion."""
        if self.root.change_mode:
            if self.resizing:
                # Calculate new size
                new_width = self.start_width + (event.x - self.start_x)
                new_height = self.start_height + (event.y - self.start_y)

                # Set minimum size limits
                min_width = 50
                min_height = 20
                new_width = max(new_width, min_width)
                new_height = max(new_height, min_height)

                # Round sizes to nearest 10
                new_width = round_to_nearest_10(new_width)
                new_height = round_to_nearest_10(new_height)

                # Apply new size
                if new_height is None or new_width is None:
                    return None
                self.place_configure(width=new_width, height=new_height)
                self.logger.message(f"Resizing '{self.cget('text')}' to ({new_width}, {new_height})")
            elif self.moving:
                # Calculate new position
                x = self.winfo_x() - self.start_x + event.x
                y = self.winfo_y() - self.start_y + event.y

                # Round positions to nearest 10
                self.rounded_x = round_to_nearest_10(x)
                self.rounded_y = round_to_nearest_10(y)

                # Apply new position
                self.place(x=self.rounded_x, y=self.rounded_y)
                self.logger.message(message=f"Dragging '{self.cget('text')}' to ({self.rounded_x}, {self.rounded_y})",
                                    update_info_desk=False)

    def stop_action(self, event):
        """Reset states and update the database after moving or resizing."""
        if self.root.change_mode:
            try:
                new_element = {
                    "id": self.gen_id,
                }
                if self.resizing:
                    new_element["Width"] = self.winfo_width()
                    new_element["Height"] = self.winfo_height()
                    self.logger.message(
                        f"Stopped resizing '{self.cget('text')}' at size ({self.winfo_width()}, {self.winfo_height()})"
                    )
                if self.moving:
                    new_element["x"] = self.rounded_x
                    new_element["y"] = self.rounded_y
                    self.logger.message(
                        f"Stopped dragging '{self.cget('text')}' at ({self.rounded_x}, {self.rounded_y})"
                    )
                self.db.update(new_element)
            except Exception as e:
                self.logger.message(f"Error updating label position/size: {e}", log_level="ERROR")
            finally:
                # Reset states and cursor
                self.resizing = False
                self.moving = False
                self.config(cursor="arrow")


class DataDraggableRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.data_info = None
        self.reverse = 1
        self.text_var = tk.StringVar()  # Create a StringVar to manage the label's text
        self.low_bit = values["minBit"]
        self.high_bit = values["maxBit"]
        self.low_byte = values["minByte"]
        self.high_byte = values["maxByte"]
        self.sign = values["sign"]
        self.factor = values["factor"]
        self.type = values["type_number"]
        self.functions = self.db.find_data('transmit_com', int(values["id"]))
        self.convert_text = {}
        self.init()

    def init(self):
        self.data_info = tk.Label(self, textvariable=self.text_var)
        self.data_info.place(x=2, y=0)

        try:
            self.db.switch_database(f"{self.gui_name}_conf")
            for data in self.functions:
                self.convert_text[data["function_info"]] = data["function_name"]
            self.element['convert_data'] = self.convert_text

        except Exception as e:
            pass
        # Correct byte ordering if low_byte > high_byte
        if self.low_byte > self.high_byte:
            self.low_byte, self.high_byte = self.high_byte, self.low_byte
            self.reverse = -1


class ComPortRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, log, gen_id="0000"):
        super().__init__(main_root, parent_info, values, log, gen_id=gen_id)
        self.update_flag = False
        self.frame_rate = None
        self.threads = []
        self.data = None
        self.first_val = None
        self.main_root = main_root
        self.type = None
        self.logger = log
        self.port = DeviceManager(self.logger)
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

        # Retrieve the list from main_root based on the type specified in values
        self.combobox = ttk.Combobox(self.top_frame, values=list(self.val_list))
        self.combobox.pack(side=tk.RIGHT, padx=5, pady=5)
        self.combobox.set(self.val_list[0])

        # Bind the combobox selection event to a callback function
        self.combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        # Create a toggle Button under the combobox
        self.update_combo_com()
        self.button = tk.Button(self.top_frame, text="Start", command=self.on_com_click, font=("Arial", 10))

        com_info = self.db.find_data("com_info", self.gen_id)[0]
        self.port.start_byte = int(com_info["start_byte"])
        self.port.packet_size = int(com_info["packet_size"])
        self.port.header = com_info["header"]

        self.port.device_name = com_info["last_conn_info"]
        self.port.baud_rate = int(com_info["baud_rate"])
        self.frame_rate = float(com_info["frame_rate"])
        self.port.timeout = int(self.frame_rate * 1000)

        if com_info["last_conn_info"] != "None" and com_info["last_conn_info"] in self.port.find_devices():
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
        selected_value = self.combobox.get()
        self.port.device_name = selected_value
        self.logger.message(f"Selected value: {selected_value}")
        # Add any additional functionality you need on selection


    def on_com_click(self):
        """Callback function when the button is clicked."""

        if self.is_started:
            self.button.config(text="Start", fg="black", font=("Arial", 10))
            self.combobox.config(state="normal")  # Enable the combobox
            self.is_started = False
            self.port.disconnect()
        else:
            answer = self.port.connect()
            if not answer:
                self.logger.message("Port in use")
                messagebox.showerror("Connection Error!", f"Port in use")
                return False
            self.is_started = True
            process = threading.Thread(target=self.update_data_labels)
            process.start()

            self.db.switch_database(f"{self.gui_name}_conf")
            com_info = self.db.find_data("com_info", self.gen_id)[0]
            com_info["last_conn_info"] = self.port.device_name
            self.db.update(com_info)
            self.button.config(text="Stop", fg="red", font=("Arial", 10))
            self.combobox.config(state="disabled")  # Disable the combobox

            # self.update_all_data_label("------")


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
        time.sleep(1)
        while self.is_started and self.main_root.running and self.data_list:
            try:
                self.data = self.port.continuous_read()
                if self.data is None:
                    time.sleep(self.frame_rate*2)
                    continue
                self.root.script_runner.response = self.data
                self._update_data_labels()

            except Exception as e:
                pass
        return 0

    def _update_data_labels(self):
        threads = []
        for data_label in self.data_list:
            self._update_label(label=data_label)

    def _update_label(self, label: DataDraggableRightClickMenu):
        try:
            if self.update_flag:
                time.sleep(self.frame_rate)
                return None
            self.update_flag = True
            list_bytes = self.data[label.low_byte:1 + label.high_byte]
            if label.reverse < 0:
                list_bytes = list_bytes[::-1]
            data = extract_bits(list_bytes, label.low_bit, label.high_bit, label.type)
            # Update only if data has changed to reduce redundant updates

            if label.sign and label.type == 'DEC':
                bit_length = label.high_bit - label.low_bit
                data = int(data)
                if data >= 1 << (bit_length - 1):
                    data -= 1 << bit_length
                data = data * label.factor

            if data in label.convert_text.keys():
                data = label.convert_text[data]

            if label.text_var.get() != data:
                label.text_var.set(data)
            self.update_flag = False
            return "Done"
        except Exception as e:
            pass
        print("_update_label Done")


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
        self.val_list = {}
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
        self.db.switch_database(f"{self.gui_name}_conf")
        try:
            functions = self.db.find_data('transmit_com', int(values["id"]))
            self.element['function_name'] = []
            self.element['function_info'] = []
            for data in functions:
                self.val_list[data["function_name"]] = data["function_info"]
                self.element['function_name'].append(data["function_name"])
                self.element['function_info'].append(data["function_info"])
        except:
            pass
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

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
        else:
            self.button.config(text="  ON  ")  # Change text to 'Start'
            self.is_started = False
            self.uut.write(self.element['off_state'])


class SetupLoader:
    def __init__(self, root, database, log, gui_name):
        self.scope_name = None
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

    def load_setup(self):
        """Create labels/frames based on the loaded JSON data."""
        self.root.loader.packet = None
        sorted_keys_desc = sorted(self.elements_dict.keys(), reverse=False)
        sorted_dict_desc = {key: self.elements_dict[key] for key in sorted_keys_desc}
        for element in sorted_dict_desc.values():
            self.create_element(element)
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
        self.root.script_runner = ScriptRunnerApp(frame, self.logger, self.db, self.gui_name,self.root.ver)

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
            center_window(self.root, root_width, root_height)
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

# Assuming these classes and functions are defined elsewhere in your code:
# from your_module import Database, init_loader, Logger, MenuBar, SetupLoader

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

def rotate_loading_circle(canvas, angle_iter):
    angle = next(angle_iter)
    canvas.delete("loading_arc")
    canvas.create_arc(
        150, 100, 250, 200,
        start=angle, extent=270,
        style=tk.ARC, width=4, outline="white",
        tags="loading_arc"
    )
    canvas.after(100, rotate_loading_circle, canvas, angle_iter)

def main_ell_gui(root_main):
    """Create a loading window with a rotating loader.
       DO NOT call mainloop() here. Just return the loading_window."""
    loading_window = tk.Toplevel(root_main)
    loading_window.title("Loading...")
    loading_window.attributes("-alpha", 0.8)
    center_window(loading_window, 400, 300)
    loading_window.overrideredirect(True)

    # Load your logo image
    logo_image = Image.open(f"info/loader_png/MEL_GUI_{random.randint(1, 9)}.png").resize((400, 300), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_image)

    canvas = tk.Canvas(loading_window, width=400, height=300, highlightthickness=0)
    canvas.create_image(0, 0, image=logo_photo, anchor=tk.NW)
    # Keep a reference so the image isn't garbage collected
    loading_window.logo_photo = logo_photo

    # Start the rotating animation
    angle_iter = cycle(range(0, 360, 10))
    rotate_loading_circle(canvas, angle_iter)
    canvas.pack()

    return loading_window


def lab_runner(gui_name=None, root_main=None):
    def on_close():
        root_main.running = False
        root_main.logger.logger_running = False
        for _, port in root_main.comport_list.items():
            try:
                port.is_started = True
                port.on_com_click()
                port.port.disconnect()
                root_main.update_idletasks()  # Process all pending events
                root_main.update()
            except:
                pass

        time.sleep(0.5)
        root_main.destroy()
    try:
        on_close()
    except:
        pass
    # Create the main Tk window

    root_main = tk.Tk()
    root_main.withdraw()  # Hide main window until loading is done

    # Show the loading screen
    loading_window = main_ell_gui(root_main)

    # Background task to do initialization
    def initialization_task():
        # Simulate some setup time
        time.sleep(5)

        # Set up main application values
        root_main.ver = '1.5'
        root_main.running = True
        root_main.change_mode = False
        root_main.comport_list = {}
        root_main.protocol("WM_DELETE_WINDOW", lambda: on_close())

        # Attempt loading settings from DB
        try:
            loader_db = Database('loader_info')
            init_loader(loader_db.find_data(table_name='main_gui')[0]['last_gui'])
        except:
            init_loader()
            loader_db = Database('loader_info')

        if gui_name is None:
            root_main.gui_name = loader_db.find_data(table_name='main_gui')[0]['last_gui']
        else:
            root_main.gui_name = gui_name

        root_main.title(f"Project {root_main.gui_name} ver {root_main.ver}")
        root_main.logger = Logger(f"{root_main.gui_name}_logs")
        db_gui = Database(f"{root_main.gui_name}_conf", root_main.logger)

        root_main.loader = SetupLoader(root_main, db_gui, root_main.logger, root_main.gui_name)
        root_main.loader.load_setup()
        db_gui.logger = root_main.loader.logger
        MenuBar(root_main, db_gui, root_main.gui_name)

        # Once done, destroy loading window and show main window
        # All UI updates must happen in the main thread using `root_main.after()`
        def finish_loading():
            # Destroy loading screen
            loading_window.destroy()
            # Show main window
            root_main.deiconify()

        root_main.after(0, finish_loading)

    # Start initialization in a background thread
    init_thread = threading.Thread(target=initialization_task)
    init_thread.start()

    # Start the main event loop
    root_main.mainloop()

