"""Re-grade saved trials with the CURRENT grader and answer key. No API calls, no cost.

Use this after changing grader.py (or fixing a task's expected_answer) so old
transcripts are graded by the same rules as new ones.

  python regrade.py            # update results/raw/ in place and list what changed
  python regrade.py --dry-run  # only show what would change

Only trials whose prompt still matches the current task (same prompt_sha256)
are re-graded. Others are stale and are left alone (report.py ignores them).
When a grade changes, the old grade is kept in the file under "previous_grade".
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from grader import grade
from run_eval import RAW_DIR, ROOT, save_json
from tasks import load_tasks, prompt_sha256, saved_prompt_sha256


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore  # so ₱ prints on Windows; Pylance thinks stdout lacks reconfigure()
    p = argparse.ArgumentParser(description="Re-grade saved trials with the current grader.")
    p.add_argument("--dry-run", action="store_true", help="show changes without writing files")
    args = p.parse_args()

    tasks = {t["id"]: t for t in load_tasks("all")}
    counts = {"checked": 0, "changed": 0, "unchanged": 0, "skipped": 0}

    for path in sorted(RAW_DIR.glob("*/*/trial_*.json")):
        with open(path, encoding="utf-8") as f:
            trial = json.load(f)
        task = tasks.get(trial["task_id"])
        if task is None or saved_prompt_sha256(trial) != prompt_sha256(task["prompt"]):
            counts["skipped"] += 1  # task removed or prompt edited: not comparable
            continue

        counts["checked"] += 1
        new = grade(trial["response"], task["expected_answer"], task["tolerance"])
        old = {
            "status": trial.get("status"),
            "extracted_answer": trial.get("extracted_answer"),
            "expected_answer": trial.get("expected_answer"),
            "format_reason": trial.get("format_reason"),
        }
        same = (old["status"] == new["status"]
                and old["extracted_answer"] == new["extracted"]
                and old["expected_answer"] == new["expected"]
                and old["format_reason"] == new["format_reason"])
        if same:
            counts["unchanged"] += 1
            continue

        counts["changed"] += 1
        print(f"{path.relative_to(ROOT)}: {old['status']} -> {new['status']} "
              f"(got {new['extracted']}, expected {new['expected']}"
              + (f", reason {new['format_reason']}" if new["format_reason"] else "") + ")")
        if args.dry_run:
            continue

        trial["previous_grade"] = old
        trial["regraded_at"] = datetime.now(timezone.utc).isoformat()
        trial["prompt_sha256"] = saved_prompt_sha256(trial)
        trial["expected_answer"] = new["expected"]
        trial["tolerance"] = str(task["tolerance"])
        trial["extracted_answer"] = new["extracted"]
        trial["status"] = new["status"]
        trial["format_reason"] = new["format_reason"]
        trial["passed"] = new["status"] == "pass"
        trial["score"] = new["score"]
        save_json(path, trial)

    verb = "would change" if args.dry_run else "changed"
    print(f"\nchecked {counts['checked']} trial(s): {counts['changed']} {verb}, "
          f"{counts['unchanged']} unchanged, {counts['skipped']} skipped (stale or unknown task)")
    if counts["changed"] and not args.dry_run:
        print("Next: python report.py")


if __name__ == "__main__":
    main()
