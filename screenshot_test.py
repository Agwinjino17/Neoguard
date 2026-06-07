import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def take_screenshot():
    print("Setting up Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Navigating to http://127.0.0.1:5050...")
        driver.get("http://127.0.0.1:5050")
        
        # Wait a bit for JS to poll
        print("Waiting 3 seconds for API poll...")
        time.sleep(3)
        
        driver.save_screenshot(os.path.join(os.environ['TEMP'], "before_click.png"))
        
        print("Clicking notification bell...")
        bell = driver.find_element(By.ID, "globalNotificationBtn")
        bell.click()
        
        print("Waiting for transition...")
        time.sleep(1)
        
        screenshot_path = os.path.join(os.environ['TEMP'], "dropdown_screenshot.png")
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    take_screenshot()
