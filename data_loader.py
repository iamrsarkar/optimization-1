"""Utility functions to load and preprocess NexGen Logistics datasets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import streamlit as st

from config import CONFIG

LOGGER = logging.getLogger(__name__)


def _safe_read_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Read a CSV file and provide detailed logging on failure.

    Parameters
    ----------
    path: Path
        The CSV file path.
    **kwargs:
        Additional keyword arguments passed to :func:`pandas.read_csv`.

    Returns
    -------
    pd.DataFrame
        Loaded dataframe; returns an empty dataframe if file is missing.
    """

    try:
        df = pd.read_csv(path, **kwargs)
        LOGGER.info("Loaded %s with %d rows", path.name, len(df))
        return df
    except FileNotFoundError:
        LOGGER.error("Missing dataset: %%s", path)
        return pd.DataFrame()
    except Exception as exc:  # pragma: no cover - defensive programming
        LOGGER.exception("Error loading %s: %s", path, exc)
        return pd.DataFrame()


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dataframe column names to snake case."""

    df = df.copy()
    df.columns = [col.strip().replace(" ", "_").replace("-", "_") for col in df.columns]
    return df


def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse known date columns to datetime where present."""

    df = df.copy()
    for col in CONFIG.date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _clean_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply common cleaning rules such as Order_ID type coercion."""

    df = df.copy()
    if "Order_ID" in df.columns:
        df["Order_ID"] = df["Order_ID"].astype(str).str.strip()
    return df


@st.cache_data(show_spinner=False)
def load_all_data(data_dir: str = ".") -> Dict[str, pd.DataFrame]:
    """Load all CSV datasets required for the logistics analytics app.

    Parameters
    ----------
    data_dir: str
        Directory containing the CSV files.

    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary mapping dataset name to cleaned dataframe.
    """

    base_path = Path(data_dir)
    csv_files = {
        "orders": "orders.csv",
        "delivery_performance": "delivery_performance.csv",
        "routes_distance": "routes_distance.csv",
        "vehicle_fleet": "vehicle_fleet.csv",
        "warehouse_inventory": "warehouse_inventory.csv",
        "customer_feedback": "customer_feedback.csv",
        "cost_breakdown": "cost_breakdown.csv",
    }

    data: Dict[str, pd.DataFrame] = {}
    for name, file_name in csv_files.items():
        df = _safe_read_csv(base_path / file_name)
        df = _standardize_columns(df)
        df = _coerce_dates(df)
        df = _clean_common_columns(df)
        data[name] = df

    return data


def merge_order_datasets(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine orders, delivery performance, and cost breakdown data.

    Parameters
    ----------
    data: Dict[str, pd.DataFrame]
        Dictionary containing loaded dataframes.

    Returns
    -------
    pd.DataFrame
        Merged dataframe keyed by ``Order_ID``.
    """

    orders = data.get("orders", pd.DataFrame()).copy()
    delivery = data.get("delivery_performance", pd.DataFrame()).copy()
    costs = data.get("cost_breakdown", pd.DataFrame()).copy()

    merged = orders
    if not delivery.empty:
        merged = merged.merge(delivery, on="Order_ID", how="left", suffixes=("", "_delivery"))
    if not costs.empty:
        merged = merged.merge(costs, on="Order_ID", how="left")

    # Handle missing numeric values sensibly
    numeric_cols = merged.select_dtypes(include=["number"]).columns
    merged[numeric_cols] = merged[numeric_cols].fillna(0)

    # Add delivery delay information
    if {"Promised_Delivery_Date", "Actual_Delivery_Date"}.issubset(merged.columns):
        merged["Delivery_Delay_Days"] = (
            (merged["Actual_Delivery_Date"] - merged["Promised_Delivery_Date"]).dt.days
        )

    return merged


def calculate_demand_supply(
    merged_orders: pd.DataFrame, warehouse_inventory: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute demand and supply metrics per warehouse and product category."""

    if merged_orders.empty:
        demand_summary = pd.DataFrame(columns=["Origin", "Product_Category", "Order_Count", "Demand_Value"])
    else:
        demand = merged_orders.copy()
        demand["Order_Date"] = pd.to_datetime(demand["Order_Date"], errors="coerce")
        demand_summary = (
            demand.groupby(["Origin", "Product_Category"], dropna=False)
            .agg(Order_Count=("Order_ID", "nunique"), Demand_Value=("Order_Value_INR", "sum"))
            .reset_index()
        )
        demand_summary.rename(columns={"Origin": "Warehouse"}, inplace=True)

    inventory = warehouse_inventory.copy()
    inventory.rename(columns={"Warehouse": "Warehouse"}, inplace=True)

    return demand_summary, inventory
