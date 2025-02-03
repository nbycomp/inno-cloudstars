import streamlit as st
import pandas as pd
import requests
import openai
import json
import sys
import os


import concurrent.futures


# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from decision_engine.src.get_deploy_info import DataFetcher
fetcher = DataFetcher()

# Define the path to your key file
key_file_path = os.path.join(os.path.dirname(__file__), "..", "config", "key.txt")

from decision_engine.utils.llm_agents import LLM_Agents
LLM = LLM_Agents(key_file_path)



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
    required_columns = {'email', 'service_name', 'status', 'timestamp'}
    if not required_columns.issubset(data.columns):
        print(f"Error: memory.csv must contain the following columns: {required_columns}")
        return []

    # Convert timestamp column to datetime for sorting
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Filter data for the given email
    user_services = data[data['email'] == email]

    if user_services.empty:
        print(f"No services found for email: {email}")
        return []

    # Get the most recent status for each service
    latest_status = user_services.sort_values(by='timestamp', ascending=False).drop_duplicates('service_name')

    # Filter only services that are still running
    running_services = latest_status[latest_status['status'] == 'running']['service_name'].tolist()

    print(f"Running services for {email}: {running_services}")
    return running_services


# Function to validate email and proceed
def validate_email(email_input, user_services, messages):
    step = ""
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
    return messages, user_services, step, email_input



def read_from_long_memory(email):
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
    response = LLM.extract_sites_devices(data)
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
        return []



# Define the parallel extraction function
def extract_intent(email, user_input, user_services, messages):
    sites = []
    sites_ids = {}
    user_services = ["Select"]
    services = get_running_services_for_user(email.lower())
    sites_ids, sites, step, messages, market_services = get_platform_info(messages) 
    print(services) 
    print(market_services) 

    if services:
        for service in services:
            user_services.append(service)
        messages.append(
            {"role": "assistant", "content": f"Services under {email}: {', '.join(services)}"}
        )
    else:
        messages.append({"role": "assistant", "content": "No services found for your email."})

    services_str = ', '.join(market_services)
    response = LLM.user_intent_agent(user_input, services_str)

    try:
        intent_data = response["choices"][0]["message"]["content"].strip()
        intent_dict = json.loads(intent_data)
        intent = intent_dict.get("intent")
        service = intent_dict.get("service")
        suggestion = intent_dict.get("suggestion")

        if intent and service:
            if intent == "deploy":
                if suggestion:
                    messages.append({"role": "assistant", "content": suggestion}) 
                    step = "confirm_correction"
                else:
                    check_service_in_marketplace(service, market_services, messages)
            elif intent == "delete":
                step = "select_service_to_delete"
            else:
                messages.append({"role": "assistant", "content": "Could not extract intent or service from your input. Please try again."})
    except json.JSONDecodeError:
        messages.append({"role": "assistant", "content": "Could not parse the response. Please try again."})

    return intent, step, market_services, messages, service, sites_ids, sites, suggestion



def get_platform_info( messages):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Run fetch_sites() and get_available_services( messages) in parallel
        future_sites = executor.submit(fetch_sites)
        future_market = executor.submit(get_available_services, messages)

        # Get results
        sites_ids, sites = future_sites.result()
        market_services, messages = future_market.result()

    step = "deploy"
    return sites_ids, sites, step, messages, market_services



# Function to get available services using LLM
def get_available_services(messages):
    marketplace_data = fetcher.get_marketplace_data()
    response = LLM.extract_service_names(marketplace_data)

    try:
        services_list = json.loads(response["choices"][0]["message"]["content"].strip())
        # Ensure all service names are in lowercase for consistency
        services = [service.lower() for service in services_list]
        # Remove duplicates
        services = list(set(services))
        print("services", services)
        return services, messages
    except json.JSONDecodeError:
        messages.append({"role": "assistant", "content": "Could not parse the service list from the marketplace data."})
        return [], messages


# Modify the check_service_in_marketplace function
def check_service_in_marketplace(service, market_services, messages):
    # Normalize input by converting to lowercase and stripping whitespaces
    normalized_service = service.lower().strip()

    # Check for a partial match in the services list
    if any(normalized_service in s.lower() for s in market_services): 
        messages.append({"role": "assistant", "content": f"The service '{service}' is available in the marketplace."})
    else:
        messages.append({"role": "assistant", "content": f"The service '{service}' is not available in the marketplace."})
    return messages


# Function to fetch sites
def fetch_sites():
    sites_ids = {}
    sites = []
    print("fetch sites")
    sites_devices = extract_sites_and_devices()
    print(sites_devices)
    for site in sites_devices:
        sites_ids[site['site_name']]= site['site_id']
        device = "None"
        if site['devices']:
            device = site['devices'][0]
        sites.append(site['site_name']+": " + device)
    return sites_ids, sites


def handle_correction_confirmation(confirmation, messages, user_intent, service, market_services):
    if confirmation in ["yes", "y"]:
        messages.append({"role": "assistant", "content": f"Great! Proceeding to {user_intent} '{service}'."})
        step = "deploy"
        check_service_in_marketplace(service, market_services, messages)
    else:
        messages.append({"role": "assistant", "content": "Please re-enter your action with the correct service name."})
        step = "action"
    return messages, step

# Assuming previous imports and initial code setup remain unchanged
def get_cluster_metrics(clusters_path, queries_file_path):
    with open(clusters_path, "r") as file:
        data = json.load(file)

    # Access the dictionary
    clusters = data["clusters"]
    queries = load_queries_from_file(queries_file_path)
    cluster_metrics = {}

    for cluster_name, prometheus_url in clusters.items():
        cluster_metrics[cluster_name] = {}

        for metric_name, query in queries.items():
            try:
                response = requests.get(prometheus_url, params={"query": query})
                response.raise_for_status()
                data = response.json()
                print(data)

                if "data" in data and "result" in data["data"] and data["data"]["result"]:
                    metric_value = data["data"]["result"][0]["value"][1]
                    cluster_metrics[cluster_name][metric_name] = float(metric_value)
                else:
                    cluster_metrics[cluster_name][metric_name] = None
            except Exception as e:
                cluster_metrics[cluster_name][metric_name] = f"Error: {str(e)}"
    return cluster_metrics


def rank_clusters(user_intent, cluster_data):
    try:
        response = LLM.ranking_agent(user_intent, cluster_data)
        print(response)
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {e}"
    

def load_queries_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            print(json.load(file))
            return json.load(file)
    except Exception as e:
        print(f"Error loading queries from file: {str(e)}")
        return {}


# Function to select a site
def delete_service(deleted_service, messages):
    messages.append({"role": "user", "content": f"Selected service to delete: {deleted_service}"})
    step = "delete"
    return step, messages




def fetch_ids_for_user_services():
    data = fetcher.fetch_services()
    response = LLM_Agents.extract_service_name_id(data) 
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

def delete(selected_service_to_delete):
    all_services = fetch_ids_for_user_services()
    print("All services:", all_services)
    
    service_id = all_services.get(selected_service_to_delete.lower())

    if not service_id:
        print(f"Service '{selected_service_to_delete}' not found.")
        return
    
    print(f"Deleting service with ID: {service_id}")
    fetcher.delete_service(service_id)
    step = "action"
    return step


def save_action(short_memory, long_memory_path):
    # Ensure user_intent is a string, not a list
    user_intent = short_memory["user_intent"]
    print("user intent")
    print(user_intent)

    # Check if the file exists
    file_exists = os.path.isfile(long_memory_path)
    if file_exists:
        try:
            data = pd.read_csv(long_memory_path)
        except pd.errors.EmptyDataError:
            data = pd.DataFrame()  # Initialize empty DataFrame if file is empty
    else:
        data = pd.DataFrame()  # Initialize empty DataFrame if file does not exist

    # DELETE action: Update status to "terminated"
    if user_intent[0] == "delete":
        if not data.empty:
            short_memory['status'] = "terminated"
        else:
            print("No data found in memory.csv to update.")
    # DEPLOY action: Append new row
    elif user_intent[0] == "deploy":
        short_memory['status'] = "running"
    print(short_memory)
    session_df = pd.DataFrame(short_memory)
    data = pd.concat([data, session_df], ignore_index=True)
    print(f"New record added with status 'running' for service '{st.session_state.service_name}'")

    # Save the updated data back to the CSV file
    data.to_csv(long_memory_path, index=False)


def fill_json_with_dict(template, values_dict):
    response = LLM.generate_action_file_agent(template, values_dict)
    # Extract the JSON result from the response
    filled_json = response['choices'][0]['message']['content']

    # Parse the generated JSON to ensure it's valid
    try:
        filled_json_data = json.loads(filled_json)
    except json.JSONDecodeError as e:
        raise ValueError("The response from GPT-3.5 was not valid JSON.") from e
    return filled_json_data
    

def deploy_fetcher(data):
    fetcher.deploy(data)
