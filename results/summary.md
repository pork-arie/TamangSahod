# Results

## Overall

| Model | Pass rate | pass^k | Format failures | Truncated | Trials |
|---|---|---|---|---|---|
| `google/gemma-4-31b-it:free` | 100% (14/14) | 100% (7/7 tasks, k=1/2/3) | 0% | 0% | 14 |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 100% (21/21) | 100% (7/7 tasks, k=3) | 0% | 0% | 21 |

_pass^k = share of tasks where every one of the k trials passed. Truncated = reply cut off by max_tokens (counted inside format failures)._

## Per task (passed / trials)

| Task | Difficulty | `google/gemma-4-31b-it:free` | `nvidia/nemotron-3-ultra-550b-a55b:free` |
|---|---|---|---|
| task_01 | medium | 3/3 | 3/3 |
| task_03 | hard | 2/2 | 3/3 |
| task_04 | hard | 3/3 | 3/3 |
| task_05 | hard | 2/2 | 3/3 |
| task_06 | medium | 1/1 | 3/3 |
| task_07 | hard | 2/2 | 3/3 |
| task_08 | hard | 1/1 | 3/3 |

## By difficulty

| Difficulty | tasks | google/gemma-4-31b-it:free | nvidia/nemotron-3-ultra-550b-a55b:free |
|---|---|---|---|
| hard | 5 | 100% | 100% |
| medium | 2 | 100% | 100% |

## By tag

_A task with several tags counts in each tag's row._

| Tag | tasks | google/gemma-4-31b-it:free | nvidia/nemotron-3-ultra-550b-a55b:free |
|---|---|---|---|
| absence | 1 | 100% | 100% |
| holiday_pay_eligibility | 1 | 100% | 100% |
| holiday_pay_exemption | 1 | 100% | 100% |
| meal_break | 3 | 100% | 100% |
| minimum_separation_pay | 1 | 100% | 100% |
| night_shift | 3 | 100% | 100% |
| nsd_exemption | 1 | 100% | 100% |
| overtime | 3 | 100% | 100% |
| redundancy | 1 | 100% | 100% |
| regular_holiday | 4 | 100% | 100% |
| rest_day | 3 | 100% | 100% |
| retrenchment | 2 | 100% | 100% |
| rounding | 1 | 100% | 100% |
| separation_pay | 3 | 100% | 100% |
| special_non_working_day | 1 | 100% | 100% |
| unworked_day | 1 | 100% | 100% |
| unworked_holiday | 1 | 100% | 100% |
| weekly_payroll | 1 | 100% | 100% |
| years_of_service_fraction | 3 | 100% | 100% |

![Pass rate per model](pass_rate.png)
