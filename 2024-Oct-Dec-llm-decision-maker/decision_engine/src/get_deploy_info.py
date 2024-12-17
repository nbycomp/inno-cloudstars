import os
import json
import subprocess


class DataFetcher:
    def __init__(self):
        self.parent_path = self._get_parent_path()

    def _get_parent_path(self):
        """Returns the parent path of the current script."""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _run_script(self, script_name, value=None):
        """
        Executes a Python script located in the utils directory with an optional argument.
        
        Args:
            script_name (str): Name of the script to run.
            value (str): Optional argument to pass to the script.
        
        Returns:
            str: Output from the script if successful, None otherwise.
        """
        script_path = os.path.join(self.parent_path, "utils", script_name)
        command = ["python", script_path]
        if value:
            command.append(value)

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Script {script_name} failed with error: {e.stderr.strip()}")
        except FileNotFoundError:
            print(f"Script {script_path} not found.")
        except Exception as e:
            print(f"Unexpected error executing {script_name}: {e}")
        return None

    def _parse_json_response(self, response, key="Response:", index=2):
        """
        Parses a JSON response string split by a keyword and converts the desired part to JSON.
        
        Args:
            response (str): The full response string.
            key (str): The keyword to split the string on.
            index (int): The index of the split parts to parse as JSON.
        
        Returns:
            list: Parsed JSON as a list, or an empty list if parsing fails.
        """
        try:
            parts = response.split(key)
            target_part = parts[index].strip() if len(parts) > index else parts[1].strip()
            return json.loads(target_part)
        except (IndexError, json.JSONDecodeError) as e:
            print(f"Error parsing JSON response: {e}")
        return []

    def _extract_sites_and_device_meta_ids(self, data):
        """
        Extracts site names and device meta IDs from a list of dictionaries.
        
        Args:
            data (list): List of dictionaries containing "sites" and "device_metas".
        
        Returns:
            tuple: A tuple containing a list of site names and a list of device meta IDs.
        """
        sites = []
        device_meta_ids = []

        for entry in data:
            sites.extend(entry.get("sites", []))
            device_meta_ids.extend(meta.get("id") for meta in entry.get("device_metas", []))

        return sites, device_meta_ids

    def get_marketplace_data(self):
        """
        Runs the marketplace script and returns the parsed JSON response.
        
        Returns:
            list: Parsed JSON data from the marketplace script.
        """
        script_name = "get_token_and_all_blockchart_in_marketplace.py"
        output = self._run_script(script_name)
        return self._parse_json_response(output) if output else []

    def get_site_name_and_id(self):
        """
        Retrieves site name and ID by executing a series of scripts to fetch organization and device data.
        
        Returns:
            tuple: Site display name and site ID, or None if retrieval fails.
        """
        devices = []
        sites = []
        sites_dic = {}
        script_name = "get_token_and_all_organizations.py"
        organizations_output = self._run_script(script_name)

        if not organizations_output:
            print("Failed to fetch organizations data.")
            return None

        parsed_data = self._parse_json_response(organizations_output)
        site_ids, device_meta_ids = self._extract_sites_and_device_meta_ids(parsed_data)

        for site_id in site_ids:
            site_output = self._run_script("get_token_and_one_site.py", site_id)
            if not site_output:
                print(f"Failed to retrieve data for device ID: {site_id}")
                continue

            site_data = self._parse_json_response(site_output)
            sites.append(site_data)
            sites_dic[site_id] = site_data

        for device_id in device_meta_ids:
            device_output = self._run_script("get_token_and_one_device.py", device_id)
            if not device_output:
                print(f"Failed to retrieve data for device ID: {device_id}")
                continue

            device_data = self._parse_json_response(device_output)
            devices.append(device_data)

            device_data = self._parse_json_response(device_output)
            devices.append(device_data)
        data = {
        "devices": devices,
        "sites": sites,
        "organizations": organizations_output
    }
        return data
    
    def fetch_services(self):
        services_output = self._run_script("get_token_and_all_services.py")
        services_data = self._parse_json_response(services_output)
        return services_data


    def deploy(self,data):

        self._run_script("get_token_and_post_one_service.py", data)

    
    def delete_service(self, service_id):
        self._run_script("get_token_and_delete_one_service.py", service_id)



    