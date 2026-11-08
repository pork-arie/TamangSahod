"""Shared helpers for loading task folders (tasks/<id>/task.json).

Each task can be run in two CONDITIONS:
  open    the prompt exactly as written in task.json (rules + scenario + question)
  closed  the same prompt with the "RULES (...)" section removed, so the model must
          know the Philippine rules itself. Scenario, question and the FINAL ANSWER
          format line are unchanged, and so is the expected answer.
"""

import hashlib
import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent

REQUIRED_FIELDS = ["id", "title", "difficulty", "tags", "prompt", "expected_answer", "verified"]

CONDITIONS = ("open", "closed")
RULES_MARKER = "RULES ("            # start of the rules section, e.g. "RULES (from the DOLE Handbook ...):"
SCENARIO_MARKER = "\nSCENARIO:"     # the rules section ends where the scenario starts


def closed_book_prompt(prompt: str) -> str:
    """The prompt with its RULES section cut out (from "RULES (" up to "SCENARIO:").

    Everything before the rules (the one-line intro) and everything from SCENARIO:
    onwards is kept character for character.
    """
    if prompt.count(RULES_MARKER) != 1:
        raise ValueError(f"prompt must contain exactly one {RULES_MARKER!r} section")
    start = prompt.index(RULES_MARKER)
    end = prompt.find(SCENARIO_MARKER, start)
    if end == -1:
        raise ValueError(f"prompt has no {SCENARIO_MARKER.strip()!r} after the rules section")
    return prompt[:start] + prompt[end + 1:]  # +1 keeps "SCENARIO:" and drops one newline


def prompt_for(task: dict, condition: str) -> str:
    """The exact text sent to the model for this task under this condition."""
    if condition == "open":
        return task["prompt"]
    if condition == "closed":
        return closed_book_prompt(task["prompt"])
    raise ValueError(f"Unknown condition {condition!r}; choose from {CONDITIONS}")


def trial_condition(trial: dict) -> str:
    """Condition a saved trial was run under. Trials saved before conditions existed were open."""
    return trial.get("condition", "open")


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
        try:
            closed_book_prompt(task["prompt"])  # every task must support the closed condition
        except ValueError as e:
            raise ValueError(f"{path}: cannot build the closed-book prompt: {e}") from None
        tasks.append(task)

    if selection in (None, "", "all"):
        return tasks
    wanted = [s.strip() for s in selection.split(",") if s.strip()]
    by_id = {t["id"]: t for t in tasks}
    unknown = [w for w in wanted if w not in by_id]
    if unknown:
        raise ValueError(f"Unknown task ids: {unknown}. Available: {sorted(by_id)}")
    return [by_id[w] for w in wanted]
