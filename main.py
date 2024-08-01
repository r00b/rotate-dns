import requests
from dotenv import load_dotenv
import os

load_dotenv()

api_url = "https://api.dreamhost.com/"
api_key = os.getenv("DREAMHOST_API_KEY")


def get_external_ip():
    try:
        ip_response = requests.get('https://api.ipify.org?format=json')
        ip_info = ip_response.json()
        return ip_info['ip']
    except requests.RequestException as e:
        return f"Error: {e}"


external_ip = get_external_ip()


def list_dns_records():
    params = {
        "key": api_key,
        "cmd": "dns-list_records",
        "format": "tab"
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200 and response.text is not None:
        lines_array = response.text.strip().split('\n')
        lines_split = list(map(lambda n: n.split('\t'), lines_array[2:]))  # first two lines are headers
        records = {}
        for line in lines_split:
            record_name = line[2]
            record = {'record': record_name, 'type': line[3], 'value': line[4]}
            records[record_name] = record
        return records
    else:
        print(f"Failed to retrieve DNS records from DreamHost; status code={response.status_code}")
        return None


def perform_dns_command(command, record_name, record_type, record_value):
    params = {
        "key": api_key,
        "cmd": command,
        "record": record_name,
        "type": record_type,
        "value": record_value
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        print(f"Successfully performed {command}; record={record_name}, type={record_type}, value={record_value}")
        return True
    else:
        print(f"Failed to perform {command}; status code={response.status_code}")
        return False


def add_dns_record(record_name, record_type, record_value):
    return perform_dns_command("dns-add_record", record_name, record_type, record_value)


def remove_dns_record(record_name, record_type, record_value):
    return perform_dns_command("dns-remove_record", record_name, record_type, record_value)


def check_and_rotate_dns_record(record_to_update):
    print(f'Checking {record_to_update} for DNS updates')
    dns_records = list_dns_records()
    if dns_records is not None:
        existing_record = None
        # find the record to update
        for key, value in dns_records.items():
            if value['record'] == record_to_update and value['type'] == 'A':
                existing_record = value
                break
        if existing_record is None:
            print("Failed to find record to update, creating a new one")
            return add_dns_record(record_to_update, 'A', external_ip)
        else:
            # rotate the record
            print('Found record to update: ' + str(existing_record))
            existing_record_name = existing_record['record']
            existing_record_type = existing_record['type']
            existing_record_ip = existing_record['value']
            if existing_record['value'] != external_ip:
                print('IP has drifted from ' + existing_record['value'] + ' to ' + external_ip)
                removed = remove_dns_record(existing_record_name, existing_record_type, existing_record_ip)
                if removed:
                    return add_dns_record(existing_record_name, existing_record_type, external_ip)

            else:
                print('IP has not drifted, exiting')
    return False


result = check_and_rotate_dns_record(os.getenv("RECORD_TO_UPDATE"))
if result:
    print('Successfully rotated DNS record')
