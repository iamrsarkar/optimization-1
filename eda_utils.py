"""Exploratory data analysis helpers for the NexGen Logistics project."""
from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd

from analysis_utils import DemandFilters, combine_inventory_with_demand, estimate_demand
from config import DEFAULT_SAFETY_STOCK_DAYS, SURPLUS_MULTIPLIER


def compute_overview_kpis(master_orders: pd.DataFrame, inventory: pd.DataFrame) -> Dict[str, float]:
    metrics: Dict[str, float] = {
        "total_orders": float(master_orders["Order_ID"].nunique()) if not master_orders.empty else 0.0,
        "total_revenue": master_orders.get("Order_Value_INR", pd.Series(dtype=float)).sum(),
        "on_time_rate": 0.0,
        "average_delay_days": 0.0,
        "total_inventory_value": 0.0,
    }

    if not master_orders.empty and {"Delayed_Flag"}.issubset(master_orders.columns):
        valid = master_orders["Delayed_Flag"].notna()
        if valid.any():
            on_time = (master_orders.loc[valid, "Delayed_Flag"] == 0).mean()
            metrics["on_time_rate"] = float(on_time)
        if "Delivery_delay_days" in master_orders.columns:
            delays = master_orders.loc[master_orders["Delivery_delay_days"].notna(), "Delivery_delay_days"]
            if not delays.empty:
                metrics["average_delay_days"] = float(delays.mean())

    if not inventory.empty and "Storage_Cost_INR_per_unit" in inventory.columns:
        metrics["total_inventory_value"] = float(
            (inventory["Stock_Level"] * inventory["Storage_Cost_INR_per_unit"]).sum()
        )

    return metrics


def compute_inventory_demand_summary(
    master_orders: pd.DataFrame,
    inventory: pd.DataFrame,
    filters: Optional[DemandFilters] = None,
    safety_stock_days: float = DEFAULT_SAFETY_STOCK_DAYS,
    surplus_multiplier: float = SURPLUS_MULTIPLIER,
) -> pd.DataFrame:
    demand = estimate_demand(master_orders, filters)
    summary = combine_inventory_with_demand(inventory, demand, safety_stock_days, surplus_multiplier)
    return summary


def top_overstock(summary: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if summary.empty:
        return summary
    df = summary.copy()
    df = df[df["is_overstock"]]
    df["excess_units"] = df["Stock_Level"] - df["target_stock"]
    return df.sort_values("excess_units", ascending=False).head(top_n)


def top_understock(summary: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if summary.empty:
        return summary
    df = summary.copy()
    df = df[df["is_understock"]]
    df["short_units"] = df["target_stock"] - df["Stock_Level"]
    return df.sort_values("short_units", ascending=False).head(top_n)


def delivery_performance_summary(delivery_df: pd.DataFrame) -> Dict[str, float]:
    if delivery_df.empty:
        return {"on_time_rate": 0.0, "avg_customer_rating": 0.0, "delay_days_avg": 0.0}

    metrics: Dict[str, float] = {}
    if {"Promised_Delivery_Date", "Actual_Delivery_Date"}.issubset(delivery_df.columns):
        delays = (
            delivery_df["Actual_Delivery_Date"] - delivery_df["Promised_Delivery_Date"]
        ).dt.days
        metrics["delay_days_avg"] = float(delays.mean()) if not delays.empty else 0.0
        metrics["on_time_rate"] = float((delays <= 0).mean()) if not delays.empty else 0.0
    metrics["avg_customer_rating"] = float(delivery_df["Customer_Rating"].mean(skipna=True))
    return metrics


def customer_feedback_summary(feedback_df: pd.DataFrame) -> pd.DataFrame:
    if feedback_df.empty:
        return pd.DataFrame()
    summary = (
        feedback_df.groupby("Issue_Category")
        .agg(avg_rating=("Rating", "mean"), feedback_count=("Feedback_ID", "count"))
        .reset_index()
    )
    return summary


def cost_component_summary(cost_df: pd.DataFrame, master_orders: pd.DataFrame) -> pd.DataFrame:
    if cost_df.empty:
        return pd.DataFrame()
    component_cols = [
        "Fuel_Cost_INR",
        "Labor_Cost_INR",
        "Maintenance_Cost_INR",
        "Insurance_Cost_INR",
        "Packaging_Cost_INR",
        "Technology_Fee_INR",
        "Other_Overhead_INR",
    ]
    available_cols = [col for col in component_cols if col in cost_df.columns]
    summary = (
        cost_df[available_cols]
        .mean()
        .rename("avg_cost")
        .reset_index()
        .rename(columns={"index": "Cost_Component"})
    )

    if not master_orders.empty:
        per_warehouse = master_orders.groupby("Origin")["total_delivery_cost"].mean().reset_index()
        per_warehouse.rename(columns={"Origin": "Warehouse", "total_delivery_cost": "avg_order_cost"}, inplace=True)
        summary = summary.merge(per_warehouse, how="cross")
    return summary


def aggregate_costs(master_orders: pd.DataFrame) -> pd.DataFrame:
    if master_orders.empty:
        return pd.DataFrame()
    component_cols = [
        "Delivery_Cost_INR",
        "Fuel_Cost_INR",
        "Labor_Cost_INR",
        "Maintenance_Cost_INR",
        "Insurance_Cost_INR",
        "Packaging_Cost_INR",
        "Technology_Fee_INR",
        "Other_Overhead_INR",
    ]
    available_cols = [col for col in component_cols if col in master_orders.columns]
    melted = master_orders.melt(
        id_vars=["Order_ID", "Origin", "Product_Category"],
        value_vars=available_cols,
        var_name="Cost_Component",
        value_name="Amount_INR",
    )
    melted = melted.dropna(subset=["Amount_INR"])
    return melted
