try:
    from tor import make_request_through_tor
except ImportError:
    from app.tor import make_request_through_tor
import requests
import random
from bs4 import BeautifulSoup

session = requests.Session()

user_agents = [
    # Common Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/109.0",
    # Common Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    # Generic Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    # Linux Firefox
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
]


def company_url(company_name=None):
    url = "https://www.skylinerta.com/ipo.php"
    response = make_request_through_tor(session, url)
    cookies = response.cookies.get_dict()
    print(f"Cookies: {cookies}")
    soup = BeautifulSoup(response.text, "html.parser")
    select_tag = soup.find("select", class_="create_account_txt selectdrop")
    options = select_tag.find_all("option")[1:]
    if company_name:
        company_upper = company_name.upper().strip()
        
        # First, try exact match
        for option in options:
            if company_upper == option.text.upper():
                print(f"Company code found: {option['value']}")
                return option["value"], cookies
        
        # Then, try match at the start of company name
        for option in options:
            if option.text.upper().startswith(company_upper):
                print(f"Company code found: {option['value']}")
                return option["value"], cookies
        
        # Finally, try substring match
        for option in options:
            if company_upper in option.text.upper():
                print(f"Company code found: {option['value']}")
                return option["value"], cookies
        
        # Not found
        print(f"No company found matching: {company_name}")
        return None, cookies
    else:
        return {option.text: option["value"] for option in options}


# def get_skyline_data(company_name=None, headers=None, params=None):
#     company_code, cookies = company_url(company_name)
#     if type(company_code) != str:
#         raise ValueError("Company code must be a string")
#     url = f"https://www.skylinerta.com/display_application.php?app={company_code}"
#     response = make_request_through_tor(session, url, cookies=cookies)
#     cookies = response.cookies.get_dict()
#     print(f"Cookies: {cookies}")
#     return response.text if response else None

# get_skyline_data("balaji")


def search_application(company_name, pan, client_id="", application_no=""):
    # Step 1: Visit ipo.php to get company code AND extract CSRF token
    url_ipo = "https://www.skylinerta.com/ipo.php"
    headers_get = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
        "cache-control": "max-age=0",
        "user-agent": random.choice(user_agents),
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }
    
    # Get the IPO page - let session handle cookies automatically
    response_ipo = make_request_through_tor(session, url_ipo, headers=headers_get)
    print(f"IPO page status: {response_ipo.status_code}")
    
    soup_ipo = BeautifulSoup(response_ipo.text, "html.parser")
    
    # Find company code
    select_tag = soup_ipo.find("select", class_="create_account_txt selectdrop")
    if not select_tag:
        print("Could not find company dropdown")
        return {"error": "Could not find company dropdown"}
    
    options = select_tag.find_all("option")[1:]
    company_code = None
    company_upper = company_name.upper().strip()
    
    # Try exact match, then starts with, then contains
    for option in options:
        if company_upper == option.text.upper():
            company_code = option["value"]
            break
    if not company_code:
        for option in options:
            if option.text.upper().startswith(company_upper):
                company_code = option["value"]
                break
    if not company_code:
        for option in options:
            if company_upper in option.text.upper():
                company_code = option["value"]
                break
    
    if not company_code:
        print(f"No company found matching: {company_name}")
        return {"error": f"No company found matching: {company_name}"}
    
    print(f"Company code: {company_code}")
    
    # Get cookies from IPO page response
    cookies_dict = response_ipo.cookies.get_dict()
    print(f"Cookies after IPO page: {cookies_dict}")
    
    # Look for CSRF token on the IPO page itself (in the form)
    csrf_token = ""
    
    # Analyze the form on the IPO page
    forms = soup_ipo.find_all("form")
    print(f"Found {len(forms)} forms on IPO page")
    
    for i, form in enumerate(forms):
        action = form.get("action", "")
        method = form.get("method", "GET")
        form_id = form.get("id", "")
        print(f"Form {i}: action='{action}', method='{method}', id='{form_id}'")
        inputs = form.find_all("input")
        for inp in inputs:
            print(f"  Input: name={inp.get('name')}, type={inp.get('type')}, value={inp.get('value', '')[:50] if inp.get('value') else ''}")
        selects = form.find_all("select")
        for sel in selects:
            print(f"  Select: name={sel.get('name')}, id={sel.get('id')}")
        
        # Check for csrf token in this form
        csrf_in_form = form.find("input", {"name": "csrf_token"})
        if csrf_in_form:
            csrf_token = csrf_in_form.get("value", "")
            print(f"CSRF Token from form: {csrf_token}")
    
    # Step 2: Submit the IPO form to select the company
    # The form likely POSTs to a URL that sets up the session
    ipo_form = soup_ipo.find("form")
    if ipo_form:
        form_action = ipo_form.get("action", "")
        if form_action and not form_action.startswith("http"):
            form_action = f"https://www.skylinerta.com/{form_action.lstrip('/')}"
        elif not form_action:
            form_action = url_ipo  # Post to same URL
        
        print(f"Submitting IPO form to: {form_action}")
        
        # Build form data from the form
        form_data = {}
        for inp in ipo_form.find_all("input"):
            name = inp.get("name")
            if name:
                form_data[name] = inp.get("value", "")
        
        # Set the company in the select
        select_name = select_tag.get("name", "company")
        form_data[select_name] = company_code
        
        print(f"Form data: {form_data}")
        
        # Submit the form
        headers_post = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.skylinerta.com",
            "referer": "https://www.skylinerta.com/ipo.php",
            "user-agent": random.choice(user_agents),
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }
        
        response_select = make_request_through_tor(session, form_action, headers=headers_post, cookies=cookies_dict, post=True, data=form_data)
        print(f"Company select response status: {response_select.status_code}")
        print(f"Company select response URL: {response_select.url}")
        
        # Update cookies
        cookies_dict.update(response_select.cookies.get_dict())
        print(f"Cookies after company select: {cookies_dict}")
        
        # Parse the response to get CSRF token for the search form
        soup_select = BeautifulSoup(response_select.text, "html.parser")
        title = soup_select.find("title")
        print(f"Page title after select: {title.text if title else 'No title'}")
        
        csrf_input = soup_select.find("input", {"name": "csrf_token"})
        if csrf_input:
            csrf_token = csrf_input.get("value", "")
            print(f"CSRF Token from select response: {csrf_token}")
    
    # Now POST the search request
    url_post = "https://www.skylinerta.com/display_application.php"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.skylinerta.com",
        "referer": "https://www.skylinerta.com/display_application.php",
        "user-agent": random.choice(user_agents),
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }

    data = {
        "client_id": client_id,
        "application_no": application_no,
        "pan": pan,
        "csrf_token": csrf_token,
        "company": company_code,
        "action": "search",
    }
    
    print(f"Posting with data: {data}")
    print(f"Cookies for POST: {cookies_dict}")

    response = make_request_through_tor(session, url_post, headers=headers, cookies=cookies_dict, post=True, data=data)
    
    if response:
        soup = BeautifulSoup(response.text, "html.parser")
        print("Search Results:")
        print("----------------")
        
        # Check for error message
        error_div = soup.find("div", class_="error")
        if error_div:
            print(f"Error from server: {error_div.text.strip()}")
            return {"error": error_div.text.strip()}
        
        # Find the result section
        result_section = soup.find("div", class_="resultsec")
        if not result_section:
            print("No results found")
            return {"error": "No results found"}
        
        # Parse applicant details from the list
        result_data = {}
        detail_list = result_section.find("ul", class_="dtl_list")
        if detail_list:
            for li in detail_list.find_all("li"):
                strong_tag = li.find("strong")
                if strong_tag:
                    # Get the label (remove the colon)
                    label = strong_tag.text.strip().rstrip(" :").rstrip(":")
                    # Get the value (text after the strong tag)
                    value = strong_tag.next_sibling
                    if value:
                        value = value.strip() if isinstance(value, str) else li.get_text().replace(strong_tag.text, "").strip()
                    else:
                        # Fallback: get all text and remove the label
                        value = li.get_text().replace(strong_tag.text, "").strip()
                    
                    # Map to standardized keys
                    if "Applicant Name" in label:
                        result_data["applicant_name"] = value
                    elif "DP" in label or "Client ID" in label:
                        result_data["dp_client_id"] = value
                    elif "Application Number" in label:
                        result_data["application_no"] = value
                    elif "Pan" in label:
                        result_data["pan"] = value
                    elif "Allotment Date" in label:
                        result_data["allotment_date"] = value
                    elif "Address" in label:
                        result_data["address"] = value
        
        # Parse the allotment table
        table = result_section.find("table", class_="table")
        if table:
            rows = table.find_all("tr")
            if len(rows) >= 2:  # Header + at least one data row
                # Get the data row (skip header)
                data_row = rows[1]
                cells = data_row.find_all("td")
                if len(cells) >= 7:
                    result_data["shares_applied"] = cells[0].text.strip()
                    result_data["application_amount"] = cells[1].text.strip()
                    result_data["shares_allotted"] = cells[2].text.strip()
                    result_data["amount_adjusted"] = cells[3].text.strip()
                    result_data["amount_refunded"] = cells[4].text.strip()
                    result_data["credit_date"] = cells[5].text.strip()
                    result_data["status"] = cells[6].text.strip()
        
        print(f"Parsed data: {result_data}")
        return result_data
    
    return {"error": "No response received"}


# # # # Example usage
# for i in range(1):
#     print(f"Search attempt {i+1}")
#     result = search_application("krm", pan="AANHP4945G")
#     print(f"Result: {result}")
