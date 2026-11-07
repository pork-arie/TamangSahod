"""Copy the final trial transcripts into results/sample/ so judges can read them.

results/raw/ is git-ignored (it can be large and messy). results/sample/ is
tracked, so it is what ends up on GitHub and in submission.zip.

What gets copied:
  * only trials whose prompt still matches the task (same prompt_sha256);
    stale trials are skipped
  * only VERIFIED tasks, unless --include-drafts is given
  * the folder layout is kept: results/sample/<model>/<task>/trial_N.json

results/sample/ is emptied first (except .gitkeep), so it always mirrors the
current results and never keeps transcripts from old prompts.

  python make_sample.py
  python make_sample.py --include-drafts
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from tasks import load_tasks, prompt_sha256, saved_prompt_sha256

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "results" / "raw"
SAMPLE_DIR = ROOT / "results" / "sample"
KEY_PREFIX = "sk-" + "or-"  # written in two parts so this file itself never contains a key-like string


def clear_sample_dir():
    """Delete everything in results/sample/ except .gitkeep."""
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for item in SAMPLE_DIR.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def select_trials(tasks):
    """Return (paths to copy, skipped list of (path, reason))."""
    current_hash = {t["id"]: prompt_sha256(t["prompt"]) for t in tasks}
    chosen, skipped = [], []
    for path in sorted(RAW_DIR.glob("*/*/trial_*.json")):
        trial = json.loads(path.read_text(encoding="utf-8"))
        task_id = trial.get("task_id")
        if task_id not in current_hash:
            skipped.append((path, "task not selected (draft or removed)"))
        elif saved_prompt_sha256(trial) != current_hash[task_id]:
            skipped.append((path, "stale (prompt changed)"))
        elif KEY_PREFIX in path.read_text(encoding="utf-8"):
            skipped.append((path, "contains an API-key-like string; NOT copied"))
        else:
            chosen.append(path)
    return chosen, skipped


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore  # so ₱ prints on Windows; Pylance thinks stdout lacks reconfigure()
    p = argparse.ArgumentParser(description="Copy final trial JSONs into results/sample/.")
    p.add_argument("--include-drafts", action="store_true",
                   help="also copy trials for draft tasks (verified=false)")
    args = p.parse_args()

    tasks = [t for t in load_tasks("all") if t["verified"] or args.include_drafts]
    if not tasks:
        sys.exit("No verified tasks yet. Verify tasks first, or use --include-drafts.")

    chosen, skipped = select_trials(tasks)
    clear_sample_dir()
    for path in chosen:
        target = SAMPLE_DIR / path.relative_to(RAW_DIR)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    for path, reason in skipped:
        print(f"skipped {path.relative_to(ROOT)}: {reason}")
    print(f"\nCopied {len(chosen)} trial(s) for {len(tasks)} task(s) into "
          f"{SAMPLE_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
