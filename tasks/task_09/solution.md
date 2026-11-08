# task_09 — Reference solution

**Scenario:** daily rate ₱720, hourly rate ₱720 ÷ 8 = **₱90.00**. Workdays are Monday to Saturday;
Sunday is the rest day. Each day is rounded to centavos, then all 14 days are added.

## Day by day

| Day | Type | Hours | Computation | Pay |
|---|---|---|---|---|
| W1 Mon | ordinary | 8 | 720 × 1.00 | ₱720.00 |
| W1 Tue | ordinary | 10 (2 OT, 5–7 PM) | 720 + 2 × 90 × 1.25 | ₱945.00 |
| W1 Wed | special day, company closed, not worked | 0 | no work, no pay | ₱0.00 |
| W1 Thu | regular holiday, not worked | 0 | eligible (see below) → 720 × 1.00 | ₱720.00 |
| W1 Fri | ordinary, absent without pay | 0 | — | ₱0.00 |
| W1 Sat | ordinary | 8 | 720 × 1.00 | ₱720.00 |
| W1 Sun | rest day | 10 (OT 10 PM–12 AM, both night hours) | 720 × 1.30 + 2 × 90 × 1.30 × 1.30 × 1.10 | ₱1,270.62 |
| W2 Mon | regular holiday, worked | 8 (night hour 10–11 PM) | 7 × 90 × 2.00 + 1 × 90 × 2.00 × 1.10 | ₱1,458.00 |
| W2 Tue | ordinary | 8 | 720 × 1.00 | ₱720.00 |
| W2 Wed | ordinary | 8 | 720 × 1.00 | ₱720.00 |
| W2 Thu | ordinary | 10 (OT 10 PM–12 AM, both night hours) | 720 + 2 × 90 × 1.25 × 1.10 | ₱967.50 |
| W2 Fri | ordinary | 8 | 720 × 1.00 | ₱720.00 |
| W2 Sat | special day, worked | 10 (2 OT, 5–7 PM) | 720 × 1.30 + 2 × 90 × 1.30 × 1.30 | ₱1,240.20 |
| W2 Sun | rest day, not worked | 0 | — | ₱0.00 |

**Week 1 Thursday: is Grace eligible?** The day immediately before the holiday (Wednesday) is a
**non-working day in the establishment** (the company was closed). So the rule looks at the workday
before that: **Tuesday**, when she was present. She is eligible for 100%. Friday's absence comes
*after* the holiday and does not matter.

**Week 1 Sunday:** the first 8 hours are 1–5 PM and 6–10 PM. 10 PM–12 AM is overtime **and** night work
on a rest day: 90 × 1.30 × 1.30 × 1.10 = ₱167.31 per hour.

**Total = ₱10,201.32**

```
FINAL ANSWER: ₱10,201.32
```

(Rounding once at the end gives the same ₱10,201.32.)

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Treats the closed Wednesday like an absence, so no holiday pay on Thursday | ₱9,481.32 |
| Pays the Week 1 Sunday rest day as an ordinary day | ₱9,898.20 |
| Forgets the night shift differential everywhere | ₱10,130.40 |
| Pays the closed special day at 100%, **or** pays the Friday absence (both give the same total) | ₱10,921.32 |
