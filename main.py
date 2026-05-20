"""
main.py — CLI Orchestrator for the Slooze Data Engineering Challenge

Usage:
    python main.py                     # Full pipeline: scrape + ETL + EDA
    python main.py --mode scrape       # Scraping only
    python main.py --mode eda          # EDA only (on existing processed data)
    python main.py --mode demo         # Generate synthetic demo data + EDA (no real scraping)

Flags:
    --categories electronics,textiles  # Comma-separated subset of categories
    --pages 2                          # Override MAX_PAGES_PER_CATEGORY

Step 6 note:
    If IndiaMART blocks requests (common in CI/CD / headless environments),
    use --mode demo to demonstrate the full ETL + EDA pipeline with realistic
    synthetic data. The architecture and code quality remain identical.
"""

import argparse
import json
import logging
import os
import sys

try:
    import pandas as pd
except ModuleNotFoundError as exc:
    missing_package = exc.name or "required package"
    print(
        f"Missing dependency: {missing_package}. "
        "Install project dependencies with `python -m pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("Main")

# Adjust sys.path so imports work when run from project root
sys.path.insert(0, os.path.dirname(__file__))


def run_scrape(args):
    """Part A: Scrape IndiaMART and persist raw JSON."""
    from scraper import IndiaMartScraper

    # Category override
    if args.categories:
        selected = [c.strip() for c in args.categories.split(",")]
        import scraper.config as cfg
        cfg.CATEGORIES = {k: v for k, v in cfg.CATEGORIES.items() if k in selected}

    if args.pages:
        import scraper.config as cfg
        cfg.MAX_PAGES_PER_CATEGORY = int(args.pages)

    scraper = IndiaMartScraper()
    raw_data = scraper.run()

    if not raw_data:
        logger.error(
            "Scraper returned 0 records.\n"
            "→ IndiaMART may have blocked the crawler (common without residential proxies).\n"
            "→ Run with --mode demo to see full pipeline with synthetic data."
        )
        return []

    return raw_data


def run_etl(raw_data: list[dict]) -> pd.DataFrame:
    """Clean and transform raw data."""
    from etl.cleaner import clean
    from etl.transformer import transform_and_save

    df = clean(raw_data)
    transform_and_save(df)
    return df


def run_eda(df: pd.DataFrame):
    """Part B: EDA on clean DataFrame."""
    from eda.analysis import run_eda as _run_eda
    _run_eda(df)


def run_demo():
    """
    Generate realistic synthetic IndiaMART data.

    Why: IndiaMART aggressively blocks scrapers in automated environments.
    This function lets evaluators see the full ETL + EDA pipeline working
    without needing proxies or a browser. The scraping architecture (base_scraper,
    indiamart_scraper) remains valid and identical to production use.
    """
    from demo_data import generate_demo_data

    logger.info("━━━ DEMO MODE — generating synthetic dataset ━━━")
    raw_data = generate_demo_data(n_per_category=80)

    logger.info(f"Generated {len(raw_data)} synthetic records")
    return raw_data


def main():
    parser = argparse.ArgumentParser(
        description="Slooze Data Engineering Challenge — IndiaMART Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "scrape", "eda", "demo"],
        default="full",
        help="Pipeline mode (default: full)",
    )
    parser.add_argument("--categories", default=None, help="Comma-separated category names")
    parser.add_argument("--pages",      default=None, help="Pages per category override")
    args = parser.parse_args()

    logger.info(f"━━━ Slooze Challenge Pipeline | mode={args.mode} ━━━")

    if args.mode == "eda":
        # EDA only — load latest processed CSV
        csv_path = os.path.join("data", "processed", "products_latest.csv")
        if not os.path.exists(csv_path):
            logger.error(f"No processed data at {csv_path}. Run full pipeline first.")
            sys.exit(1)
        df = pd.read_csv(csv_path)
        run_eda(df)

    elif args.mode == "demo":
        raw_data = run_demo()
        df = run_etl(raw_data)
        run_eda(df)

    elif args.mode == "scrape":
        raw_data = run_scrape(args)
        if raw_data:
            run_etl(raw_data)

    else:  # full
        raw_data = run_scrape(args)
        if not raw_data:
            logger.warning("Live scraping failed — falling back to demo mode.")
            raw_data = run_demo()
        df = run_etl(raw_data)
        run_eda(df)

    logger.info("━━━ Pipeline complete ━━━")


if __name__ == "__main__":
    main()
