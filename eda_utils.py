"""Analytical utility functions supporting the Streamlit dashboards."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from config import CONFIG


def compute_kpis(merged_orders: pd.DataFrame, inventory: pd.DataFrame) -> Dict[str, float]:
    """Calculate core KPI metrics for the overview dashboard."""

    total_orders = merged_orders["Order_ID"].nunique() if not merged_orders.empty else 0
    total_value = merged_orders["Order_Value_INR"].sum() if "Order_Value_INR" in merged_orders else 0.0

    if "Delivery_Delay_Days" in merged_orders:
        avg_delay = merged_orders["Delivery_Delay_Days"].replace({np.nan: 0}).mean()
        on_time_pct = (
            (merged_orders["Delivery_Delay_Days"] <= 0).mean() * 100
            if not merged_orders.empty
            else np.nan
        )
    else:
        avg_delay = np.nan
        on_time_pct = np.nan

    if inventory.empty:
        avg_cover = np.nan
        total_storage_cost = 0.0
    else:
        avg_cover = inventory.get("Stock_Cover_Days", pd.Series(dtype=float)).replace({np.inf: np.nan}).mean()
        total_storage_cost = inventory.get("Storage_Cost_Total", pd.Series(dtype=float)).sum()

    return {
        "total_orders": total_orders,
        "total_value": total_value,
        "avg_delay": avg_delay,
        "on_time_pct": on_time_pct,
        "avg_cover": avg_cover,
        "total_storage_cost": total_storage_cost,
    }


def augment_inventory_with_metrics(
    inventory: pd.DataFrame, demand_summary: pd.DataFrame
) -> pd.DataFrame:
    """Enrich the inventory table with demand-based metrics for analysis."""

    inventory = inventory.copy()
    if inventory.empty:
        return inventory

    alias_map = {
        "Warehouse": ["Warehouse", "Location", "warehouse", "location"],
        "Product_Category": ["Product_Category", "Product", "Category"],
        "Stock_Level": ["Stock_Level", "Current_Stock_Units", "stock_level"],
        "Reorder_Level": ["Reorder_Level", "reorder_level"],
        "Storage_Cost_INR_per_unit": [
            "Storage_Cost_INR_per_unit",
            "Storage_Cost_per_Unit",
            "storage_cost_inr_per_unit",
        ],
    }

    for canonical, candidates in alias_map.items():
        if canonical not in inventory.columns:
            for candidate in candidates:
                if candidate in inventory.columns:
                    inventory[canonical] = inventory[candidate]
                    break
        if canonical not in inventory.columns:
            if "Cost" in canonical or "Level" in canonical:
                inventory[canonical] = 0
            else:
                inventory[canonical] = "Unknown"

    demand_summary = demand_summary.copy()
    demand_summary.rename(columns={"Demand_Value": "Demand_Value_INR"}, inplace=True)

    if "Warehouse" not in demand_summary.columns:
        for candidate in ("Origin", "warehouse", "Warehouse_ID"):
            if candidate in demand_summary.columns:
                demand_summary.rename(columns={candidate: "Warehouse"}, inplace=True)
                break
    if "Product_Category" not in demand_summary.columns:
        for candidate in ("Product", "Category"):
            if candidate in demand_summary.columns:
                demand_summary.rename(columns={candidate: "Product_Category"}, inplace=True)
                break

    inventory = inventory.merge(
        demand_summary,
        on=["Warehouse", "Product_Category"],
        how="left",
    )

    inventory["Order_Count"] = inventory["Order_Count"].fillna(0)
    inventory["Demand_Value_INR"] = inventory["Demand_Value_INR"].fillna(0.0)

    # Average daily demand based on order count (assume monthly dataset ~30 days)
    inventory["Avg_Daily_Demand"] = inventory["Order_Count"] / 30.0
    inventory["Avg_Daily_Demand"] = inventory["Avg_Daily_Demand"].replace(0, np.nan)
    inventory["Stock_Cover_Days"] = inventory["Stock_Level"] / inventory["Avg_Daily_Demand"]
    inventory["Stock_Cover_Days"] = inventory["Stock_Cover_Days"].replace({np.nan: np.inf})

    inventory["Storage_Cost_Total"] = (
        inventory["Stock_Level"] * inventory.get("Storage_Cost_INR_per_unit", 0)
    )

    inventory["Understock_Flag"] = (
        (inventory["Stock_Level"] < inventory["Reorder_Level"]) |
        (inventory["Stock_Cover_Days"] < CONFIG.stock_cover_threshold)
    )
    inventory["Overstock_Flag"] = (
        (inventory["Stock_Level"] > inventory["Reorder_Level"] * CONFIG.overstock_multiplier)
    )

    inventory["Potential_Reorder_Qty"] = (
        inventory["Reorder_Level"] - inventory["Stock_Level"]
    ).clip(lower=0)

    return inventory


def filter_orders(
    orders: pd.DataFrame,
    date_range: Tuple[pd.Timestamp, pd.Timestamp] | None = None,
    product_categories: Tuple[str, ...] | None = None,
    warehouses: Tuple[str, ...] | None = None,
    segments: Tuple[str, ...] | None = None,
    priorities: Tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Apply interactive filters to the merged orders dataset."""

    df = orders.copy()
    if df.empty:
        return df

    if date_range:
        start, end = date_range
        df = df[(df["Order_Date"] >= start) & (df["Order_Date"] <= end)]

    if product_categories:
        df = df[df["Product_Category"].isin(product_categories)]

    if warehouses:
        df = df[df["Origin"].isin(warehouses)]

    if segments:
        df = df[df["Customer_Segment"].isin(segments)]

    if priorities:
        df = df[df["Priority"].isin(priorities)]

    return df


def moving_average_forecast(orders: pd.DataFrame) -> pd.DataFrame:
    """Generate a simple moving average forecast of demand per product category."""

    if orders.empty or "Order_Date" not in orders:
        return pd.DataFrame(columns=["Order_Date", "Product_Category", "Actual_Orders", "MA_Forecast"])

    df = orders.copy()
    df = df.dropna(subset=["Order_Date"])
    df["Order_Date"] = pd.to_datetime(df["Order_Date"])
    grouped = (
        df.groupby([pd.Grouper(key="Order_Date", freq="D"), "Product_Category"])
        .size()
        .reset_index(name="Actual_Orders")
    )
    grouped.sort_values("Order_Date", inplace=True)

    grouped["MA_Forecast"] = (
        grouped.groupby("Product_Category")["Actual_Orders"].transform(
            lambda s: s.rolling(CONFIG.moving_average_window, min_periods=1).mean()
        )
    )
    return grouped
