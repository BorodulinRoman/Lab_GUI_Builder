import tkinter as tk
from tkinter import messagebox, ttk
import json
import random

def round_to_nearest_10(n):
    if n < 0:
        return 0
    """Round the number to the nearest multiple of 10, rounding up on ties."""
    return ((n + 5) // 10) * 10


class InputWindow:
    """A window for getting input from the user with a dimension combobox."""

    def __init__(self, main_root, title, fields, callback, default_values=None):
        """Initialize the InputWindow with a root, title, fields, callback, and default values."""
        self.root = main_root
        self.window = tk.Toplevel(self.root)
        self.window.title(title)
        self.fields = fields
        self.entries = {}
        self.callback = callback
        self.default_values = default_values if default_values else {}
        self.init()

    def init(self):
        """Initialize the input window layout."""
        height = 30 + len(self.fields) * 30 + 30  # Adjust height for combobox
        width = 300  # Define a minimum width for the window
        self.window.geometry(f"{width}x{height}")
        self.window.grid_columnconfigure(1, weight=1)  # Make column 1 expandable

        # Combobox for selecting dimensions
        dimension_options = ['130x40', '300x40', '300x600', '400x300', '400x100', '500x40',  '600x300', '800x300', '800x600']

        dimension_label = tk.Label(self.window, text="Dimension:")
        dimension_label.grid(row=0, column=0, sticky="e")

        self.dimension_combobox = ttk.Combobox(self.window, values=dimension_options)
        self.dimension_combobox.grid(row=0, column=1, sticky="ew")
        self.dimension_combobox.set('Select Dimension')  # Default text

        # Create labels and entries for other fields
        for i, field in enumerate(self.fields):
            label = tk.Label(self.window, text=f"{field}:")
            label.grid(row=i + 1, column=0, sticky="e")  # Adjust row index for other fields

            entry = tk.Entry(self.window)
            entry.grid(row=i + 1, column=1, sticky="ew")
            entry.insert(0, str(self.default_values.get(field, '')))
            self.entries[field] = entry

        apply_btn = tk.Button(self.window, text="Apply", command=self.apply)
        apply_btn.grid(row=len(self.fields) + 1, column=1, sticky="e")

    def apply(self):
        """Apply the input and close the window."""
        dimension = self.dimension_combobox.get()
        if dimension != 'Select Dimension':
            width, height = dimension.split('x')
            values = {'Width': width, 'Height': height}
            for field, entry in self.entries.items():
                values[field] = entry.get()
            self.callback(values)
            self.window.destroy()
        else:
            messagebox.showerror("Input Error", "Please select a valid dimension.")



class JsonManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.element_data = None
        self.data = []
        self.load()

    def update(self, new_data):
        self.get_info(new_data['id'], "remove")
        for key, new_val in new_data.items():
            self.element_data[key] = new_val
        return self.add_element(self.element_data)

    def load(self):
        """Load the JSON data from the file."""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = []

    def save(self):
        """Save the JSON data to the file."""
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)

    def generate_unique_id(self):
        """Generate a unique ID between 0000 and 9999."""
        existing_ids = {element['id'] for element in self.data}
        all_ids = [f"{i:04d}" for i in range(10000)]
        available_ids = list(set(all_ids) - existing_ids)
        if not available_ids:
            raise ValueError("No available unique IDs left.")
        return random.choice(available_ids)

    def add_element(self, element):
        """Add an element to the JSON data."""
        if "id" not in element.keys():
            element['id'] = self.generate_unique_id()
        self.data.append(element)
        self.save()
        return element['id']

    def remove_element(self, element_id):
        """Remove an element and its children from the JSON data by its ID."""
        elements_to_remove = self._collect_all_children(element_id)
        self.data = [el for el in self.data if el['id'] not in elements_to_remove]
        self.save()
        return elements_to_remove

    def _collect_all_children(self, element_id):
        """Recursively collect all child elements of a given element."""
        to_remove = {element_id}
        for element in self.data:
            if element.get('parent') == element_id:
                to_remove.update(self._collect_all_children(element['id']))
        return to_remove

    def get_info(self, element_id, process='info'):
        temp_data = []
        self.element_data = None
        for element in self.data:
            if element['id'] != element_id:
                temp_data.append(element)
            else:
                self.element_data = element
        if process == 'remove':
            self.data = temp_data

    def get_elements(self):
        return self.data


# Example usage
if __name__ == "__main__":
    json_manager = JsonManager('data.json')

    # Adding an element
    new_element = {
        "text": "New Element",
        "x": 100,
        "y": 100,
        "width": 200,
        "height": 100,
        "parent": "0000",
        "class": "DraggableRightClickMenu"
    }
    json_manager.add_element(new_element)

    # Print current elements
    print(json_manager.get_elements())