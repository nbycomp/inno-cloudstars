import streamlit as st
import pandas as pd
import openai
import json
import sys
import os
import re
import requests

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from decision_engine.src.get_deploy_info import DataFetcher
fetcher = DataFetcher()

import decision_engine.utils.utils as utils
   


# Define the path to your key file
key_file_path = os.path.join(os.path.dirname(__file__), "key.txt")

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


# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = "email"  # Start with email validation
if "input" not in st.session_state:
    st.session_state.input = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sites_ids" not in st.session_state:
    st.session_state.sites_ids = {}  # Initialize sites as an empty list
if "sites" not in st.session_state:
    st.session_state.sites = ["Select"]
if "services" not in st.session_state:
    st.session_state.services = []
if "selected_site" not in st.session_state:
    st.session_state.selected_site = ""
if "cpu_memory_details" not in st.session_state:
    st.session_state.cpu_memory_details = {"cpu_limit": "", "cpu_request": "", "memory_limit": "", "memory_request": ""}
if "selected_service" not in st.session_state:
    st.session_state.selected_service = ""
if "version" not in st.session_state:
    st.session_state.version = ""
if "service_name" not in st.session_state:
    st.session_state.service_name = ""
if "user_services" not in st.session_state:
    st.session_state.user_services = ["Select"]
if "email" not in st.session_state:
    st.session_state.email = ""
if "user_intent" not in st.session_state:
    st.session_state.user_intent = ""
if "selected_service_to_delete" not in st.session_state:
    st.session_state.selected_service_to_delete = ""
if "st.session_state.generated_json" not in st.session_state:
    st.session_state.generated_json = {}
if "st.session_state.val_dict" not in st.session_state:
    st.session_state.val_dict = {}
if "name" not in st.session_state:
    st.session_state.name = ""
if "displayName" not in st.session_state:
    st.session_state.displayName = ""
if "blockChartName" not in st.session_state:
    st.session_state.blockChartName = ""
if "site_id" not in st.session_state:
    st.session_state.site_id = ""
if "blockChartVersion" not in st.session_state:
    st.session_state.blockChartVersion = ""
if "label" not in st.session_state:
    st.session_state.label = ""



# Function to render chat messages
def render_chat_messages():
    chat_container = st.container()  # Container for chat messages
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                st.chat_message("assistant").markdown(message["content"])
            elif message["role"] == "user":
                st.chat_message("user").markdown(message["content"])

################################# Email ####################################################



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
def validate_email():
    email = st.session_state.email_input.lower()
    if is_valid_email(email):
        st.session_state.email = email
        st.session_state.messages.append({"role": "assistant", "content": f"Email validated: {email}"})
        st.session_state.messages.append({"role": "assistant", "content": "What action would you like to take?"})
        st.session_state.step = "action"
    else:
        st.session_state.messages.append({"role": "assistant", "content": "Invalid email. Please try again."})

# GPT-based email validation
def is_valid_email(email):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that validates email addresses."},
            {"role": "user", "content": f"Is '{email}' a valid email address? Respond with 'Yes' or 'No'."}
        ],
        max_tokens=1,
        temperature=0,
    )
    return response["choices"][0]["message"]["content"].strip().lower() == "yes"


############################################# User Intent & Action #######################################################################3


# Modify the extract_intent function
def extract_intent():
    st.session_state.user_services = ["Select"]
    services = get_running_services_for_user(st.session_state.email.lower())
    print(services)
    

    if services:
        for service in services:
            st.session_state.user_services.append(service)
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Services under {st.session_state.email}: {', '.join(services)}"}
        )
    else:
        st.session_state.messages.append({"role": "assistant", "content": "No services found for your email."})
    user_input = st.session_state["action_input"]
    st.session_state.input = user_input
    services_str = ', '.join(st.session_state.services)

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

    try:
        intent_data = response["choices"][0]["message"]["content"].strip()
        intent_dict = json.loads(intent_data)
        intent = intent_dict.get("intent")
        service = intent_dict.get("service")
        suggestion = intent_dict.get("suggestion")

        st.session_state.user_intent = intent
        st.session_state.service = service
        print(intent)
        if intent and service:
            if intent == "deploy":
                if suggestion:
                    st.session_state.messages.append({"role": "assistant", "content": suggestion})
                    st.session_state["correct_intent"] = suggestion
                    st.session_state.step = "confirm_correction"
                else:
                    # st.session_state.step = "select_site_to_deploy"
                    # fetch_sites()
                    # check_service_in_marketplace()
                    deploy()
            elif intent == "delete":
                st.session_state.step = "select_service_to_delete"

            

        else:
            st.session_state.messages.append({"role": "assistant", "content": "Could not extract intent or service from your input. Please try again."})
    except json.JSONDecodeError:
        st.session_state.messages.append({"role": "assistant", "content": "Could not parse the response. Please try again."})



def deploy():
    fetch_sites()
    check_service_in_marketplace()
    st.session_state.step = "deploy"

    

# Assuming previous imports and initial code setup remain unchanged
def get_cluster_metrics():
    clusters = {
    "sepideh-laptop-edge2": "http://localhost:9090/api/v1/query",
    "sepideh-laptop-edge1": "http://localhost:9091/api/v1/query",
    "test-site": "http://localhost:9092/api/v1/query",
    "acens-nbc": "http://213.229.169.44:30090/"
}
    queries_file = os.path.join(project_root, "decision_engine", "config", "queries.json")
    queries = load_queries_from_file(queries_file)
    cluster_metrics = {}

    for cluster_name, prometheus_url in clusters.items():
        cluster_metrics[cluster_name] = {}

        for metric_name, query in queries.items():
            try:
                response = requests.get(prometheus_url, params={"query": query})
                response.raise_for_status()
                data = response.json()

                if "data" in data and "result" in data["data"] and data["data"]["result"]:
                    metric_value = data["data"]["result"][0]["value"][1]
                    cluster_metrics[cluster_name][metric_name] = float(metric_value)
                else:
                    cluster_metrics[cluster_name][metric_name] = None
            except Exception as e:
                cluster_metrics[cluster_name][metric_name] = f"Error: {str(e)}"

    return cluster_metrics


def rank_clusters(user_intent, cluster_data):
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
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in cloud computing and resource optimization."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {e}"
    
# Default JSON data


# Path to the queries file

def load_queries_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading queries from file: {str(e)}")
        return {}


def handle_correction_confirmation():
    confirmation = st.session_state.confirmation_input.strip().lower()
    if confirmation in ["yes", "y"]:
        st.session_state.messages.append({"role": "assistant", "content": f"Great! Proceeding to {st.session_state.user_intent} '{st.session_state.service}'."})
        # st.session_state.step = "select_site_to_deploy"
        # fetch_sites()
        # check_service_in_marketplace()
        deploy()

    else:
        st.session_state.messages.append({"role": "assistant", "content": "Please re-enter your action with the correct service name."})
        st.session_state.step = "action"

# Modify the check_service_in_marketplace function
def check_service_in_marketplace():
    services = utils.get_available_services()
        # Normalize input by converting to lowercase and stripping whitespaces
    normalized_service = st.session_state.service.lower().strip()

    # Check for a partial match in the services list
    if any(normalized_service in s.lower() for s in services): 
        st.session_state.messages.append({"role": "assistant", "content": f"The service '{st.session_state.service}' is available in the marketplace."})
    else:
        st.session_state.messages.append({"role": "assistant", "content": f"The service '{st.session_state.service}' is not available in the marketplace."})


############################################ Sites ########################################################################
# Function to fetch sites
def fetch_sites():
    print("fetch sites")
    sites_devices = extract_sites_and_devices()
    print(sites_devices)
    for site in sites_devices:
        st.session_state.sites_ids[site['site_name']]= site['site_id']
        device = "None"
        if site['devices']:
            device = site['devices'][0]
        st.session_state.sites.append(site['site_name']+": " + device)


def clean_data(data):
    # Clean 'organizations' key if it's a string containing JSON data
    if isinstance(data.get('organizations', ''), str):
        try:
            # Extract JSON string from 'organizations' value
            json_start = data['organizations'].find('[')
            json_str = data['organizations'][json_start:]
            data['organizations'] = json.loads(json_str)
        except json.JSONDecodeError:
            data['organizations'] = []
    return data

def extract_sites_and_devices():
    raw_data = fetcher.get_site_name_and_id()
    data = clean_data(raw_data)
    
    # The prompt to ask the model to extract relevant information
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
    
    try:
        # Extract the function call arguments
        function_call = response["choices"][0]["message"]["function_call"]
        arguments = json.loads(function_call["arguments"])
        sites_list = arguments["sites"]
    
        # Process the sites list
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
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Could not parse the sites list from the data: {str(e)}"
        })
        return []



########################################### Deploy ##################################################################
def apply_deploy(json_data):

    # Optionally, call the deploy method on the fetcher
    fetcher.deploy(json_data)


############################################################# Delete ##############################################

# Function to select a site
def delete_service():
    selected_service = st.session_state.deleted_service
    st.session_state.selected_service_to_delete = selected_service
    st.session_state.messages.append({"role": "user", "content": f"Selected service to delete: {selected_service}"})
    st.session_state.step = "delete"




def fetch_ids_for_user_services():
    data = fetcher.fetch_services()
    
    # Debug: Ensure data structure is as expected
    print("Fetched data:", json.dumps(data, indent=2))
    
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
    
    try:
        # Extract the JSON response
        content = response["choices"][0]["message"]["content"]
        services_list = json.loads(content)  # Parse JSON string into Python list
        
        # Map services into a dictionary
        services = {service["name"].lower(): service["id"] for service in services_list}
        return services
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing response: {e}")
        return {}

def delete():
    all_services = fetch_ids_for_user_services()
    print("All services:", all_services)
    
    service_id = all_services.get(st.session_state.selected_service_to_delete.lower())

    if not service_id:
        print(f"Service '{st.session_state.selected_service_to_delete}' not found.")
        return
    
    print(f"Deleting service with ID: {service_id}")
    fetcher.delete_service(service_id)
    st.session_state.step = "action"

def save_action():
    # Path to the CSV file
    memory_path = os.path.join(project_root, "decision_engine", "data", "memory.csv")

    # Check if the file exists
    file_exists = os.path.isfile(memory_path)
    if file_exists:
        try:
            # Load existing data
            data = pd.read_csv(memory_path)
        except pd.errors.EmptyDataError:
            data = pd.DataFrame()  # Initialize empty DataFrame if file is empty
    else:
        data = pd.DataFrame()  # Initialize empty DataFrame if file does not exist

    if st.session_state.user_intent == "delete":
        # Update the status of the service_name under the given email to "terminated"
        if not data.empty:
            mask = (data['email'] == st.session_state.email) & \
                   (data['service_name'] == st.session_state.selected_service_to_delete)
            if mask.any():
                data.loc[mask, 'status'] = "terminated"
                print(f"Service '{st.session_state.selected_service_to_delete}' status updated to 'terminated'")
            else:
                print(f"Service '{st.session_state.selected_service_to_delete}' not found for email '{st.session_state.email}'")
        else:
            print("No data found in memory.csv to update.")
    elif st.session_state.user_intent == "deploy":
        # Append new record with status "running"
        session_data = {
            "sites_ids": [st.session_state.get("sites_ids", {})],
            "sites": [st.session_state.get("sites", [])],
            "services": [st.session_state.get("services", [])],
            "selected_site": [st.session_state.get("selected_site", "")],
            "cpu_memory_details": [st.session_state.get("cpu_memory_details", {"cpu_limit": "", "cpu_request": "", "memory_limit": "", "memory_request": ""})],
            "selected_service": [st.session_state.get("selected_service", "")],
            "version": [st.session_state.get("blockChartVersion", "")],
            "service_name": [st.session_state.get("name", "")],
            "user_services": [st.session_state.get("user_services", [])],
            "email": [st.session_state.get("email", "")],
            "selected_service_to_delete": [st.session_state.get("selected_service_to_delete", "")],
            "status": "running"
        }
        session_df = pd.DataFrame(session_data)
        data = pd.concat([data, session_df], ignore_index=True)
        print(f"New record added with status 'running' for service '{st.session_state.service_name}'")

    # Save the updated data back to the CSV file
    data.to_csv(memory_path, index=False)


def fill_json_with_dict(template, values_dict):
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
    print("PPPPPPPPPP")
    print(prompt)
    # Call the GPT-3.5 Turbo model
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that works with JSON data."},
            {"role": "user", "content": prompt},
        ],
        temperature=0
    )

    # Extract the JSON result from the response
    filled_json = response['choices'][0]['message']['content']

    # Parse the generated JSON to ensure it's valid
    try:
        filled_json_data = json.loads(filled_json)
    except json.JSONDecodeError as e:
        raise ValueError("The response from GPT-3.5 was not valid JSON.") from e
    st.session_state.generated_json = filled_json_data


################################################### Main ############################################################


template = {
        "name": "",
        "blocks": [
            {
                "displayName": "",
                "blockChartName": "NginxSimpleContainer",
                "blockChartVersion": "0.1.0",
                "site_id": "",
                "values": """
Block:
  InstanceId: 12345678-9012-3456-7890-123456789012
deployments:
  nginx:
    configuration:
      chart:
        baseRegistryUrl: charts.bitnami.com
        name: nginx
        repo: bitnami
        version: 18.2.3
    values:
      service:
        httpsPort: 443
        port: 80
        type: NodePort
    variables:
      appname: nginx
placement:
  site:
    label: 
""" 
            }
        ]
    }


val_dict = {}
# Main UI Logic
st.title("NearbyOne Chatbot")

# Chatbox at the top
render_chat_messages()
# User input section (fixed at the bottom)
with st.container():
    if st.session_state.step == "email":
        st.text_input("Please enter your email address:", key="email_input", on_change=validate_email)

    elif st.session_state.step == "action":
        st.text_input("Please enter your action (e.g., deploy a service):", key="action_input", on_change=extract_intent)
    
    elif st.session_state.step == "confirm_correction":
        st.text_input(
            "Please confirm if this is correct (yes/no):",
            key="confirmation_input",
            on_change=handle_correction_confirmation,
        )

    elif st.session_state.step == "select_service_to_delete":
        st.selectbox(
            "Please select a service to delete:",
            st.session_state.user_services,  # Use the initialized sites
            key="deleted_service",
            on_change=delete_service,
        )

    elif st.session_state.step == "deploy":
        with st.form(key=f"form_step_{st.session_state.step}"):
            # Editable fields for the JSON
            st.subheader("Edit JSON Data")
            st.session_state["name"] = st.text_input("Name", value=template["name"])
            
            updated_blocks = []

            # Editable blocks{}
            st.session_state["displayName"]= st.text_input("Display Name", value=template["blocks"][0]["displayName"])
            st.session_state["blockChartName"]= st.text_input("Block Chart Name", value=template["blocks"][0]["blockChartName"])
            st.session_state["blockChartVersion"]= st.text_input("Block Chart Version", value=template["blocks"][0]["blockChartVersion"])

            submitted = st.form_submit_button("Submit")
            if submitted:
                st.session_state.step = "cpu_memory"

    elif st.session_state.step == "cpu_memory":
        with st.form(key=f"form_step_{st.session_state.step}"):

            cpu_limit = st.text_input("Enter CPU Limit:", value="500m")
            cpu_request = st.text_input("Enter CPU Request:", value="250m")
            memory_limit = st.text_input("Enter Memory Limit:", value="256Mi")
            memory_request = st.text_input("Enter Memory Request:", value="128Mi")

            # Save these values but don't add to the final JSON
            st.session_state.cpu_memory_details = {
                "cpu_limit": cpu_limit,
                "cpu_request": cpu_request,
                "memory_limit": memory_limit,
                "memory_request": memory_request
            }

            submitted = st.form_submit_button("Submit")
            if submitted:
                 st.session_state.step = "ranking"

    elif st.session_state.step == "ranking":
        cluster_metrics = get_cluster_metrics()
                # Combine user input with session state details
        combined_input = {
            "user_intent": st.session_state.user_intent+ " "+ st.session_state.correct_intent,
            "resource_requirements": st.session_state.cpu_memory_details
        }

        # Convert combined input to a string or formatted JSON for the GPT prompt
        user_intent_with_resources = json.dumps(combined_input, indent=2)

        # Call rank_clusters
        llm_response = rank_clusters(user_intent_with_resources, cluster_metrics) 

        # Save the response and metrics in session state
        st.session_state["llm_response"] = llm_response
        st.session_state["cluster_metrics"] = cluster_metrics

        # Display the LLM's recommendation if available
        if "llm_response" in st.session_state:
            st.text_area("Site Ranking and Explanation:", value=st.session_state["llm_response"], height=300)

        if "cluster_metrics" in st.session_state:
            ranked_sites = list(st.session_state["cluster_metrics"].keys())
            # Dropdown for site_id selection
            selected_site_name = st.selectbox(f"Select a new Site Name", options=st.session_state.sites_ids, index=0)
            print(st.session_state["name"],
                st.session_state["displayName"],
                st.session_state["blockChartName"],
                st.session_state["blockChartVersion"],
                st.session_state["site_id"],
                st.session_state["label"])

            # Automatically update `site_id` and `values` field
            st.session_state["site_id"] = st.session_state.sites_ids[selected_site_name]
            st.session_state["label"] =  st.session_state.sites_ids[selected_site_name]
        st.session_state.step = "generate_json"

    elif st.session_state.step == "generate_json":    
        with st.form(key=f"form_step_{st.session_state.step}"):
            val_dict = {
                "name":st.session_state["name"],
                "displayName":st.session_state["displayName"],
                "blockChartName":st.session_state["blockChartName"],
                "blockChartVersion":st.session_state["blockChartVersion"],
                "site_id":st.session_state["site_id"],
                "placement.site.label":st.session_state["label"]
            }
            print(val_dict)
            fill_json_with_dict(template, val_dict)
            st.json(st.session_state.generated_json)
            # Pass the JSON data to the deploy function
            st.session_state.messages.append({"role": "assistant", "content": "Thank you! The process is complete."})
            submitted = st.form_submit_button("Submit")
            if submitted:
                fetcher.deploy(json.dumps(st.session_state.generated_json, indent=2))
                save_action()
                st.write("Configuration complete!")

                st.session_state.step = "action"

    elif st.session_state.step == "delete":
        with st.form(key=f"form_step_{st.session_state.step}"):
            delete()
            st.write("Configuration complete!")
            save_action()
            st.session_state.messages.append({"role": "assistant", "content": "Thank you! The process is complete."})
            submitted = st.form_submit_button("Refresh")
            if submitted:
                st.session_state.step = "action"
            
