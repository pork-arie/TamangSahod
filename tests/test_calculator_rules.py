"""Tests for the Part D calculator rules (D1-D6). Hand-computed from the rules supplied in the brief."""

from datetime import date
from decimal import Decimal

import pytest

from reference import calculator as calc
from reference.calculator import (
    compute_day_pay, compute_from_inputs, compute_period_pay, daily_rate_from_monthly,
    is_holiday_pay_exempt, is_nsd_exempt, qualifies_for_unworked_holiday, separation_pay,
    service_months, unworked_day_pay, years_of_service_for_separation,
)

FULL_DAY = [("08:00", "12:00"), ("13:00", "17:00")]  # 8 h with a 1 h unpaid lunch
PRESENT = [{"kind": "workday", "attendance": "present"}]


# --- D1. Monthly-paid -> daily rate ------------------------------------------------

@pytest.mark.parametrize("monthly, factor, expected", [
    (20000, 261, "919.54"),   # 240000 / 261 = 919.5402...
    (20000, 313, "766.77"),   # 240000 / 313 = 766.7731...
    (20000, 365, "657.53"),   # 240000 / 365 = 657.5342...
    (26100, 261, "1200.00"),  # 313200 / 261 = 1200 exactly
])
def test_daily_rate_from_monthly(monthly, factor, expected):
    assert daily_rate_from_monthly(monthly, factor) == Decimal(expected)


def test_daily_rate_rounding_switch(monkeypatch):
    monkeypatch.setattr(calc, "ROUND_DAILY_RATE", False)
    assert daily_rate_from_monthly(20000, 261) == Decimal(240000) / Decimal(261)


def test_daily_rate_rejects_bad_factor():
    with pytest.raises(ValueError):
        daily_rate_from_monthly(20000, 0)


# --- D2. Holiday pay exemption -------------------------------------------------------

@pytest.mark.parametrize("est, workers, category, exempt", [
    ("retail", 9, "rank_and_file", True),      # less than 10
    ("retail", 10, "rank_and_file", False),    # exactly 10 is NOT less than 10
    ("service", 3, "rank_and_file", True),
    ("other", 3, "rank_and_file", False),      # only retail/service are exempt by size
    ("other", 500, "managerial", True),
    ("other", 500, "field_personnel", True),
])
def test_is_holiday_pay_exempt(est, workers, category, exempt):
    assert is_holiday_pay_exempt(est, workers, category) is exempt


def test_holiday_exemption_needs_worker_count_for_retail():
    with pytest.raises(ValueError):
        is_holiday_pay_exempt("retail", None)


def test_exempt_worker_regular_holiday_paid_as_ordinary():
    assert compute_day_pay(640, "regular_holiday", FULL_DAY, holiday_pay_exempt=True) == Decimal("640.00")
    assert compute_day_pay(640, "double_regular_holiday", FULL_DAY, holiday_pay_exempt=True) \
        == Decimal("640.00")


def test_exempt_worker_holiday_overtime_is_ordinary_overtime():
    # 9 h straight: 640 + 1 OT h at 80 x 1.25 = 740 (author's decision: OT also as ordinary day)
    assert compute_day_pay(640, "regular_holiday", [("08:00", "17:00")], holiday_pay_exempt=True) \
        == Decimal("740.00")


def test_exempt_worker_on_plain_rest_day_keeps_rest_day_premium():
    # D2 is about holiday pay only: 640 x 1.30 = 832
    assert compute_day_pay(640, "rest_day", FULL_DAY, holiday_pay_exempt=True) == Decimal("832.00")


@pytest.mark.parametrize("day_type", ["regular_holiday_rest_day", "double_regular_holiday_rest_day",
                                      "special_non_working", "special_non_working_rest_day"])
def test_exempt_worker_unverified_combinations_raise(day_type):
    with pytest.raises(NotImplementedError):
        compute_day_pay(640, day_type, FULL_DAY, holiday_pay_exempt=True)


# --- D3. Night shift differential exemption --------------------------------------------

@pytest.mark.parametrize("est, workers, exempt", [
    ("retail", 5, True),      # not more than 5
    ("retail", 6, False),
    ("service", 1, True),
    ("other", 2, False),
])
def test_is_nsd_exempt(est, workers, exempt):
    assert is_nsd_exempt(est, workers) is exempt


def test_nsd_exempt_removes_night_premium():
    # 2 night hours on an ordinary day: 80 x 2 = 160 (instead of 176)
    assert compute_day_pay(640, "ordinary", [("22:00", "24:00")], nsd_exempt=True) == Decimal("160.00")


def test_holiday_exempt_but_not_nsd_exempt():
    # Retail store with 7 workers: holiday-exempt (7 < 10) but NOT NSD-exempt (7 > 5).
    assert is_holiday_pay_exempt("retail", 7) and not is_nsd_exempt("retail", 7)
    # Regular holiday 22:00-24:00 -> paid as ordinary night: 80 x 1.10 x 2 = 176
    assert compute_day_pay(640, "regular_holiday", [("22:00", "24:00")],
                           holiday_pay_exempt=True, nsd_exempt=False) == Decimal("176.00")


# --- D4. Unworked regular holiday ---------------------------------------------------------

@pytest.mark.parametrize("preceding, qualifies", [
    ([{"kind": "workday", "attendance": "present"}], True),
    ([{"kind": "workday", "attendance": "paid_leave"}], True),
    ([{"kind": "workday", "attendance": "absent_unpaid"}], False),
    ([{"kind": "rest_day"}, {"kind": "workday", "attendance": "present"}], True),
    ([{"kind": "rest_day"}, {"kind": "workday", "attendance": "absent_unpaid"}], False),
    ([{"kind": "non_working_day"}, {"kind": "workday", "attendance": "paid_leave"}], True),
    # only the decisive workday matters, not days further back
    ([{"kind": "workday", "attendance": "present"},
      {"kind": "workday", "attendance": "absent_unpaid"}], True),
])
def test_unworked_holiday_attendance_rule(preceding, qualifies):
    assert qualifies_for_unworked_holiday(preceding) is qualifies


def test_unworked_holiday_pay_amounts():
    assert unworked_day_pay(640, "regular_holiday", PRESENT) == Decimal("640.00")
    absent = [{"kind": "rest_day"}, {"kind": "workday", "attendance": "absent_unpaid"}]
    assert unworked_day_pay(640, "regular_holiday", absent) == Decimal("0.00")
    assert unworked_day_pay(640, "regular_holiday", PRESENT, holiday_pay_exempt=True) == Decimal("0.00")


@pytest.mark.parametrize("day_type", ["ordinary", "rest_day", "special_non_working",
                                      "special_non_working_rest_day"])
def test_other_unworked_days_pay_nothing(day_type):
    assert unworked_day_pay(640, day_type) == Decimal("0.00")


@pytest.mark.parametrize("day_type", ["regular_holiday_rest_day", "double_regular_holiday",
                                      "double_regular_holiday_rest_day"])
def test_unworked_unverified_holiday_types_raise(day_type):
    with pytest.raises(NotImplementedError):
        unworked_day_pay(640, day_type, PRESENT)


def test_unworked_holiday_bad_inputs():
    with pytest.raises(ValueError):
        qualifies_for_unworked_holiday([])
    with pytest.raises(ValueError):
        qualifies_for_unworked_holiday([{"kind": "rest_day"}])
    with pytest.raises(ValueError):
        qualifies_for_unworked_holiday([{"kind": "workday", "attendance": "late"}])
    with pytest.raises(NotImplementedError):
        qualifies_for_unworked_holiday([{"kind": "rest_day"}, {"kind": "non_working_day"},
                                        {"kind": "workday", "attendance": "present"}])


# --- D5. Period payroll -----------------------------------------------------------------------

def test_period_pay_sums_days():
    days = [
        {"label": "Mon", "day_type": "ordinary", "worked": True, "intervals": FULL_DAY},     # 640
        {"label": "Tue", "day_type": "rest_day", "worked": False},                           # 0
        {"label": "Wed", "day_type": "regular_holiday", "worked": False,
         "preceding_days": PRESENT},                                                         # 640
        {"label": "Thu", "day_type": "rest_day", "worked": True, "intervals": FULL_DAY},     # 832
    ]
    result = compute_period_pay(640, days)
    assert [r["pay"] for r in result["days"]] == [Decimal("640.00"), Decimal("0.00"),
                                                   Decimal("640.00"), Decimal("832.00")]
    assert result["total"] == Decimal("2112.00")


def test_period_rounding_mode(monkeypatch):
    # daily 610.50 -> hourly 76.3125; 1 ordinary night hour = 83.94375 per day
    day = {"day_type": "ordinary", "worked": True, "intervals": [["22:00", "23:00"]]}
    monkeypatch.setattr(calc, "ROUNDING_MODE", "per_day")
    assert compute_period_pay("610.50", [day, day])["total"] == Decimal("167.88")   # 83.94 + 83.94
    monkeypatch.setattr(calc, "ROUNDING_MODE", "per_period")
    assert compute_period_pay("610.50", [day, day])["total"] == Decimal("167.89")   # 167.8875
    monkeypatch.setattr(calc, "ROUNDING_MODE", "nonsense")
    with pytest.raises(ValueError):
        compute_period_pay("610.50", [day])


# --- D6. Separation pay ---------------------------------------------------------------------

@pytest.mark.parametrize("start, end, months", [
    ("2018-03-01", "2025-09-30", 91),   # 7 years 7 months
    ("2018-03-01", "2025-07-31", 89),   # 7 years 5 months
    ("2020-03-15", "2025-03-14", 60),   # exactly 5 years
    ("2020-03-15", "2025-03-13", 59),   # one day short of 5 years
    ("2025-01-01", "2025-01-31", 1),
    ("2025-01-01", "2025-01-30", 0),    # leftover days are ignored
])
def test_service_months(start, end, months):
    assert service_months(date.fromisoformat(start), date.fromisoformat(end)) == months


@pytest.mark.parametrize("months, years", [(91, 8), (89, 7), (90, 8), (60, 5), (5, 0), (6, 1)])
def test_fraction_of_six_months_counts_as_a_year(months, years, monkeypatch):
    monkeypatch.setattr(calc, "service_months", lambda s, e: months)
    assert years_of_service_for_separation(None, None) == years


@pytest.mark.parametrize("cause, start, end, expected", [
    # 7y7m -> 8 years
    ("redundancy", "2018-03-01", "2025-09-30", "160000.00"),            # 20000 x 8
    ("labor_saving_device", "2018-03-01", "2025-09-30", "160000.00"),
    ("retrenchment", "2018-03-01", "2025-09-30", "80000.00"),           # 10000 x 8
    ("closure_not_due_to_losses", "2018-03-01", "2025-09-30", "80000.00"),
    ("disease", "2018-03-01", "2025-09-30", "80000.00"),
    # 7y5m -> 7 years
    ("retrenchment", "2018-03-01", "2025-07-31", "70000.00"),           # 10000 x 7
    ("redundancy", "2018-03-01", "2025-07-31", "140000.00"),
    # short service: the 1-month minimum applies
    ("retrenchment", "2024-06-01", "2025-09-30", "20000.00"),           # 1y4m -> 1 yr -> 10000 < 20000
    ("retrenchment", "2025-07-01", "2025-09-30", "20000.00"),           # 3 months -> 0 yrs -> minimum
    ("redundancy", "2025-07-01", "2025-09-30", "20000.00"),
    ("closure_due_to_serious_losses", "2018-03-01", "2025-09-30", "0.00"),
])
def test_separation_pay(cause, start, end, expected):
    assert separation_pay(20000, start, end, cause) == Decimal(expected)


def test_separation_pay_bad_inputs():
    with pytest.raises(ValueError):
        separation_pay(20000, "2018-03-01", "2025-09-30", "resignation")
    with pytest.raises(ValueError):
        separation_pay(20000, "2025-09-30", "2018-03-01", "redundancy")


# --- compute_from_inputs dispatch ------------------------------------------------------------

def test_compute_from_inputs_kinds():
    assert compute_from_inputs({"daily_rate": 640, "day_type": "regular_holiday_rest_day",
                                "intervals": [["13:00", "17:00"], ["18:00", "24:00"]]}) == Decimal("2258.88")
    assert compute_from_inputs({"kind": "day", "monthly_rate": 26100, "days_factor": 261,
                                "day_type": "ordinary", "intervals": FULL_DAY}) == Decimal("1200.00")
    assert compute_from_inputs({"kind": "day", "daily_rate": 640, "day_type": "regular_holiday",
                                "intervals": [["22:00", "24:00"]],
                                "establishment": {"type": "retail", "worker_count": 7}}) == Decimal("176.00")
    assert compute_from_inputs({"kind": "unworked", "daily_rate": 640, "day_type": "regular_holiday",
                                "preceding_days": PRESENT}) == Decimal("640.00")
    assert compute_from_inputs({"kind": "period", "daily_rate": 640, "days": [
        {"day_type": "ordinary", "worked": True, "intervals": FULL_DAY}]}) == Decimal("640.00")
    assert compute_from_inputs({"kind": "separation", "monthly_rate": 20000, "start_date": "2018-03-01",
                                "end_date": "2025-09-30", "cause": "redundancy"}) == Decimal("160000.00")
    with pytest.raises(ValueError):
        compute_from_inputs({"kind": "bonus"})
