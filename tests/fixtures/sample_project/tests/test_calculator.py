"""Weak tests for calculator — intentionally missing edge cases for demo."""
import pytest
from src.calculator import divide, discount, is_adult


def test_divide_normal():
    assert divide(10, 2) == 5.0


def test_divide_zero():
    with pytest.raises(ValueError):
        divide(10, 0)


def test_discount_basic():
    assert discount(100, 10) == 90.0


def test_is_adult_true():
    assert is_adult(25) is True

# Missing: test_is_adult_at_boundary (age=18)
# Missing: test_discount_at_boundary (pct=0, pct=100)
# This makes these easy targets for surviving mutants
