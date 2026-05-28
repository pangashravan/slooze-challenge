"""EDA package exports."""
from .analysis import run_eda  # re-export for convenience
from .data_loader import load_data

__all__ = ["run_eda", "load_data"]
