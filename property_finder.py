import requests
from anthropic import Anthropic
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ATTOM_API_KEY = os.getenv('ATTOM_API_KEY')

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ATTOM API base URL
ATTOM_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/"

# Update ATTOM API headers to use environment variable
def query_attom(zip_code):
    endpoint = "property/basicprofile"
    headers = {
        "Accept": "application/json",
        "apikey": ATTOM_API_KEY
    }
    params = {
        "postalcode": zip_code,
        "pagesize": "10"  # Reduced page size for simpler results
    }
    
    try:
        response = requests.get(
            f"{ATTOM_BASE_URL}{endpoint}",
            headers=headers,
            params=params,
            timeout=30
        )
        print(f"Request URL: {response.url}")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            properties = data.get("property", [])
            if not properties:
                return f"No properties found in ZIP {zip_code}."
            # Simplified field selection
            basic_info = [{
                "address": f"{p.get('address', {}).get('line1', 'N/A')}",
                "city": p.get('address', {}).get('city', 'N/A'),
                "value": p.get('assessment', {}).get('assessed', 'N/A')
            } for p in properties]
            return basic_info
        else:
            error_msg = response.json().get("status", {}).get("msg", "Unknown error")
            return f"ATTOM API Error: {response.status_code} - {error_msg}"
            
    except requests.exceptions.RequestException as e:
        return f"Request Error: {str(e)}"

def analyze_gems(properties):
    if isinstance(properties, str):  # Error case
        return properties
    
    prompt = f"""
    You're a real estate investor analyzing properties in this area.
    Here's a list of properties with their basic information:
    {properties}
    
    Please analyze these properties and identify the top 3 based on:
    - Location value and potential
    - Current assessed value
    - Comparative market analysis
    
    Provide a brief analysis of each selected property and why it might be worth investigating further.
    """
    
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content

def chatbot():
    print("Welcome to the Distressed Property Finder!")
    while True:
        user_input = input("Enter a ZIP code (or 'quit' to exit): ")
        if user_input.lower() == "quit":
            break
        
        properties = query_attom(user_input)
        analysis = analyze_gems(properties)
        print("\nTop Picks:\n", analysis)

if __name__ == "__main__":
    chatbot()