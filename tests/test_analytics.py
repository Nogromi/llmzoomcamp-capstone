import pytest

from dlmm_position_lab.analytics import analyze_range


def test_analyze_range_summarizes_prices() -> None:
    analysis = analyze_range([100, 105, 111, 108, 99], 100, 110)

    assert analysis.current_price == 99
    assert analysis.inside_range is False
    assert analysis.range_width == 10
    assert analysis.min_price == 99
    assert analysis.max_price == 111
    assert analysis.percentage_inside_range == pytest.approx(60)
    assert analysis.number_of_range_exits == 2
    assert analysis.distance_to_lower_boundary == -1
    assert analysis.distance_to_upper_boundary == 11


def test_analyze_range_accepts_boundary_prices() -> None:
    analysis = analyze_range([100, 110], 100, 110)

    assert analysis.percentage_inside_range == 100
    assert analysis.inside_range is True
    assert analysis.number_of_range_exits == 0
