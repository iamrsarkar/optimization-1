"""Reusable Plotly visualisations for the Streamlit app."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px


def orders_over_time(master_orders: pd.DataFrame) -> Optional[px.line]:
    if master_orders.empty or "Order_Date" not in master_orders.columns:
        return None
    df = master_orders.dropna(subset=["Order_Date"])
    if df.empty:
        return None
    time_series = (
        df.groupby(pd.Grouper(key="Order_Date", freq="W"))
        .agg(order_count=("Order_ID", "nunique"), total_value=("Order_Value_INR", "sum"))
        .reset_index()
    )
    fig = px.line(
        time_series,
        x="Order_Date",
        y="order_count",
        title="Orders Over Time (Weekly)",
        markers=True,
    )
    fig.update_layout(yaxis_title="Order Count", xaxis_title="Week")
    return fig


def orders_by_warehouse_category(master_orders: pd.DataFrame) -> Optional[px.bar]:
    if master_orders.empty:
        return None
    grouped = (
        master_orders.groupby(["Origin", "Product_Category"])
        .agg(order_count=("Order_ID", "nunique"))
        .reset_index()
    )
    if grouped.empty:
        return None
    fig = px.bar(
        grouped,
        x="Origin",
        y="order_count",
        color="Product_Category",
        title="Orders by Warehouse and Product Category",
        barmode="stack",
    )
    fig.update_layout(xaxis_title="Warehouse", yaxis_title="Order Count")
    return fig


def on_time_by_priority(master_orders: pd.DataFrame) -> Optional[px.bar]:
    if master_orders.empty or "Delayed_Flag" not in master_orders.columns:
        return None
    df = master_orders.dropna(subset=["Delayed_Flag", "Priority"])
    if df.empty:
        return None
    summary = (
        df.groupby("Priority")
        .agg(on_time_rate=("Delayed_Flag", lambda x: (x == 0).mean()))
        .reset_index()
    )
    fig = px.bar(
        summary,
        x="Priority",
        y="on_time_rate",
        title="On-Time Delivery Rate by Priority",
        text="on_time_rate",
    )
    fig.update_layout(yaxis_tickformat=".0%", yaxis_title="On-Time Rate")
    fig.update_traces(texttemplate="%{text:.1%}", textposition="outside")
    return fig


def inventory_heatmap(summary: pd.DataFrame, value_col: str = "Stock_Level") -> Optional[px.imshow]:
    if summary.empty or value_col not in summary.columns:
        return None
    pivot = summary.pivot_table(index="Warehouse", columns="Product_Category", values=value_col, aggfunc="sum")
    if pivot.empty:
        return None
    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        title=f"{value_col.replace('_', ' ')} by Warehouse & Product",
        color_continuous_scale="Blues",
    )
    fig.update_layout(xaxis_title="Product Category", yaxis_title="Warehouse")
    return fig


def inventory_value_bar(summary: pd.DataFrame) -> Optional[px.bar]:
    if summary.empty or "inventory_value" not in summary.columns:
        return None
    grouped = summary.groupby("Warehouse")["inventory_value"].sum().reset_index()
    fig = px.bar(
        grouped,
        x="Warehouse",
        y="inventory_value",
        title="Inventory Value by Warehouse",
        text="inventory_value",
    )
    fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
    fig.update_layout(yaxis_title="Inventory Value (INR)")
    return fig


def stock_cover_distribution(summary: pd.DataFrame) -> Optional[px.histogram]:
    if summary.empty or "stock_cover_days" not in summary.columns:
        return None
    df = summary.replace({"stock_cover_days": {float("inf"): None}}).dropna(subset=["stock_cover_days"])
    if df.empty:
        return None
    fig = px.histogram(
        df,
        x="stock_cover_days",
        color="Warehouse",
        nbins=30,
        title="Distribution of Stock Cover Days",
    )
    fig.update_layout(xaxis_title="Stock Cover (Days)", yaxis_title="Count of Combinations")
    return fig


def cost_component_stacked(costs: pd.DataFrame) -> Optional[px.bar]:
    if costs.empty:
        return None
    fig = px.bar(
        costs,
        x="Origin",
        y="Amount_INR",
        color="Cost_Component",
        title="Cost Components per Order",
        barmode="stack",
    )
    fig.update_layout(xaxis_title="Warehouse", yaxis_title="Cost (INR)")
    return fig


def cost_per_order_by_warehouse(master_orders: pd.DataFrame) -> Optional[px.line]:
    if master_orders.empty:
        return None
    grouped = (
        master_orders.groupby("Origin")["total_delivery_cost"].mean().reset_index()
    )
    if grouped.empty:
        return None
    fig = px.line(
        grouped,
        x="Origin",
        y="total_delivery_cost",
        title="Average Delivery Cost per Order by Warehouse",
        markers=True,
    )
    fig.update_layout(xaxis_title="Warehouse", yaxis_title="Avg Cost (INR)")
    return fig


def rating_vs_delay_scatter(master_orders: pd.DataFrame) -> Optional[px.scatter]:
    if master_orders.empty or "Customer_Rating" not in master_orders.columns:
        return None
    df = master_orders.dropna(subset=["Customer_Rating", "Delivery_delay_days"])
    if df.empty:
        return None
    fig = px.scatter(
        df,
        x="Delivery_delay_days",
        y="Customer_Rating",
        color="Priority",
        trendline="ols",
        title="Customer Rating vs Delivery Delay",
    )
    fig.update_layout(xaxis_title="Delivery Delay (days)", yaxis_title="Customer Rating")
    return fig
