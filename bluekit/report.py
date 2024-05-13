import json
import logging
import re
from tabulate import tabulate
from colorama import Fore, Back, Style, init

from pathlib import Path


from bluekit.constants import RETURN_CODE_ERROR, RETURN_CODE_NONE_OF_4_STATE_OBSERVED, RETURN_CODE_NOT_VULNERABLE, RETURN_CODE_UNDEFINED, RETURN_CODE_VULNERABLE
from bluekit.constants import TARGET_DIRECTORY, REPORT_OUTPUT_FILE, SKIP_DIRECTORIES, TOOLKIT_BLUEEXPLOITER_INSTALLATION_DIRECTORY, MAX_CHARS_DATA_TRUNCATION
from bluekit.constants import OUTPUT_DIRECTORY, BLUING_BR_LMP, REGEX_BT_MANUFACTURER, REGEX_BT_VERSION, MACHINE_READABLE_REPORT_OUTPUT_FILE
from bluekit.factories.exploitfactory import ExploitFactory


def report_data(code, data):
    logging.info("BLUEEXPLOITER DATA: code={code}, data={data}".format(code=code, data=data))
    print("BLUEEXPLOITER DATA: code={code}, data={data}".format(code=code, data=data))

def report_not_vulnerable(data):
    report_data(RETURN_CODE_NOT_VULNERABLE, data)

def report_vulnerable(data):
    report_data(RETURN_CODE_VULNERABLE, data)

def report_none_of_4_state_observed(data):
    report_data(RETURN_CODE_NONE_OF_4_STATE_OBSERVED, data)

def report_error(data):
    report_data(RETURN_CODE_ERROR, data)

def report_undefined(data):
    report_data(RETURN_CODE_UNDEFINED, data)



class Report:
    def __init__(self):
        self.exploitFactory = ExploitFactory(TOOLKIT_BLUEEXPLOITER_INSTALLATION_DIRECTORY)

    def save_data(self, exploit_name, target, data, code):
        doc = {
            "code":code,
            "data": data 
        }
        logging.info("Rport - save_data -> document -> " + str(doc))

        jsonfile = open(REPORT_OUTPUT_FILE.format(target=target, exploit=exploit_name), 'w')
        json.dump(doc, jsonfile, indent=6)
        jsonfile.close()

    def read_data(self, exploit_name, target):
        logging.info("Loading report output data")
        path = REPORT_OUTPUT_FILE.format(target=target, exploit=exploit_name)
        if Path(path).exists():
            jsonfile = open(REPORT_OUTPUT_FILE.format(target=target, exploit=exploit_name),)
            doc = json.load(jsonfile)
            logging.info("Report output data is loaded")
            logging.info("Report - read_data -> document -> " + str(doc))
            return doc["code"], doc["data"]
        return None, None

    def get_done_exploits(self, target):
        path = Path(TARGET_DIRECTORY.format(target=target))
        exploits = [entry.name for entry in path.iterdir() if entry.is_dir() and entry.name not in SKIP_DIRECTORIES]
        logging.info("Extracted following completed exploits: " + str(exploits))
        return exploits

    def generate_report(self, target):
        done_exploits = self.get_done_exploits(target=target)
        all_exploits = self.exploitFactory.get_all_exploits()
        skipped_exploits = [exploit.name for exploit in all_exploits if exploit.name not in done_exploits]

        logging.info("Report.generate_report -> done_exploits = " + str(done_exploits))
        logging.info("Report.generate_report -> all_exploits = " + str(all_exploits))
        logging.info("Report.generate_report -> skipped_exploits = " + str(skipped_exploits))

        headers = ['Index', 'Exploit', 'Result', 'Data']
        table_data = []
        index = 1
        sorted_done_exploits = sorted(done_exploits, key=lambda x: x[2])
        for exploit in sorted_done_exploits:
            code, data = self.read_data(exploit_name=exploit, target=target)
            if code is None:
                code = RETURN_CODE_NONE_OF_4_STATE_OBSERVED
                data = "Error during loading the report"
            logging.info("data - " + str(data))
            if data is None:
                data = "Error with data"
            symbol = ''
            if code == RETURN_CODE_VULNERABLE:
                symbol = '❗'
            elif code == RETURN_CODE_ERROR or code == RETURN_CODE_NONE_OF_4_STATE_OBSERVED:
                symbol = '⚠️'
            
            if code == RETURN_CODE_VULNERABLE:
                table_data.append([index, f"{Fore.RED}{exploit}{Style.RESET_ALL}", f"{Fore.RED}Vulnerable{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            elif code == RETURN_CODE_NOT_VULNERABLE:
                table_data.append([index, f"{Fore.GREEN}{exploit}{Style.RESET_ALL}", f"{Fore.GREEN}Not vulnerable{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            elif code == RETURN_CODE_ERROR:
                table_data.append([index, f"{Fore.CYAN}{exploit}{Style.RESET_ALL}", f"{Fore.CYAN}Error{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            elif code == RETURN_CODE_UNDEFINED:
                table_data.append([index, f"{Fore.WHITE}{exploit}{Style.RESET_ALL}", f"{Fore.WHITE}Undefined{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            elif code == RETURN_CODE_NONE_OF_4_STATE_OBSERVED:
                table_data.append([index, f"{Fore.WHITE}{exploit}{Style.RESET_ALL}", f"{Fore.WHITE}Toolkit error{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            else:
                table_data.append([index, f"{Fore.WHITE}{exploit}{Style.RESET_ALL}", f"{Fore.WHITE}Toolkit error during report generation{symbol}{Style.RESET_ALL}", data[:MAX_CHARS_DATA_TRUNCATION]])
            index += 1
        for skipped_exploit in skipped_exploits:
            table_data.append([index, f"{Fore.WHITE}{skipped_exploit}{Style.RESET_ALL}", f"{Fore.WHITE}Not tested{Style.RESET_ALL}", ""])
            index += 1

        logging.info("Report.generate_report -> table_data = " + str(table_data))

        table = tabulate(table_data, headers, tablefmt='pretty', colalign=('center', 'left', 'left', 'left'))

        return table
    
    def get_manufacturer(self, target) -> str:
        file_path = Path(OUTPUT_DIRECTORY.format(target=target, exploit='recon') + BLUING_BR_LMP[1])
        if file_path.is_file():
            with file_path.open('r') as f:
                text = f.read()
                mm = re.compile(REGEX_BT_MANUFACTURER)
                output = mm.search(text).group()
                return output.split(":")[1].strip()
    
    def get_bt_version(self, target) -> float:
        file_path = Path(OUTPUT_DIRECTORY.format(target=target, exploit='recon') + BLUING_BR_LMP[1])
        if file_path.is_file():
            with file_path.open('r') as f:
                text = f.read()
                mm = re.compile(REGEX_BT_VERSION)
                output = mm.search(text).group()
                return float(output.split(" ")[3])

    def generate_machine_readable_report(self, target):
        done_exploits = self.get_done_exploits(target=target)
        all_exploits = self.exploitFactory.get_all_exploits()
        skipped_exploits = [exploit.name for exploit in all_exploits if exploit.name not in done_exploits]

        logging.info("Report.generate_report -> done_exploits = " + str(done_exploits))
        logging.info("Report.generate_report -> all_exploits = " + str(all_exploits))
        logging.info("Report.generate_report -> skipped_exploits = " + str(skipped_exploits))

        index = 1
        sorted_done_exploits = sorted(done_exploits, key=lambda x: x[2])

        output_json = {}
        sorted_done_exploits_json = []
        skipped_exploits_json = []
        for exploit in sorted_done_exploits:
            code, data = self.read_data(exploit_name=exploit, target=target)
            if code is None:
                code = RETURN_CODE_NONE_OF_4_STATE_OBSERVED
                data = "Error during loading the report"
            logging.info("data - " + str(data))
            sorted_done_exploits_json.append({
                "index": index,
                "name":exploit,
                "code": code,
                "data": data 
            })
            index += 1
        for skipped_exploit in skipped_exploits:
            skipped_exploits_json.append({
                "index": index,
                "name": skipped_exploit,
                "code": 6,
                "data": "Not tested"
            })
            index += 1
        
        output_json["done_exploits"] = sorted_done_exploits_json
        output_json["skipped_exploits"] = skipped_exploits_json
        output_json['manually_added_exploits'] = list()
        output_json["bt_version"] = self.get_bt_version(target=target)
        output_json['manufacturer'] = self.get_manufacturer(target=target)
        output_json['mac_address'] = target
        output_json['vehicle_name'] = ""
        output_json["vehicle manufacturer"] = ""
        output_json['parent_company'] = ""
        output_json["year_manufactured"] = 1
        
        jsonfile = open(MACHINE_READABLE_REPORT_OUTPUT_FILE.format(target=target), 'w')
        json.dump(output_json, jsonfile, indent=6)
        jsonfile.close()


if __name__ == "__main__":
    pass 


