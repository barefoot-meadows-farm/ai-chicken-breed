# webscraper/cackle/supabase_uploader.py

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CackleSupabaseUploader:
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize the Cackle Supabase uploader.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/service key
        """
        load_dotenv()
        self.supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self.supabase_key = supabase_key or os.environ.get("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and key must be provided or set in environment variables")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self._hatchery_id = None

    @property
    def hatchery_id(self):
        """Get or fetch the Cackle hatchery ID"""
        if not self._hatchery_id:
            result = self.client.table('hatcheries').select('id').eq('code', 'cackle').single().execute()
            self._hatchery_id = result.data['id']
        return self._hatchery_id

    def upload_product(self, product_data: Dict) -> Dict:
        """
        Upload a Cackle product to Supabase.

        Args:
            product_data: Dictionary containing the scraped Cackle product data

        Returns:
            Dictionary with the created product record
        """
        try:
            # Extract slug from URL
            product_slug = self._extract_slug_from_url(product_data['url'])

            # Parse minimums from description
            minimums = self._parse_minimums(product_data.get('description', ''))

            # Extract seasonal info
            seasonal_info = self._extract_seasonal_info(product_data.get('description', ''))

            # Get or create breed alias
            breed_alias_id = self._get_or_create_breed_alias(product_data['name'])

            # Prepare product data
            cackle_product = {
                'breed_alias_id': breed_alias_id,
                'product_url': product_data['url'],
                'product_slug': product_slug,
                'product_name': product_data['name'],
                'description': product_data.get('description', ''),
                'base_price': product_data.get('price', '$0.00'),
                'minimum_not_sexed': minimums.get('not_sexed'),
                'minimum_female': minimums.get('female'),
                'minimum_male': minimums.get('male'),
                'minimum_total': minimums.get('total'),
                'seasonal_info': seasonal_info,
                'last_scraped_at': datetime.utcnow().isoformat()
            }

            # Upsert the product
            result = self.client.table('cackle_products').upsert(
                cackle_product,
                on_conflict='product_url'
            ).execute()

            product_id = result.data[0]['id']

            # Upload pricing tiers
            self._upload_pricing_tiers(product_id, product_data.get('products', {}))

            # Upload availability if present
            if 'availability' in product_data:
                self._upload_availability(product_id, product_data['availability'])

            logger.info(f"Successfully uploaded product: {product_data['name']}")
            return result.data[0]

        except Exception as e:
            logger.error(f"Error uploading product {product_data.get('name', 'Unknown')}: {str(e)}")
            raise

    def _extract_slug_from_url(self, url: str) -> str:
        """Extract the product slug from the URL"""
        # https://www.cacklehatchery.com/product/columbian-wyandottes
        parts = url.split('/')
        return parts[-1] if parts else ''

    def _parse_minimums(self, description: str) -> Dict[str, Optional[int]]:
        """
        Parse minimum order quantities from the description.

        Args:
            description: Product description containing minimums

        Returns:
            Dictionary with minimum quantities by type
        """
        minimums = {
            'not_sexed': None,
            'female': None,
            'male': None,
            'total': None
        }

        # Look for patterns like "Not Sexed = 3", "Female = 3", etc.
        patterns = {
            'not_sexed': r'Not Sexed\s*=\s*(\d+)',
            'female': r'Female\s*=\s*(\d+)',
            'male': r'Male\s*=\s*(\d+)',
            'total': r'Total of\s*(\d+)\s*birds'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                minimums[key] = int(match.group(1))

        return minimums

    def _extract_seasonal_info(self, description: str) -> Optional[str]:
        """Extract seasonal/shipping information from description"""
        # Look for patterns like "Seasonal/Shipped Feb thru September"
        seasonal_match = re.search(r'(Seasonal[^.]+)', description)
        if seasonal_match:
            return seasonal_match.group(1).strip()

        # Look for shipping period info
        ship_match = re.search(r'(Shipped [^.]+)', description)
        if ship_match:
            return ship_match.group(1).strip()

        return None

    def _get_or_create_breed_alias(self, product_name: str) -> str:
        """Get or create a breed alias for the product"""
        # Clean the product name
        clean_name = self._clean_breed_name(product_name)

        # Check if alias already exists
        existing = self.client.table('breed_aliases').select('id').eq(
            'hatchery_id', self.hatchery_id
        ).eq('hatchery_breed_name', product_name).execute()

        if existing.data:
            return existing.data[0]['id']

        # Try to find a matching breed
        breed_id = self._find_matching_breed(clean_name)

        # Create new breed alias
        new_alias = {
            'hatchery_id': self.hatchery_id,
            'hatchery_breed_name': product_name,
            'breed_id': breed_id,
            'mapping_method': 'pattern-match' if breed_id else 'unmatched',
            'mapping_confidence': 0.8 if breed_id else 0.0,
            'mapping_notes': f"Auto-matched from Cackle scraper for: {clean_name}"
        }

        result = self.client.table('breed_aliases').upsert(
            new_alias,
            on_conflict='hatchery_id,hatchery_breed_name'
        ).execute()
        return result.data[0]['id']

    def _clean_breed_name(self, name: str) -> str:
        """Clean breed name for matching"""
        # Remove common suffixes
        suffixes = ['Chicken', 'Chickens', 'Chicks', 'Bantam']
        for suffix in suffixes:
            name = name.replace(suffix, '')

        # Remove extra whitespace
        return ' '.join(name.split()).strip()

    def _find_matching_breed(self, clean_name: str) -> Optional[str]:
        """Try to find a matching breed in the breeds table"""
        # Try exact match
        result = self.client.table('breeds').select('id').eq(
            'standard_name', clean_name
        ).execute()

        if result.data:
            return result.data[0]['id']

        # Try case-insensitive match
        result = self.client.table('breeds').select('id').ilike(
            'standard_name', clean_name
        ).execute()

        if result.data:
            return result.data[0]['id']

        # Try partial match
        words = clean_name.lower().split()
        if len(words) >= 2:
            partial_name = ' '.join(words[:2])
            result = self.client.table('breeds').select('id').ilike(
                'standard_name', f'%{partial_name}%'
            ).execute()

            if result.data and len(result.data) == 1:
                return result.data[0]['id']

        return None

    def _upload_pricing_tiers(self, product_id: str, pricing_data: Dict[str, List[Dict]]):
        """Upload pricing tiers for all genders"""
        for gender, tiers in pricing_data.items():
            for tier in tiers:
                # Parse the quantity range
                quantity_min, quantity_max = self._parse_quantity_range(tier['size'])

                # Parse the price
                price_value = self._parse_price(tier['price'])

                tier_data = {
                    'cackle_product_id': product_id,
                    'gender': gender,
                    'quantity_min': quantity_min,
                    'quantity_max': quantity_max,
                    'quantity_range': tier['size'],
                    'price': price_value,
                    'price_string': tier['price']
                }

                self.client.table('cackle_pricing_tiers').upsert(
                    tier_data,
                    on_conflict='cackle_product_id,gender,quantity_range'
                ).execute()

    def _parse_quantity_range(self, range_str: str) -> Tuple[int, Optional[int]]:
        """
        Parse quantity range string like "1-4" or "100+"

        Returns:
            Tuple of (min, max) where max is None for "100+"
        """
        if range_str.endswith('+'):
            # Handle "100+"
            min_qty = int(range_str[:-1])
            return (min_qty, None)
        elif '-' in range_str:
            # Handle "1-4"
            parts = range_str.split('-')
            return (int(parts[0]), int(parts[1]))
        else:
            # Single number
            qty = int(range_str)
            return (qty, qty)

    def _parse_price(self, price_str: str) -> float:
        """Parse price string like "$4.28" to float"""
        # Remove dollar sign and any whitespace
        cleaned = price_str.replace('$', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return 0.0

    def _upload_availability(self, product_id: str, availability_data: List[Dict]):
        """Upload availability calendar data"""
        for entry in availability_data:
            avail_data = {
                'cackle_product_id': product_id,
                'available_date': entry['date'],
                'status': entry['status'],
                'last_checked_at': datetime.utcnow().isoformat()
            }

            self.client.table('cackle_availability').upsert(
                avail_data,
                on_conflict='cackle_product_id,available_date'
            ).execute()

    def batch_upload_products(self, products: List[Dict]) -> Dict:
        """
        Upload multiple products in batch.

        Args:
            products: List of product dictionaries

        Returns:
            Dictionary with upload statistics
        """
        stats = {
            'total': len(products),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        for product in products:
            try:
                self.upload_product(product)
                stats['successful'] += 1
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'product': product.get('name', 'Unknown'),
                    'error': str(e)
                })
                logger.error(f"Failed to upload {product.get('name', 'Unknown')}: {str(e)}")

        logger.info(f"Batch upload complete: {stats['successful']} successful, {stats['failed']} failed")
        return stats

    def update_product_availability(self, product_url: str, availability_data: List[Dict]):
        """
        Update only the availability for an existing product.

        Args:
            product_url: The product URL
            availability_data: List of availability entries
        """
        # Find the product
        result = self.client.table('cackle_products').select('id').eq(
            'product_url', product_url
        ).single().execute()

        if not result.data:
            raise ValueError(f"Product not found: {product_url}")

        product_id = result.data['id']

        # Update availability
        self._upload_availability(product_id, availability_data)

        logger.info(f"Updated availability for: {product_url}")


# Convenience function
def upload_cackle_data_to_supabase(product_data: Dict):
    """
    Convenience function to upload Cackle data to Supabase.

    Args:
        product_data: Dictionary containing the scraped Cackle product data
    """
    uploader = CackleSupabaseUploader()
    return uploader.upload_product(product_data)