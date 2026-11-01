"""Deterministic reference calculator for Philippine premium / holiday / OT / night pay.

Every multiplier below comes ONLY from the rules the author supplied in the
project brief. Nothing here is taken from memory of the Labor Code. Anything the
supplied rules do not cover is marked TODO and either raises an error or is
documented as an assumption, so the author can check it against the
DOLE-BWC Handbook on Workers' Statutory Monetary Benefits.

How it works (in plain words):
  1. Turn the work intervals into a list of minutes actually worked
     (unpaid meal breaks are just gaps between intervals, so they are never counted).
  2. Label each minute: is it overtime (after the first 8 hours = 480 minutes)?
     Is it night shift (10:00 PM - 6:00 AM)?
  3. Count minutes in each of the 4 buckets (regular/OT x day/night).
  4. Pay for a bucket = hourly rate x multipliers x (minutes / 60).
     Premiums MULTIPLY; they never add.
  5. Round the total to 2 decimals.

All money math uses Decimal, never float, so results are exact.

Example (task_01):
    >>> compute_day_pay(640, "regular_holiday_rest_day", [("13:00", "17:00"), ("18:00", "24:00")])
    Decimal('2258.88')
"""

from decimal import Decimal, ROUND_HALF_UP

# --- Rules supplied by the author (verify against DOLE handbook) -------------

HOURS_PER_DAY = Decimal(8)          # Hourly rate = daily rate / 8
NORMAL_MINUTES = 8 * 60             # first 8 hours worked are "regular" hours

# Multiplier on the hourly rate for the first 8 hours, by type of day.
DAY_MULTIPLIERS = {
    "ordinary": Decimal("1.00"),
    "rest_day": Decimal("1.30"),
    "special_non_working": Decimal("1.30"),
    "special_non_working_rest_day": Decimal("1.50"),
    "regular_holiday": Decimal("2.00"),
    "regular_holiday_rest_day": Decimal("2.60"),
    "double_regular_holiday": Decimal("3.00"),
    "double_regular_holiday_rest_day": Decimal("3.90"),
}

# Overtime factor applied on top of the day's hourly rate.
OT_FACTOR_ORDINARY = Decimal("1.25")     # ordinary day: hourly x 125%
OT_FACTOR_PREMIUM_DAY = Decimal("1.30")  # rest day / holiday: (hourly x day mult) x 130%

# Night shift differential: x 110% on the applicable hourly rate for that hour.
NIGHT_FACTOR = Decimal("1.10")
NIGHT_START_MINUTE = 22 * 60   # 10:00 PM
NIGHT_END_MINUTE = 6 * 60      # 6:00 AM

# TODO(verify): rounding. We round only the final total, half-up, to centavos.
# Confirm whether payroll practice / the handbook rounds per line item instead
# (this can change the result by a centavo in some tasks).
CENTAVO = Decimal("0.01")


def _to_minute(hhmm: str) -> int:
    """Convert 'HH:MM' (24-hour clock, '24:00' = midnight at end of day) to minutes since 00:00."""
    hours, minutes = hhmm.split(":")
    h, m = int(hours), int(minutes)
    if not (0 <= h <= 24 and 0 <= m < 60) or (h == 24 and m != 0):
        raise ValueError(f"Bad time {hhmm!r}; use 'HH:MM' between 00:00 and 24:00")
    return h * 60 + m


def _is_night(minute_of_day: int) -> bool:
    """True if this minute falls in the 10:00 PM - 6:00 AM night-shift window."""
    return minute_of_day >= NIGHT_START_MINUTE or minute_of_day < NIGHT_END_MINUTE


def worked_minutes(intervals):
    """Expand [("13:00","17:00"), ...] into a sorted list of minute-of-day ints worked.

    Unpaid meal breaks are simply left OUT of the intervals, so they are never counted.
    """
    minutes = []
    for start, end in intervals:
        s, e = _to_minute(start), _to_minute(end)
        if e <= s:
            # TODO(verify): shifts that cross midnight. The supplied rules do not
            # say how to treat hours that spill into the NEXT calendar day when
            # that day has a different day type (e.g. Dec 30 regular holiday ->
            # Dec 31 special day). Until that rule is verified, we refuse to guess.
            raise NotImplementedError(
                f"Interval {start}-{end} crosses midnight; next-day rules not implemented yet"
            )
        minutes.extend(range(s, e))
    if len(minutes) != len(set(minutes)):
        raise ValueError("Work intervals overlap")
    return sorted(minutes)


def hourly_rate(daily_rate) -> Decimal:
    """Hourly rate = daily rate / 8."""
    return Decimal(str(daily_rate)) / HOURS_PER_DAY


def bucket_multiplier(day_type: str, is_overtime: bool, is_night: bool) -> Decimal:
    """Total multiplier on the plain hourly rate for one hour in this bucket.

    Premiums multiply: e.g. regular holiday + rest day, OT, night
    = 2.60 x 1.30 x 1.10.
    """
    if day_type not in DAY_MULTIPLIERS:
        raise ValueError(f"Unknown day_type {day_type!r}; choose from {sorted(DAY_MULTIPLIERS)}")

    mult = DAY_MULTIPLIERS[day_type]
    if is_overtime:
        mult *= OT_FACTOR_ORDINARY if day_type == "ordinary" else OT_FACTOR_PREMIUM_DAY
    if is_night:
        mult *= NIGHT_FACTOR
    return mult


def compute_breakdown(daily_rate, day_type: str, intervals):
    """Return a dict with minutes and pay for each bucket, plus the rounded total.

    Useful for writing solution.md and for debugging a task.
    """
    rate = hourly_rate(daily_rate)
    buckets = {}  # (is_overtime, is_night) -> minutes
    for index, minute in enumerate(worked_minutes(intervals)):
        key = (index >= NORMAL_MINUTES, _is_night(minute))
        buckets[key] = buckets.get(key, 0) + 1

    lines = []
    total = Decimal(0)
    for (is_ot, is_night), mins in sorted(buckets.items()):
        mult = bucket_multiplier(day_type, is_ot, is_night)
        pay = rate * mult * Decimal(mins) / Decimal(60)
        total += pay
        lines.append({
            "overtime": is_ot,
            "night": is_night,
            "minutes": mins,
            "multiplier": mult,
            "pay": pay,
        })

    return {
        "hourly_rate": rate,
        "lines": lines,
        "total": total.quantize(CENTAVO, rounding=ROUND_HALF_UP),
    }


def compute_day_pay(daily_rate, day_type: str, intervals) -> Decimal:
    """Total pay for one work day, rounded to centavos."""
    return compute_breakdown(daily_rate, day_type, intervals)["total"]


def compute_from_inputs(inputs: dict) -> Decimal:
    """Run the calculator from a task.json "reference_inputs" block.

    Expected shape:
      {"daily_rate": 640, "day_type": "regular_holiday_rest_day",
       "intervals": [["13:00", "17:00"], ["18:00", "24:00"]]}
    """
    return compute_day_pay(inputs["daily_rate"], inputs["day_type"], inputs["intervals"])


# TODO(verify): rules NOT implemented because they were not supplied:
#   - Coverage exemptions (e.g. retail/service establishments with fewer than
#     10 workers for holiday pay; managerial employees; field personnel).
#   - Unworked holiday pay, absences before a holiday, "double holiday" edge cases.
#   - Night shift differential exemptions (e.g. small retail/service establishments).
#   - Separation pay / final pay / 13th-month proration (planned later tasks).
#   - Whether a COLA or allowance is part of the "daily rate" for premium computation.
