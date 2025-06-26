import re

import requests
from bs4 import BeautifulSoup


def get_page_content(url):
    """Get the page content and return both the response text and soup object"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return response.text, soup

def get_ecwid_token(page_source):
    """Extract the Ecwid public token from the page source"""
    # Look for a script containing the token
    token_match = re.search(r'public_[A-Za-z0-9_]+', page_source)
    if token_match:
        return token_match.group(0)
    return None

def get_ecwid_product_id(url):
    """Extract the Ecwid product ID from the product page class name"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for the div with the product ID class
    product_div = soup.find('div', class_=lambda x: x and 'ecwid-productBrowser-ProductPage-' in x)
    if product_div:
        # Extract the ID from the class name
        class_name = next(c for c in product_div['class'] if 'ecwid-productBrowser-ProductPage-' in c)
        return class_name.split('-')[-1]
    return None


def get_product_data(product_id):
    """Fetch product data from Ecwid API"""
    api_url = f"https://app.ecwid.com/api/v3/19699130/products/{product_id}"
    params = {
        'token': 'public_Tg2T71mhciztnMPKr3Jq7xrR6aWe4DNf'
    }

    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching product data: {response.status_code}")
        return None


def extract_prices(product_data):
    """Extract prices from the combinations data"""
    if not product_data or 'combinations' not in product_data:
        return {}

    prices = {}

    for combination in product_data['combinations']:
        # Get the gender option
        gender_option = next((opt for opt in combination['options']
                              if opt['name'] == 'Gender'), None)

        if gender_option:
            gender = gender_option['value']
            price = combination.get('price', 0)
            prices[gender] = f"${price:.2f}"

            # Also store additional information if needed
            prices[f"{gender}_quantity"] = combination.get('quantity', 0)
            prices[f"{gender}_in_stock"] = combination.get('inStock', False)

    return prices


def scrape_chicken_prices(url):
    """Main function to scrape chicken prices"""

    page_source, soup = get_page_content(url)

    # Get token
    token = get_ecwid_token(page_source)
    if not token:
        print("Could not find Ecwid token")
        return {}
    print(f"Found token: {token}")

    # Get product ID from the page
    product_id = get_ecwid_product_id(url)
    if not product_id:
        print(f"Could not find product ID for {url}")
        return {}

    # Fetch product data from API
    product_data = get_product_data(product_id)

    if not product_data:
        return {}
    else:
        print(f"Fetched product data for ID {product_id}")
        print(product_data)

    response = extract_prices(product_data)
    response['url'] = url

    # Extract prices
    return response