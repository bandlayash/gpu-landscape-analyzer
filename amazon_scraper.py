import sqlite3
import time
import random
import re
from statistics import mean
from selenium import webdriver
from selenium.webdriver.common.by import By

# Webdriver
driver = webdriver.Chrome() 

# Database config
DB_PATH = "gpus.db"
TABLE_NAME = "gpus"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Add Column
try:
    cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN amazon_new_avg REAL")
    print(f"Column 'amazon_new_avg' added.")
except sqlite3.OperationalError:
    pass # Column already exists, proceed.

# Reset prices to NULL
print("Resetting Amazon prices to NULL...")
cursor.execute(f"UPDATE {TABLE_NAME} SET amazon_new_avg = NULL")
conn.commit()

# convert price to float

def get_price_float(price_str):
    """
    Converts price to float ($19.99 --> 19.99)
    
    :param price_str: Price string ("$19.99")
    """
    try:
        clean_str = re.sub(r'[^\d.]', '', price_str)
        return float(clean_str)
    except ValueError:
        return None

def scrape_amazon_avg(driver, gpu_name):
    """
    Gets top 5 results for the GPU (default sort) and finds the mean of their prices
    
    :param driver: Chrome webdriver
    :param gpu_name: GPU name
    """
    try:
        query = f"{gpu_name} graphics card"
        encoded_query = query.replace(" ", "+")
        url = f"https://www.amazon.com/s?k={encoded_query}"
        
        
        driver.get(url)
        time.sleep(random.uniform(10, 15)) # To not seem suspicious

        prices = []
        
        
        items = driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']")
        
        for item in items:

            full_text = item.text.lower()
            
            # Skip Refurbished/Renewed stuff
            if "renewed" in full_text or "refurbished" in full_text:
                continue

            # Skip sponsored stuff
            if "sponsored" in full_text:
                continue

            search_words = gpu_name.lower().split()
            if not all(word in full_text for word in search_words if word not in ["geforce", "radeon", "nvidia", "amd"]):
                 continue
            
            # Get price
            try:
                price_element = item.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
                price_text = price_element.get_attribute("textContent")
                prices.append(get_price_float(price_text))
            except:
                continue # No price on this item, move to next
            
            if len(prices) >= 5:
                break
                
        if not prices:
            return None
            
        return round(mean(prices), 2)

    except Exception as e:
        print(f"  Error scraping Amazon: {e}")
        return None


# Main

# Select all GPUs
cursor.execute(f"SELECT name FROM {TABLE_NAME}")
rows = cursor.fetchall()
gpu_names = [r[0] for r in rows]

print(f"Found {len(gpu_names)} GPUs to update.")

for i, name in enumerate(gpu_names):
    print(f"[{i+1}/{len(gpu_names)}] Processing: {name}")
    
    amazon_price = scrape_amazon_avg(driver, name)
    
    if amazon_price is not None:
        print(f"  -> Amazon Avg (New): ${amazon_price}")
        
        # Only update if we actually found a price
        cursor.execute(f"UPDATE {TABLE_NAME} SET amazon_new_avg = ? WHERE name = ?", (amazon_price, name))
        conn.commit()
    else:
        print(f"  -> No valid prices found. Keeping as NULL.")
    
    # Sleep
    sleep_time = random.uniform(10, 15)
    time.sleep(sleep_time)

conn.close()
driver.quit()
print("Pricing update complete.")