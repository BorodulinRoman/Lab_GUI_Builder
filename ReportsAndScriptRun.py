import json
from copy import deepcopy
from DeviceManager import get_start_time_in_sec, get_start_time
import os
import winshell
import webbrowser


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


class Report:
    def __init__(self):
        self.test = None
        self.report = None
        self.table = None
        self.finale = 2
        self.init_report = load_config('info/init_report.json')
        self.init_table = load_config('info/init_table.json')
        self.init_test = load_config('info/init_test.json')
        self.conf = load_config('info/conf.json')

    def build(self, data=None):
        print(data)
        self.report = deepcopy(self.init_report)
        self.report["ResultStatus"] = self.finale
        self.report["test_name"] = self.init_report['test_name']
        self.report["StartTimeFormatted"] = get_start_time()
        self.report["project_name"] = self.conf["title"]
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

        reports_dir_path = os.path.join(winshell.desktop(), "Reports")
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
