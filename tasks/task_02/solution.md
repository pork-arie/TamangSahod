# task_02 — Reference solution (DRAFT, not yet verified)

**Scenario:** monthly salary ₱25,000, days factor 261. August 21 is a special non-working
day (not a rest day). Jose worked 2:00 PM to 12:00 midnight, with an unpaid meal break 6:00–7:00 PM.

## Step 1: Daily and hourly rate

- Daily rate = ₱25,000 × 12 ÷ 261 = ₱1,149.4252… → rounded to **₱1,149.43**
- Hourly rate = ₱1,149.43 ÷ 8 = **₱143.67875**

## Step 2: Hours worked

2:00–6:00 PM (4 h) + 7:00 PM–12:00 midnight (5 h) = **9 hours**.

- First 8 hours: 2:00–6:00 PM and 7:00–11:00 PM
- Overtime: 11:00 PM – 12:00 midnight (1 h)
- Night hours (10 PM – 6 AM): 10:00–11:00 PM (regular hour) and 11:00 PM–12:00 midnight (overtime hour)

## Step 3: Compute (premiums multiply)

| Hours | Multiplier | Pay |
|---|---|---|
| 7 regular day hours | 1.30 | 7 × 143.67875 × 1.30 = ₱1,307.4766 |
| 1 regular night hour (10–11 PM) | 1.30 × 1.10 = 1.43 | ₱205.4606 |
| 1 overtime night hour (11 PM–12 AM) | 1.30 × 1.30 × 1.10 = 1.859 | ₱267.0988 |

**Total = ₱1,780.036 → ₱1,780.04**

```
FINAL ANSWER: ₱1,780.04
```

Note: if the daily rate is NOT rounded first, the result is ₱1,780.03. That is within the
₱0.01 tolerance, so both pass.

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Uses a 313-day factor instead of the given 261 | ₱1,484.31 |
| Treats the special day as an ordinary day (no 130%, OT at 125%) | ₱1,361.36 |
| Forgets the night shift differential | ₱1,737.08 |
| Overtime at 125% instead of +30% of the special-day rate | ₱1,769.76 |
