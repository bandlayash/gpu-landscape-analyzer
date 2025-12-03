from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://www.techpowerup.com/gpu-specs/")
links = driver.find_elements(By.CSS_SELECTOR, "a.item-name")

for gpu in links:
    print(gpu)