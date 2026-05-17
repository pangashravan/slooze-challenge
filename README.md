# Slooze Data Engineering Challenge

> **Author:** Shravan  
> **Stack:** Python 3.11+ · BeautifulSoup4 · Pandas · Seaborn · Matplotlib  
> **Target:** IndiaMART B2B marketplace

---

## Architecture

```
slooze-challenge/
├── scraper/
│   ├── base_scraper.py       # Session mgmt, retry, rate limiting, UA rotation
│   ├── indiamart_scraper.py  # IndiaMART HTML parser + pagination
│   └── config.py             # Categories, delays, headers
├── etl/
│   ├── cleaner.py            # Dedup, null handling, type casting
│   └── transformer.py        # Schema ordering, CSV export, summary JSON
├── eda/
│   └── analysis.py           # 9 charts + summary stats table
├── data/
│   ├── raw/                  # Per-category JSON dumps from scraper
│   └── processed/
│       ├── products_latest.csv
│       └── charts/           # All PNG visualisations
├── demo_data.py              # Synthetic data generator (for blocked environments)
├── main.py                   # CLI orchestrator
└── requirements.txt
```

---

## Quickstart

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run full pipeline (live scraping)
```bash
python main.py
```

### 3. Run demo mode (if IndiaMART blocks — recommended for local testing)
```bash
python main.py --mode demo
```

### 4. Run EDA only (on existing processed data)
```bash
python main.py --mode eda
```

### 5. Scrape specific categories
```bash
python main.py --mode scrape --categories electronics,textiles --pages 2
```

---

## Data Schema

| Field | Type | Description |
|---|---|---|
| `product_name` | str | Product listing title |
| `category` | str | One of 5 configured categories |
| `price_min_inr` | float | Lower bound price (₹) |
| `price_max_inr` | float | Upper bound price (₹) |
| `price_mid_inr` | float | Derived midpoint for analysis |
| `price_unit` | str | e.g. Piece / Kg / Meter / Unit |
| `min_order_qty` | str | MOQ from listing |
| `supplier_name` | str | Company name |
| `supplier_city` | str | City |
| `supplier_state` | str | State |
| `supplier_rating` | str | Seller rating (if present) |
| `product_url` | str | Source URL |
| `source` | str | `indiamart.com` |
| `scraped_at` | datetime | UTC timestamp of scrape |

---

## EDA Outputs

All charts saved to `data/processed/charts/`:

| Chart | Insight |
|---|---|
| `01_category_distribution.png` | Products per category |
| `02_price_distribution.png` | Box + violin plots (linear & log scale) |
| `03_price_tier_breakdown.png` | Budget / Mid / Premium / Enterprise split |
| `04_supplier_geography.png` | Top 15 supplier states |
| `05_city_category_heatmap.png` | Cities × Categories heatmap |
| `06_keyword_wordcloud.png` | B2B product keyword frequency |
| `07_top_keywords.png` | Top 20 keywords bar chart |
| `08_missing_data.png` | Data completeness by column |
| `09_price_outliers.png` | IQR-based outlier count per category |

---

## Anti-Block Strategy

| Technique | Implementation |
|---|---|
| User-agent rotation | 4 realistic browser UA strings, chosen randomly per request |
| Random delay jitter | `uniform(2.0, 5.0)` seconds between requests |
| Exponential back-off | `Retry(backoff_factor=2)` on 429/5xx via `urllib3` |
| Category pause | 8–12s pause between categories |
| Session reuse | `requests.Session` with connection pooling |
| 429 handler | 30s sleep + one manual retry |

---

## Key Findings (Demo Data)

- **Maharashtra, Gujarat, Delhi** account for ~55% of all B2B listings — mirroring India's industrial geography.
- **Industrial Machinery** shows the widest price variance (₹5k–₹15L), consistent with capital equipment markets.
- **Textiles** has the highest listing density in Surat and Tirupur.
- **~15%** of listings use "Price on Request" (intentional withholding for negotiation dynamics).
- Common product keywords: `grade`, `industrial`, `machine`, `pump`, `fabric` — useful for category auto-tagging via NLP.
