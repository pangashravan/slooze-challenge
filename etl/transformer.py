"""
transformer.py — ETL Step 2: Transform & Persist

Responsibilities:
  - Apply final schema ordering
  - Export clean DataFrame to CSV (for EDA + submission)
  - Export summary stats JSON
"""

import json
import logging
import os
from datetime import datetime

import pandas as pd

from scraper.config import PROCESSED_DATA_DIR

logger = logging.getLogger("ETL.Transformer")

# Final column order — controls what goes into the CSV
SCHEMA = [
    "product_name",
    "category",
    "price_min_inr",
    "price_max_inr",
    "price_mid_inr",
    "price_unit",
    "min_order_qty",
    "supplier_name",
    "supplier_city",
    "supplier_state",
    "supplier_rating",
    "has_price",
    "has_location",
    "has_supplier",
    "product_url",
    "source",
    "scraped_at",
]


def transform_and_save(df: pd.DataFrame) -> str:
    """
    Reorder columns to final schema, then write CSV.
    Returns the output file path.
    """
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    if df.empty:
        logger.warning("Empty DataFrame — nothing to save.")
        return ""

    # Keep only schema columns that exist; preserve extras at end
    ordered_cols = [c for c in SCHEMA if c in df.columns]
    extra_cols   = [c for c in df.columns if c not in SCHEMA]
    df = df[ordered_cols + extra_cols]

    # Filename includes run timestamp for traceability
    run_ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(PROCESSED_DATA_DIR, f"products_{run_ts}.csv")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved processed CSV → {csv_path}  ({len(df)} rows × {len(df.columns)} cols)")

    # Also save a static name for easy reference in EDA
    static_path = os.path.join(PROCESSED_DATA_DIR, "products_latest.csv")
    df.to_csv(static_path, index=False, encoding="utf-8-sig")

    _save_summary(df, run_ts)

    return csv_path


def _save_summary(df: pd.DataFrame, run_ts: str):
    """Write a quick metadata JSON alongside the CSV."""
    summary = {
        "run_timestamp":   run_ts,
        "total_records":   int(len(df)),
        "categories":      df["category"].value_counts().to_dict() if "category" in df.columns else {},
        "price_coverage":  f"{df['has_price'].mean() * 100:.1f}%" if "has_price" in df.columns else "N/A",
        "location_coverage": f"{df['has_location'].mean() * 100:.1f}%" if "has_location" in df.columns else "N/A",
        "unique_suppliers": int(df["supplier_name"].nunique()) if "supplier_name" in df.columns else 0,
        "states_covered":  df["supplier_state"].dropna().unique().tolist() if "supplier_state" in df.columns else [],
    }

    summary_path = os.path.join(PROCESSED_DATA_DIR, f"summary_{run_ts}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Summary saved → {summary_path}")
