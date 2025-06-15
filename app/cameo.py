import random
import requests
from bs4 import BeautifulSoup
from pytesseract import image_to_string
import pytesseract
import cv2
from tor import make_request_through_tor

class CaptchaSolver:
    def __init__(self, tesseract_path):
        self.tesseract_path = tesseract_path
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def solve(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Image not found or unable to load.")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 11, 2)
        binary = cv2.fastNlMeansDenoising(binary, None, 30, 7, 21)
        return pytesseract.image_to_string(binary, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()


class WebScraper:
    def __init__(self, url, user_agents,session=None):
        self.url = url
        self.user_agents = user_agents
        self.session = session or requests.Session() 

    def get_headers(self):
        return {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": self.url,
            "referer": self.url,
            "user-agent": random.choice(self.user_agents),
        }

    def get_page_content(self):
        response = make_request_through_tor(self.session,self.url, headers=self.get_headers())
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        else:
            raise Exception(f"Failed to retrieve page. Status code: {response.status_code}")

    def download_captcha(self, captcha_url, save_path):
        captcha_response = make_request_through_tor(self.session,captcha_url, headers=self.get_headers())
        with open(save_path, "wb") as f:
            f.write(captcha_response.content)
        print(f"CAPTCHA image saved to {save_path}")
        return save_path


class IpoStatus:
    def __init__(self, url, user_agents, captcha_solver, session=None):
        self.url = url
        self.user_agents = user_agents
        self.captcha_solver = captcha_solver
        self.session = session or requests.Session()
        self.scraper = WebScraper(url, user_agents, session=self.session)

    def fetch_form_data(self):
        soup = self.scraper.get_page_content()
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        captcha_image_url = soup.find('img', {'id': 'imgCaptcha'})['src']
        return viewstate, eventvalidation, captcha_image_url

    def submit_form(self, viewstate, eventvalidation, captcha_solution, pancard, company):
        data = {
            "ScriptManager1": "OrdersPanel|btngenerate",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__EVENTVALIDATION": eventvalidation,
            "drpCompany": company,
            "ddlUserTypes": "PAN NO",
            "txtfolio": pancard,
            "txt_phy_captcha": captcha_solution,
            "__ASYNCPOST": "true",
            "btngenerate": "Submit",
        }

        post_response = make_request_through_tor(self.session,self.url, headers=self.scraper.get_headers(), data=data, post=True)
        if post_response.status_code == 200:
            soup = BeautifulSoup(post_response.text, 'html.parser')
            div = soup.find('table', {'class': 'table table-bordered text-center'})
            print("POST request successful.")
            if div:
                if "NO DATA FOUND FOR THIS SEARCH KEY" in div.text:
                    print("Mostly PAN NO is invalid.")
                    return True
                print("Form submitted successfully.")
                print(div.prettify())
                # extract the table details from the div as a dictionary
                table_data = {}
                headers = div.find_all('th')
                cols = div.find_all('td')
                i = 0
                for header,col in zip(headers, cols):
                    if i == 0:
                        key = "PAN NO"
                        value = "omops4188f"
                        table_data[key] = value
                    key = header.text.strip()
                    value = col.text.strip()
                    table_data[key] = value
                    i += 1
                print("Table Data:")
                for key, value in table_data.items():
                    print(f"{key}: {value}")
                

                return True
            else :
                strip = post_response.text.split("</footer>")[1].strip()

                if 'Captcha entered is incorrect' in strip:
                    print("invalid captcha.")
                    return  False
                elif "PAN NO should be 10 digit" in strip:
                        print("PAN NO should be 10 digit.")
                        return True
                else:
                    print("Captcha is invalid.")
                    print(post_response.text)
                    return False
        else:
            print(f"POST request failed. Status code: {post_response.status_code}")
            return False

def get_choice(url, user_agents):
    response = requests.get(url, headers={"User-Agent": random.choice(user_agents)})
    soup = BeautifulSoup(response.text, 'html.parser')
    company_dropdown = soup.find('select', {'id': 'drpCompany'})
    companies = {option.text.strip(): option['value'] for option in company_dropdown.find_all('option')[1:] if option['value'] != ''}
    print("Available companies:")
    print("-"*20)
    i = 1
    for value, name in companies.items():
        print(f"{i}) {value}: {name}")
        i += 1
    # choice can be 1..n or value or key
    print("-"*20)
    while True:
        choice = input("Enter the company name or value: ")
        if choice in companies:
            print(f"You selected: {companies[choice]}")
            return companies[choice]
            break
        elif choice.isdigit() and int(choice) in range(1, len(companies) + 1):
            selected_value = list(companies.keys())[int(choice) - 1]
            print(f"You selected: {companies[selected_value]}")
            return companies[selected_value]
            break
        else:
            print("Invalid choice. Please try again.")

def main():
    url = "https://ipostatus1.cameoindia.com/"
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/99.0",
    ]
    captcha_solver = CaptchaSolver(tesseract_path=r'C:\\Users\\kavya\\Downloads\\Tesseract-OCR\\tesseract.exe')
    # Create a session once
    session = requests.Session()
    company = get_choice(url,user_agents)
     # Retry mechanism
    attempts = 3
    for attempt in range(attempts):
        ipo_status = IpoStatus(url, user_agents, captcha_solver, session=session)
        # Step 1: Fetch form data
        viewstate, eventvalidation, captcha_image_url = ipo_status.fetch_form_data()
        # give choice to user to select company name
        

        # Step 2: Download and solve CAPTCHA
        captcha_image_path = ipo_status.scraper.download_captcha(url + captcha_image_url, "captcha.png")
        
        captcha_solution = captcha_solver.solve(captcha_image_path)
        print(f"Solved CAPTCHA: {captcha_solution}")

        # Step 3: Submit the form
        success = ipo_status.submit_form(viewstate, eventvalidation, captcha_solution,"omops4188f",company)
        
        if success:
            print("Form submission was successful!")
            break  # Exit the loop if successful
        else:
            print(f"Attempt {attempt + 1} failed. Retrying...")

main()


