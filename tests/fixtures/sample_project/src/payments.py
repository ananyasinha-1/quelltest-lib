"""
Sample project for Quell integration tests.
Rich docstrings + Pydantic model — exercises all readers.
"""
from typing import Literal
from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):
    """Pydantic model — TypeReader extracts 3 requirements from this."""
    amount: float = Field(gt=0)
    currency: Literal["USD", "EUR", "GBP"]
    description: str = Field(min_length=1, max_length=500)


def process_payment(request: PaymentRequest) -> dict:  # type: ignore[type-arg]
    """
    Process a payment transaction.

    Args:
        request: PaymentRequest. Amount must be greater than 0.
                 Currency must be one of: USD, EUR, GBP.

    Returns:
        dict with transaction_id (str), status ("completed"), amount (float).

    Raises:
        ValueError: If amount is zero or negative.
        ValueError: If currency is not supported.
    """
    if request.amount <= 0:
        raise ValueError(f"Amount must be positive, got {request.amount}")
    return {
        "transaction_id": "txn_12345",
        "status": "completed",
        "amount": request.amount,
    }


def apply_discount(price: float, percentage: float) -> float:
    """
    Apply percentage discount to price.

    Args:
        price: Must be positive.
        percentage: Must be between 0 and 100 inclusive.

    Returns:
        Discounted price as float.

    Raises:
        ValueError: If percentage not between 0 and 100.
        ValueError: If price is negative.
    """
    if not 0 <= percentage <= 100:
        raise ValueError(f"Percentage must be 0-100, got {percentage}")
    if price < 0:
        raise ValueError(f"Price cannot be negative")
    return price * (1 - percentage / 100)
