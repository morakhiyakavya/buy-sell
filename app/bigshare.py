import random
# from app.tor import make_request_through_tor
try :
    from app.tor import make_request_through_tor  # Import the make_request_through_tor function
except ImportError:
    from tor import make_request_through_tor
from bs4 import BeautifulSoup
import requests

session = requests.Session()

# Function to get random user-agent
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    ]
    return random.choice(user_agents)


url = "https://ipo.bigshareonline.com/Data.aspx/FetchIpodetails"

headers = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
    "content-type": "application/json; charset=UTF-8",
    "origin": "https://ipo.bigshareonline.com",
    "user-agent": get_random_user_agent(),
    "referer": "https://ipo.bigshareonline.com/ipo_status.html",
}



def big_company(company_name  = None, url = "https://ipo.bigshareonline.com/ipo_status.html"):
    response = make_request_through_tor(session,url)
    soup = BeautifulSoup(response.text, 'html.parser')
    select_element = soup.find('select', id='ddlCompany')
    company_dict = {}
    for option in select_element.find_all('option'):
        # Skip the first option if it's just a placeholder
        if option.get('value') and option.string != '--Select Company--':
            value = int(option['value'])  # Convert the value to an integer
            company_names = option.string.strip()  # Get the text inside the <option> tag
            company_dict[value] = company_names
    # Extract company_id and companyname
    # company_dict = {entry["companyname"].strip().upper(): int(entry["company_id"]) for entry in company_dict.items()}

    print(company_dict)  # Debugging: Print extracted company data

    if company_name:
        company_name_upper = company_name.upper().strip()

    #     # **Try partial matching**
    for key,value in company_dict.items():
        if company_name_upper in value.upper():
            print(f"Matched '{company_name}' to '{value}'")
            return key
        
    print(f"Company name '{company_name}' not found in the response.")
    return None


# big_company()

def big_pan(company,pan):

    data = {
    "Applicationno": "",
    "Company": company,
    "SelectionType": "PN",
    "PanNo": pan,
    "txtcsdl": "",
    "txtDPID": "",
    "txtClId": "",
    "ddlType": "0",
    "lang": "en"
}
    # Make the request using Tor
    response = make_request_through_tor(session, url, headers=headers, json=data, post=True)
    result_dict = {}
    for key, value in response.json()['d'].items():
        if key == '__type':
            continue
        result_dict[key] = value
    return result_dict

# print(big_pan(big_company('desco'), 'OMOPS4188F'))