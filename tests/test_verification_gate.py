"""Tests for the task verification gate (Part C).

  * task.json must have "verified": true/false
  * run_eval.py skips drafts unless --include-drafts
  * report.py leaves drafts out unless --include-drafts, and marks them DRAFT
  * oracle_check.py fails a verified task whose source_refs are empty or contain TODO
"""

import json
import sys

import pytest

import oracle_check
import report
import run_eval
from tasks import load_tasks

TASK = load_tasks("task_01")[0]


def write_task(folder, **overrides):
    """Write a minimal valid task.json into folder/<id>/ and return its dict."""
    task = {"id": "task_x", "title": "t", "difficulty": "easy", "tags": ["a"],
            "prompt": "p", "expected_answer": 100, "verified": False}
    task.update(overrides)
    (folder / task["id"]).mkdir(parents=True)
    (folder / task["id"] / "task.json").write_text(json.dumps(task), encoding="utf-8")
    return task


# --- task.json schema ---------------------------------------------------------

def test_verified_field_is_required(tmp_path):
    task = write_task(tmp_path)
    del task["verified"]
    (tmp_path / "task_x" / "task.json").write_text(json.dumps(task), encoding="utf-8")
    with pytest.raises(ValueError, match="verified"):
        load_tasks("all", tasks_dir=tmp_path)


@pytest.mark.parametrize("bad", ["false", "yes", 0, 1, None])
def test_verified_must_be_a_boolean(tmp_path, bad):
    write_task(tmp_path, verified=bad)
    with pytest.raises(ValueError, match="true or false"):
        load_tasks("all", tasks_dir=tmp_path)


def test_real_tasks_all_have_verified_flag():
    for task in load_tasks("all"):
        assert isinstance(task["verified"], bool)


# --- oracle_check gate ----------------------------------------------------------

def verified_copy(**overrides):
    task = dict(TASK, verified=True)
    task.update(overrides)
    return task


def test_draft_with_todo_refs_is_ok():
    assert oracle_check.check_task(dict(TASK, verified=False)) == []


def test_verified_with_todo_refs_fails():
    problems = oracle_check.check_task(verified_copy(source_refs=["TODO(verify): p. ___"]))
    assert any("TODO" in p for p in problems)


def test_verified_with_empty_refs_fails():
    problems = oracle_check.check_task(verified_copy(source_refs=[]))
    assert any("source_refs is empty" in p for p in problems)


def test_verified_with_real_refs_passes():
    task = verified_copy(source_refs=["DOLE-BWC Handbook 2024, Part I, Sec. X, p. 12"])
    assert oracle_check.check_task(task) == []


def test_oracle_still_checks_draft_answers():
    # A draft with a wrong expected answer must still fail checks 1-3.
    problems = oracle_check.check_task(dict(TASK, verified=False, expected_answer=9999))
    assert any("calculator gives" in p for p in problems)


# --- run_eval gate ------------------------------------------------------------------

def only_draft_task(*_args, **_kwargs):
    """Stand-in for load_tasks(): one task, forced to be a draft.

    The gate tests must not depend on whether the real task_01 is verified yet.
    """
    return [dict(TASK, verified=False)]


@pytest.fixture
def fake_api(tmp_path, monkeypatch):
    monkeypatch.setattr(run_eval, "load_tasks", only_draft_task)
    monkeypatch.setattr(run_eval, "ROOT", tmp_path)
    monkeypatch.setattr(run_eval, "RAW_DIR", tmp_path / "results" / "raw")
    monkeypatch.setattr(run_eval, "STALE_DIR", tmp_path / "results" / "stale")
    monkeypatch.setattr(run_eval, "ERROR_LOG", tmp_path / "results" / "api_errors.jsonl")
    monkeypatch.setattr(run_eval, "load_config", lambda: {
        "models": ["m"], "trials_per_task": 1, "temperature": 0.0, "max_tokens": 100,
        "request_timeout_seconds": 5, "max_retries": 0,
        "backoff_base_seconds": 0, "backoff_max_seconds": 0})
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")
    calls = []

    class Resp:
        status_code, headers = 200, {}
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "FINAL ANSWER: ₱2,258.88"}}], "usage": {}}

    monkeypatch.setattr(run_eval.requests, "post", lambda *a, **k: calls.append(1) or Resp())
    return calls


def test_run_eval_refuses_drafts_by_default(fake_api, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_eval.py", "--tasks", "task_01"])
    with pytest.raises(SystemExit, match="No tasks to run"):
        run_eval.main()
    assert fake_api == []  # no API call made


def test_run_eval_runs_drafts_when_asked(fake_api, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_eval.py", "--tasks", "task_01", "--include-drafts"])
    run_eval.main()
    assert len(fake_api) == 1


# --- report gate ---------------------------------------------------------------------

@pytest.fixture
def report_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "load_tasks", only_draft_task)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "RAW_DIR", tmp_path / "results" / "raw")
    monkeypatch.setattr(report, "SUMMARY_MD", tmp_path / "results" / "summary.md")
    monkeypatch.setattr(report, "CHART_PNG", tmp_path / "results" / "pass_rate.png")
    monkeypatch.setattr(report, "TASKS_MD", tmp_path / "results" / "tasks_table.md")
    trial = tmp_path / "results" / "raw" / "m" / "task_01" / "trial_1.json"
    trial.parent.mkdir(parents=True)
    trial.write_text(json.dumps({"task_id": "task_01", "model": "m", "prompt": TASK["prompt"],
                                 "status": "pass", "passed": True, "settings": {}}), encoding="utf-8")
    return tmp_path


def test_report_excludes_drafts_by_default(report_sandbox, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["report.py"])
    with pytest.raises(SystemExit, match="include-drafts"):
        report.main()  # task_01 is the only task and it is a draft


def test_report_marks_drafts_when_included(report_sandbox, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["report.py", "--include-drafts"])
    report.main()
    md = (report_sandbox / "results" / "summary.md").read_text(encoding="utf-8")
    assert "DRAFT RESULTS INCLUDED" in md
    assert "task_01 (DRAFT)" in md


def test_tasks_table_lists_drafts_even_with_no_reportable_trials(report_sandbox, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["report.py"])
    with pytest.raises(SystemExit):
        report.main()  # no verified tasks -> nothing to report...
    table = (report_sandbox / "results" / "tasks_table.md").read_text(encoding="utf-8")
    assert "| [task_01](../tasks/task_01/task.json) |" in table  # ...but the table is still written
    assert "no (DRAFT)" in table
