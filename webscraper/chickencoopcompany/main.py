from webscraper.chickencoopcompany.chicken_scraper import scrape_chickens

if __name__ == "__main__":
    print("Starting Chicken Coop Company scraper...")
    total_images = scrape_chickens()
    print(f"Scraping complete! Downloaded {total_images} images.")
    print("Images saved to ./dataset/train/{breed_name}/")