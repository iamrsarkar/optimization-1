"""Utilities for loading and cleaning NexGen Logistics datasets."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from config import DATE_FORMAT, WAREHOUSES

try:  # pragma: no cover - caching only relevant inside Streamlit
    import streamlit as st

    cache_data = st.cache_data
except ModuleNotFoundError:  # pragma: no cover - fallback for CLI usage
    st = None

    def cache_data(func=None, **_kwargs):  # type: ignore[misc]
        if func is None:
            return lambda f: f
        return func


LOGGER = logging.getLogger(__name__)

DATE_COLUMNS = {
    "orders.csv": ["Order_Date"],
}


def _parse_dates(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def _standardize_strings(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype(str)
                .str.strip()
                .replace({"nan": np.nan})
                .fillna("Unknown")
                .str.title()
            )
    return df


def _standardize_order_ids(df: pd.DataFrame) -> pd.DataFrame:
    if "Order_ID" in df.columns:
        df["Order_ID"] = df["Order_ID"].astype(str).str.strip()
    return df


@cache_data(show_spinner=False)
def load_csv(file_path: str | Path, parse_dates: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Load a CSV file with graceful error handling."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    if parse_dates:
        df = _parse_dates(df, parse_dates)
    df = _standardize_order_ids(df)
    return df


def load_orders() -> pd.DataFrame:
    df = load_csv("orders.csv", parse_dates=DATE_COLUMNS.get("orders.csv"))
    df = _standardize_strings(
        df,
        ["Customer_Segment", "Priority", "Product_Category", "Origin", "Destination", "Special_Handling"],
    )
    df["Origin"] = df["Origin"].replace({w: w for w in WAREHOUSES})
    df["Order_Value_INR"] = pd.to_numeric(df["Order_Value_INR"], errors="coerce")
    return df


def load_delivery_performance() -> pd.DataFrame:
    df = load_csv("delivery_performance.csv")
    rename_map = {
        "Promised_Delivery_Days": "Promised_Delivery_Days",
        "Actual_Delivery_Days": "Actual_Delivery_Days",
    }
    df = df.rename(columns=rename_map)
    df = _standardize_strings(df, ["Carrier", "Delivery_Status", "Quality_Issue"])
    for col in ["Promised_Delivery_Days", "Actual_Delivery_Days"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Customer_Rating"] = pd.to_numeric(df.get("Customer_Rating"), errors="coerce")
    df["Delivery_Cost_INR"] = pd.to_numeric(df.get("Delivery_Cost_INR"), errors="coerce")
    return df


def load_routes_distance() -> pd.DataFrame:
    df = load_csv("routes_distance.csv")
    df = df.rename(
        columns={
            "Distance_KM": "Distance_km",
            "Fuel_Consumption_L": "Fuel_Consumed_L",
            "Toll_Charges_INR": "Toll_Cost_INR",
            "Traffic_Delay_Minutes": "Traffic_Delay_Min",
        }
    )
    numeric_cols = ["Distance_km", "Fuel_Consumed_L", "Toll_Cost_INR", "Traffic_Delay_Min"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = _standardize_strings(df, ["Route", "Weather_Impact"])
    return df


def load_vehicle_fleet() -> pd.DataFrame:
    df = load_csv("vehicle_fleet.csv")
    df = df.rename(
        columns={
            "Capacity_KG": "Capacity_kg",
            "Fuel_Efficiency_KM_per_L": "Fuel_Efficiency_km_per_L",
            "Age_Years": "Vehicle_Age_Years",
            "CO2_Emissions_Kg_per_KM": "CO2_kg_per_km",
        }
    )
    df = _standardize_strings(df, ["Vehicle_Type", "Current_Location", "Status"])
    numeric_cols = ["Capacity_kg", "Fuel_Efficiency_km_per_L", "Vehicle_Age_Years", "CO2_kg_per_km"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_warehouse_inventory() -> pd.DataFrame:
    df = load_csv("warehouse_inventory.csv")
    df = df.rename(
        columns={
            "Location": "Warehouse",
            "Current_Stock_Units": "Stock_Level",
            "Storage_Cost_per_Unit": "Storage_Cost_INR_per_unit",
        }
    )
    df = _standardize_strings(df, ["Warehouse", "Product_Category"])
    numeric_cols = ["Stock_Level", "Reorder_Level", "Storage_Cost_INR_per_unit"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_customer_feedback() -> pd.DataFrame:
    df = load_csv("customer_feedback.csv")
    df = df.rename(columns={"Would_Recommend": "Recommendation_Likelihood"})
    df = _parse_dates(df, ["Feedback_Date"])
    df = _standardize_strings(df, ["Issue_Category"])
    df["Rating"] = pd.to_numeric(df.get("Rating"), errors="coerce")
    if "Recommendation_Likelihood" in df.columns:
        df["Recommendation_Likelihood"] = df["Recommendation_Likelihood"].fillna("Unknown")
    return df


def load_cost_breakdown() -> pd.DataFrame:
    df = load_csv("cost_breakdown.csv")
    df = df.rename(
        columns={
            "Fuel_Cost": "Fuel_Cost_INR",
            "Labor_Cost": "Labor_Cost_INR",
            "Vehicle_Maintenance": "Maintenance_Cost_INR",
            "Insurance": "Insurance_Cost_INR",
            "Packaging_Cost": "Packaging_Cost_INR",
            "Technology_Platform_Fee": "Technology_Fee_INR",
            "Other_Overhead": "Other_Overhead_INR",
        }
    )
    cost_columns = [
        "Fuel_Cost_INR",
        "Labor_Cost_INR",
        "Maintenance_Cost_INR",
        "Insurance_Cost_INR",
        "Packaging_Cost_INR",
        "Technology_Fee_INR",
        "Other_Overhead_INR",
    ]
    for col in cost_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_all_data() -> Dict[str, pd.DataFrame]:
    """Load all datasets and return a mapping."""
    loaders = {
        "orders": load_orders,
        "delivery_performance": load_delivery_performance,
        "routes_distance": load_routes_distance,
        "vehicle_fleet": load_vehicle_fleet,
        "warehouse_inventory": load_warehouse_inventory,
        "customer_feedback": load_customer_feedback,
        "cost_breakdown": load_cost_breakdown,
    }
    datasets: Dict[str, pd.DataFrame] = {}
    for name, loader in loaders.items():
        try:
            datasets[name] = loader()
        except FileNotFoundError as err:
            LOGGER.error("Missing dataset %s: %s", name, err)
            datasets[name] = pd.DataFrame()
    return datasets


def create_master_orders(datasets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create the master orders table by merging available datasets."""
    orders = datasets.get("orders", pd.DataFrame()).copy()
    if orders.empty:
        return pd.DataFrame()

    delivery = datasets.get("delivery_performance", pd.DataFrame())
    routes = datasets.get("routes_distance", pd.DataFrame())
    costs = datasets.get("cost_breakdown", pd.DataFrame())

    master = orders.copy()

    if not delivery.empty:
        master = master.merge(delivery, on="Order_ID", how="left", suffixes=("", "_delivery"))
        master["Has_delivery_data"] = master["Carrier"].notna()
        if "Promised_Delivery_Days" in master.columns:
            master["Promised_Delivery_Date"] = master["Order_Date"] + pd.to_timedelta(
                master["Promised_Delivery_Days"], unit="D"
            )
        if "Actual_Delivery_Days" in master.columns:
            master["Actual_Delivery_Date"] = master["Order_Date"] + pd.to_timedelta(
                master["Actual_Delivery_Days"], unit="D"
            )
        if {"Promised_Delivery_Date", "Actual_Delivery_Date"}.issubset(master.columns):
            master["Delivery_delay_days"] = (
                master["Actual_Delivery_Date"] - master["Promised_Delivery_Date"]
            ).dt.days
            master["Delayed_Flag"] = (master["Delivery_delay_days"] > 0).astype(int)
    else:
        master["Has_delivery_data"] = False

    if not routes.empty:
        master = master.merge(routes, on="Order_ID", how="left", suffixes=("", "_route"))
        master["Has_route_data"] = master["Distance_km"].notna()
        master.loc[master["Fuel_Consumed_L"] > 0, "Fuel_Efficiency_km_per_L"] = (
            master.loc[master["Fuel_Consumed_L"] > 0, "Distance_km"]
            / master.loc[master["Fuel_Consumed_L"] > 0, "Fuel_Consumed_L"]
        )
    else:
        master["Has_route_data"] = False

    if not costs.empty:
        master = master.merge(costs, on="Order_ID", how="left", suffixes=("", "_cost"))
        master["Has_cost_data"] = master[[
            "Fuel_Cost_INR",
            "Labor_Cost_INR",
            "Maintenance_Cost_INR",
            "Insurance_Cost_INR",
            "Packaging_Cost_INR",
            "Technology_Fee_INR",
            "Other_Overhead_INR",
        ]].notna().any(axis=1)
    else:
        master["Has_cost_data"] = False

    cost_components = [
        "Delivery_Cost_INR",
        "Fuel_Cost_INR",
        "Labor_Cost_INR",
        "Maintenance_Cost_INR",
        "Insurance_Cost_INR",
        "Packaging_Cost_INR",
        "Technology_Fee_INR",
        "Other_Overhead_INR",
    ]
    master["total_delivery_cost"] = master[cost_components].fillna(0).sum(axis=1)
    master.loc[master["Distance_km"] > 0, "Cost_per_km"] = (
        master.loc[master["Distance_km"] > 0, "total_delivery_cost"]
        / master.loc[master["Distance_km"] > 0, "Distance_km"]
    )
    master["Order_Date"] = pd.to_datetime(master["Order_Date"], format=DATE_FORMAT, errors="coerce")

    return master
