"""Shared helpers for loading task folders (tasks/<id>/task.json)."""

import hashlib
import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent

REQUIRED_FIELDS = ["id", "title", "difficulty", "tags", "prompt", "expected_answer", "verified"]


def prompt_sha256(prompt: str) -> str:
    """Fingerprint of the exact prompt text. If a task's prompt is edited, this changes."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def saved_prompt_sha256(trial: dict) -> str:
    """Hash of the prompt a saved trial was run with.

    Trials saved before prompt_sha256 existed still contain the full prompt text,
    so we can compute the hash from it.
    """
    return trial.get("prompt_sha256") or prompt_sha256(trial.get("prompt", ""))


def load_tasks(selection="all", tasks_dir=TASKS_DIR):
    """Load tasks sorted by id. selection is "all" or a comma list like "task_01,task_03".

    Every task must have "verified": true or false. Draft tasks (false) are still
    loaded here; run_eval.py and report.py decide whether to use them.
    """
    tasks = []
    for path in sorted(Path(tasks_dir).glob("*/task.json")):
        with open(path, encoding="utf-8") as f:
            task = json.load(f)
        missing = [k for k in REQUIRED_FIELDS if k not in task]
        if missing:
            raise ValueError(f"{path} is missing fields: {missing}")
        if not isinstance(task["verified"], bool):
            raise ValueError(f"{path}: \"verified\" must be true or false, got {task['verified']!r}")
        if task["id"] != path.parent.name:
            raise ValueError(f"{path}: id {task['id']!r} must match folder name {path.parent.name!r}")
        task.setdefault("tolerance", 0.01)
        tasks.append(task)

    if selection in (None, "", "all"):
        return tasks
    wanted = [s.strip() for s in selection.split(",") if s.strip()]
    by_id = {t["id"]: t for t in tasks}
    unknown = [w for w in wanted if w not in by_id]
    if unknown:
        raise ValueError(f"Unknown task ids: {unknown}. Available: {sorted(by_id)}")
    return [by_id[w] for w in wanted]
