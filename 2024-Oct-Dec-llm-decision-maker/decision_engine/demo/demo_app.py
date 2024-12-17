import streamlit as st
import sys
import os

import openai
import pandas as pd
import os
import json


# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)


import decision_engine.utils.utils as utils
   

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = "email"  # Start with email validation
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


# Function to validate email
def validate_email():
    st.session_state.messages, st.session_state.user_services, st.session_state.step, st.session_state.email = utils.validate_email(
        st.session_state.email_input, st.session_state.user_services, st.session_state.messages
        )


# Function to extract user intent
def extract_intent():
    user_input = st.session_state.action_input
    st.session_state.intent, st.session_state.step, st.session_state.messages,
    st.session_state.service, st.session_state.sites_ids, st.session_state.sites = utils.extract_intent(
        user_input, st.session_state.user_services, st.session_state.messages
        )

def handle_correction_confirmation():
    confirmation = st.session_state.confirmation_input.strip().lower()
    st.session_state.messages, st.session_state.step, st.session_state.sites_ids,
    st.session_state.sites = utils.handle_correction_confirmation(confirmation, st.session_state.messages)

# Function to fetch sites
def fetch_sites():
    st.session_state.sites = ["Site A", "Site B"]  # Replace with actual logic

# Function to handle CPU and memory submission
def handle_cpu_memory_submission():
    st.session_state.messages.append({"role": "assistant", "content": "CPU/Memory details saved."})
    st.session_state.step = "service_name"

# Function to handle service name submission
def handle_service_name_submission():
    st.session_state.service_name = st.session_state.service_name_input
    st.session_state.messages.append({"role": "assistant", "content": f"Service '{st.session_state.service_name}' saved."})
    st.session_state.step = "completed"

# Function to deploy a service
def deploy():
    st.session_state.messages.append({"role": "assistant", "content": "Deployment initiated."})

# Function to delete a service
def delete_service():
    st.session_state.messages.append({"role": "assistant", "content": "Service deletion initiated."})

# Function to save actions
def save_action():
    st.session_state.messages.append({"role": "assistant", "content": "Action saved to memory."})


st.title("NearbyOne Chatbot")

# Function to render chat messages
def render_chat_messages():
    for message in st.session_state.messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        st.chat_message(role).markdown(message["content"])

# Main UI Logic
render_chat_messages()

with st.container():
    if st.session_state.step == "email":
        st.text_input("Enter your email address:", key="email_input", on_change=validate_email)

    elif st.session_state.step == "action":
        st.text_input("Enter your action (e.g., deploy a service):", key="action_input", on_change=extract_intent)

    elif st.session_state.step == "select_site_to_deploy":
        st.selectbox("Select a site:", st.session_state.sites, key="site_selection", on_change=fetch_sites)

    elif st.session_state.step == "cpu_memory":
        with st.form(key="cpu_memory_form"):
            st.text_input("Enter CPU Limit:", key="cpu_limit")
            st.text_input("Enter CPU Request:", key="cpu_request")
            st.text_input("Enter Memory Limit:", key="memory_limit")
            st.text_input("Enter Memory Request:", key="memory_request")
            if st.form_submit_button("Submit"):
                handle_cpu_memory_submission()

    elif st.session_state.step == "service_name":
        st.text_input("Enter the service name:", key="service_name_input", on_change=handle_service_name_submission)

    elif st.session_state.step == "delete":
        delete_service()
        st.write("Service deleted!")
        save_action()

    elif st.session_state.step == "completed":
        deploy()
        save_action()
        st.write("Deployment completed!")
