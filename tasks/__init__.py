"""Shared helpers for loading task folders (tasks/<id>/task.json).

Each task can be run in two CONDITIONS:
  open    the prompt exactly as written in task.json (rules + scenario + question)
  closed  the same prompt with the "RULES (...)" section removed, so the model must
          know the Philippine rules itself. Scenario, question and the FINAL ANSWER
          format line are unchanged, and so is the expected answer.
          Task-specific facts that are NOT general law (a days factor, a company policy,
          a rounding convention) stay, under "GIVEN FACTS:" (task.json "closed_book_keep").
          Wording that refers to the missing rules is fixed for the closed prompt only
          (task.json "closed_book_replace").
"""

import hashlib
import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent

REQUIRED_FIELDS = ["id", "title", "difficulty", "tags", "prompt", "expected_answer", "verified"]

CONDITIONS = ("open", "closed")
RULES_MARKER = "RULES ("            # start of the rules section, e.g. "RULES (from the DOLE Handbook ...):"
SCENARIO_MARKER = "\nSCENARIO:"     # the rules section ends where the scenario starts


GIVEN_FACTS_HEADING = "GIVEN FACTS:"


def closed_book_prompt(prompt: str, keep=None, replace=None) -> str:
    """The prompt with its RULES section cut out (from "RULES (" up to "SCENARIO:").

    keep     task.json "closed_book_keep": task-specific facts/conventions (not general law)
             that must stay. They are put back under "GIVEN FACTS:" just before SCENARIO:.
    replace  task.json "closed_book_replace": {old text: new text} for wording that only makes
             sense when rules are shown (e.g. "a rule above"). Applied to the closed prompt only,
             so the open prompt and its hash never change.

    Everything else (the intro line, scenario, question, FINAL ANSWER line) is kept as is.
    """
    if prompt.count(RULES_MARKER) != 1:
        raise ValueError(f"prompt must contain exactly one {RULES_MARKER!r} section")
    start = prompt.index(RULES_MARKER)
    end = prompt.find(SCENARIO_MARKER, start)
    if end == -1:
        raise ValueError(f"prompt has no {SCENARIO_MARKER.strip()!r} after the rules section")
    intro, rest = prompt[:start], prompt[end + 1:]  # rest starts with "SCENARIO:"

    for old, new in (replace or {}).items():
        if rest.count(old) != 1:
            raise ValueError(f"closed_book_replace text {old!r} must appear exactly once "
                             f"after the rules section (found {rest.count(old)})")
        rest = rest.replace(old, new)

    if keep:
        if not all(isinstance(line, str) and line.strip() for line in keep):
            raise ValueError("closed_book_keep must be a list of non-empty strings")
        facts = "\n".join(f"- {line}" for line in keep)
        rest = f"{GIVEN_FACTS_HEADING}\n{facts}\n\n{rest}"
    return intro + rest


def prompt_for(task: dict, condition: str) -> str:
    """The exact text sent to the model for this task under this condition."""
    if condition == "open":
        return task["prompt"]
    if condition == "closed":
        return closed_book_prompt(task["prompt"], task.get("closed_book_keep"),
                                  task.get("closed_book_replace"))
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
        if not isinstance(task.get("closed_book_keep", []), list):
            raise ValueError(f"{path}: closed_book_keep must be a list of strings")
        if not isinstance(task.get("closed_book_replace", {}), dict):
            raise ValueError(f"{path}: closed_book_replace must be a {{old: new}} object")
        try:
            prompt_for(task, "closed")  # every task must support the closed condition
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
