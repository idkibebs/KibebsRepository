"""
Shopify Admin REST API client.
Handles authentication, rate-limiting, pagination, and retries.
"""
import time
import logging
import requests
from typing import Generator

from config.settings import (
    SHOPIFY_STORE_URL,
    SHOPIFY_ACCESS_TOKEN,
    SHOPIFY_API_VERSION,
    API_RATE_LIMIT_SLEEP,
    MAX_RETRIES,
    RETRY_BACKOFF,
)

logger = logging.getLogger(__name__)


class ShopifyClient:
    """Thin wrapper around the Shopify Admin REST API."""

    def __init__(self):
        if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
            raise ValueError(
                "SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set in .env"
            )
        self.base_url = (
            f"https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
                "Content-Type": "application/json",
            }
        )

    # ── Core request ─────────────────────────────────────────────────────────

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        GET a single page from the API with retry + back-off.
        endpoint: e.g. '/products.json'
        """
        url = self.base_url + endpoint
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 2))
                    logger.warning("Rate-limited. Sleeping %.1fs", retry_after)
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                time.sleep(API_RATE_LIMIT_SLEEP)
                return resp.json()
            except requests.RequestException as exc:
                wait = RETRY_BACKOFF ** attempt
                logger.warning("Request failed (attempt %d/%d): %s. Retrying in %ds",
                               attempt, MAX_RETRIES, exc, wait)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(wait)

    # ── Cursor-based pagination ───────────────────────────────────────────────

    def paginate(
        self, endpoint: str, resource_key: str, params: dict = None
    ) -> Generator[list, None, None]:
        """
        Yield pages of results using Shopify cursor-based pagination.
        resource_key: top-level JSON key to extract (e.g. 'products')
        """
        params = {**(params or {}), "limit": 250}
        url = self.base_url + endpoint

        while url:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    resp = self.session.get(url, params=params, timeout=30)
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", 2))
                        logger.warning("Rate-limited. Sleeping %.1fs", retry_after)
                        time.sleep(retry_after)
                        continue
                    resp.raise_for_status()
                    break
                except requests.RequestException as exc:
                    wait = RETRY_BACKOFF ** attempt
                    logger.warning("Paginate failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
                    if attempt == MAX_RETRIES:
                        raise
                    time.sleep(wait)

            data = resp.json()
            page = data.get(resource_key, [])
            if page:
                yield page

            # Parse Link header for next cursor
            link_header = resp.headers.get("Link", "")
            url = _parse_next_link(link_header)
            params = {}   # cursor URL already contains all params
            time.sleep(API_RATE_LIMIT_SLEEP)

    # ── Convenience endpoints ─────────────────────────────────────────────────

    def get_locations(self) -> list:
        data = self.get("/locations.json")
        return data.get("locations", [])

    def get_inventory_levels(self, location_id: str, params: dict = None) -> Generator:
        p = {"location_ids": location_id, **(params or {})}
        return self.paginate("/inventory_levels.json", "inventory_levels", params=p)

    def get_products(self, params: dict = None) -> Generator:
        return self.paginate("/products.json", "products", params=params)

    def get_orders(self, params: dict = None) -> Generator:
        p = {"status": "any", **(params or {})}
        return self.paginate("/orders.json", "orders", params=p)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_next_link(link_header: str) -> str | None:
    """Extract the 'next' URL from a Shopify Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url_part = part.split(";")[0].strip()
            return url_part.strip("<>")
    return None
