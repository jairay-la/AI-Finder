import requests
from anthropic import Anthropic
from flask import Flask, request, render_template_string
from dotenv import load_dotenv
import os

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ATTOM_API_KEY = os.getenv('ATTOM_API_KEY')

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ATTOM API base URL
ATTOM_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/"

def query_attom(zip_code):
    endpoint = "property/basicprofile"
    headers = {"Accept": "application/json", "apikey": ATTOM_API_KEY}
    params = {"postalcode": zip_code, "pagesize": "10"}
    
    try:
        response = requests.get(f"{ATTOM_BASE_URL}{endpoint}", headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            properties = data.get("property", [])
            if not properties:
                return f"No properties found in ZIP {zip_code}."
            basic_info = [{
                "address": f"{p.get('address', {}).get('line1', 'N/A')}",
                "city": p.get('address', {}).get('city', 'N/A'),
                "value": p.get('assessment', {}).get('assessed', {}).get('assdTtlValue', 'N/A')
            } for p in properties]
            return basic_info
        else:
            error_msg = response.json().get("status", {}).get("msg", "Unknown error")
            return f"ATTOM API Error: {response.status_code} - {error_msg}"
    except requests.exceptions.RequestException as e:
        return f"Request Error: {str(e)}"

def analyze_gems(data):
    if isinstance(data, str):
        return data
    
    prompt = f"""
    You're a real estate investor analyzing properties in this area.
    Here's a list of properties with detailed information:
    {data}
    
    Identify the top 3 properties based on:
    - Location value and potential
    - Current assessed value
    - Comparative market analysis
    
    Format the output as a concise report:
    1. [Address, City] - Assessed Value: $[value]
       - Reason: [brief reason]
    2. [Address, City] - Assessed Value: $[value]
       - Reason: [brief reason]
    3. [Address, City] - Assessed Value: $[value]
       - Reason: [brief reason]
    """
    
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Distressed Property Finder</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: auto; }
        input, button { padding: 10px; margin: 5px; }
        pre { background: #f4f4f4; padding: 10px; white-space: pre-wrap; font-size: 14px; }
        .download { margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Distressed Property Finder</h1>
    <form method="POST">
        <input type="text" name="zip_code" placeholder="Enter ZIP Code" required>
        <button type="submit">Find Properties</button>
    </form>
    {% if analysis %}
        <h2>Top Picks for ZIP {{ zip_code }}</h2>
        <pre>{{ analysis }}</pre>
        <a href="data:text/plain;charset=utf-8,{{ analysis|string|urlencode }}" 
           download="property-report-{{ zip_code }}.txt" class="download">
            Download Report
        </a>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    analysis = None
    try:
        if request.method == "POST":
            zip_code = request.form["zip_code"]
            data = query_attom(zip_code)
            analysis = analyze_gems(data)
    except Exception as e:
        analysis = f"Error processing request: {str(e)}"
    return render_template_string(HTML_TEMPLATE, analysis=analysis, zip_code=request.form.get("zip_code", ""))

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)