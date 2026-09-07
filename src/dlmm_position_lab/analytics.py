"""Deterministic price-range calculations used by the application."""

from collections.abc import Sequence
from itertools import pairwise

from dlmm_position_lab.models import RangeAnalysis


def analyze_range(
    prices: Sequence[float], lower_price: float, upper_price: float
) -> RangeAnalysis:
    """Summarize how a sequence of closing prices behaved within a range."""
    if not prices:
        raise ValueError("prices must not be empty")
    if lower_price >= upper_price:
        raise ValueError("lower_price must be less than upper_price")

    normalized_prices = [float(price) for price in prices]
    inside = [lower_price <= price <= upper_price for price in normalized_prices]
    exits = sum(
        was_inside and not is_inside
        for was_inside, is_inside in pairwise(inside)
    )
    current_price = normalized_prices[-1]

    return RangeAnalysis(
        current_price=current_price,
        inside_range=inside[-1],
        range_width=upper_price - lower_price,
        min_price=min(normalized_prices),
        max_price=max(normalized_prices),
        percentage_inside_range=sum(inside) / len(inside) * 100,
        number_of_range_exits=exits,
        distance_to_lower_boundary=current_price - lower_price,
        distance_to_upper_boundary=upper_price - current_price,
    )
