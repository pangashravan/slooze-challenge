"""
base_scraper.py — Abstract base class for all scrapers.

Responsibilities:
  - Session management (connection reuse)
  - User-agent rotation
  - Exponential back-off retry logic
  - Polite rate limiting (random delay between requests)
  - Centralised error logging

Child classes only implement `parse_page()`.
"""

import time
import random
import logging
from abc import ABC, abstractmethod

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.config import (
    USER_AGENTS, BASE_HEADERS,
    MIN_DELAY_SECONDS, MAX_DELAY_SECONDS,
    MAX_RETRIES, BACKOFF_FACTOR, REQUEST_TIMEOUT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


class BaseScraper(ABC):
    """
    All site-specific scrapers inherit from here.
    Provides: fetch(), polite_sleep(), and a pre-configured requests.Session.
    """

    def __init__(self, name: str = "BaseScraper"):
        self.name   = name
        self.logger = logging.getLogger(name)
        self.session = self._build_session()

    # ── Session setup ──────────────────────────────────────────────────────────
    def _build_session(self) -> requests.Session:
        """
        Build a requests.Session with:
          - Connection pooling (keep-alive)
          - Automatic retry on connection errors / 5xx responses
        """
        session = requests.Session()

        retry_strategy = Retry(
            total              = MAX_RETRIES,
            backoff_factor     = BACKOFF_FACTOR,
            status_forcelist   = [429, 500, 502, 503, 504],
            allowed_methods    = ["GET", "HEAD"],
            raise_on_status    = False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://",  adapter)

        return session

    # ── User-agent rotation ────────────────────────────────────────────────────
    def _random_headers(self) -> dict:
        """Pick a random user-agent and merge with base headers."""
        headers = BASE_HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers

    # ── Polite delay ───────────────────────────────────────────────────────────
    def polite_sleep(self):
        """
        Wait a random amount between MIN and MAX delay.
        Random jitter is crucial — fixed delays are trivially fingerprinted.
        """
        delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        self.logger.debug(f"Sleeping {delay:.2f}s …")
        time.sleep(delay)

    # ── HTTP fetch ─────────────────────────────────────────────────────────────
    def fetch(self, url: str) -> requests.Response | None:
        """
        GET a URL with rotating headers.
        Returns the response object, or None if all retries failed.
        """
        self.logger.info(f"Fetching: {url}")
        try:
            response = self.session.get(
                url,
                headers = self._random_headers(),
                timeout = REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                self.logger.warning("Rate limited (429) — sleeping 30s before retry")
                time.sleep(30)
                return self.fetch(url)   # one manual retry after long pause
            else:
                self.logger.warning(f"HTTP {response.status_code} for {url}")
                return None
        except requests.exceptions.RequestException as exc:
            self.logger.error(f"Request failed: {exc}")
            return None

    # ── Abstract interface ─────────────────────────────────────────────────────
    @abstractmethod
    def parse_page(self, html: str, category: str) -> list[dict]:
        """
        Parse raw HTML and return a list of product dicts.
        Each child class implements this for its target site.
        """
        raise NotImplementedError

    @abstractmethod
    def scrape_category(self, category: str, url: str) -> list[dict]:
        """Paginate through a category and collect all products."""
        raise NotImplementedError
