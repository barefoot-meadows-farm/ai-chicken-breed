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


def extract_availability_table(soup):
    """
    Extract availability information from the availability table on Cackle Hatchery chicken pages.

    Args:
        soup: BeautifulSoup object of the page content

    Returns:
        List of dictionaries containing availability data with dates and status
    """
    availability_data = []

    # Find the availability table - it has id="availability"
    availability_table = soup.find("table", {"id": "availability"})

    if not availability_table:
        # Try to find it within the availability tab panel if not found directly
        availability_panel = soup.find("div", {"id": "tab-availability"})
        if availability_panel:
            availability_table = availability_panel.find("table", {"id": "availability"})

    if not availability_table:
        return availability_data

    # Find all rows in the tbody
    tbody = availability_table.find("tbody")
    if not tbody:
        return availability_data

    rows = tbody.find_all("tr")

    for row in rows:
        # Skip rows that don't have data cells
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # Get the date from the first td
        date_cell = cells[0]
        date = date_cell.get_text(strip=True)

        # Get the availability status from the second td
        status_cell = cells[1]

        # Determine status based on the classes of the td
        cell_classes = status_cell.get("class", [])

        # Check for status based on class names
        if "available" in cell_classes:
            status = "Available"
        elif "low-availability" in cell_classes:
            status = "Low Availability"
        elif "unavailable" in cell_classes:
            status = "Unavailable"
        else:
            # If no class matches, check for the span inside and its title attribute
            status_span = status_cell.find("span", class_="dashicons")
            if status_span:
                title = status_span.get("title", "")
                if "Available" in title and "Low" in title:
                    status = "Low Availability"
                elif "Available" in title:
                    status = "Available"
                elif "Unavailable" in title:
                    status = "Unavailable"
                else:
                    status = "Unknown"
            else:
                status = "Unknown"

        availability_data.append({
            "date": date,
            "status": status
        })

    return availability_data


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

    # Extract availability data
    availability_data = extract_availability_table(soup)

    return {
        "name": name,
        "price": price,
        "description": description,
        "url": chicken_url,
        "products": pricing_data,
        "availability": availability_data
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
                {"size": size_row.get_text(strip=True), "price": price_row.get_text(strip=True)}
                for i in range(0, len(rows), 2)
                for size_row, price_row in
                zip(rows[i].find_all("td"), rows[i + 1].find_all("td") if i + 1 < len(rows) else [])
            ]
            pricing_data[product_id['gender']] = product_prices

    return pricing_data