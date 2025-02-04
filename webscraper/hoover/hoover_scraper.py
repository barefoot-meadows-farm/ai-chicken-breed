import requests
from bs4 import BeautifulSoup
import time

from webscraper.hoover.chicken_scraper import scrape_pricing_table, scrape_availability_dates, \
    get_shipping_location_with_selenium

BASE_URL = "https://www.hoovershatchery.com"


# Function to get soup object from a URL
def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


# Function to extract category URLs
def get_category_links(main_url):
    soup = get_soup(main_url)
    category_links = []
    category_elements = soup.select('.title-content-wrapper a')  # Update this selector if necessary
    for element in category_elements:
        link = element['href']
        if link.startswith('/'):
            link = BASE_URL + link
        category_links.append(link)
    return category_links


# Function to extract chicken data from a category page
def extract_chickens(soup):
    chickens = []
    chicken_cards = soup.select('.product-item')
    for card in chicken_cards:
        name = card.select_one('.product-title').get_text(strip=True) if card.select_one('.product-title') else "N/A"

        # Extract price after "Starting at: " if available
        price_element = card.select_one('span.price.only-price')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = price_text.replace("Starting at: ", "")
        else:
            price = "N/A"

        url = card.find('a')['href'] if card.find('a') else "N/A"
        print(name, price, url)
        chickens.append({
            'Name': name,
            'Price': price,
            'URL': BASE_URL + url if url != "N/A" else "N/A"
        })
    return chickens


def scrape_chicken_page(chicken_url):
    """Extracts tiered pricing information from a chicken product page."""
    soup = get_soup(chicken_url)
    detailed_info = {
        "Pricing": scrape_pricing_table(soup),
        "Availability": scrape_availability_dates(soup),
        "Location": get_shipping_location_with_selenium(chicken_url)
    }

    return detailed_info



def scrape_category(category_url):
    """Scrape all pages of a category."""
    chickens = []
    while category_url:
        soup = get_soup(category_url)
        chickens.extend(extract_chickens(soup))

        # Find the next-page link
        next_page_element = soup.select_one('li.next-page a')
        if next_page_element:
            category_url = next_page_element['href']
            time.sleep(1)  # Be respectful to the server
        else:
            category_url = None  # No more pages
    return chickens

def main():
    main_url = f"{BASE_URL}/chicks"
    categories = get_category_links(main_url)
    all_chickens = []

    for category_url in categories:
        print(f"Scraping category: {category_url}")
        all_chickens.extend(scrape_category(category_url))


    # Remove duplicates based on unique URLs
    all_chickens = [dict(t) for t in {tuple(d.items()) for d in all_chickens}]

    print("\nList of Chickens:")
    for chicken in all_chickens:
        chicken["detailed_pricing"] = scrape_chicken_page(chicken['URL'])
        print(chicken)


if __name__ == "__main__":
    main()