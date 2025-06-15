import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import xmltodict
import json
import time
from bs4 import BeautifulSoup
try :
    from app.tor import make_request_through_tor  # Import the make_request_through_tor function
except ImportError:
    from tor import make_request_through_tor
# start_time = time.time() 

# Fixed key and IV (both must be 16 bytes for AES-128)
key = b'8080808080808080'
iv = b'8080808080808080'
headers = {"Content-Type": "application/json; charset=utf-8"} 
session = requests.Session()
# Function to encrypt the token value using AES encryption
def encrypt_value(value):
    # Convert the string value to bytes
    data = value.encode('utf-8')
    # Pad the data according to PKCS7
    padded_data = pad(data, AES.block_size)
    # Create AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)
    # Encode to base64 to get a string
    return base64.b64encode(encrypted).decode('utf-8')

# Generate Token function
def generate_token():
    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/generateToken"
    
    response = make_request_through_tor(session,url, headers=headers, post=True)

    if response.status_code == 200:
        token = response.json().get("d")
        return token
    else:
        raise Exception("Error generating token")

def get_company_name(company_name=None):
    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/GetDetails"
    response = make_request_through_tor(session, url, headers=headers, post=True)

    if response.status_code != 200:
        print(f"Failed to fetch company names. Status code: {response.status_code}")
        return None

    try:
        json_data = json.loads(response.text)  # Convert response to dictionary
        xml_string = json_data["d"]  # Extract XML from JSON
        data = xmltodict.parse(xml_string)  # Parse XML
    except (json.JSONDecodeError, KeyError):
        print("Error: Response is not JSON or missing 'd' key.")
        return None

    # Navigate to the "Table" elements inside "NewDataSet"
    tables = data.get("NewDataSet", {}).get("Table", [])

    # Ensure tables is always a list (xmltodict may return a dict if there's only one Table element)
    if isinstance(tables, dict):
        tables = [tables]

    # Extract company_id and companyname
    company_dict = {entry["companyname"].strip().upper(): int(entry["company_id"]) for entry in tables}

    print(company_dict)  # Debugging: Print extracted company data

    if company_name:
        company_name_upper = company_name.upper().strip()

        # **Try partial matching**
        for key in company_dict.keys():
            if company_name_upper in key:
                print(f"Matched '{company_name}' to '{key}'")
                return company_dict[key]
        
        print(f"Company name '{company_name}' not found in the response.")
        return None  # Explicitly return None if no match found

    return list(company_dict.values())

# Search on PAN using the encrypted token
def search_on_pan(clientid, pan, ifsc="", chkval="1"):

    if clientid is None:
        print("Error: No matching company found.")
        return {"error": "Company not found"}
    
    token = generate_token()
    encrypted_token = encrypt_value(token)

    url = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx/SearchOnPan"
    
    payload = {
        'clientid': clientid,
        'PAN': pan,
        'IFSC': ifsc,
        'CHKVAL': chkval,
        'token': encrypted_token
    }

    response = make_request_through_tor(session, url, json=payload, headers=headers, post=True)

    if response.status_code != 200:
        raise Exception(f"Error in SearchOnPan: {response.text}")

    try:
        json_data = response.json()
        xml_string = json_data.get("d")  # Extract XML from JSON
        data_dict = xmltodict.parse(xml_string)  # Parse XML
    except (json.JSONDecodeError, KeyError, xmltodict.expat.ExpatError):
        print("Error parsing response.")
        return {"error": "Invalid response format"}

    readable_dict = json.loads(json.dumps(data_dict, indent=2))

    return readable_dict

# Example: Search for PAN
company = get_company_name("Belrise Industries Limited")
print(search_on_pan(company, "DEWPG1078F"))

# end_time = time.time()
# print(f"Time taken: {end_time - start_time} seconds")
