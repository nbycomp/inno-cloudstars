import openai
import json
from pathlib import Path


class LLM_Agents:
    def __init__(self, key_file_path: str):
        """
        Initialize the LLM_Agents with the provided API key file path.
        """
        self.key_file_path = Path(key_file_path)

        # Load the API key from the file
        try:
            openai.api_key = self.key_file_path.read_text().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"The key file '{self.key_file_path}' was not found. Please ensure it exists.")
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading the API key: {e}")

        # Verify the key is loaded correctly
        if not openai.api_key:
            raise ValueError("API key is empty. Please check your key file.")

    def is_key_loaded(self) -> bool:
        """
        Verify if the API key has been successfully loaded.
        """
        return bool(openai.api_key)
    
    def user_intent_agent(self,user_input, services_str):
        prompt = f"""
                You are an assistant that extracts the user's intent and corrects any typos in the service name based on the available services.

                User Input: "{user_input}"

                Available Services: {services_str}

                Instructions:
                - Determine if the user wants to "deploy" or "delete" a service.
                - Identify the service name, correcting any typos to match the closest service in the available services.
                - If you correct a typo, suggest the corrected service name.

                Respond in JSON format:
                {{
                    "intent": "deploy" or "delete",
                    "service": "corrected service name",
                    "suggestion": "Did you mean 'corrected service name'?"
                }}

                If you cannot determine the intent or the service, set their values to null.
                """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You help users deploy or delete services, correcting typos in service names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        return response
    
    def ranking_agent(self, user_intent, cluster_data):
        """
        Use GPT to rank clusters based on user intent and metrics.
        """
        prompt = f"""
        The user wants to deploy a new service with the following details:
        {user_intent}

        Here is the data for available clusters:
        {json.dumps(cluster_data, indent=2)}

        Rank the clusters based on CPU usage, memory usage, and the user's intent.
        Provide a ranking and explanation for your choices.
        """
        response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert in cloud computing and resource optimization."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
        return response
    

    def extract_service_names(self, marketplace_data):
        """
        Extracts service names from marketplace data.
        
        :param marketplace_data: JSON data containing marketplace services.
        :return: List of service names as a JSON array.
        """
        # Prepare the prompt for the LLM
        prompt = f"""
    You are provided with marketplace data containing various services. Extract the list of service names from the data.

    Marketplace Data:
    {json.dumps(marketplace_data, indent=4)}

    Instructions:
    - Extract the names of all services from the marketplace data.
    - The service names may be found in fields like "name", "display_name", or "vendor" within each chart.
    - Provide the list of service names as a JSON array.

    Respond with:
    ["service_name1", "service_name2", "service_name3", ...]
    """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts service names from marketplace data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )

        print(response)

        return response
    

    def extract_sites_devices(self, data):
        """
        Extracts sites and associated devices from the given structured data.
        
        :param site_device_data: JSON data about organizations, sites, and devices.
        :return: JSON array with site and device information.
        """
        prompt = f"""
    Given the following structured data about organizations, sites, and devices, extract each site along with its associated devices (if any). For each site, indicate whether it has devices.

    Data:
    {json.dumps(data)}

    Please respond ONLY with a JSON array in the following format:

    [
    {{
        "site_id": "site_id1",
        "site_name": "site_name1",
        "device_name": "device1",
        "has_device": true
    }},
    {{
        "site_id": "site_id2",
        "site_name": "site_name2",
        "device_name": "",
        "has_device": false
    }}
    ...
    ]

    Do not include any explanations or additional text.
    """
        
        # Define the function schema for function calling
        functions = [
            {
                "name": "store_sites_devices",
                "description": "Stores sites and devices information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sites": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "site_id": {"type": "string"},
                                    "site_name": {"type": "string"},
                                    "devices": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "has_device": {"type": "boolean"}
                                },
                                "required": ["site_id", "site_name", "has_device"]
                            }
                        }
                    },
                    "required": ["sites"]
                }
            }
        ]
        
        # Send the request to the chat model using the function calling feature
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            functions=functions,
            function_call={"name": "store_sites_devices"},
            max_tokens=500,
            temperature=0
        )
        return response

    def extract_service_name_id(data):
        # The prompt to ask the model to extract relevant information
        prompt = f"""
        Given the following structured data about services extract each serviceChain name and id. For each serviceChain.

        Data:
        {json.dumps(data)}

        Please respond ONLY with a JSON array in the following format:

        [
        {{
            "name": "string",
            "id": "string"
        }},
        ...
        ]

        Do not include any explanations or additional text.
        """
        # Send the request to the chat model
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0
        )
        return response


    def generate_action_file_agent(self, template, values_dict):
        """
        Reads a template JSON file, fills it with values from a dictionary using GPT-3.5 Turbo,
        and writes the result to a new JSON file.
        """
        # Convert the template JSON and dictionary into a prompt
        prompt = (
            "Given the following JSON structure template and a dictionary of values, "
            "fill the template with values from the dictionary. "
            "Ensure that values match the dictionary exactly, especially for 'site_id'. "
            "Use the exact format of the template JSON.\n\n"
            f"Template JSON:\n{json.dumps(template, indent=2)}\n\n"
            f"Values Dictionary:\n{json.dumps(values_dict, indent=2)}\n\n"
            "Resulting JSON with values filled:"
        )
        # Call the GPT-3.5 Turbo model
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that works with JSON data."},
                {"role": "user", "content": prompt},
            ],
            temperature=0
        )
        return response
    

if __name__ == "__main__":
    key_file_path = Path(__file__).parent / "decision_engine/config/key.txt"
    try:
        agent = LLM_Agents(key_file_path)
        if agent.is_key_loaded():
            print("API key loaded successfully.")
    except Exception as e:
        print(f"Error: {e}")
