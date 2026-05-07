"""Sample project for Quell integration testing."""


def divide(a: float, b: float) -> float:
    """Divide a by b. Raises ValueError for division by zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def discount(price: float, pct: float) -> float:
    """Apply percentage discount. pct must be between 0 and 100."""
    if pct < 0 or pct > 100:
        raise ValueError(f"Invalid percentage: {pct}")
    return price * (1 - pct / 100)


def is_adult(age: int) -> bool:
    """Return True if age is 18 or older."""
    return age >= 18
