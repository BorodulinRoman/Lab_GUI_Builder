import pyvisa
from tkinter import filedialog
from datetime import datetime


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

    def find_devices(self):
        """Finds all connected VISA devices."""
        devices = self.rm.list_resources()
        return devices

    def connect(self, device_name):
        """Connect to a specific VISA device by name."""
        try:
            self.device = self.rm.open_resource(device_name)
            self.logger.message(f"Connected to {device_name}")
        except Exception as e:
            self.logger.message(f"Failed to connect to {device_name}: {str(e)}")

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

    def query(self, command):
        """Send a command and get a response from the connected VISA device."""
        if self.device:
            try:
                response = self.device.query(command)
                self.logger.message(f"Query '{command}' received response: {response}")
                return response
            except Exception as e:
                self.logger.message(f"Failed to query command '{command}': {str(e)}")
                return None
        else:
            self.logger.message("No device connected to send query")
            return None


class KeySightScopeUSB:
    def __init__(self, logger):
        self.logger = logger
        self.scopes = {}
        self.data = {}
        self.rm = pyvisa.ResourceManager()
        self.init()

    def init(self):
        for resource_name in self.rm.list_resources():
            try:
                resource_split_name = resource_name.split('::')
                dec_list = [str(int(item, 16)) if '0x' in item else item for item in resource_split_name]
                dec_list.remove(dec_list[-2])
                resource_name = '::'.join(dec_list)
                self.scopes[resource_name] = self.rm.open_resource(resource_name)
                self.logger.message(self.scopes[resource_name].query('*IDN?'))
            except Exception as e:
                self.logger.message(e)

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
