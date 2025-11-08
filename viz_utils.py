"""Visualization utilities using Plotly for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def warehouse_stock_bar(inventory: pd.DataFrame):
    """Return a stacked bar chart of stock levels by warehouse and product."""

    if inventory.empty:
        return px.bar(title="No inventory data available")

    df = inventory.copy()
    fig = px.bar(
        df,
        x="Warehouse",
        y="Stock_Level",
        color="Product_Category",
        title="Warehouse Stock Levels",
        labels={"Stock_Level": "Units", "Warehouse": "Warehouse"},
    )
    fig.update_layout(legend_title_text="Product Category")
    return fig


def stock_vs_reorder_heatmap(inventory: pd.DataFrame):
    """Visualize stock versus reorder levels using a heatmap."""

    if inventory.empty:
        return px.imshow([[0]], text_auto=True, title="No data")

    df = inventory.pivot_table(
        index="Warehouse",
        columns="Product_Category",
        values="Stock_Level",
        aggfunc="sum",
        fill_value=0,
    )
    fig = px.imshow(
        df,
        text_auto=True,
        labels=dict(color="Stock Level"),
        title="Stock Distribution by Warehouse & Product",
    )
    return fig


def storage_cost_chart(inventory: pd.DataFrame):
    """Bar chart of total storage cost per warehouse."""

    if inventory.empty:
        return px.bar(title="No inventory data available")

    df = inventory.groupby("Warehouse", as_index=False)["Storage_Cost_Total"].sum()
    fig = px.bar(
        df,
        x="Warehouse",
        y="Storage_Cost_Total",
        title="Storage Cost by Warehouse",
        labels={"Storage_Cost_Total": "INR"},
    )
    return fig


def demand_trend_chart(orders: pd.DataFrame):
    """Line chart showing demand trend over time."""

    if orders.empty:
        return px.line(title="No order data available")

    df = orders.copy()
    df = df.dropna(subset=["Order_Date"])
    df["Order_Date"] = pd.to_datetime(df["Order_Date"])
    trend = df.groupby(pd.Grouper(key="Order_Date", freq="D"))[["Order_Value_INR"]].sum().reset_index()
    fig = px.line(
        trend,
        x="Order_Date",
        y="Order_Value_INR",
        title="Daily Demand Value",
        labels={"Order_Date": "Date", "Order_Value_INR": "Demand Value (INR)"},
    )
    return fig


def reorder_scatter(inventory: pd.DataFrame):
    """Scatter plot comparing stock and reorder levels highlighting status."""

    if inventory.empty:
        return px.scatter(title="No inventory data available")

    df = inventory.copy()
    df["Status"] = df.apply(
        lambda row: "Understock" if row.get("Understock_Flag") else (
            "Overstock" if row.get("Overstock_Flag") else "Balanced"
        ),
        axis=1,
    )

    fig = px.scatter(
        df,
        x="Reorder_Level",
        y="Stock_Level",
        color="Status",
        symbol="Status",
        hover_data=["Warehouse", "Product_Category", "Stock_Cover_Days"],
        title="Stock vs Reorder Levels",
        labels={"Reorder_Level": "Reorder Level", "Stock_Level": "Stock Level"},
    )
    return fig


def cost_breakdown_chart(costs: pd.DataFrame):
    """Stacked bar chart of average cost components."""

    if costs.empty:
        return px.bar(title="No cost data available")

    numeric_cols = [col for col in costs.columns if col.endswith("_INR")]
    df = costs[numeric_cols].mean().reset_index()
    df.columns = ["Cost_Component", "Average_INR"]
    fig = px.bar(
        df,
        x="Cost_Component",
        y="Average_INR",
        title="Average Cost Components per Order",
        labels={"Average_INR": "INR"},
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def co2_emission_chart(vehicle_data: pd.DataFrame):
    """Visualize CO2 emissions per vehicle type."""

    if vehicle_data.empty:
        return px.bar(title="No vehicle data available")

    df = vehicle_data.groupby("Vehicle_Type", as_index=False)["CO2_kg_per_km"].mean()
    fig = px.bar(
        df,
        x="Vehicle_Type",
        y="CO2_kg_per_km",
        title="Average CO₂ Emissions per Vehicle Type",
        labels={"CO2_kg_per_km": "CO₂ (kg/km)"},
    )
    return fig
