import pyvisa
import time
from threading import Thread
from multiprocessing import Process

# Define the COM port settings
receive_port = 'COM15'  # Port for receiving data
baud_rate = 115200  # Set the correct baud rate for your devices

# Sending process function
# Receiving process function
def receive_data():
    rm = pyvisa.ResourceManager()
    try:
        receiver = rm.open_resource(
            receive_port,
            baud_rate=baud_rate,
            data_bits=8,
            parity=pyvisa.constants.Parity.none,
            stop_bits=pyvisa.constants.StopBits.one,
            read_termination='\n'
        )
        receiver.timeout = 5000
        print("Receiver started.")

        # Receiving data in a loop
        while True:
            try:
                response = receiver.read()  # Read as ASCII string
                if response:
                    print(f"Received hex data as string: {response}")
                    # Optionally, convert back to bytes if needed
                    bytes_data = bytes.fromhex(response)
                    print(f"Received hex data as bytes: {bytes_data}")
                else:
                    print("No data received.")
            except pyvisa.errors.VisaIOError:
                print("No data received within timeout.")
                time.sleep(0.1)  # Short delay to avoid busy waiting

    except Exception as e:
        print(f"Receiver error: {e}")
    finally:
        receiver.close()
        print("Receiver closed.")

if __name__ == '__main__':
    # Create and start separate processes for sending and receiving
    receiver_process = Thread(target=receive_data)
    receiver_process.start()

