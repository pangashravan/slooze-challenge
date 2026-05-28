"""Data loading utilities for EDA.

Provides a `load_data()` function which prefers processed CSVs, falls back
to a local scraped CSV, and finally generates representative demo data.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd


def generate_demo_data(n: int = 300) -> pd.DataFrame:
    """Generate realistic IndiaMART-style demo data."""
    np.random.seed(42)
    categories = [
        "Industrial Machinery",
        "Electronic Components",
        "Textile & Fabric",
        "Chemical & Dyes",
        "Agricultural Products",
        "Packaging Materials",
        "Construction Materials",
        "Auto Parts",
    ]
    cities = [
        "Mumbai",
        "Delhi",
        "Surat",
        "Ahmedabad",
        "Chennai",
        "Hyderabad",
        "Pune",
        "Kolkata",
        "Bengaluru",
        "Jaipur",
    ]
    units = ["Per Piece", "Per Kg", "Per Meter", "Per Set", "Per Box", "Per Ton"]

    cat_weights = [0.20, 0.18, 0.15, 0.12, 0.10, 0.10, 0.08, 0.07]
    chosen_cats = np.random.choice(categories, n, p=cat_weights)

    base_prices = {
        "Industrial Machinery": (5000, 50000),
        "Electronic Components": (100, 5000),
        "Textile & Fabric": (50, 800),
        "Chemical & Dyes": (200, 3000),
        "Agricultural Products": (30, 500),
        "Packaging Materials": (20, 300),
        "Construction Materials": (500, 8000),
        "Auto Parts": (300, 6000),
    }

    prices, min_orders, ratings, review_counts = [], [], [], []
    for cat in chosen_cats:
        lo, hi = base_prices[cat]
        prices.append(round(np.random.uniform(lo, hi), 2))
        min_orders.append(np.random.choice([1, 5, 10, 25, 50, 100]))
        ratings.append(round(np.random.uniform(3.0, 5.0), 1))
        review_counts.append(np.random.randint(0, 500))

    suppliers = [f"Supplier_{i:03d}" for i in np.random.randint(1, 80, n)]

    df = pd.DataFrame(
        {
            "product_name": [f"{cat.split()[0]} Product {i+1}" for i, cat in enumerate(chosen_cats)],
            "category": chosen_cats,
            "price_inr": prices,
            "unit": np.random.choice(units, n),
            "min_order_qty": min_orders,
            "supplier_name": suppliers,
            "supplier_city": np.random.choice(cities, n),
            "rating": ratings,
            "review_count": review_counts,
            "is_verified_supplier": np.random.choice([True, False], n, p=[0.6, 0.4]),
        }
    )
    # Derive a mid-price column similar to analysis expectations
    df["price_mid_inr"] = df["price_inr"]
    df["has_price"] = True
    return df


def load_data(processed_path: str | None = None) -> pd.DataFrame:
    """Load product data preferring processed CSVs.

    Order of preference:
    - provided `processed_path`
    - data/processed/products_latest.csv
    - indiamart_products.csv (local scraped CSV)
    - generated demo data
    """
    candidates = []
    if processed_path:
        candidates.append(processed_path)
    candidates.append(os.path.join("data", "processed", "products_latest.csv"))
    candidates.append("indiamart_products.csv")

    for path in candidates:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                # ensure expected derived columns exist for EDA module
                if "price_mid_inr" not in df.columns and "price_inr" in df.columns:
                    df["price_mid_inr"] = df["price_inr"]
                if "has_price" not in df.columns:
                    df["has_price"] = df["price_mid_inr"].notna()
                return df
            except Exception:
                continue

    # Fallback: generate demo data
    return generate_demo_data(300)
