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

import numpy as np
import pandas as pd

logger = logging.getLogger("ETL.Cleaner")

SPACE_RE = re.compile(r"\s+")
NON_NUMERIC_RE = re.compile(r"[^\d.]")


# ── Field-level cleaning helpers ───────────────────────────────────────────────

def _clean_string(val) -> str | None:
    """Strip whitespace, collapse internal spaces, return None if empty."""
    if pd.isna(val) or val is None:
        return None
    s = SPACE_RE.sub(" ", str(val)).strip()
    return s if s else None


def _clean_string_series(series: pd.Series, *, title: bool = False) -> pd.Series:
    """Vectorized whitespace cleanup with empty strings normalized to NA."""
    cleaned = (
        series.astype("string")
        .str.replace(SPACE_RE, " ", regex=True)
        .str.strip()
        .replace("", pd.NA)
    )
    return cleaned.str.title() if title else cleaned


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
        clean = NON_NUMERIC_RE.sub("", str(val))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None


def _parse_numeric_series(series: pd.Series) -> pd.Series:
    """Parse numeric values with a fast vectorized path before regex cleanup."""
    numeric = pd.to_numeric(series, errors="coerce")
    missing = numeric.isna() & series.notna()
    if missing.any():
        numeric.loc[missing] = pd.to_numeric(
            series.loc[missing].astype("string").str.replace(NON_NUMERIC_RE, "", regex=True),
            errors="coerce",
        )
    return numeric


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
            df[col] = _clean_string_series(df[col])

    # Title-case location fields
    for col in ["supplier_city", "supplier_state"]:
        if col in df.columns:
            df[col] = _clean_string_series(df[col], title=True)

    # ── Step 3: Numeric casting ────────────────────────────────────────────────
    for col in ["price_min_inr", "price_max_inr"]:
        if col in df.columns:
            df[col] = _parse_numeric_series(df[col])

    # ── Step 4: Derived columns ────────────────────────────────────────────────
    # Mid-price for analysis where min==max is fine
    if "price_min_inr" in df.columns and "price_max_inr" in df.columns:
        df["price_mid_inr"] = (
            (df["price_min_inr"].fillna(df["price_max_inr"]) +
             df["price_max_inr"].fillna(df["price_min_inr"])) / 2
        )

    # Price range flag
    df["has_price"] = df.get("price_mid_inr", pd.Series(index=df.index)).notna()
    df["has_location"] = df.get("supplier_city", pd.Series(index=df.index)).notna()
    df["has_supplier"] = df.get("supplier_name", pd.Series(index=df.index)).notna()

    # ── Step 5: Timestamp ──────────────────────────────────────────────────────
    if "scraped_at" in df.columns:
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")

    # ── Step 6: Quality report ─────────────────────────────────────────────────
    _log_quality_report(df)

    return df.reset_index(drop=True)


def _log_quality_report(df: pd.DataFrame):
    """Log completeness % for each column."""
    logger.info("── Data Quality Report ──────────────────────────")
    total = len(df)
    missing_counts = df.isna().sum()
    for col, missing in missing_counts.items():
        complete = round((1 - missing / total) * 100, 1) if total else 0
        logger.info(f"  {col:<25} {complete:>5.1f}% complete  ({missing} nulls)")
    logger.info("────────────────────────────────────────────────")
