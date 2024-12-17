import streamlit as st
import pandas as pd
import openai
import json
import sys
import os

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from decision_engine.src.get_deploy_info import DataFetcher
fetcher = DataFetcher()

# Initialize model configuration
MODEL_NAME = "gpt-3.5-turbo"
PROMPT_FILE_PATH = os.path.join(project_root, "decision_engine", "config", "prompts.json")

# Load prompts from a JSON file
def load_prompts(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found at {file_path}.")
    except json.JSONDecodeError:
        raise ValueError("Error parsing the prompts JSON file.")

PROMPTS = load_prompts(PROMPT_FILE_PATH)

# Define the path to your key file
key_file_path = os.path.join(os.path.dirname(__file__), "..", "demo", "key.txt")


# Load the API key from the file
try:
    with open(key_file_path, "r") as key_file:
        openai.api_key = key_file.read().strip()
except FileNotFoundError:
    raise FileNotFoundError("The key.txt file is not found. Please ensure it exists in the script's directory.")
except Exception as e:
    raise RuntimeError(f"An error occurred while loading the API key: {e}")

# Verify the key is loaded correctly
if not openai.api_key:
    raise ValueError("API key is empty. Please check your key.txt file.")



# Chat with model
def chat_with_model(prompt_key, **kwargs):
    prompt_config = {prompt_key: PROMPTS.get(prompt_key)}
    print(prompt_config)
    if not prompt_config:
        raise ValueError(f"Prompt key '{prompt_key}' not found in the prompts file.")

    if isinstance(prompt_config, dict):
        prompt = prompt_config[prompt_key].format(**kwargs)
        function_schema = prompt_config.get("function_schema")
    else:
        prompt = prompt_config
        function_schema = None

    request_params = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": f"You are an assistant for {prompt_key.replace('_', ' ')}."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 500,
    }

    if function_schema:
        request_params["functions"] = [function_schema]
        request_params["function_call"] = {"name": function_schema["name"]}

    response = openai.ChatCompletion.create(**request_params)
    return response["choices"][0]["message"]



def get_running_services_for_user(email):
    # Path to the CSV file
    memory_path = os.path.join(project_root, "decision_engine", "data", "memory.csv")
    
    try:
        # Load the CSV file
        data = pd.read_csv(memory_path)
    except pd.errors.EmptyDataError:
        print("Error: memory.csv is empty.")
        return []

    # Check if required columns exist
    required_columns = {'email', 'service_name', 'status'}
    if not required_columns.issubset(data.columns):
        print(f"Error: memory.csv must contain the following columns: {required_columns}")
        return []

    # Filter records matching the email
    user_services = data[(data['email'] == email) & (data['status'] == 'running')]

    if not user_services.empty:
        # Extract and return all service names
        running_services = user_services['service_name'].tolist()
        print(f"Running services for {email}: {running_services}")
    else:
        running_services = []
        print(f"No running services found for email: {email}")
    
    return running_services



# Function to validate email and proceed
def validate_email(email_input, user_services, messages):
    step = ""
    if is_valid_email(email_input):
        email = email_input
        messages.append({"role": "assistant", "content": f"Email validated: {email_input}"})
        services = get_running_services_for_user(email_input.lower())
        print(services)
        if services:
            for service in services:
                user_services.append(service)
            messages.append(
                {"role": "assistant", "content": f"Services under {email_input}: {', '.join(services)}"}
            )
        else:
            messages.append({"role": "assistant", "content": "No services found for your email."})
        messages.append({"role": "assistant", "content": "What action would you like to take?"})
        step = "action"
    else:
        email = ""
        messages.append({"role": "assistant", "content": "Invalid email. Please try again."})
    return messages, user_services, step, email




# Email validation function
def is_valid_email(email):
    """
    Validates an email address using the "email_validation" prompt.
    """
    response = chat_with_model("email_validation", email=email)
    return response["content"].strip().lower() == "yes"



# Function to get available services using LLM
def get_available_services():
    marketplace_data = fetcher.get_marketplace_data()
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

    try:
        services_list = json.loads(response["choices"][0]["message"]["content"].strip())
        # Ensure all service names are in lowercase for consistency
        services = [service.lower() for service in services_list]
        # Remove duplicates
        services = list(set(services))
        print("services", services)
        return services
    except json.JSONDecodeError:
        st.session_state.messages.append({"role": "assistant", "content": "Could not parse the service list from the marketplace data."})
        return []


def extract_intent(user_input, messages):
    services = get_available_services() 
    services_str = ', '.join(services)
    print(services_str)
    response = chat_with_model("extract_intent", user_input=user_input, services_str=services_str)
    print(response)
    try:
        if "choices" in response:
            content = response["choices"][0]["message"]["content"].strip()
        elif "content" in response:
            content = response["content"].strip()
        else:
            raise ValueError(f"Unexpected response format: {response}")
        
        intent_data = json.loads(content)
        intent = intent_data.get("intent")
        service = intent_data.get("service")
        suggestion = intent_data.get("suggestion")

        if intent and service:
            # Handle intents and suggestions as needed
            if intent == "deploy":
                if suggestion:
                    messages.append({"role": "assistant", "content": suggestion})
                    step = "confirm_correction"
                else:
                    step = "select_site_to_deploy"
            elif intent == "delete":
                step = "select_service_to_delete"
        else:
            messages.append({"role": "assistant", "content": "Could not extract intent or service from your input. Please try again."})
            step = "action"
    except json.JSONDecodeError:
        messages.append({"role": "assistant", "content": "Could not parse the response. Please try again."})
        step = "action"
    print(step)
    return intent, step, messages, service, services



def handle_correction_confirmation(confirmation, messages, user_intent, service, services):
    if confirmation in ["yes", "y"]:
        messages.append({"role": "assistant", "content": f"Great! Proceeding to {user_intent} '{service}'."})
        step = "select_site_to_deploy"
        sites_ids, sites = fetch_sites(messages)
        messages = check_service_in_marketplace(service, messages, services)

    else:
        messages.append({"role": "assistant", "content": "Please re-enter your action with the correct service name."})
        step = "action"
    return messages, step, sites_ids, sites

# Modify the check_service_in_marketplace function
def check_service_in_marketplace(service, messages, services):
    if service.lower() in services:
        messages.append({"role": "assistant", "content": f"The service '{service}' is available in the marketplace."})
    else:
        messages.append({"role": "assistant", "content": f"The service '{service}' is not available in the marketplace."})
    return messages


def fetch_sites(messages):
    sites_ids = {}
    sites = []
    sites_devices = extract_sites_and_devices(messages)
    for site in sites_devices:
        sites_ids[site['site_name']] = site['site_id']
        device = "None"
        if site['devices']:
            device = site['devices'][0]
        sites.append(site['site_name']+": " + device)
    return sites_ids, sites

# Function to select a site
def select_site():
    selected_site = st.session_state.site_selection
    st.session_state.selected_site = selected_site
    st.session_state.messages.append({"role": "user", "content": f"Selected site: {selected_site}"})
    st.session_state.messages.append({"role": "assistant", "content": f"Site '{selected_site}' selected. Please provide CPU and Memory details."})
    st.session_state.step = "cpu_memory"



# Clean raw data for sites and devices
def clean_data(data):
    """
    Cleans raw data to ensure proper structure for site and device extraction.
    """
    if isinstance(data.get("organizations", ""), str):
        try:
            json_start = data["organizations"].find("[")
            json_str = data["organizations"][json_start:]
            data["organizations"] = json.loads(json_str)
        except json.JSONDecodeError:
            data["organizations"] = []
    return data



# Extract sites and devices function
def extract_sites_and_devices(messages):
    """
    Extracts site and device information using the "extract_sites" prompt and schema.
    """
    raw_data = fetcher.get_site_name_and_id()
    cleaned_data = clean_data(raw_data)

    response = chat_with_model("extract_sites", data=json.dumps(cleaned_data))
    if "function_call" in response:
        try:
            arguments = json.loads(response["function_call"]["arguments"])
            sites_list = arguments["sites"]
            sites = []
            for site in sites_list:
                site_id = site.get("site_id", "").lower()
                site_name = site.get("site_name", "").lower()
                devices = [device.lower() for device in site.get("devices", [])]
                has_device = site.get("has_device", False)
                sites.append({
                    "site_id": site_id,
                    "site_name": site_name,
                    "devices": devices,
                    "has_device": has_device
                })
        
            return sites
        except (KeyError, json.JSONDecodeError) as e:
            messages.append({
                "role": "assistant",
                "content": f"Could not parse the sites list from the data: {str(e)}"
            })
            return []





    
    
