#!/usr/bin/env python3

"""Recursive web site scraper with javascript rendering support and 2FA"""
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
    """Recursive web scraper with javascript rendering support and 2FA""" 

    def __init__(self, site_urls, scraped_dir="./scraped-data", meta_file="meta.json", 
                 convert_to_absolute_url=False, skip_patterns=[], 
                 auth_config=None) -> None:
        
        self.scraped_dir = scraped_dir + "/data"
        self.meta_file = scraped_dir + "/" + meta_file
        self.skip_patterns = skip_patterns
        self.auth_config = auth_config or {}
        
        #self.options = FirefoxOptions()
        #self.options.add_argument("--headless")
        #self.driver = webdriver.Firefox(options=self.options)

        self.options = Options()
        self.options.add_argument("--no-sandbox");
        # Comment out headless mode for 2FA login (you need to see the page)
        # self.options.add_argument("--headless=new") # for Chrome >= 109        
        self.options.add_argument("--disable-dev-shm-usage");
        ser=Service("/snap/bin/chromium.chromedriver")
        self.driver = webdriver.Chrome(service=ser, options=self.options)

        self.scraped_urls = {}
        self.site_urls = site_urls  # TODO: Extract root url to use when convert_to_absolulte_url=True in case sit_url is not to level
        self.rec_depth = 0
        self.content_hashes = {}
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

    def authenticate_2fa(self, login_url, username_selector, password_selector, 
                        totp_selector, submit_selector, totp_secret=None):
        """Handle 2FA authentication"""
        print("Starting 2FA authentication...")
        
        # Navigate to login page
        self.driver.get(login_url)
        time.sleep(3)
        
        # Get credentials
        if not self.auth_config.get('username'):
            username = input("Enter username: ")
        else:
            username = self.auth_config['username']
            
        if not self.auth_config.get('password'):
            password = getpass.getpass("Enter password: ")
        else:
            password = self.auth_config['password']
        
        # Fill in username and password
        try:
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            username_field.send_keys(username)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.send_keys(password)
            
            # Submit login form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_button.click()
            
            time.sleep(3)  # Wait for 2FA page to load
            
            # Handle 2FA
            if totp_secret:
                # Generate TOTP code
                totp = pyotp.TOTP(totp_secret)
                totp_code = totp.now()
                print(f"Generated TOTP code: {totp_code}")
            else:
                # Manual TOTP entry
                totp_code = input("Enter the 6-digit code from Google Authenticator: ")
            
            # Enter TOTP code
            totp_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, totp_selector))
            )
            totp_field.send_keys(totp_code)
            
            # Submit 2FA form
            submit_2fa = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_2fa.click()
            
            time.sleep(5)  # Wait for authentication to complete
            
            print("2FA authentication completed successfully!")
            return True
            
        except TimeoutException:
            print("Authentication failed - timeout waiting for elements")
            return False
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False

    def authenticate_interactive(self):
        """Interactive authentication - user handles login manually"""
        print("Please complete the authentication process manually...")
        print("The browser window will open. Please:")
        print("1. Log in with your username and password")
        print("2. Complete the 2FA process with Google Authenticator")
        print("3. Once logged in successfully, press Enter here to continue...")
        
        input("Press Enter once you have completed the login process...")
        print("Continuing with scraping...")
        return True

    def navigate(self, target) -> None:
        """Navigtate""" 
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
        # Perform authentication if configured
        if self.auth_config.get('enabled', False):
            if self.auth_config.get('method') == 'interactive':
                # Navigate to the first site for interactive login
                self.driver.get(self.site_urls[0])
                if not self.authenticate_interactive():
                    print("Authentication failed. Exiting...")
                    return
            elif self.auth_config.get('method') == 'automatic':
                if not self.authenticate_2fa(
                    self.auth_config['login_url'],
                    self.auth_config['username_selector'],
                    self.auth_config['password_selector'],
                    self.auth_config['totp_selector'],
                    self.auth_config['submit_selector'],
                    self.auth_config.get('totp_secret')
                ):
                    print("Automatic authentication failed. Exiting...")
                    return
        
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
        
        #if o.path.endswith(".html"):
        #    tmpf = o.path.replace(".html", o.fragment + ".html")            
        #else: 
        #    tmpf = o.path
        tmpf = o.path
        
        head, _, tail = tmpf.partition('#')
        #if tail != "":
        #    tmpf = head + "_" + tail
        #else:
        #    tmpf = head
        tmpf = head    
       
        parts = tmpf.split('/')
        file_name = parts[-1]
        parts.pop()

        file_name, file_extension = os.path.splitext(file_name)
        print("EXTN: "+ file_extension)
        if file_extension == ".png" or  file_extension == ".jpg" or  file_extension == ".jpeg" or  file_extension == ".gif":
            print("Skippint image "+ urlen)
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
                    #elm['links'] = hrefs
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
        if hash1 in self.content_hashes: # Check if content already added . (Avoid duplicates in vector databasae)                                                                                                     
            print(f"Skipping duplicate content {urlen} {hash1} {self.content_hashes[hash1]}")
            self.scraped_urls[urlen] = True
            return
        self.content_hashes[hash1] = True

        if self.convert_to_absolute_url:
            html_content = self.srcrepl(rooturl, html_content)

        with open(self.scraped_dir + "/" + file_name, 'w', encoding='utf-8') as f:
            f.write(html_content)
        #print(html_content)

        soup = BeautifulSoup(html_content, 'html.parser')
        
        #print(soup.prettify())
        title = ""
        if soup.title:
            title = soup.title.string
        #print(f'Page Title: {title} url: {urlen}' )

        all_links = self.extract_all_elements('a', By.TAG_NAME)
        hrefs = []
        for el in all_links:
            hrefs.append(el.get_attribute('href'))

        elm = {}
        elm['title'] = title
        #elm['links'] = hrefs
        elm['url'] = urlen
        elm['file_name'] = file_name
        self.metadata.append(elm)
        ### Scrape one page 
        #return
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
                    #print(f"{urlen} already scraped. Skipping")
                    continue
                else:
                    self.scraped_urls[href] = True
                    #print(f"Scraping {href } \"{title }\" to {file_name} ({self.rec_depth})")
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

if __name__ == "__main__":

    # Configuration for 2FA authentication
    # Method 1: Interactive (recommended for first time)
    auth_config_interactive = {
        'enabled': True,
        'method': 'interactive'  # User handles login manually
    }
    
    # Method 2: Automatic (requires knowing the form selectors)
    # You'll need to inspect the login page to get the correct selectors
    auth_config_automatic = {
        'enabled': True,
        'method': 'automatic',
        'login_url': 'https://systems-overview.pages.met.no/systems-overview/login',  # Update with actual login URL
        'username_selector': 'input[name="username"]',  # Update with actual selector
        'password_selector': 'input[name="password"]',  # Update with actual selector  
        'totp_selector': 'input[name="totp"]',  # Update with actual selector
        'submit_selector': 'button[type="submit"]',  # Update with actual selector
        'username': '',  # Optional: set username here
        'password': '',  # Optional: set password here
        'totp_secret': ''  # Optional: your TOTP secret key from Google Authenticator setup
    }

    scraper = YeehaaScraper([
        'https://systems-overview.pages.met.no/systems-overview/'
    ], 
        skip_patterns=['dokit-dump', '.rst.txt'],
        scraped_dir='scraped-systems-overview-2025-01-25',
        auth_config=auth_config_interactive  # Use interactive method
    )

    scraper.scrape_sites()
    print("Done")
    