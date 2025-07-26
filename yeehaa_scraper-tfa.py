#!/usr/bin/env python3

"""Recursive web site scraper with javascript rendering support and 2FA authentication"""
# pylint: disable=line-too-long
# pylint: disable=C0103
# pylint: disable=broad-except

import sys
import re
import time
import os
import json
import getpass
from urllib.parse import urlparse
import requests
import tldextract
from urllib.parse import urlparse
import hashlib
import pyotp

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.chrome.service import Service

class YeehaaScraper:
    """Recursive web scraper with javascript rendering support and 2FA authentication""" 

    def __init__(self, site_urls, scraped_dir="./scraped-data", meta_file="meta.json", 
                 convert_to_absolute_url=False, skip_patterns=[], 
                 username=None, password=None, totp_secret=None, 
                 login_url=None, username_field="username", password_field="password", 
                 totp_field="totp", submit_button_selector="input[type='submit']") -> None:
        
        self.scraped_dir = scraped_dir + "/data"
        self.meta_file = scraped_dir + "/" + meta_file
        self.skip_patterns = skip_patterns
        
        # Authentication parameters
        self.username = username
        self.password = password
        self.totp_secret = totp_secret
        self.login_url = login_url
        self.username_field = username_field
        self.password_field = password_field
        self.totp_field = totp_field
        self.submit_button_selector = submit_button_selector
        
        #self.options = FirefoxOptions()
        #self.options.add_argument("--headless")
        #self.driver = webdriver.Firefox(options=self.options)

        self.options = Options()
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--headless=new") # for Chrome >= 109        
        self.options.add_argument("--disable-dev-shm-usage")
        ser=Service("/snap/bin/chromium.chromedriver")
        self.driver = webdriver.Chrome(service=ser, options=self.options)

        self.scraped_urls = {}
        self.site_urls = site_urls
        self.rec_depth = 0
        self.content_hashes = {}
        self.authenticated = False
        
        root_urls = []
        for s in self.site_urls: 
            parsed_uri = urlparse(s)
            root_urls.append(f"{parsed_uri.scheme}://{parsed_uri.netloc}/")
        self.root_urls = root_urls

        self.metadata = []
        self.convert_to_absolute_url = convert_to_absolute_url 
        # Todo: Error check
        os.system("mkdir -p " + self.scraped_dir)
        sys.setrecursionlimit(10000)

    def debug_page_elements(self):
        """Debug helper to inspect page elements"""
        print(f"Current URL: {self.driver.current_url}")
        print(f"Page title: {self.driver.title}")
        
        # Find all input fields
        inputs = self.driver.find_elements(By.TAG_NAME, 'input')
        print(f"Found {len(inputs)} input elements:")
        for i, inp in enumerate(inputs):
            input_type = inp.get_attribute('type') or 'text'
            input_name = inp.get_attribute('name') or 'unnamed'
            input_id = inp.get_attribute('id') or 'no-id'
            input_placeholder = inp.get_attribute('placeholder') or 'no-placeholder'
            print(f"  Input {i}: type='{input_type}', name='{input_name}', id='{input_id}', placeholder='{input_placeholder}'")
        
        # Find all buttons
        buttons = self.driver.find_elements(By.TAG_NAME, 'button')
        submit_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')
        all_buttons = buttons + submit_inputs
        print(f"Found {len(all_buttons)} button/submit elements:")
        for i, btn in enumerate(all_buttons):
            btn_text = btn.text or btn.get_attribute('value') or 'no-text'
            btn_type = btn.get_attribute('type') or 'button'
            btn_class = btn.get_attribute('class') or 'no-class'
            print(f"  Button {i}: text='{btn_text}', type='{btn_type}', class='{btn_class}'")

    def authenticate(self):
        """Perform 2FA authentication with better error handling and debugging"""
        if not self.login_url:
            print("No login URL provided, skipping authentication")
            return True
            
        if not all([self.username, self.password, self.totp_secret]):
            print("Missing authentication credentials")
            return False
            
        try:
            print("Starting authentication process...")
            self.driver.get(self.login_url)
            time.sleep(3)  # Wait for page to load
            
            # Debug: Show what we found on the page
            print("=== PAGE DEBUG INFO ===")
            self.debug_page_elements()
            print("=====================")
            
            wait = WebDriverWait(self.driver, 15)
            
            # Try multiple strategies to find username field
            username_input = None
            username_selectors = [
                (By.NAME, self.username_field),
                (By.ID, self.username_field), 
                (By.ID, 'username'),
                (By.ID, 'email'),
                (By.NAME, 'email'),
                (By.CSS_SELECTOR, 'input[type="text"]'),
                (By.CSS_SELECTOR, 'input[type="email"]'),
                (By.XPATH, '//input[@placeholder="Username" or @placeholder="Email" or @placeholder="username" or @placeholder="email"]')
            ]
            
            for selector_type, selector in username_selectors:
                try:
                    username_input = wait.until(EC.presence_of_element_located((selector_type, selector)))
                    print(f"Found username field using: {selector_type}, {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not username_input:
                print("Could not find username field")
                return False
                
            username_input.clear()
            username_input.send_keys(self.username)
            print("Entered username")
            
            # Try multiple strategies to find password field
            password_input = None
            password_selectors = [
                (By.NAME, self.password_field),
                (By.ID, self.password_field),
                (By.ID, 'password'),
                (By.NAME, 'password'),
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.XPATH, '//input[@placeholder="Password" or @placeholder="password"]')
            ]
            
            for selector_type, selector in password_selectors:
                try:
                    password_input = self.driver.find_element(selector_type, selector)
                    print(f"Found password field using: {selector_type}, {selector}")
                    break
                except:
                    continue
                    
            if not password_input:
                print("Could not find password field")
                return False
                
            password_input.clear()
            password_input.send_keys(self.password)
            print("Entered password")
            
            # Generate TOTP code
            totp = pyotp.TOTP(self.totp_secret)
            totp_code = totp.now()
            print(f"Generated TOTP code: {totp_code}")
            
            # Look for TOTP field - try multiple strategies
            totp_input = None
            totp_selectors = [
                (By.NAME, self.totp_field),
                (By.ID, self.totp_field),
                (By.NAME, 'totp'),
                (By.NAME, 'code'),
                (By.NAME, 'token'),
                (By.NAME, 'authenticator_code'),
                (By.NAME, 'verification_code'),
                (By.ID, 'totp'),
                (By.ID, 'code'),
                (By.ID, 'token'),
                (By.XPATH, '//input[@placeholder="Code" or @placeholder="TOTP" or @placeholder="Authentication Code"]')
            ]
            
            # First, try to find TOTP field on current page
            for selector_type, selector in totp_selectors:
                try:
                    totp_input = self.driver.find_element(selector_type, selector)
                    print(f"Found TOTP field using: {selector_type}, {selector}")
                    break
                except:
                    continue
            
            if totp_input:
                # TOTP field found on same page
                totp_input.clear()
                totp_input.send_keys(totp_code)
                print("Entered TOTP code")
            else:
                # TOTP field not found, try submitting username/password first
                print("TOTP field not found initially, submitting credentials first...")
                
                # Find and click submit button
                submit_button = None
                submit_selectors = [
                    (By.CSS_SELECTOR, self.submit_button_selector),
                    (By.CSS_SELECTOR, 'input[type="submit"]'),
                    (By.CSS_SELECTOR, 'button[type="submit"]'),
                    (By.XPATH, '//button[contains(text(), "Login") or contains(text(), "Sign in") or contains(text(), "Submit")]'),
                    (By.XPATH, '//input[@value="Login" or @value="Sign in" or @value="Submit"]')
                ]
                
                for selector_type, selector in submit_selectors:
                    try:
                        submit_button = self.driver.find_element(selector_type, selector)
                        print(f"Found submit button using: {selector_type}, {selector}")
                        break
                    except:
                        continue
                
                if not submit_button:
                    print("Could not find submit button")
                    return False
                    
                submit_button.click()
                time.sleep(3)  # Wait for potential redirect/new page
                
                print("=== PAGE AFTER FIRST SUBMIT ===")
                self.debug_page_elements()
                print("=============================")
                
                # Now look for TOTP field again
                for selector_type, selector in totp_selectors:
                    try:
                        totp_input = wait.until(EC.presence_of_element_located((selector_type, selector)))
                        print(f"Found TOTP field after submit using: {selector_type}, {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not totp_input:
                    print("Could not find TOTP field even after submitting credentials")
                    return False
                    
                totp_input.clear()
                totp_input.send_keys(totp_code)
                print("Entered TOTP code on second page")
            
            # Submit the final form
            final_submit = None
            submit_selectors = [
                (By.CSS_SELECTOR, self.submit_button_selector),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.XPATH, '//button[contains(text(), "Login") or contains(text(), "Sign in") or contains(text(), "Submit") or contains(text(), "Verify")]'),
                (By.XPATH, '//input[@value="Login" or @value="Sign in" or @value="Submit" or @value="Verify"]')
            ]
            
            for selector_type, selector in submit_selectors:
                try:
                    final_submit = self.driver.find_element(selector_type, selector)
                    print(f"Found final submit button using: {selector_type}, {selector}")
                    break
                except:
                    continue
                    
            if final_submit:
                final_submit.click()
                print("Clicked final submit button")
            else:
                print("Warning: Could not find final submit button, authentication may be incomplete")
            
            # Wait for authentication to complete
            time.sleep(5)
            
            # Check if authentication was successful
            current_url = self.driver.current_url
            print(f"Final URL after authentication: {current_url}")
            
            # More sophisticated success detection
            success_indicators = [
                "dashboard" in current_url.lower(),
                "overview" in current_url.lower() and "systems-overview" in current_url,
                "profile" in current_url.lower(),
                "home" in current_url.lower(),
                "login" not in current_url.lower() and "auth" not in current_url.lower()
            ]
            
            if any(success_indicators):
                print("Authentication appears successful!")
                self.authenticated = True
                return True
            else:
                print(f"Authentication may have failed - current URL: {current_url}")
                return False
                
        except TimeoutException as e:
            print(f"Timeout during authentication: {e}")
            return False
        except Exception as e:
            print(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def navigate(self, target) -> None:
        """Navigate to target URL, authenticating if necessary""" 
        if not self.authenticated and self.login_url:
            if not self.authenticate():
                print("Authentication failed, continuing without auth...")
        
        self.driver.get(target)

    def extract_raw_data(self) -> str:
        """Extract html"""
        return self.driver.page_source

    def extract_single_element(self,  selector: str, selector_type: By = By.CSS_SELECTOR) -> WebElement:
        """Extract element"""
        return self.driver.find_element(selector_type, selector)

    def extract_all_elements(self, selector: str, selector_type: By = By.CSS_SELECTOR) -> list[WebElement]:
        """Extract all elements"""
        return self.driver.find_elements(selector_type, selector)

    def srcrepl(self, absolute_url, content):

        def _srcrepl(match):
            "Return the file contents with paths replaced"
            return "<" + match.group(1) + match.group(2) + "=" + "\"" + absolute_url + match.group(3) + match.group(4) + "\"" + ">"

        p = re.compile(r"<(.*?)(src|href)=\"(?!http)(.*?)\"(.*?)>")
        content = p.sub(_srcrepl, content)
        return content

    def scrape_sites(self) -> None:
        cnt = 0
        for site in self.site_urls:
            self._scrape_site(site, self.root_urls[cnt])
            cnt += 1

        with open(self.meta_file, 'w+', encoding='utf-8') as fp:
            json.dump(self.metadata, fp, indent=4)

    def _scrape_site(self, urlen, rooturl) -> None:

        for pattern in self.skip_patterns: # TODO: Use regex
            if pattern in urlen:
                print(f"{urlen} in skiplist. Skipping")
                return
        """Scrape urlen"""
        print("Scraping " + urlen)
        self.rec_depth = self.rec_depth + 1
        self.navigate(urlen)
        time.sleep(2) # Give time to render ..
     
        o = urlparse(urlen)
        urlen = o._replace(fragment="").geturl()
        
        tmpf = o.path
        
        head, _, tail = tmpf.partition('#')
        tmpf = head    
       
        parts = tmpf.split('/')
        file_name = parts[-1]
        parts.pop()

        file_name, file_extension = os.path.splitext(file_name)
        print("EXTN: "+ file_extension)
        if file_extension == ".png" or  file_extension == ".jpg" or  file_extension == ".jpeg" or  file_extension == ".gif":
            print("Skipping image "+ urlen)
            return
        if file_extension == "":
            file_extension = ".html"

        file_name =  o.netloc + "__".join(parts) + "--" + file_name + file_extension
        print("TO " + file_name)
        print("")
        if file_extension != '.html':
            try:
                response = requests.get(urlen, timeout=None)
                if 200 <= response.status_code <= 299:
                    with open(self.scraped_dir + "/" + file_name, 'wb') as f:
                        f.write(response.content)
                    elm = {}
                    elm['title'] = ""
                    elm['url'] = urlen
                    elm['file_name'] = file_name
                    self.metadata.append(elm)
                else:
                    print(f"Failed to get {urlen} https status {response.status_code}")
            except Exception as e :
                print("urlretrieve failed " + str(e))
            return

        # Extract the entire HTML document
        html_content = self.driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
        hash1 = hashlib.md5(html_content.encode('utf-8')).hexdigest()
        if hash1 in self.content_hashes: # Check if content already added . (Avoid duplicates in vector database)                                                                                                     
            print(f"Skipping duplicate content {urlen} {hash1} {self.content_hashes[hash1]}")
            self.scraped_urls[urlen] = True
            return
        self.content_hashes[hash1] = True

        if self.convert_to_absolute_url:
            html_content = self.srcrepl(rooturl, html_content)

        with open(self.scraped_dir + "/" + file_name, 'w', encoding='utf-8') as f:
            f.write(html_content)

        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = ""
        if soup.title:
            title = soup.title.string

        all_links = self.extract_all_elements('a', By.TAG_NAME)
        hrefs = []
        for el in all_links:
            hrefs.append(el.get_attribute('href'))

        elm = {}
        elm['title'] = title
        elm['url'] = urlen
        elm['file_name'] = file_name
        self.metadata.append(elm)
        
        for href in hrefs:
            if href is None:
                continue
            try:
                o = urlparse(href)
                href = o._replace(fragment="").geturl()
                if href is None or href == "":
                    self.scraped_urls[href] = True
                    continue
                if not href.startswith(rooturl):
                    print(href + " outside domain. Skipping")
                    self.scraped_urls[href] = True
                    continue

                if  href in self.scraped_urls:
                    continue
                else:
                    self.scraped_urls[href] = True
                    self._scrape_site(href, rooturl)
                    time.sleep(1) # Be nice
            except Exception as e:
                self.scraped_urls[href] = True
                print("Exception on url " + href)
                if hasattr(e, 'message'):
                    print(e.message)
                else:
                    print(e)
                continue
        self.rec_depth = self.rec_depth -1

def get_credentials():
    """Get credentials from environment variables or config file"""
    # Try environment variables first
    username = os.getenv('SCRAPER_USERNAME')
    password = os.getenv('SCRAPER_PASSWORD')
    totp_secret = os.getenv('SCRAPER_TOTP_SECRET')
    
    # If env vars not found, try config file
    if not all([username, password, totp_secret]):
        config_file = 'scraper_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    username = config.get('username')
                    password = config.get('password')
                    totp_secret = config.get('totp_secret')
                    print("Loaded credentials from config file")
            except Exception as e:
                print(f"Error reading config file: {e}")
        else:
            # Create example config file
            example_config = {
                "username": "your_username",
                "password": "your_password", 
                "totp_secret": "your_totp_secret_key",
                "login_url": "https://systems-overview.pages.met.no/login",
                "username_field": "username",
                "password_field": "password",
                "totp_field": "totp"
            }
            with open('scraper_config.example.json', 'w') as f:
                json.dump(example_config, f, indent=4)
            print(f"Created example config file: scraper_config.example.json")
            print("Please copy it to scraper_config.json and fill in your credentials")
    
    if not all([username, password, totp_secret]):
        print("Error: Missing credentials!")
        print("Set environment variables:")
        print("  export SCRAPER_USERNAME='your_username'")
        print("  export SCRAPER_PASSWORD='your_password'")
        print("  export SCRAPER_TOTP_SECRET='your_totp_secret'")
        print("Or create scraper_config.json with your credentials")
        sys.exit(1)
        
    return username, password, totp_secret

def load_config():
    """Load additional configuration from file or use defaults"""
    config_file = 'scraper_config.json'
    default_config = {
        "login_url": "https://systems-overview.pages.met.no/login",
        "username_field": "username", 
        "password_field": "password",
        "totp_field": "totp"
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                # Merge with defaults
                for key, value in file_config.items():
                    if key in default_config:
                        default_config[key] = value
        except Exception as e:
            print(f"Error reading config file: {e}")
    
    return default_config

if __name__ == "__main__":
    
    # Get credentials automatically
    username, password, totp_secret = get_credentials()
    
    # Load additional configuration
    config = load_config()
    
    scraper = YeehaaScraper([
        'https://systems-overview.pages.met.no/systems-overview/'
    ], 
        skip_patterns=['dokit-dump', '.rst.txt'],
        scraped_dir='scraped-systems-overview-2025-07-25',
        username=username,
        password=password,
        totp_secret=totp_secret,
        login_url=config['login_url'],
        username_field=config['username_field'],
        password_field=config['password_field'],
        totp_field=config['totp_field']
    )

    scraper.scrape_sites()
    print("Done")
