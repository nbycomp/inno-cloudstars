

# **LLM Decision Maker for NearbyOne**

## **Project Overview**  
This project provides a demo for an **LLM-based Decision Engine** designed to interact with the NearbyOne platform. The tool uses OpenAI's API to power decision-making capabilities.

---

## **Setup Instructions**

Follow these steps to set up and run the project:

### 1. **Prepare Your Workspace**  
Create a workspace directory and clone the repository:  
```bash
mkdir ~/workspace/ && cd ~/workspace/
git clone <repository_url>
cd inno-cloudstars/2024-Oct-Dec-llm-decision-maker/
```

---

### 2. **Install Dependencies**  
Install the required Python libraries:  
```bash
python -m pip install -r requirements.txt
```

---

### 3. **Configure API Keys and Account Information**

- **OpenAI API Key**  
   Add your OpenAI API key to the following file:  
   ```text
   decision_engine/demo/key.txt
   ```
   Example content:  
   ```
   YOUR_OPENAI_API_KEY
   ```

- **NearbyOne Account Information**  
   Add your NearbyOne account information to the configuration file:  

   decision_engine/config/nbi_account_info.json

   Example format:  
   ```json
    {
    "user_email": "",
    "password": "",
    "org": "",
    "env_name": ""
    }
   ```

---

### 4. **Run the Application**

Start the demo using Streamlit:  
```bash
streamlit run decision_engine/demo/demo_app.py
```

---

## **Usage**

Once the Streamlit demo is running:  
1. Open the displayed URL (usually `http://localhost:8501/`) in your browser.  
2. Follow the prompts to interact with the LLM-based decision engine.

---

## **Dependencies**  
- Python (>=3.8)  
- OpenAI API  
- Streamlit  

All dependencies are listed in `requirements.txt`.

---

## **Troubleshooting**  
- **Missing API Key**: Ensure you have added the OpenAI API key to `key.txt`.  
- **Dependency Errors**: Run `pip install -r requirements.txt` again.  
- **Streamlit Not Found**: Install it using `pip install streamlit`.

---
