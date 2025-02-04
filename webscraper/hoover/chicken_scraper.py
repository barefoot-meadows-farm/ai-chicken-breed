import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.hoovershatchery.com"

def get_shipping_location_with_selenium(chicken_url):
    """
    Use Selenium to navigate to the product page, add to cart,
    and extract shipping location
    """
    # Setup Chrome WebDriver
    # Initialize the WebDriver
    # Setup Chrome WebDriver with more options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-gpu')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Increase page load timeout
        driver.set_page_load_timeout(30)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # Navigate to the chicken product page
        print(f"Navigating to URL: {chicken_url}")
        driver.get(chicken_url)

        # Wait for page to load completely
        driver.implicitly_wait(10)

        print("Starting Plus Button Clicks")
        # Find and click the plus button 5 times
        plus_buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.plus'))
        )

        # If multiple plus buttons, use the first one
        if plus_buttons:
            plus_button = plus_buttons[0]

            # Click plus button 5 times
            for _ in range(5):
                plus_button.click()
                # Short wait between clicks to ensure website registers each click
                time.sleep(0.5)
        else:
            print("No plus button found")
            return None

        time.sleep(2)
        print("Finished Plus Button Clicks")

        print("Starting Add to Cart Button Clicks")
        # Wait for button to be present
        add_to_cart_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.add-to-cart-button'))
        )

        # Try multiple methods to click the button
        try:
            # Try regular click
            add_to_cart_button.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            try:
                # Try ActionChains
                actions = ActionChains(driver)
                actions.move_to_element(add_to_cart_button).click().perform()
            except Exception:
                # Try JavaScript click as last resort
                driver.execute_script("arguments[0].click();", add_to_cart_button)


        time.sleep(2)
        # Navigate to cart page
        print("Navigating to cart page")
        driver.get(BASE_URL + '/cart')

        # Wait for page to load completely
        driver.implicitly_wait(10)
        time.sleep(2)

        # Extract shipping location
        print("Extracting shipping location")
        # Find location directly on the page
        location_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.location-heading'))
        )

        location_text = location_element.text

        # Extract location
        if 'Location:' in location_text:
            location = location_text.split('Location:')[1].strip()

            # Validate against known locations
            known_locations = ['Rudd, IA', 'Quakertown, PA', 'Portales, NM']
            for known_location in known_locations:
                if known_location in location:
                    return known_location

        # If no match found
        print(f"Found location text: {location_text}")
        return location_text


    except Exception as e:
        print(f"Error extracting shipping location: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Always close the browser
        driver.quit()


def scrape_pricing_table(soup):
    pricing_data = []

    # Locate the pricing table
    pricing_table = soup.select_one('.prices-table.custom-grouped-pdp')
    if not pricing_table:
        return pricing_data

    # Extract quantity headers
    quantity_ranges = [span.get_text(strip=True) for span in
                       pricing_table.select('.thead .item-quantity span:nth-child(1)')]

    # Extract rows for male, female, and unsexed
    rows = pricing_table.select('.tbody')
    for row in rows:
        sex = row.select_one('.field-header').get_text(strip=True)
        prices = [price.get_text(strip=True) for price in row.select('.item-price') if price.get_text(strip=True)]

        # Build a structured dictionary for the current row
        pricing_data.append({
            "Sex": sex,
            "Pricing": dict(zip(quantity_ranges, prices))
        })

    return pricing_data

def scrape_availability_dates(soup):
    # Find the availability table
    availability_table = soup.select_one('#availTable')
    if not availability_table:
        return []

    # Extract the dates from the table headers
    dates = [th.get_text(strip=True) for th in availability_table.select('thead th')[1:]]

    # Extract availability data for each sex
    availability_data = []
    for row in availability_table.select('tbody tr'):
        sex = row.select_one('td.hmcol0').get_text(strip=True)

        # Check availability for each date
        available_dates = []
        for i, cell in enumerate(row.select('td')[1:], start=1):
            if cell.select_one('.fas.fa-check'):
                available_dates.append(dates[i - 1])

        availability_data.append({
            "Sex": sex,
            "Available_Dates": available_dates
        })

    return availability_data