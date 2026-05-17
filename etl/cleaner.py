"""
cleaner.py — ETL Step 1: Data Cleaning

Responsibilities:
  - Remove duplicate records
  - Handle missing / null values with appropriate strategies
  - Type cast fields to correct Python types
  - Normalise string casing and whitespace
  - Flag data quality issues

Input:  list[dict]  (raw scraped data)
Output: pd.DataFrame (clean, typed, deduplicated)
"""

import logging
import re

import pandas as pd
import numpy as np

logger = logging.getLogger("ETL.Cleaner")


# ── Field-level cleaning helpers ───────────────────────────────────────────────

def _clean_string(val) -> str | None:
    """Strip whitespace, collapse internal spaces, return None if empty."""
    if pd.isna(val) or val is None:
        return None
    s = re.sub(r"\s+", " ", str(val)).strip()
    return s if s else None


def _title_case(val) -> str | None:
    s = _clean_string(val)
    return s.title() if s else None


def _parse_numeric(val) -> float | None:
    """
    Try to extract a float from messy strings like '₹1,500', '500.0', etc.
    Returns None if conversion fails.
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        clean = re.sub(r"[^\d.]", "", str(val))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None


# ── Main cleaner ───────────────────────────────────────────────────────────────

def clean(raw_data: list[dict]) -> pd.DataFrame:
    """
    Full cleaning pipeline:
      1. Cast to DataFrame
      2. Deduplicate
      3. Clean strings
      4. Cast numeric columns
      5. Derive helper columns
      6. Report quality summary
    """
    if not raw_data:
        logger.warning("clean() received empty data — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.DataFrame(raw_data)
    logger.info(f"Raw records loaded: {len(df)}")

    # ── Step 1: Deduplication ──────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates(subset=["product_url"], keep="first")
    df = df.drop_duplicates(subset=["product_name", "supplier_name", "supplier_city"], keep="first")
    logger.info(f"Deduplication: {before} → {len(df)} records ({before - len(df)} removed)")

    # ── Step 2: String normalisation ───────────────────────────────────────────
    string_cols = ["product_name", "supplier_name", "category",
                   "price_unit", "min_order_qty", "supplier_rating"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].apply(_clean_string)

    # Title-case location fields
    for col in ["supplier_city", "supplier_state"]:
        if col in df.columns:
            df[col] = df[col].apply(_title_case)

    # ── Step 3: Numeric casting ────────────────────────────────────────────────
    for col in ["price_min_inr", "price_max_inr"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_numeric)

    # ── Step 4: Derived columns ────────────────────────────────────────────────
    # Mid-price for analysis where min==max is fine
    if "price_min_inr" in df.columns and "price_max_inr" in df.columns:
        df["price_mid_inr"] = (
            (df["price_min_inr"].fillna(df["price_max_inr"]) +
             df["price_max_inr"].fillna(df["price_min_inr"])) / 2
        )

    # Price range flag
    df["has_price"]     = df["price_mid_inr"].notna()
    df["has_location"]  = df["supplier_city"].notna()
    df["has_supplier"]  = df["supplier_name"].notna()

    # ── Step 5: Timestamp ──────────────────────────────────────────────────────
    if "scraped_at" in df.columns:
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")

    # ── Step 6: Quality report ─────────────────────────────────────────────────
    _log_quality_report(df)

    return df.reset_index(drop=True)


def _log_quality_report(df: pd.DataFrame):
    """Log completeness % for each column."""
    logger.info("── Data Quality Report ──────────────────────────")
    for col in df.columns:
        total    = len(df)
        missing  = df[col].isna().sum()
        complete = round((1 - missing / total) * 100, 1) if total else 0
        logger.info(f"  {col:<25} {complete:>5.1f}% complete  ({missing} nulls)")
    logger.info("────────────────────────────────────────────────")
