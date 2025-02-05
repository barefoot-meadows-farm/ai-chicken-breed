# Step 3: Extract chicken information from an individual chicken page
import requests
from bs4 import BeautifulSoup


# Headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

# Function to get the HTML content of a page
def get_page_content(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve {url}: {response.status_code}")
        return None

def get_chicken_info(chicken_url):
    content = get_page_content(chicken_url)
    if not content:
        return {}

    soup = BeautifulSoup(content, "html.parser")

    # Extract chicken name
    name = soup.find("h1", class_="product_title entry-title")
    name = name.get_text(strip=True) if name else "N/A"

    # Extract price
    price = soup.find("span", class_="woocommerce-Price-amount")
    price = price.get_text(strip=True) if price else "N/A"

    # Extract description (if available)
    description = soup.find("div", class_="woocommerce-product-details__short-description")
    description = description.get_text(strip=True) if description else "N/A"

    # Step 2: Extract product IDs from table row elements
    pricing_data = extract_pricing_table(soup)

    return {
        "name": name,
        "price": price,
        "description": description,
        "url": chicken_url,
        "products": pricing_data
    }


def extract_pricing_table(soup):
    # Extract product IDs from table row elements
    product_ids = [
        {"id": row['id'].replace('product-', ''), "gender": row.find('label', {"for": row['id']}).get_text(strip=True)}
        for row in soup.find_all('tr', id=True)
    ]

    pricing_data = {}
    base_url = "https://www.cacklehatchery.com/pricing_table.php?id="

    for product_id in product_ids:
        api_url = f"{base_url}{product_id['id']}"
        response = requests.get(api_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr")
            product_prices = [
                {size_row.get_text(strip=True): price_row.get_text(strip=True)}
                for i in range(0, len(rows), 2)
                for size_row, price_row in
                zip(rows[i].find_all("td"), rows[i + 1].find_all("td") if i + 1 < len(rows) else [])
            ]
            pricing_data[product_id['gender']] = product_prices

    return pricing_data