"""Minimal existing tests for the payments sample — intentionally incomplete."""
from tests.fixtures.sample_project.src.payments import (
    PaymentRequest,
    apply_discount,
    process_payment,
)


def test_process_payment_happy_path():
    """Basic happy path — does not cover all requirements."""
    req = PaymentRequest(amount=100.0, currency="USD", description="test")
    result = process_payment(req)
    assert result["status"] == "completed"
    assert result["amount"] == 100.0


def test_apply_discount_basic():
    """Basic discount — does not cover boundary conditions."""
    assert apply_discount(100.0, 10.0) == 90.0
