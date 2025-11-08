"""Streamlit application for NexGen Logistics warehouse optimization."""
from __future__ import annotations

from io import StringIO
from typing import Optional

import pandas as pd
import streamlit as st

from analysis_utils import DemandFilters
from data_loader import create_master_orders, load_all_data
from eda_utils import (
    aggregate_costs,
    compute_inventory_demand_summary,
    compute_overview_kpis,
    customer_feedback_summary,
    delivery_performance_summary,
    top_overstock,
    top_understock,
)
from viz_utils import (
    cost_component_stacked,
    cost_per_order_by_warehouse,
    inventory_heatmap,
    inventory_value_bar,
    on_time_by_priority,
    orders_by_warehouse_category,
    orders_over_time,
    rating_vs_delay_scatter,
    stock_cover_distribution,
)
from warehouse_optimizer import run_warehouse_optimization

st.set_page_config(
    page_title="NexGen Logistics – Warehouse Optimization",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("NexGen Logistics – Warehouse Optimization & Analytics")
st.caption(
    "Integrated analytics workspace for demand, inventory and logistics decision-making."
)


@st.cache_data(show_spinner=False)
def _load_data():
    datasets = load_all_data()
    master = create_master_orders(datasets)
    return datasets, master


def _downloadable_csv(df: pd.DataFrame) -> str:
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def _render_metrics_row(kpis: dict[str, float]):
    cols = st.columns(len(kpis))
    for col, (label, value) in zip(cols, kpis.items()):
        if "rate" in label or "ratio" in label:
            col.metric(label.replace("_", " ").title(), f"{value:.1%}")
        elif "delay" in label:
            col.metric(label.replace("_", " ").title(), f"{value:.2f} days")
        else:
            col.metric(label.replace("_", " ").title(), f"{value:,.0f}")


def _sidebar_filters(master_orders: pd.DataFrame, inventory: pd.DataFrame) -> DemandFilters:
    with st.sidebar:
        st.header("Inventory Filters")
        date_range = st.date_input(
            "Order date range",
            value=(master_orders["Order_Date"].min(), master_orders["Order_Date"].max())
            if not master_orders.empty
            else None,
        )
        start_date: Optional[pd.Timestamp] = None
        end_date: Optional[pd.Timestamp] = None
        if isinstance(date_range, tuple) and len(date_range) == 2 and all(date_range):
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1])

        warehouses = sorted(inventory["Warehouse"].unique()) if not inventory.empty else []
        selected_warehouses = st.multiselect("Warehouses", warehouses, default=warehouses)

        categories = sorted(inventory["Product_Category"].unique()) if not inventory.empty else []
        selected_categories = st.multiselect("Product Categories", categories, default=categories)
    return DemandFilters(
        start_date=start_date,
        end_date=end_date,
        warehouses=selected_warehouses,
        product_categories=selected_categories,
    )


def main() -> None:
    datasets, master_orders = _load_data()
    inventory = datasets.get("warehouse_inventory", pd.DataFrame())
    delivery = datasets.get("delivery_performance", pd.DataFrame())
    feedback = datasets.get("customer_feedback", pd.DataFrame())

    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Go to",
        (
            "Overview & KPIs",
            "Warehouse Inventory & Demand EDA",
            "Warehouse Optimization",
            "Cost & Risk Insights",
            "Customer & Service View",
        ),
    )

    st.sidebar.markdown("---")
    if not master_orders.empty:
        csv_data = _downloadable_csv(master_orders)
        st.sidebar.download_button(
            "Download master orders",
            data=csv_data,
            file_name="master_orders.csv",
            mime="text/csv",
        )

    if page == "Overview & KPIs":
        st.subheader("Network Overview")
        kpis = compute_overview_kpis(master_orders, inventory)
        _render_metrics_row(kpis)

        charts = [
            ("Orders Over Time", orders_over_time(master_orders)),
            ("Orders by Warehouse & Category", orders_by_warehouse_category(master_orders)),
            ("On-time Rate by Priority", on_time_by_priority(master_orders)),
        ]

        for title, fig in charts:
            if fig is None:
                st.info(f"{title} chart is unavailable due to insufficient data.")
            else:
                st.plotly_chart(fig, use_container_width=True)

        if not delivery.empty:
            st.subheader("Delivery Performance Snapshot")
            perf = delivery_performance_summary(delivery)
            perf_cols = st.columns(len(perf))
            for col, (label, value) in zip(perf_cols, perf.items()):
                if "rate" in label:
                    col.metric(label.replace("_", " ").title(), f"{value:.1%}")
                else:
                    col.metric(label.replace("_", " ").title(), f"{value:.2f}")

    elif page == "Warehouse Inventory & Demand EDA":
        filters = _sidebar_filters(master_orders, inventory)
        summary = compute_inventory_demand_summary(master_orders, inventory, filters=filters)

        st.subheader("Inventory vs Demand Alignment")
        heatmap = inventory_heatmap(summary, value_col="Stock_Level")
        if heatmap is not None:
            st.plotly_chart(heatmap, use_container_width=True)
        else:
            st.info("Heatmap unavailable – adjust filters.")

        demand_heatmap = inventory_heatmap(summary, value_col="avg_monthly_demand")
        if demand_heatmap is not None:
            st.plotly_chart(demand_heatmap, use_container_width=True)

        inv_value_chart = inventory_value_bar(summary)
        if inv_value_chart is not None:
            st.plotly_chart(inv_value_chart, use_container_width=True)

        stock_cover_fig = stock_cover_distribution(summary)
        if stock_cover_fig is not None:
            st.plotly_chart(stock_cover_fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Top Overstocked Combinations**")
            overstock = top_overstock(summary)
            st.dataframe(overstock)
        with col2:
            st.markdown("**Top Understocked Combinations**")
            understock = top_understock(summary)
            st.dataframe(understock)

    elif page == "Warehouse Optimization":
        st.sidebar.subheader("Optimization Controls")
        window_days = st.sidebar.slider("Demand lookback window (days)", min_value=30, max_value=180, value=90, step=15)
        safety_stock_days = st.sidebar.slider("Safety stock (days)", min_value=5, max_value=60, value=14, step=1)
        use_lp = st.sidebar.checkbox("Use linear programming (if available)", value=False)

        end_date = master_orders["Order_Date"].max() if not master_orders.empty else None
        start_date = (end_date - pd.Timedelta(days=window_days)) if end_date is not None else None
        filters = DemandFilters(start_date=start_date, end_date=end_date)

        result = run_warehouse_optimization(
            master_orders,
            inventory,
            filters=filters,
            safety_stock_days=safety_stock_days,
            use_linear_programming=use_lp,
        )

        st.subheader("Optimization Summary")
        _render_metrics_row(result.metrics)

        st.markdown("### Transfer Plan")
        if result.transfer_plan.empty:
            st.info("No transfers recommended under current assumptions.")
        else:
            st.dataframe(result.transfer_plan)
            st.download_button(
                "Download transfer plan",
                data=_downloadable_csv(result.transfer_plan),
                file_name="transfer_plan.csv",
                mime="text/csv",
            )

        st.markdown("### Reorder Recommendations")
        if result.reorder_recommendations.empty:
            st.info("No reorder actions triggered by current thresholds.")
        else:
            st.dataframe(result.reorder_recommendations)
            st.download_button(
                "Download reorder list",
                data=_downloadable_csv(result.reorder_recommendations),
                file_name="reorder_recommendations.csv",
                mime="text/csv",
            )

        with st.expander("Detailed Inventory Summary"):
            st.dataframe(result.summary)

    elif page == "Cost & Risk Insights":
        st.subheader("Cost Breakdown Across the Network")
        costs = aggregate_costs(master_orders)
        cost_chart = cost_component_stacked(costs)
        if cost_chart is not None:
            st.plotly_chart(cost_chart, use_container_width=True)
        else:
            st.info("Cost breakdown unavailable. Ensure cost data is loaded.")

        avg_cost_line = cost_per_order_by_warehouse(master_orders)
        if avg_cost_line is not None:
            st.plotly_chart(avg_cost_line, use_container_width=True)

        st.markdown(
            "Maintaining balanced inventory reduces urgent replenishment costs and protects service levels. "
            "Use transfer plans to mitigate storage hotspots and minimise risk of stockouts that lead to costly express shipments."
        )

    elif page == "Customer & Service View":
        st.subheader("Customer Feedback & Service Quality")
        if not feedback.empty:
            summary = customer_feedback_summary(feedback)
            st.dataframe(summary)
        else:
            st.info("Feedback dataset not available.")

        scatter = rating_vs_delay_scatter(master_orders)
        if scatter is not None:
            st.plotly_chart(scatter, use_container_width=True)
        else:
            st.info("Insufficient joined data to show rating vs delay trend.")

    st.sidebar.markdown("---")
    st.sidebar.caption("Developed for NexGen Logistics Pvt. Ltd.")


if __name__ == "__main__":
    main()
