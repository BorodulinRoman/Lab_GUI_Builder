# Lab Environment GUI

This project creates a graphical user interface (GUI) for a lab environment, enabling connections to various peripherals such as Keysight instruments, Keithley instruments, PS Lambda power supplies, and COM ports.
The GUI also parses UART data into readable slots, making it easier to analyze and interpret the information.

Features
Peripheral Connections: Seamlessly connect to and communicate with lab instruments, including:

  -Keysight Instruments
  -Keithley Instruments
  -PS Lambda Power Supplies
  -COM Ports
  -UART Data Parsing: Efficiently parse and split UART data bits into readable slots, facilitating data analysis.

User-Friendly Interface: Intuitive GUI built using tkinter for ease of use and improved user experience.

Customizable Layout: Users can stabilize the software and create fields, placing them in a user-friendly manner to meet their specific needs.

# How to Use

Install Dependencies:
  pip install -r requirements.txt


Use the GUI to select and connect to your desired peripheral.
Configure the connection settings as needed.
Parse UART Data:

Connect to the COM port receiving UART data.
The GUI will automatically parse and display the data in readable slots.
Customize the Layout:

Use the drag-and-drop functionality to create and place fields as needed.
Arrange the fields in a way that suits your workflow and preferences.
