from playwright.sync_api import sync_playwright

from webscraper.mcmurray.chicken_scraper import scrape_mcmurray_chicken_info

BASE_URL = "https://www.mcmurrayhatchery.com"

def scrape_mcmurray():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Set up a realistic browser context
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        # Navigate to the chicken listing page
        page.goto(f"{BASE_URL}/chicks.html")
        page.wait_for_timeout(5000)  # Wait for the page to fully load
        # Save a screenshot for debugging
        page.screenshot(path="debug_screenshot.png")

        # Extract chicken cards
        chicken_cards = page.locator("div.productOuter")
        chickens = []
        for i in range(chicken_cards.count()):
            card = chicken_cards.nth(i)
            title = card.locator("div.title").inner_text()
            link = card.locator("a.details").first.get_attribute("href")
            chickens.append({"name": title, "link": BASE_URL + link})

        browser.close()
        return chickens


if __name__ == "__main__":
    chicken_list = scrape_mcmurray()
    for chicken in chicken_list:
        try:
            print(chicken)
            chicken_info = scrape_mcmurray_chicken_info(chicken)
            print(chicken_info)
        except Exception as e:
            print(f"Error extracting Chicken Info: {e}")
            import traceback
            traceback.print_exc()