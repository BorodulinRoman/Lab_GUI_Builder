import pyvisa as visa
import time
from datetime import datetime

# Create the resource manager
rm = visa.ResourceManager()

def hex_to_bytes(hex_string):
    hex_values = hex_string.split(',')
    byte_array = bytes(int(h, 16) for h in hex_values)
    return byte_array

# Open resources for the instruments
instrument4 = rm.open_resource('ASRL4::INSTR')
packet_hex = 'AA,3D,FF,00,EF,55'
packet = hex_to_bytes(packet_hex)
# Set up your instruments
instrument4.baud_rate = 4000000
instrument4.timeout = 1  # in milliseconds

counter = 0
try:
    while True:
        counter += 1
        try:
            if counter >= 255:
                counter = 0
            instrument4.write(f"{hex(255 - counter)[2:].upper()},{packet_hex},{hex(counter)[2:].upper()}")  # Send command
        except visa.errors.VisaIOError as e:
            if e.error_code == visa.constants.VI_ERROR_TMO:
                print("No data received. Sending trigger command...")
        except KeyboardInterrupt:
            break
finally:
    instrument4.close()
    print("Cleanup complete.")