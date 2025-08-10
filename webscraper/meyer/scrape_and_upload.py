# webscraper/meyer/scrape_and_upload.py

import json
import time
import random
from typing import List, Dict
import logging

from webscraper.meyer.meyer_scraper import get_chick_list
from webscraper.meyer.chicken_scraper import get_product_data, get_ecwid_token, get_page_content, get_ecwid_product_id
from webscraper.meyer.supabase_uploader import MeyerSupabaseUploader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MeyerScraperIntegration:
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize the Meyer scraper integration.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/service key
        """
        self.uploader = MeyerSupabaseUploader(supabase_url, supabase_key)
        self.scraped_products = []

    def scrape_all_products(self, delay_range: tuple = (2, 5), batch_size: int = 5) -> List[Dict]:
        """
        Scrape all Meyer products and upload in batches.

        Args:
            delay_range: Tuple of (min, max) seconds to delay between requests
            batch_size: Number of products to scrape before uploading to Supabase

        Returns:
            List of scraped product data
        """
        logger.info("Starting Meyer hatchery scraping...")

        # Get all chicken product URLs
        chicken_urls = get_chick_list()

        # Retry logic if no chickens found
        retry_count = 0
        while not chicken_urls and retry_count < 15:
            logger.warning(f"No chickens found. Retry {retry_count + 1}/15...")
            time.sleep(random.randint(3, 7))
            chicken_urls = get_chick_list()
            retry_count += 1

        if not chicken_urls:
            logger.error("Failed to fetch chicken URLs after 15 retries")
            return []

        logger.info(f"Found {len(chicken_urls)} chicken products to scrape")

        # Clear any previously scraped products
        self.scraped_products = []

        # Keep track of current batch
        current_batch = []
        upload_stats = {'total': 0, 'successful': 0, 'failed': 0, 'errors': []}

        # Scrape each product
        for i, url in enumerate(chicken_urls, 1):
            try:
                page_source, soup = get_page_content(url)

                # Get token
                token = get_ecwid_token(page_source)
                if not token:
                    logger.error(f"Could not find Ecwid token for {url}")
                    continue
                logger.debug(f"Found token: {token}")

                # Get product ID from the page
                product_id = get_ecwid_product_id(url)
                if not product_id:
                    logger.error(f"Could not find product ID for {url}")
                    continue

                # Get full product data from API
                product_data = get_product_data(product_id)

                if product_data:
                    # Add the URL to the product data
                    product_data['url'] = url
                    self.scraped_products.append(product_data)
                    current_batch.append(product_data)
                    logger.info(f"Successfully scraped: {product_data.get('name', 'Unknown')}")

                    # Upload batch when it reaches the batch size
                    if len(current_batch) >= batch_size:
                        logger.info(f"Uploading batch of {len(current_batch)} products to Supabase")
                        batch_stats = self.upload_to_supabase(current_batch)

                        # Update overall stats
                        upload_stats['total'] += batch_stats.get('total', 0)
                        upload_stats['successful'] += batch_stats.get('successful', 0)
                        upload_stats['failed'] += batch_stats.get('failed', 0)
                        if 'errors' in batch_stats and batch_stats['errors']:
                            upload_stats['errors'].extend(batch_stats['errors'])

                        # Clear the batch
                        current_batch = []
                else:
                    logger.warning(f"No data returned for: {url}")

                # Random delay to be respectful
                delay = random.uniform(*delay_range)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue

        # Upload any remaining products in the last batch
        if current_batch:
            logger.info(f"Uploading final batch of {len(current_batch)} products to Supabase")
            batch_stats = self.upload_to_supabase(current_batch)

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
        Scrape all products and upload to Supabase in batches.

        Args:
            save_backup: Whether to save a backup JSON file
            batch_size: Number of products to scrape before uploading to Supabase

        Returns:
            Dictionary with scraping and upload statistics
        """
        # Scrape all products and upload in batches
        products = self.scrape_all_products(batch_size=batch_size)

        # Save backup if requested
        if save_backup and products:
            backup_file = f"meyer_products_backup_{int(time.time())}.json"
            with open(backup_file, 'w') as f:
                json.dump(products, f, indent=2)
            logger.info(f"Saved backup to: {backup_file}")

        # Note: Upload is now handled within scrape_all_products in batches
        # No need to upload again here

        return {
            'scraped': len(products),
            'upload_stats': {
                'note': 'Upload statistics are tracked within scrape_all_products method'
            }
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
            # Extract product ID
            product_id = product_url.split('/')[-1].split('-')[-1]

            # Get product data
            product_data = get_product_data(product_id)

            if not product_data:
                raise ValueError(f"No data found for product: {product_url}")

            # Add URL to product data
            product_data['url'] = product_url

            # Upload to Supabase
            result = self.uploader.upload_product(product_data)

            logger.info(f"Successfully updated product: {product_data['name']}")
            return result

        except Exception as e:
            logger.error(f"Error updating product {product_url}: {str(e)}")
            raise


def main():
    """Main function to run the Meyer scraper and upload to Supabase"""

    # Initialize the integration
    integration = MeyerScraperIntegration()

    # Run scraping and upload in batches of 5
    results = integration.scrape_and_upload(save_backup=True, batch_size=5)

    # Print results
    print("\n=== Meyer Hatchery Scraping Complete ===")
    print(f"Products scraped: {results['scraped']}")
    print("Upload statistics: Products were uploaded in batches of 5 during scraping")


if __name__ == "__main__":
    main()
