"""Price-range statistics calculated from user-supplied prices."""

from itertools import pairwise
from math import isfinite


def analyze_range(prices: list[float], lower: float, upper: float) -> dict:
    if not prices or not all(isfinite(p) and p > 0 for p in [*prices, lower, upper]):
        raise ValueError("Prices and boundaries must be positive, finite numbers.")
    if lower >= upper:
        raise ValueError("Lower price must be less than upper price.")
    inside = [lower <= price <= upper for price in prices]
    return {
        "current_price": prices[-1],
        "inside_range": inside[-1],
        "range_width": upper - lower,
        "min_price": min(prices),
        "max_price": max(prices),
        "percentage_inside_range": sum(inside) / len(inside) * 100,
        "number_of_range_exits": sum(a and not b for a, b in pairwise(inside)),
        "distance_to_lower_boundary": prices[-1] - lower,
        "distance_to_upper_boundary": upper - prices[-1],
    }
