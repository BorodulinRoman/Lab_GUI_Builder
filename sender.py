import pyvisa
import time

# Define the COM port settings
send_port = 'COM14'  # Port for sending data
baud_rate = 4000000   # Set the correct baud rate for your devices

# Sending process function
def send_data():
    # Initialize the VISA resource manager
    rm = pyvisa.ResourceManager()
    try:
        # Open the COM port for sending data
        sender = rm.open_resource(
            send_port,
            baud_rate=baud_rate,
            data_bits=8,
            parity=pyvisa.constants.Parity.none,
            stop_bits=pyvisa.constants.StopBits.one,
            write_termination=''  # No line feed or other termination character
        )
        sender.timeout = 5000
        print("Sender started.")

        counter = 0  # Initialize the counter

        # Sending data in a loop
        while True:
            # Convert counter to a hex string, padded to 8 characters
            hex_counter = f"A1BB{counter:08X}"  # Uppercase hexadecimal
            print(f"Sending hex data as string: {hex_counter}")
            sender.write(hex_counter)  # Sending as a string without line feed
            counter += 1  # Increment the counter
            time.sleep(0.01)  # Adjust delay as needed

    except Exception as e:
        print(f"Sender error: {e}")
    finally:
        sender.close()
        print("Sender closed.")

send_data()
