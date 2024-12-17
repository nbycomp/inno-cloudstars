import json
import requests
import sys
import os
import re

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)
queries_path = os.path.join(project_root, "decision_engine", "config", "queries.json")
# Load the queries from the JSON file
with open(queries_path, "r") as file:
    queries = json.load(file)

# Prometheus server URL
prometheus_url = "http://localhost:9090/api/v1/query"

# Function to fetch data from Prometheus
def fetch_prometheus_data(query):
    try:
        response = requests.get(prometheus_url, params={"query": query})
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("result", [])
        else:
            print(f"Failed to fetch data for query: {query}")
            print(f"HTTP Status Code: {response.status_code}, Response: {response.text}")
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Iterate through the queries and fetch results
for query_name, query in queries.items():
    print(f"Fetching data for: {query_name}")
    results = fetch_prometheus_data(query)
    print(f"Results for {query_name}:")
    for result in results:
        print(result)
    print("-" * 50)