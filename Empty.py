import tkinter as tk
from tkinter import Menu, messagebox
from test import InputWindow, round_to_nearest_10, JsonManager

PROJECT = "test.json"


class RightClickMenu(tk.LabelFrame):
    """A label frame that shows a context menu on right-click."""

    def __init__(self, main_root, parent_info, label, gen_id="0000", width=100, height=30, text=None):
        """Initialize the RightClickMenu with a root, parent, label, width, height, and optional text."""
        super().__init__(parent_info, text=text if text else label)  # Pass text or label to the LabelFrame

        self.label_name = None
        self.menu = None
        self.x_start = None
        self.y_start = None
        self.root = main_root  # Reference to the root window
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
            self.menu.add_command(label='Remove', command=lambda: self.del_label())
            self.menu.add_cascade(label='New', menu=self.build_menu(x, y))  # Add the submenu to the main menu
        else:
            self.menu.add_command(label='Info', command=self.get_info)
            self.menu.add_command(label='Enable Change Mode', command=self.confirm_enable_change_mode)

    def del_label(self):
        temp = self.db.remove_element(self.gen_id)
        """Delete the label and save the setup."""
        self.destroy()  # This destroys the widget
        print(f"Removed '{temp}'")

    def build_menu(self, x, y):
        cls = DraggableRightClickMenu
        create_menu = Menu(self.menu, tearoff=0)  # Create a new submenu
        create_menu.add_command(label='Label', command=lambda: self.open_creation_window(x, y, cls))
        create_menu.add_command(label='Combobox', command=lambda: self.open_creation_window(x, y, cls))
        create_menu.add_command(label='Button', command=lambda: self.open_creation_window(x, y, cls))
        create_menu.add_command(label='Entry window', command=lambda: self.open_creation_window(x, y, cls))
        return create_menu

    def open_creation_window(self, x, y, cls):
        """Opens the InputWindow for user to input settings and create a new widget."""
        default_values = {'Name': 'New Widget'}  # Set the default name
        InputWindow(self.root, "Create New Widget", ['Name'],
                    lambda values: self.create_new_widget_with_settings(values, x, y, cls), default_values)

    def create_new_widget_with_settings(self, values, x, y, cls):
        """Creates a new widget with the specified settings."""
        x = round_to_nearest_10(x - self.winfo_rootx()),
        y = round_to_nearest_10(y - self.winfo_rooty()),

        new_element = {"text": values['Name'],
                       "x": x[0], "y": y[0],
                       'width': values['Width'], 'height': values['Height'],
                       "parent":  self.gen_id, "class": str(cls)}

        gen_id = self.db.add_element(new_element)
        new_widget = cls(self.root, self, values['Name'], gen_id)  # Corrected line
        new_widget.place(x=x, y=y)
        new_widget.config(width=int(values['Width']), height=int(values['Height']))
        print(f"New widget '{values['Name']}' created at ({x}, {y})")

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
        self.db.get_info(self.gen_id)
        print(self.db.element_data)
        print(f"Label id '{self.gen_id}' location: ({self.winfo_x()}, {self.winfo_y()})")


class DraggableRightClickMenu(RightClickMenu):
    def __init__(self, main_root, parent_info, label, gen_id="0000"):
        """Initialize the DraggableRightClickMenu with a root, parent, and label."""
        super().__init__(main_root, parent_info, label, gen_id=gen_id, text=label)
        self.label_name = label
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
            new_element = {"id": self.gen_id,
                           "x": self.rounded_x,
                           "y": self.rounded_y}
            self.db.update(new_element)


def load_setup(json_manager, root):
    """Create labels/frames based on the loaded JSON data."""
    elements_dict = {element['id']: element for element in json_manager.get_elements()}
    created_elements = {}

    def create_element(element):
        element_id = element.get('id', '')
        parent_id = element.get('parent', 'root')

        if element_id in created_elements:
            return created_elements[element_id]

        if parent_id == 'root':
            parent_info = root
            # Update the size of the root window to match the element's dimensions
            root_width = int(element.get('width', 100))
            root_height = int(element.get('height', 100))
            root.geometry(f"{root_width}x{root_height}")
        else:
            if parent_id not in created_elements:
                parent_element = elements_dict[parent_id]
                created_elements[parent_id] = create_element(parent_element)
            parent_info = created_elements[parent_id]

        class_name = element.get('class', '')
        if 'RightClickMenu' in class_name:
            frame = RightClickMenu(
                main_root=root,
                parent_info=parent_info,
                label=element.get('text', ''),
                gen_id=element.get('id', '')
            )
        elif 'DraggableRightClickMenu' in class_name:
            frame = DraggableRightClickMenu(
                main_root=root,
                parent_info=parent_info,
                label=element.get('text', ''),
                gen_id=element.get('id', '')
            )
        else:
            return None

        # Retrieve position and size from the JSON element
        x = element.get('x', [0])
        y = element.get('y', [0])
        width = int(element.get('width', 100))
        height = int(element.get('height', 100))
        frame.place(x=x, y=y, width=width, height=height)
        frame.config(width=width, height=height)

        created_elements[element_id] = frame
        return frame

    for element in json_manager.get_elements():
        create_element(element)


# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    root.change_mode = False
    json_manager = JsonManager("test.json")
    load_setup(json_manager, root)
    root.mainloop()
