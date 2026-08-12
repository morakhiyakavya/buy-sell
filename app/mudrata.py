import requests
from bs4 import BeautifulSoup
import json
import time
import difflib
import re

try:
    from app.tor import make_request_through_tor
except ImportError:
    from tor import make_request_through_tor

session = requests.Session()

def get_company_name(company_name=None):
    url = "https://www.mudrarta.com/ipo.php"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
        "cache-control": "max-age=0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
    }
    try:
        response = make_request_through_tor(session, url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch company names. Status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        select_tag = soup.find('select')
        if not select_tag:
            print("No select element found on Mudrata IPO page")
            return None

        options = select_tag.find_all('option')
        company_dict = {}
        for opt in options:
            val = opt.get('value')
            text = opt.get_text(strip=True)
            if val and val.strip():
                company_dict[text.upper().strip()] = val.strip()

        if company_name:
            company_name_upper = company_name.upper().strip()

            # 1. Exact match
            if company_name_upper in company_dict:
                print(f"Matched '{company_name}' exactly to '{company_name_upper}'")
                return company_dict[company_name_upper]

            # 2. Prefix match
            for name, code in company_dict.items():
                if name.startswith(company_name_upper):
                    print(f"Matched '{company_name}' to '{name}' (prefix)")
                    return code

            # 3. Substring match
            for name, code in company_dict.items():
                if company_name_upper in name:
                    print(f"Matched '{company_name}' to '{name}' (substring)")
                    return code

            # 4. Word overlap match
            company_words = set(company_name_upper.split())
            for name, code in company_dict.items():
                name_words = set(name.split())
                if company_words & name_words:
                    print(f"Matched '{company_name}' to '{name}' (word overlap)")
                    return code

            # 5. Fuzzy match
            matches = difflib.get_close_matches(company_name_upper, list(company_dict.keys()), n=1, cutoff=0.5)
            if matches:
                matched_name = matches[0]
                print(f"Matched '{company_name}' to '{matched_name}' (fuzzy)")
                return company_dict[matched_name]

            print(f"Company name '{company_name}' not found in Mudrata.")
            return None

        return list(company_dict.values())
    except Exception as e:
        print(f"Error in get_company_name: {e}")
        return None

def parse_result_text(text):
    if not text:
        return {"Error": "No record found"}
        
    text_clean = " ".join(text.split())
    
    # Check for obvious error keywords
    for err_msg in ["no record", "no data", "not found", "invalid", "error"]:
        if err_msg in text_clean.lower() and "applicant name" not in text_clean.lower():
            return {"Error": text_clean}
            
    patterns = {
        "Company Name": r"Company\s*Name\s*:\s*(.*?)(?=Applicant\s*Name|DP\s*ID\s*/\s*Client|DP\s*ID/Client|Application\s*Number|Pan|Shares\s*Applied|Shares\s*Allotted|Status|$)",
        "Applicant Name": r"Applicant\s*Name\s*:\s*(.*?)(?=DP\s*ID\s*/\s*Client|DP\s*ID/Client|Application\s*Number|Pan|Shares\s*Applied|Shares\s*Allotted|Status|$)",
        "DP Client ID": r"(?:DP\s*ID\s*/\s*Client\s*ID|DP\s*ID/Client\s*ID|DP\s*Client\s*ID|Client\s*ID)\s*:\s*(.*?)(?=Application\s*Number|Pan|Shares\s*Applied|Shares\s*Allotted|Status|$)",
        "Application No": r"(?:Application\s*Number|Application\s*No)\s*:\s*(.*?)(?=Pan|Shares\s*Applied|Shares\s*Allotted|Status|$)",
        "PAN": r"(?:Pan|PAN)\s*:\s*(.*?)(?=Shares\s*Applied|Shares\s*Allotted|Status|$)",
        "Shares Applied": r"(?:Shares\s*Applied|Applied\s*Shares)\s*:\s*(.*?)(?=Shares\s*Allotted|Status|$)",
        "Shares Allotted": r"(?:Shares\s*Allotted|Allotted\s*Shares)\s*:\s*(.*?)(?=Status|$)",
        "Status": r"Status\s*:\s*(.*?)(?=$)"
    }
    
    parsed = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            parsed[key] = match.group(1).strip()
        else:
            parsed[key] = ""
            
    # If we didn't find applicant name and status, it's not a valid record
    if not parsed["Applicant Name"] and not parsed["Status"]:
        return {"Error": text_clean if text_clean else "No record found"}
        
    # Clean up empty or missing numerical values
    shares_applied = parsed["Shares Applied"] if parsed["Shares Applied"] else "0"
    shares_allotted = parsed["Shares Allotted"] if parsed["Shares Allotted"] else "0"
    
    # Map to both casing formats to support any Excel column layout
    result = {
        "company_name": parsed["Company Name"],
        "Company Name": parsed["Company Name"],
        "applicant_name": parsed["Applicant Name"],
        "Applicant Name": parsed["Applicant Name"],
        "dp_client_id": parsed["DP Client ID"],
        "DP Client ID": parsed["DP Client ID"],
        "application_no": parsed["Application No"],
        "Application No": parsed["Application No"],
        "pan": parsed["PAN"],
        "PAN": parsed["PAN"],
        "shares_applied": shares_applied,
        "Shares Applied": shares_applied,
        "shares_allotted": shares_allotted,
        "Shares Allotted": shares_allotted,
        "status": parsed["Status"],
        "Status": parsed["Status"],
        "error": None,
        "Error": None
    }
    
    return result

def search_on_pan(clientid, pan, client_id="", application_no=""):
    if not clientid:
        print("Error: No matching company found.")
        return {"Error": "Company not found"}

    url_get = f"https://www.mudrarta.com/display_application.php?app={clientid}"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
        "cache-control": "max-age=0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
    }

    try:
        # Step 1: GET display_application.php?app=... to establish session / cookies
        make_request_through_tor(session, url_get, headers=headers)

        # Step 2: POST search query
        url_post = "https://www.mudrarta.com/display_application.php"
        headers_post = headers.copy()
        headers_post["referer"] = url_get
        headers_post["content-type"] = "application/x-www-form-urlencoded"
        headers_post["origin"] = "https://www.mudrarta.com"

        payload = {
            "client_id": client_id,
            "application_no": application_no,
            "pan": pan.upper().strip(),
            "app": clientid,
            "action": "search",
            "image": "Search"
        }

        response = make_request_through_tor(session, url_post, headers=headers_post, data=payload, post=True)
        if response.status_code != 200:
            return {"Error": f"HTTP {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")
        result_section = soup.find("div", class_="resultsec")
        if not result_section:
            return {"Error": "No record found"}

        text_content = result_section.get_text(strip=True)
        return parse_result_text(text_content)

    except Exception as e:
        print(f"Error querying Mudrata: {e}")
        return {"Error": str(e)}
