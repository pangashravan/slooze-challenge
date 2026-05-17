"""
analysis.py — Exploratory Data Analysis

Responsibilities:
  - Summary statistics per category
  - Price distribution analysis
  - Supplier geography heatmap
  - Keyword frequency from product names
  - Missing data visualisation
  - Anomaly detection (price outliers)
  - Export all charts to data/processed/charts/

Run standalone:  python -m eda.analysis
Or import:       from eda.analysis import run_eda
"""

import logging
import os
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from wordcloud import WordCloud

logger = logging.getLogger("EDA")

# ── Style ──────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
CHARTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "charts"
)
COLORS = sns.color_palette("muted", 10)


def _save(fig, name: str):
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = os.path.join(CHARTS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Chart saved → {path}")


# ── 1. Dataset Overview ────────────────────────────────────────────────────────

def plot_category_distribution(df: pd.DataFrame):
    """Bar chart: number of products per category."""
    counts = df["category"].value_counts().reset_index()
    counts.columns = ["category", "count"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=counts, x="category", y="count", hue="category", ax=ax, palette="muted", legend=False)
    ax.set_title("Products per Category", fontsize=14, fontweight="bold")
    ax.set_xlabel("Category")
    ax.set_ylabel("Product Count")
    ax.tick_params(axis="x", rotation=25)

    for bar in ax.patches:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            int(bar.get_height()),
            ha="center", va="bottom", fontsize=10
        )

    _save(fig, "01_category_distribution.png")


# ── 2. Price Analysis ──────────────────────────────────────────────────────────

def plot_price_distribution(df: pd.DataFrame):
    """Box plots of mid-price by category (log scale for wide range)."""
    price_df = df[df["price_mid_inr"].notna() & (df["price_mid_inr"] > 0)].copy()

    if price_df.empty:
        logger.warning("No price data available for price distribution plot.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Raw scale
    sns.boxplot(data=price_df, x="category", y="price_mid_inr",
                ax=axes[0], palette="pastel", showfliers=False)
    axes[0].set_title("Price Distribution by Category (Linear)")
    axes[0].set_xlabel("Category")
    axes[0].set_ylabel("Price (₹)")
    axes[0].tick_params(axis="x", rotation=30)

    # Log scale (better for B2B where prices span orders of magnitude)
    price_df["log_price"] = np.log10(price_df["price_mid_inr"])
    sns.violinplot(data=price_df, x="category", y="log_price",
                   ax=axes[1], palette="pastel", inner="quartile")
    axes[1].set_title("Price Distribution (Log₁₀ Scale)")
    axes[1].set_xlabel("Category")
    axes[1].set_ylabel("log₁₀(Price ₹)")
    axes[1].tick_params(axis="x", rotation=30)

    fig.suptitle("Price Analysis Across Categories", fontsize=15, fontweight="bold")
    plt.tight_layout()
    _save(fig, "02_price_distribution.png")


def plot_price_tier_breakdown(df: pd.DataFrame):
    """Stacked bar: price tier (budget / mid / premium) per category."""
    price_df = df[df["price_mid_inr"].notna()].copy()
    if price_df.empty:
        return

    def tier(p):
        if p < 500:    return "Budget (<₹500)"
        if p < 5000:   return "Mid (₹500–5k)"
        if p < 50000:  return "Premium (₹5k–50k)"
        return "Enterprise (>₹50k)"

    price_df["tier"] = price_df["price_mid_inr"].apply(tier)

    pivot = price_df.groupby(["category", "tier"]).size().unstack(fill_value=0)
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(11, 6))
    pivot_pct.plot(kind="bar", stacked=True, ax=ax, colormap="Set2")
    ax.set_title("Price Tier Distribution by Category (%)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Percentage of Listings (%)")
    ax.set_xlabel("Category")
    ax.tick_params(axis="x", rotation=30)
    ax.legend(title="Price Tier", bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.tight_layout()
    _save(fig, "03_price_tier_breakdown.png")


# ── 3. Supplier Geography ──────────────────────────────────────────────────────

def plot_supplier_geography(df: pd.DataFrame):
    """Horizontal bar: top 15 states by supplier count."""
    if "supplier_state" not in df.columns:
        return

    state_counts = (
        df[df["supplier_state"].notna()]["supplier_state"]
        .value_counts()
        .head(15)
        .reset_index()
    )
    state_counts.columns = ["state", "count"]

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(data=state_counts, x="count", y="state", hue="state", ax=ax, palette="Blues_r", legend=False)
    ax.set_title("Top 15 Supplier States", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of Listings")
    ax.set_ylabel("State")
    _save(fig, "04_supplier_geography.png")


def plot_city_heatmap(df: pd.DataFrame):
    """Top cities per category — heatmap style."""
    if "supplier_city" not in df.columns:
        return

    top_cities = df["supplier_city"].value_counts().head(10).index.tolist()
    city_df = df[df["supplier_city"].isin(top_cities)]

    pivot = city_df.groupby(["supplier_city", "category"]).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="YlOrRd",
                linewidths=0.5, ax=ax)
    ax.set_title("Product Listings Heatmap: Top Cities × Categories",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    _save(fig, "05_city_category_heatmap.png")


# ── 4. Keyword / Product Name Analysis ────────────────────────────────────────

def plot_keyword_wordcloud(df: pd.DataFrame):
    """Word cloud of product names — reveals common B2B terminology."""
    if "product_name" not in df.columns:
        return

    STOPWORDS = {
        "and", "or", "for", "the", "with", "of", "in",
        "a", "an", "to", "is", "are", "at", "by",
    }

    all_words = []
    for name in df["product_name"].dropna():
        tokens = re.findall(r"[a-zA-Z]{3,}", name.lower())
        all_words.extend([t for t in tokens if t not in STOPWORDS])

    if not all_words:
        return

    word_freq = Counter(all_words)

    wc = WordCloud(
        width=900, height=450,
        background_color="white",
        colormap="plasma",
        max_words=120,
    ).generate_from_frequencies(word_freq)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Most Frequent Product Keywords", fontsize=14, fontweight="bold")
    _save(fig, "06_keyword_wordcloud.png")


def plot_top_keywords_bar(df: pd.DataFrame):
    """Top 20 keywords by frequency — bar chart (more precise than word cloud)."""
    if "product_name" not in df.columns:
        return

    STOPWORDS = {
        "and", "or", "for", "the", "with", "of", "in",
        "a", "an", "to", "is", "are", "at", "by", "type",
        "grade", "size", "model", "new", "used", "per",
    }

    words = []
    for name in df["product_name"].dropna():
        tokens = re.findall(r"[a-zA-Z]{4,}", name.lower())
        words.extend([t for t in tokens if t not in STOPWORDS])

    top20 = Counter(words).most_common(20)
    kw_df = pd.DataFrame(top20, columns=["keyword", "count"])

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(data=kw_df, x="count", y="keyword", hue="keyword", ax=ax, palette="rocket_r", legend=False)
    ax.set_title("Top 20 Product Keywords", fontsize=14, fontweight="bold")
    ax.set_xlabel("Frequency")
    _save(fig, "07_top_keywords.png")


# ── 5. Data Quality ────────────────────────────────────────────────────────────

def plot_missing_data(df: pd.DataFrame):
    """Horizontal bar showing % missing for each column."""
    miss_pct = (df.isna().mean() * 100).sort_values(ascending=True)
    miss_pct = miss_pct[miss_pct > 0]   # only columns with missing data

    if miss_pct.empty:
        logger.info("No missing data — skipping missing-data chart.")
        return

    fig, ax = plt.subplots(figsize=(9, max(4, len(miss_pct) * 0.5)))
    miss_pct.plot(kind="barh", ax=ax, color="salmon", edgecolor="white")
    ax.set_xlim(0, 100)
    ax.set_xlabel("% Missing Values")
    ax.set_title("Data Completeness Issues", fontsize=14, fontweight="bold")
    ax.axvline(50, color="red", linestyle="--", linewidth=1, alpha=0.6, label="50% threshold")
    ax.legend()
    plt.tight_layout()
    _save(fig, "08_missing_data.png")


# ── 6. Outlier / Anomaly Detection ────────────────────────────────────────────

def plot_price_outliers(df: pd.DataFrame):
    """
    IQR-based outlier detection per category.
    Flags listings where price is > 3× the 75th percentile.
    """
    price_df = df[df["price_mid_inr"].notna() & (df["price_mid_inr"] > 0)].copy()
    if price_df.empty:
        return

    outlier_counts = {}
    for cat, grp in price_df.groupby("category"):
        q1, q3 = grp["price_mid_inr"].quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + 3 * iqr
        n_outliers = (grp["price_mid_inr"] > upper).sum()
        outlier_counts[cat] = int(n_outliers)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(outlier_counts.keys(), outlier_counts.values(), color="tomato")
    ax.set_title("Extreme Price Outliers per Category (IQR × 3 method)",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Number of Outlier Listings")
    ax.set_xlabel("Category")
    ax.tick_params(axis="x", rotation=25)
    plt.tight_layout()
    _save(fig, "09_price_outliers.png")


# ── 7. Summary Stats Table ─────────────────────────────────────────────────────

def generate_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-category summary:  count, price median/mean/std, supplier count, coverage %.
    """
    rows = []
    for cat, grp in df.groupby("category"):
        price = grp["price_mid_inr"].dropna()
        rows.append({
            "Category":         cat,
            "Total Listings":   len(grp),
            "Price Median ₹":   round(price.median(), 2) if len(price) else None,
            "Price Mean ₹":     round(price.mean(), 2)   if len(price) else None,
            "Price Std ₹":      round(price.std(), 2)    if len(price) else None,
            "Unique Suppliers": grp["supplier_name"].nunique(),
            "States Covered":   grp["supplier_state"].nunique(),
            "Price Coverage %": round(grp["has_price"].mean() * 100, 1) if "has_price" in grp else None,
        })

    summary = pd.DataFrame(rows).set_index("Category")
    logger.info("\n" + summary.to_string())
    return summary


# ── Main EDA runner ────────────────────────────────────────────────────────────

def run_eda(df: pd.DataFrame):
    """Execute all EDA steps and persist charts."""
    logger.info(f"Starting EDA on {len(df)} records across {df['category'].nunique()} categories")

    plot_category_distribution(df)
    plot_price_distribution(df)
    plot_price_tier_breakdown(df)
    plot_supplier_geography(df)
    plot_city_heatmap(df)
    plot_keyword_wordcloud(df)
    plot_top_keywords_bar(df)
    plot_missing_data(df)
    plot_price_outliers(df)

    summary = generate_summary_table(df)

    logger.info("EDA complete. Charts saved to data/processed/charts/")
    return summary


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import glob

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

    # Find latest processed CSV
    pattern = os.path.join(
        os.path.dirname(__file__), "..", "data", "processed", "products_latest.csv"
    )
    if not os.path.exists(pattern):
        logger.error("No processed data found. Run main.py first.")
        sys.exit(1)

    df = pd.read_csv(pattern)
    run_eda(df)
