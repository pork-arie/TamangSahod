# PH Payroll Eval

A small, reproducible eval of where frontier AI models fail at **Philippine payroll
and labor-compliance computations**: premium pay, holiday pay, overtime, night shift
differential, and (planned) separation and final pay.

> Fill in every `TODO` before submitting.

---

## What the eval tests

Each task gives the model a realistic payroll scenario **and the exact rules it needs**,
quoted from the DOLE-BWC *Handbook on Workers' Statutory Monetary Benefits*. Because the
rules are in the prompt, this tests **multi-step reasoning over the rules**, not recall of
Philippine law. That includes stacking multipliers, excluding unpaid breaks, and spotting
which hours are overtime and which are night hours.

## Why it matters

TODO: e.g. payroll errors on holiday, OT, and night premiums are a common source of labor
complaints and back-pay liability. SMEs and HR staff increasingly ask AI assistants to do or
check these computations. A wrong answer said with confidence costs real workers real pesos.

## Who it's for

- Teams building HR, payroll, or compliance assistants for the Philippine market
- Model developers checking multi-step numeric reasoning under jurisdiction-specific rules
- TODO: add others

## Task design

| Field | Meaning |
|---|---|
| `prompt` | Full text sent to the model: rules + scenario + required answer format |
| `expected_answer` | Correct amount in pesos |
| `tolerance` | Allowed difference (default ₱0.01) |
| `difficulty`, `tags` | Used for the breakdowns in the report |
| `failure_categories` | Mistakes the task is designed to catch |
| `source_refs` | Where each rule comes from in the DOLE handbook |
| `reference_inputs` | Inputs for `reference/calculator.py`, used by the oracle check |

Every task also has a `solution.md` with the step-by-step reference computation.

Every prompt ends with a fixed line format:

```
FINAL ANSWER: ₱<amount with 2 decimals>
```

**Tasks:** TODO: table of all tasks (id, title, difficulty, tags).

## Grading method

`grader.py` is deterministic. It does not use an LLM judge.

1. It reads only the **last** `FINAL ANSWER:` line. Numbers in the working are ignored.
2. That line must hold exactly **one** amount. Accepted forms are `₱` or `PHP`, valid
   thousands commas, and 0–2 decimals. Light markdown like `**bold**` is allowed.
3. The result is `pass` if |answer − expected| ≤ tolerance, and `fail` otherwise.
4. If there's no parsable final line, the result is `format_failure`. That covers no line,
   two amounts, words around the number, or a malformed number. These are reported
   separately from wrong answers.
5. Comparisons use `Decimal`, not float, so an answer exactly at the tolerance edge is
   never falsely failed.

**Grader reliability:**
- `tests/test_grader.py` has 40+ tricky outputs: multiple numbers, commas, `PHP 2258.9`,
  a missing line, a corrected answer, European formatting, and more.
- `oracle_check.py` proves every task is solvable and graded correctly. For each task:
  - the expected answer passes the grader;
  - an independent reference calculator reproduces the expected answer;
  - a wrong answer fails.

API errors (rate limits, timeouts, provider errors) are retried with backoff and
**never counted as model failures**.

## How to run

Tested with Python TODO (3.11+) on TODO (OS).

```bash
git clone TODO && cd ph-payroll-eval
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # then paste your OpenRouter key into .env

python -m pytest                  # grader + calculator tests (no API key needed)
python oracle_check.py            # every task solvable & graded correctly (no API key needed)

python run_eval.py                # all models/tasks/trials from config.yaml
python report.py                  # writes results/summary.md + results/pass_rate.png
```

Options:

```bash
python run_eval.py --models openai/gpt-4o,anthropic/claude-sonnet-4 --tasks task_01 --trials 3
```

- Runs **resume**: a finished trial is saved to
  `results/raw/<model>/<task>/trial_<n>.json` and skipped next time.
- To start fresh, delete `results/raw/`.
- Each trial records: prompt, full response, extracted answer, status, latency, token usage,
  cost, the exact model OpenRouter served, and a timestamp.

**Expected runtime and cost:** TODO: fill in from your run's printed summary,
e.g. "N models × M tasks × 3 trials ≈ X minutes, ≈ $Y on OpenRouter".

**Models and settings used for the reported results:** TODO: copy from `config.yaml`
(model ids, temperature, max_tokens, trials) and give the run date.

## Results

TODO: paste `results/summary.md` here.

![Pass rate per model](results/pass_rate.png)

## Failure analysis

TODO: for each common failure, give the category, how many trials it occurred in, and a
short quoted excerpt from a transcript (`results/raw/...`). Examples to look for:
- counted the unpaid meal break as hours worked
- added premiums (200% + 30% + 10%) instead of multiplying them
- applied the night differential to the basic hourly rate only
- missed that the overtime hours are also night hours
- format failures (no final line, or truncated output)

## Limitations

- Small task set (TODO: N tasks); results are indicative, not a full benchmark.
- Rules are given in the prompt, so this does **not** test whether a model knows Philippine
  law unaided.
- Covers private-sector rules only. These are not implemented:
  - coverage exemptions (e.g. small retail/service establishments, managerial staff,
    field personnel);
  - shifts that cross midnight into a different day type;
  - unworked-holiday pay.

  See the `TODO(verify)` notes in `reference/calculator.py`.
- Model outputs vary between runs, even at temperature 0. pass^k over k trials is reported
  to show consistency.
- OpenRouter may route a model id to different providers. The served model and provider are
  logged per trial.
- Not legal advice. Rules should be checked against the current DOLE-BWC Handbook.

## What existed before vs. built during the hackathon

| Before the hackathon | Built during the hackathon |
|---|---|
| TODO (e.g. domain knowledge, notes on DOLE rules) | TODO (e.g. all code in this repo, tasks, tests, results) |

## Repository layout

```
config.yaml            default models, trials, temperature, max_tokens
tasks/<id>/task.json   prompt, expected answer, tags, ...
tasks/<id>/solution.md step-by-step reference computation
reference/calculator.py deterministic calculator (only the rules supplied)
grader.py              answer extraction + pass/fail/format_failure
oracle_check.py        proves tasks are solvable and the grader is correct
run_eval.py            calls models via OpenRouter, saves every trial
report.py              tables, pass^k, breakdowns, chart -> results/
tests/                 pytest for grader and calculator
```
