# task_10 — Reference solution

**Scenario:** December 25 is a regular holiday. Each of the 3 employees worked 2:00 PM to 12:00 midnight,
with an unpaid meal break from 6:00 to 7:00 PM. That is **9 hours**:
- first 8 hours: 2–6 PM and 7–11 PM (10–11 PM is a night hour);
- overtime: 11 PM–12 AM (also a night hour).

## Step 1: Which exemptions apply? (the cut-offs are the whole point)

| Business | Workers | Holiday pay exempt? (less than 10) | NSD exempt? (not more than 5) |
|---|---|---|---|
| Bakery (retail) | 5 | **yes** (5 < 10) | **yes** (5 ≤ 5) |
| Laundry (service) | 9 | **yes** (9 < 10) | **no** (9 > 5) |
| Hardware (retail) | 10 | **no** (10 is not less than 10) | **no** |

## Step 2: Compute each employee

**Ana**: hourly ₱70; ordinary day, no NSD.
- 8 regular hours × 70 = ₱560.00
- 1 OT hour × 70 × 1.25 = ₱87.50
- **₱647.50**

**Ben**: hourly ₱76.25; ordinary day, with NSD.
- 7 h × 76.25 = ₱533.75
- 1 night hour × 76.25 × 1.10 = ₱83.875
- 1 OT night hour × 76.25 × 1.25 × 1.10 = ₱104.84375
- ₱722.46875 → **₱722.47**

**Cora**: hourly ₱80.625; regular holiday, with NSD.
- 7 h × 80.625 × 2.00 = ₱1,128.75
- 1 night hour × 80.625 × 2.00 × 1.10 = ₱177.375
- 1 OT night hour × 80.625 × 2.00 × 1.30 × 1.10 = ₱230.5875
- ₱1,536.7125 → **₱1,536.71**

**Total = 647.50 + 722.47 + 1,536.71 = ₱2,906.68**

```
FINAL ANSWER: ₱2,906.68
```

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Reads "not more than 5" as "less than 5" (gives Ana the NSD) | ₱2,922.43 |
| Gives Ben holiday pay (treats 9 workers as covered) | ₱3,637.54 |
| Treats Cora's 10-worker store as exempt from holiday pay | ₱2,133.89 |
| Ignores both exemptions for everyone | ₱4,324.24 |
