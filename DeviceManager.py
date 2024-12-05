from tkinter import filedialog, messagebox
from datetime import datetime
from nidaqmx.system import System
import nidaqmx
import picosdk
import pyvisa
import atexit
import time
import threading
import serial
import serial.tools.list_ports
import re


def is_port_in_use(port_name):
    """Check if a COM port is in use without taking full control."""
    try:
        # Attempt to open the port in a non-exclusive mode
        with serial.Serial(port=port_name, baudrate=9600, timeout=1) as ser:
            return False  # Port is not in use if we can open it successfully
    except serial.SerialException:
        return True  # Port is already in use or cannot be accessed


def extract_bits(lst, low, high, format_type='decimal'):
    # Convert hex strings to integers
    int_list = [int(hex_str, 16) for hex_str in lst]

    if high > 7:
        # Combine all bytes into one big integer
        combined_value = 0
        for val in int_list:
            combined_value = (combined_value << 8) | val
        # Create mask to extract bits from 'low' to 'high'
        mask = ((1 << (high - low + 1)) - 1) << low
        # Extract bits
        extracted_bits = (combined_value & mask) >> low
        # Format the result
        if format_type == 'binary':
            result = bin(extracted_bits)
        elif format_type == 'hexadecimal':
            result = hex(extracted_bits)
        else:
            result = str(extracted_bits)
        # Return the result as is for a single value
        return result
    else:
        # Process each byte separately
        results = []
        mask = ((1 << (high - low + 1)) - 1) << low
        for val in int_list:
            extracted_bits = (val & mask) >> low
            # Format the result
            if format_type == 'binary':
                formatted_result = bin(extracted_bits)
            elif format_type == 'hexadecimal':
                formatted_result = hex(extracted_bits)
            else:
                formatted_result = str(extracted_bits)
            results.append(formatted_result)
        # Return comma-separated string for multiple values
        return ','.join(results)


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


class DeviceManager:
    def __init__(self, logger):
        self.logger = logger
        self.start_byte = 2
        self.header = ''
        self.response = []
        self.packet_size = 36
        self.baud_rate = 1000000
        self.timeout = 5
        self.rm = pyvisa.ResourceManager()
        self.device = None
        self.device_name = None
        self.ni_controller = None  # Used for NI6009Controller
        atexit.register(self.cleanup)

    def cleanup(self):
        try:
            """Cleanup resources before exiting."""
            if "ASRL" in self.device_name and self.device:
                self.device.close()
                self.logger.message("Cleanly disconnected from VISA device on exit")
            elif "Dev" in self.device_name and self.ni_controller:
                self.ni_controller.close()
                self.logger.message("Cleanly disconnected from NI device on exit")
        except Exception as e:
            self.logger.message(e, 'ERROR')

    def find_devices(self):
        """Find all connected devices (both VISA and NI devices)."""
        system = nidaqmx.system.System.local()
        ni_devices = [dev.name for dev in system.devices]
        visa_devices = self.rm.list_resources()

        all_devices = ni_devices + [dev for dev in visa_devices if "ASRL" in dev]
        return all_devices

    def connect(self):
        try:
            """Connect to a specific device based on the type selected (VISA or NI)."""
            if "ASRL" in self.device_name:
                return self.connect_visa()
            elif "Dev" in self.device_name:
                return self.connect_ni()
            else:
                self.logger.message("Unsupported device type selected")
                return False
        except Exception as e:
            messagebox.showerror("Connection Error", f"Error: {e}")
            return False

    def connect_visa(self):
        """Connect to a VISA device."""
        match = re.search(r'ASRL(\d+)::INSTR', self.device_name)
        if not is_port_in_use(f'COM{int(match.group(1))}'):
            self.device = self.rm.open_resource(
                self.device_name,
                baud_rate=self.baud_rate,
                data_bits=8,
                parity=pyvisa.constants.Parity.none,
                stop_bits=pyvisa.constants.StopBits.one,
                read_termination=''  # No termination character
            )
            self.logger.message(f"Connected to VISA device: {self.device_name}")
            self.device.timeout = self.timeout
            return True
        else:
            self.logger.message(f"Failed to connect to VISA device")

            return False

    def connect_ni(self):
        """Connect to an NI device."""
        self.ni_controller = NI6009Controller(self.device_name, self.logger)
        return self.ni_controller.connect()

    def disconnect(self):
        """Disconnect the currently connected device."""
        if "ASRL" in self.device_name and self.device:
            self.device.close()
            self.logger.message("Disconnected from VISA device")
            self.device = None
        elif "Dev" in self.device_name and self.ni_controller:
            self.ni_controller.close()
            self.logger.message("Disconnected from NI device")
            self.ni_controller = None
        else:
            self.logger.message("No device to disconnect")

    def write(self, command):
        """Send a command to the connected device (VISA or NI)."""
        if "ASRL" in self.device_name and self.device:
            try:
                self.device.write_raw(bytes.fromhex(command))
                self.logger.message(f"Command '{bytes.fromhex(command)}' sent to VISA device")
            except Exception as e:
                self.device.write(command)
                self.logger.message(f"Failed to send command to VISA device: {str(e)}")
        elif "Dev" in self.device_name and self.ni_controller:
            self.ni_controller.write(command)
        else:
            self.logger.message("No device connected to send command")

    def continuous_read(self):
        """Read response from the connected device."""
        if "ASRL" in self.device_name and self.device:
            try:
                if self.device.bytes_in_buffer > self.packet_size * 3:
                    response = self.device.read_bytes(self.device.bytes_in_buffer)
                    temp_packet = ''
                    temp_response = str(response.hex()).split(self.header)

                    if not temp_response:
                        return None

                    for i, packet in enumerate(temp_response):
                        if i == 0:
                            temp_packet = packet
                            continue

                        data = temp_packet[-self.start_byte * 2:] + self.header + packet[:-self.start_byte * 2]
                        temp_packet = packet

                        if len(data) == self.packet_size * 2:
                            self.response.append(data)

                response = None
                for packet in self.response:
                    response = [packet[i:i + 2] for i in range(0, len(packet), 2)]
                    self.logger.message(message=f"{response}", update_info_desk=False)

                self.response = []
                return response

            except Exception as e:
                return None
        else:
            time.sleep(0.1)
            # self.logger.message("No device connected to read from", 'ERROR')
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
            # pico_scope = picosdk.open_picoscope()
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


class NI6009Controller:
    def __init__(self, device_name, logger):
        self.device_name = device_name
        self.logger = logger
        self.ni_device = None

    def connect(self):
        """Connect to the NI 6009 device."""
        try:
            self.ni_device = nidaqmx.Task()
            self.logger.message(f"Connected to NI device: {self.device_name}")
            return True
        except Exception as e:
            self.logger.message(f"Failed to connect to NI device: {str(e)}")
            return False

    def write(self, command):
        """Process command strings and map to specific NI actions."""
        if not self.ni_device:
            self.logger.message("NI device not connected.")
            return

        try:
            if command.startswith("RELAY"):
                self.process_relay_command(command)
            else:
                self.logger.message(f"Unknown NI command: {command}")
        except Exception as e:
            self.logger.message(f"Failed to process command '{command}': {str(e)}")

    def process_relay_command(self, command):
        """Process RELAY command strings and control digital outputs."""
        try:
            _, *relay_params = command.split(',')
            relay_params = [param.strip() for param in relay_params]

            # Check for simple format: RELAY, <line>, <state>
            if '&' not in relay_params[0]:
                line = int(relay_params[0])
                state = int(relay_params[1])
                self.set_output(line, state == 1)  # Convert 1 -> True, 0 -> False
            elif '&' in relay_params[0]:
                lines = []
                states = []
                times = []
                for relay in relay_params:

                    l, s, t = relay.split('&')
                    lines.append(l)
                    states.append(bool(s))
                    if int(t) > 3:
                        times.append((int(t)-2) / 1000.0)
                    else:
                        times.append(0)
                    # Format: RELAY, line1&state1&delay1, line2&state2&delay1......

                #line2, state2 = map(int, relay_params[1].split('&'))
                #delay_ms = int(relay_params[2].strip())
                self.pulse_output_multy(lines, states, times)
                #self.pulse_output(line1, state1 == 1, line2, state2 == 1, delay_ms)
            else:
                self.logger.message(f"Invalid command format: {command}")
        except Exception as e:
            self.logger.message(f"Failed to process RELAY command: {e}")

    def set_output(self, line, value):
        """Set a specific digital line to high or low."""
        try:
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan(f"{self.device_name}/port0/line{line}")
                task.write([bool(value)])  # Ensure value is a boolean: True/False
                self.logger.message(f"Set line {line} to {'High' if value else 'Low'}")
        except Exception as e:
            self.logger.message(f"Failed to set output on line {line}: {e}")

    def pulse_output_multy(self, lines, states, times):
        """
        Pulse multiple lines with specified states and delays.
        :param lines: List of channel lines to pulse (e.g., [0, 1, 2]).
        :param states: List of target states for each channel (e.g., [1, 0, 1]).
        :param times: List of delays (in ms) for each channel (e.g., [10, 20, 30]).
        """

        def perform_pulse():
            try:
                with nidaqmx.Task() as task:
                    # Add all specified lines to the task
                    for line in lines:
                        task.do_channels.add_do_chan(f"{self.device_name}/port0/line{line}")

                    for i, state in enumerate(states):  # Use enumerate here
                        states[i] = not state
                        task.write(states)  # Set target states

                        # Delay to allow state stabilization

                        start_time = time.perf_counter()
                        while (time.perf_counter() - start_time) < times[i]:
                            pass  # Wait for the maximum delay

                    self.logger.message(
                        f"Pulsed lines {lines} to states {states} with delays {times}ms."
                    )
            except Exception as e:
                self.logger.message(f"Error during pulse operation: {e}")

        # Start the pulse operation in a separate thread
        pulse_thread = threading.Thread(target=perform_pulse)
        pulse_thread.start()
        pulse_thread.join()

    def pulse_output(self, line1, state1, line2, state2, delay_ms):
        """Pulse two lines with a specified delay between state changes."""
        state_1 = bool(state1)
        state_2 = bool(state2)
        if delay_ms < 3:
            delay_ms = 3

        def perform_pulse():
            try:
                with nidaqmx.Task() as task:
                    # Add both lines to the task
                    task.do_channels.add_do_chan(f"{self.device_name}/port0/line{line1}")
                    task.do_channels.add_do_chan(f"{self.device_name}/port0/line{line2}")

                    # Set the initial state of both lines
                    initial_state = [state_1, not state_2]  # Convert to boolean
                    task.write(initial_state)  # Set initial states

                    # Busy-wait loop for the delay (in milliseconds)
                    start_time = time.perf_counter()
                    while (time.perf_counter() - start_time) < ((delay_ms - 2) / 1000.0):
                        pass  # Wait precisely for the delay

                    # Switch to the target state after the delay
                    task.write([state_1, state_2])  # Ensure all states are boolean
                    self.logger.message(
                        f"Pulsed line {line1} to {'High' if state1 else 'Low'} and line {line2}"
                        f" to {'High' if state2 else 'Low'} after {delay_ms}ms delay."
                    )
            except Exception as e:
                self.logger.message(f"Error during pulse operation: {e}")

        pulse_thread = threading.Thread(target=perform_pulse)
        pulse_thread.start()
        pulse_thread.join()



    def close(self):
        """Close the NI device."""
        if self.ni_device:
            self.ni_device.close()
            self.ni_device = None
            self.logger.message(f"NI device {self.device_name} disconnected.")



# if __name__ == "__main__":
#     class Logger:
#         def message(self, msg):
#             print(msg)
#
#
#     logger = Logger()
#     dev = DeviceManager(logger)
#     dev.device_name = dev.find_devices()[0]
#     print(dev.device_name)
#     dev.connect()
#     while 1:
#         # Example RELAY commands
#         time.sleep(.1)
#         dev.write("RELAY, 0, 1")  # Set line 0 to High
#         dev.write("RELAY, 1, 1")  # Set line 0 to Low
#         dev.write("RELAY, 2, 1")  # Set line 0 to Low
#         time.sleep(.1)
#
#         dev.write("RELAY, 0&0&10, 1&0&0, 2&0&0")
#
#     dev.close()
