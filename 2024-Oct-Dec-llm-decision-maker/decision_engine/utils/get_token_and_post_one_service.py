import os
import json
import sys
import requests


class KratosClient:
    def __init__(self, user_email, password, org, env_name):
        self.user_email = user_email
        self.password = password
        self.org = org
        self.env_name = env_name

        self.kratos_public = f"https://{self.env_name}.nearbycomputing.com/.ory/kratos/public"
        self.base_url = f"https://{self.env_name}.nearbycomputing.com/inno-nbi-api/"
        self.session_token = None

    def fetch_action_url(self) -> str:
        response = requests.get(f"{self.kratos_public}/self-service/login/api", headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json().get('ui', {}).get('action')

    def fetch_token(self, action_url: str) -> str:
        login_payload = {
            "identifier": self.user_email,
            "password": self.password,
            "method": "password",
            "org": self.org
        }
        response = requests.post(action_url, json=login_payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        self.session_token = response.json().get('session_token')
        return self.session_token

    def make_authenticated_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        if not self.session_token:
            raise ValueError("No session token available. Please fetch a token first.")

        headers = {
            "Authorization": f"Bearer {self.session_token}",
            "x-org": self.org,
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Check for command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python script.py '<JSON_DATA>'")
        sys.exit(1)

    # Load credentials from JSON file
    config_file = os.path.abspath(os.path.join(os.path.dirname("__file__"), "decision_engine/config/nbi_account_info.json"))
    print(config_file)
    with open(config_file, "r") as file:
        config = json.load(file)

    user_email = config.get("user_email")
    password = config.get("password")
    org = config.get("org")
    env_name = config.get("env_name")

    # Initialize the Kratos client
    kratos_client = KratosClient(user_email, password, org, env_name)
    action_url = kratos_client.fetch_action_url()
    session_token = kratos_client.fetch_token(action_url)
    print(f"Session Token: {session_token}")

    

    try:
        new_service_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"Invalid new service data JSON provided: {e}")
        sys.exit(1)
    try:
        new_service_data = json.loads(json.dumps(new_service_data))
    except (TypeError, json.JSONDecodeError) as e:
        print(f"Error in new_service_data format: {e}")
        sys.exit(1)
    print(new_service_data)


    # Log the corrected data
    print("Corrected JSON Data:")
    print(json.dumps(new_service_data, indent=4))

    # Make the POST request
    response = kratos_client.make_authenticated_request("POST", "services", data=new_service_data)
    print("Response:")
    print(json.dumps(response, indent=4))

    # Print the response in a prettier format
    print("Response:")
    print(json.dumps(response, indent=4))
