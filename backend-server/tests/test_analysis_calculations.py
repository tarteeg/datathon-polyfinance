from math import isclose

import pytest

from app.modules.analysis import calculations as calc

TECH_20 = {"technology": 0.2, "financial_services": 0.8}
TECH_80 = {"technology": 0.8, "healthcare": 0.2}


def tech_after(percent: float) -> float:
    after = calc.apply_transfer({"FUND_A": 1.0}, "FUND_A", "FUND_TECH", percent / 100)
    exposure = calc.sector_exposure(after, {"FUND_A": TECH_20, "FUND_TECH": TECH_80})
    return exposure["sectors"]["technology"]


def test_organizers_case_ten_percent_transfer_gives_26_percent():
    assert isclose(tech_after(10), 0.26)


def test_organizers_case_five_percent_transfer_gives_23_percent():
    assert isclose(tech_after(5), 0.23)


def test_exposure_before_transfer_is_20_percent():
    exposure = calc.sector_exposure({"FUND_A": 1.0}, {"FUND_A": TECH_20})
    assert isclose(exposure["sectors"]["technology"], 0.2)
    assert exposure["unknown"] == 0


def test_missing_profile_is_reported_not_guessed():
    exposure = calc.sector_exposure({"FUND_A": 0.6, "MYSTERY": 0.4}, {"FUND_A": TECH_20, "MYSTERY": None})
    assert isclose(exposure["unknown"], 0.4)
    assert exposure["missingProfiles"] == ["MYSTERY"]
    assert isclose(exposure["sectors"]["technology"], 0.12)


def test_transfer_keeps_weights_summing_to_one():
    after = calc.apply_transfer({"A": 0.5, "B": 0.5}, "A", "C", 0.1)
    assert isclose(sum(after.values()), 1.0)
    assert isclose(after["A"], 0.4) and isclose(after["C"], 0.1)


def test_transfer_larger_than_the_holding_is_rejected():
    with pytest.raises(ValueError):
        calc.apply_transfer({"A": 0.05, "B": 0.95}, "A", "C", 0.1)


def test_transfer_of_a_whole_line_removes_it():
    after = calc.apply_transfer({"A": 0.3, "B": 0.7}, "A", "C", 0.3)
    assert "A" not in after


def test_concentration_of_equal_weights():
    result = calc.concentration({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25})
    assert isclose(result["herfindahl"], 0.25)
    assert isclose(result["effectiveLines"], 4)
    assert isclose(result["top3Weight"], 0.75)


def test_series_statistics_drawdown_and_recovery():
    dates = ["d0", "d1", "d2", "d3", "d4"]
    prices = [100, 120, 90, 110, 125]
    stats = calc.series_statistics(dates, prices)
    assert isclose(stats["totalReturn"], 0.25)
    assert isclose(stats["maxDrawdown"]["value"], -0.25)
    assert stats["maxDrawdown"]["peak"] == "d1"
    assert stats["maxDrawdown"]["trough"] == "d2"
    assert stats["maxDrawdown"]["recovered"] == "d4"


def test_constant_prices_have_zero_volatility():
    stats = calc.series_statistics(["a", "b", "c"], [10, 10, 10])
    assert stats["annualizedVolatility"] == 0
    assert stats["maxDrawdown"]["value"] == 0


def test_constant_weight_portfolio_averages_daily_returns():
    level = calc.constant_weight_prices({"A": [100, 110], "B": [100, 90]}, {"A": 0.5, "B": 0.5})
    assert isclose(level[-1], 100)


def test_coverage_flags_different_periods_currencies_and_missing_data():
    issues = calc.coverage_issues({
        "A": {"start": "2021-01-04", "end": "2026-11-13", "observations": 1400, "currency": "USD"},
        "B": {"start": "2024-06-03", "end": "2026-11-13", "observations": 600, "currency": "CAD"},
        "C": {"observations": 0, "currency": None},
    })
    text = " ".join(issues)
    assert "No usable price history for C" in text
    assert "2024-06-03" in text
    assert "different currencies" in text


def test_coverage_is_clean_for_matching_series():
    meta = {"start": "2021-01-04", "end": "2026-11-13", "observations": 1400, "currency": "USD"}
    assert calc.coverage_issues({"A": meta, "B": dict(meta)}) == []
