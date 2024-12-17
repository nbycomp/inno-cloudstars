import openai
import sys
import os
import requests

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

# Prometheus server URL
prometheus_url = "http://localhost:9090/api/v1/query"

def generate_promql_query(request):
    """
    Generate PromQL query based on the user request using GPT-3.5-Turbo.
    """
    prompt = f"""
    The user wants a PromQL query to monitor metrics related to '{request}'.
    Generate a PromQL query based on the request. Ensure the query is suitable for 
    low latency, delay, or energy consumption and can work with standard Prometheus metrics.
    Provide only the PromQL query and no explanation.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in Prometheus monitoring and PromQL query generation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"An error occurred: {e}"

def clean_promql_query(query):
    """
    Clean PromQL query to remove unintended formatting artifacts.
    """
    # Remove any backticks and unintended prefixes like `plaintext`
    return query.replace("`", "").replace("plaintext", "").strip()

def fetch_prometheus_data(promql_query):
    """
    Fetch data from Prometheus using the cleaned PromQL query.
    """
    try:
        response = requests.get(prometheus_url, params={"query": promql_query})
        if response.status_code == 200:
            return response.json().get("data", {}).get("result", [])
        else:
            return f"Failed to fetch data. HTTP Status Code: {response.status_code}, Response: {response.text}"
    except Exception as e:
        return f"An error occurred while fetching data: {e}"

# User input for query generation
user_request = input("Enter your monitoring requirement (e.g., low latency, delay, energy consumption): ")

# Generate PromQL query using GPT-3.5-Turbo
promql_query = generate_promql_query(user_request)
print("\nGenerated PromQL Query:")
print(promql_query)

# Clean the PromQL query
cleaned_query = clean_promql_query(promql_query)
print("\nCleaned PromQL Query:")
print(cleaned_query)

# Fetch the output from Prometheus
if not cleaned_query.startswith("An error occurred"):
    prometheus_output = fetch_prometheus_data(cleaned_query)
    print("\nPrometheus Output:")
    print(prometheus_output)
else:
    print("\nError generating PromQL query.")