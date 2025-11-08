"""Shared analytical utilities for NexGen Logistics datasets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from config import WAREHOUSES


@dataclass
class DemandFilters:
    start_date: Optional[pd.Timestamp] = None
    end_date: Optional[pd.Timestamp] = None
    warehouses: Optional[Sequence[str]] = None
    product_categories: Optional[Sequence[str]] = None


def apply_order_filters(df: pd.DataFrame, filters: Optional[DemandFilters] = None) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    if filters is None:
        return result

    if filters.start_date is not None:
        result = result[result["Order_Date"] >= filters.start_date]
    if filters.end_date is not None:
        result = result[result["Order_Date"] <= filters.end_date]
    if filters.warehouses:
        result = result[result["Origin"].isin(filters.warehouses)]
    if filters.product_categories:
        result = result[result["Product_Category"].isin(filters.product_categories)]
    return result


def estimate_demand(master_orders: pd.DataFrame, filters: Optional[DemandFilters] = None) -> pd.DataFrame:
    """Estimate order demand per warehouse and product category."""
    if master_orders.empty:
        return pd.DataFrame()

    filtered = apply_order_filters(master_orders, filters)
    if filtered.empty:
        return pd.DataFrame()

    if filters and filters.start_date and filters.end_date:
        days = max((filters.end_date - filters.start_date).days + 1, 1)
    else:
        min_date = filtered["Order_Date"].min()
        max_date = filtered["Order_Date"].max()
        if pd.isna(min_date) or pd.isna(max_date):
            days = 30
        else:
            days = max((max_date - min_date).days + 1, 1)

    demand = (
        filtered.groupby(["Origin", "Product_Category"], dropna=False)
        .agg(
            order_count=("Order_ID", "nunique"),
            total_order_value=("Order_Value_INR", "sum"),
        )
        .reset_index()
    )

    demand.rename(columns={"Origin": "Warehouse"}, inplace=True)
    demand["Warehouse"] = demand["Warehouse"].fillna("Unknown").str.title()
    demand = demand[demand["Warehouse"].isin(WAREHOUSES)]

    demand["avg_daily_demand"] = demand["order_count"] / days
    demand["avg_monthly_demand"] = demand["avg_daily_demand"] * 30
    demand["avg_daily_value"] = demand["total_order_value"] / days

    return demand


def combine_inventory_with_demand(
    inventory: pd.DataFrame,
    demand: pd.DataFrame,
    safety_stock_days: float,
    surplus_multiplier: float,
) -> pd.DataFrame:
    if inventory.empty:
        return pd.DataFrame()

    inv = inventory.copy()
    inv["Warehouse"] = inv["Warehouse"].fillna("Unknown").str.title()
    inv = inv[inv["Warehouse"].isin(WAREHOUSES)]

    summary = inv.merge(
        demand,
        on=["Warehouse", "Product_Category"],
        how="left",
        validate="m:1",
    )
    summary["order_count"] = summary["order_count"].fillna(0)
    summary["total_order_value"] = summary["total_order_value"].fillna(0.0)
    summary["avg_daily_demand"] = summary["avg_daily_demand"].fillna(0.0)
    summary["avg_monthly_demand"] = summary["avg_monthly_demand"].fillna(0.0)

    summary["stock_cover_days"] = np.where(
        summary["avg_daily_demand"] > 0,
        summary["Stock_Level"] / summary["avg_daily_demand"],
        np.inf,
    )

    summary["inventory_value"] = summary["Stock_Level"] * summary.get("Storage_Cost_INR_per_unit", 0)

    summary["target_stock"] = summary[["Reorder_Level", "avg_daily_demand"]].apply(
        lambda row: max(row["Reorder_Level"], row["avg_daily_demand"] * safety_stock_days), axis=1
    )

    summary["surplus_threshold"] = summary["target_stock"] * surplus_multiplier
    summary["surplus_qty"] = (summary["Stock_Level"] - summary["target_stock"]).clip(lower=0)
    summary["available_to_transfer"] = (summary["Stock_Level"] - summary["target_stock"]).clip(lower=0)
    summary["shortage_qty"] = (summary["target_stock"] - summary["Stock_Level"]).clip(lower=0)

    def classify(row: pd.Series) -> str:
        if row["Stock_Level"] <= 0:
            return "Deficit"
        if row["Stock_Level"] < row["target_stock"] or row["Stock_Level"] < row["Reorder_Level"]:
            return "Deficit"
        if row["Stock_Level"] > row["surplus_threshold"]:
            return "Surplus"
        return "Balanced"

    summary["Classification"] = summary.apply(classify, axis=1)
    summary["is_overstock"] = summary["Classification"] == "Surplus"
    summary["is_understock"] = summary["Classification"] == "Deficit"

    return summary
