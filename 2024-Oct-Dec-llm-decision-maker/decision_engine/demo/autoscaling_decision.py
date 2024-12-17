import subprocess
import json
import openai
import os
import sys
from datetime import datetime
import pandas as pd
import requests

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

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
# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)
path_file = os.path.join(project_root, "decision_engine", "src")

# List of Prometheus URLs for each cluster
clusters = {
    "cluster1": "http://localhost:9090/api/v1/query",
    "cluster2": "http://localhost:9091/api/v1/query",
    "cluster3": "http://localhost:9092/api/v1/query",
}

# Path to the queries file
queries_file = os.path.join(project_root, "decision_engine", "config", "queries.json")

# Function to query Prometheus
def query_prometheus(prometheus_url, query):
    response = requests.get(prometheus_url, params={"query": query})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error querying Prometheus at {prometheus_url}: {response.status_code}")
        return None

# Preprocess metrics to summarize data
def preprocess_metrics(metrics_data):
    processed_data = {}
    for metric_name, result in metrics_data.items():
        if "data" in result and "result" in result["data"]:
            values = [float(item["value"][1]) for item in result["data"]["result"]]
            if values:
                processed_data[metric_name] = {
                    "average": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values),
                }
    return processed_data

# Downsample time-series data
def downsample_time_series(result):
    if "data" in result and "result" in result["data"]:
        time_series = [
            {"timestamp": item["value"][0], "value": float(item["value"][1])}
            for item in result["data"]["result"]
        ]
        df = pd.DataFrame(time_series)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        downsampled = df.resample("1min", on="timestamp").mean().to_dict(orient="records")
        return downsampled
    return []

# Function to run the Prometheus script for each cluster
def query_cluster_metrics(script_path, prometheus_url, queries_file):
    try:
        result = subprocess.run(
            ["python3", script_path, prometheus_url, queries_file],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Subprocess stdout for {prometheus_url}:{result.stdout}")  # Debug: Print stdout
        print(f"Subprocess stderr for {prometheus_url}:{result.stderr}")  # Debug: Print stderr
        if result.stdout.strip():  # Check if stdout is not empty
            return json.loads(result.stdout)  # Attempt to load JSON
        else:
            print(f"Warning: No JSON output from {prometheus_url}. Returning empty dict.")
            return {}
    except subprocess.CalledProcessError as e:
        print(f"Error querying {prometheus_url}: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError for {prometheus_url}: {e} | Raw output: {result.stdout}")
        return {}

# Function to pass aggregated data to OpenAI GPT
def make_decision_with_gpt( aggregated_data):

    prompt = f"""
    You are a cloud orchestration decision engine. Based on the following cluster metrics, decide whether to scale up, scale down, or maintain resources for each cluster. Provide a brief explanation for each decision.

    Metrics Data: {json.dumps(aggregated_data, indent=4)}
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message["content"]

if __name__ == "__main__":
    # Path to the existing script
    script_path = os.path.join(path_file, "get_prometheus_info.py")

    # API key for OpenAI


    # Aggregate metrics from all clusters
    aggregated_metrics = {}
    for cluster_name, prometheus_url in clusters.items():
        print(f"Querying metrics for {cluster_name}...")
        cluster_metrics = query_cluster_metrics(script_path, prometheus_url, queries_file)
        if cluster_metrics:
            aggregated_metrics[cluster_name] = cluster_metrics
        else:
            print(f"Warning: No metrics collected for {cluster_name}.")

    # Pass the aggregated metrics to OpenAI GPT for decision-making
    print("Passing data to GPT for decision-making...")
    decision = make_decision_with_gpt(aggregated_metrics)

    # Print the GPT's decision
    print("GPT Decision:")
    print(decision)