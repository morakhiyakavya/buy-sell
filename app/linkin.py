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
        return {"Error": "Company not found"}
    
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
        return {"Error": f"HTTP {response.status_code}: {response.text}"}

    try:
        json_data = response.json()
        xml_string = json_data.get("d")
        data_dict = xmltodict.parse(xml_string)
    except (json.JSONDecodeError, KeyError, xmltodict.expat.ExpatError):
        print("Error parsing response.")
        return {"Error": "Invalid response format"}

    readable_dict = json.loads(json.dumps(data_dict))

    new_dataset = readable_dict.get("NewDataSet")

    if new_dataset is None:
        return {"Error": "No record found"}

    if "Table1" in new_dataset:
        return {"Error": "Invalid PAN"}

    table_data = new_dataset.get("Table")

    if isinstance(table_data, dict):
        return table_data

    if isinstance(table_data, list):
    # Find the index of the "Shareholder" entry (if it exists and not already at index 1)
        shareholder_index = next((i for i, item in enumerate(table_data) if item.get("PEMNDG") == "Shareholder"), None)

        if shareholder_index is not None and shareholder_index != 1:
            # Swap the entry at index 1 with the shareholder entry
            table_data[shareholder_index], table_data[1] = table_data[1], table_data[shareholder_index]

        flat_result = {}
        for idx, entry in enumerate(table_data, 1):
            for k, v in entry.items():
                if idx == 1:
                    flat_result[k] = v
                else:
                    flat_result[f"{k}_{idx}"] = v
        return flat_result



    return {"Error": "Unexpected Table format"}

# Example: Search for PAN
# company = get_company_name("OSWAL")
# print(search_on_pan(company, "OMOPS4188F"))
# print(search_on_pan(company, "BKIPS5813G"))
# print(search_on_pan(company, "HQTPS3086L"))
# print(search_on_pan(company, "AWUPP67080"))

# end_time = time.time()
# print(f"Time taken: {end_time - start_time} seconds")

def normalize_data(data):
    pass