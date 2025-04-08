#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import ui
from selenium.webdriver import FirefoxOptions

opts = FirefoxOptions()
opts.add_argument("--headless")
driver = webdriver.Firefox(options=opts)

driver.get('https://www.google.com/')
#page_url=driver.find_elements_by_xpath("//a[@class='content']")
#page = driver.find_element("xpath", '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input')
#print(page)
#all_title = driver.find_elements_by_class_name("title")
#title = [title.text for title in all_title]
#print(title)
