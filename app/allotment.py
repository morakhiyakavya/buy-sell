# Imports
from datetime import datetime
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchWindowException, WebDriverException, NoAlertPresentException
import pandas as pd
import time
from fuzzywuzzy import process
from app.captcha import predict_captcha
from app.excel import process_excel_data, write_in_excel, print_details
import json
import os
from flask_socketio import emit 

# Configuration

# current_directory = os.getcwd()6
# driver_path = os.path.join(current_directory, 'chromedriver', 'chromedriver.exe')
driver_path = 'C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\chromedriver\\chromedriver.exe'
# headless = False  # or True for headless mode
headless = True  # or True for headless mode


website_configs = {

    'kfintech': {
        'website_name': 'kfintech',
        'website_url': 'https://evault.kfintech.com/ipostatus/',
        # 'dropdown': 'ddl_ipo', # ID
        'dropdown': '/html/body/div/div/div/div[2]/div/button', # xpath
        'pan': 'pan',
        # 'username_field': 'txt_pan', # ID
        'username_field': 'outlined-start-adornment', # ID
        # 'captcha_field': 'txt_captcha',
        # 'submit_button': 'btn_submit_query',
        'submit_button': '/html/body/div/div/div/div[2]/div/div/div/div/table/tbody[3]/tr/td/button',
        # 'back_button': 'lnk_new',
        'back_button': '/html/body/div[1]/div/div/div[2]/div/div/div/div/div/div[2]/div/button',
        # 'error_message': 'jconfirm-content',
        'error_message': '/html/body/div[2]/div[3]/div/div[1]/p', # xpath
        # 'error_message': 'MuiDialogContentText-root MuiTypography-root MuiTypography-body1 css-j90wp2',
        # 'close_dialog': 'btn.btn-blue',
        'close_dialog': '/html/body/div[2]/div[3]/div/div[2]/button', # xpath
        'refresh_button': 'refresh', # CLASS_NAME
        # Add other necessary identifiers
    },

    'bigshare': {
        'website_name': 'bigshare',
        'website_url': 'https://ipo.bigshareonline.com/IPO_Status.html',
        # 'website_url': 'https://ipo1.bigshareonline.com/IPO_Status.html',
        'dropdown': 'ddlCompany', # ID
        'pan': 'ddlSelectionType',
        'username_field': 'txtpan', # ID
        'captcha_field': 'captcha-input',
        'submit_button': 'btnSearch',
        'back_button': False,
        'error_message': 'confirm',
        'close_dialog': 'confirm',
        'refresh_button': False,
        # 'refresh_button': 'refresh-captcha',
        # Add other necessary identifiers
    },

    'linkin': {
        'website_name': 'linkin',
        'website_url': 'https://www.linkintime.co.in/Initial_Offer/public-issues.html',
        'dropdown': 'ddlCompany', # ID
        'pan': 349,
        'username_field': 'txtStat', # ID
        'captcha_field': False,
        'submit_button': 'btnsearc',
        'back_button': 'chknextAppln', # ID
        'error_message': 'lblMessage', # ID
        'close_dialog': 'showcss', # CLASS_NAME
        'refresh_button': False,
        # Add other necessary identifiers
    },

    'skyline': {# Skyline is left cux of error message
        'website_name': 'skyline',
        'website_url': 'https://www.skylinerta.com/ipo.php',
        'dropdown': 'company',# ID
        'pan': False,
        'username_field': 'pan', # ID
        'captcha_field': False,
        'submit_button': 'iposearch', #CLASS_NAME
        'back_button': False,
        # 'error_message': 'jconfirm-content',
        # 'close_dialog': 'btn.btn-blue',
        # 'refresh_button': 'refresh',
        # Add other necessary identifiers
    },

    'purva': { #Purva is left to done.
        'website_name': 'purva',
        'website_url': 'https://purvashare.com/investor-service/ipo-query',
        'dropdown': 'company_id', #ID
        'pan': False,
        'username_field': 'panNumber',#NAME
        'captcha_field': False,
        'submit_button': 'submit', #'//input[@value=" Search "]'  XPATH or 'submit' NAME
        'back_button': False,
        'error_message': 'div.alert b',#CSS SELECTOR
        'close_dialog': 'div.alert button.btn-close',#CSS SELECTOR  
        'refresh_button': False,
        # Add other necessary identifiers
    },
    # 'cameoindia': {
    #     'website_name': 'cameoindia',
    #     'website_url': 'https://ipo.cameoindia.com/',
    #     'dropdown': 'company_id', #ID
    #     'pan': False,
    #     'username_field': 'panNumber',#NAME
    #     'captcha_field': True,
    #     'submit_button': 'submit', #'//input[@value=" Search "]'  XPATH or 'submit' NAME
    #     'back_button': False,
    #     'error_message': 'div.alert b',#CSS SELECTOR
    #     'close_dialog': 'div.alert button.btn-close',#CSS SELECTOR  
    #     'refresh_button': False,
    # },
    # Making the configuration for chittorgarh so we get details about the ongoing IPO's
    'chittorgarh': {
        'website_name': 'chittorgarh',
        'website_url': 'https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/?year=2024',
        'green': 'color-green',
        'lightyellow': 'color-lightyellow',
        'aqua': 'color-aqua',

    },
    # Define configurations for other websites similarly
}



class BaseScraper:
    
    """
    Base class for web scraping.

    Args:
    - driver_path: The path to the Chrome WebDriver
    - website: The name of the website to scrape
    - headless: A boolean indicating whether to run the browser in headless mode

    Through this the driver is initialized and closed.
    """
    
    def __init__(self, driver_path, website, headless=True):
        
        """
        Initialize the object.

        Args:
            driver_path (str): The path to the driver executable.
            website (str): The URL of the website to scrape.
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to False.
        """

        self.driver_path = driver_path
        self.website = website
        self.headless = headless
        self.initialize_driver()

    def initialize_driver(self):
        
        """
        Initializes the web driver and sets up necessary configurations.

        This method initializes the web driver using the Chrome browser and sets up
        any necessary configurations such as headless mode and driver path. It also
        sets up the web driver wait and navigates to the website URL specified in
        the configuration.

        Args:
            None

        Returns:
            None
        """
        
        self.config = website_configs[self.website]
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        os.environ["PATH"] += os.pathsep + self.driver_path
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get(self.config['website_url'])

    def close(self):
        """
        Closes the driver and marks it as not available.

        Args:
            None

        Returns:
            None
        """
        
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            self.driver = None  # Ensure the driver is marked as not available

class Scrape_Website(BaseScraper):
    
    """
    A class for scraping a website.

    This class inherits from the BaseScraper class and provides methods for selecting options from a dropdown menu,
    inputting a username and submitting a form, solving a captcha, and handling dialog boxes.

    Attributes:
        driver_path (str): The path to the driver executable.
        website (str): The URL of the website to scrape.
        headless (bool): Whether to run the browser in headless mode.
        result_dict (dict): A dictionary to store the scraping results.
        message (str): A message to store any error or informational messages.
    """

    def __init__(self, driver_path, website, room,socketio, headless=True):
        """
        Initialize the Scrape_Website class.

        Args:
            driver_path (str): The path to the driver executable.
            website (str): The URL of the website to scrape.
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to False.
        """
        
        super().__init__(driver_path, website, headless)
        time.sleep(5)
        self.result_dict = {}
        self.message = ""
        self.allotment = 0
        self.total_shares = 0
        self.mistakes = 0
        self.room = room
        self.socketio = socketio

    def log(self, data, room):
        # Emit a SocketIO event to the client
        self.socketio.emit('log', data, room=room)
            
    def select_dropdown_option(self, ipo):
        
        """
        Selects the specified option from a dropdown menu based on the given IPO.

        Args:
            ipo (str): The IPO to select from the dropdown menu.

        Returns:
            bool: True if the option was successfully selected, False otherwise.

        Raises:
            Exception: If there is an error selecting the dropdown option.
        """
        try:
            dropdown_id = self.config['dropdown']
            if self.config['website_name'] == 'kfintech':
                dropdown_element = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, dropdown_id)))
                dropdown_element.click()
                print("Clicked on dropdown")
            else:
                dropdown_element = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.ID, dropdown_id)))
                dropdown = Select(dropdown_element)
                available_options = [opt.text for opt in dropdown.options]
                user_input = ipo.title()
                matching_option, confidence = process.extractOne(user_input, available_options)
                print(f"Matching option: {matching_option}, confidence: {confidence}")
                if confidence >= 20:
                    dropdown.select_by_visible_text(matching_option)
                    print(f"Selected option: {matching_option}")
                    self.log({"type": "selected_option", "ipo": matching_option}, self.room)
                else:
                    self.message = "No matching options found for the specified IPO."
                    return False
            if self.config['website_name'] != 'kfintech':
                website = self.config['website_name']
                pan_id = self.config['pan']
                if website != 'bigshare':
                    if pan_id:
                        select_element = self.driver.find_element(By.ID, pan_id)
                        select_element.click()
                if website == 'bigshare':
                    select_element = Select(self.driver.find_element(By.ID, pan_id))
                    desired_option_text = 'PAN Number'
                    select_element.select_by_visible_text(desired_option_text)
                return True
        except Exception as e:
            print(f"Error selecting dropdown option: {e}")
            raise

    def input_username_and_submit(self, username):
            
            """
            Inputs the given username into the username field, solves the captcha, and submits the form.
            If there are any errors during submission, it retries a maximum of 2 times before giving up.
            
            Args:
                username (str): The username to input into the username field.
            
            Returns:
                bool: True if the submission is successful and data scraping can proceed, False otherwise.
            
            Raises:
                Exception: If there is an error while inputting the username and submitting.
            """
        
            try:
                retry_count = 0
                max_retries = 2  # Example limit, adjust as needed
                while retry_count < max_retries:
                    username_field_id = self.config['username_field']
                    if self.config['website_name'] == 'purva':
                        username_field = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.NAME, username_field_id)))
                    else:
                        username_field = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, username_field_id)))
                    print(f"Username field found: {username_field}")
                    username_field.clear()
                    username_field.send_keys(username.replace(" ", "").strip().upper())
                    # Assuming captcha solving is required here; implement as needed.
                
                    # solve_captcha_start_time = time.time()
                
                    self.solve_captcha_and_submit()
                
                    # solve_captcha_end_time = time.time()
                    # print(f"Duration for solving captcha and submitting: {solve_captcha_end_time - solve_captcha_start_time} seconds")

                    # Check for errors after submission
                    # handle_dialog_box_start_time = time.time()

                    error_type = self.handle_dialog_box()
                    
                    # handle_dialog_end_time = time.time()
                    # print(f"Duration for handling dialog box: {handle_dialog_end_time - handle_dialog_box_start_time} seconds")

                    if error_type == "captcha_error":
                        time.sleep(2)  # Add a delay before retrying captcha solving
                        retry_count += 1
                        print("Captcha error, retrying...")
                        refresh_button = self.config['refresh_button']
                        if refresh_button:
                            refresh = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CLASS_NAME, refresh_button)))
                            refresh.click()
                        continue  # Retry captcha solving
                    elif error_type == "no_error":
                        return True  # Success, proceed to data scraping
                    else:
                        print(f"{error_type} error, stopping retries.")
                        time.sleep(2) # Add a delay before moving to the next username
                        return error_type  # For unknown errors, you might choose to stop or log and continue
                    
                print("Max captcha retries reached, moving to next username.")
                return False  # Exceeded retries, log this and move to next username
            except Exception as e:
                print(f"Error inputting username and submitting: {e}")
                raise

    def solve_captcha_and_submit(self):
        
        """
        Solves the captcha and submits the form.

        This method implements the logic to solve the captcha based on the website's configuration.
        It retrieves the captcha type from the configuration, predicts the captcha solution,
        and fills in the captcha field on the webpage. Finally, it clicks the submit button.

        If the website does not require a captcha, this method is used to Submit the button for searching application Details.

        Args:
            self: The instance of the class.

        Returns:
            None
        """
        
        captcha_type = self.config['website_name']  # Replace with actual captcha type
        if captcha_type == 'bigshare':
            captcha_input = predict_captcha(self.driver,captcha_type)
            captcha_id = self.config['captcha_field']
            captcha_field = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.ID, captcha_id)))
            captcha_field.clear()
            captcha_field.send_keys(captcha_input)
        submit_id = self.config['submit_button']
        if self.config['website_name'] == 'skyline':
            submit_button = self.driver.find_element(By.CLASS_NAME, submit_id)
        elif self.config['website_name'] == 'purva':
            submit_button = self.driver.find_element(By.NAME, submit_id)
        elif self.config['website_name'] == 'kfintech':
            submit_button = self.driver.find_element(By.XPATH, submit_id)
        else:
            submit_button = self.driver.find_element(By.ID, submit_id)
        submit_button.click()

    def handle_dialog_box(self):
        
        """
        Handles the dialog box based on the configuration of the website.

        Returns:
            str: The error message or status indicating the result of handling the dialog box.
                Possible return values:
                - "captcha_error": If the error message indicates a captcha error.
                - "Invalid Pan.": If the error message indicates an invalid PAN.
                - "no_error": If no error message was found or the dialog box was successfully handled.
                - The actual error message: If a specific error message was found.
        Raises:
            Exception: If an error occurs while handling the dialog box.
        """
        
        if self.config['website_name'] == 'kfintech':
            try:
                div_lookup = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[3]/div')))
                if div_lookup:
                    print("Dialog box found")
                error_message = self.config['error_message']
                
                message_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, error_message)))
                message_text = message_element.text
                print(f"Message text HERE : {message_text}")
                close_dialog = self.config['close_dialog']
                if close_dialog:
                    close_button = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, close_dialog)))
                    print("Close Dialog : ",close_dialog)
                    close_button.click()
                    if div_lookup:
                        print("Dialog box found")
                        # refresh driver
                        self.driver.refresh()
                        self.select_dropdown_option(self)

                    # known_captcha_errors = ["CAPTCHA is invalid or Expired", "Captcha is invalid."]
                    # # Check if the message matches known captcha errors
                    # matching_option, confidence = process.extractOne(message_text, known_captcha_errors)
                    # if confidence >= 90:  # Adjust threshold as needed    
                    #     return "captcha_error"
                return message_text
            except TimeoutException:
                return "no_error"  # No error message was found
            except Exception as e:
                print(f"Error handling dialog box: {str(e)}")
                raise

        elif self.config['website_name'] == 'bigshare':
            try:
                error_message = self.config['error_message']
                message_element = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.CLASS_NAME, error_message)))
                message_text = 'No Record Found'
                close_dialog = self.config['close_dialog']
                if close_dialog:
                    close_button = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CLASS_NAME, close_dialog)))
                    close_button.click()
                return message_text
            except TimeoutException:
                pass
            try:
                # Check for the "lblpan" element indicating a PAN error
                lblpan_element = WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.ID, 'lblpan')))
                if lblpan_element:
                    return "Invalid Pan."
            except TimeoutException:
                # If not found, proceed to check for the next element
                pass
            try:
                # Check for the "lblcaptcha" element indicating a captcha error
                lblcaptcha_element = WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.ID, 'lblcaptcha')))
                if lblcaptcha_element:
                    return "captcha_error"
            except TimeoutException:
                # If none of the specific elements are found, assume no error or handle as needed
                return "no_error"

        elif self.config['website_name'] == 'linkin':
            try:
                try:
                    alert = self.driver.switch_to.alert
                    alert.accept()
                    return "undefined"
                except NoAlertPresentException:
                    pass 
                dialog = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CLASS_NAME, 'ui-dialog')))
                # dialog_title = dialog.find_element(By.CLASS_NAME, 'ui-dialog-title').text
                error_message = self.config['error_message']
                message_element = WebDriverWait(dialog, 2).until(
                    EC.visibility_of_element_located((By.ID, error_message)))
                message_text = message_element.text       
                close_dialog = self.config['close_dialog']
                if close_dialog:
                    close_button = dialog.find_element(By.CLASS_NAME, close_dialog)
                    close_button.click()
                if message_text is not None:
                    return message_text
                # return message_text
            except TimeoutException:
                return "no_error"  # No error message was found
            except Exception as e:
                print(f"Error handling dialog box: {str(e)}")
                raise

        elif self.config['website_name'] == 'skyline':
            return "no_error"

        elif self.config['website_name'] == 'purva':
            error_message = self.config['error_message']
            try:
                message_element = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CSS_SELECTOR, error_message)))
                message_text = message_element.text
                print(f"Error message purva: {message_text}")
                close_dialog = self.config['close_dialog']                
                close_button = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CSS_SELECTOR, close_dialog)))
                print(f"Close button purva: {close_button}")
                close_button.click()
                return message_text
            except TimeoutException:
                return "no_error"
            except Exception as e:
                print(f"Error handling dialog box: {str(e)}")
                raise
        else:
            return "no_error"

    def scrape_data(self):
        
        """
        Scrapes data from different websites based on the website name specified in the configuration.
        Returns the scraped data as a dictionary.
        If an error occurs during scraping, returns None.
        """
        
        if self.config['website_name'] == 'kfintech':
            try:
                # Wait for the main table container to be visible
                output_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'MuiTableContainer-root')))
                
                if output_element:
                    html_source = self.driver.page_source
                    # Parse the HTML
                    soup = BeautifulSoup(html_source, 'html.parser')

                    # Initialize result_data dictionary
                    result_data = {}

                    # Find all relevant divs
                    divs = soup.find_all('div', class_='MuiCardContent-root css-1qw96cp')

                    # Define the order of keys
                    keys = [
                        'application_number',
                        'category',
                        'name',
                        'dp_id_client_id',
                        'pan',
                        'applied',
                        'allotted'
                    ]

                    # Iterate over each div and extract data
                    for i, div in enumerate(divs, start=1):
                        
                        # Extract bold text from the div
                        bold_texts = div.find_all('b')
                        
                        # Initialize a dictionary to hold data for the current div
                        current_data = {}
                        securities_allotted = int(bold_texts[6].text.strip())
                        print(f"Securities Allotted: {securities_allotted}")
                        if securities_allotted > 0:
                            self.allotment += 1
                            self.total_shares += securities_allotted
                            print(f" Allotted : {self.allotment}")
                            self.log({"type": "allotted", "allotment": self.allotment}, self.room)
                            print(f" Total shares : {self.total_shares}")
                            self.log({"type": "total_shares", "total_share": self.total_shares}, self.room)
                            # Assign bold text to keys in the defined order
                        for index, bold in enumerate(bold_texts):
                            text = bold.get_text(strip=True)
                            if index < len(keys):
                                key = keys[index]
                                current_data[f"{key}_{i}"] = re.sub(r'\s+', ' ', text.strip())
                        
                    
                        # Merge current data into result_data
                        result_data.update(current_data)
                            # If any shares are allotted, update the counters

                            # # Store the results in the dictionary
                            # result_data[f'applicant_name_{i}'] = name
                            # result_data[f'application_number_{i}'] = application_number
                            # result_data[f'category_{i}'] = category
                            # result_data[f'dp_id_{i}'] = dp_id
                            # result_data[f'pan_{i}'] = pan
                            # result_data[f'shares_allotted_{i}'] = securities_allotted
                            # result_data[f'shares_applied_{i}'] = securities_applied
                    print(result_data)
                    return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None



        elif self.config['website_name'] == 'bigshare':
            try:
                div_element = self.driver.find_element(By.ID,"dPrint")
                # Find all label elements inside the table inside the div
                label_elements = div_element.find_elements(By.TAG_NAME,"label")

                # Extract data from label elements and store them in variables
                alloted = label_elements[4].text.strip()
                try:
                    alloted = int(alloted)
                except ValueError:
                    pass
                result_data = {
                    'name': label_elements[2].text,
                    'alloted': alloted,
                    'applied': int(label_elements[3].text),
                    'dp_id': label_elements[1].text,
                    'application_no': label_elements[0].text,
                    'error' : None
                }
                if type(alloted) == int:
                    self.allotment += 1
                    self.total_shares += alloted
                    print(f" Alloted : {self.allotment}")
                    self.log({"type": "alloted", "allotment": self.allotment}, self.room)
                    print(f" Total shares : {self.total_shares}")
                    self.log({"type": "total_shares", "total_share": self.total_shares}, self.room)
                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None

        elif self.config['website_name'] == 'linkin':
            try:
                # start_time = time.time()
                output_element = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.ID, 'tbl_DetSec')))
                
                if output_element :
                    # fetch_time = time.time()
                    html_source = self.driver.page_source
                    # soup_time = time.time()
                    soup = BeautifulSoup(html_source, 'html.parser')

                    # Extract the table within the div with id="tbl_DetSec"
                    tables = soup.select('#tbl_DetSec table')
                    
                    result_data = {}
                    for i, table in enumerate(tables,1):
                        applicant_name = table.find(text='Sole / 1st Applicant').find_next('td').text.strip()
                        error = None
                        if not applicant_name:
                            applicant_name = 'Client/Id not found'
                            error = 'Client/Id not found'

                        securities_applied = int(table.find(text='Securities applied').find_next('td').text.strip())
                        cutoff_price = int(table.find(text='Cut off Price').find_next('td').text.strip())
                        securities_allotted = int(table.find(text='Securities Allotted').find_next('td').text.strip())
                        amount_adjusted = int(table.find(text='Amount Adjusted').find_next('td').text.strip())
                        heading_text = table.find('tr', class_='heading_table').th.span.text.strip()
                        formtype = heading_text.split(' - ')[1]

                        if securities_allotted > 0:
                            self.allotment += 1
                            self.total_shares += securities_allotted
                            print(f" Alloted : {self.allotment}")
                            self.log({"type": "alloted", "allotment": self.allotment}, self.room)
                            print(f" Total shares : {self.total_shares}")
                            self.log({"type": "total_shares", "total_share": self.total_shares}, self.room)
                        
                        result_data[f'applicant_name_{i}'] = applicant_name
                        result_data[f'Type_{i}'] = formtype
                        result_data[f'shares_allotted_{i}'] = securities_allotted
                        result_data[f'shares_applied_{i}'] = securities_applied
                        result_data[f'application_amount_{i}'] = cutoff_price
                        result_data[f'amount_adjusted_{i}'] = amount_adjusted
                        result_data['error'] = error
                    # parse_time = time.time()
                    # Calculate the durations
                    # duration_fetch = fetch_time - start_time
                    # duration_parse = parse_time - soup_time
                    # total_duration = parse_time - start_time
                    
                    # print(f"Time to fetch page: {duration_fetch} seconds")
                    # print(f"Time to parse HTML and extract data: {duration_parse} seconds")
                    # print(f"Total time: {total_duration} seconds")

                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None
        
        elif self.config['website_name'] == 'skyline':
            try:
                div_element = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.CLASS_NAME, "fullwidth.resultsec")))
                self.driver.execute_script("arguments[0].scrollIntoView();", div_element)
                print("Scrolled to the element -> ", div_element)
                applicant_name =  div_element.find_elements(By.TAG_NAME,"p")

                if len(applicant_name) != 0:
                    shares_allotted = int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(3)")[0].text)
                    result_data = {
                    'applicant_name': div_element.find_elements(By.TAG_NAME,"p")[1].text.split(" : ")[1],
                    'shares_allotted': shares_allotted,
                    'shares_applied': float(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(1)")[0].text),
                    'pan_number': div_element.find_elements(By.TAG_NAME,"p")[4].text.split(" : ")[1],
                    'application_amount': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(2)")[0].text),
                    'amount_adjusted': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(4)")[0].text),
                    'amount_refunded': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(2)")[0].text),
                    'status': div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(9)")[0].text,
                    'error' : None
                }
                    if shares_allotted > 0:
                        self.allotment += 1
                        self.total_shares += shares_allotted
                        print(f" Alloted : {self.allotment}")
                        self.log({"type": "alloted", "allotment": self.allotment}, self.room)
                        print(f" Total shares : {self.total_shares}")
                        self.log({"type": "total_shares", "total_share": self.total_shares}, self.room)

                if len(applicant_name) == 0:
                    result_data = {
                        'error' : "No data found"
                    }
                print(result_data)
                return result_data
            except NoSuchElementException:
                result_data = {'error' : "NoSuchElement found"}
                print(f"Error nosuchelement: {result_data}")
                return result_data
            except TimeoutException:
                result_data = {'error' : "TimeoutException"}
                print(f"Error timeout: {result_data}")
                return result_data
            except Exception as e:
                print(f"Error scraping data: {str(e)}")
                # print(f"Data: {result_data}")
                return None

        # Still Left to do
        elif self.config['website_name'] == 'purva':
            try:
                result_data = {
                    'application_number': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_l1']"))).text,
                    'category': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label1']"))).text,
                    'name': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label2']"))).text,
                    'client_id': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_dpclid']"))).text,
                    'pan': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_pan']"))).text,
                    'applied': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label2']"))).text,
                    'securities_allotted': WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_allot']"))).text,
                    'error' : None
                }
                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None

    def run(self, ipo, usernames): # self.room will be user id
        
        """
        Executes the scraping process for a list of usernames.

        Args:
            ipo (str): The dropdown option to select.
            usernames (list): A list of usernames to process.

        Returns:
            dict: A dictionary containing the results of the scraping process for each username.
        """
        run_start_time = time.time()
        # results = {}
        
        max_retries = 3
        print(f"Total pan numbers {len(usernames)}")
        self.log({"type": "total_pan_numbers", "count": len(usernames)}, self.room)
        
        # dropdown_start_time = time.time()
        if self.config['website_name'] != 'purva':
            self.select_dropdown_option(ipo)
        
        # dropdown_end_time = time.time()
        # print(f"Duration for dropdown: {dropdown_end_time - dropdown_start_time} seconds")
        
        for username in usernames:
            one_username_start_time = time.time()
            retries = 0
            while retries < max_retries:
                try:
                    if username not in self.result_dict:  # Check if this username has already been processed
                        # if self.select_dropdown_option(ipo):

                        # input_start_time = time.time()
                        if self.config['website_name'] == 'purva':
                            self.select_dropdown_option(ipo)
        
                        writing_pan = self.input_username_and_submit(username)
        
                        # input_end_time = time.time()
                        # print(f"Duration for input and submit: {input_end_time - input_start_time} seconds")
                        
                        self.log({"type": "processing_username", "username": username}, self.room)
                        username_index = usernames.index(username) + 1
                        self.log({"type": "processing_on", "checked": username_index}, self.room)
                        print(f"Left pan numbers {len(usernames) - username_index}")
                        self.log({"type": "left_pan_numbers", "count": len(usernames) - username_index}, self.room)
                        if writing_pan == True:
                            
                            # scrape_start_time = time.time()
                            
                            data = self.scrape_data()

                            # scrape_end_time = time.time()
                            # print(f"Duration for scraping data: {scrape_end_time - scrape_start_time} seconds")
                            
                            if data:
                                self.result_dict[username] = data
                            else:
                                self.result_dict[username] = {'error': "Failed to scrape data or data not found"}
                            # Assuming you want to go back or refresh between usernames
                            # prepare_start_time = time.time()
                            
                            self.prepare_for_next_username()

                            # prepare_end_time = time.time()
                            # print(f"Duration for preparing for next username: {prepare_end_time - prepare_start_time} seconds")

                        else:
                            self.result_dict[username] = {'error': writing_pan}
                            self.mistakes += 1
                            self.log({"type": "mistakes", "count": self.mistakes}, self.room)
                            
                    break  # Exit the loop if everything goes well for this username
                except (NoSuchWindowException, WebDriverException) as e:
                    print(f"Encountered an error: {e}. \nRetrying...")
                    self.initialize_driver() # Re-initialize the driver for retry
                    self.select_dropdown_option(ipo)
                    retries += 1
                    if retries >= max_retries:
                        print(f"Maximum retries reached for {username}. Moving to next username.")
                        self.result_dict[username] = {'error': "Maximum retries reached"}
                        self.mistakes += 1
                        self.log({"type": "mistakes", "count": self.mistakes}, self.room)
                        break
                except Exception as e:
                    print(f"Encountered an error with {username}: {str(e)}. \nRetrying...")
                    self.close()  # Close the current driver
                    self.initialize_driver()  # Re-initialize the driver for retry
                    self.select_dropdown_option(ipo)
                    retries += 1
                    if retries >= max_retries:
                        print(f"Maximum retries reached for {username}. Moving to next username.")
                        self.result_dict[username] = {'error': "Maximum retries reached"}
                        self.mistakes += 1
                        self.log({"type": "mistakes", "count": self.mistakes}, self.room)
                        break
            one_username_end_time = time.time()
            one_username_duration = one_username_end_time - one_username_start_time
            print(f"Duration for {username}: {one_username_duration} seconds")
            print("*"*20)
        run_end_time = time.time()
        run_duration = run_end_time - run_start_time
        print(f"Total run function duration: {run_duration} seconds")
        return self.result_dict

    def prepare_for_next_username(self):
            
            """
            Prepares the application for the next username by going back to the initial form or refreshing the page.

            This method implements the logic to navigate back or refresh the page to reset the form state.

            Args:
                self: The instance of the class.

            Returns:
                None
            """
            
            try:
                back_id = self.config['back_button']
                if back_id:
                    if self.config['website_name'] == 'kfintech':
                        back_button = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.XPATH, back_id)))
                    else:
                        back_button = WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((By.ID, back_id)))
                    back_button.click()
                    # print("Going back to the initial form...")
                else:
                    pass
            except NoSuchElementException:
                # If the back button is not found, assume it's not needed or handle as needed
                print("Back button not found, refreshing the page...")
                pass
            except Exception as e:
                print(f"Error preparing for next username: {str(e)}")
                raise

def scrape_data_from_websites(driver_path, company, ipo, usernames, room, socketio, headless=True):
    """
    Scrape data from multiple websites based on the given company and IPO.

    Args:
        driver_path (str): The path to the Chrome WebDriver.
        company (str): The name of the company.
        ipo (str): The IPO name.
        usernames (list): A list of usernames to process.
        headless (bool): Whether to run the browser in headless mode.

    Returns:
        dict: A dictionary containing the results of the scraping process for each username.
    """
    scraper = Scrape_Website(driver_path, company, room, socketio, headless)
    results = scraper.run(ipo, usernames)
    print_details(company, ipo, results)
    return results

class IPODetailsScraper(BaseScraper):

    def __init__(self, driver_path, website, headless=True):
        super().__init__(driver_path, website, headless)

    def scrape_ipo_details(self):
        """
        Scrapes IPO details from the website.

        This method navigates through the website initialized by the BaseScraper and
        extracts IPO details based on their row color coding. The extracted details are
        categorized and returned as a dictionary.

        Args:
            None

        Returns:
            dict: A dictionary containing categorized IPO details.
        """
        # Mapping class names to their corresponding categories
            
        # Selector for rows with the specific classes
        row_selector = "//tr[@class='color-green' or @class='color-lightyellow' or @class='color-aqua']"

        # Find all rows matching the selector
        rows = self.driver.find_elements(By.XPATH, row_selector)

        # Lists to hold IPO details for each class
        ipo_details_green = []
        ipo_details_lightyellow = []
        ipo_details_aqua = []

        # Function to extract details from a row
        
        def extract_details(row):
            name = row.find_element(By.XPATH, ".//td[1]/a").text
            open_date = row.find_element(By.XPATH, ".//td[2]").text
            close_date = row.find_element(By.XPATH, ".//td[3]").text
            listing_date = row.find_element(By.XPATH, ".//td[4]").text
            price = row.find_element(By.XPATH, ".//td[5]").text
            issue_size = row.find_element(By.XPATH, ".//td[6]").text
            lot_size = row.find_element(By.XPATH, ".//td[7]").text
            listing_at = row.find_element(By.XPATH, ".//td[8]").text

            return {
                "Name": name,
                "Open Date" : dateSetup(open_date),
                "Close Date" : dateSetup(close_date),
                "Listing Date": dateSetup(listing_date), 
                "Price": price,
                "Issue Size": issue_size,
                "Lot Size": lot_size,
                "Listing At": listing_at,
            }

        # Iterate over each row and add details to the corresponding list based on its class
        for row in rows:
            class_attribute = row.get_attribute("class")
            ipo_details = extract_details(row)
            
            if "color-green" in class_attribute:
                ipo_details_green.append(ipo_details)
            elif "color-lightyellow" in class_attribute:
                ipo_details_lightyellow.append(ipo_details)
            elif "color-aqua" in class_attribute:  # Assuming there are rows with this class
                ipo_details_aqua.append(ipo_details)

        # Print or use the extracted IPO details
        # print("Green IPOs:", ipo_details_green)
        # print("Light Yellow IPOs:", ipo_details_lightyellow)
        # print("Aqua IPOs:", ipo_details_aqua)  # Adjust usage based on actual presence
        self.close()
        return ipo_details_green, ipo_details_lightyellow, ipo_details_aqua


def dateSetup(date_string):
    if date_string:
        if isinstance(date_string, str):
            try:
                print(f"Parsing date string: {date_string}")
                date_object = datetime.strptime(date_string, '%b %d, %Y')
                print(f"Converted date: {date_object}")
            except ValueError as e:
                print(f"Error parsing date: {e}")
                # Fallback to current date if parsing fails
                date_object = datetime.now()
        elif isinstance(date_string, datetime):
            print(f"Received datetime object: {date_string}")
            date_object = date_string
        else:
            print("Invalid type for date_string. Expected str or datetime.")
            date_object = datetime.now()
    else:
        print("Date string is empty.")
        date_object = datetime.now()
    
    return date_object
