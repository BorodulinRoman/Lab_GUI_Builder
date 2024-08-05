import pyvisa


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

