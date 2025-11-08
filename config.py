"""Configuration constants for NexGen Logistics warehouse optimization app."""
from __future__ import annotations

WAREHOUSES = [
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Chennai",
    "Kolkata",
]

CUSTOMER_SEGMENTS = ["Enterprise", "SMB", "Individual"]

PRIORITIES = ["Express", "Standard", "Economy"]

DEFAULT_SAFETY_STOCK_DAYS = 14
SURPLUS_MULTIPLIER = 1.5

# Approximate great-circle distances between warehouses in kilometres.
WAREHOUSE_DISTANCE_KM = {
    ("Mumbai", "Delhi"): 1400,
    ("Mumbai", "Bangalore"): 980,
    ("Mumbai", "Chennai"): 1330,
    ("Mumbai", "Kolkata"): 1960,
    ("Delhi", "Bangalore"): 2150,
    ("Delhi", "Chennai"): 2200,
    ("Delhi", "Kolkata"): 1500,
    ("Bangalore", "Chennai"): 350,
    ("Bangalore", "Kolkata"): 1870,
    ("Chennai", "Kolkata"): 1660,
}

DEFAULT_TRANSFER_DISTANCE_KM = 1500
TRANSFER_COST_PER_KM_PER_UNIT = 2.5
SHORTAGE_PENALTY_PER_UNIT = 150.0

CURRENCY = "INR"
DATE_FORMAT = "%d-%m-%Y"
