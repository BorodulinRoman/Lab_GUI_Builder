import tkinter as tk
from tkinter import Menu, messagebox, ttk
from test import InputWindow, round_to_nearest_10, JsonManager
from database import Database

PROJECT = "test.json"


class RightClickMenu(tk.LabelFrame):
    """A label frame that shows a context menu on right-click."""

    def __init__(self, main_root, values, gen_id=1, width=0, height=0, text=None):
        """Initialize the RightClickMenu with a root, parent, label, width, height, and optional text."""
        super().__init__(text=text if text else values["label_name"])  # Pass text or label to the LabelFrame
        self.config(width=int(values['width']), height=int(values['height']))
        self.label_name = None
        self.menu = None
        self.x_start = None
        self.y_start = None

        self.root = main_root  # Reference to the root window
        self.root.com_list = {"COM1": "COM1", "COM4": "COM4"}
        self.root.function = {"Relay1": "FF,AA,DD", "Relay2": "F3,FF,AA", "Relay3": "F6,F0,DA"}
        self.gen_id = gen_id
        self.grid_propagate(False)
        self.db = Database("gui_conf")
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
            if self.gen_id != 1:
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
            print(f"Removed '{temp}'")
        except Exception as e:
            print(f"Error removing label: {e}")

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
        default_values = {'label_name': 'New Widget'}  # Set the default name
        InputWindow(self.root, "Create New Widget",
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values,
                    {"Dimension": ['150x400', '520x400', '820x600', '320x600', '920x200', '260x200']})

    def packet_label(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'label_name': 'New Packet', 'maxByte': 0, 'minByte': 0, 'maxBit': 0, 'minBit': 0}
        InputWindow(self.root, "Create New Widget",
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values,
                    {"Dimension": ['130x40', '300x40', '600x40']})

    def open_combobox(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'label_name': 'New combo'}  # Set the default name
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

            print(f"New widget '{values['label_name']}' created at ({x}, {y})")
        except KeyError as e:
            print(f"Key error in widget settings: {e}")
        except ValueError as e:
            print(f"Value error in widget settings: {e}")

    def confirm_enable_change_mode(self):
        """Confirm with the user before enabling change mode."""
        answer = messagebox.askyesno("Enable Change Mode", "Are you sure you want to enable change mode?")
        if answer:
            self.root.change_mode = True
            print("Change mode enabled")
            self.update_menu()

    def disable_change_mode(self):
        """Disable change mode, save the setup, and update the menu."""
        self.root.change_mode = False
        print("Change mode disabled")
        self.update_menu()

    def update_menu(self):
        """Update the context menu."""
        self.create_menu(self.winfo_rootx(), self.winfo_rooty())  # Recreate menu with the current root position

    def get_info(self):
        """Print the label's information."""
        element_info = self.db.get_info(self.gen_id)
        print(element_info)  # Print the element information
        if element_info:
            print(f"Label id '{self.gen_id}' location: ({self.winfo_x()}, {self.winfo_y()})")
        else:
            print(f"No element found with id: {self.gen_id}")

class DraggableRightClickMenu(RightClickMenu):
    """A label frame that can be dragged and shows a context menu on right-click."""

    def __init__(self, main_root, values, gen_id=1):
        """Initialize the DraggableRightClickMenu with a root, parent, and label."""
        super().__init__(main_root, values, gen_id=gen_id, text=values["label_name"])
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
            print(f"Dragging '{self.cget('text')}' to ({self.rounded_x}, {self.rounded_y})")

    def start_drag(self, event):
        """Start dragging the label."""
        if self.root.change_mode:
            self.x_start = event.x
            self.y_start = event.y

    def stop_drag(self, event):
        """Stop dragging the label and save the setup."""
        if event:
            try:
                new_element = {
                    "id": self.gen_id,
                    "x": self.rounded_x,
                    "y": self.rounded_y
                }
                self.db.update(new_element)
                print(f"Stopped dragging '{self.cget('text')}' at ({self.rounded_x}, {self.rounded_y})")
            except Exception as e:
                print(f"Error updating label position: {e}")


class ComboboxRightClickMenu(DraggableRightClickMenu):
    """A draggable label frame that includes a combobox and a toggle button."""

    def __init__(self, main_root, values, gen_id=1):
        """Initialize the ComboboxRightClickMenu with a root, parent, label, width, and height."""
        super().__init__(main_root, values, gen_id=gen_id)
        self.val_list = None
        self.top_frame = None
        self.label = None
        self.combobox = None
        self.button = None
        self.width = values.get('width', 150)
        self.height = values.get('height', 100)
        self.init_box(values, main_root)
        self.is_started = False

    def init_box(self, values, main_root):
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Create a Label
        self.label = tk.Label(self.top_frame, text=values["label_name"])
        self.label.pack(side=tk.LEFT, padx=5, pady=5)

        # Retrieve the list from main_root based on the type specified in values
        self.val_list = getattr(main_root, values["Type"], {})
        self.combobox = ttk.Combobox(self.top_frame, values=list(self.val_list.keys()))
        self.combobox.pack(side=tk.LEFT, padx=5, pady=5)

        # Bind the combobox selection event to a callback function
        self.combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        # Create a toggle Button under the combobox
        if values["Type"] == "com_list":
            self.button = tk.Button(self, text="Start", command=self.on_com_click, font=("Arial", 10))

        elif values["Type"] == "function":
            self.button = tk.Button(self, text="Send", command=self.on_fun_click, font=("Arial", 10))
        self.button.pack(side=tk.TOP, padx=5, pady=5)

        self.config(width=self.width, height=self.height)

        # Force the size change by using place geometry manager
        self.place_configure(width=self.width, height=self.height)

    def on_combobox_select(self, event):
        """Callback function when a combobox item is selected."""
        selected_value = self.combobox.get()
        print(f"Selected value: {selected_value}")
        # Add any additional functionality you need on selection

    def on_fun_click(self):
        # Send data if type is function
        if self.val_list and callable(self.val_list.get(self.combobox.get())):
            selected_function = self.val_list[self.combobox.get()]
            selected_function()  # Call the function
        else:
            selected_value = self.combobox.get()
            print(f"Button clicked! Current combobox selection: {selected_value}")
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
        if self.val_list and callable(self.val_list.get(self.combobox.get())):
            selected_function = self.val_list[self.combobox.get()]
            selected_function()  # Call the function
        else:
            selected_value = self.combobox.get()
            print(f"Button clicked! Current combobox selection: {selected_value}")
            # Add any additional functionality you need on button click


class SetupLoader:
    def __init__(self, root, database):
        self.root = root
        self.waiting_list = []
        self.db = database

    def load_setup(self):
        """Create labels/frames based on the loaded JSON data."""
        all_ids = self.db.get_by_feature("id")
        for id_num in all_ids:
            fd = self.db.find_data("label_param", id_num)
            self.create_element(fd[0])
        print(all_ids)

    def create_element(self, element):
        print(element)
        element_id = element["id"]
        parent_id = element["parent"]

        if parent_id is None:
            root_width = int(element["width"])
            root_height = int(element["height"])
            self.root.geometry(f"{root_width}x{root_height}")
        frame = self.create_frame(element)

        if frame:
            x = element['x']
            y = element['y']
            frame.place(x=x, y=y)

        return frame

    def create_frame(self, element):
        class_name = element["class"]

        if 'Draggable' in class_name:
            frame = DraggableRightClickMenu(
                main_root=self.root,
                values=element,
                gen_id=element.get('id', ''))
        elif 'Combobox' in class_name:
            frame = ComboboxRightClickMenu(
                main_root=self.root,

                values=element,
                gen_id=element.get('id', ''))
        elif 'RightClickMenu' in class_name:
            frame = RightClickMenu(
                main_root=self.root,
                values=element,
                gen_id=element.get('id', ''))
        else:
            return None
        return frame


# Example usage
if __name__ == "__main__":
    root_main = tk.Tk()
    root_main.change_mode = False
    db = Database("gui_conf")
    root_main.loader = SetupLoader(root_main, db)
    root_main.loader.load_setup()
    root_main.mainloop()