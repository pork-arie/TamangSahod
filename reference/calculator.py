"""Deterministic reference calculator for Philippine pay computations.

Every rule below comes ONLY from the rules the author supplied in the project
brief. Nothing here is taken from memory of the Labor Code. Each rule's
constants carry a "# SOURCE:" comment citing the
DOLE-BWC Handbook on Workers' Statutory Monetary Benefits. Anything the
supplied rules do not cover raises NotImplementedError instead of guessing.

What it can compute:
  1. Pay for one work day             compute_day_pay()
     (day-type premiums, overtime, night shift differential, meal breaks,
      holiday-pay and night-differential exemptions)
  2. Pay for an UNWORKED day          unworked_day_pay()
  3. Pay for several days (a week)    compute_period_pay()
  4. Daily rate of a monthly-paid employee   daily_rate_from_monthly()
  5. Separation pay (authorized causes)      separation_pay()

How a worked day is computed (in plain words):
  1. Turn the work intervals into a list of minutes actually worked
     (unpaid meal breaks are gaps between intervals, so they are never counted).
  2. Label each minute: is it overtime (after the first 8 hours = 480 minutes)?
     Is it night shift (10:00 PM - 6:00 AM)?
  3. Count minutes in each of the 4 buckets (regular/OT x day/night).
  4. Pay for a bucket = hourly rate x multipliers x (minutes / 60).
     Premiums MULTIPLY; they never add.

All money math uses Decimal, never float, so results are exact.

Example (task_01):
    >>> compute_day_pay(640, "regular_holiday_rest_day", [("13:00", "17:00"), ("18:00", "24:00")])
    Decimal('2258.88')
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")

# =============================================================================
# RULES (each block must be verified against the DOLE-BWC Handbook)
# =============================================================================

# --- Hourly rate --------------------------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 1 C (8-hour normal day), p. 7; Ch. 4 C ("hourly rate of the basic wage"), p. 23
HOURS_PER_DAY = Decimal(8)          # Hourly rate = daily rate / 8
NORMAL_MINUTES = 8 * 60             # first 8 hours worked are "regular" hours

# --- Day-type multipliers for the first 8 hours ------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Compliance Guide A (table of rates), p. 2; Ch. 2 D, pp. 17-18; Ch. 3 D, pp. 21-22
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
REGULAR_HOLIDAY_TYPES = {"regular_holiday", "regular_holiday_rest_day",
                         "double_regular_holiday", "double_regular_holiday_rest_day"}
SPECIAL_DAY_TYPES = {"special_non_working", "special_non_working_rest_day"}

# --- Overtime ----------------------------------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 4 C. Overtime Pay Rates, p. 23; Compliance Guide A, pp. 2-3
OT_FACTOR_ORDINARY = Decimal("1.25")     # ordinary day: hourly x 125%
OT_FACTOR_PREMIUM_DAY = Decimal("1.30")  # rest day / holiday: (hourly x day mult) x 130%

# --- Night shift differential ---------------------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 5 A and C, pp. 25-26; Compliance Guide A (premiums multiply), pp. 2-3
NIGHT_FACTOR = Decimal("1.10")           # x 110% on the applicable hourly rate for that hour
NIGHT_START_MINUTE = 22 * 60             # 10:00 PM
NIGHT_END_MINUTE = 6 * 60                # 6:00 AM

# --- D1. Monthly-paid employee -> daily rate ---------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 1 D-E (EEMR = daily rate x factor / 12; factors 365, 313, 261), pp. 9-11.
# NOTE: the Handbook lists 313 and 261 under DAILY-paid employees and uses 365 for monthly-paid.
# daily_rate = (monthly_rate x 12) / days_factor. days_factor (e.g. 313, 261, 365) is
# GIVEN by each task; the calculator never chooses it.
MONTHS_PER_YEAR = 12
# Author's decision (2026-11-07): round the daily rate to centavos before using it,
# and say so in the task prompt.
ROUND_DAILY_RATE = True

# --- D2. Holiday pay coverage exemption -------------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 2 B. Coverage, pp. 16-17; Compliance Guide table, p. 1.
# NOTE: the Handbook also excludes managerial employees and field personnel from premium pay,
# overtime (Ch. 3 B, Ch. 4 B, pp. 20-23) and NSD (Ch. 5 B, pp. 25-26). This calculator only applies
# the holiday-pay exclusion to them; no task uses those categories.
# Retail and service establishments regularly employing LESS THAN 10 workers are
# exempt; managerial employees and field personnel are exempt.
HOLIDAY_EXEMPT_ESTABLISHMENT_TYPES = {"retail", "service"}
HOLIDAY_EXEMPT_IF_WORKERS_LESS_THAN = 10
HOLIDAY_EXEMPT_EMPLOYEE_CATEGORIES = {"managerial", "field_personnel"}

# --- D3. Night shift differential exemption ---------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 5 B. Coverage, p. 25; Compliance Guide table, p. 1
# Retail and service establishments regularly employing NOT MORE THAN 5 workers are exempt.
NSD_EXEMPT_ESTABLISHMENT_TYPES = {"retail", "service"}
NSD_EXEMPT_IF_WORKERS_AT_MOST = 5

# --- D4. Unworked regular holiday ---------------------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 2 D. Holiday Pay Rates, p. 17, and E. Absences (items 1 and 3), p. 18
# Covered employees get 100% of the daily rate if present, or on leave with pay, on the
# workday immediately preceding the holiday. If the day immediately preceding is a
# non-working day or rest day, look at the workday immediately before THAT day.
UNWORKED_REGULAR_HOLIDAY_MULTIPLIER = Decimal("1.00")
ATTENDANCE_THAT_QUALIFIES = {"present", "paid_leave"}
ATTENDANCE_VALUES = {"present", "paid_leave", "absent_unpaid"}

# --- D5. Multi-day (period) payroll --------------------------------------------------------
# SOURCE: none - the Handbook gives no rounding rule. This is a convention stated in each prompt.
# "per_day":    round each day's pay to centavos, then add the days up.
# "per_period": add up the exact day amounts, then round the total once.
ROUNDING_MODE = "per_day"

# --- D6. Separation pay (authorized causes) -----------------------------------------------
# SOURCE: DOLE-BWC Handbook on Workers' Statutory Monetary Benefits, 2024 Ed., Ch. 14 C. Amount, pp. 45-46. NOTE: "closure due to serious losses = 0" is not
# stated in the Handbook (it only lists the causes that DO get separation pay); no task uses it.
# A fraction of AT LEAST 6 months counts as one whole year of service.
SEPARATION_FRACTION_MONTHS_FOR_FULL_YEAR = 6
# Per year of service, as a fraction of one month's pay. Minimum is always 1 month pay.
SEPARATION_PAY_PER_YEAR = {
    "labor_saving_device": Decimal("1"),        # 1 month pay x years
    "redundancy": Decimal("1"),
    "retrenchment": Decimal("0.5"),             # half-month pay x years
    "closure_not_due_to_losses": Decimal("0.5"),
    "disease": Decimal("0.5"),
}
SEPARATION_MINIMUM_MONTHS = Decimal("1")
NO_SEPARATION_PAY_CAUSES = {"closure_due_to_serious_losses"}

# NOT IMPLEMENTED (raise NotImplementedError; verify before adding):
#   - shifts crossing midnight, retirement pay, 13th month pay
#   - exempt employee working a holiday that is also a rest day, or a special day
#   - unworked regular holiday that is also a rest day; unworked double holiday
#   - unworked special day paid by company policy / CBA
#   - more than one non-working day/rest day before an unworked holiday
#   - whether COLA/allowances are part of the daily rate


# =============================================================================
# Helpers
# =============================================================================

def _money(value) -> Decimal:
    return Decimal(str(value))


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENTAVO, rounding=ROUND_HALF_UP)


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


def _check_day_type(day_type: str):
    if day_type not in DAY_MULTIPLIERS:
        raise ValueError(f"Unknown day_type {day_type!r}; choose from {sorted(DAY_MULTIPLIERS)}")


# =============================================================================
# D1. Daily rate of a monthly-paid employee
# =============================================================================

def daily_rate_from_monthly(monthly_rate, days_factor) -> Decimal:
    """daily_rate = (monthly_rate x 12) / days_factor  (days_factor is given by the task)."""
    days_factor = int(days_factor)
    if days_factor <= 0:
        raise ValueError("days_factor must be a positive number of days")
    rate = _money(monthly_rate) * MONTHS_PER_YEAR / Decimal(days_factor)
    return _round(rate) if ROUND_DAILY_RATE else rate


def hourly_rate(daily_rate) -> Decimal:
    """Hourly rate = daily rate / 8."""
    return _money(daily_rate) / HOURS_PER_DAY


# =============================================================================
# D2 / D3. Exemptions
# =============================================================================

def is_holiday_pay_exempt(establishment_type="other", worker_count=None,
                          employee_category="rank_and_file") -> bool:
    """True if the employee is exempt from holiday pay (rule D2)."""
    if employee_category in HOLIDAY_EXEMPT_EMPLOYEE_CATEGORIES:
        return True
    if establishment_type in HOLIDAY_EXEMPT_ESTABLISHMENT_TYPES:
        if worker_count is None:
            raise ValueError("worker_count is needed to decide the retail/service exemption")
        return worker_count < HOLIDAY_EXEMPT_IF_WORKERS_LESS_THAN
    return False


def is_nsd_exempt(establishment_type="other", worker_count=None) -> bool:
    """True if the employer is exempt from night shift differential (rule D3)."""
    if establishment_type in NSD_EXEMPT_ESTABLISHMENT_TYPES:
        if worker_count is None:
            raise ValueError("worker_count is needed to decide the retail/service exemption")
        return worker_count <= NSD_EXEMPT_IF_WORKERS_AT_MOST
    return False


def _effective_day_type(day_type: str, holiday_pay_exempt: bool) -> str:
    """Day type actually used for pay, after the holiday-pay exemption (rule D2)."""
    if not holiday_pay_exempt:
        return day_type
    if day_type in ("regular_holiday", "double_regular_holiday"):
        return "ordinary"  # exempt: a worked regular holiday is paid as an ordinary day
    if day_type in ("regular_holiday_rest_day", "double_regular_holiday_rest_day"):
        # TODO(verify): does the rest-day premium still apply to an exempt worker?
        raise NotImplementedError("Exempt employee working a regular holiday that is also a rest day")
    if day_type in SPECIAL_DAY_TYPES:
        # TODO(verify): does the special-day premium apply to a holiday-pay-exempt worker?
        raise NotImplementedError("Holiday-pay-exempt employee working a special non-working day")
    return day_type  # ordinary days and plain rest days are not affected by D2


# =============================================================================
# Worked day
# =============================================================================

def worked_minutes(intervals):
    """Expand [("13:00","17:00"), ...] into a sorted list of minute-of-day ints worked.

    Unpaid meal breaks are simply left OUT of the intervals, so they are never counted.
    """
    minutes = []
    for start, end in intervals:
        s, e = _to_minute(start), _to_minute(end)
        if e <= s:
            # TODO(verify): shifts that cross midnight into a day with another day type.
            raise NotImplementedError(
                f"Interval {start}-{end} crosses midnight; next-day rules not implemented yet"
            )
        minutes.extend(range(s, e))
    if len(minutes) != len(set(minutes)):
        raise ValueError("Work intervals overlap")
    return sorted(minutes)


def bucket_multiplier(day_type: str, is_overtime: bool, is_night: bool,
                      nsd_exempt: bool = False) -> Decimal:
    """Total multiplier on the plain hourly rate for one hour in this bucket.

    Premiums multiply: e.g. regular holiday + rest day, OT, night = 2.60 x 1.30 x 1.10.
    """
    _check_day_type(day_type)
    mult = DAY_MULTIPLIERS[day_type]
    if is_overtime:
        mult *= OT_FACTOR_ORDINARY if day_type == "ordinary" else OT_FACTOR_PREMIUM_DAY
    if is_night and not nsd_exempt:
        mult *= NIGHT_FACTOR
    return mult


def compute_breakdown(daily_rate, day_type: str, intervals,
                      holiday_pay_exempt: bool = False, nsd_exempt: bool = False):
    """Minutes and pay for each bucket of one worked day, plus the exact and rounded total."""
    _check_day_type(day_type)
    pay_type = _effective_day_type(day_type, holiday_pay_exempt)
    rate = hourly_rate(daily_rate)

    buckets = {}  # (is_overtime, is_night) -> minutes
    for index, minute in enumerate(worked_minutes(intervals)):
        key = (index >= NORMAL_MINUTES, _is_night(minute))
        buckets[key] = buckets.get(key, 0) + 1

    lines = []
    exact = Decimal(0)
    for (is_ot, is_night), mins in sorted(buckets.items()):
        mult = bucket_multiplier(pay_type, is_ot, is_night, nsd_exempt)
        pay = rate * mult * Decimal(mins) / Decimal(60)
        exact += pay
        lines.append({"overtime": is_ot, "night": is_night, "minutes": mins,
                      "multiplier": mult, "pay": pay})

    return {"hourly_rate": rate, "pay_day_type": pay_type, "lines": lines,
            "exact_total": exact, "total": _round(exact)}


def compute_day_pay(daily_rate, day_type: str, intervals,
                    holiday_pay_exempt: bool = False, nsd_exempt: bool = False) -> Decimal:
    """Total pay for one worked day, rounded to centavos."""
    return compute_breakdown(daily_rate, day_type, intervals, holiday_pay_exempt, nsd_exempt)["total"]


# =============================================================================
# D4. Unworked day
# =============================================================================

def qualifies_for_unworked_holiday(preceding_days) -> bool:
    """Attendance test for an unworked regular holiday (rule D4).

    preceding_days lists the days BEFORE the holiday, nearest first, e.g.
      [{"kind": "rest_day"}, {"kind": "workday", "attendance": "absent_unpaid"}]
    kind is "workday", "rest_day" or "non_working_day"; workdays need attendance
    "present", "paid_leave" or "absent_unpaid".
    """
    if not preceding_days:
        raise ValueError("preceding_days is needed to decide holiday pay eligibility")
    first = preceding_days[0]
    if first["kind"] == "workday":
        decisive = first
    elif first["kind"] in ("rest_day", "non_working_day"):
        if len(preceding_days) < 2:
            raise ValueError("Need the workday before the rest/non-working day")
        decisive = preceding_days[1]
        if decisive["kind"] != "workday":
            # TODO(verify): two or more non-working days in a row before the holiday.
            raise NotImplementedError("More than one rest/non-working day before the holiday")
    else:
        raise ValueError(f"Unknown day kind {first['kind']!r}")

    attendance = decisive.get("attendance")
    if attendance not in ATTENDANCE_VALUES:
        raise ValueError(f"attendance must be one of {sorted(ATTENDANCE_VALUES)}, got {attendance!r}")
    return attendance in ATTENDANCE_THAT_QUALIFIES


def unworked_day_pay(daily_rate, day_type: str, preceding_days=None,
                     holiday_pay_exempt: bool = False) -> Decimal:
    """Pay for a day the employee did NOT work (daily-paid employee)."""
    _check_day_type(day_type)
    if day_type in ("ordinary", "rest_day"):
        return Decimal("0.00")  # no work, no pay (author's decision 2026-11-07)
    if day_type in SPECIAL_DAY_TYPES:
        return Decimal("0.00")  # no work, no pay (a company policy/CBA could change this; not modelled)
    if day_type != "regular_holiday":
        # TODO(verify): unworked regular holiday on a rest day; unworked double holiday.
        raise NotImplementedError(f"Unworked {day_type} is not implemented")
    if holiday_pay_exempt:
        return Decimal("0.00")  # exempt: nothing if unworked
    if not qualifies_for_unworked_holiday(preceding_days):
        return Decimal("0.00")
    return _round(_money(daily_rate) * UNWORKED_REGULAR_HOLIDAY_MULTIPLIER)


# =============================================================================
# D5. Period (weekly) payroll
# =============================================================================

def compute_period_pay(daily_rate, days, holiday_pay_exempt=False, nsd_exempt=False):
    """Pay for several days. Each day is a dict:

      {"label": "Mon", "day_type": "ordinary", "worked": True,
       "intervals": [["08:00","12:00"], ["13:00","17:00"]]}
      {"label": "Thu", "day_type": "regular_holiday", "worked": False,
       "preceding_days": [{"kind": "workday", "attendance": "present"}]}

    Returns {"days": [{"label", "day_type", "worked", "exact", "pay"}...], "total"}.
    Rounding follows ROUNDING_MODE.
    """
    rows = []
    for day in days:
        if day["worked"]:
            b = compute_breakdown(daily_rate, day["day_type"], day["intervals"],
                                  holiday_pay_exempt, nsd_exempt)
            exact = b["exact_total"]
        else:
            exact = unworked_day_pay(daily_rate, day["day_type"], day.get("preceding_days"),
                                     holiday_pay_exempt)
        rows.append({"label": day.get("label", ""), "day_type": day["day_type"],
                     "worked": day["worked"], "exact": exact, "pay": _round(exact)})

    if ROUNDING_MODE == "per_day":
        total = sum((r["pay"] for r in rows), Decimal(0))
    elif ROUNDING_MODE == "per_period":
        total = _round(sum((r["exact"] for r in rows), Decimal(0)))
    else:
        raise ValueError(f"Unknown ROUNDING_MODE {ROUNDING_MODE!r}")
    return {"days": rows, "total": _round(total)}


# =============================================================================
# D6. Separation pay
# =============================================================================

def service_months(start_date: date, end_date: date) -> int:
    """Complete calendar months from start_date through end_date (end_date is the LAST day worked).

    Author's decision (2026-11-07): count whole calendar months only and ignore
    leftover days. Example: 2018-03-01 .. 2025-09-30 = 7 years 7 months = 91 months.
    """
    if end_date < start_date:
        raise ValueError("end_date is before start_date")
    stop = end_date + timedelta(days=1)  # employment ends at the END of end_date
    months = (stop.year - start_date.year) * 12 + (stop.month - start_date.month)
    if stop.day < start_date.day:
        months -= 1  # the last month is not complete
    return months


def years_of_service_for_separation(start_date: date, end_date: date) -> int:
    """Whole years, where a leftover fraction of at least 6 months counts as 1 year."""
    years, extra_months = divmod(service_months(start_date, end_date), 12)
    if extra_months >= SEPARATION_FRACTION_MONTHS_FOR_FULL_YEAR:
        years += 1
    return years


def separation_pay(monthly_rate, start_date, end_date, cause: str) -> Decimal:
    """Separation pay for an authorized cause (rule D6)."""
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if cause in NO_SEPARATION_PAY_CAUSES:
        return Decimal("0.00")
    if cause not in SEPARATION_PAY_PER_YEAR:
        raise ValueError(f"Unknown cause {cause!r}; choose from "
                         f"{sorted(set(SEPARATION_PAY_PER_YEAR) | NO_SEPARATION_PAY_CAUSES)}")

    month_pay = _money(monthly_rate)
    years = years_of_service_for_separation(start_date, end_date)
    by_years = month_pay * SEPARATION_PAY_PER_YEAR[cause] * years
    minimum = month_pay * SEPARATION_MINIMUM_MONTHS
    return _round(max(minimum, by_years))


# =============================================================================
# Entry point used by task.json "reference_inputs"
# =============================================================================

def _daily_rate_from_inputs(inputs: dict) -> Decimal:
    if "daily_rate" in inputs:
        return _money(inputs["daily_rate"])
    return daily_rate_from_monthly(inputs["monthly_rate"], inputs["days_factor"])


def _exemptions_from_inputs(inputs: dict):
    est = inputs.get("establishment", {})
    est_type = est.get("type", "other")
    workers = est.get("worker_count")
    category = inputs.get("employee_category", "rank_and_file")
    return (is_holiday_pay_exempt(est_type, workers, category),
            is_nsd_exempt(est_type, workers))


def compute_from_inputs(inputs: dict) -> Decimal:
    """Run the calculator from a task.json "reference_inputs" block.

    "kind" picks the computation ("day" if missing, for task_01):
      day:        {"daily_rate" | "monthly_rate"+"days_factor", "day_type", "intervals",
                   optional "establishment": {"type", "worker_count"}, "employee_category"}
      unworked:   {..rate.., "day_type", "preceding_days", optional establishment/category}
      period:     {..rate.., "days": [...], optional establishment/category}
      separation: {"monthly_rate", "start_date", "end_date", "cause"}
    """
    kind = inputs.get("kind", "day")
    if kind not in ("day", "unworked", "period", "separation"):
        raise ValueError(f"Unknown reference_inputs kind {kind!r}")
    if kind == "separation":
        return separation_pay(inputs["monthly_rate"], inputs["start_date"],
                              inputs["end_date"], inputs["cause"])

    rate = _daily_rate_from_inputs(inputs)
    holiday_exempt, nsd_exempt = _exemptions_from_inputs(inputs)
    if kind == "day":
        return compute_day_pay(rate, inputs["day_type"], inputs["intervals"], holiday_exempt, nsd_exempt)
    if kind == "unworked":
        return unworked_day_pay(rate, inputs["day_type"], inputs.get("preceding_days"), holiday_exempt)
    return compute_period_pay(rate, inputs["days"], holiday_exempt, nsd_exempt)["total"]  # "period"
