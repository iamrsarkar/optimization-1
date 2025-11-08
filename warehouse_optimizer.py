"""Warehouse optimization logic for NexGen Logistics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from analysis_utils import DemandFilters, combine_inventory_with_demand, estimate_demand
from config import (
    DEFAULT_SAFETY_STOCK_DAYS,
    DEFAULT_TRANSFER_DISTANCE_KM,
    SHORTAGE_PENALTY_PER_UNIT,
    SURPLUS_MULTIPLIER,
    TRANSFER_COST_PER_KM_PER_UNIT,
    WAREHOUSE_DISTANCE_KM,
)

try:  # pragma: no cover - optional dependency
    import pulp
except ModuleNotFoundError:  # pragma: no cover
    pulp = None


@dataclass
class OptimizationResult:
    summary: pd.DataFrame
    transfer_plan: pd.DataFrame
    reorder_recommendations: pd.DataFrame
    metrics: Dict[str, float]


def _distance_between(warehouse_a: str, warehouse_b: str) -> float:
    if warehouse_a == warehouse_b:
        return 0.0
    if (warehouse_a, warehouse_b) in WAREHOUSE_DISTANCE_KM:
        return float(WAREHOUSE_DISTANCE_KM[(warehouse_a, warehouse_b)])
    if (warehouse_b, warehouse_a) in WAREHOUSE_DISTANCE_KM:
        return float(WAREHOUSE_DISTANCE_KM[(warehouse_b, warehouse_a)])
    return float(DEFAULT_TRANSFER_DISTANCE_KM)


def compute_transfer_cost(from_wh: str, to_wh: str, quantity: float) -> float:
    distance = _distance_between(from_wh, to_wh)
    return distance * TRANSFER_COST_PER_KM_PER_UNIT * quantity


def prepare_inventory_summary(
    master_orders: pd.DataFrame,
    inventory: pd.DataFrame,
    filters: Optional[DemandFilters] = None,
    safety_stock_days: float = DEFAULT_SAFETY_STOCK_DAYS,
    surplus_multiplier: float = SURPLUS_MULTIPLIER,
) -> pd.DataFrame:
    demand = estimate_demand(master_orders, filters)
    summary = combine_inventory_with_demand(inventory, demand, safety_stock_days, surplus_multiplier)
    return summary


def _heuristic_transfer_plan(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=[
            "Product_Category",
            "From_Warehouse",
            "To_Warehouse",
            "Transfer_Qty",
            "Estimated_Transfer_Cost",
            "Inventory_Value_Relief",
        ])

    plan_records: List[Dict[str, float | str]] = []
    summary = summary.copy()
    summary["available_to_transfer"] = summary["available_to_transfer"].clip(lower=0)
    summary["shortage_qty"] = summary["shortage_qty"].clip(lower=0)

    for product in summary["Product_Category"].unique():
        product_rows = summary[summary["Product_Category"] == product]
        surpluses = product_rows[product_rows["Classification"] == "Surplus"].copy()
        deficits = product_rows[product_rows["Classification"] == "Deficit"].copy()
        if surpluses.empty or deficits.empty:
            continue

        surpluses = surpluses.sort_values("available_to_transfer", ascending=False)
        deficits = deficits.sort_values("shortage_qty", ascending=False)

        for _, deficit in deficits.iterrows():
            needed = float(deficit["shortage_qty"])
            if needed <= 0:
                continue
            for s_idx, surplus in surpluses.iterrows():
                available = float(surplus["available_to_transfer"])
                if available <= 0:
                    continue
                transfer_qty = min(available, needed)
                if transfer_qty <= 0:
                    continue
                cost = compute_transfer_cost(surplus["Warehouse"], deficit["Warehouse"], transfer_qty)
                value_relief = transfer_qty * float(surplus.get("Storage_Cost_INR_per_unit", 0))
                plan_records.append(
                    {
                        "Product_Category": product,
                        "From_Warehouse": surplus["Warehouse"],
                        "To_Warehouse": deficit["Warehouse"],
                        "Transfer_Qty": transfer_qty,
                        "Estimated_Transfer_Cost": cost,
                        "Inventory_Value_Relief": value_relief,
                    }
                )
                needed -= transfer_qty
                summary.loc[s_idx, "available_to_transfer"] -= transfer_qty
                if needed <= 0:
                    break
            # update shortage to reflect coverage
            summary.loc[(summary["Warehouse"] == deficit["Warehouse"]) & (summary["Product_Category"] == product), "shortage_qty"] = max(needed, 0)

    if not plan_records:
        return pd.DataFrame(columns=[
            "Product_Category",
            "From_Warehouse",
            "To_Warehouse",
            "Transfer_Qty",
            "Estimated_Transfer_Cost",
            "Inventory_Value_Relief",
        ])

    plan = pd.DataFrame(plan_records)
    plan = plan.groupby(["Product_Category", "From_Warehouse", "To_Warehouse"], as_index=False).agg(
        Transfer_Qty=("Transfer_Qty", "sum"),
        Estimated_Transfer_Cost=("Estimated_Transfer_Cost", "sum"),
        Inventory_Value_Relief=("Inventory_Value_Relief", "sum"),
    )
    return plan


def _lp_transfer_plan(summary: pd.DataFrame) -> pd.DataFrame:
    if pulp is None or summary.empty:
        return pd.DataFrame()

    surpluses = summary[(summary["Classification"] == "Surplus") & (summary["available_to_transfer"] > 0)].copy()
    deficits = summary[(summary["Classification"] == "Deficit") & (summary["shortage_qty"] > 0)].copy()
    if surpluses.empty or deficits.empty:
        return pd.DataFrame()

    problem = pulp.LpProblem("Warehouse_Rebalancing", pulp.LpMinimize)

    decision_vars: Dict[tuple, pulp.LpVariable] = {}
    shortage_vars: Dict[tuple, pulp.LpVariable] = {}

    for _, deficit in deficits.iterrows():
        key = (deficit["Warehouse"], deficit["Product_Category"])
        shortage_vars[key] = pulp.LpVariable(f"shortage_{deficit['Warehouse']}_{deficit['Product_Category']}", lowBound=0)

    for _, surplus in surpluses.iterrows():
        for _, deficit in deficits.iterrows():
            if surplus["Product_Category"] != deficit["Product_Category"]:
                continue
            key = (
                surplus["Warehouse"],
                deficit["Warehouse"],
                surplus["Product_Category"],
            )
            decision_vars[key] = pulp.LpVariable("transfer_%s_%s_%s" % key, lowBound=0)

    cost_terms = []
    for key, var in decision_vars.items():
        from_wh, to_wh, _product = key
        unit_cost = compute_transfer_cost(from_wh, to_wh, 1.0)
        cost_terms.append(unit_cost * var)

    shortage_terms = []
    for key, var in shortage_vars.items():
        shortage_terms.append(SHORTAGE_PENALTY_PER_UNIT * var)

    problem += pulp.lpSum(cost_terms + shortage_terms)

    # Supply constraints
    for idx, surplus in surpluses.iterrows():
        outgoing = []
        for key, var in decision_vars.items():
            if key[0] == surplus["Warehouse"] and key[2] == surplus["Product_Category"]:
                outgoing.append(var)
        if outgoing:
            problem += pulp.lpSum(outgoing) <= float(surplus["available_to_transfer"])

    # Demand constraints
    for idx, deficit in deficits.iterrows():
        incoming = []
        for key, var in decision_vars.items():
            if key[1] == deficit["Warehouse"] and key[2] == deficit["Product_Category"]:
                incoming.append(var)
        shortage_var = shortage_vars[(deficit["Warehouse"], deficit["Product_Category"])]
        problem += pulp.lpSum(incoming) + shortage_var == float(deficit["shortage_qty"])

    problem.solve(pulp.PULP_CBC_CMD(msg=False))

    plan_records: List[Dict[str, float | str]] = []
    for key, var in decision_vars.items():
        qty = var.value() if var.value() is not None else 0.0
        if qty and qty > 0:
            from_wh, to_wh, product = key
            plan_records.append(
                {
                    "Product_Category": product,
                    "From_Warehouse": from_wh,
                    "To_Warehouse": to_wh,
                    "Transfer_Qty": qty,
                    "Estimated_Transfer_Cost": compute_transfer_cost(from_wh, to_wh, qty),
                }
            )

    plan = pd.DataFrame(plan_records)
    if plan.empty:
        return plan

    # Add inventory relief estimate using storage costs from summary
    storage_cost_lookup = summary.set_index(["Warehouse", "Product_Category"])["Storage_Cost_INR_per_unit"].to_dict()
    plan["Inventory_Value_Relief"] = plan.apply(
        lambda row: row["Transfer_Qty"] * storage_cost_lookup.get((row["From_Warehouse"], row["Product_Category"]), 0.0),
        axis=1,
    )

    plan = plan.groupby(["Product_Category", "From_Warehouse", "To_Warehouse"], as_index=False).agg(
        Transfer_Qty=("Transfer_Qty", "sum"),
        Estimated_Transfer_Cost=("Estimated_Transfer_Cost", "sum"),
        Inventory_Value_Relief=("Inventory_Value_Relief", "sum"),
    )
    return plan


def generate_reorder_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    recom = summary.copy()
    recom["Suggested_Reorder_Qty"] = np.maximum(
        recom["Reorder_Level"] - recom["Stock_Level"],
        recom["target_stock"] - recom["Stock_Level"],
    )
    recom = recom[(recom["Suggested_Reorder_Qty"] > 0) | (recom["Classification"] == "Deficit")]
    columns = [
        "Warehouse",
        "Product_Category",
        "Stock_Level",
        "Reorder_Level",
        "target_stock",
        "stock_cover_days",
        "Suggested_Reorder_Qty",
    ]
    return recom[columns].drop_duplicates().sort_values("Suggested_Reorder_Qty", ascending=False)


def run_warehouse_optimization(
    master_orders: pd.DataFrame,
    inventory: pd.DataFrame,
    filters: Optional[DemandFilters] = None,
    safety_stock_days: float = DEFAULT_SAFETY_STOCK_DAYS,
    surplus_multiplier: float = SURPLUS_MULTIPLIER,
    use_linear_programming: bool = False,
) -> OptimizationResult:
    summary = prepare_inventory_summary(
        master_orders,
        inventory,
        filters=filters,
        safety_stock_days=safety_stock_days,
        surplus_multiplier=surplus_multiplier,
    )

    if use_linear_programming:
        plan = _lp_transfer_plan(summary)
        if plan.empty:
            plan = _heuristic_transfer_plan(summary)
    else:
        plan = _heuristic_transfer_plan(summary)

    reorder = generate_reorder_recommendations(summary)

    metrics = {
        "surplus_combos": float(summary[summary["Classification"] == "Surplus"].shape[0]),
        "deficit_combos": float(summary[summary["Classification"] == "Deficit"].shape[0]),
        "transfer_plan_rows": float(plan.shape[0]),
        "reorder_rows": float(reorder.shape[0]),
        "estimated_transfer_cost_total": float(plan["Estimated_Transfer_Cost"].sum()) if not plan.empty else 0.0,
        "inventory_value_relief": float(plan.get("Inventory_Value_Relief", pd.Series(dtype=float)).sum()) if not plan.empty else 0.0,
    }

    return OptimizationResult(summary=summary, transfer_plan=plan, reorder_recommendations=reorder, metrics=metrics)
