"""Summarise saved trials into tables + one chart.

Reads results/raw/<model>/<condition>/<task>/trial_*.json and writes:
  results/summary.md     (paste into the README)
  results/pass_rate.png  (bar chart: overall pass rate per model, open vs closed)
  results/tasks_table.md (every task: id, title, difficulty, tags, verified)

Conditions (see tasks/__init__.py):
  open    rules given in the prompt
  closed  the same prompt with the RULES section removed (same expected answer)
By default both are shown SIDE BY SIDE (one column per model per condition).
--condition open|closed reports only that one.

Metrics:
  pass rate  = passed trials / all graded trials
  pass^k     = share of tasks where ALL k trials passed (consistency, not just luck)
  format     = share of trials with no parsable FINAL ANSWER line
  truncated  = share of trials cut off by max_tokens (finish_reason "length"); these are
               usually also format failures, so a high value means "budget", not "skill"

Only verified tasks are reported by default. With --include-drafts, draft tasks
are added and every place they appear is marked DRAFT.

  python report.py
  python report.py --condition closed
  python report.py --include-drafts
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # render to file; no display needed
import matplotlib.pyplot as plt

from tasks import CONDITIONS, load_tasks, prompt_for, prompt_sha256, saved_prompt_sha256, trial_condition

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "results" / "raw"
SUMMARY_MD = ROOT / "results" / "summary.md"
CHART_PNG = ROOT / "results" / "pass_rate.png"
TASKS_MD = ROOT / "results" / "tasks_table.md"

CONDITION_LABEL = {"open": "open (rules given)", "closed": "closed (rules removed)"}


def load_trials(tasks):
    """Load saved trials, keeping only those run with the CURRENT prompt for their condition.

    Returns (kept, ignored) where ignored is a list of (path, reason).
    Every kept trial has a "condition" key (old trials without one are "open").
    """
    by_id = {t["id"]: t for t in tasks}
    kept, ignored = [], []
    for path in sorted(RAW_DIR.glob("*/*/*/trial_*.json")):  # <model>/<condition>/<task>/
        with open(path, encoding="utf-8") as f:
            trial = json.load(f)
        rel = path.relative_to(ROOT)
        condition = trial_condition(trial)
        task = by_id.get(trial["task_id"])
        if task is None:
            ignored.append((rel, "task no longer exists"))
        elif condition not in CONDITIONS:
            ignored.append((rel, f"unknown condition {condition!r}"))
        elif saved_prompt_sha256(trial) != prompt_sha256(prompt_for(task, condition)):
            ignored.append((rel, "prompt changed since this trial ran (stale)"))
        else:
            trial["condition"] = condition
            kept.append(trial)
    return kept, ignored


def settings_warnings(trials):
    """One warning per model whose trials were run with different settings (e.g. max_tokens)."""
    by_model = defaultdict(set)
    for t in trials:
        by_model[t["model"]].add(json.dumps(t.get("settings"), sort_keys=True))
    return [f"{m}: trials used mixed settings {sorted(s)}" for m, s in by_model.items() if len(s) > 1]


def pct(num, den):
    return f"{100 * num / den:.0f}%" if den else "–"


def summarise(trials, tasks):
    """Group trials by series = (model, condition) and task; compute every number the report needs.

    Series are ordered model by model, open before closed, so tables show them side by side.
    """
    task_meta = {t["id"]: t for t in tasks}
    by_series_task = defaultdict(list)      # ((model, condition), task_id) -> [trial, ...]
    for t in trials:                         # load_trials already dropped stale/unknown tasks
        by_series_task[((t["model"], t["condition"]), t["task_id"])].append(t)

    present = {s for s, _ in by_series_task}
    models = sorted({m for m, _ in present})
    conditions = [c for c in CONDITIONS if any(s[1] == c for s in present)]
    series = [(m, c) for m in models for c in conditions]   # every model gets every shown condition
    task_ids = [t["id"] for t in tasks if any((s, t["id"]) in by_series_task for s in series)]

    stats = {}
    for s in series:
        passed = total = fmt = truncated = 0
        tasks_all_pass = tasks_seen = 0
        trial_counts = set()
        per_task = {}
        for tid in task_ids:
            ts = by_series_task.get((s, tid), [])
            if not ts:
                continue
            p = sum(x["passed"] for x in ts)
            per_task[tid] = (p, len(ts))
            passed += p
            total += len(ts)
            fmt += sum(x["status"] == "format_failure" for x in ts)
            truncated += sum(x.get("finish_reason") == "length" for x in ts)
            tasks_seen += 1
            tasks_all_pass += p == len(ts)
            trial_counts.add(len(ts))
        stats[s] = {"passed": passed, "total": total, "format": fmt, "truncated": truncated,
                    "per_task": per_task,
                    "pass_k": (tasks_all_pass, tasks_seen), "k": trial_counts}
    return models, conditions, series, task_ids, task_meta, stats, by_series_task


def series_header(s):
    model, condition = s
    return f"`{model}` {condition}"


def breakdown_table(series, task_ids, task_meta, by_series_task, key_fn, label):
    """Pass rate per series for each group (difficulty or tag). A task can be in several tag groups."""
    groups = defaultdict(set)
    for tid in task_ids:
        for g in key_fn(task_meta[tid]):
            groups[g].add(tid)
    lines = [f"| {label} | tasks | " + " | ".join(series_header(s) for s in series) + " |",
             "|---|---|" + "---|" * len(series)]
    for g in sorted(groups):
        cells = []
        for s in series:
            ts = [x for tid in groups[g] for x in by_series_task.get((s, tid), [])]
            cells.append(pct(sum(x["passed"] for x in ts), len(ts)))
        lines.append(f"| {g} | {len(groups[g])} | " + " | ".join(cells) + " |")
    return lines


def task_label(task):
    """Task id as shown in tables; drafts are always visibly marked."""
    return task["id"] if task["verified"] else f"{task['id']} (DRAFT)"


def rate(st):
    return 100 * st["passed"] / st["total"] if st["total"] else None


def write_markdown(models, conditions, series, task_ids, task_meta, stats, by_series_task):
    out = ["# Results", ""]
    draft_ids = [tid for tid in task_ids if not task_meta[tid]["verified"]]
    if draft_ids:
        out += [f"> **DRAFT RESULTS INCLUDED.** {len(draft_ids)} task(s) are not yet verified "
                f"against the DOLE-BWC Handbook: {', '.join(draft_ids)}. "
                "Do not cite these numbers as final.", ""]
    out += ["Conditions shown: " + ", ".join(f"**{CONDITION_LABEL[c]}**" for c in conditions)
            + ". The expected answers are the same in both.", ""]

    if len(conditions) == 2:
        out += ["## Open vs closed book", "",
                "| Model | Open (rules given) | Closed (rules removed) | Difference |",
                "|---|---|---|---|"]
        for m in models:
            o, c = stats[(m, "open")], stats[(m, "closed")]
            ro, rc = rate(o), rate(c)
            diff = f"{rc - ro:+.0f} pp" if ro is not None and rc is not None else "–"
            out.append(f"| `{m}` | {pct(o['passed'], o['total'])} ({o['passed']}/{o['total']}) "
                       f"| {pct(c['passed'], c['total'])} ({c['passed']}/{c['total']}) | {diff} |")
        out += ["", "_pp = percentage points (closed minus open)._", ""]

    out += ["## Overall", "",
            "| Model | Condition | Pass rate | pass^k | Format failures | Truncated | Trials |",
            "|---|---|---|---|---|---|---|"]
    for s in series:
        st = stats[s]
        k = "/".join(str(x) for x in sorted(st["k"])) or "–"
        out.append(f"| `{s[0]}` | {s[1]} | {pct(st['passed'], st['total'])} ({st['passed']}/{st['total']}) "
                   f"| {pct(*st['pass_k'])} ({st['pass_k'][0]}/{st['pass_k'][1]} tasks, k={k}) "
                   f"| {pct(st['format'], st['total'])} | {pct(st['truncated'], st['total'])} "
                   f"| {st['total']} |")
    out += ["", "_pass^k = share of tasks where every one of the k trials passed. "
            "Truncated = reply cut off by max_tokens (counted inside format failures)._", ""]

    out += ["## Per task (passed / trials)", "",
            "| Task | Difficulty | " + " | ".join(series_header(s) for s in series) + " |",
            "|---|---|" + "---|" * len(series)]
    for tid in task_ids:
        cells = []
        for s in series:
            p, n = stats[s]["per_task"].get(tid, (0, 0))
            cells.append(f"{p}/{n}" if n else "–")
        out.append(f"| {task_label(task_meta[tid])} | {task_meta[tid]['difficulty']} | "
                   + " | ".join(cells) + " |")
    out.append("")

    out += ["## By difficulty", ""]
    out += breakdown_table(series, task_ids, task_meta, by_series_task,
                           lambda t: [t["difficulty"]], "Difficulty")
    out += ["", "## By tag", "", "_A task with several tags counts in each tag's row._", ""]
    out += breakdown_table(series, task_ids, task_meta, by_series_task,
                           lambda t: t["tags"], "Tag")
    out += ["", "![Pass rate per model](pass_rate.png)", ""]

    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(out), encoding="utf-8")


def write_tasks_table(tasks):
    """results/tasks_table.md: one row per task (drafts included), linked from the README."""
    out = ["# Tasks", "",
           f"{len(tasks)} task(s), {sum(t['verified'] for t in tasks)} verified against the "
           "DOLE-BWC Handbook. Draft tasks are left out of reported results unless "
           "`--include-drafts` is used.", "",
           "| ID | Title | Difficulty | Tags | Verified |",
           "|---|---|---|---|---|"]
    for t in tasks:
        tags = ", ".join(f"`{tag}`" for tag in t["tags"])
        verified = "yes" if t["verified"] else "no (DRAFT)"
        out.append(f"| [{t['id']}](../tasks/{t['id']}/task.json) | {t['title']} "
                   f"| {t['difficulty']} | {tags} | {verified} |")
    TASKS_MD.parent.mkdir(parents=True, exist_ok=True)
    TASKS_MD.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_chart(models, conditions, stats, has_drafts=False):
    """Horizontal bars (model names are long): one bar per condition for each model.

    Colours are validated categorical slots (blue = open, orange = closed); bars are
    direct-labelled with their value and a legend is shown when there are 2 conditions.
    """
    surface, ink, ink_muted, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    colors = {"open": "#2a78d6", "closed": "#eb6834"}
    n = len(conditions)
    bar_h = 0.7 / n                           # bars of one model share a 0.7-tall slot
    fig, ax = plt.subplots(figsize=(8, (0.45 + 0.35 * n) * len(models) + 1.6), facecolor=surface)
    ax.set_facecolor(surface)
    for i, c in enumerate(conditions):
        ys = [y + (i - (n - 1) / 2) * bar_h for y in range(len(models))]
        values = [rate(stats[(m, c)]) for m in models]
        ax.barh(ys, [v or 0 for v in values], height=bar_h, color=colors[c],
                edgecolor=surface, linewidth=2, label=CONDITION_LABEL[c])  # 2px surface gap between bars
        for y, v in zip(ys, values):
            ax.text((v or 0) + 1, y, "no trials" if v is None else f"{v:.0f}%",
                    va="center", color=ink, fontsize=9)
    ax.set_yticks(range(len(models)), models, color=ink, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 110)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("Pass rate (% of trials)", color=ink_muted)
    title = "TamangSahod: pass rate by model"
    if n == 2:
        title += ", open vs closed book"
    if has_drafts:
        title += "  (includes DRAFT tasks)"
    ax.set_title(title, color=ink, loc="left", fontsize=12)
    if n == 2:
        # below the x-axis, so it can never cover a bar
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.22), ncol=2, frameon=False,
                  fontsize=9, labelcolor=ink)
    ax.grid(axis="x", color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ink_muted)
    ax.tick_params(colors=ink_muted, length=0)
    fig.tight_layout()
    fig.savefig(CHART_PNG, dpi=150, facecolor=surface)
    plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore  # so ₱ prints on Windows; Pylance thinks stdout lacks reconfigure()
    p = argparse.ArgumentParser(description="Summarise saved trials into tables and a chart.")
    p.add_argument("--include-drafts", action="store_true",
                   help="also report draft tasks (verified=false), marked DRAFT")
    p.add_argument("--condition", choices=CONDITIONS, default=None,
                   help="report only this condition (default: open and closed side by side)")
    args = p.parse_args()

    tasks = load_tasks("all")
    write_tasks_table(tasks)              # always lists ALL tasks, with their verified flag
    print(f"Wrote {TASKS_MD.relative_to(ROOT)}\n")
    trials, ignored = load_trials(tasks)  # stale check uses ALL tasks, drafts included
    if args.condition:
        trials = [t for t in trials if t["condition"] == args.condition]

    # Verification gate: leave draft tasks out unless asked for.
    draft_ids = {t["id"] for t in tasks if not t["verified"]}
    if not args.include_drafts:
        excluded = [t for t in trials if t["task_id"] in draft_ids]
        if excluded:
            print(f"Note: {len(excluded)} trial(s) on draft task(s) {', '.join(sorted(draft_ids))} "
                  "are excluded. Use --include-drafts to see them (marked DRAFT).\n")
        trials = [t for t in trials if t["task_id"] not in draft_ids]
        tasks = [t for t in tasks if t["verified"]]

    if ignored:
        print(f"WARNING: ignoring {len(ignored)} trial(s) that don't match the current tasks:")
        for path, reason in ignored:
            print(f"  - {path}: {reason}")
        print("  (python run_eval.py moves stale trials to results/stale/ and re-runs them)\n")
    for w in settings_warnings(trials):
        print(f"WARNING: {w}\n")

    if not trials:
        hint = " (all tasks are drafts? try --include-drafts)" if draft_ids and not args.include_drafts else ""
        cond = f" --condition {args.condition}" if args.condition else ""
        sys.exit(f"No current trials to report{hint}. Run: python run_eval.py{cond}")
    models, conditions, series, task_ids, task_meta, stats, by_series_task = summarise(trials, tasks)
    write_markdown(models, conditions, series, task_ids, task_meta, stats, by_series_task)
    write_chart(models, conditions, stats,
                has_drafts=any(not task_meta[tid]["verified"] for tid in task_ids))
    print(SUMMARY_MD.read_text(encoding="utf-8"))
    print(f"\nWrote {SUMMARY_MD.relative_to(ROOT)} and {CHART_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
