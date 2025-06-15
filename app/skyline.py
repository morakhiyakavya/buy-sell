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
        for option in options:
            if company_name.upper() in option.text.upper():
                print(f"Company code found: {option['value']}")
                return option["value"], cookies
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
    company_code, cookies = company_url(company_name)
    print(f"Company code: {company_code}")
    print(f"Cookies: {cookies}")
    url = "https://www.skylinerta.com/display_application.php"

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.skylinerta.com",
        "referer": f"https://www.skylinerta.com/display_application.php?app={company_code}",
        "user-agent": random.choice(user_agents),
        "DNT": "1",  # Optional: Do Not Track
    }

    cookies = {
        "PHPSESSID": cookies.get("PHPSESSID"),
    }

    data = {
        "client_id": client_id,
        "application_no": application_no,
        "pan": pan,
        "app": company_code,
        "action": "search",
        "image": "Search",
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=data)
    soup = BeautifulSoup(response.text, "html.parser")
    # print(soup.prettify())
    div = soup.find("div", class_="fullwidth resultsec").text.strip()
    div2  = soup.find("div", class_="fullwidth searchapp").text.strip()
    print(f"Div Contains : {div2 if div2 else None}")
    print(f"Div 2 contains : {div if div else None}")
    return response


# Example usage
response = search_application("balaji", pan="OMOPS4188F")
print(response.status_code)
# print(response.text)
