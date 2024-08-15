import json
from copy import deepcopy
import time
from DeviceManager import get_start_time_in_sec, get_start_time, KeySightScopeUSB
import os
import winshell
import webbrowser


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


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
        return str(e)


def get_bytes_range(bytes_string):
    if ":" in bytes_string:
        low_byte, high_byte = bytes_string.split(":")
    else:
        low_byte, high_byte = bytes_string, bytes_string
    reverse = 1
    if low_byte > high_byte:
        temp = low_byte
        low_byte = high_byte
        high_byte = temp
        reverse = -1
    return reverse, high_byte, low_byte


class Report:
    def __init__(self):
        self.test = None
        self.report = None
        self.table = None
        self.finale = 2
        self.init_report = load_config('info/init_report.json')
        self.init_table = load_config('info/init_table.json')
        self.init_test = load_config('info/init_test.json')

    def build(self, data=None):
        self.report = deepcopy(self.init_report)
        self.report["ResultStatus"] = self.finale
        self.report["test_name"] = self.init_report['test_name']
        self.report["StartTimeFormatted"] = get_start_time()
        self.report["project_name"] = "project"
        self.report["gui_type"] = "GUI_8_Relay"
        self.report["gui_ver"] = "1.0"

        self.table = deepcopy(self.init_table)
        self.table["GroupName"] = "Main"

    def build_new_table(self, table_name):
        if len(self.table["StepResults"]):
            self.report["GroupResults"].append(self.table)

        self.table = deepcopy(self.init_table)
        self.table["GroupName"] = table_name

    def build_new_test(self, data):
        self.test = deepcopy(self.init_test)
        self.test = data
        self.table["StepResults"].append(self.test)
        if self.test["ResultStatus"] == 1:
            self.finale = 1
            self.table["ResultStatus"] = 1
            self.table["NumOfFail"] += 1

    def save_report(self):
        self.report["ResultStatus"] = self.finale
        self.report["GroupResults"].append(self.table)
        original_file_path = 'info/reports/rafael.html'

        try:
            with open(original_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"Error: The file {original_file_path} was not found.")
            return
        except Exception as e:
            print(f"Unexpected error reading file {original_file_path}: {e}")
            return

        for i, line in enumerate(lines):
            if 'var obj =  paste_results_here' in line:
                formatted_json = json.dumps(self.report, indent=4)
                # Replace 'paste_results_here' with formatted_json and ensure it does not escape the quotes
                lines[i] = line.replace('paste_results_here', formatted_json)

        t = get_start_time_in_sec()
        new_file_path = f'info/reports/rafael_{t}.html'
        os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

        try:
            with open(new_file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            print(f"Report successfully saved to {new_file_path}")
        except Exception as e:
            print(f"Error writing to file {new_file_path}: {e}")
            return

        # Reset attributes
        self.test = None
        self.report = None
        self.table = None

        reports_dir_path = os.path.join(winshell.desktop(), "reports")
        os.makedirs(reports_dir_path, exist_ok=True)

        # Create the shortcut path within the "Reports" directory
        shortcut_path = os.path.join(reports_dir_path, f"ReportShortcut_{t}.lnk")

        # Create the shortcut
        with winshell.shortcut(shortcut_path) as shortcut:
            shortcut.path = os.path.abspath(new_file_path)
            shortcut.description = "Shortcut to the latest report"
            shortcut.working_directory = os.path.dirname(new_file_path)

        # Convert the shortcut path to a URL format and open it
        folder_url = 'file://' + shortcut_path.replace(os.sep, '/')
        webbrowser.open(folder_url)


class Script:
    def __init__(self, logger, tester="RelayCTRL"):
        self.port = None
        self.path = None
        self.scope = KeySightScopeUSB(logger)
        self.stop_flag = 1
        self.logger = logger
        self.last_line = None
        self.uuts = None
        self.cmd_button = []
        self.response = None
        self.report = Report()
        self.tester = tester
        self.peripheral = load_config('info/peripheral.json')
        self.relay_cmd = self.peripheral["ports"][self.tester]["script"]

    def run(self, line):
        if "REM" in line:
            return 1
        if "," in line:
            list_line = line.split(',')
        else:
            return 1
        if "#" in list_line[0]:
            return 1

        if "NEWTBL" in list_line[0].upper():
            self.report.build_new_table(list_line[1])
        elif "PS" in list_line[0].upper():
            self.logger.message(self.power_supply(list_line))
        elif list_line[0] in self.cmd_button:
            self.response = None
            self.logger.message(self.send_get_command(list_line[0:]))
        elif "DELAYMS" in list_line[0].upper():
            self.delay(list_line[1])
        elif "RELAY" in list_line[0].upper():
            self.logger.message(self.relay(relay_number=list_line[1], status=list_line[2]))
        elif "CHKMSGBYTE" in list_line[0].upper():
            self.logger.message(self.get_data_info(list_line[1:]))
        elif "SCP" in list_line[0].upper():
            self.logger.message(self.scope_scripts(list_line=list_line[0][3:], data=list_line[1:]))
        return self.stop_flag

    def power_supply(self, list_line):
        print(list_line)
        return list_line

    def scope_scripts(self, list_line, data):
        if "MEAS" in list_line.upper():
            self.scope.save_meas(scp_id=self.peripheral['scope'][list_line[0]])
        elif "M" in list_line.upper():
            self.get_scope_info(scp_id=self.peripheral['scope'][list_line[0]], index=[list_line[-1]], data=data)
        elif "LDSU" in list_line.upper():
            self.scope.load_setup(scp_id=self.peripheral['scope'][list_line[0]], file_path=data[0])
        elif "SING" in list_line.upper():
            self.scope.single(scp_id=self.peripheral['scope'][list_line[0]])
        elif "STOP" in list_line.upper():
            self.scope.stop(scp_id=self.peripheral['scope'][list_line[0]])
        elif "RST" in list_line.upper():
            self.scope.reset(scp_id=self.peripheral['scope'][list_line[0]])
        elif "SVSC" in list_line.upper():
            temp = self.path.split('/')
            self.path = "/".join(temp[:-1])
            self.scope.save_img(scp_id=self.peripheral['scope'][list_line[0]], path=self.path)
        elif "SAVE" in list_line.upper():
            self.scope.save_setup(scp_id=self.peripheral['scope'][list_line[0]])

    def relay(self, relay_number, status):
        relay = f"Relay{relay_number}_"
        try:
            if status == "1":
                relay += 'ON'
                return self.send_get_command([self.tester, self.relay_cmd[relay]])
            elif "0" in status:
                relay += 'OFF'
                return self.send_get_command([self.tester, self.relay_cmd[relay]])
            else:
                return f"Invalid arguments-{status} for the relay {relay_number} "
        except Exception as e:
            return f"Error Relay arguments-{e} "

    def send_get_command(self, line):
        # Prepare the hex string from the line argument, skipping the first item
        try:
            self.last_line = line
            hex_string = ''.join(hex_code.replace('x', '') for hex_code in line[1:])
            time.sleep(0.01)
            data_bytes = bytes.fromhex(hex_string)
        except Exception as e:
            self.logger.message(f'send_get_command fail {e}')
            data_bytes = bytes.fromhex(line[1].replace('x', '').replace(',', ''))

        try:
            self.port.send_packet(hex_string=','.join(line[1:]), button_name=line[0])
            return f"Send data {data_bytes} to {line[0]}"
        except Exception as e:
            return f"Error {e}, Send data {data_bytes} to {line[0]} Failed!"

    def delay(self, t):
        try:
            time.sleep(int(t) / 1000)
            self.logger.message(f"Initiate a {t} mS, delay")
        except Exception as e:
            self.logger.message(f"Error Initiate a {t} mS,{e}")

    def get_scope_info(self, scp_id, index, data):
        result = self.scope.get_measurement_results(scp_id=scp_id, index=int(index[0]))
        print(result)
        test_name, scale_factor, low_range, high_range, fail_mode = data[:5]
        t = get_start_time()
        results = {
            "StepName": test_name,
            "Description": fail_mode,
            "Min": str(float(low_range) / (10 ** int(scale_factor))).lower(),
            "Max": str(float(high_range) / (10 ** int(scale_factor))).lower(),
            "ResultStatus": 0,
            "Message": str(float(result) / (10 ** int(scale_factor))),
            "TestStart": t
        }
        min_val = float(low_range) / 10 ** int(scale_factor)
        max_val = float(high_range) / 10 ** int(scale_factor)
        if min_val <= float(result) / (10 ** int(scale_factor)) <= max_val:
            results["ResultStatus"] = 2
        else:
            self.report.init_report['ResultStatus'] = 'Fail'
            results["ResultStatus"] = 3
            if int(fail_mode) == 1:
                self.stop_flag = 0
                results["ResultStatus"] = 1

        self.report.build_new_test(results)

        return results

    def get_data_info(self, data):
        t = get_start_time()
        retry = 1
        test_name, msb, lsb, h_bit, l_bit, in_hex, scale_factor, signed, low_range, high_range, fail_mode = data[:11]
        reverse, high_byte, low_byte = get_bytes_range(f"{msb}:{lsb}")

        results = {
            "StepName": test_name,
            "Description": fail_mode,
            "Min": str(low_range).lower(),
            "Max": str(high_range).lower(),
            "ResultStatus": 0,
            "Message": "",
            "TestStart": t
        }
        try:
            for i in range(int(retry)):
                if self.response is None:
                    self.logger.message("No response re-sending massage")
                    self.send_get_command(self.last_line)
            list_bytes = [self.response[int(some_bit)] for some_bit in range(int(low_byte), int(high_byte) + 1)]
        except Exception as e:
            return f"Problem with response: {e}"

        if not len(list_bytes):
            return f"return list empty"

        data = extract_bits(list_bytes[::reverse], int(l_bit), int(h_bit))

        if int(in_hex):
            results["Message"] = hex(int(data))

            formatted_low_range = low_range
            formatted_high_range = high_range
            lower_bound = float(int(formatted_low_range, 16))
            upper_bound = float(int(formatted_high_range, 16))
        else:
            scale_factor_float = 1
            if float(scale_factor):
                scale_factor_float = float(scale_factor)
            lower_bound = float(low_range)
            upper_bound = float(high_range)
            results["Message"] = float(data) * scale_factor_float

        time.sleep(0.01)

        if lower_bound <= float(data) <= upper_bound:
            results["ResultStatus"] = 2
        else:
            self.report.init_report['ResultStatus'] = 'Fail'
            results["ResultStatus"] = 3
            if int(fail_mode) == 1:
                self.stop_flag = 0
                results["ResultStatus"] = 1

        self.report.build_new_test(results)

        return results
