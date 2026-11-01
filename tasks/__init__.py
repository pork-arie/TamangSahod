"""Shared helper for loading task folders (tasks/<id>/task.json)."""

import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent

REQUIRED_FIELDS = ["id", "title", "difficulty", "tags", "prompt", "expected_answer"]


def load_tasks(selection="all"):
    """Load tasks sorted by id. selection is "all" or a comma list like "task_01,task_03"."""
    tasks = []
    for path in sorted(TASKS_DIR.glob("*/task.json")):
        with open(path, encoding="utf-8") as f:
            task = json.load(f)
        missing = [k for k in REQUIRED_FIELDS if k not in task]
        if missing:
            raise ValueError(f"{path} is missing fields: {missing}")
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
