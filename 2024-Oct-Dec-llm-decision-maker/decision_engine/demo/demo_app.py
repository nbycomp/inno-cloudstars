import streamlit as st
import sys
import os

import pandas as pd
import os
import json
from datetime import datetime


# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)


import decision_engine.utils.utils as utils
   

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
if "market_services" not in st.session_state:
    st.session_state.market_services = []
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
if "user_services_names" not in st.session_state:
    st.session_state.user_services_names = ["Select"]
if "email" not in st.session_state:
    st.session_state.email = ""
if "selected_service_to_delete" not in st.session_state:
    st.session_state.selected_service_to_delete = ""
if "generated_json" not in st.session_state:
    st.session_state.generated_json = {}
if "val_dict" not in st.session_state:
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
if "intent" not in st.session_state:
    st.session_state.intent = ""
if "sites_ids" not in st.session_state:
    st.session_state.sites_ids = {}  # Initialize sites as an empty list


# Function to render chat messages
def render_chat_messages():
    chat_container = st.container()  # Container for chat messages
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                st.chat_message("assistant").markdown(message["content"])
            elif message["role"] == "user":
                st.chat_message("user").markdown(message["content"])


# Function to validate email
def validate_email():
    st.session_state.messages, st.session_state.user_services_names, st.session_state.step, st.session_state.email = utils.validate_email(
        st.session_state.email_input, st.session_state.user_services_names, st.session_state.messages
        )


# Function to extract user intent
def extract_intent():
    st.session_state.input = st.session_state.action_input
    st.session_state.intent, st.session_state.step, st.session_state.market_services, st.session_state.messages, st.session_state.service, st.session_state.sites_ids, st.session_state.sites, st.session_state["correct_intent"] = utils.extract_intent(
        st.session_state.email, st.session_state.input, st.session_state.user_services_names, st.session_state.messages
        )

def handle_correction_confirmation():
    confirmation = st.session_state.confirmation_input.strip().lower()
    st.session_state.messages, st.session_state.step= utils.handle_correction_confirmation(confirmation, st.session_state.messages, st.session_state.intent, st.session_state.service, st.session_state.market_services)


def delete_service():
    st.session_state.selected_service_to_delete = st.session_state.deleted_service
    st.session_state.step, st.session_state.messages = utils.delete_service(st.session_state.selected_service_to_delete, st.session_state.messages) 

def save_action():
    status = st.session_state.intent
    long_memory_path = os.path.join(project_root, "decision_engine", "data", "memory.csv")
    short_memory = {
    "inpt": [st.session_state.get("input", {})],
    "email": [st.session_state.get("email", "")],
    "user_intent": [st.session_state.get("intent", "")],
    "selected_site": [st.session_state.get("selected_site", "")],
    "cpu_memory_details": [st.session_state.get("cpu_memory_details", {"cpu_limit": "", "cpu_request": "", "memory_limit": "", "memory_request": ""})],
    "selected_service": [st.session_state.get("selected_service", "")],
    "version": [st.session_state.get("blockChartVersion", "")],
    "service_name": [st.session_state.get("name", "")],
    "user_services_names": [st.session_state.get("user_services_names", [])],
    "messages": [st.session_state.get("messages", [])],
    "selected_service_to_delete": [st.session_state.get("selected_service_to_delete", "")],
    "generated_json_file" : [st.session_state.get("generated_json", {})],
    "status": status,
    "timestamp": datetime.utcnow().isoformat()  # Adding the timestamp as the last key

} 
    utils.save_action(short_memory, long_memory_path)

def get_cluster_metrics():
    queries_file_path = os.path.join(project_root, "decision_engine", "config", "queries.json")
    clusters_path = os.path.join(project_root, "decision_engine", "config", "prometheus_links_cluster.json")
    cluster_metrics = utils.get_cluster_metrics(clusters_path, queries_file_path)
    return cluster_metrics




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
            st.session_state.user_services_names,  # Use the initialized sites
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
            "user_intent": st.session_state.intent+ " "+ st.session_state.correct_intent,
            "resource_requirements": st.session_state.cpu_memory_details
        }

        # Convert combined input to a string or formatted JSON for the GPT prompt
        user_intent_with_resources = json.dumps(combined_input, indent=2)

        # Call rank_clusters
        llm_response = utils.rank_clusters(user_intent_with_resources, cluster_metrics) 

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
            print(st.session_state.sites_ids)
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
            st.session_state.generated_json = utils.fill_json_with_dict(template, val_dict)
            st.json(st.session_state.generated_json)
            # Pass the JSON data to the deploy function
            st.session_state.messages.append({"role": "assistant", "content": "Thank you! The process is complete."})
            submitted = st.form_submit_button("Submit")
            if submitted:
                utils.deploy_fetcher(json.dumps(st.session_state.generated_json, indent=2))
                save_action()
                st.write("Configuration complete!")

                st.session_state.step = "action"

    elif st.session_state.step == "delete":
        with st.form(key=f"form_step_{st.session_state.step}"):
            st.session_state.step = utils.delete(st.session_state.selected_service_to_delete)
            st.write("Configuration complete!")
            save_action()
            st.session_state.messages.append({"role": "assistant", "content": "Thank you! The process is complete."})
            submitted = st.form_submit_button("Refresh")
            if submitted:
                st.session_state.step = "action"
            