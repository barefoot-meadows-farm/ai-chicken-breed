import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib

# Base URL
BASE_URL = "https://www.chickencoopcompany.com"
BREEDS_URL = f"{BASE_URL}/collections/poultry-chicken-breeds"

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Referer": BASE_URL
}


def get_page_content(url, retry=3, delay=2):
    """
    Fetches the content of a page with retry mechanism.

    Args:
        url (str): The URL to fetch
        retry (int): Number of retries if request fails
        delay (int): Delay between retries in seconds

    Returns:
        BeautifulSoup object or None if all retries fail
    """
    for attempt in range(retry):
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()

            # Add a small delay to be respectful to the server
            time.sleep(delay)

            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1}/{retry} failed: {e}")
            if attempt < retry - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff

    return None


def get_breed_links():
    """
    Gets links to all chicken breed pages.

    Returns:
        list: List of dictionaries with breed name and URL
    """
    print("Getting breed links from main page...")

    # Use a different approach for this site - we need to handle infinite scroll/load more functionality
    # This will require Selenium or Playwright to interact with the page

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')

    # Initialize the webdriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    breeds = []

    try:
        # Load the main page
        driver.get(BREEDS_URL)
        print("Page loaded, waiting for content...")
        time.sleep(5)  # Initial wait for the page to load

        # Check if there's a "Load more" or pagination button
        load_more_button_selectors = [
            "button:contains('Load more')",
            "button.load-more",
            "a.load-more",
            ".load-more-button",
            "button:contains('View more')",
            ".view-more",
            "[data-action='load-more']",
            ".btn--load-more",
            ".loadmore",
            "#more",
            ".more-products"
        ]

        # Function to find and click the load more button
        def click_load_more():
            for selector in load_more_button_selectors:
                try:
                    # Try to find the button using different strategies
                    if selector.startswith("button:contains("):
                        text = selector.split("'")[1]
                        buttons = driver.find_elements(By.TAG_NAME, "button")
                        for button in buttons:
                            if text.lower() in button.text.lower():
                                print(f"Found load more button with text: {button.text}")
                                driver.execute_script("arguments[0].scrollIntoView();", button)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", button)
                                return True
                    else:
                        try:
                            button = driver.find_element(By.CSS_SELECTOR, selector)
                            print(f"Found load more button with selector: {selector}")
                            driver.execute_script("arguments[0].scrollIntoView();", button)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", button)
                            return True
                        # FIX: Use a tuple for multiple exceptions instead of the '|' operator
                        except (NoSuchElementException, ElementClickInterceptedException):
                            print(f"Found load more button with selector: {selector}")
                            continue
                # FIX: Use a tuple for multiple exceptions instead of the '|' operator
                except (NoSuchElementException, ElementClickInterceptedException):
                    print(f"Load more button not found with selector: {selector}")
                    continue
            return False

        # Try to load more content until no more load button is found
        max_clicks = 10  # Safety limit
        click_count = 0

        while click_count < max_clicks:
            # Scroll to the bottom to trigger any lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Wait for content to load

            # Try to click the load more button
            if click_load_more():
                print(f"Clicked load more button ({click_count + 1}/{max_clicks})")
                click_count += 1
                time.sleep(5)  # Wait for new content to load
            else:
                print("No more load buttons found")
                break

        # Now extract all product links from the fully loaded page
        print("Extracting product links...")

        # Different possible selectors for product cards/links
        product_selectors = [
            ".product-card",
            ".product-item",
            "li[id^='product-']",
            ".grid-product",
            ".grid__item",
            ".grid-view-item",
            "[data-product-card]",
            ".product-block",
            ".product"
        ]

        all_products = []
        for selector in product_selectors:
            products = driver.find_elements(By.CSS_SELECTOR, selector)
            if products:
                print(f"Found {len(products)} products with selector: {selector}")
                all_products.extend(products)
                break

        # If we didn't find products with the card selectors, try link selectors
        if not all_products:
            link_selectors = [
                "a[href*='/products/']",
                "a[href*='/collections/'][href*='/products/']",
                ".product-link"
            ]

            for selector in link_selectors:
                products = driver.find_elements(By.CSS_SELECTOR, selector)
                if products:
                    print(f"Found {len(products)} product links with selector: {selector}")
                    all_products.extend(products)
                    break

        # Process each product to extract breed information
        for product in all_products:
            try:
                # Extract product URL
                if product.tag_name == 'a':
                    product_url = product.get_attribute('href')
                else:
                    # If it's not an <a> tag, find the link inside
                    link_element = product.find_element(By.CSS_SELECTOR, "a[href*='/products/']")
                    product_url = link_element.get_attribute('href')

                # Find breed name - try multiple possible elements
                breed_name = None

                # Try to find heading elements first
                heading_selectors = [
                    "h2", "h3", "h4",
                    ".product-title",
                    ".product-name",
                    ".grid-product__title",
                    ".card__heading"
                ]

                for selector in heading_selectors:
                    try:
                        name_element = product.find_element(By.CSS_SELECTOR, selector)
                        breed_name = name_element.text.strip()
                        if breed_name and not breed_name.lower() in ["buy now", "add to cart", "added to cart"]:
                            break
                    except NoSuchElementException:
                        continue

                # If no heading found with valid name, try alt text of the image
                if not breed_name or breed_name.lower() in ["buy now", "add to cart", "added to cart"]:
                    try:
                        img = product.find_element(By.TAG_NAME, "img")
                        breed_name = img.get_attribute("alt")
                    except NoSuchElementException:
                        pass

                # Last resort - use the URL path to extract a name
                if not breed_name or breed_name.lower() in ["buy now", "add to cart", "added to cart"]:
                    # Extract from URL: /products/breed-name -> breed-name
                    url_path = product_url.split("/products/")[-1].split("?")[0]
                    breed_name = url_path.replace("-", " ").replace("_", " ").title()

                if breed_name and product_url:
                    # Clean the breed name
                    clean_name = clean_breed_name(breed_name)
                    # Add to list if it looks like a valid breed name and not a button text
                    if clean_name and not clean_name.lower() in ["buy_now", "add_to_cart", "added_to_cart"]:
                        print(f"Found breed: {clean_name} - {product_url}")
                        breeds.append({
                            'name': clean_name,
                            'url': product_url
                        })
            except Exception as e:
                print(f"Error processing a product: {e}")
                continue

        print(f"Total breeds found: {len(breeds)}")

    except Exception as e:
        print(f"Error during web scraping: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close the driver
        driver.quit()

    return breeds


def clean_breed_name(name):
    """
    Cleans a breed name for use as a directory name.

    Args:
        name (str): The raw breed name

    Returns:
        str: A cleaned name suitable for folder names
    """
    if not name:
        return ""

    # Skip button text and other non-breed names
    lower_name = name.lower()
    skip_texts = ["buy now", "add to cart", "added to cart", "view details", "learn more", "sold out"]
    if any(skip_text in lower_name for skip_text in skip_texts):
        return ""

    # Remove any references to "chicken" or "breed" or "chicks"
    name = name.replace("Chicken", "").replace("chicken", "")
    name = name.replace("Breed", "").replace("breed", "")
    name = name.replace("Chicks", "").replace("chicks", "")

    # Remove common suffixes
    name = name.replace("Poultry", "").replace("poultry", "")

    # Remove any parentheses and their contents
    while '(' in name and ')' in name:
        start = name.find('(')
        end = name.find(')')
        if start < end:
            name = name[:start] + name[end + 1:]
        else:
            break

    # Replace special characters with underscores
    import re
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    # If name became empty after cleanup, return empty string
    if not name:
        return ""

    return name


def extract_images(soup, breed_name):
    """
    Extracts image URLs from the product page.

    Args:
        soup (BeautifulSoup): The parsed HTML
        breed_name (str): The breed name

    Returns:
        list: List of image URLs
    """
    image_urls = []

    # First, look for Swiper slider images (as shown in the example)
    swiper_images = soup.select('.swiper-wrapper img')

    if swiper_images:
        print(f"Found {len(swiper_images)} images in Swiper carousel")
        for img in swiper_images:
            src = img.get('src') or img.get('data-srcset') or img.get('srcset')
            if src:
                # For srcset, take the largest image
                if ' ' in src and ',' in src:  # It's a srcset
                    parts = src.split(',')
                    # Get the last part which usually has the highest resolution
                    src = parts[-1].strip().split(' ')[0]

                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = f"https:{src}"
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(BASE_URL, src)

                # Remove query parameters that limit image size
                src = src.split('?')[0]

                # Remove width specifications in the URL path
                src = re.sub(r'&width=\d+', '', src)

                image_urls.append(src)

    # If no Swiper images found, try other common selectors
    if not image_urls:
        # Try various selectors commonly used in Shopify sites
        selectors = [
            '.product-single__photo img',
            '.product__photo img',
            '.featured-media img',
            '[data-product-media-type="image"] img',
            '.product-gallery__image',
            '.product-image img',
            '.product-single__image',
            '.product__images img',
            'figure img',
            '.carousel img'
        ]

        for selector in selectors:
            product_images = soup.select(selector)
            if product_images:
                print(f"Found {len(product_images)} images using selector: {selector}")
                for img in product_images:
                    src = img.get('src') or img.get('data-src') or img.get('srcset')
                    if src:
                        # Handle srcset
                        if ' ' in src and ',' in src:  # It's a srcset
                            parts = src.split(',')
                            src = parts[-1].strip().split(' ')[0]

                        # Convert relative URLs to absolute
                        if src.startswith('//'):
                            src = f"https:{src}"
                        elif not src.startswith(('http://', 'https://')):
                            src = urljoin(BASE_URL, src)

                        # Remove query parameters
                        src = src.split('?')[0]

                        image_urls.append(src)

    # Also look for images in the product thumbnails
    thumbnail_images = soup.select('.product-single__thumbnails img, .product-thumbnails img')
    if thumbnail_images:
        print(f"Found {len(thumbnail_images)} thumbnail images")
        for img in thumbnail_images:
            src = img.get('src') or img.get('data-src') or img.get('data-full-size-url')
            if src:
                if src.startswith('//'):
                    src = f"https:{src}"
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(BASE_URL, src)

                src = src.split('?')[0]

                image_urls.append(src)

    # Look for any additional hidden images in data attributes
    for img_container in soup.select('[data-full-size-url], [data-zoom-image], [data-zoom], [data-high-res-url]'):
        src = (img_container.get('data-full-size-url') or
               img_container.get('data-zoom-image') or
               img_container.get('data-zoom') or
               img_container.get('data-high-res-url'))

        if src:
            if src.startswith('//'):
                src = f"https:{src}"
            elif not src.startswith(('http://', 'https://')):
                src = urljoin(BASE_URL, src)

            src = src.split('?')[0]
            image_urls.append(src)

    # Process image URLs to get highest quality version
    processed_urls = []
    for url in image_urls:
        # Remove any image size limitations in the URL
        url = url.replace('_small', '').replace('_medium', '').replace('_large', '')
        url = url.replace('_100x', '').replace('_200x', '').replace('_400x', '')
        url = re.sub(r'_\d+x\d+', '', url)
        url = re.sub(r'_\d+x', '', url)
        url = re.sub(r'&width=\d+', '', url)

        processed_urls.append(url)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in processed_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def download_image(url, output_path, breed_name, index=0):
    """
    Downloads an image to the specified path.

    Args:
        url (str): The image URL
        output_path (str): The directory to save the image
        breed_name (str): The breed name
        index (int): Image index for naming

    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Make sure the directory exists
        os.makedirs(output_path, exist_ok=True)

        # Clean up the URL - check if there's a version parameter and remove it
        url = re.sub(r'\?v=\d+', '', url)
        url = re.sub(r'&v=\d+', '', url)

        # Handle URLs with CDN width modifiers - extract and save the largest version
        width_match = re.search(r'&width=(\d+)', url)
        if width_match:
            width = int(width_match.group(1))
            # Replace with a larger width to get a better quality image
            url = re.sub(r'&width=\d+', '&width=2000', url)

        # Create a unique filename based on URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        file_extension = os.path.splitext(url)[1]
        if not file_extension or len(file_extension) <= 1:
            file_extension = '.jpg'  # Default to jpg if no extension

        file_name = f"{breed_name}_{index}_{url_hash}{file_extension}"
        file_path = os.path.join(output_path, file_name)

        # Check if file already exists
        if os.path.exists(file_path):
            print(f"File already exists: {file_path}")
            return True

        # Download the image with a timeout and retry logic
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = requests.get(url, headers=HEADERS, stream=True, timeout=30)
                response.raise_for_status()
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if retry < max_retries - 1:
                    sleep_time = 2 ** retry  # Exponential backoff
                    print(f"Retry {retry + 1}/{max_retries} after {sleep_time}s. Error: {e}")
                    time.sleep(sleep_time)
                else:
                    raise

        # Check if it's actually an image by content-type
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            print(f"Not an image: {url} (Content-Type: {content_type})")
            return False

        # Save the image
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify the image is valid
        try:
            from PIL import Image
            img = Image.open(file_path)
            img.verify()  # Verify it's a valid image

            # Get the image dimensions
            img = Image.open(file_path)  # Need to reopen after verify
            width, height = img.size

            # Log image details
            print(f"Downloaded: {file_path} ({width}x{height})")
            return True
        except Exception as e:
            print(f"Invalid image: {file_path} - {e}")
            # Remove the invalid image
            os.remove(file_path)
            return False

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def scrape_chickens():
    """
    Main function to scrape chicken breed images and download them.

    Returns:
        int: Number of images downloaded
    """
    breeds = get_breed_links()
    print(f"Found {len(breeds)} chicken breeds")

    total_images = 0

    for breed in breeds:
        print(f"Processing breed: {breed['name']}")

        # Create output directory
        output_dir = os.path.join("../dataset/train", breed['name'])

        # Get the breed page
        soup = get_page_content(breed['url'])
        if not soup:
            print(f"Failed to retrieve the page for {breed['name']}")
            continue

        # Extract image URLs
        image_urls = extract_images(soup, breed['name'])
        print(f"Found {len(image_urls)} images for {breed['name']}")

        # Download each image
        for i, url in enumerate(image_urls):
            success = download_image(url, output_dir, breed['name'], i)
            if success:
                total_images += 1

            # Small delay to avoid overloading the server
            time.sleep(1)

    return total_images


if __name__ == "__main__":
    print("Starting to scrape chicken breed images...")
    num_images = scrape_chickens()
    print(f"Scraping complete. Downloaded {num_images} images.")