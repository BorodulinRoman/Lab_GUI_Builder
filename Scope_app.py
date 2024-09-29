import sys
import numpy as np
import threading
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

class RandomDataGenerator(QtCore.QObject):
    data_ready = QtCore.pyqtSignal(float, dict)

    def __init__(self, channels_enabled):
        super().__init__()
        self.channels_enabled = channels_enabled
        self.running = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.generate_data)
        self.time = 0
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.timer.start(10)  # Generate data every 10 ms

    def stop(self):
        self.running = False
        self.timer.stop()

    def generate_data(self):
        with self.lock:
            time_increment = 0.01  # 10 ms
            self.time += time_increment

            data = {}
            for i, ch in enumerate(self.channels_enabled):
                if self.channels_enabled[ch]:
                    frequency = 1*i  # 1Hz signal frequency
                    voltage = np.sin(2 * np.pi * frequency * self.time) + np.random.normal(0, 0.1)
                    data[ch] = voltage * i

            self.data_ready.emit(self.time, data)


class MeasurementWidget(QtWidgets.QWidget):
    def __init__(self, measurement):
        super().__init__()
        self.measurement = measurement
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Measurement name label
        name_label = QtWidgets.QLabel(f"<b>{self.measurement.name}</b>")
        name_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(name_label)

        # Measurement description
        description = f"{self.measurement.get_description()}"
        description_label = QtWidgets.QLabel(description)
        layout.addWidget(description_label)

        # Result
        self.result_label = QtWidgets.QLabel(f"Result: {self.measurement.result}")
        layout.addWidget(self.result_label)

        # Set color based on channel
        color = self.measurement.get_color()
        self.setStyleSheet(f"background-color: {color}; border: 1px solid black;")

    def update_result(self):
        self.result_label.setText(f"Result: {self.measurement.result}")

class Measurement:
    def __init__(self, name, measurement_type, channels, params):
        self.name = name
        self.measurement_type = measurement_type
        self.channels = channels  # List of channels
        self.params = params  # Additional parameters
        self.result = None

    def get_description(self):
        if self.measurement_type == "Average Voltage":
            return f"Average voltage on channel {self.channels[0]}"
        elif self.measurement_type == "Frequency":
            return f"Frequency on channel {self.channels[0]}"
        elif self.measurement_type == "Delay":
            return f"Delay between channel {self.channels[0]} ({self.params['edge1']}) and channel {self.channels[1]} ({self.params['edge2']})"
        else:
            return "Measurement"

    def get_color(self):
        if len(self.channels) == 1:
            colors = {'A': 'lightcoral', 'B': 'lightgreen', 'C': 'lightblue', 'D': 'lightyellow'}
            return colors.get(self.channels[0], 'white')
        else:
            return 'lightgray'


class RealTimeScopeApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.channel_checkboxes = None
        self.time_scale_input = None
        self.time_scale_display_label = None
        self.voltage_scale_input = None
        self.voltage_scale_display_label = None
        self.run_stop_button = None
        self.overlay_checkbox = None
        self.measurements = []  # List of Measurement objects
        self.measurement_widgets = []  # List of tuples (Measurement, MeasurementWidget)
        self.setWindowTitle("Real-Time Oscilloscope Simulation")

        self.acquiring = False
        self.data_buffer = {}  # Store data for each channel
        self.max_time = 5  # Default time scale is 5 seconds

        # Trigger settings
        self.trigger_mode = 'AUTO'
        self.trigger_channel = 'A'
        self.trigger_level = 0.0
        self.trigger_edge = 'RISING'  # Default trigger edge type
        self.triggered = False

        # Main layout creation
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)

        # Now we create a horizontal layout to place the graph and the measurement panel side by side
        self.main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(self.main_layout)

        # Left layout (controls and graph)
        left_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(left_layout)

        # Control panel
        self.create_control_panel()
        left_layout.addWidget(self.control_panel)

        # Graph area
        self.graphics_layout = pg.GraphicsLayoutWidget()
        left_layout.addWidget(self.graphics_layout)

        # Trigger panel
        self.create_trigger_panel()
        left_layout.addWidget(self.trigger_panel)

        # Right layout (measurement panel)
        self.create_measurement_panel()
        self.main_layout.addWidget(self.measurement_panel)

        # Dictionaries for storing plots and curves
        self.plots = {}
        self.curves = {}
        self.trigger_line = None

        # Initialize plots
        self.channels_enabled = {'A': True, 'B': False, 'C': False, 'D': False}
        self.update_plot_layout()

        # Data generator
        self.data_generator = RandomDataGenerator(self.channels_enabled)
        self.data_generator.data_ready.connect(self.update_graph)

    def create_control_panel(self):
        self.control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout()
        self.control_panel.setLayout(control_layout)

        # Channel selection
        self.channel_checkboxes = {}
        channel_group = QtWidgets.QGroupBox("Channels")
        channel_layout = QtWidgets.QHBoxLayout()
        channel_group.setLayout(channel_layout)
        control_layout.addWidget(channel_group)

        for ch in ['A', 'B', 'C', 'D']:
            checkbox = QtWidgets.QCheckBox(f"Channel {ch}")
            checkbox.setChecked(ch == 'A')  # Default: Channel A is active
            checkbox.stateChanged.connect(self.update_channels)
            channel_layout.addWidget(checkbox)
            self.channel_checkboxes[ch] = checkbox

        # Time scale control
        time_group = QtWidgets.QGroupBox("Time Scale")
        time_layout = QtWidgets.QHBoxLayout()
        time_group.setLayout(time_layout)
        control_layout.addWidget(time_group)

        self.time_scale_input = QtWidgets.QLineEdit("5")  # Default: 5 seconds
        time_layout.addWidget(QtWidgets.QLabel("Time (seconds):"))
        time_layout.addWidget(self.time_scale_input)
        time_set_button = QtWidgets.QPushButton("Set")
        time_set_button.clicked.connect(self.update_time_scale)
        time_layout.addWidget(time_set_button)

        self.time_scale_display_label = QtWidgets.QLabel("Time: 5 s")
        time_layout.addWidget(self.time_scale_display_label)

        # Voltage scale control
        voltage_group = QtWidgets.QGroupBox("Voltage Scale")
        voltage_layout = QtWidgets.QHBoxLayout()
        voltage_group.setLayout(voltage_layout)
        control_layout.addWidget(voltage_group)

        self.voltage_scale_input = QtWidgets.QLineEdit("1")  # Default: +/-1V
        voltage_layout.addWidget(QtWidgets.QLabel("Voltage (V):"))
        voltage_layout.addWidget(self.voltage_scale_input)
        voltage_set_button = QtWidgets.QPushButton("Set")
        voltage_set_button.clicked.connect(self.update_voltage_scale)
        voltage_layout.addWidget(voltage_set_button)

        self.voltage_scale_display_label = QtWidgets.QLabel("Voltage: 1 V")
        voltage_layout.addWidget(self.voltage_scale_display_label)

        # Overlay option
        self.overlay_checkbox = QtWidgets.QCheckBox("Overlay Channels")
        self.overlay_checkbox.setChecked(False)
        self.overlay_checkbox.stateChanged.connect(self.update_plot_layout)
        control_layout.addWidget(self.overlay_checkbox)

    def create_trigger_panel(self):
        self.trigger_panel = QtWidgets.QGroupBox("Trigger")
        trigger_layout = QtWidgets.QHBoxLayout()
        self.trigger_panel.setLayout(trigger_layout)

        # Add buttons for AUTO and SIGNAL modes
        self.auto_button = QtWidgets.QPushButton("AUTO")
        self.auto_button.setCheckable(True)
        self.auto_button.setChecked(True)  # Default is AUTO
        self.auto_button.clicked.connect(self.set_auto_mode)
        trigger_layout.addWidget(self.auto_button)

        self.signal_button = QtWidgets.QPushButton("SIGNAL")
        self.signal_button.setCheckable(True)
        self.signal_button.clicked.connect(self.set_signal_mode)
        trigger_layout.addWidget(self.signal_button)

        # Add RUN/STOP button
        self.run_stop_button = QtWidgets.QPushButton("RUN")
        self.run_stop_button.clicked.connect(self.toggle_acquisition)
        trigger_layout.addWidget(self.run_stop_button)

        # Trigger channel selection
        self.trigger_channel_combo = QtWidgets.QComboBox()
        self.trigger_channel_combo.addItems(['A', 'B', 'C', 'D'])
        self.trigger_channel_combo.currentTextChanged.connect(self.change_trigger_channel)
        trigger_layout.addWidget(QtWidgets.QLabel("Channel:"))
        trigger_layout.addWidget(self.trigger_channel_combo)

        # Trigger voltage level
        self.trigger_level_input = QtWidgets.QLineEdit("0")
        self.trigger_level_input.setFixedWidth(50)
        self.trigger_level_input.returnPressed.connect(self.change_trigger_level)
        trigger_layout.addWidget(QtWidgets.QLabel("Level (V):"))
        trigger_layout.addWidget(self.trigger_level_input)

        # Trigger edge selection (RISING/FALLING)
        self.trigger_edge_combo = QtWidgets.QComboBox()
        self.trigger_edge_combo.addItems(["RISING", "FALLING"])
        self.trigger_edge_combo.currentTextChanged.connect(self.change_trigger_edge)
        trigger_layout.addWidget(QtWidgets.QLabel("Edge:"))
        trigger_layout.addWidget(self.trigger_edge_combo)
        trigger_layout.addWidget(QtWidgets.QLabel(" "*180))

    def set_auto_mode(self):
        self.auto_button.setChecked(True)
        self.signal_button.setChecked(False)
        self.trigger_mode = 'AUTO'
        print("AUTO mode activated")

    def set_signal_mode(self):
        self.signal_button.setChecked(True)
        self.auto_button.setChecked(False)
        self.trigger_mode = 'SINGLE'
        print("SIGNAL mode activated")

    def toggle_acquisition(self):
        if self.acquiring:
            self.stop_acquisition()
            self.run_stop_button.setText("RUN")
        else:
            self.start_acquisition()
            self.run_stop_button.setText("STOP")

    def create_measurement_panel(self):
        self.measurement_panel = QtWidgets.QWidget()
        measurement_layout = QtWidgets.QVBoxLayout()
        self.measurement_panel.setLayout(measurement_layout)

        # Measurement list
        self.measurement_list = QtWidgets.QListWidget()
        self.measurement_list.setFixedWidth(200)  # Set fixed width to 200 pixels, height will be dynamic
        measurement_layout.addWidget(self.measurement_list)

        # Context menu for adding/removing measurements
        self.measurement_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.measurement_list.customContextMenuRequested.connect(self.show_measurement_context_menu)
        self.measurement_list.itemDoubleClicked.connect(self.edit_measurement)

    def show_measurement_context_menu(self, position):
        menu = QtWidgets.QMenu()
        add_action = menu.addAction("Add Measurement")
        delete_action = menu.addAction("Delete Measurement")

        action = menu.exec_(self.measurement_list.viewport().mapToGlobal(position))

        if action == add_action:
            self.add_measurement_dialog()
        elif action == delete_action:
            self.remove_measurement()

    def edit_measurement(self, item):
        # Can implement editing measurement on double-click if needed
        pass

    def add_measurement_dialog(self):
        dialog = AddMeasurementDialog(self.channels_enabled.keys(), self)
        if dialog.exec_():
            measurement = dialog.get_measurement()
            if measurement:
                self.measurements.append(measurement)
                widget = MeasurementWidget(measurement)
                item = QtWidgets.QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                self.measurement_list.addItem(item)
                self.measurement_list.setItemWidget(item, widget)
                self.measurement_widgets.append((measurement, widget))

    def remove_measurement(self):
        selected_items = self.measurement_list.selectedItems()
        if selected_items:
            index = self.measurement_list.row(selected_items[0])
            self.measurement_list.takeItem(index)
            self.measurements.pop(index)
            self.measurement_widgets.pop(index)

    def update_channels(self):
        self.channels_enabled = {ch: cb.isChecked() for ch, cb in self.channel_checkboxes.items()}
        self.data_generator.channels_enabled = self.channels_enabled
        self.update_plot_layout()

    def update_time_scale(self):
        try:
            current_time_scale = float(self.time_scale_input.text())
            if current_time_scale <= 0:
                raise ValueError("Time must be a positive number.")
            self.max_time = current_time_scale
            self.time_scale_display_label.setText(f"Time: {current_time_scale} s")
            # Update the x-axis range
            for plot in self.plots.values():
                plot.setXRange(0, self.max_time)
            # Trim the data according to the new time scale
            self.trim_data_buffers()
        except Exception as e:
            print(f"Error updating time scale: {e}")

    def update_voltage_scale(self):
        try:
            current_voltage_scale = float(self.voltage_scale_input.text())
            if current_voltage_scale <= 0:
                raise ValueError("Voltage must be a positive number.")
            self.voltage_scale_display_label.setText(f"Voltage: {current_voltage_scale} V")
            # Update the y-axis range
            for plot in self.plots.values():
                plot.setYRange(-current_voltage_scale, current_voltage_scale)
            # Update the trigger line
            self.update_trigger_line()
        except Exception as e:
            print(f"Error updating voltage scale: {e}")

    def toggle_acquisition(self):
        if self.acquiring:
            self.stop_acquisition()
            self.run_stop_button.setText("RUN")
        else:
            self.start_acquisition()
            self.run_stop_button.setText("STOP")

    def start_acquisition(self):
        if not self.acquiring:
            self.acquiring = True
            self.triggered = False
            self.data_generator.start()

    def stop_acquisition(self):
        if self.acquiring:
            self.acquiring = False
            self.data_generator.stop()

    def update_plot_layout(self):
        # Clear existing plots
        self.graphics_layout.clear()
        self.plots.clear()
        self.curves.clear()
        self.data_buffer.clear()
        self.trigger_line = None

        enabled_channels = [ch for ch in self.channels_enabled if self.channels_enabled[ch]]
        num_channels = len(enabled_channels)
        overlay = self.overlay_checkbox.isChecked()

        if num_channels == 0:
            return

        if overlay:
            # Single plot for all channels
            p = self.graphics_layout.addPlot()
            p.showGrid(x=True, y=True)
            p.setLabel('left', 'Voltage', units='V')
            p.setLabel('bottom', 'Time', units='s')
            self.plots['overlay'] = p
            for ch in enabled_channels:
                curve = p.plot(pen=pg.mkPen(color=self.get_channel_color(ch), width=1.5), name=f"Channel {ch}")
                self.curves[ch] = curve
                self.data_buffer[ch] = {'time': [], 'voltage': []}
            p.addLegend()
        else:
            # Separate plot for each channel
            for idx, ch in enumerate(enabled_channels):
                p = self.graphics_layout.addPlot(row=idx, col=0)
                p.showGrid(x=True, y=True)
                p.setTitle(f"Channel {ch}")
                p.setLabel('left', 'Voltage', units='V')
                p.setLabel('bottom', 'Time', units='s')
                self.plots[ch] = p
                self.curves[ch] = p.plot(pen=pg.mkPen(color=self.get_channel_color(ch), width=1.5))
                self.data_buffer[ch] = {'time': [], 'voltage': []}

        # Add trigger line
        self.update_trigger_line()

    def get_channel_color(self, ch):
        colors = {'A': 'r', 'B': 'g', 'C': 'b', 'D': 'y'}
        return colors.get(ch, 'w')

    def update_graph(self, time, data):
        # Handle trigger mode
        if self.trigger_mode != 'AUTO' and not self.triggered:
            if self.check_trigger():
                self.triggered = True
                if self.trigger_mode == 'SINGLE':
                    # Record data from the trigger point for the defined time scale
                    self.reset_data_buffers()
                    self.trigger_time = time
                    # Continue sampling until time window is filled
                    self.stop_after_trigger = True
            else:
                return  # Do not update graphs until trigger occurs

        for ch in data:
            if ch in self.data_buffer:
                self.data_buffer[ch]['time'].append(time)
                self.data_buffer[ch]['voltage'].append(data[ch])

                # Remove old data beyond the time scale
                while self.data_buffer[ch]['time'] and (time - self.data_buffer[ch]['time'][0]) > self.max_time:
                    self.data_buffer[ch]['time'].pop(0)
                    self.data_buffer[ch]['voltage'].pop(0)

                curve = self.curves.get(ch)
                if curve:
                    curve.setData(self.data_buffer[ch]['time'], self.data_buffer[ch]['voltage'])
                    # Update x-axis range so that the graph scrolls with time
                    self.update_plot_x_range(ch)

        # After filling time window in SINGLE mode, stop the sampling
        if self.trigger_mode == 'SINGLE' and self.triggered and self.stop_after_trigger:
            if (time - self.trigger_time) >= self.max_time:
                self.stop_acquisition()
                self.run_stop_button.setText("RUN")
                self.stop_after_trigger = False

        # Update measurements
        self.update_measurements()

    def reset_data_buffers(self):
        for ch in self.data_buffer:
            self.data_buffer[ch]['time'] = []
            self.data_buffer[ch]['voltage'] = []

    def update_plot_x_range(self, ch):
        if not self.data_buffer[ch]['time']:
            return
        current_time = self.data_buffer[ch]['time'][-1]
        start_time = current_time - self.max_time
        plot = self.plots.get(ch if not self.overlay_checkbox.isChecked() else 'overlay')
        if plot:
            plot.setXRange(start_time, current_time)

    def trim_data_buffers(self):
        for ch in self.data_buffer:
            times = self.data_buffer[ch]['time']
            voltages = self.data_buffer[ch]['voltage']
            if times:
                current_time = times[-1]
                indices = [i for i, t in enumerate(times) if current_time - t <= self.max_time]
                self.data_buffer[ch]['time'] = [times[i] for i in indices]
                self.data_buffer[ch]['voltage'] = [voltages[i] for i in indices]
                curve = self.curves.get(ch)
                if curve:
                    curve.setData(self.data_buffer[ch]['time'], self.data_buffer[ch]['voltage'])
                self.update_plot_x_range(ch)

    def update_measurements(self):
        for measurement, widget in self.measurement_widgets:
            if measurement.measurement_type == "Delay":
                # Measure delay between channels with specified edges
                ch1, ch2 = measurement.channels
                edge1 = measurement.params['edge1']
                edge2 = measurement.params['edge2']
                time1 = self.find_edge_time(ch1, edge1)
                time2 = self.find_edge_time(ch2, edge2)
                if time1 is not None and time2 is not None:
                    delay = abs(time2 - time1)
                    measurement.result = f"{delay:.3f} s"
                else:
                    measurement.result = "Edge not found"
            elif measurement.measurement_type == "Frequency":
                # Calculate frequency
                ch = measurement.channels[0]
                freq = self.calculate_frequency(ch)
                if freq is not None:
                    measurement.result = f"{freq:.2f} Hz"
                else:
                    measurement.result = "Cannot calculate"
            elif measurement.measurement_type == "Average Voltage":
                # Calculate average voltage
                ch = measurement.channels[0]
                voltages = self.data_buffer.get(ch, {}).get('voltage', [])
                if voltages:
                    avg_voltage = np.mean(voltages)
                    measurement.result = f"{avg_voltage:.2f} V"
                else:
                    measurement.result = "No data"
            widget.update_result()

    def find_edge_time(self, channel, edge):
        data = self.data_buffer.get(channel, {})
        voltages = data.get('voltage', [])
        times = data.get('time', [])
        if voltages:
            if edge == 'RISING':
                for i in range(1, len(voltages)):
                    if voltages[i-1] < 0 and voltages[i] >= 0:
                        return times[i]
            elif edge == 'FALLING':
                for i in range(1, len(voltages)):
                    if voltages[i-1] > 0 and voltages[i] <= 0:
                        return times[i]
        return None

    def calculate_frequency(self, channel):
        data = self.data_buffer.get(channel, {})
        voltages = data.get('voltage', [])
        times = data.get('time', [])
        if voltages:
            crossings = []
            for i in range(1, len(voltages)):
                if voltages[i-1] < 0 and voltages[i] >= 0:
                    crossings.append(times[i])
            if len(crossings) >= 2:
                periods = [crossings[i+1] - crossings[i] for i in range(len(crossings)-1)]
                avg_period = np.mean(periods)
                frequency = 1 / avg_period if avg_period != 0 else None
                return frequency
        return None

    def change_trigger_mode(self, mode):
        self.trigger_mode = mode
        self.triggered = False  # Reset trigger
        if mode == 'SINGLE':
            self.stop_acquisition()
            self.run_stop_button.setText("RUN")

    def change_trigger_channel(self, channel):
        self.trigger_channel = channel
        self.update_trigger_line()

    def change_trigger_level(self):
        try:
            level = float(self.trigger_level_input.text())
            self.trigger_level = level
            self.update_trigger_line()
        except ValueError:
            print("Trigger level must be a number.")

    def change_trigger_edge(self, edge):
        self.trigger_edge = edge

    def check_trigger(self):
        data = self.data_buffer.get(self.trigger_channel, {})
        voltages = data.get('voltage', [])
        if voltages:
            if self.trigger_edge == "RISING" and voltages[-2] < self.trigger_level <= voltages[-1]:
                return True
            elif self.trigger_edge == "FALLING" and voltages[-2] > self.trigger_level >= voltages[-1]:
                return True
        return False

    def update_trigger_line(self):
        # Remove the previous trigger line
        if self.trigger_line:
            for plot in self.plots.values():
                plot.removeItem(self.trigger_line)
        # Add new trigger line
        level = self.trigger_level
        color = 'magenta'
        self.trigger_line = pg.InfiniteLine(pos=level, angle=0, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine))
        if self.overlay_checkbox.isChecked():
            plot = self.plots.get('overlay')
            if plot:
                plot.addItem(self.trigger_line)
        else:
            plot = self.plots.get(self.trigger_channel)
            if plot:
                plot.addItem(self.trigger_line)

    def closeEvent(self, event):
        self.stop_acquisition()
        event.accept()  # Close the application

class AddMeasurementDialog(QtWidgets.QDialog):
    def __init__(self, channels, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Measurement")
        self.channels = channels
        self.measurement = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Measurement type selection
        self.measurement_type_combo = QtWidgets.QComboBox()
        self.measurement_type_combo.addItems(["Delay", "Frequency", "Average Voltage"])
        layout.addWidget(QtWidgets.QLabel("Select Measurement Type:"))
        layout.addWidget(self.measurement_type_combo)

        # Parameters area
        self.params_widget = QtWidgets.QWidget()
        self.params_layout = QtWidgets.QFormLayout()
        self.params_widget.setLayout(self.params_layout)
        layout.addWidget(self.params_widget)

        # OK/Cancel buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.measurement_type_combo.currentTextChanged.connect(self.update_params)

        self.update_params()

    def update_params(self):
        # Clear old parameters
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        measurement_type = self.measurement_type_combo.currentText()

        if measurement_type == "Delay":
            self.channel_combo1 = QtWidgets.QComboBox()
            self.channel_combo1.addItems(self.channels)
            self.edge_combo1 = QtWidgets.QComboBox()
            self.edge_combo1.addItems(["RISING", "FALLING"])

            self.channel_combo2 = QtWidgets.QComboBox()
            self.channel_combo2.addItems(self.channels)
            self.edge_combo2 = QtWidgets.QComboBox()
            self.edge_combo2.addItems(["RISING", "FALLING"])

            self.params_layout.addRow("Channel 1:", self.channel_combo1)
            self.params_layout.addRow("Edge 1:", self.edge_combo1)
            self.params_layout.addRow("Channel 2:", self.channel_combo2)
            self.params_layout.addRow("Edge 2:", self.edge_combo2)

        elif measurement_type == "Frequency":
            self.channel_combo = QtWidgets.QComboBox()
            self.channel_combo.addItems(self.channels)
            self.params_layout.addRow("Channel:", self.channel_combo)

        elif measurement_type == "Average Voltage":
            self.channel_combo = QtWidgets.QComboBox()
            self.channel_combo.addItems(self.channels)
            self.params_layout.addRow("Channel:", self.channel_combo)

    def get_measurement(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Measurement Name", "Enter name for measurement:")
        if not ok or not name:
            return None

        measurement_type = self.measurement_type_combo.currentText()
        params = {}
        channels = []

        if measurement_type == "Delay":
            ch1 = self.channel_combo1.currentText()
            edge1 = self.edge_combo1.currentText()
            ch2 = self.channel_combo2.currentText()
            edge2 = self.edge_combo2.currentText()
            channels.extend([ch1, ch2])
            params['edge1'] = edge1
            params['edge2'] = edge2

        elif measurement_type == "Frequency":
            ch = self.channel_combo.currentText()
            channels.append(ch)

        elif measurement_type == "Average Voltage":
            ch = self.channel_combo.currentText()
            channels.append(ch)

        return Measurement(name, measurement_type, channels, params)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimeScopeApp()
    window.show()
    sys.exit(app.exec_())
