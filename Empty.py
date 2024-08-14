import tkinter as tk
from tkinter import Menu, messagebox, ttk
from test import InputWindow, round_to_nearest_10, JsonManager
import os
import threading
from datetime import datetime
from queue import Queue
from DeviceManager import VisaDeviceManager
import time
PROJECT = "test.json"


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
            print(self.text_widget)
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


class RightClickMenu(tk.LabelFrame):
    """A label frame that shows a context menu on right-click."""

    def __init__(self, main_root, parent_info, values, logger, gen_id="0000", width=0, height=0, text=None):
        """Initialize the RightClickMenu with a root, parent, label, width, height, and optional text."""
        self.logger = logger
        super().__init__(parent_info, text=text if text else values["Name"])  # Pass text or label to the LabelFrame
        self.config(width=int(values['Width']), height=int(values['Height']))
        self.label_name = None
        self.menu = None
        self.x_start = None
        self.y_start = None
        self.root = main_root  # Reference to the root window
        self.visaDevices = VisaDeviceManager(logger=self.logger)
        self.root.com_list = self.visaDevices.find_devices()
        self.root.function = {"Relay1": "FF,AA,DD", "Relay2": "F3,FF,AA", "Relay3": "F6,F0,DA"}
        self.gen_id = gen_id
        self.parent_info = parent_info
        self.config(width=width, height=height, bg=parent_info['bg'])  # Match parent's background
        self.grid_propagate(False)
        self.db = JsonManager(PROJECT)
        self.bind("<Button-3>", self.show_menu)

    def show_menu(self, event):
        """Show the context menu at the event's location."""
        self.create_menu(event.x_root, event.y_root)  # Pass click location
        self.menu.tk_popup(event.x_root, event.y_root)

    def create_menu(self, x, y):
        """Create the context menu based on the current state."""
        self.menu = Menu(self, tearoff=0)
        if self.root.change_mode:
            self.menu.add_command(label='Disable Change Mode', command=self.disable_change_mode)
            if self.gen_id != "0000":
                self.menu.add_command(label='Remove', command=self.del_label)
            self.menu.add_cascade(label='New', menu=self.build_menu(x, y))  # Add the submenu to the main menu
        else:
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Enable Change Mode', command=self.confirm_enable_change_mode)

    def del_label(self):
        """Delete the label and save the setup."""
        try:
            temp = self.db.remove_element(self.gen_id)
            self.destroy()  # This destroys the widget
            self.logger.message(f"Removed '{temp}'")
        except Exception as e:
            self.logger.message(f"Error removing label: {e}")

    def build_menu(self, x, y):
        """Build the submenu for creating new widgets."""
        drag_rcm = DraggableRightClickMenu
        comb_rcm = ComboboxRightClickMenu
        create_menu = Menu(self.menu, tearoff=0)  # Create a new submenu
        create_menu.add_command(label='Data Label', command=lambda: self.packet_label(x, y, drag_rcm))
        create_menu.add_command(label='Label', command=lambda: self.open_creation_window(x, y, drag_rcm))
        create_menu.add_command(label='Combobox', command=lambda: self.open_combobox(x, y, comb_rcm))
        create_menu.add_command(label='Button', command=lambda: self.open_creation_window(x, y, drag_rcm))
        create_menu.add_command(label='Entry window', command=lambda: self.open_creation_window(x, y, drag_rcm))
        return create_menu

    def open_creation_window(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'Name': 'New Widget'}  # Set the default name
        InputWindow(self.root, "Create New Widget",
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values,
                    {"Dimension": ['150x400', '520x400', '820x600', '320x600', '920x200', '260x200']})

    def packet_label(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'Name': 'New Packet', 'maxByte': 0, 'minByte': 0, 'maxBit': 0, 'minBit': 0}
        InputWindow(self.root, "Create New Widget",
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values,
                    {"Dimension": ['130x40', '300x40', '600x40']})

    def open_combobox(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'Name': 'New combo'}  # Set the default name
        InputWindow(self.root, "Create New Widget",
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values,
                    {"Dimension": ['160x100', '300x100', '600x100'], "Type": ["com_list", "function"]})

    def create_new_widget_with_settings(self, values, x, y, cls):
        """Creates a new widget with the specified settings."""
        try:
            values["x"] = round_to_nearest_10(x - self.winfo_rootx())
            values["y"] = round_to_nearest_10(y - self.winfo_rooty())
            values["parent"] = self.gen_id
            values["class"] = str(cls)
            values["id"] = self.db.add_element(values)
            frame = self.root.loader.create_frame(values, self)
            frame.place(x=values["x"], y=values["y"])




            self.logger.message(f"New widget '{values['Name']}' created at ({x}, {y})")
        except KeyError as e:
            self.logger.message(f"Key error in widget settings: {e}")
        except ValueError as e:
            self.logger.message(f"Value error in widget settings: {e}")

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

    def __init__(self, main_root, parent_info, values, logger, gen_id="0000"):
        """Initialize the DraggableRightClickMenu with a root, parent, and label."""
        super().__init__(main_root, parent_info, values, logger,  gen_id=gen_id, text=values["Name"])
        self.logger = logger
        self.label_name = values["Name"]
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
                self.logger.message(f"Error updating label position: {e}")


class ComboboxRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, parent_info, values, logger, gen_id="0000"):
        """Initialize the ComboboxRightClickMenu with a root, parent, label, width, and height."""
        super().__init__(main_root, parent_info, values, logger, gen_id=gen_id)
        self.logger = logger
        self.checkbox_var = None
        self.checkbox = None
        self.val_list = None
        self.top_frame = None
        self.label = None
        self.combobox = None
        self.button = None
        self.width = values.get('Width', 150)
        self.height = values.get('Height', 100)
        self.init_box(values, main_root)
        self.is_started = False

    def init_box(self, values, main_root):
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Create a Label
        self.label = tk.Label(self.top_frame, text=values["Name"])
        self.label.pack(side=tk.LEFT, padx=5, pady=5)

        # Retrieve the list from main_root based on the type specified in values
        self.val_list = getattr(main_root, values["Type"], {})
        self.combobox = ttk.Combobox(self.top_frame, values=list(self.val_list))
        self.combobox.pack(side=tk.LEFT, padx=5, pady=5)

        # Bind the combobox selection event to a callback function
        self.combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        # Create a toggle Button under the combobox
        if values["Type"] == "com_list":
            self.button = tk.Button(self, text="Start", command=self.on_com_click, font=("Arial", 10))
        elif values["Type"] == "function":
            self.button = tk.Button(self, text="Send", command=self.on_fun_click, font=("Arial", 10))
            self.checkbox_var = tk.IntVar()
            self.checkbox = tk.Checkbutton(self, text="AUTO RUN", variable=self.checkbox_var)
            self.checkbox.pack(side=tk.LEFT, padx=5, pady=5)
        self.button.pack(side=tk.TOP, padx=5, pady=5)

        self.config(width=self.width, height=self.height)

        # Force the size change by using place geometry manager
        self.place_configure(width=self.width, height=self.height)

    def on_combobox_select(self, event):
        """Callback function when a combobox item is selected."""
        print(event)
        selected_value = self.combobox.get()
        self.logger.message(f"Selected value: {selected_value}")
        # Add any additional functionality you need on selection

    def on_fun_click(self):
        # Send data if type is function
        auto_run = self.checkbox_var.get()
        self.logger.message(rf" check box is {auto_run}")
        if self.val_list and callable(self.val_list.get(self.combobox.get())):
            selected_function = self.val_list[self.combobox.get()]
            selected_function()  # Call the function
        else:
            selected_value = self.combobox.get()
            self.logger.message(f"Button clicked! Current combobox selection: {selected_value}")
            # Add any additional functionality you need on button click

    def on_com_click(self):
        """Callback function when the button is clicked."""
        if self.is_started:
            self.button.config(text="Start", fg="black", font=("Arial", 10))
            self.combobox.config(state="normal")  # Enable the combobox
            self.is_started = False
        else:
            self.button.config(text="Stop", fg="red", font=("Arial", 10))
            self.combobox.config(state="disabled")  # Disable the combobox
            self.is_started = True

        # Send data if type is function
        if self.val_list and callable(self.combobox.get()):
            selected_function = self.combobox.get()
            self.logger.message(f"Button clicked! Current combobox selection: {selected_function}")
            selected_function()  # Call the function
        else:
            selected_value = self.combobox.get()
            self.logger.message(f"Button clicked! Current combobox selection: {selected_value}")
            # Add any additional functionality you need on button click


class SetupLoader:
    def __init__(self, root, json_manager):
        self.root = root
        self.logger_setup = Logger("setup")
        self.logger = Logger()
        self.json_manager = json_manager
        self.elements_dict = {element['id']: element for element in self.json_manager.get_elements()}
        self.created_elements = {}
        self.waiting_list = []

    def load_setup(self):
        """Create labels/frames based on the loaded JSON data."""
        for element in self.elements_dict.values():
            self.create_element(element)

        # Process waiting list until it's empty
        while self.waiting_list:
            waiting_list_copy = self.waiting_list.copy()
            self.waiting_list.clear()
            for element in waiting_list_copy:
                self.create_element(element)

        # Remove any elements that are still waiting for a parent
        for element in self.waiting_list:
            self.json_manager.remove_element(element['id'])

    def create_info_label(self, frame):
        text_widget = tk.Text(frame, height=10, width=108, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.logger.text_widget = text_widget

    def create_element(self, element):
        element_id = element.get('id', '')
        parent_id = element.get('parent', 'root')

        if element_id in self.created_elements:
            self.logger_setup.message(f"Element {element_id} already created on Parent - {parent_id}")
            return self.created_elements[element_id]

        if parent_id == 'root':
            parent_info = self.root
            # Update the size of the root window to match the element's dimensions
            root_width = 1215
            root_height = 820
            self.logger_setup.message(f"Setting root size to - {root_width}x{root_height}")
            self.root.geometry(f"{root_width}x{root_height}")
        else:
            if parent_id not in self.created_elements:
                parent_element = self.elements_dict.get(parent_id)
                if parent_element:
                    self.logger_setup.message(
                        f"Parent element {parent_id} not yet created, adding {element_id} to waiting list")
                    self.waiting_list.append(element)
                    return None
                else:
                    self.logger_setup.message(f"Warning: Parent element with ID {parent_id} not found.")
                    return None
            parent_info = self.created_elements[parent_id]

        # Create the frame
        frame = self.create_frame(element, parent_info)

        if frame:
            x = element.get('x')
            y = element.get('y')

            if x is None or y is None:
                self.logger_setup.message(f"Warning: Element {element_id} has no specified coordinates, placing skipped.")
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
                    logger=self.logger)
        if frame_id == "info":
            self.create_info_label(frame)
        return frame


# Example usage
if __name__ == "__main__":
    root_main = tk.Tk()
    root_main.change_mode = False
    jm = JsonManager("test.json")
    root_main.loader = SetupLoader(root_main, jm)
    root_main.loader.load_setup()
    root_main.mainloop()
