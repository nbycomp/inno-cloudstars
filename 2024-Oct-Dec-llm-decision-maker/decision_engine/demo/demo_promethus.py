import re
import streamlit as st
from transformers import pipeline

# Initialize text generation model
intent_model = pipeline("text-generation", model="EleutherAI/gpt-neo-1.3B", tokenizer="EleutherAI/gpt-neo-1.3B")

def mock_prometheus_script():
    """Simulate the output of the Prometheus script with mock data."""
    return {
        'cpu_total_cores': 16,
        'cpu_used_cores': 6,
        'cpu_available_cores': 10,
        'memory_total_gb': 64.0,
        'memory_used_gb': 24.0,
        'memory_available_gb': 40.0
    }

def extract_requirements(user_input):
    """Use the model to extract CPU and memory requirements from user input, with fallback pattern matching."""
    # Prompt for CPU requirements
    cpu_prompt = f"Extract the number of CPU cores needed from this request: '{user_input}'. Return only the numeric value."
    cpu_response = intent_model(cpu_prompt, max_length=50, do_sample=False)[0]["generated_text"].strip()

    # Attempt to convert the response to an integer
    try:
        required_cpu = int(re.search(r"\d+", cpu_response).group())
    except (ValueError, AttributeError):
        # Fallback: Regex extraction from user input
        cpu_match = re.search(r'(\d+)\s*(?:cpu|cpus?|c|cores?)', user_input, re.IGNORECASE)
        required_cpu = int(cpu_match.group(1)) if cpu_match else 0

    # Prompt for memory requirements
    memory_prompt = f"Extract the memory requirement in GB from this request: '{user_input}'. Return only the numeric value."
    memory_response = intent_model(memory_prompt, max_length=50, do_sample=False)[0]["generated_text"].strip()

    # Attempt to convert the response to an integer
    try:
        required_memory = int(re.search(r"\d+", memory_response).group())
    except (ValueError, AttributeError):
        # Fallback: Regex extraction from user input
        memory_match = re.search(r'(\d+)\s*(?:gb|g|mb|m|kb|k)?', user_input, re.IGNORECASE)
        required_memory = int(memory_match.group(1)) if memory_match else 0

    return required_cpu, required_memory

def check_feasibility(metrics, required_cpu, required_memory):
    """Check if the system meets the CPU and memory requirements."""
    cpu_available = metrics['cpu_available_cores']
    memory_available = metrics['memory_available_gb']

    if cpu_available >= required_cpu and memory_available >= required_memory:
        result_message = (
            f"Feasible configuration found.\n"
            f"Available CPU cores: {cpu_available} (required: {required_cpu})\n"
            f"Available Memory: {memory_available} GB (required: {required_memory} GB)"
        )
    else:
        result_message = (
            f"No feasible configuration found.\n"
            f"Available CPU cores: {cpu_available} (required: {required_cpu})\n"
            f"Available Memory: {memory_available} GB (required: {required_memory} GB)"
        )
    return result_message

# Streamlit App for Demo
def main():
    st.title("Demo: System Resource Allocation Based on High-Level User Intent")

    # Get high-level user input for CPU and memory requirements
    user_input = st.text_input("Enter your deployment request:", "")

    if st.button("Check Feasibility"):
        # Step 1: Use mock Prometheus data
        metrics = mock_prometheus_script()

        # Step 2: Extract requirements from high-level request
        required_cpu, required_memory = extract_requirements(user_input)
        
        # Display extracted requirements
        st.write(f"Extracted CPU requirement: {required_cpu} cores")
        st.write(f"Extracted Memory requirement: {required_memory} GB")

        # Step 3: Check if the system meets the user intent requirements
        result_message = check_feasibility(metrics, required_cpu, required_memory)

        # Display result
        st.write(result_message)

if __name__ == "__main__":
    main()
