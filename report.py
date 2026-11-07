"""Summarise saved trials into tables + one chart.

Reads results/raw/**/trial_*.json and writes:
  results/summary.md     (paste into the README)
  results/pass_rate.png  (bar chart: overall pass rate per model)

Metrics:
  pass rate  = passed trials / all graded trials
  pass^k     = share of tasks where ALL k trials passed (consistency, not just luck)
  format     = share of trials with no parsable FINAL ANSWER line
  truncated  = share of trials cut off by max_tokens (finish_reason "length"); these are
               usually also format failures, so a high value means "budget", not "skill"

Only verified tasks are reported by default. With --include-drafts, draft tasks
are added and every place they appear is marked DRAFT.

  python report.py
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

from tasks import load_tasks, prompt_sha256, saved_prompt_sha256

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "results" / "raw"
SUMMARY_MD = ROOT / "results" / "summary.md"
CHART_PNG = ROOT / "results" / "pass_rate.png"


def load_trials(tasks):
    """Load saved trials, keeping only those run with each task's CURRENT prompt.

    Returns (kept, ignored) where ignored is a list of (path, reason).
    """
    current_hash = {t["id"]: prompt_sha256(t["prompt"]) for t in tasks}
    kept, ignored = [], []
    for path in sorted(RAW_DIR.glob("*/*/trial_*.json")):
        with open(path, encoding="utf-8") as f:
            trial = json.load(f)
        rel = path.relative_to(ROOT)
        if trial["task_id"] not in current_hash:
            ignored.append((rel, "task no longer exists"))
        elif saved_prompt_sha256(trial) != current_hash[trial["task_id"]]:
            ignored.append((rel, "prompt changed since this trial ran (stale)"))
        else:
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
    """Group trials by (model, task) and compute every number the report needs."""
    task_meta = {t["id"]: t for t in tasks}
    by_model_task = defaultdict(list)       # (model, task_id) -> [trial, ...]
    for t in trials:                         # load_trials already dropped stale/unknown tasks
        by_model_task[(t["model"], t["task_id"])].append(t)

    models = sorted({m for m, _ in by_model_task})
    task_ids = [t["id"] for t in tasks if any((m, t["id"]) in by_model_task for m in models)]

    stats = {}
    for m in models:
        passed = total = fmt = truncated = 0
        tasks_all_pass = tasks_seen = 0
        trial_counts = set()
        per_task = {}
        for tid in task_ids:
            ts = by_model_task.get((m, tid), [])
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
        stats[m] = {"passed": passed, "total": total, "format": fmt, "truncated": truncated,
                    "per_task": per_task,
                    "pass_k": (tasks_all_pass, tasks_seen), "k": trial_counts}
    return models, task_ids, task_meta, stats, by_model_task


def breakdown_table(models, task_ids, task_meta, by_model_task, key_fn, label):
    """Pass rate per model for each group (difficulty or tag). A task can be in several tag groups."""
    groups = defaultdict(set)
    for tid in task_ids:
        for g in key_fn(task_meta[tid]):
            groups[g].add(tid)
    lines = [f"| {label} | tasks | " + " | ".join(models) + " |",
             "|---|---|" + "---|" * len(models)]
    for g in sorted(groups):
        cells = []
        for m in models:
            ts = [x for tid in groups[g] for x in by_model_task.get((m, tid), [])]
            cells.append(pct(sum(x["passed"] for x in ts), len(ts)))
        lines.append(f"| {g} | {len(groups[g])} | " + " | ".join(cells) + " |")
    return lines


def task_label(task):
    """Task id as shown in tables; drafts are always visibly marked."""
    return task["id"] if task["verified"] else f"{task['id']} (DRAFT)"


def write_markdown(models, task_ids, task_meta, stats, by_model_task):
    out = ["# Results", ""]
    draft_ids = [tid for tid in task_ids if not task_meta[tid]["verified"]]
    if draft_ids:
        out += [f"> **DRAFT RESULTS INCLUDED.** {len(draft_ids)} task(s) are not yet verified "
                f"against the DOLE-BWC Handbook: {', '.join(draft_ids)}. "
                "Do not cite these numbers as final.", ""]

    out += ["## Overall", "",
            "| Model | Pass rate | pass^k | Format failures | Truncated | Trials |",
            "|---|---|---|---|---|---|"]
    for m in models:
        s = stats[m]
        k = "/".join(str(x) for x in sorted(s["k"]))
        out.append(f"| `{m}` | {pct(s['passed'], s['total'])} ({s['passed']}/{s['total']}) "
                   f"| {pct(*s['pass_k'])} ({s['pass_k'][0]}/{s['pass_k'][1]} tasks, k={k}) "
                   f"| {pct(s['format'], s['total'])} | {pct(s['truncated'], s['total'])} "
                   f"| {s['total']} |")
    out += ["", "_pass^k = share of tasks where every one of the k trials passed. "
            "Truncated = reply cut off by max_tokens (counted inside format failures)._", ""]

    out += ["## Per task (passed / trials)", "",
            "| Task | Difficulty | " + " | ".join(f"`{m}`" for m in models) + " |",
            "|---|---|" + "---|" * len(models)]
    for tid in task_ids:
        cells = []
        for m in models:
            p, n = stats[m]["per_task"].get(tid, (0, 0))
            cells.append(f"{p}/{n}" if n else "–")
        out.append(f"| {task_label(task_meta[tid])} | {task_meta[tid]['difficulty']} | "
                   + " | ".join(cells) + " |")
    out.append("")

    out += ["## By difficulty", ""]
    out += breakdown_table(models, task_ids, task_meta, by_model_task,
                           lambda t: [t["difficulty"]], "Difficulty")
    out += ["", "## By tag", "", "_A task with several tags counts in each tag's row._", ""]
    out += breakdown_table(models, task_ids, task_meta, by_model_task,
                           lambda t: t["tags"], "Tag")
    out += ["", "![Pass rate per model](pass_rate.png)", ""]

    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(out), encoding="utf-8")


def write_chart(models, stats, has_drafts=False):
    """Horizontal bar chart (model names are long), sorted best -> worst, labelled values."""
    rows = sorted(((100 * stats[m]["passed"] / stats[m]["total"], m) for m in models), reverse=True)
    values = [r[0] for r in rows]
    names = [r[1] for r in rows]

    surface, ink, ink_muted, bar = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(names) + 1.4), facecolor=surface)
    ax.set_facecolor(surface)
    y = range(len(names))
    ax.barh(y, values, color=bar, height=0.6)
    ax.set_yticks(list(y), names, color=ink, fontsize=10)
    ax.invert_yaxis()  # best model on top
    ax.set_xlim(0, 100)
    ax.set_xlabel("Pass rate (% of trials)", color=ink_muted)
    title = "PH payroll eval: overall pass rate by model"
    if has_drafts:
        title += "  (includes DRAFT tasks)"
    ax.set_title(title, color=ink, loc="left", fontsize=12)
    for yi, v in zip(y, values):
        ax.text(v + 1, yi, f"{v:.0f}%", va="center", color=ink, fontsize=10)
    ax.grid(axis="x", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ink_muted)
    ax.tick_params(colors=ink_muted, length=0)
    fig.tight_layout()
    fig.savefig(CHART_PNG, dpi=150, facecolor=surface)
    plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarise saved trials into tables and a chart.")
    p.add_argument("--include-drafts", action="store_true",
                   help="also report draft tasks (verified=false), marked DRAFT")
    args = p.parse_args()

    tasks = load_tasks("all")
    trials, ignored = load_trials(tasks)  # stale check uses ALL tasks, drafts included

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
        sys.exit(f"No current trials to report{hint}. Run: python run_eval.py")
    models, task_ids, task_meta, stats, by_model_task = summarise(trials, tasks)
    write_markdown(models, task_ids, task_meta, stats, by_model_task)
    write_chart(models, stats, has_drafts=any(not task_meta[tid]["verified"] for tid in task_ids))
    print(SUMMARY_MD.read_text(encoding="utf-8"))
    print(f"\nWrote {SUMMARY_MD.relative_to(ROOT)} and {CHART_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
