"""Small runnable script to execute the EDA runner outside the notebook.

Usage:
    python scripts/run_eda.py [--csv PATH]
"""
from __future__ import annotations

import argparse
import logging
from eda import load_data, run_eda


def main():
    parser = argparse.ArgumentParser(description="Run EDA and export charts.")
    parser.add_argument("--csv", help="Path to CSV to analyse", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

    df = load_data(args.csv)
    summary = run_eda(df)
    print(summary)


if __name__ == "__main__":
    main()
