# Imports 

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchWindowException, WebDriverException
import pandas as pd
import time
from fuzzywuzzy import process
from app.captcha import predict_captcha
from app.excel import process_excel_data, write_in_excel, print_details
import json
import os

# Configuration

# current_directory = os.getcwd()
# driver_path = os.path.join(current_directory, 'chromedriver', 'chromedriver.exe')
driver_path = 'C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\chromedriver\\chromedriver.exe'
headless = False  # or True for headless mode

class BaseScraper:
    
    """
    Base class for web scraping.

    Args:
    - driver_path: The path to the Chrome WebDriver
    - website: The name of the website to scrape
    - headless: A boolean indicating whether to run the browser in headless mode

    Through this the driver is initialized and closed.
    """
    
    def __init__(self, driver_path, website, headless=False):
        
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

    def __init__(self, driver_path, website, headless=False):
        """
        Initialize the Scrape_Website class.

        Args:
            driver_path (str): The path to the driver executable.
            website (str): The URL of the website to scrape.
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to False.
        """
        
        super().__init__(driver_path, website, headless)
        self.result_dict = {}
        self.message = ""
        self.allotment = 0
        self.total_shares = 0

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
            dropdown_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, dropdown_id)))
            dropdown = Select(dropdown_element)
            available_options = [opt.text for opt in dropdown.options]
            user_input = ipo.title()
            matching_option, confidence = process.extractOne(user_input, available_options)
            print(f"Matching option: {matching_option}, confidence: {confidence}")
            if confidence >= 50:
                dropdown.select_by_visible_text(matching_option)
                print(f"Selected option: {matching_option}")
            else:
                self.message = "No matching options found for the specified IPO."
                return False
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
            If there are any errors during submission, it retries a maximum of 5 times before giving up.
            
            Args:
                username (str): The username to input into the username field.
            
            Returns:
                bool: True if the submission is successful and data scraping can proceed, False otherwise.
            
            Raises:
                Exception: If there is an error while inputting the username and submitting.
            """
        
            try:
                retry_count = 0
                max_retries = 5  # Example limit, adjust as needed
                while retry_count < max_retries:
                    username_field_id = self.config['username_field']
                    username_field = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, username_field_id)))
                    username_field.clear()
                    username_field.send_keys(username.strip().upper())
                    # Assuming captcha solving is required here; implement as needed.
                    self.solve_captcha_and_submit()
                    # Check for errors after submission
                    error_type = self.handle_dialog_box()
                    
                    if error_type == "captcha_error":
                        retry_count += 1
                        print("Captcha error, retrying...")
                        refresh_button = self.config['refresh_button']
                        if refresh_button:
                            refresh = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, refresh_button)))
                            refresh.click()
                        continue  # Retry captcha solving
                    elif error_type == "no_error":
                        return True  # Success, proceed to data scraping
                    else:
                        print(f"{error_type} error, stopping retries.")
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
        if captcha_type == 'bigshare' or captcha_type == 'kfintech':
            captcha_input = predict_captcha(self.driver,captcha_type)# Replace with actual captcha solution logic
            captcha_id = self.config['captcha_field']
            captcha_field = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, captcha_id)))
            captcha_field.clear()
            captcha_field.send_keys(captcha_input)
        submit_id = self.config['submit_button']
        if self.config['website_name'] == 'skyline':
            submit_button = self.driver.find_element(By.CLASS_NAME, submit_id)
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
                error_message = self.config['error_message']
                message_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, error_message)))
                message_text = message_element.text
                close_dialog = self.config['close_dialog']
                if close_dialog:
                    close_button = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, close_dialog)))
                    close_button.click()
                if self.config['website_name'] == 'kfintech':
                    known_captcha_errors = ["CAPTCHA is invalid or Expired", "Captcha is invalid."]
                    # Check if the message matches known captcha errors
                    matching_option, confidence = process.extractOne(message_text, known_captcha_errors)
                    if confidence >= 100:  # Adjust threshold as needed    
                        return "captcha_error"
                return message_text
            except TimeoutException:
                return "no_error"  # No error message was found
            except Exception as e:
                print(f"Error handling dialog box: {str(e)}")
                raise

        elif self.config['website_name'] == 'bigshare':
            try:
                error_message = self.config['error_message']
                message_element = WebDriverWait(self.driver, 10).until(
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
                    # Wait up to 10 seconds for the alert to be present
                    WebDriverWait(self.driver, 5).until(EC.alert_is_present())

                    # Switch to the alert
                    alert = self.driver.switch_to.alert

                    # You can now accept (OK) or dismiss (Cancel) the alert
                    alert.accept()
                    # alert.dismiss()  # Use this if you want to cancel/dismiss the alert
                    return "undefined"

                except TimeoutException:
                    pass
                dialog = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, 'ui-dialog')))
                # dialog_title = dialog.find_element(By.CLASS_NAME, 'ui-dialog-title').text
                error_message = self.config['error_message']
                message_element = WebDriverWait(dialog, 5).until(
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
                securities_allotted = int(WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_allot']"))).text)
                result_data = {
                    'application_number': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_l1']"))).text,
                    'category': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label1']"))).text,
                    'name': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label2']"))).text,
                    'client_id': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_dpclid']"))).text,
                    'pan': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_pan']"))).text,
                    'applied': int(WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label5']"))).text),
                    'securities_allotted': securities_allotted,
                    'error' : None
                }
                if securities_allotted > 0:
                    self.allotment += 1
                    self.total_shares += securities_allotted
                    print(f" Alloted : {self.allotment}")
                    print(f" Total shares : {self.total_shares}")
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
                    'application_no': label_elements[0].text,
                    'dp_id': label_elements[1].text,
                    'name': label_elements[2].text,
                    'applied': int(label_elements[3].text),
                    'alloted': alloted,
                    'error' : None
                }
                if type(alloted) == int:
                    self.allotment += 1
                    self.total_shares += alloted
                    print(f" Alloted : {self.allotment}")
                    print(f" Total shares : {self.total_shares}")
                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None
        
        elif self.config['website_name'] == 'linkin':
            try:
                output_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, 'tbl_DetSec')))
                
                if output_element : 
                    tables = self.driver.find_elements(By.CSS_SELECTOR, '#tbl_DetSec table')

                    for i,table in enumerate(tables,1):
                        # Use CSS selectors to extract data from the table
                        applicant_name = table.find_element(By.XPATH, "//td[text()='Sole / 1st Applicant']/following-sibling::td").text
                        if applicant_name == '':
                            applicant_name = 'Client/Id not found'
                        securities_applied = int(table.find_element(By.XPATH, "//td[text()='Securities applied']/following-sibling::td").text)
                        cutoff_price = int(table.find_element(By.XPATH, "//td[text()='Cut off Price']/following-sibling::td").text)
                        securities_allotted = int(table.find_element(By.XPATH, "//td[text()='Securities Allotted']/following-sibling::td").text)
                        amount_adjusted = int(table.find_element(By.XPATH, "//td[text()='Amount Adjusted']/following-sibling::td").text)
                        heading_text = table.find_element(By.CSS_SELECTOR, 'tr.heading_table th span').text
                        formtype = heading_text.split(' - ')[1]
                        if securities_allotted > 0:
                            self.allotment += 1
                            self.total_shares += securities_allotted
                            print(f" Alloted : {self.allotment}")
                            print(f" Total shares : {self.total_shares}")
                        result_data = {
                            'applicant_name' : applicant_name,
                            'shares_applied': securities_applied,
                            'application_amount': cutoff_price,
                            'shares_allotted': securities_allotted,
                            'amount_adjusted': amount_adjusted,
                            'Type': formtype,
                            'error' : None
                        }
                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None

        elif self.config['website_name'] == 'skyline':
            try:
                div_element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "fullwidth.resultsec")))
                self.driver.execute_script("arguments[0].scrollIntoView();", div_element)
                print("Scrolled to the element -> ", div_element)
                applicant_name =  div_element.find_elements(By.TAG_NAME,"p")

                if len(applicant_name) != 0:
                    shares_allotted = int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(3)")[0].text)
                    result_data = {
                    'applicant_name' : div_element.find_elements(By.TAG_NAME,"p")[1].text.split(" : ")[1],
                    'pan_number' : div_element.find_elements(By.TAG_NAME,"p")[4].text.split(" : ")[1],
                    'shares_applied': float(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(1)")[0].text),
                    'application_amount': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(2)")[0].text),
                    'shares_allotted': shares_allotted,
                    'amount_adjusted': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(4)")[0].text),
                    'amount_refunded': int(div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(5)")[0].text),
                    'status': div_element.find_elements(By.CSS_SELECTOR,".tablediv table tbody tr:nth-child(2) td:nth-child(9)")[0].text,
                    'error' : None
                }
                    if shares_allotted > 0:
                        self.allotment += 1
                        self.total_shares += shares_allotted
                        print(f" Alloted : {self.allotment}")
                        print(f" Total shares : {self.total_shares}")

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
                    'application_number': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_l1']"))).text,
                    'category': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label1']"))).text,
                    'name': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label2']"))).text,
                    'client_id': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_dpclid']"))).text,
                    'pan': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_pan']"))).text,
                    'applied': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_Label5']"))).text,
                    'securities_allotted': WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//span[@id='grid_results_ctl02_lbl_allot']"))).text,
                    'error' : None
                }
                return result_data
            except Exception as e:
                print(f"Error scraping data: {e}")
                return None

    def run(self, ipo, usernames):
        
        """
        Executes the scraping process for a list of usernames.

        Args:
            ipo (str): The dropdown option to select.
            usernames (list): A list of usernames to process.

        Returns:
            dict: A dictionary containing the results of the scraping process for each username.
        """

        results = {}
        max_retries = 3
        print(f"Total pan numbers {len(usernames)}")
        self.select_dropdown_option(ipo)
        for username in usernames:
            retries = 0
            while retries < max_retries:
                try:
                    if username not in results:  # Check if this username has already been processed
                        # if self.select_dropdown_option(ipo):
                        writing_pan = self.input_username_and_submit(username)
                        print(f"Working on {username}")
                        username_index = usernames.index(username) + 1
                        print(f"Left pan numbers {len(usernames) - username_index}")
                        if writing_pan == True:
                            data = self.scrape_data()
                            if data:
                                results[username] = data
                            else:
                                results[username] = {'error': "Failed to scrape data or data not found"}
                            # Assuming you want to go back or refresh between usernames
                            self.prepare_for_next_username()
                        else:
                            results[username] = {'error': 'unknown error'}
                    break  # Exit the loop if everything goes well for this username
                except (NoSuchWindowException, WebDriverException) as e:
                    print(f"Encountered an error: {e}. \nRetrying...")
                    self.initialize_driver() # Re-initialize the driver for retry
                    self.select_dropdown_option(ipo)
                    retries += 1
                    if retries >= max_retries:
                        print(f"Maximum retries reached for {username}. Moving to next username.")
                        results[username] = {'error': "Maximum retries reached"}
                        break
                except Exception as e:
                    print(f"Encountered an error with {username}: {str(e)}. \nRetrying...")
                    self.close()  # Close the current driver
                    self.initialize_driver()  # Re-initialize the driver for retry
                    self.select_dropdown_option(ipo)
                    retries += 1
                    if retries >= max_retries:
                        print(f"Maximum retries reached for {username}. Moving to next username.")
                        results[username] = {'error': "Maximum retries reached"}
                        break
        return results
        
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
                    back_button = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, back_id)))
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

website_configs = {

    'kfintech': {
        'website_name': 'kfintech',
        'website_url': 'https://rti.kfintech.com/ipostatus/',
        'dropdown': 'ddl_ipo', # ID
        'pan': 'pan',
        'username_field': 'txt_pan', # ID
        'captcha_field': 'txt_captcha',
        'submit_button': 'btn_submit_query',
        'back_button': 'lnk_new',
        'error_message': 'jconfirm-content',
        'close_dialog': 'btn.btn-blue',
        'refresh_button': 'refresh',
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
        'submit_button': '//input[@value=" Search "]' ,#XPATH or 'submit' -NAME
        'back_button': False,
        'error_message': 'alert-warning',#CLASS_NAME
        'close_dialog': 'close',#CLASS_NAME
        'refresh_button': False,
        # Add other necessary identifiers
    },
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


# # # Path to your Excel file

# # Example usage: To be taken from the user
# file_path = 'jana.xlsx'
# df = pd.read_excel(file_path)
# column_index = 'B'
# start_row = 15
# end_row = 25
# # end_row = None

# usernames = process_excel_data(df, column_index, start_row, end_row)



# --website_and_ipo_name-- #

# company = "skyline"
# ipo = "Alpex" # skyline

# company = "linkin"
# ipo = "capital" # linkin

# company = "kfintech"
# ipo = "jana" # kfintech

# company = "bigshare"
# ipo = "nova" # bigshare

# company = "purva"
# ipo = None

# ---pan_name--- #
# usernames = ["ABVFA3322P","HQTPS3086L","AIJPS0335D","AABHD3347","ANDPS8030N","ADOPS3545D"]  # List of usernames

# scraper = Scrape_Website(driver_path,company, headless)

# results = scraper.run(ipo, usernames)

# with open(f"{ipo}.json", "w") as file:
#     json.dump(results, file) # Save the results to a JSON file

# # print(results)

# # # Data Printing


def scrape_data_from_websites(driver_path, company, ipo, usernames, headless=False):
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
    scraper = Scrape_Website(driver_path, company, headless)
    results = scraper.run(ipo, usernames)
    print_details(company, ipo, results)
    return results


# Writing to Excel

# Example usage
# write_in_excel(file_path, df,results)

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
            return {
                "Name": row.find_element(By.XPATH, ".//td[1]/a").text,
                "Open Date": row.find_element(By.XPATH, ".//td[2]").text,
                "Close Date": row.find_element(By.XPATH, ".//td[3]").text,
                "Listing Date": row.find_element(By.XPATH, ".//td[4]").text,
                "Price": row.find_element(By.XPATH, ".//td[5]").text,
                "Issue Size": row.find_element(By.XPATH, ".//td[6]").text,
                "Lot Size": row.find_element(By.XPATH, ".//td[7]").text,
                "Listing At": row.find_element(By.XPATH, ".//td[8]").text,
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
    

