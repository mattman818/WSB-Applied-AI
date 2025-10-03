"""Utility for scraping product information from https://failure.museum/.

The site is powered by Shopify, which exposes a JSON endpoint at
``/products.json`` that returns paginated product information.

This script fetches all pages from that endpoint and writes a normalized list
of products to either stdout (as JSON) or a specified file.  It also includes a
simple retry mechanism and descriptive logging so that network failures—such as
those encountered in restricted environments—are reported clearly.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from typing import Iterable, List, Optional

import requests
from requests import Response


logger = logging.getLogger(__name__)


SHOPIFY_PRODUCTS_ENDPOINT = "/products.json"
DEFAULT_PAGE_SIZE = 250
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


@dataclass
class Product:
    """Normalized representation of a Shopify product."""

    id: int
    handle: str
    title: str
    vendor: str
    product_type: str
    tags: List[str]
    status: str
    variants: List[dict]
    images: List[dict]
    options: List[dict]

    @classmethod
    def from_shopify_payload(cls, payload: dict) -> "Product":
        """Create a :class:`Product` from the raw Shopify JSON payload."""

        return cls(
            id=payload["id"],
            handle=payload.get("handle", ""),
            title=payload.get("title", ""),
            vendor=payload.get("vendor", ""),
            product_type=payload.get("product_type", ""),
            tags=[tag for tag in payload.get("tags", "").split(",") if tag],
            status=payload.get("status", ""),
            variants=payload.get("variants", []),
            images=payload.get("images", []),
            options=payload.get("options", []),
        )


class FailureMuseumScraper:
    """Scrape product data from failure.museum via the Shopify JSON API."""

    def __init__(self, base_url: str = "https://failure.museum", session: Optional[requests.Session] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.session.headers.setdefault("Accept", "application/json")

    def _request(self, endpoint: str, **params) -> Response:
        """Perform an HTTP GET request with retries."""

        url = f"{self.base_url}{endpoint}"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:  # pragma: no cover - network failure path
                logger.warning("Attempt %s failed for %s: %s", attempt, url, exc)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)
        raise RuntimeError("Unreachable code in _request")  # pragma: no cover

    def iter_products(self, page_size: int = DEFAULT_PAGE_SIZE) -> Iterable[Product]:
        """Yield all products available from the Shopify endpoint."""

        page = 1
        while True:
            response = self._request(SHOPIFY_PRODUCTS_ENDPOINT, limit=page_size, page=page)
            payload = response.json()
            products = payload.get("products", [])
            if not products:
                break

            logger.debug("Fetched %s products from page %s", len(products), page)
            for product_payload in products:
                yield Product.from_shopify_payload(product_payload)

            page += 1

    def scrape(self, page_size: int = DEFAULT_PAGE_SIZE) -> List[Product]:
        """Return all products as a list."""

        return list(self.iter_products(page_size=page_size))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape all products from failure.museum")
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="Number of products to request per page (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="-",
        help="Path to write JSON output (default: stdout)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with indentation",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: %(default)s)",
    )
    return parser.parse_args(argv)


def configure_logging(log_level: str) -> None:
    logging.basicConfig(level=getattr(logging, log_level), format="%(levelname)s: %(message)s")


def dump_products(products: Iterable[Product], output_path: str, pretty: bool) -> None:
    data = [asdict(product) for product in products]
    if output_path == "-":
        json.dump(data, sys.stdout, indent=2 if pretty else None)
        if pretty:
            sys.stdout.write("\n")
        return

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2 if pretty else None)
        fh.write("\n")



def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    scraper = FailureMuseumScraper()
    try:
        products = scraper.scrape(page_size=args.page_size)
    except requests.RequestException as exc:
        logger.error("Failed to retrieve products: %s", exc)
        return 1

    dump_products(products, args.output, args.pretty)
    logger.info("Scraped %s products", len(products))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
