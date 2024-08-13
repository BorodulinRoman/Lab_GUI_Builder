# Lab Environment GUI

This project creates a graphical user interface (GUI) for a lab environment, enabling connections to various peripherals such as Keysight instruments, Keithley instruments, PS Lambda power supplies, and COM ports. The GUI also parses UART data into readable slots, making it easier to analyze and interpret the information.

## Features

- **Peripheral Connections**: Seamlessly connect to and communicate with lab instruments, including:
  - **Keysight Instruments**
  - **Keithley Instruments**
  - **TDK Lambda Power Supplies**
  - **COM Ports**

- **UART Data Parsing**: Efficiently parse and split UART data bits into readable slots, facilitating data analysis.

- **User-Friendly Interface**: Intuitive GUI built using `tkinter` for ease of use and improved user experience.

- **Customizable Layout**: Users can stabilize the software and create fields, placing them in a user-friendly manner to meet their specific needs.

## How to Use

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/yourusername/lab-environment-gui.git
    cd lab-environment-gui
    ```

2. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

3. **Run the Application**:
    ```sh
    python main.py
    ```

4. **Connect to Peripherals**:
    - Use the GUI to select and connect to your desired peripheral.
    - Configure the connection settings as needed.

5. **Parse UART Data**:
    - Connect to the COM port receiving UART data.
    - The GUI will automatically parse and display the data in readable slots.

6. **Customize the Layout**:
    - Use the drag-and-drop functionality to create and place fields as needed.
    - Arrange the fields in a way that suits your workflow and preferences.

## Folder Structure

- **main.py**: Entry point for the application.
- **gui/**: Contains GUI-related code and widgets.
- **peripherals/**: Contains classes and logic for connecting to various peripherals.
- **uart/**: Contains UART data parsing logic.
- **docs/**: Documentation and user guides.

## Contributions

Contributions are welcome! Please fork the repository and submit a pull request with your changes. Ensure your code follows the project's coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Drivers

NI-MAX, NI-VISA, NI-488.2, TDI-Lambda, MySQL-Workbench
