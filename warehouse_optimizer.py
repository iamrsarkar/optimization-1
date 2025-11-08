"""Optimization logic for warehouse stock rebalancing and reorder planning."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from config import CONFIG

try:  # Optional LP support
    import pulp
except Exception:  # pragma: no cover - optional dependency
    pulp = None


WAREHOUSE_DISTANCE_KM: Dict[str, Dict[str, float]] = {
    "Mumbai": {"Delhi": 1400, "Bangalore": 985, "Chennai": 1335, "Kolkata": 1960, "Mumbai": 0},
    "Delhi": {"Mumbai": 1400, "Bangalore": 2150, "Chennai": 2200, "Kolkata": 1500, "Delhi": 0},
    "Bangalore": {"Mumbai": 985, "Delhi": 2150, "Chennai": 350, "Kolkata": 1870, "Bangalore": 0},
    "Chennai": {"Mumbai": 1335, "Delhi": 2200, "Bangalore": 350, "Kolkata": 1670, "Chennai": 0},
    "Kolkata": {"Mumbai": 1960, "Delhi": 1500, "Bangalore": 1870, "Chennai": 1670, "Kolkata": 0},
}

TRANSFER_COST_PER_KM = 15  # INR per unit per km approximation


def _calculate_surplus_deficit(inventory: pd.DataFrame) -> pd.DataFrame:
    df = inventory.copy()
    df["Surplus"] = (df["Stock_Level"] - df["Reorder_Level"] * CONFIG.surplus_multiplier).clip(lower=0)
    df["Deficit"] = (df["Reorder_Level"] - df["Stock_Level"]).clip(lower=0)
    return df


def generate_transfer_plan(inventory: pd.DataFrame) -> pd.DataFrame:
    """Heuristic transfer suggestions between warehouses for each product."""

    if inventory.empty:
        return pd.DataFrame(columns=[
            "Product_Category",
            "From_Warehouse",
            "To_Warehouse",
            "Recommended_Transfer_Units",
            "Estimated_Transfer_Cost_INR",
        ])

    df = _calculate_surplus_deficit(inventory)
    plans: List[Dict[str, object]] = []

    for product, group in df.groupby("Product_Category"):
        surplus_df = group[group["Surplus"] > 0].sort_values("Surplus", ascending=False)
        deficit_df = group[group["Deficit"] > 0].sort_values("Deficit", ascending=False)

        if surplus_df.empty or deficit_df.empty:
            continue

        for _, deficit_row in deficit_df.iterrows():
            deficit = deficit_row["Deficit"]
            to_wh = deficit_row["Warehouse"]
            if deficit <= 0:
                continue

            # Prioritize nearest surplus warehouses for transfers
            surplus_iter = surplus_df.copy()
            surplus_iter["Distance"] = surplus_iter["Warehouse"].map(
                lambda wh: WAREHOUSE_DISTANCE_KM.get(wh, {}).get(to_wh, np.inf)
            )
            surplus_iter.sort_values(["Distance", "Surplus"], inplace=True)

            for _, surplus_row in surplus_iter.iterrows():
                surplus_idx_series = surplus_df[surplus_df.index == surplus_row.name].index
                if surplus_idx_series.empty:
                    continue
                surplus_idx = surplus_idx_series[0]
                available = surplus_df.at[surplus_idx, "Surplus"]
                if available <= 0:
                    continue
                from_wh = surplus_row["Warehouse"]
                if from_wh == to_wh:
                    continue

                transfer_units = min(available, deficit)
                distance = WAREHOUSE_DISTANCE_KM.get(from_wh, {}).get(to_wh, np.nan)
                transfer_cost = transfer_units * distance * TRANSFER_COST_PER_KM if not np.isnan(distance) else np.nan

                plans.append(
                    {
                        "Product_Category": product,
                        "From_Warehouse": from_wh,
                        "To_Warehouse": to_wh,
                        "Recommended_Transfer_Units": transfer_units,
                        "Estimated_Transfer_Cost_INR": transfer_cost,
                    }
                )

                surplus_df.at[surplus_idx, "Surplus"] -= transfer_units
                deficit -= transfer_units

                if deficit <= 0:
                    break

    plan_df = pd.DataFrame(plans)
    return plan_df


def generate_reorder_plan(inventory: pd.DataFrame) -> pd.DataFrame:
    """Recommend reorder quantities for products under critical stock levels."""

    if inventory.empty:
        return pd.DataFrame(columns=[
            "Warehouse",
            "Product_Category",
            "Potential_Reorder_Qty",
            "Storage_Cost_INR_per_unit",
        ])

    reorder_df = inventory[inventory["Potential_Reorder_Qty"] > 0].copy()
    reorder_df = reorder_df[[
        "Warehouse",
        "Product_Category",
        "Potential_Reorder_Qty",
        "Storage_Cost_INR_per_unit",
    ]]
    reorder_df.sort_values(["Potential_Reorder_Qty"], ascending=False, inplace=True)
    return reorder_df


def run_lp_optimization(inventory: pd.DataFrame) -> pd.DataFrame:
    """Optional linear programming model to minimize transfer and storage cost."""

    if inventory.empty or pulp is None:
        return pd.DataFrame()

    df = _calculate_surplus_deficit(inventory)
    surplus_nodes = df[df["Surplus"] > 0]
    deficit_nodes = df[df["Deficit"] > 0]

    if surplus_nodes.empty or deficit_nodes.empty:
        return pd.DataFrame()

    model = pulp.LpProblem("Warehouse_Rebalancing", pulp.LpMinimize)

    decision_vars: Dict[tuple, pulp.LpVariable] = {}

    for _, surplus_row in surplus_nodes.iterrows():
        for _, deficit_row in deficit_nodes.iterrows():
            if surplus_row["Warehouse"] == deficit_row["Warehouse"]:
                continue
            key = (surplus_row["Warehouse"], deficit_row["Warehouse"], surplus_row["Product_Category"])
            decision_vars[key] = pulp.LpVariable(f"x_{key[0]}_{key[1]}_{key[2]}", lowBound=0)

    # Objective: transfer cost + storage cost for remaining stock
    transfer_terms = []
    for key, var in decision_vars.items():
        from_wh, to_wh, _ = key
        distance = WAREHOUSE_DISTANCE_KM.get(from_wh, {}).get(to_wh, 1000)
        transfer_terms.append(var * distance * TRANSFER_COST_PER_KM)

    storage_cost_terms = []
    for _, row in df.iterrows():
        storage_cost_terms.append(row["Stock_Level"] * row.get("Storage_Cost_INR_per_unit", 0))

    model += pulp.lpSum(transfer_terms) + pulp.lpSum(storage_cost_terms)

    # Surplus constraints
    for _, surplus_row in surplus_nodes.iterrows():
        related_vars = [
            var
            for (from_wh, _, product), var in decision_vars.items()
            if from_wh == surplus_row["Warehouse"] and product == surplus_row["Product_Category"]
        ]
        if related_vars:
            model += pulp.lpSum(related_vars) <= surplus_row["Surplus"], f"Surplus_{surplus_row['Warehouse']}_{surplus_row['Product_Category']}"

    # Deficit constraints
    for _, deficit_row in deficit_nodes.iterrows():
        related_vars = [
            var
            for (_, to_wh, product), var in decision_vars.items()
            if to_wh == deficit_row["Warehouse"] and product == deficit_row["Product_Category"]
        ]
        if related_vars:
            model += pulp.lpSum(related_vars) >= deficit_row["Deficit"], f"Deficit_{deficit_row['Warehouse']}_{deficit_row['Product_Category']}"

    model.solve(pulp.PULP_CBC_CMD(msg=False))

    results: List[Dict[str, object]] = []
    for key, var in decision_vars.items():
        if var.value() and var.value() > 0:
            from_wh, to_wh, product = key
            distance = WAREHOUSE_DISTANCE_KM.get(from_wh, {}).get(to_wh, np.nan)
            cost = var.value() * distance * TRANSFER_COST_PER_KM if not np.isnan(distance) else np.nan
            results.append(
                {
                    "Product_Category": product,
                    "From_Warehouse": from_wh,
                    "To_Warehouse": to_wh,
                    "Optimized_Transfer_Units": var.value(),
                    "Estimated_Transfer_Cost_INR": cost,
                }
            )

    return pd.DataFrame(results)
