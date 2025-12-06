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
    cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN ebay_used_avg REAL")
    print(f"Column 'ebay_used_avg' added.")
except sqlite3.OperationalError:
    pass 

# Reset prices
print("Resetting eBay prices to NULL...")
cursor.execute(f"UPDATE {TABLE_NAME} SET ebay_used_avg = NULL")
conn.commit()


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

def scrape_ebay_sold(driver, gpu_name):
    """
    Scrapes the 'Sold Items' page on eBay for the last 10 sales.

    :param driver: Chrome webdriver
    :param gpu_name: GPU name
    """
    try:
        query = f"{gpu_name}"
        encoded_query = query.replace(" ", "+")
        
        url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&_sacat=0&_from=R40&LH_BIN=1&LH_Sold=1&LH_Complete=1&LH_ItemCondition=3000"
        
        driver.get(url)
        time.sleep(random.uniform(5, 10))
        
        prices = []

        items = driver.find_elements(By.CSS_SELECTOR, "li.s-card")
        
        for item in items:
            try:
                # Get Title
                try:
                    title_el = item.find_element(By.CSS_SELECTOR, ".s-card__title, .s-item__title")
                    title_text = title_el.text.lower()
                except:
                    continue

                # Filters
                if "parts only" in title_text or "broken" in title_text or "box only" in title_text:
                    continue

                # Strict Name Match (Ensure "3080" is in title if we searched for it)
                search_words = gpu_name.lower().split()
                ignore_list = ["geforce", "radeon", "nvidia", "amd", "intel", "arc", "rtx", "gtx"]
                critical_keywords = [w for w in search_words if w not in ignore_list]
                
                if not all(k in title_text for k in critical_keywords):
                    continue

                # Get price
                price_el = item.find_element(By.CSS_SELECTOR, ".s-card__price, .s-item__price")
                val = get_price_float(price_el.text)
                

                prices.append(val)

            except Exception as e:
                continue # Skip bad items

            if len(prices) >= 10:
                break
        
        if not prices:
            return None
            
        return round(mean(prices), 2)

    except Exception as e:
        print(f"  Error scraping eBay: {e}")
        return None

# Main

# Get List of GPUs
cursor.execute(f"SELECT name FROM {TABLE_NAME}")
rows = cursor.fetchall()
gpu_names = [r[0] for r in rows]

print(f"Found {len(gpu_names)} GPUs to update.")

for i, name in enumerate(gpu_names):
    print(f"[{i+1}/{len(gpu_names)}] Processing: {name}")
    
    avg_price = scrape_ebay_sold(driver, name)
    
    if avg_price is not None: # Only update if price is found
        print(f"   -> eBay Avg (Used): ${avg_price}")
        cursor.execute(f"UPDATE {TABLE_NAME} SET ebay_used_avg = ? WHERE name = ?", (avg_price, name))
        conn.commit()
    else:
        print(f"   -> No sales found. Keeping as NULL.")
    
    time.sleep(random.uniform(10, 15))

conn.close()
driver.quit()
print("Done.")