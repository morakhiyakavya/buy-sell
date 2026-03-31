import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import xmltodict
import json
import time
from bs4 import BeautifulSoup
try:
    from app.tor import make_request_through_tor  # Import the make_request_through_tor function
except ImportError:
    from tor import make_request_through_tor
# start_time = time.time() 


headers = {"Content-Type": "application/json; charset=utf-8"} 
session = requests.Session()


def mashilta_company(company_name=None):
    url = f"https://microservices.maashitla.com/public-issues-service/companies"
    response = make_request_through_tor(session, url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch company names. Status code: {response.status_code}")
        return None
    
    try:
        response_json = json.loads(response.text)
    except json.JSONDecodeError:
        print("Error: Response is not JSON.")
        return None
    
    if not response_json.get("success") or not response_json.get("data"):
        print("Error: Invalid response structure.")
        return None
    
    companies = response_json.get("data", [])
    
    if company_name:
        company_name_lower = company_name.lower()
        
        # First try exact substring match
        for company in companies:
            company_title = company.get("companyTitle", "").lower()
            if company_name_lower in company_title:
                print(f"Matched '{company_name}' to '{company.get('companyTitle')}'")
                return company.get("companyId")
        
        # If no match, try matching individual words
        company_name_words = company_name_lower.split()
        for company in companies:
            company_title = company.get("companyTitle", "").lower()
            if any(word in company_title for word in company_name_words):
                print(f"Matched '{company_name}' to '{company.get('companyTitle')}'")
                return company.get("companyId")
        
        print(f"Company name '{company_name}' not found in the response.")
        return None
    
    return companies

    
# Search on PAN using the encrypted token
def search_on_maashilta(clientid, pan, ifsc="", chkval="1"):

    if clientid is None:
        print("Error: No matching company found.")
        return {"error": "Company not found"}
    
    url = f"https://microservices.maashitla.com/public-issues-service/search?company={clientid}&pan={pan}"

    response = make_request_through_tor(session, url, headers=headers)

    print(response.text)
    
    try:
        response_json = json.loads(response.text)
    except json.JSONDecodeError:
        print("Error: Response is not JSON.")
        return None

    # Check if the API response indicates success
    if not response_json.get("success", False):
        return response_json

    return response_json.get("data")

# Example: Search for PAN
# print(mashilta_company(company_name="msafe"))
# print(search_on_maashilta(mashilta_company(company_name="msafe"), "OMOPS4188F"))