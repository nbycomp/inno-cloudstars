import requests
import json
from datetime import datetime
import sys
import pandas as pd
import sys
import re
import os

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)
path_file = os.path.join(project_root, "decision_engine", "config")

# Function to query Prometheus
def query_prometheus(prometheus_url, query):
    response = requests.get(prometheus_url, params={"query": query})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error querying Prometheus: {response.status_code}")
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

# Collect metrics
def collect_metrics(prometheus_url, queries):
    results = {}
    for metric_name, query in queries.items():
        data = query_prometheus(prometheus_url, query)
        if data:
            results[metric_name] = data
    return results

# Save metrics to a JSON file
def save_metrics_to_json(data, filename):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = f"{filename}_{timestamp}.json"
    with open(filepath, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Metrics saved to {filepath}")

# At the end of your script
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <prometheus_url> <queries_file>")
        sys.exit(1)

    prometheus_url = sys.argv[1]  # Prometheus URL passed as an argument
    queries_file = os.path.join(path_file,sys.argv[2])  # JSON file with queries passed as an argument

    # Load queries from the JSON file
    try:
        with open(queries_file, "r") as file:
            queries = json.load(file)
    except FileNotFoundError:
        print("Error: JSON file not found.")
        exit(1)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON file.")
        exit(1)

    # Collect metrics from Prometheus
    metrics_data = collect_metrics(prometheus_url, queries)

    # Preprocess the metrics to summarize them
    summarized_metrics = preprocess_metrics(metrics_data)

    # Print summarized metrics as JSON
    print(json.dumps(summarized_metrics))
