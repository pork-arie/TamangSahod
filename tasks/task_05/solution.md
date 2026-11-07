# task_05 — Reference solution (DRAFT, not yet verified)

**Scenario:** daily rate ₱645, rest day Saturday. Hourly rate = ₱645 ÷ 8 = **₱80.625**.

## Day by day (each day rounded to centavos, then added)

| Day | Type | Hours worked | Computation | Pay |
|---|---|---|---|---|
| Mon | ordinary | 8 | ₱645 × 1.00 | ₱645.00 |
| Tue | ordinary | 8 | ₱645 × 1.00 | ₱645.00 |
| Wed | special non-working, not worked | 0 | no work, no pay | ₱0.00 |
| Thu | regular holiday | 8 (2–6 PM, 7–11 PM) | see below | ₱1,306.13 |
| Fri | ordinary | 8 | ₱645 × 1.00 | ₱645.00 |
| Sat | rest day | 10 (8–12, 1–7 PM) | see below | ₱1,111.01 |
| Sun | ordinary | 8 | ₱645 × 1.00 | ₱645.00 |

**Thursday (regular holiday, 1 night hour from 10–11 PM, no overtime):**
- 7 h × 80.625 × 2.00 = ₱1,128.75
- 1 h × 80.625 × 2.00 × 1.10 = ₱177.375
- Day total ₱1,306.125 → **₱1,306.13**

**Saturday (rest day, 8 regular hours + 2 OT hours from 5–7 PM, no night hours):**
- 8 h × 80.625 × 1.30 = ₱838.50
- 2 h × 80.625 × 1.30 × 1.30 = ₱272.5125
- Day total ₱1,111.0125 → **₱1,111.01**

**Week total = 645 × 4 + 1,306.13 + 1,111.01 = ₱4,997.14**

```
FINAL ANSWER: ₱4,997.14
```

(Rounding once at the end gives ₱4,997.1375 → ₱4,997.14, the same answer.)

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Pays the unworked special day at 100% | ₱5,642.14 |
| Counts Saturday's meal break as worked (11 h, 3 OT) | ₱5,133.40 |
| Forgets the night shift differential on Thursday | ₱4,981.01 |
