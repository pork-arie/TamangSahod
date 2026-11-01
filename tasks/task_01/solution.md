# task_01 — Reference solution

**Scenario:** daily rate ₱640; December 30 is a regular holiday and Maria's scheduled
rest day. She worked 1:00 PM to 12:00 midnight with an unpaid meal break from 5:00 PM to 6:00 PM.

## Step 1: Hours actually worked

| Interval | Hours | Counted? |
|---|---|---|
| 1:00 PM – 5:00 PM | 4 | yes |
| 5:00 PM – 6:00 PM | 1 | **no** (unpaid meal break) |
| 6:00 PM – 12:00 AM | 6 | yes |

Total hours worked = 4 + 6 = **10 hours**.

## Step 2: Split into regular hours and overtime

The first 8 hours worked are 1:00–5:00 PM (4 h) and 6:00–10:00 PM (4 h).
Overtime is the 2 hours after that: 10:00 PM – 12:00 midnight.

## Step 3: Find the night-shift hours (10:00 PM – 6:00 AM)

Only 10:00 PM – 12:00 midnight is night work. Those are the **same 2 hours** as the overtime.
None of the first 8 hours fall in the night window.

## Step 4: Compute

- Hourly rate = ₱640 ÷ 8 = **₱80.00**
- First 8 hours (regular holiday + rest day = 200% × 130% = 260%):
  ₱640 × 2.60 = **₱1,664.00**
- 2 overtime hours that are also night hours. Premiums multiply:
  ₱80 × 2.60 (holiday + rest day) × 1.30 (OT) × 1.10 (night) = ₱297.44 per hour,
  and × 2 hours = **₱594.88**

**Total = ₱1,664.00 + ₱594.88 = ₱2,258.88**

```
FINAL ANSWER: ₱2,258.88
```

## Common wrong answers (what each mistake looks like)

These come from re-running the reference calculator with the mistake built in.
They show what the grader's `fail` cases look like for this task.

| Mistake | Result |
|---|---|
| Counts the meal break as worked (11 h, 3 OT hours of which 2 are night) | ₱2,529.28 |
| Applies night differential to the basic ₱80 only, added on top (`+ 80 × 0.10 × 2`) | ₱2,220.80 |
| Forgets night differential | ₱2,204.80 |
| Forgets the OT premium (OT hours paid at 260% × 110%) | ₱2,121.60 |
