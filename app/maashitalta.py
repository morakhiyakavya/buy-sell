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
    url = f"https://maashitla.com/allotment-status/public-issues"
    response = make_request_through_tor(session, url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch company names. Status code: {response.status_code}")
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    company_names = []
    for option in soup.find_all('option')[1:]:
        company_names.append(option.text.strip())
    if company_name:
        for company in company_names:
            if company_name.lower() in company.lower():
                print(f"Matched '{company_name}' to '{company}'")
                company = company.replace(" ", "_").lower()
                print(company)
                return company
        print(f"Company name '{company_name}' not found in the response.")
    return company_names

    
# Search on PAN using the encrypted token
def search_on_maashilta(clientid, pan, ifsc="", chkval="1"):

    if clientid is None:
        print("Error: No matching company found.")
        return {"error": "Company not found"}
    
    url = f"https://maashitla.com/PublicIssues/Search?company={clientid}&search={pan}"


    response = make_request_through_tor(session, url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error in SearchOnPan: {response.text}")

    print(response.text)
    
    try:
        response_json = json.loads(response.text)
    except json.JSONDecodeError:
        print("Error: Response is not JSON.")
        return None

    return response_json

# Example: Search for PAN
# print(mashilta_company(company_name="virtual"))
# print(search_on_pan("virtual_galaxy_infotech_limited", "OBAPS4860K"))