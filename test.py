import tkinter as tk
from tkinter import messagebox, ttk
import json
import random


def remove_duplicate_ids(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return

    unique_elements = {}
    for element in data:
        unique_elements[element['id']] = element

    cleaned_data = list(unique_elements.values())

    with open(file_path, 'w') as file:
        json.dump(cleaned_data, file, indent=4)

    print(f"Removed duplicates. {len(data) - len(cleaned_data)} duplicates found and removed.")


def round_to_nearest_10(n):
    if n < 0:
        return 0
    """Round the number to the nearest multiple of 10, rounding up on ties."""
    return ((n + 5) // 10) * 10


class InputWindow:
    """A window for getting input from the user with a dimension combobox."""

    def __init__(self, main_root, title, callback, default_values, options=None):
        """Initialize the InputWindow with a root, title, fields, callback, and default values."""
        self.combobox = {}
        self.root = main_root
        self.window = tk.Toplevel(self.root)
        self.window.title(title)
        self.fields = default_values.keys()
        self.entries = {}
        self.callback = callback
        self.default_values = default_values if default_values else {}
        self.init(options)

    def init(self, options):
        if options is None:
            self.options = {"Dimension": ['800x600']}
        else:
            self.options = options
        """Initialize the input window layout."""
        height = 30 + len(self.fields) * 30 + 30  # Adjust height for combobox
        width = 300  # Define a minimum width for the window
        self.window.geometry(f"{width}x{height}")
        self.window.grid_columnconfigure(1, weight=1)  # Make column 1 expandable

        # Combobox for selecting dimensions
        row = 0
        for type_option, data_option in self.options.items():
            dimension_label = tk.Label(self.window, text=f"{type_option}:")
            dimension_label.grid(row=0, column=0, sticky="e")
            self.combobox[type_option] = (ttk.Combobox(self.window, values=data_option))
            self.combobox[type_option].grid(row=row, column=1, sticky="ew")
            self.combobox[type_option].set(f'Select {type_option}')  # Default text
            row += 1

        # Create labels and entries for other fields
        for i, field in enumerate(self.fields):
            label = tk.Label(self.window, text=f"{field}:")
            label.grid(row=row + i + 1, column=0, sticky="e")  # Adjust row index for other fields

            entry = tk.Entry(self.window)
            entry.grid(row=row + i + 1, column=1, sticky="ew")
            entry.insert(0, str(self.default_values.get(field, '')))
            self.entries[field] = entry
        apply_btn = tk.Button(self.window, text="Apply", command=self.apply)
        apply_btn.grid(row=len(self.fields) + row + 1, column=1, sticky="e")

    def apply(self):
        values = {}
        """Apply the input and close the window."""
        for type_option, data_option in self.combobox.items():
            temp_data = data_option.get()
            if "Dimension" in type_option:
                values['Width'], values['Height'] = temp_data.split('x')
            elif "Type" in type_option:
                values["Type"] = temp_data
            else:
                messagebox.showerror("Input Error", "Please select a valid dimension.")
        for field, entry in self.entries.items():
            values[field] = entry.get()
        self.callback(values)
        self.window.destroy()


class JsonManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = []
        self.load()

    def load(self):
        """Load the JSON data from the file."""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = []

    def save(self):
        """Save the JSON data to the file."""
        self.sanitize_data()  # Ensure data is clean before saving
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)
        self.load()

    def sanitize_data(self):
        """Remove duplicate elements based on ID."""
        unique_elements = {}
        for element in self.data:
            unique_elements[element['id']] = element
        self.data = list(unique_elements.values())

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

    def update(self, new_data):
        """Update an existing element by ID."""
        element_id = new_data.get('id')
        if not element_id:
            raise ValueError("Element ID is required for updating.")

        # Find and update the existing element
        for element in self.data:
            if element['id'] == element_id:
                element.update(new_data)
                break
        else:
            raise ValueError(f"No element found with ID: {element_id}")

        self.save()

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

    def get_info(self, element_id):
        """Retrieve information about a specific element."""
        for element in self.data:
            if element['id'] == element_id:
                return element
        return None

    def get_elements(self):
        return self.data

#remove_duplicate_ids("test.json")