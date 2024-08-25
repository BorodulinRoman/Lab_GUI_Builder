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

