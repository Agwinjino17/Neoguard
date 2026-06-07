import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def run_test():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    
    # Enable performance logging to capture console logs
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Navigating to dashboard...")
        driver.get("http://127.0.0.1:5050/dashboard")
        
        # Wait for alerts to load
        time.sleep(3)
        
        # Find all assess and clear buttons
        assess_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Assess')]")
        clear_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Clear')]")
        
        print(f"Found {len(assess_buttons)} Assess buttons and {len(clear_buttons)} Clear buttons.")
        
        if assess_buttons:
            print("Clicking Assess...")
            driver.execute_script("arguments[0].click();", assess_buttons[0])
            time.sleep(2)
            
        if clear_buttons:
            print("Clicking Clear...")
            driver.execute_script("arguments[0].click();", clear_buttons[-1])
            time.sleep(2)
            
        print("\n--- BROWSER CONSOLE LOGS ---")
        for log in driver.get_log('browser'):
            print(f"[{log['level']}] {log['message']}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    run_test()
