import json
import random
import time

import requests
from bs4 import BeautifulSoup

from webscraper.meyer.chicken_scraper import scrape_chicken_prices

BASE_URL = "https://meyerhatchery.com"
CHICKENS_URL = f"{BASE_URL}/products/chickens"


def get_page_content(url):
    """
    Fetches and parses the HTML content of the given URL.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes
    return BeautifulSoup(response.text, "html.parser")


def get_chick_list():
    """
    Scrapes the chicken categories listed on the main chickens page.
    """
    soup = get_page_content(CHICKENS_URL)
    chicken_list = []

    # Find category links (assuming they are within anchor tags in some list)
    for a_tag in soup.select("a[href*='/products/'][href$='chicks']"):
        href = a_tag.get("href")
        if href.startswith('https://meyerhatchery.com/products/') and href.endswith('chicks'):
            full_url = href
            chicken_list.append(full_url)

    return list(set(chicken_list))  # Remove duplicates if any




def main():
    print("Fetching chicken links...")
    chickens = get_chick_list()

    # Check if chickens is empty, if it is, keep trying every 3 seconds
    retry_count = 0
    while not chickens and retry_count < 15:
        print("No chickens found. Retrying...")
        time.sleep(random.randint(2, 7))
        chickens = get_chick_list()
        retry_count += 1

    if not chickens and retry_count >= 15:
        print("Failed to fetch chicken categories. Please try again later.")
        return

    print("\nList of Chickens:")
    for chicken in chickens:
        print(scrape_chicken_prices(chicken))


if __name__ == "__main__":
    main()
