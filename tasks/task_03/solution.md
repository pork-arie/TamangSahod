# task_03 — Reference solution (DRAFT, not yet verified)

**Scenario:** retail store regularly employing 7 workers; daily rate ₱610. December 25 is
a regular holiday (not a rest day). Liza worked 2:00 PM to 12:00 midnight, with an unpaid meal break 6:00–7:00 PM.

## Step 1: Which exemptions apply?

| Exemption | Rule | 7 workers | Applies? |
|---|---|---|---|
| Holiday pay | retail/service with **less than 10** workers | 7 < 10 | **yes**: pay as an ordinary day |
| Night shift differential | retail/service with **not more than 5** workers | 7 > 5 | **no**: NSD still applies |

So the day is paid as an ordinary working day (OT at 125%), **with** the night differential.

## Step 2: Hours worked

2:00–6:00 PM (4 h) + 7:00 PM–12:00 midnight (5 h) = **9 hours**.

- First 8 hours: 2:00–6:00 PM and 7:00–11:00 PM
- Overtime: 11:00 PM – 12:00 midnight
- Night hours: 10:00–11:00 PM (regular) and 11:00 PM–12:00 midnight (overtime)

## Step 3: Compute

Hourly rate = ₱610 ÷ 8 = **₱76.25**

| Hours | Multiplier | Pay |
|---|---|---|
| 7 regular day hours | 1.00 | ₱533.75 |
| 1 regular night hour | 1.10 | ₱83.875 |
| 1 overtime night hour | 1.25 × 1.10 = 1.375 | ₱104.84375 |

**Total = ₱722.46875 → ₱722.47**

```
FINAL ANSWER: ₱722.47
```

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Applies BOTH exemptions (no holiday premium, no NSD) | ₱705.31 |
| Applies NEITHER exemption (200% holiday pay + NSD) | ₱1,453.33 |
| Swaps them (holiday premium paid, NSD dropped) | ₱1,418.25 |
