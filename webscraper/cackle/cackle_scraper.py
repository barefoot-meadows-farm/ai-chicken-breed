import requests
from bs4 import BeautifulSoup

from webscraper.cackle.chicken_scraper import get_chicken_info

# Base URLs
BASE_URL = "https://www.cacklehatchery.com"
BABY_CHICKS_URL = f"{BASE_URL}/product-category/baby-chicks/"

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

# Step 1: Get all category links from the baby-chicks page
def get_category_links():
    print("Getting category links...")
    content = get_page_content(BABY_CHICKS_URL)
    if not content:
        return []

    soup = BeautifulSoup(content, "html.parser")
    category_links = []

    # Find category links (adjust selectors based on page structure)
    category_section = soup.find_all("li", class_="product-category")
    for category_item in category_section:
        link = category_item.find("a")
        if not link:
            continue
        href = link.get("href")
        if href:
            print(href)
            category_links.append(BASE_URL + href if not href.startswith("http") else href)

    return category_links

# Step 2: Get all chicken links from a category page
def get_chicken_links(category_url):
    content = get_page_content(category_url)
    if not content:
        return []

    soup = BeautifulSoup(content, "html.parser")
    chicken_links = []

    # Find chicken product links (adjust selectors as needed)
    product_links = soup.find_all("li", class_="type-product")
    for product_item in product_links:
        link = product_item.find("a")
        if not link:
            continue
        href = link.get("href")
        # Pull Chicken name from woocommerce-LoopProduct-link
        name = link.find("h2", class_="woocommerce-loop-product__title")
        print(name.get_text(strip=True))
        print(href)
        if href:
            # Append the name and url to the chicken_links list
            chicken_links.append({"name": name.get_text(strip=True), "url": href})

    return chicken_links


if __name__ == "__main__":
    print("Scraping Cackle Hatchery...")
    categories = get_category_links()
    print(f"Found {len(categories)} categories.")

    all_chickens = []

    for category_url in categories:
        print(f"Scraping category: {category_url}")
        chicken_links = get_chicken_links(category_url)
        print(f"Found {len(chicken_links)} chickens in this category.")

        # Add all chicken links to the list
        all_chickens.extend(chicken_links)


    # Remove Duplicates based on URL
    all_chickens = [dict(t) for t in {tuple(d.items()) for d in all_chickens}]

    print("Scraping complete. Total chickens scraped:", len(all_chickens))

    # Example: print the first 5 chicken records
    for chicken in all_chickens[:5]:
        print(get_chicken_info(chicken['url']))