# task_04 — Reference solution (DRAFT, not yet verified)

**Scenario:** daily rate ₱595, covered by holiday pay. Workdays are Monday to Saturday; Sunday is the rest day.
Friday: worked 8 hours. Saturday: absent without pay. Sunday: rest day. Monday: regular holiday, not worked.

## Step 1: Friday

8:00 AM–5:00 PM minus the 1-hour meal break = 8 hours, an ordinary day → **₱595.00**

## Step 2: Saturday and Sunday

- Saturday: absent without pay → ₱0.00
- Sunday: rest day, not worked → ₱0.00 (he is paid only for days he works)

## Step 3: Monday (unworked regular holiday). Is he eligible?

1. The day immediately before Monday is **Sunday, a rest day**.
2. So the rule looks at the workday immediately before that rest day: **Saturday**.
3. On Saturday he was **absent without pay**. That is neither present nor on paid leave.
4. So he is **not entitled** to holiday pay → ₱0.00

The trap: Friday (when he was present) is NOT the decisive day. The rule skips back over the
rest day only, not over the absence.

**Total = ₱595.00 + ₱0 + ₱0 + ₱0 = ₱595.00**

```
FINAL ANSWER: ₱595.00
```

## Common wrong answers (re-run through the calculator with one mistake each)

| Mistake | Result |
|---|---|
| Treats him as eligible (checks Friday, or ignores the absence) | ₱1,190.00 |
| Eligible, and pays the unworked holiday at 200% (two mistakes combined) | ₱1,785.00 |
