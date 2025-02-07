import re
from datetime import datetime
from playwright.async_api import async_playwright

async def scrape_mcmurray_chicken_info(chicken):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set up a realistic browser context
        await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        # Navigate to the chicken listing page
        await page.goto(chicken["link"])
        await page.wait_for_timeout(5000)  # Wait for the page to fully load

        pricing = await extract_pricing_table(page)
        availability = await extract_availability_table(page)
        info = await extract_chicken_info(page)
        # Extract chicken Info
        return {
            "name": chicken["name"],
            "price": pricing,
            "availability": availability,
            "info": info,
            "url": chicken["link"]
        }

async def extract_pricing_table(page):
    rows = await page.locator("table.mmSkuPriceTable tbody tr").all()

    products = []
    for row in rows:
        # Ensure you await async methods for each element
        sku_element = await row.locator('.product_sku').text_content()
        sku = {
            'code': sku_element.strip(),
            'id': await row.locator('.product_sku').get_attribute('data-skuid')
        }

        # Same for description, prices, etc.
        description = await row.locator('.pricing-table-desc').text_content()

        # Await the locator here and then slice it
        price_cells = await row.locator('td.text-right').all()
        prices = []
        for cell in price_cells[:-1]:  # Now it's properly sliced after awaiting
            range_text = await cell.locator('.colDesc').text_content()
            price_text = (await cell.text_content()).replace(range_text, '').strip()
            prices.append({
                'range': range_text.strip(),
                'price': price_text.strip()
            })

        product_data = {
            'sku': sku,
            'type': description.strip(),
            'prices': prices,
        }

        products.append(product_data)

    return products

async def extract_availability_table(page):
    # Wait for the page to load and locate the accordion by its ID
    await page.wait_for_selector('#mmAvailToggleTitle')

    # Click the accordion to reveal the content
    await page.click('#mmAvailToggleTitle')
    await page.wait_for_timeout(5000)  # Wait for the page to fully load

    # Optional: Ensure the content is now visible
    await page.wait_for_selector('#show_avail', state='visible')

    # Click the "Show All Dates" button
    await page.wait_for_selector('#btnAvailShowAllDates')
    await page.click('#btnAvailShowAllDates')
    await page.wait_for_timeout(5000)  # Wait for the page to fully load
    await page.screenshot(path='mcmurray.png')

    # Wait for the table to update
    await page.wait_for_selector('table', state='visible')

    # Extract or process the data if needed
    table_html = await page.locator('#show_avail').inner_html()

    cells = await page.locator("div#show_avail table td").all()
    print(f"Found {len(cells)} cells")
    availability_data = []

    for cell in cells:
        cell_text = await cell.inner_text()
        if not cell_text:  # Skip empty cells
            continue

        # Split cell text into lines
        lines = cell_text.split('\n')
        if not lines:
            continue

        # Parse date from first line
        date_text = lines[0].strip()
        try:
            # Replace non-breaking spaces with regular spaces
            date_text = date_text.replace('\xa0', ' ')
            date = datetime.strptime(date_text, '%b %d, %Y').strftime('%Y-%m-%d')
        except ValueError as e:
            print(f"Date parsing error: {e} for text: {date_text}")
            continue

        # Initialize availability dictionary
        availability = {
            'female': {'status': 'Not Available', 'available': 0},
            'male': {'status': 'Not Available', 'available': 0},
            'straight_run': {'status': 'Not Available', 'available': 0}
        }

        # Get all availability spans
        spans = await cell.locator('span').all()
        for span in spans:
            class_name = await span.get_attribute('class')
            text = await span.inner_text()

            # Determine type and status
            type_key = None
            if text.startswith('F'):
                type_key = 'female'
            elif text.startswith('M'):
                type_key = 'male'
            elif text.startswith('SR'):
                type_key = 'straight_run'

            if type_key:
                if 'prodAvailAvail' in class_name:
                    availability[type_key] = {'status': 'Available', 'available': None}
                elif 'prodAvailLtd' in class_name:
                    # Extract number available using regex
                    match = re.search(r'\((\d+)\s*avail\)', text)
                    if match:
                        available = int(match.group(1))
                        availability[type_key] = {'status': 'Limited', 'available': available}
                elif 'prodAvailNA' in class_name:
                    availability[type_key] = {'status': 'Not Available', 'available': 0}

        availability_data.append({
            'date': date,
            'availability': availability
        })

    return availability_data

async def extract_chicken_info(page):
    # Expand the Quick Stats accordion
    quick_stats_toggle = page.locator('.et_pb_toggle_0')
    await quick_stats_toggle.locator('h5:has-text("QUICK STATS")').click()

    # Wait for the content to become visible
    await page.wait_for_selector('.et_pb_toggle_content', state='visible')

    # Extract table data
    rows = await quick_stats_toggle.locator('table tr').all()
    quick_stats = {}

    for i in range(len(rows)):
        key = await rows[i].locator('td').nth(0).text_content()
        value = await rows[i].locator('td').nth(1).text_content()
        quick_stats[key.strip(':')] = value.strip()

    return quick_stats