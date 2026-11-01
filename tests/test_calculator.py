"""Calculator tests. Expected values are hand-computed from the supplied rules only."""

from decimal import Decimal

import pytest

from reference.calculator import compute_breakdown, compute_day_pay, hourly_rate

FULL_DAY = [("08:00", "12:00"), ("13:00", "17:00")]  # 8 h with a 1 h unpaid lunch


def test_seed_task_01():
    # 640 x 2.60 = 1664.00 ; 80 x 2.60 x 1.30 x 1.10 x 2 = 594.88 ; total 2258.88
    pay = compute_day_pay(640, "regular_holiday_rest_day", [("13:00", "17:00"), ("18:00", "24:00")])
    assert pay == Decimal("2258.88")


def test_seed_task_01_breakdown():
    b = compute_breakdown(640, "regular_holiday_rest_day", [("13:00", "17:00"), ("18:00", "24:00")])
    assert b["hourly_rate"] == Decimal(80)
    lines = {(l["overtime"], l["night"]): l for l in b["lines"]}
    assert lines[(False, False)]["minutes"] == 480                  # first 8 h, none at night
    assert lines[(True, True)]["minutes"] == 120                    # 2 OT h, both at night
    assert lines[(True, True)]["pay"] == Decimal("594.88")
    assert set(lines) == {(False, False), (True, True)}


def test_hourly_rate():
    assert hourly_rate(640) == Decimal(80)
    assert hourly_rate("610.50") == Decimal("76.3125")


@pytest.mark.parametrize("day_type, multiplier", [
    ("ordinary", "1.00"),
    ("rest_day", "1.30"),
    ("special_non_working", "1.30"),
    ("special_non_working_rest_day", "1.50"),
    ("regular_holiday", "2.00"),
    ("regular_holiday_rest_day", "2.60"),
    ("double_regular_holiday", "3.00"),
    ("double_regular_holiday_rest_day", "3.90"),
])
def test_first_8_hours_day_multipliers(day_type, multiplier):
    assert compute_day_pay(640, day_type, FULL_DAY) == Decimal(640) * Decimal(multiplier)


def test_meal_break_not_counted():
    # 8:00-17:00 with lunch excluded = 8 h, no OT
    assert compute_day_pay(640, "ordinary", FULL_DAY) == Decimal("640.00")
    # same span WITHOUT excluding lunch = 9 h = 8 h + 1 OT h at 125%
    assert compute_day_pay(640, "ordinary", [("08:00", "17:00")]) == Decimal("740.00")


def test_overtime_ordinary_day():
    # 8 h + 2 OT h: 640 + 80 x 1.25 x 2 = 840
    assert compute_day_pay(640, "ordinary", [("08:00", "12:00"), ("13:00", "19:00")]) == Decimal("840.00")


def test_overtime_rest_day():
    # 8 h at 130% + 1 OT h at 80 x 1.30 x 1.30 = 832 + 135.20
    assert compute_day_pay(640, "rest_day", [("08:00", "12:00"), ("13:00", "18:00")]) == Decimal("967.20")


def test_night_differential_ordinary_day():
    # 22:00-24:00 = 2 night h on an ordinary day: 80 x 1.10 x 2 = 176
    assert compute_day_pay(640, "ordinary", [("22:00", "24:00")]) == Decimal("176.00")
    # 00:00-06:00 are night hours too: 6 x 88 = 528
    assert compute_day_pay(640, "ordinary", [("00:00", "06:00")]) == Decimal("528.00")
    # 06:00 onward is not night
    assert compute_day_pay(640, "ordinary", [("06:00", "08:00")]) == Decimal("160.00")


def test_premiums_multiply_not_add():
    # regular holiday, night, not OT: 80 x 2.00 x 1.10 = 176 per hour (NOT 80 x (2.00 + 0.10) = 168)
    assert compute_day_pay(640, "regular_holiday", [("22:00", "23:00")]) == Decimal("176.00")


def test_ordinary_overtime_at_night():
    # 14:00-23:00 straight = 9 h; 8th hour ends 22:00, OT hour 22-23 is night: 80 x 1.25 x 1.10 = 110
    assert compute_day_pay(640, "ordinary", [("14:00", "23:00")]) == Decimal("750.00")


def test_partial_hours():
    # 30 minutes on an ordinary day = 40.00
    assert compute_day_pay(640, "ordinary", [("09:00", "09:30")]) == Decimal("40.00")


def test_rejects_unknown_day_type():
    with pytest.raises(ValueError):
        compute_day_pay(640, "holiday", FULL_DAY)


def test_rejects_overlapping_intervals():
    with pytest.raises(ValueError):
        compute_day_pay(640, "ordinary", [("08:00", "12:00"), ("11:00", "13:00")])


def test_crossing_midnight_not_implemented():
    # See TODO in calculator.py: next-day day-type rules are not supplied yet.
    with pytest.raises(NotImplementedError):
        compute_day_pay(640, "ordinary", [("22:00", "02:00")])
