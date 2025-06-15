import requests
from concurrent.futures import ThreadPoolExecutor
from tor import make_request_through_tor
from bs4 import BeautifulSoup
from bs4 import BeautifulSoup
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
from captcha import predict_captcha
from io import BytesIO
from PIL import Image


def aes_encrypt(plain_text: str, key_str: str) -> str:
    """Encrypts the given plain text using AES-128-CBC with the provided key."""
    key = key_str.encode('utf-8')  # Convert key to bytes
    iv = key  # Using key as IV (not recommended for security, but matching given logic)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_text)
    
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def aes_decrypt(encrypted_base64: str, key_str: str) -> str:
    """Decrypts the given Base64-encoded AES-128-CBC ciphertext using the provided key."""
    key = key_str.encode('utf-8')
    iv = key  # Using key as IV
    
    encrypted_bytes = base64.b64decode(encrypted_base64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    
    return decrypted_bytes.decode('utf-8')

session = requests.Session()

# # Run tests in parallel
# working_proxies = []
# with ThreadPoolExecutor(max_workers=10) as executor:
#     results = executor.map(test_proxy, proxies_list)
#     working_proxies = [proxy for proxy in results if proxy]

# # Output the working proxies
# working_proxies
# print("Working Proxies:", working_proxies)

# def get_ip():
#     response = make_request_through_tor(session,url = 'https://api64.ipify.org?format=json').json()
#     return response["ip"]


# def get_location():
#     ip_address = get_ip()
#     response = make_request_through_tor(session,url = f'https://ipapi.co/{ip_address}/json/').json()
#     location_data = {
#         "ip": ip_address,
#         "city": response.get("city"),
#         "region": response.get("region"),
#         "country": response.get("country_name")
#     }
#     return location_data
# location = get_location()
# print(location)

headers = {
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
    "Content-Encoding": "gzip",
    "Content-Type": "text/html; charset=utf-8",
    "Referrer-Policy": "strict-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Permissions-Policy": "geolocation=(), microphone=()",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Vary": "Accept-Encoding",
    "Content-Security-Policy": (
        "default-src https://ris.kfintech.com/ https://karisma.kfintech.com/ 'self' data: gap: 'unsafe-eval'; "
        "style-src https://fonts.googleapis.com/ 'self' 'unsafe-inline'; "
        "media-src *; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://platform.twitter.com/; "
        "connect-src * https://ris.kfintech.com 'self'; "
        "font-src https://fonts.googleapis.com/ https://fonts.gstatic.com 'self'"
    ),
}
url = "https://ipostatus.kfintech.com/"
response = make_request_through_tor(session,url, headers=headers)
# Parse the HTML response
soup = BeautifulSoup(response.text, 'html.parser')
# Find the <a> element with id="btn_submit_query"
element = soup.find('a', id='btn_submit_query')

# Extract the onclick attribute
onclick_text = element['onclick']

# Use regex to extract the value inside the single quotes
match = re.search(r"validate_all\('([^']+)'\)", onclick_text)

if match:
    # This will be the value inside the validate_all function
    key = match.group(1)
    print(f"Extracted token: {key}")
else:
    print("No token found.")


# Extract necessary form fields (modify selectors as needed)
viewstate = soup.find("input", {"name": "__VIEWSTATE"})['value'] if soup.find("input", {"name": "__VIEWSTATE"}) else None
event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})['value'] if soup.find("input", {"name": "__EVENTVALIDATION"}) else None
viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})['value'] if soup.find("input", {"name": "__VIEWSTATEGENERATOR"}) else None
# Extract cookies from the response
cookies = response.cookies

# Print the cookies
for cookie in cookies:
    print(f"{cookie.name}: {cookie.value}")

captcha_img_tag = soup.find("img", {"id": "captchaimg"})
if captcha_img_tag:
    captcha_url = captcha_img_tag["src"]

    # Ensure the CAPTCHA URL is absolute
    # if captcha_url.startswith("/"):
    captcha_url = url + captcha_url  # Append to base URL if relative
    print(captcha_url)

    # Step 3: Request the CAPTCHA image using the same session (NOT a new request)
    captcha_response = make_request_through_tor(session,captcha_url, stream=True)

    # Step 4: Save the image
    img = Image.open(BytesIO(captcha_response.content))
    img.save("C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\captcha.png")

predict = predict_captcha(None, 'kfintech')
print(predict)

print("ViewState:", viewstate)
print("EventValidation:", event_validation)
print("ViewStateGenerator:", viewstate_generator)
# Encrypt
encrypted_text = aes_encrypt("omops4188f", key)
print(f"Encrypted (Base64): {encrypted_text}")

# Decrypt
decrypted_text = aes_decrypt(encrypted_text, key)
print(f"Decrypted: {decrypted_text}")

# post request neccessary data
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://ipostatus.kfintech.com",
    "Referer": "https://ipostatus.kfintech.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
    "sec-ch-ua": '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


data = {
    "__EVENTTARGET": "btn_submit_query",
    "__EVENTARGUMENT": "",
    "__LASTFOCUS": "",
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": viewstate_generator,
    "__EVENTVALIDATION": event_validation,
    "txtIPONo": "NSE-123456",
    "ddl_ipo": "HEXA~hexawaretech~0~17/02/2025~17/02/2025~EQT",
    "query": "pan",
    "txt_applno": "",
    "ddl_depository": "N",
    "txt_nsdl_dpid": "",
    "txt_nsdl_clid": "",
    "txt_cdsl_clid": "",
    "txt_pan": encrypted_text,
    "txt_captcha": predict,
    "txt_conf_pan": "",
    "_h_query": "pan",
    "encrypt_payload": "Y",
    "req_src": "",
}



response = make_request_through_tor(session,url, headers=headers, cookies=cookies, data=data, post =True)

print(response.text)