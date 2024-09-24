import pyvisa
from pyvisa import constants
from tkinter import filedialog
from datetime import datetime
from nidaqmx.system import System
import atexit
import picosdk


def extract_bits(byte_string_list, low, high):
    try:
        # Convert byte strings to integers
        byte_list = [int(byte_str, 16) for byte_str in byte_string_list]

        # Calculate the total bit span
        total_bits = len(byte_list) * 8
        # Validate range
        if not (0 <= low <= high < total_bits):
            raise ValueError("Low and high must be within the range determined by the byte list size.")

        # Combine bytes into a single integer
        combined_bytes = 0
        for i, byte in enumerate(byte_list):
            combined_bytes |= byte << (8 * i)

        # Mask and extract bits
        mask = (1 << (high - low + 1)) - 1
        extracted_value = (combined_bytes >> low) & mask

        return int(extracted_value)  # Return as integer for flexible formatting
    except Exception as e:
        return "------"


def get_start_time_in_sec():
    # Placeholder function; replace with your actual implementation
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def get_start_time():
    now = datetime.now()

    # Get current time with hours, minutes, seconds
    hours = now.hour
    minutes = now.minute
    seconds = now.second

    # Get milliseconds
    milliseconds = int(now.microsecond / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


class VisaDeviceManager:
    def __init__(self, logger):
        self.logger = logger
        self.rm = pyvisa.ResourceManager()
        self.device = None
        self.device_name = None
        atexit.register(self.cleanup)

    def cleanup(self):
        """Cleanup resources before exiting."""
        if self.device:
            self.device.close()
            self.device = None
            self.logger.message("Cleanly disconnected from device on exit")

    def find_devices(self):
        """Finds all connected VISA devices."""
        devices = self.rm.list_resources()
        asrl_devices = []
        for device in devices:
            if "ASRL" in device:
                asrl_devices.append(device)
        return asrl_devices

    def connect(self):
        """Connect to a specific VISA device by name."""
        try:
            self.device = self.rm.open_resource(self.device_name, access_mode=constants.VI_EXCLUSIVE_LOCK)
            self.logger.message(f"Connected to {self.device_name}")
            self.set_device_timeout()
            self.device.write_termination = None
            self.device.term_chars = None
            self.device.timeout = 1  # in milliseconds
            self.device.baud_rate = 4000000
            return True
        except Exception as e:
            self.logger.message(f"Failed to connect to {self.device_name}: {str(e)}")
            return False

    def disconnect(self):
        """Disconnect the currently connected VISA device."""
        if self.device:
            self.device.close()
            self.logger.message("Disconnected from device")
            self.device = None
        else:
            self.logger.message("No device to disconnect")

    def write(self, command):
        """Send a command to the connected VISA device."""
        if self.device:
            try:
                self.device.write(command)
                self.logger.message(f"Command '{command}' sent")
            except Exception as e:
                self.logger.message(f"Failed to send command '{command}': {str(e)}")
        else:
            self.logger.message("No device connected to send command")

    def set_device_timeout(self, timeout_ms=1000):
        """Set the timeout for the VISA device in milliseconds."""
        if self.device:
            self.device.timeout = timeout_ms
            self.logger.message(f"Device timeout set to {timeout_ms} milliseconds")
        else:
            self.logger.message("No device connected to set timeout")

    def query_read(self, command=None):
        if self.device:
            if command is None:
                return self.read_response()
            try:
                response = self.device.query(command)
                return response
            except Exception as e:
                return None
        else:
            return None

    def read_response(self):
        """Read a response from the connected VISA device without sending a command."""
        if self.device:
            try:
                self.device.read_termination = None
                response = self.device.read()
                return response
            except Exception as e:
                return None
        else:
            return None


class ScopeUSB:
    def __init__(self, logger):
        self.logger = logger
        self.scopes = {}
        self.data = {}
        self.rm = pyvisa.ResourceManager()
        self.init()

    def init(self):
        # Initialize VISA resources
        for resource_name in self.rm.list_resources():
            try:
                resource_split_name = resource_name.split('::')
                dec_list = [str(int(item, 16)) if '0x' in item else item for item in resource_split_name]
                dec_list.remove(dec_list[-2])
                resource_name = '::'.join(dec_list)
                self.scopes[resource_name] = {"scope_address": self.rm.open_resource(resource_name),
                                              'scope_type': "KeySight"}

                self.logger.message(self.scopes[resource_name].query('*IDN?'))
            except Exception as e:
                self.logger.message(f"Error with VISA resource {resource_name}: {e}")

        # Initialize NI-DAQ devices
        try:
            system = System.local()
            for device in system.devices:
                # Here you can customize how much device info you want to log and save
                device_info = {
                    'scope_address': device.name,
                    'scope_type': device.product_type,
                }

                self.scopes[device.name] = device_info
                self.logger.message(f"NI-DAQ device added: {device_info}")
        except Exception as e:
            self.logger.message(f"Error initializing NI-DAQ devices: {e}")

        # Initialize PicoScope devices
        try:
            # Example initialization, adjust based on actual API calls for PicoScope
            pico_scope = picosdk.open_picoscope()
            pico_devices = picosdk.discover_devices()
            for device in pico_devices:
                self.scopes[device.serial_number] = {
                    'scope_address': device.handle,
                    'scope_type': 'PicoScope'
                }
                self.logger.message(f"PicoScope device added: Serial {device.serial_number}")
        except Exception as e:
            self.logger.message(f"Error initializing PicoScope devices: {e}")

    def reset(self, scp_id):
        self.scopes[scp_id].write('*RST')

    def send_command(self, scp_id, command):
        self.data[scp_id] = None
        self.scopes[scp_id].write(command)
        self.data[scp_id] = self.scopes[scp_id].read()

    def close_connection(self, scp_id):
        self.scopes[scp_id].close()

    def load_setup(self, scp_id, file_path):
        with open(file_path, 'rb') as file:
            setup = file.read()
        self.scopes[scp_id].write_binary_values(":SYSTem:SETup ", setup, datatype='B')

    def save_setup(self, scp_id, file_path=None):
        try:
            self.data[scp_id] = self.scopes[scp_id].query_binary_values(':SYSTem:SETup?', datatype='B', container=bytes)
            self.data = {}
            self.send_command(scp_id, ':SYST:SET?')

            temp = self.data[scp_id].split("\n")
            self.data[scp_id] = "".join(temp)
            file_path = filedialog.asksaveasfilename(defaultextension='.agilent',
                                                     filetypes=[('Script file', "*agilent"),
                                                                ('All files', "*.*")])
        except Exception as e:
            self.logger.message(f"Can't save the setup error: {e}")
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.data[scp_id])
        self.data[scp_id] = None

    def stop(self, scp_id):
        self.scopes[scp_id].write(":STOP")

    def single(self, scp_id):
        self.scopes[scp_id].write(":SINGle")

    def save_meas(self, scp_id):
        self.send_command(scp_id, ":MEAS:RES?")

    def get_measurement_results(self, scp_id, index):
        data = self.data[scp_id].split(',')
        i = (index - 1) * 7 + 4
        return data[i]

    def save_img(self, scp_id, path):
        try:
            self.scopes[scp_id].timeout = 30000
            screen = self.scopes[scp_id].query_binary_values(':DISP:DATA? PNG, COL', datatype='B', container=bytes)
            img = f"{path}/{'_'.join(scp_id.split('::'))}_screenshot_{get_start_time_in_sec()}.png"
            with open(img, 'wb') as f:
                f.write(screen)
            self.scopes[scp_id].timeout = 2000
        except Exception as e:
            self.logger.message(f"Can't save img error {e}")

    def __del__(self):
        try:
            for resource_name in self.rm.list_resources():
                resource_split_name = resource_name.split('::')
                dec_list = [str(int(item, 16)) if '0x' in item else item for item in resource_split_name]
                dec_list.remove(dec_list[-2])
                resource_name = '::'.join(dec_list)
                self.close_connection(resource_name)
        except Exception as e:
            self.logger.message(e)
