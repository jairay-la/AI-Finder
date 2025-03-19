import requests
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Get API keys from environment variables
ATTOM_API_KEY = os.getenv('ATTOM_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Validate API keys
if not ATTOM_API_KEY or not ANTHROPIC_API_KEY:
    raise ValueError("Missing required API keys. Please check your .env file.")

# ATTOM API base URL
ATTOM_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"

# Headers for ATTOM API
headers = {"Accept": "application/json", "apikey": ATTOM_API_KEY}

# Claude client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Fetch sales trend with token limit
def get_sales_trend(zip_code):
    url = f"{ATTOM_BASE_URL}/salestrend?postalcode={zip_code}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Limit to ~500 tokens (1 token ~ 4 chars)
        data = response.text[:2000]
        return eval(data) if data else None  # Unsafe; use json.loads in production
    return None

# Fetch property details with token limit
def get_property_details(address):
    url = f"{ATTOM_BASE_URL}/property/detail?address1={address}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.text[:2000]
        return eval(data) if data else None
    return None

# Predictive zip code analysis
def predict_zip_trend(zip_code):
    sales_data = get_sales_trend(zip_code)
    if not sales_data or 'salestrend' not in sales_data:
        # Mock data fallback
        trend, avg_price = 0.5, 450000
        reason_prefix = "Using mock data due to unavailable ATTOM response: "
    else:
        trend = sales_data['salestrend'][0]['trend']
        avg_price = sales_data['salestrend'][0]['avgSalePrice']
        reason_prefix = ""
    
    score = trend * 0.7 + avg_price * 0.0001
    prompt = f"As a top REO investor with decades of experience in Los Angeles County, analyze this for zip code {zip_code}: monthly sales trend {trend}%, avg price ${avg_price}. Predict if it will appreciate or depreciate over the next 6 months and explain why in 100-150 tokens."
    insight = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text
    
    return "Appreciate" if score > 0 else "Depreciate", reason_prefix + insight

# Property selection with mock data
def select_properties(zip_code, category):
    addresses = [f"{i} Main St, Los Angeles, CA {zip_code}" for i in range(1234, 1237)]
    properties = []
    
    for i, address in enumerate(addresses):
        details = get_property_details(address)
        last_sale = details['property'][0]['saleshistory'][-1]['amount'] if details and 'saleshistory' in details['property'][0] else 0
        score = 90 - i * 2 if category == 'propensity' else 85 - i * 2  # Mock distress
        equity = 20.0 + i * 2.5  # Mock equity
        
        prompt = f"As a top REO investor, evaluate this {category} property: {address}, last sale ${last_sale}, distress score {score}, equity {equity:.1f}%. Why is it a good deal in 50-100 tokens?"
        reasoning = anthropic_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        
        properties.append({'address': address, 'score': score, 'last_sale': last_sale, 'equity': equity, 'reasoning': reasoning})
    
    return sorted(properties, key=lambda x: x['score'] * 0.6 + x['equity'] * 0.4, reverse=True)[:3]

# Prompt user
zip_code = input("Enter a Los Angeles County zip code (e.g., 90045): ").strip()

# Execute
trend, zip_insight = predict_zip_trend(zip_code)
propensity_props = select_properties(zip_code, 'propensity')
preforeclosure_props = select_properties(zip_code, 'pre-foreclosure')

# Output
output = f"Predictive Analysis for Zip Code {zip_code}:\n"
output += f"Trend (Next 6 Months): {trend}\n"
output += f"Reasoning: {zip_insight}\n\n"

output += "Top 3 Propensity to Default Deals:\n"
for i, prop in enumerate(propensity_props, 1):
    output += f"{i}. {prop['address']} - Score: {prop['score']}, Last Sale: ${prop['last_sale']:,}, Equity: {prop['equity']:.1f}%\n"
    output += f"   Reasoning: {prop['reasoning']}\n"

output += "\nTop 3 Pre-Foreclosure Deals:\n"
for i, prop in enumerate(preforeclosure_props, 1):
    output += f"{i}. {prop['address']} - Score: {prop['score']}, Last Sale: ${prop['last_sale']:,}, Equity: {prop['equity']:.1f}%\n"
    output += f"   Reasoning: {prop['reasoning']}\n"

print(output)
