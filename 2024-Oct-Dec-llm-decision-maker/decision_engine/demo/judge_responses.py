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


# Step 1: Generate multiple responses (Model 1)
def generate_responses(user_intent, cluster_data, num_responses=3):
    """
    Generate multiple ranked responses based on user intent and cluster data.
    """
    prompt = f"""
    The user wants to deploy a new service with the following intent: "{user_intent}".
    Here is the data for available clusters:
    {json.dumps(cluster_data, indent=2)}
    Generate {num_responses} different ranked responses for cluster selection.
    Each response should rank the clusters and explain the reasoning behind the ranking.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in cloud computing and resource optimization."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.9  # Higher temperature for diverse responses
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"An error occurred: {e}"

# Step 2: Evaluate responses (Model 2)
def evaluate_responses(user_intent, responses):
    """
    Evaluate the generated responses based on user intent.
    """
    prompt = f"""
    The user wants to deploy a new service with the following intent: "{user_intent}".
    Here are several ranked responses for cluster selection:
    {json.dumps(responses, indent=2)}
    Evaluate these responses and select the one that best aligns with the user's intent.
    Provide the evaluation reasoning and the chosen response.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert evaluator for cloud computing decisions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.5  # Lower temperature for deterministic evaluation
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"An error occurred: {e}"

# Simulated cluster data
cluster_data = [
    {"cluster_name": "ClusterA", "cpu_usage": 0.7, "memory_usage": 0.6, "latency": 20, "error_rate": 0.01, "region": "us-east-1"},
    {"cluster_name": "ClusterB", "cpu_usage": 0.5, "memory_usage": 0.4, "latency": 10, "error_rate": 0.005, "region": "us-west-2"},
    {"cluster_name": "ClusterC", "cpu_usage": 0.9, "memory_usage": 0.8, "latency": 30, "error_rate": 0.02, "region": "eu-central-1"}
]

# User intent
user_intent = input("Enter user intent for service deployment (e.g., low latency, high availability): ")

# Step 1: Generate multiple ranked responses
print("Generating ranked responses...")
ranked_responses = generate_responses(user_intent, cluster_data, num_responses=3)
print("\nGenerated Responses:")
print(ranked_responses)

# Step 2: Evaluate the responses
print("\nEvaluating responses...")
best_response = evaluate_responses(user_intent, ranked_responses)
print("\nBest Response:")
print(best_response)
