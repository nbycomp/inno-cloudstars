import openai
import json
import sys
import os

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)



# Define the path to your key file
key_file_path = os.path.join(os.path.dirname(__file__), "key.txt")
# Set your OpenAI API key

# Load the API key from the file
try:
    with open(key_file_path, "r") as key_file:
        openai.api_key = key_file.read().strip()
except FileNotFoundError:
    raise FileNotFoundError("The key.txt file is not found. Please ensure it exists in the script's directory.")
except Exception as e:
    raise RuntimeError(f"An error occurred while loading the API key: {e}")


def fetch_cluster_data():
    """
    Simulate fetching cluster data from Prometheus or other sources.
    Replace this function with real data gathering from Prometheus or your system.
    """
    return [
        {
            "cluster_name": "ClusterA",
            "cpu_usage": 0.7,
            "memory_usage": 0.6,
            "network_bandwidth": 100,  # Mbps
            "latency": 20,  # ms
            "error_rate": 0.01,  # %
            "region": "us-east-1",
        },
        {
            "cluster_name": "ClusterB",
            "cpu_usage": 0.5,
            "memory_usage": 0.4,
            "network_bandwidth": 200,
            "latency": 10,
            "error_rate": 0.005,
            "region": "us-west-2",
        },
        {
            "cluster_name": "ClusterC",
            "cpu_usage": 0.9,
            "memory_usage": 0.8,
            "network_bandwidth": 50,
            "error_rate": 0.02
        },
    ]

def rank_clusters(user_intent, cluster_data):
    """
    Use GPT to rank clusters based on user intent and metrics.
    """
    prompt = f"""
    The user wants to deploy a new service with the following intent: "{user_intent}".
    Here is the data for available clusters:
    {json.dumps(cluster_data, indent=2)}
    Rank the clusters based on the user intent and the data provided.
    Provide a ranking along with explanations for your choices.
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

# Fetch cluster data
cluster_data = fetch_cluster_data()

# User request
user_intent = input("Enter user intent for service deployment (e.g., low latency, high availability): ")

# Rank clusters
ranking = rank_clusters(user_intent, cluster_data)

# Output the results
print("\nCluster Ranking and Explanation:")
print(ranking)
