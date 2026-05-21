"""
indiamart_scraper.py — IndiaMART-specific scraper.

Responsibilities:
  - Build paginated URLs for each category
  - Parse product cards from search result HTML
  - Extract: name, price, supplier, location, MOQ, category, URL, timestamp
  - Save raw results as JSON

IndiaMART search page structure (as of 2024):
  - Product cards: <div class="card-body"> or similar wrappers
  - Pagination: &page=N query param
"""

import json
import os
import random
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper
from scraper.config import (
    CATEGORIES, MAX_PAGES_PER_CATEGORY, RAW_DATA_DIR,
)

PRICE_CLEAN_RE = re.compile(r"[\u20b9,]")
NUMBER_RE = re.compile(r"[\d]+(?:\.\d+)?")
UNIT_RE = re.compile(r"/\s*(.+)$")
CARD_SELECTORS = (
    "div.productcart",
    "div.product-unit",
    "div.srpPrdct",
    "li.product-list-item",
)
FIELD_SELECTORS = {
    "name": ("h2.pname", ".prd-name", "h3.pname", ".pname"),
    "price": (".price-unit", ".prc", ".price"),
    "supplier": (".companyname", ".sup-name", ".company-name"),
    "location": (".locationspan", ".lcname", ".location"),
    "moq": (".moqspan", ".punit", ".moq"),
    "rating": (".rating-count", ".rat-num"),
}


class IndiaMartScraper(BaseScraper):
    """
    Scrapes product listings from IndiaMART search results.

    Usage:
        scraper = IndiaMartScraper()
        products = scraper.run()   # scrapes all configured categories
    """

    SITE = "indiamart.com"

    def __init__(self):
        super().__init__(name="IndiaMartScraper")
        os.makedirs(RAW_DATA_DIR, exist_ok=True)

    # ── URL building ───────────────────────────────────────────────────────────
    def _paginate_url(self, base_url: str, page: int) -> str:
        """Append pagination query parameter."""
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}page={page}"

    # ── HTML Parsing ───────────────────────────────────────────────────────────
    def parse_page(self, html: str, category: str) -> list[dict]:
        """
        Parse one search-result page.

        IndiaMART renders product cards inside <div class="productcart">.
        Each card contains:
          - Product name  : h2.pname or .prd-name
          - Price         : .price-unit span elements
          - Supplier name : .companyname or .sup-name
          - Location      : .locationspan or .lcname  
          - MOQ           : .moqspan or .punit
          - Product URL   : <a> in card header
        """
        soup = BeautifulSoup(html, "html.parser")
        products = []
        timestamp = datetime.now(timezone.utc).isoformat()

        cards = []
        for selector in CARD_SELECTORS:
            cards = soup.select(selector)
            if cards:
                self.logger.info(f"Found {len(cards)} cards with selector '{selector}'")
                break

        if not cards:
            self.logger.warning("No product cards found — page structure may have changed.")
            return []

        for card in cards:
            try:
                product = self._extract_card(card, category, timestamp)
                if product and product.get("product_name"):
                    products.append(product)
            except Exception as exc:
                self.logger.debug(f"Card parse error (skipping): {exc}")
                continue

        self.logger.info(f"Parsed {len(products)} products from page (category={category})")
        return products

    @staticmethod
    def _first_match(card, selectors):
        for selector in selectors:
            found = card.select_one(selector)
            if found is not None:
                return found
        return None

    def _extract_card(self, card, category: str, timestamp: str) -> dict:
        """Extract all fields from a single product card."""

        # ── Product name ───────────────────────────────────────────────────────
        name_el = self._first_match(card, FIELD_SELECTORS["name"])
        product_name = name_el.get_text(strip=True) if name_el else None

        # ── Price ──────────────────────────────────────────────────────────────
        price_el = self._first_match(card, FIELD_SELECTORS["price"])
        raw_price = price_el.get_text(strip=True) if price_el else ""
        price_min, price_max, price_unit = self._parse_price(raw_price)

        # ── Supplier info ──────────────────────────────────────────────────────
        supplier_el = self._first_match(card, FIELD_SELECTORS["supplier"])
        supplier_name = supplier_el.get_text(strip=True) if supplier_el else None

        # ── Location ───────────────────────────────────────────────────────────
        location_el = self._first_match(card, FIELD_SELECTORS["location"])
        raw_location = location_el.get_text(strip=True) if location_el else ""
        city, state = self._parse_location(raw_location)

        # ── Minimum Order Quantity ─────────────────────────────────────────────
        moq_el = self._first_match(card, FIELD_SELECTORS["moq"])
        moq = moq_el.get_text(strip=True) if moq_el else None

        # ── Product URL ────────────────────────────────────────────────────────
        link_el = card.select_one("a[href]")
        product_url = link_el["href"] if link_el else None
        if product_url and not product_url.startswith("http"):
            product_url = f"https://www.indiamart.com{product_url}"

        # ── Rating ────────────────────────────────────────────────────────────
        rating_el = self._first_match(card, FIELD_SELECTORS["rating"])
        rating = rating_el.get_text(strip=True) if rating_el else None

        return {
            "product_name":    product_name,
            "category":        category,
            "price_raw":       raw_price,
            "price_min_inr":   price_min,
            "price_max_inr":   price_max,
            "price_unit":      price_unit,
            "supplier_name":   supplier_name,
            "supplier_city":   city,
            "supplier_state":  state,
            "min_order_qty":   moq,
            "supplier_rating": rating,
            "product_url":     product_url,
            "source":          self.SITE,
            "scraped_at":      timestamp,
        }

    # ── Price parser ───────────────────────────────────────────────────────────
    def _parse_price(self, raw: str):
        """
        IndiaMART price formats:
          "₹ 500 - 1,500 / Piece"
          "₹ 2,000 / Kg"
          "Get Latest Price"
          "Price on Request"
        Returns: (min_price, max_price, unit) as floats/None
        """
        if not raw or raw.strip() in ("Get Latest Price", "Price on Request", ""):
            return None, None, None

        # Remove ₹ and commas
        clean = PRICE_CLEAN_RE.sub("", raw)

        # Extract numbers
        numbers = NUMBER_RE.findall(clean)
        nums = [float(n) for n in numbers] if numbers else []

        # Extract unit (after last /)
        unit_match = UNIT_RE.search(raw.strip())
        unit = unit_match.group(1).strip() if unit_match else None

        if len(nums) == 0:
            return None, None, unit
        elif len(nums) == 1:
            return nums[0], nums[0], unit
        else:
            return min(nums[0], nums[1]), max(nums[0], nums[1]), unit

    # ── Location parser ────────────────────────────────────────────────────────
    def _parse_location(self, raw: str):
        """
        Formats: "Mumbai, Maharashtra"  /  "Delhi"  /  "Chennai - Tamil Nadu"
        Returns: (city, state)
        """
        if not raw:
            return None, None

        for sep in [",", " - ", "-"]:
            if sep in raw:
                parts = raw.split(sep, 1)
                return parts[0].strip(), parts[1].strip()

        return raw.strip(), None

    # ── Category scraper ───────────────────────────────────────────────────────
    def scrape_category(self, category: str, base_url: str) -> list[dict]:
        """Paginate through MAX_PAGES_PER_CATEGORY and collect all products."""
        all_products = []

        for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
            url = self._paginate_url(base_url, page)
            response = self.fetch(url)

            if response is None:
                self.logger.warning(f"Failed to fetch page {page} of '{category}' — stopping pagination")
                break

            page_products = self.parse_page(response.text, category)

            if not page_products:
                self.logger.info(f"No products on page {page} — end of results for '{category}'")
                break

            all_products.extend(page_products)
            self.logger.info(f"Category '{category}' | Page {page} | Total so far: {len(all_products)}")

            # Polite delay between pages
            if page < MAX_PAGES_PER_CATEGORY:
                self.polite_sleep()

        return all_products

    # ── Save raw data ──────────────────────────────────────────────────────────
    def _save_raw(self, category: str, products: list[dict]):
        """Save raw scraped list as JSON for reproducibility."""
        filename = os.path.join(RAW_DATA_DIR, f"{category}_raw.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved {len(products)} records → {filename}")

    # ── Main entry point ───────────────────────────────────────────────────────
    def run(self) -> list[dict]:
        """Scrape all configured categories. Returns combined product list."""
        all_data = []
        categories = tuple(CATEGORIES.items())
        last_category = categories[-1][0] if categories else None

        for category, url in categories:
            self.logger.info(f"━━━ Starting category: {category} ━━━")
            products = self.scrape_category(category, url)
            self._save_raw(category, products)
            all_data.extend(products)

            # Longer pause between categories
            if category != last_category:
                self.logger.info("Category done — waiting before next…")
                time_wait = 8 + random.uniform(0, 4)
                import time
                time.sleep(time_wait)

        self.logger.info(f"Scraping complete. Total records: {len(all_data)}")
        return all_data
