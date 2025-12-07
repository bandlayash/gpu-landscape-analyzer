import sqlite3
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- CONFIGURATION ---
DB_PATH = "gpus.db"
TABLE_NAME = "gpus"
ANCHOR_URL = "https://www.techpowerup.com/gpu-specs/geforce-rtx-4060-mobile.c3946"

# --- DATABASE SETUP ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
try:
    cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN rel_performance REAL")
except sqlite3.OperationalError:
    pass 

def scroll_to_section(driver):
    print("   Scrolling to trigger lazy loading...")
    # Scroll in chunks to trigger JS events
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    for i in range(0, total_height, 500):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(0.1)
    
    # Scroll explicitly to the bottom just in case
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

# --- SCRAPING ---

driver = webdriver.Chrome()

print(f"Visiting Anchor Page: {ANCHOR_URL}")
driver.get(ANCHOR_URL)


# 2. Scroll to load the chart
scroll_to_section(driver)

performance_map = {}

try:
    print("   Waiting for chart to render...")
    
    # Wait specifically for the entries to appear in the DOM
    # We use CSS Selector with the dot (.) which is safer than Class Name
    wait = WebDriverWait(driver, 10)
    entries = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".gpudb-relative-performance-entry")))
    
    print(f"Found {len(entries)} entries in Relative Performance chart.")
    
    for entry in entries:
        try:
            # Extract Name
            title_div = entry.find_element(By.CSS_SELECTOR, ".gpudb-relative-performance-entry__title")
            card_name = title_div.text.strip()
            
            # Extract Percentage
            number_div = entry.find_element(By.CSS_SELECTOR, ".gpudb-relative-performance-entry__number")
            percent_text = number_div.text.replace('%', '').strip()
            
            # Save to map
            performance_map[card_name] = float(percent_text)
        except Exception as e:
            continue

except Exception as e:
    print(f"Error finding elements: {e}")

driver.quit()

# --- UPDATING DATABASE ---
print(f"Updating Database with {len(performance_map)} benchmarks...")

cursor.execute(f"SELECT name FROM {TABLE_NAME}")
db_gpus = cursor.fetchall()

match_count = 0

for row in db_gpus:
    db_name = row[0]
    
    # Exact Match
    score = performance_map.get(db_name)
    
    # Fuzzy Match Fallback (e.g. DB: "RTX 4090" vs TPU: "GeForce RTX 4090")
    if score is None:
        for key in performance_map:
            # Check if the DB name is inside the TPU name or vice versa
            if db_name in key or key in db_name:
                score = performance_map[key]
                break
    
    if score is not None:
        cursor.execute(f"UPDATE {TABLE_NAME} SET rel_performance = ? WHERE name = ?", (score, db_name))
        match_count += 1

conn.commit()
conn.close()

print(f"Done. Updated {match_count} GPUs.")