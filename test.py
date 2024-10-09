import ctypes
import numpy as np
import sys
import threading
import time
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
from picosdk.errors import PicoSDKCtypesError
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import adc2mV, assert_pico_ok


class PicoScopeReader:
    def __init__(self):
        self.chan_dle = ctypes.c_int16()
        self.status = {}
        self.connected = False

        try:
            # Open PicoScope
            self.status["openunit"] = ps.ps2000aOpenUnit(ctypes.byref(self.chan_dle), None)
            assert_pico_ok(self.status["openunit"])
            self.connected = True

            # Default settings
            self.channels_enabled = {'A': True, 'B': True, 'C': False, 'D': False}
            self.chRanges = {'A': 7, 'B': 7, 'C': 7, 'D': 7}
            self.timebase = 8  # Default timebase
            self.trigger_channel = 0  # Channel A
            self.trigger_threshold = 1024  # Midpoint ADC count
            self.trigger_direction = 2  # Rising
            self.trigger_delay = 0
            self.trigger_auto_trigger_ms = 1000

            self.configure_channels()
            self.configure_trigger()

        except Exception as e:
            print(f"Error initializing PicoScope: {e}")
            self.connected = False

    def configure_channels(self):
        if not self.connected:
            return
        try:
            channel_dict = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            for ch_name, enabled in self.channels_enabled.items():
                ch = channel_dict[ch_name]
                chr_range = self.chRanges[ch_name]
                # Set the channel
                self.status[f"setCh{ch_name}"] = ps.ps2000aSetChannel(
                    self.chan_dle, ch, int(enabled), 1, chr_range, 0)
                assert_pico_ok(self.status[f"setCh{ch_name}"])
        except Exception as e:
            print(f"Error configuring channels: {e}")

    def configure_trigger(self):
        if not self.connected:
            return
        try:
            # Set trigger
            self.status["trigger"] = ps.ps2000aSetSimpleTrigger(
                self.chan_dle,
                1,  # Enable trigger
                self.trigger_channel,
                self.trigger_threshold,
                self.trigger_direction,
                self.trigger_delay,
                self.trigger_auto_trigger_ms)
            assert_pico_ok(self.status["trigger"])
        except Exception as e:
            print(f"Error configuring trigger: {e}")

    def set_channels(self, channels_enabled):
        self.channels_enabled = channels_enabled
        self.configure_channels()

    def set_timebase(self, timebase):
        self.timebase = timebase

    def set_voltage_range(self, voltage_scale_mv):
        # Voltage ranges for PicoScope ps2000a in mV
        voltage_ranges = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]  # in mV
        chr_range = min(range(len(voltage_ranges)), key=lambda i: abs(voltage_ranges[i] - voltage_scale_mv))
        # Apply the new voltage range to enabled channels
        for ch in self.channels_enabled:
            if self.channels_enabled[ch]:
                self.chRanges[ch] = chr_range
        self.configure_channels()

    def set_trigger(self, channel, threshold_mv, direction):
        self.trigger_channel = channel
        try:
            # Convert threshold_mv to ADC counts
            max_adc = ctypes.c_int16()
            self.status["maximumValue"] = ps.ps2000aMaximumValue(
                self.chan_dle, ctypes.byref(max_adc))
            assert_pico_ok(self.status["maximumValue"])
            # Assuming chRange of 7 (+/-10V)
            adc_threshold = int(threshold_mv / 10000 * max_adc.value)
            self.trigger_threshold = adc_threshold
            self.trigger_direction = direction  # Direction as per API
            self.configure_trigger()
        except Exception as e:
            print(f"Error setting trigger: {e}")

    def capture_data(self):
        try:
            time.sleep(0.1)
            # Stop any previous data collection
            self.status["stop"] = ps.ps2000aStop(self.chan_dle)
            assert_pico_ok(self.status["stop"])

            # Set number of pre and post trigger samples to be collected
            pre_trigger_samples = 0  # No need for pre-trigger in your case
            post_trigger_samples = 10 * 1000  # 10 seconds * 1000 samples per second = 10,000 samples
            total_samples = pre_trigger_samples + post_trigger_samples

            # Get timebase
            time_intervalns = ctypes.c_float()
            returned_max_samples = ctypes.c_int32()
            over_sample = ctypes.c_int16(0)

            self.status["getTimebase2"] = ps.ps2000aGetTimebase2(
                self.chan_dle,
                self.timebase,
                total_samples,
                ctypes.byref(time_intervalns),
                over_sample,
                ctypes.byref(returned_max_samples),
                0
            )
            assert_pico_ok(self.status["getTimebase2"])

            # Run block capture
            self.status["runBlock"] = ps.ps2000aRunBlock(
                self.chan_dle,
                pre_trigger_samples,
                post_trigger_samples,
                self.timebase,
                over_sample,
                None,
                0,
                None,
                None
            )
            assert_pico_ok(self.status["runBlock"])

            # Check for data collection to finish
            ready = ctypes.c_int16(0)
            while ready.value == 0:
                ps.ps2000aIsReady(self.chan_dle, ctypes.byref(ready))
                time.sleep(0.01)

            # Create buffers for data
            buffers = {}
            channel_dict = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            for ch_name, enabled in self.channels_enabled.items():
                if enabled:
                    buffers[ch_name] = (ctypes.c_int16 * total_samples)()
                    self.status[f"setDataBuffers{ch_name}"] = ps.ps2000aSetDataBuffers(
                        self.chan_dle,
                        channel_dict[ch_name],
                        ctypes.byref(buffers[ch_name]),
                        None,
                        total_samples,
                        0,
                        0
                    )
                    assert_pico_ok(self.status[f"setDataBuffers{ch_name}"])

            # Retrieve data
            overflow = ctypes.c_int16()
            c_total_samples = ctypes.c_int32(total_samples)
            self.status["getValues"] = ps.ps2000aGetValues(
                self.chan_dle,
                0,
                ctypes.byref(c_total_samples),
                0,
                0,
                0,
                ctypes.byref(overflow)
            )
            assert_pico_ok(self.status["getValues"])

            # Convert data to mV
            max_adc = ctypes.c_int16()
            self.status["maximumValue"] = ps.ps2000aMaximumValue(self.chan_dle, ctypes.byref(max_adc))
            assert_pico_ok(self.status["maximumValue"])

            adc2mv_data = {}
            for ch_name, buffer in buffers.items():
                adc2mv_data[ch_name] = adc2mV(buffer, self.chRanges[ch_name], max_adc)

            # Create time data (in seconds)
            time_data = np.linspace(
                0,  # Start time at 0 seconds
                post_trigger_samples * time_intervalns.value * 1e-9,  # End time in seconds
                post_trigger_samples
            )

            return time_data, adc2mv_data

        except PicoSDKCtypesError as e:
            print(f"Error capturing data: PicoSDK returned {e}")
            return None, None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None, None

    def close_device(self):
        try:
            self.status["close"] = ps.ps2000aCloseUnit(self.chan_dle)
            assert_pico_ok(self.status["close"])
            print("Device closed successfully.")
        except PicoSDKCtypesError as e:
            print(f"Error closing device: PicoSDK returned {e}")

    def close(self):
        # Ensure the PicoScope is stopped and properly closed
        try:
            ps.ps2000aStop(self.chan_dle)  # Stop the device
            ps.ps2000aCloseUnit(self.chan_dle)  # Close the connection to the device
            print("PicoScope closed successfully.")
        except Exception as e:
            print(f"Error closing PicoScope: {e}")


class RealTimeScopeApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.channel_checkboxes = None
        self.time_scale_input = None
        self.time_scale_display_label = None
        self.voltage_scale_input = None
        self.voltage_scale_display_label = None
        self.start_button = None
        self.stop_button = None
        self.overlay_checkbox = None
        self.timebase = None
        self.acquisition_thread = None
        self.setWindowTitle("Real-Time PicoScope GUI")

        # Initialize PicoScopeReader
        self.scope = PicoScopeReader()
        self.acquiring = False

        # Main widget and layout
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(self.main_layout)

        # Control panel
        self.create_control_panel()

        # Graphics layout for plots
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.main_layout.addWidget(self.graphics_layout)

        # Timer for updating plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_graph)

        # Dictionary to hold plot references
        self.plots = {}
        self.curves = {}

        # Initialize plots
        self.update_plot_layout()

    def create_control_panel(self):
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        control_panel.setLayout(control_layout)
        self.main_layout.addWidget(control_panel)

        # Channel selection
        self.channel_checkboxes = {}
        channel_group = QtWidgets.QGroupBox("Channels")
        channel_layout = QtWidgets.QHBoxLayout()
        channel_group.setLayout(channel_layout)
        control_layout.addWidget(channel_group)

        for ch in ['A', 'B', 'C', 'D']:
            checkbox = QtWidgets.QCheckBox(f"Channel {ch}")
            checkbox.setChecked(self.scope.channels_enabled[ch])
            checkbox.stateChanged.connect(self.update_channels)
            channel_layout.addWidget(checkbox)
            self.channel_checkboxes[ch] = checkbox

        # Timescale control
        time_group = QtWidgets.QGroupBox("Time Scale")
        time_layout = QtWidgets.QHBoxLayout()
        time_group.setLayout(time_layout)
        control_layout.addWidget(time_group)

        self.time_scale_input = QtWidgets.QLineEdit("1e-3")  # Default 1 ms
        time_layout.addWidget(QtWidgets.QLabel("Time Scale (s):"))
        time_layout.addWidget(self.time_scale_input)
        time_set_button = QtWidgets.QPushButton("Set")
        time_set_button.clicked.connect(self.update_time_scale)
        time_layout.addWidget(time_set_button)

        # Display label for time scale
        self.time_scale_display_label = QtWidgets.QLabel("Time Scale: 1e-3 s")
        time_layout.addWidget(self.time_scale_display_label)

        # Voltage scale control
        voltage_group = QtWidgets.QGroupBox("Voltage Scale")
        voltage_layout = QtWidgets.QHBoxLayout()
        voltage_group.setLayout(voltage_layout)
        control_layout.addWidget(voltage_group)

        self.voltage_scale_input = QtWidgets.QLineEdit("5000")  # Default +/-5V
        voltage_layout.addWidget(QtWidgets.QLabel("Voltage Scale (mV):"))
        voltage_layout.addWidget(self.voltage_scale_input)
        voltage_set_button = QtWidgets.QPushButton("Set")
        voltage_set_button.clicked.connect(self.update_voltage_scale)
        voltage_layout.addWidget(voltage_set_button)

        # Display label for voltage scale
        self.voltage_scale_display_label = QtWidgets.QLabel("Voltage Scale: 5000 mV")
        voltage_layout.addWidget(self.voltage_scale_display_label)

        # Start and Stop buttons
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.clicked.connect(self.start_acquisition)
        control_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_acquisition)
        control_layout.addWidget(self.stop_button)

        # Overlay option
        self.overlay_checkbox = QtWidgets.QCheckBox("Overlay Channels")
        self.overlay_checkbox.setChecked(False)
        self.overlay_checkbox.stateChanged.connect(self.update_plot_layout)
        control_layout.addWidget(self.overlay_checkbox)

    def update_channels(self):
        channels_enabled = {ch: cb.isChecked() for ch, cb in self.channel_checkboxes.items()}
        self.scope.set_channels(channels_enabled)
        self.update_plot_layout()

    def update_time_scale(self):
        try:
            current_time_scale = float(self.time_scale_input.text())
            if current_time_scale <= 0:
                raise ValueError("Time scale must be a positive number.")

            # Map the desired time scale to the appropriate timebase index
            # PicoScope's timebase starts at 0 for the fastest time per sample
            # Use the device's maximum sample rate to calculate the timebase
            total_samples = 5000  # Total samples as used in capture_data
            desired_sample_interval = current_time_scale / total_samples  # in seconds
            # The timebase index can be calculated or found via lookup
            # For simplicity, we assume timebase = log2(desired_sample_interval * max_sample_rate)
            # For PicoScope 2000 series, timebase of 0 corresponds to 16 ns per sample
            # We'll use an approximate method here
            timebase = int(np.log2(desired_sample_interval * 125e6))  # Assuming 125 MS/s max sample rate
            timebase = max(0, timebase)
            self.scope.set_timebase(timebase)
            self.timebase = timebase  # Save for use in plotting

            self.update_screen_scale(current_time_scale)
            print(f"Time scale updated to {current_time_scale} s (Timebase: {timebase})")
        except Exception as e:
            print(f"Error updating time scale: {e}")

    def update_screen_scale(self, current_time_scale):
        # Update the timescale display label
        self.time_scale_display_label.setText(f"Time Scale: {current_time_scale} s")
        # Update the X-axis range for each plot
        for plot in self.plots.values():
            plot.setXRange(-current_time_scale / 2, current_time_scale / 2)

    def update_voltage_scale(self):
        try:
            current_voltage_scale = float(self.voltage_scale_input.text())
            if current_voltage_scale <= 0:
                raise ValueError("Voltage scale must be a positive number.")

            self.scope.set_voltage_range(current_voltage_scale)
            self.update_screen_voltage_scale(current_voltage_scale)
            print(f"Voltage scale updated to {current_voltage_scale} mV")
        except Exception as e:
            print(f"Error updating voltage scale: {e}")

    def update_screen_voltage_scale(self, current_voltage_scale):
        # Update the voltage scale display label
        self.voltage_scale_display_label.setText(f"Voltage Scale: {current_voltage_scale} mV")
        # Update the Y-axis range for each plot
        voltage_scale_v = current_voltage_scale / 1000  # Convert mV to V
        for plot in self.plots.values():
            plot.setYRange(-voltage_scale_v, voltage_scale_v)

    def start_acquisition(self):
        if not self.acquiring:
            self.acquiring = True
            self.timer.start(50)  # Update every 50 ms

    def stop_acquisition(self):
        if self.acquiring:
            self.acquiring = False
            self.timer.stop()

    def update_plot_layout(self):
        # Clear existing plots
        self.graphics_layout.clear()
        self.plots.clear()
        self.curves.clear()

        enabled_channels = [ch for ch in self.scope.channels_enabled if self.scope.channels_enabled[ch]]
        num_channels = len(enabled_channels)
        overlay = self.overlay_checkbox.isChecked()

        if num_channels == 0:
            return

        if overlay:
            # Single plot overlaying all channels
            p = self.graphics_layout.addPlot()
            self.plots['overlay'] = p
            for ch in enabled_channels:
                curve = p.plot(pen=pg.mkPen(color=self.get_channel_color(ch), width=1.5), name=f"Channel {ch}")
                self.curves[ch] = curve
            p.addLegend()
        else:
            # Separate plots for each channel
            for idx, ch in enumerate(enabled_channels):
                p = self.graphics_layout.addPlot(row=idx, col=0)
                p.setTitle(f"Channel {ch}")
                p.setLabel('left', 'Voltage', units='V')
                p.setLabel('bottom', 'Time', units='s')
                curve = p.plot(pen=pg.mkPen(color=self.get_channel_color(ch), width=1.5))
                self.plots[ch] = p
                self.curves[ch] = curve

    def get_channel_color(self, ch):
        colors = {'A': 'r', 'B': 'g', 'C': 'b', 'D': 'y'}
        return colors.get(ch, 'w')

    def update_graph(self):
        if not self.acquiring:
            return
        try:
            # Check if a thread is already running
            if hasattr(self, 'acquisition_thread') and self.acquisition_thread.is_alive():
                return  # Do not start a new thread if the previous one is still running
        except:
            pass
        # Run data acquisition in a separate thread
        self.semaphore = threading.Semaphore(1)
        self.acquisition_thread = threading.Thread(target=self.acquire_and_plot)
        self.acquisition_thread.start()

    def acquire_and_plot(self):
        if not self.semaphore.acquire(blocking=False):
            # Another thread is capturing data, so we skip this call
            return
        try:
            time_data, adc2mv_data = self.scope.capture_data()
            if time_data is None or adc2mv_data is None:
                return

            # Safely update the plot in the main thread
            QtCore.QMetaObject.invokeMethod(self, 'plot_data',
                                            QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(object, time_data),
                                            QtCore.Q_ARG(object, adc2mv_data))
        finally:
            self.semaphore.release()

    @QtCore.pyqtSlot(object, object)
    def plot_data(self, time_data, adc2mv_data):
        # Convert voltage data from mV to V
        for ch, data in adc2mv_data.items():
            # Convert from mV to V based on the new voltage range
            data_volts = np.array(data) / 1000.0  # Convert mV to V
            curve = self.curves.get(ch)
            if curve:
                curve.setData(time_data, data_volts)

    def closeEvent(self, event):
        try:
            self.scope.close()  # Make sure to close the scope before closing the app
        except AttributeError:
            print("Error: PicoScope object does not have a 'close' method.")
        event.accept()  # Allow the application to close


import nidaqmx
import time
import threading


# Function to pulse two lines with a software-based busy-wait delay in a separate thread
def pulse_output_with_threading(device_name, line1, line2, delay_ms, port=0):
    if device_name is None:
        print("Device with the name dev1 not found")
        return

    def perform_pulse():
        with nidaqmx.Task() as task:
            task.do_channels.add_do_chan(f"{device_name}/port{port}/line{line1}")
            task.do_channels.add_do_chan(f"{device_name}/port{port}/line{line2}")

            # Activate first line
            task.write([True, False])  # Turn on line1, keep line2 off

            # Busy-wait loop for the delay (in milliseconds)
            start_time = time.perf_counter()
            while (time.perf_counter() - start_time) < (delay_ms / 1000.0):
                pass  # Do nothing, just wait precisely

            # Activate second line
            task.write([False, True])  # Turn off line1, turn on line2

    # Create a thread for the timing-sensitive pulse task
    pulse_thread = threading.Thread(target=perform_pulse)

    # Set the thread priority (for some operating systems this can help)
    pulse_thread.start()
    pulse_thread.join()  # Wait for the thread to complete


if __name__ == "__main__":
    # Example: Pulse line1 for 2 milliseconds before switching to line2
    device_name = "Dev1"
    pulse_output_with_threading(device_name, line1=1, line2=2, delay_ms=2)
def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = RealTimeScopeApp()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
