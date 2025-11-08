"""Configuration settings for the NexGen Logistics warehouse optimization app."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AppConfig:
    """Dataclass encapsulating configuration parameters used across the app."""

    date_columns: List[str] = (
        "Order_Date",
        "Promised_Delivery_Date",
        "Actual_Delivery_Date",
        "Last_Restocked_Date",
        "Feedback_Date",
    )
    stock_cover_threshold: float = 7.0  # days
    overstock_multiplier: float = 1.5
    surplus_multiplier: float = 1.2
    moving_average_window: int = 7


CONFIG = AppConfig()
