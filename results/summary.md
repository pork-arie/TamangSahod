# Results

Conditions shown: **open (rules given)**. The expected answers are the same in both.

## Overall

| Model | Condition | Pass rate | pass^k | Format failures | Truncated | Trials |
|---|---|---|---|---|---|---|
| `google/gemma-4-31b-it:free` | open | 100% (16/16) | 100% (7/7 tasks, k=1/2/3) | 0% | 0% | 16 |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | open | 100% (30/30) | 100% (10/10 tasks, k=3) | 0% | 0% | 30 |

_pass^k = share of tasks where every one of the k trials passed. Truncated = reply cut off by max_tokens (counted inside format failures)._

## Per task (passed / trials)

| Task | Difficulty | `google/gemma-4-31b-it:free` open | `nvidia/nemotron-3-ultra-550b-a55b:free` open |
|---|---|---|---|
| task_01 | medium | 3/3 | 3/3 |
| task_02 | medium | – | 3/3 |
| task_03 | hard | 2/2 | 3/3 |
| task_04 | hard | 3/3 | 3/3 |
| task_05 | hard | 2/2 | 3/3 |
| task_06 | medium | 1/1 | 3/3 |
| task_07 | hard | 2/2 | 3/3 |
| task_08 | hard | 3/3 | 3/3 |
| task_09 | hard | – | 3/3 |
| task_10 | hard | – | 3/3 |

## By difficulty

| Difficulty | tasks | `google/gemma-4-31b-it:free` open | `nvidia/nemotron-3-ultra-550b-a55b:free` open |
|---|---|---|---|
| hard | 7 | 100% | 100% |
| medium | 3 | 100% | 100% |

## By tag

_A task with several tags counts in each tag's row._

| Tag | tasks | `google/gemma-4-31b-it:free` open | `nvidia/nemotron-3-ultra-550b-a55b:free` open |
|---|---|---|---|
| absence | 2 | 100% | 100% |
| days_factor | 1 | – | 100% |
| exemption_thresholds | 1 | – | 100% |
| holiday_pay_eligibility | 2 | 100% | 100% |
| holiday_pay_exemption | 2 | 100% | 100% |
| meal_break | 6 | 100% | 100% |
| minimum_separation_pay | 1 | 100% | 100% |
| monthly_paid | 1 | – | 100% |
| multi_week_payroll | 1 | – | 100% |
| multiple_employees | 1 | – | 100% |
| night_shift | 6 | 100% | 100% |
| nsd_exemption | 2 | 100% | 100% |
| overtime | 6 | 100% | 100% |
| redundancy | 1 | 100% | 100% |
| regular_holiday | 6 | 100% | 100% |
| rest_day | 4 | 100% | 100% |
| retrenchment | 2 | 100% | 100% |
| rounding | 2 | 100% | 100% |
| separation_pay | 3 | 100% | 100% |
| special_non_working_day | 3 | 100% | 100% |
| unworked_day | 1 | 100% | 100% |
| unworked_holiday | 2 | 100% | 100% |
| weekly_payroll | 1 | 100% | 100% |
| years_of_service_fraction | 3 | 100% | 100% |

![Pass rate per model](pass_rate.png)
