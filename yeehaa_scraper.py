#!/usr/bin/env python3

"""Recursive web site scraper with javascript rendering support"""
# pylint: disable=line-too-long
# pylint: disable=C0103
# pylint: disable=broad-except

import sys
import re
import time
import os
import json
from urllib.parse import urlparse
import requests
import tldextract
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

class YeehaaScraper:
    """Recursive web scraper with javascript rendering support""" 

    def __init__(self, site_urls, scraped_dir="./scraped-data", meta_file="meta.json", convert_to_absolute_url=False) -> None:

        self.options = Options()
        self.options.add_argument("--headless=new") # for Chrome >= 109
        self.scraped_dir = scraped_dir + "/data"
        self.meta_file = scraped_dir + "/" + meta_file
        self.driver = webdriver.Chrome(options=self.options)
        self.scraped_urls = {}
        self.site_urls = site_urls  # TODO: Extract root url to use when convert_to_absolulte_url=True in case sit_url is not to level
        self.rec_depth = 0
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
        cnt = 0
        for site in self.site_urls:
            self._scrape_site(site, self.root_urls[cnt])
            cnt += 1

        with open(self.meta_file, 'w+') as fp:
            json.dump(self.metadata, fp, indent=4)


    def _scrape_site(self, urlen, rooturl) -> None:
        """Scrape urlen"""
        print("Scraping " + urlen)
        self.rec_depth = self.rec_depth + 1
        self.navigate(urlen)
        time.sleep(2) # Give time to render ..
     
        o = urlparse(urlen)
     
        if o.path.endswith(".html"):
            tmpf = o.path.replace(".html", o.fragment + ".html")
        else: 
            tmpf = o.path

        head, _, tail = tmpf.partition('#')
        if tail != "":
            tmpf = head + "_" + tail
        else:
            tmpf = head
        parts = tmpf.split('/')
        file_name = parts[-1]
        parts.pop()

        file_name, file_extension = os.path.splitext(file_name)
        if file_extension == "":
            file_extension = ".html"

        file_name = self.scraped_dir + "/" + o.netloc + "__".join(parts) + "--" + file_name + file_extension
        print("TO " + file_name)
        print("")
        if file_extension != '.html':
            try:
                response = requests.get(urlen, timeout=None)
                if 200 <= response.status_code <= 299:
                    with open(file_name, 'wb') as f:
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
        if self.convert_to_absolute_url:
            html_content = self.srcrepl(rooturl, html_content)

        with open(file_name, 'w', encoding='utf-8') as f:
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


        for href in hrefs:
            if href is None:
                continue
            try:
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

    #scraper = YeehaaScraper(['https://klimaservicesenter.no/', 'https://www.met.no/'])
    #scraper = YeehaaScraper(['https://dokit.met.no/'], scraped_dir='scraped-dokit')
    #scraper = YeehaaScraper(['https://it.pages.met.no/infra/brukerdokumentasjon/ppi.html#gateways-data-room-b/'], scraped_dir='scraped-it-pages')
    scraper = YeehaaScraper(['https://sd.brukerdok.met.no/', 'https://klimaservicesenter.no/', 'https://www.met.no/', 'https://it.pages.met.no/infra/brukerdokumentasjon/ppi.html#gateways-data-room-b/'], scraped_dir='scraped-it-yeehaa-02-08')
    scraper.scrape_sites()
