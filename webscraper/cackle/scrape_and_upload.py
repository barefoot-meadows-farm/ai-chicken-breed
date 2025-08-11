# webscraper/cackle/scrape_and_upload.py

import json
import time
from typing import List, Dict
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import requests

from webscraper.cackle.cackle_scraper import get_category_links, get_chicken_links, get_page_content
from webscraper.cackle.chicken_scraper import get_chicken_info, extract_availability_table
from .supabase_uploader import CackleSupabaseUploader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CackleScraperIntegration:
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize the Cackle scraper integration.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/service key
        """
        self.uploader = CackleSupabaseUploader(supabase_url, supabase_key)
        self.scraped_products = []

    def scrape_availability_calendar(self, chicken_url: str) -> List[Dict]:
        """
        Scrape the availability calendar for a specific chicken using the existing function.

        Args:
            chicken_url: URL of the chicken product page

        Returns:
            List of availability entries
        """
        try:
            # Get page content
            content = get_page_content(chicken_url)
            if not content:
                logger.warning(f"Could not fetch page content for: {chicken_url}")
                return []

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")

            # Use the existing extraction function
            availability_data = extract_availability_table(soup)

            # Convert date format if needed (from "Aug 11" to "2025-08-11")
            current_year = datetime.now().year
            formatted_availability = []

            for entry in availability_data:
                try:
                    # Parse the date
                    date_str = entry['date']

                    # Check if the date is already in YYYY-MM-DD format (possibly with year repeated)
                    if '-' in date_str:
                        # Handle format like "2025-09-24 2025"
                        date_parts = date_str.split()
                        # Use just the first part (YYYY-MM-DD)
                        parsed_date = datetime.strptime(date_parts[0], "%Y-%m-%d")
                    else:
                        # Try the original format like "Aug 11"
                        parsed_date = datetime.strptime(f"{date_str} {current_year}", "%b %d %Y")

                        # If the date is in the past, it might be for next year
                        if parsed_date < datetime.now():
                            parsed_date = datetime.strptime(f"{date_str} {current_year + 1}", "%b %d %Y")

                    formatted_availability.append({
                        'date': parsed_date.strftime('%Y-%m-%d'),
                        'status': entry['status']
                    })
                except ValueError as e:
                    logger.warning(f"Could not parse date '{date_str}': {str(e)}")
                    # Try alternative date format or use as-is
                    formatted_availability.append(entry)

            logger.info(f"Extracted {len(formatted_availability)} availability entries for {chicken_url}")
            return formatted_availability

        except Exception as e:
            logger.error(f"Error scraping availability for {chicken_url}: {str(e)}")
            return []

    def scrape_all_products(self, delay: float = 1.0, batch_size: int = 5) -> List[Dict]:
        """
        Scrape all Cackle products with batch uploading.

        Args:
            delay: Delay between requests in seconds
            batch_size: Number of products to scrape before uploading

        Returns:
            List of scraped product data
        """
        logger.info("Starting Cackle hatchery scraping...")

        # Get all category links
        categories = get_category_links()
        if not categories:
            logger.error("No categories found")
            return []

        logger.info(f"Found {len(categories)} categories")

        all_chickens = []

        # Scrape each category
        for category_url in categories:
            logger.info(f"Scraping category: {category_url}")
            try:
                chicken_links = get_chicken_links(category_url)
                logger.info(f"Found {len(chicken_links)} chickens in this category")
                all_chickens.extend(chicken_links)
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error scraping category {category_url}: {str(e)}")
                continue

        # Remove duplicates based on URL
        unique_chickens = []
        seen_urls = set()
        for chicken in all_chickens:
            if chicken['url'] not in seen_urls:
                seen_urls.add(chicken['url'])
                unique_chickens.append(chicken)

        logger.info(f"Total unique chickens found: {len(unique_chickens)}")

        # Clear scraped products
        self.scraped_products = []

        # Keep track of current batch and upload stats
        current_batch = []
        upload_stats = {'total': 0, 'successful': 0, 'failed': 0, 'errors': []}

        # Scrape detailed info for each chicken
        for i, chicken in enumerate(unique_chickens, 1):
            try:
                logger.info(f"Scraping product {i}/{len(unique_chickens)}: {chicken['name']}")

                # Get detailed chicken info
                chicken_info = get_chicken_info(chicken['url'])

                if chicken_info:
                    # Get availability calendar using the integrated function
                    availability = self.scrape_availability_calendar(chicken['url'])
                    if availability:
                        chicken_info['availability'] = availability

                    self.scraped_products.append(chicken_info)
                    current_batch.append(chicken_info)

                    # Upload batch when it reaches the batch size
                    if len(current_batch) >= batch_size:
                        logger.info(f"Uploading batch of {len(current_batch)} products to Supabase")
                        batch_stats = self.uploader.batch_upload_products(current_batch)

                        # Update overall stats
                        upload_stats['total'] += batch_stats.get('total', 0)
                        upload_stats['successful'] += batch_stats.get('successful', 0)
                        upload_stats['failed'] += batch_stats.get('failed', 0)
                        if 'errors' in batch_stats and batch_stats['errors']:
                            upload_stats['errors'].extend(batch_stats['errors'])

                        # Clear the batch
                        current_batch = []

                # Respectful delay
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error scraping {chicken.get('name', 'Unknown')}: {str(e)}")
                continue

        # Upload any remaining products in the last batch
        if current_batch:
            logger.info(f"Uploading final batch of {len(current_batch)} products to Supabase")
            batch_stats = self.uploader.batch_upload_products(current_batch)

            # Update overall stats
            upload_stats['total'] += batch_stats.get('total', 0)
            upload_stats['successful'] += batch_stats.get('successful', 0)
            upload_stats['failed'] += batch_stats.get('failed', 0)
            if 'errors' in batch_stats and batch_stats['errors']:
                upload_stats['errors'].extend(batch_stats['errors'])

        logger.info(f"Scraping complete. Total products scraped: {len(self.scraped_products)}")
        logger.info(f"Upload stats: {upload_stats['successful']} successful, {upload_stats['failed']} failed")

        return self.scraped_products

    def upload_to_supabase(self, products: List[Dict] = None) -> Dict:
        """
        Upload scraped products to Supabase.

        Args:
            products: List of products to upload (uses scraped_products if None)

        Returns:
            Upload statistics
        """
        products_to_upload = products or self.scraped_products

        if not products_to_upload:
            logger.warning("No products to upload")
            return {'total': 0, 'successful': 0, 'failed': 0}

        logger.info(f"Starting upload of {len(products_to_upload)} products to Supabase")

        stats = self.uploader.batch_upload_products(products_to_upload)

        return stats

    def scrape_and_upload(self, save_backup: bool = True, batch_size: int = 5) -> Dict:
        """
        Scrape all products and upload to Supabase.

        Args:
            save_backup: Whether to save a backup JSON file
            batch_size: Number of products to scrape before uploading

        Returns:
            Dictionary with scraping and upload statistics
        """
        # Scrape all products with batch uploading
        products = self.scrape_all_products(batch_size=batch_size)

        # Save backup if requested
        if save_backup and products:
            backup_file = f"cackle_products_backup_{int(time.time())}.json"
            with open(backup_file, 'w') as f:
                json.dump(products, f, indent=2)
            logger.info(f"Saved backup to: {backup_file}")

        return {
            'scraped': len(products),
            'message': 'Products were uploaded in batches during scraping'
        }

    def update_single_product(self, product_url: str) -> Dict:
        """
        Update a single product in Supabase.

        Args:
            product_url: URL of the product to update

        Returns:
            Updated product data
        """
        try:
            logger.info(f"Updating product: {product_url}")

            # Scrape the product
            product_data = get_chicken_info(product_url)

            if not product_data:
                raise ValueError(f"No data found for product: {product_url}")

            # Get availability using the integrated function
            availability = self.scrape_availability_calendar(product_url)
            if availability:
                product_data['availability'] = availability

            # Upload to Supabase
            result = self.uploader.upload_product(product_data)

            logger.info(f"Successfully updated product: {product_data['name']}")
            return result

        except Exception as e:
            logger.error(f"Error updating product {product_url}: {str(e)}")
            raise
