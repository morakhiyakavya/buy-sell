import random
# from app.tor import make_request_through_tor
try :
    from app.tor import make_request_through_tor  # Import the make_request_through_tor function
except ImportError:
    from tor import make_request_through_tor
from bs4 import BeautifulSoup
import requests
import time
import base64
from app.captcha import predict_captcha
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

session = requests.Session()


def _request_with_429_retry(send, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        response = send()
        if response.status_code != 429 or attempt == max_attempts:
            return response

        retry_after = response.headers.get('Retry-After', '1')
        try:
            delay = float(retry_after)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError):
                delay = 1
        delay = min(max(delay, 0), 60)
        print({'event': 'bigshare_rate_limit', 'attempt': attempt, 'retry_after_seconds': delay})
        time.sleep(delay)

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
    "x-requested-with": "XMLHttpRequest",
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

def _parse_bigshare_response(response):
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError(f"Bigshare returned invalid JSON (HTTP {response.status_code})") from exc

    details = payload.get('d')
    if not isinstance(details, dict):
        message = payload.get('Message') or payload.get('message') or 'missing response data'
        raise RuntimeError(f"Bigshare error (HTTP {response.status_code}): {message}")

    message = details.get('Message')
    # if message has "Invalid captcha code. Please try again."
    if message and "Invalid captcha code" in message:
        return {'error': message}

    records = details.get('Records') or []
    if records:
        return records[0]

    return {key: value for key, value in details.items()
            if key not in {'__type', 'Records', 'ResultToken'}}


def fetch_bigshare_captcha():
    fetch_started = time.perf_counter()
    response = _request_with_429_retry(
        lambda: requests.get(
            f"https://ipo.bigshareonline.com/Captcha.ashx?_={int(time.time() * 1000)}",
            headers=headers,
        )
    )
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError(f"Bigshare returned invalid captcha data (HTTP {response.status_code})") from exc

    token = payload.get('token') or payload.get('Token')
    image = payload.get('image') or payload.get('Image')
    if not token or not image:
        message = payload.get('Message') or payload.get('message') or 'missing token or image'
        raise RuntimeError(f"Bigshare captcha error (HTTP {response.status_code}): {message}")
    print({
        'event': 'bigshare_captcha_fetch',
        'http_status': response.status_code,
        'duration_ms': round((time.perf_counter() - fetch_started) * 1000),
        'payload_keys': sorted(payload),
        'token_length': len(token),
        'image_length': len(image),
    })

    # reader = easyocr.Reader(["en"], gpu=False)

    encoded_data = image.split(",", 1)[-1]
    image_bytes = base64.b64decode(encoded_data)
    cap_time = int(time.time() * 1000)
    captcha_path = Path(__file__).resolve().parent.parent / "app" / f"captcha-{cap_time}.png"
    captcha_path.write_bytes(image_bytes)
    print(f"Captcha image saved to {captcha_path}")

    recognition_started = time.perf_counter()
    texts = predict_captcha(
        driver=None,
        image_type="bigshare",
        image_path=captcha_path
    )
    print({
        'event': 'bigshare_recognition',
        'duration_ms': round((time.perf_counter() - recognition_started) * 1000),
        'result_type': type(texts).__name__,
        'result_length': len(str(texts).strip()),
    })
    # print(texts)
    # print(" ".join(texts))

    # delete the captcha image after processing
    # try:
    #     captcha_path.unlink()
    #     print(f"Captcha image {captcha_path} deleted after processing.")
    # except OSError as e:
    #     print(f"Error occurred while deleting captcha image {captcha_path}: {e}")

    return {'token': token, 'image': image, 'captcha_text': texts}


def big_pan(company, pan, max_captcha_attempts=3):
    for attempt in range(1, max_captcha_attempts + 1):

        # Get a fresh captcha every attempt
        captcha = fetch_bigshare_captcha()
        captcha_token = captcha['token']
        captcha_answer = captcha['captcha_text']

        data = {
            "Applicationno": "",
            "Company": company,
            "SelectionType": "PN",
            "PanNo": pan,
            "txtcsdl": "",
            "txtDPID": "",
            "txtClId": "",
            "ddlType": "0",
            "lang": "en",
            "CaptchaToken": captcha_token,
            "CaptchaAnswer": captcha_answer,
            "ResultToken": "",
        }

        request_started = time.perf_counter()

        response = _request_with_429_retry(
            lambda: make_request_through_tor(
                session,
                url,
                headers=headers,
                json=data,
                post=True
            )
        )

        print({
            'event': 'bigshare_submit',
            'captcha_attempt': attempt,
            'http_status': response.status_code,
            'duration_ms': round(
                (time.perf_counter() - request_started) * 1000
            ),
            'answer_type': type(captcha_answer).__name__,
            'answer_length': (str(captcha_answer).strip()),
            'response': response.text

        })

        result = _parse_bigshare_response(response)

        # Retry only when captcha was invalid
        if (
            isinstance(result, dict)
            and result.get('error')
            and "Invalid captcha code" in result['error']
        ):
            print({
                'event': 'bigshare_invalid_captcha',
                'attempt': attempt,
                'max_attempts': max_captcha_attempts,
            })

            if attempt < max_captcha_attempts:
                continue

            return result

        # Successful response or some other type of response
        return result

    return {
        'error': 'Captcha failed after maximum retry attempts'
    }
company = big_company("lumino")
big_pan(company, "OMOPS4188F", max_captcha_attempts=3)