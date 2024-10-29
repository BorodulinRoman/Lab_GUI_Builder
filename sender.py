import pyvisa

# Initialize the PyVISA resource manager
rm = pyvisa.ResourceManager()

# List all connected devices (optional, for checking connected ports)
print("Available Resources:", rm.list_resources())

# Connect to the ASRL port (change 'ASRL1::INSTR' to the actual port name, like 'ASRL2::INSTR')
try:
    # Open the ASRL port with specific configurations
    device = rm.open_resource('ASRL4::INSTR')
    device.baud_rate = 115200  # Adjust based on your device
    device.data_bits = 8  # Commonly 7 or 8 bits
    device.parity = pyvisa.constants.Parity.none  # Parity: none, even, or odd
    device.stop_bits = pyvisa.constants.StopBits.one  # 1, 1.5, or 2 stop bits
    device.timeout = 5000  # Set timeout in milliseconds (5 seconds here)

    # Read data in a loop or as needed
    while True:
        try:

            # Read from the device (adjust read_termination and chunk size as necessary)
            data = device.query(" ")
            print("Data received:", data)

        except pyvisa.errors.VisaIOError as e:
            print(f"Read error: {e}")
            break

    # Close the connection
    device.close()

except pyvisa.errors.VisaIOError as e:
    print(f"Connection error: {e}")