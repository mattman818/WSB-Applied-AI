# Failure Museum product scraper

This repository does not ship the scraped data directly because outbound
requests from the execution environment consistently receive HTTP 403 responses
from `failure.museum`.  To reproduce the scraping locally:

1. Ensure Python 3.9+ is installed.
2. Install dependencies: `pip install requests` (BeautifulSoup is not required
   because the Shopify JSON endpoint is used).
3. Run the scraper:

   ```bash
   python failure_museum_scraper.py --pretty --output products.json
   ```

The script retrieves every page from `https://failure.museum/products.json` with
`limit=250` items per request and writes normalized product dictionaries to the
specified output file.  Logging is enabled by default so that HTTP or network
errors (such as a 403 response) are reported clearly.
