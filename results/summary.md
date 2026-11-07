# Results

> **DRAFT RESULTS INCLUDED.** 1 task(s) are not yet verified against the DOLE-BWC Handbook: task_01. Do not cite these numbers as final.

## Overall

| Model | Pass rate | pass^k | Format failures | Truncated | Trials |
|---|---|---|---|---|---|
| `google/gemma-4-31b-it:free` | 100% (2/2) | 100% (1/1 tasks, k=2) | 0% | 0% | 2 |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 100% (3/3) | 100% (1/1 tasks, k=3) | 0% | 0% | 3 |

_pass^k = share of tasks where every one of the k trials passed. Truncated = reply cut off by max_tokens (counted inside format failures)._

## Per task (passed / trials)

| Task | Difficulty | `google/gemma-4-31b-it:free` | `nvidia/nemotron-3-ultra-550b-a55b:free` |
|---|---|---|---|
| task_01 (DRAFT) | medium | 2/2 | 3/3 |

## By difficulty

| Difficulty | tasks | google/gemma-4-31b-it:free | nvidia/nemotron-3-ultra-550b-a55b:free |
|---|---|---|---|
| medium | 1 | 100% | 100% |

## By tag

_A task with several tags counts in each tag's row._

| Tag | tasks | google/gemma-4-31b-it:free | nvidia/nemotron-3-ultra-550b-a55b:free |
|---|---|---|---|
| meal_break | 1 | 100% | 100% |
| night_shift | 1 | 100% | 100% |
| overtime | 1 | 100% | 100% |
| regular_holiday | 1 | 100% | 100% |
| rest_day | 1 | 100% | 100% |

![Pass rate per model](pass_rate.png)
