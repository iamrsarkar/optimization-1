"""Streamlit application for NexGen Logistics warehouse optimization."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Tuple

import pandas as pd
import streamlit as st

from config import CONFIG
from data_loader import calculate_demand_supply, load_all_data, merge_order_datasets
from eda_utils import (
    augment_inventory_with_metrics,
    compute_kpis,
    filter_orders,
    moving_average_forecast,
)
from viz_utils import (
    co2_emission_chart,
    cost_breakdown_chart,
    demand_trend_chart,
    reorder_scatter,
    stock_vs_reorder_heatmap,
    storage_cost_chart,
    warehouse_stock_bar,
)
from warehouse_optimizer import generate_reorder_plan, generate_transfer_plan, run_lp_optimization


st.set_page_config(
    page_title="NexGen Logistics – Warehouse Optimization",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("NexGen Logistics Warehouse Optimization Suite")
st.caption(
    "Drive data-backed warehouse decisions with real-time inventory insights, optimization heuristics, and cost analytics."
)


@st.cache_data(show_spinner=False)
def _filter_options(df: pd.DataFrame, column: str) -> Tuple[str, ...]:
    if df.empty or column not in df:
        return tuple()
    return tuple(sorted(df[column].dropna().unique()))


def main() -> None:
    data = load_all_data()
    merged_orders = merge_order_datasets(data)
    demand_summary, inventory_raw = calculate_demand_supply(
        merged_orders, data.get("warehouse_inventory", pd.DataFrame())
    )
    inventory = augment_inventory_with_metrics(inventory_raw, demand_summary)

    # Sidebar filters
    st.sidebar.header("Filters")
    if not merged_orders.empty and "Order_Date" in merged_orders:
        min_date = merged_orders["Order_Date"].min()
        max_date = merged_orders["Order_Date"].max()
        date_range = st.sidebar.date_input(
            "Order Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_range = (pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
        else:
            date_range = None
    else:
        date_range = None

    product_filter = st.sidebar.multiselect(
        "Product Categories",
        options=_filter_options(merged_orders, "Product_Category"),
    )
    warehouse_filter = st.sidebar.multiselect(
        "Warehouses",
        options=_filter_options(merged_orders, "Origin"),
    )
    segment_filter = st.sidebar.multiselect(
        "Customer Segment",
        options=_filter_options(merged_orders, "Customer_Segment"),
    )
    priority_filter = st.sidebar.multiselect(
        "Order Priority",
        options=_filter_options(merged_orders, "Priority"),
    )

    filtered_orders = filter_orders(
        merged_orders,
        date_range=date_range,
        product_categories=tuple(product_filter) if product_filter else None,
        warehouses=tuple(warehouse_filter) if warehouse_filter else None,
        segments=tuple(segment_filter) if segment_filter else None,
        priorities=tuple(priority_filter) if priority_filter else None,
    )

    tabs = st.tabs([
        "Overview & KPIs",
        "Inventory Analysis",
        "Optimization Recommendations",
        "Cost & Sustainability",
    ])

    # Overview Tab
    with tabs[0]:
        st.subheader("Business Pulse")
        kpis = compute_kpis(filtered_orders, inventory)
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Total Orders", f"{kpis['total_orders']:,}")
        col2.metric("Total Order Value (INR)", f"{kpis['total_value']:,.0f}")
        col3.metric("Avg Delivery Delay (days)", f"{kpis['avg_delay']:.2f}" if pd.notna(kpis['avg_delay']) else "N/A")
        col4.metric("On-time %", f"{kpis['on_time_pct']:.1f}%" if pd.notna(kpis['on_time_pct']) else "N/A")
        col5.metric("Avg Stock Cover (days)", f"{kpis['avg_cover']:.1f}" if pd.notna(kpis['avg_cover']) else "N/A")
        col6.metric("Storage Cost (INR)", f"{kpis['total_storage_cost']:,.0f}")

        st.plotly_chart(demand_trend_chart(filtered_orders), use_container_width=True)

        st.markdown("### Demand Forecast (Moving Average)")
        forecast_df = moving_average_forecast(filtered_orders)
        if not forecast_df.empty:
            forecast_pivot = forecast_df.pivot_table(
                index="Order_Date", columns="Product_Category", values="MA_Forecast"
            )
            st.line_chart(forecast_pivot)
        else:
            st.info("Insufficient data for forecasting.")

    # Inventory Tab
    with tabs[1]:
        st.subheader("Inventory Health Dashboard")
        st.plotly_chart(warehouse_stock_bar(inventory), use_container_width=True)
        st.plotly_chart(reorder_scatter(inventory), use_container_width=True)
        st.plotly_chart(stock_vs_reorder_heatmap(inventory), use_container_width=True)

        st.markdown("### Inventory Table")
        st.dataframe(inventory, use_container_width=True)

        csv_buffer = io.StringIO()
        inventory.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download Inventory Snapshot",
            csv_buffer.getvalue(),
            file_name=f"inventory_snapshot_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
        )

    # Optimization Tab
    with tabs[2]:
        st.subheader("Optimization Recommendations")
        st.markdown("Use heuristic rebalancing to reduce carrying costs and avoid stock-outs.")

        if st.button("Generate Transfer Plan"):
            transfer_plan = generate_transfer_plan(inventory)
            reorder_plan = generate_reorder_plan(inventory)

            if transfer_plan.empty:
                st.warning("No transfer recommendations based on current stock levels.")
            else:
                st.success("Suggested Transfers")
                st.dataframe(transfer_plan, use_container_width=True)
                buffer = io.StringIO()
                transfer_plan.to_csv(buffer, index=False)
                st.download_button(
                    "Download Transfer Plan",
                    buffer.getvalue(),
                    file_name="transfer_plan.csv",
                    mime="text/csv",
                )

            if reorder_plan.empty:
                st.info("All warehouses meet reorder targets.")
            else:
                st.info("Reorder Recommendations")
                st.dataframe(reorder_plan, use_container_width=True)
                reorder_buffer = io.StringIO()
                reorder_plan.to_csv(reorder_buffer, index=False)
                st.download_button(
                    "Download Reorder Plan",
                    reorder_buffer.getvalue(),
                    file_name="reorder_plan.csv",
                    mime="text/csv",
                )

            if st.checkbox("Run Linear Programming Optimization (requires PuLP)"):
                lp_result = run_lp_optimization(inventory)
                if lp_result.empty:
                    st.warning("LP optimization could not run (missing PuLP or insufficient data).")
                else:
                    st.success("Optimized Transfer Recommendations")
                    st.dataframe(lp_result, use_container_width=True)
        else:
            st.info("Click 'Generate Transfer Plan' to compute recommended actions.")

    # Cost & Sustainability Tab
    with tabs[3]:
        st.subheader("Cost & Sustainability Insights")
        st.plotly_chart(cost_breakdown_chart(data.get("cost_breakdown", pd.DataFrame())), use_container_width=True)
        st.plotly_chart(storage_cost_chart(inventory), use_container_width=True)
        st.plotly_chart(co2_emission_chart(data.get("vehicle_fleet", pd.DataFrame())), use_container_width=True)

        st.markdown("### Delivery Feedback Snapshot")
        feedback = data.get("customer_feedback", pd.DataFrame())
        if feedback.empty:
            st.info("No feedback records available.")
        else:
            st.dataframe(
                feedback[[
                    "Feedback_ID",
                    "Order_ID",
                    "Rating",
                    "Recommendation_Likelihood",
                    "Issue_Category",
                    "Feedback_Date",
                ]].sort_values("Feedback_Date", ascending=False),
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
