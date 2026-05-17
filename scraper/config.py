"""
config.py — Centralised configuration for the IndiaMART scraper.
All magic numbers and environment-sensitive values live here.
"""

import os

# ── Target categories ──────────────────────────────────────────────────────────
CATEGORIES = {
    "electronics":           "https://www.indiamart.com/search.mp?ss=electronic+components",
    "industrial_machinery":  "https://www.indiamart.com/search.mp?ss=industrial+machinery",
    "textiles":              "https://www.indiamart.com/search.mp?ss=textile+fabric",
    "agriculture_equipment": "https://www.indiamart.com/search.mp?ss=agriculture+equipment",
    "chemicals":             "https://www.indiamart.com/search.mp?ss=industrial+chemicals",
}

# Max pages to scrape per category (keep low for respectful crawling)
MAX_PAGES_PER_CATEGORY = int(os.getenv("MAX_PAGES", 3))

# ── Rate limiting ──────────────────────────────────────────────────────────────
MIN_DELAY_SECONDS = 2.0   # minimum wait between requests
MAX_DELAY_SECONDS = 5.0   # maximum wait between requests (random jitter)
MAX_RETRIES       = 3
BACKOFF_FACTOR    = 2     # exponential: 2s, 4s, 8s

# ── HTTP Headers pool ──────────────────────────────────────────────────────────
# Rotate these to avoid trivial bot fingerprinting
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",

    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",

    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

BASE_HEADERS = {
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "DNT":             "1",
}

# ── Output paths ───────────────────────────────────────────────────────────────
RAW_DATA_DIR       = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# ── Timeout ────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15  # seconds
