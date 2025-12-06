from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import sqlite3

db_path = "gpus.db"
table_name = "gpus"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN launch_prices TEXT")
    conn.commit()
    print(f"Column 'launch_prices' added to {table_name}.")
except sqlite3.OperationalError:
    print(f"Column 'launch_prices' already exists.")



def clean_gpu_name(scraped_name):
    # Remove "Specs" from the end
    name = scraped_name.replace(" Specs", "").strip()
    
    # List of vendors to remove from the start
    vendors = ["NVIDIA ", "AMD ", "Intel ", "ATI "]
    
    for vendor in vendors:
        if name.startswith(vendor):
            name = name.replace(vendor, "", 1) # Remove only the first occurrence
            break
            
    return name.strip()



driver = webdriver.Chrome()
driver.get("https://www.techpowerup.com/gpu-specs/")
links = []

rows = driver.find_elements(By.XPATH, "//table[.//th[contains(text(), 'Name')]]//tr")

for row in rows:
    try:
        link_element = row.find_element(By.XPATH, ".//td[1]//a")
        url = link_element.get_attribute("href")
        if url:
            links.append(url)
    except:
        continue

links = list(set(links))
print(f"Successfully collected {len(links)} unique GPU links.")


for index, link in enumerate(links):
    try:
        driver.get(link)
        time.sleep(10)        
        launch_price = "N/A"  
        try:
            price_element = driver.find_element(By.XPATH, "//dt[contains(text(), 'Launch Price')]/following-sibling::dd[1]")
            launch_price = price_element.text.strip()
        except:
            launch_price = "Not Found"
        full_title = driver.title.split('|')[0].strip()
        clean_name = clean_gpu_name(full_title)

        print(f"[{index + 1}/{len(links)}] {clean_name} -> {launch_price}")

        if launch_price != "Not Found":
            cursor.execute(f"""
                UPDATE {table_name} 
                SET launch_prices = ? 
                WHERE name = ?
            """, (launch_price, clean_name))

            if cursor.rowcount > 0:
                print(f"   -> Saved to DB.")
            else:
                print(f"   -> GPU not found in DB (Name mismatch).")
            conn.commit()

    except Exception as e:
        print(f"Error scraping {link}: {e}")

conn.close()
driver.quit()
print("Done.")