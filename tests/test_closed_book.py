"""Tests for the closed-book condition (RULES section removed from the prompt).

No real API calls: requests.post is faked, and all files go to a temp folder.
"""

import json
import sys

import pytest

import make_sample
import oracle_check
import regrade
import report
import run_eval
from tasks import (CONDITIONS, closed_book_prompt, load_tasks, prompt_for, prompt_sha256,
                   trial_condition)

ALL_TASKS = load_tasks("all")
TASK = load_tasks("task_01")[0]
MODEL = "test/model"


# --- building the closed prompt ------------------------------------------------------

def test_closed_prompt_removes_exactly_the_rules_section():
    open_p, closed_p = TASK["prompt"], prompt_for(TASK, "closed")
    assert "RULES" not in closed_p
    assert "Hourly rate = daily rate" in open_p and "Hourly rate = daily rate" not in closed_p
    intro = open_p[:open_p.index("RULES (")]
    scenario_on = open_p[open_p.index("SCENARIO:"):]
    assert closed_p == intro + scenario_on     # intro and everything from SCENARIO: kept verbatim


@pytest.mark.parametrize("task", ALL_TASKS, ids=[t["id"] for t in ALL_TASKS])
def test_every_task_has_a_valid_closed_prompt(task):
    closed_p = prompt_for(task, "closed")
    assert "RULES" not in closed_p
    assert closed_p.startswith("You are computing pay under Philippine labor law")
    assert "SCENARIO:" in closed_p and "QUESTION:" in closed_p
    assert closed_p.rstrip().endswith("FINAL ANSWER: ₱<amount with 2 decimals>")
    assert len(closed_p) < len(task["prompt"])
    assert "above" not in closed_p.lower()       # nothing points at rules that are not shown
    for fact in task.get("closed_book_keep", []):
        assert f"- {fact}" in closed_p
    assert oracle_check.check_task(task) == []   # includes the closed-prompt check


# --- closed_book_keep / closed_book_replace ---------------------------------------------

MINI = ("Intro line.\n\nRULES (x):\n- general law A\n- convention B\n\n"
        "SCENARIO:\nPaid except where a rule above says so.\n\nQUESTION:\nq?\n\n"
        "FINAL ANSWER: ₱<amount with 2 decimals>")


def test_kept_facts_go_under_given_facts_just_before_scenario():
    closed = closed_book_prompt(MINI, keep=["convention B"])
    assert closed.startswith("Intro line.\n\nGIVEN FACTS:\n- convention B\n\nSCENARIO:\n")
    assert "general law A" not in closed


def test_no_given_facts_heading_when_nothing_is_kept():
    assert "GIVEN FACTS" not in closed_book_prompt(MINI)


def test_replace_applies_to_closed_prompt_only():
    task = {"prompt": MINI, "closed_book_replace": {"a rule above": "the applicable rules"}}
    assert "except where the applicable rules says so" in prompt_for(task, "closed")
    assert prompt_for(task, "open") == MINI            # open prompt, and so its hash, unchanged


def test_replace_text_must_exist_exactly_once():
    with pytest.raises(ValueError, match="exactly once"):
        closed_book_prompt(MINI, replace={"not in the prompt": "x"})


def test_replace_never_touches_the_removed_rules_or_kept_facts():
    # "convention B" sits inside RULES, which is cut before replacing, so it is "not found"
    with pytest.raises(ValueError, match="exactly once"):
        closed_book_prompt(MINI, replace={"convention B": "x"})


def test_empty_kept_fact_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        closed_book_prompt(MINI, keep=["  "])


def test_load_tasks_validates_closed_book_fields(tmp_path):
    folder = tmp_path / "task_x"
    folder.mkdir()
    base = {"id": "task_x", "title": "t", "difficulty": "easy", "tags": [], "verified": False,
            "expected_answer": 1, "prompt": MINI}
    for bad in ({"closed_book_keep": "one string"}, {"closed_book_replace": ["a", "b"]},
                {"closed_book_replace": {"missing text": "x"}}):
        (folder / "task.json").write_text(json.dumps({**base, **bad}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_tasks("all", tasks_dir=tmp_path)


def test_oracle_flags_above_and_missing_kept_fact():
    task = dict(TASK)
    task["closed_book_replace"] = {"Compute Maria": "Using the rules above, compute Maria"}
    assert any("above" in p for p in oracle_check.check_task(task))
    task = dict(TASK)
    task["closed_book_keep"] = ["a fact"]
    task_prompt_for = prompt_for(task, "closed")
    assert "- a fact" in task_prompt_for and oracle_check.check_task(task) == []


def test_closed_book_fields_do_not_change_open_hashes():
    # The open prompt is task["prompt"] verbatim, whatever the closed_book_* fields say.
    for task in ALL_TASKS:
        bare = {k: v for k, v in task.items() if not k.startswith("closed_book_")}
        assert prompt_sha256(prompt_for(task, "open")) == prompt_sha256(prompt_for(bare, "open"))


def test_open_condition_is_the_prompt_unchanged():
    assert prompt_for(TASK, "open") == TASK["prompt"]


def test_open_and_closed_hashes_differ():
    assert prompt_sha256(prompt_for(TASK, "open")) != prompt_sha256(prompt_for(TASK, "closed"))


@pytest.mark.parametrize("bad", [
    "no rules here\n\nSCENARIO:\nx",                           # no RULES section
    "intro\n\nRULES (a):\n- r\n\nQUESTION:\nq",                 # no SCENARIO after rules
    "RULES (a):\n- r\nRULES (b):\n- r\n\nSCENARIO:\nx",         # two RULES sections
])
def test_malformed_prompts_are_rejected(bad):
    with pytest.raises(ValueError):
        closed_book_prompt(bad)


def test_load_tasks_rejects_task_without_rules_section(tmp_path):
    folder = tmp_path / "task_x"
    folder.mkdir()
    (folder / "task.json").write_text(json.dumps({
        "id": "task_x", "title": "t", "difficulty": "easy", "tags": [], "verified": False,
        "expected_answer": 1, "prompt": "no rules\n\nSCENARIO:\nx"}), encoding="utf-8")
    with pytest.raises(ValueError, match="closed-book"):
        load_tasks("all", tasks_dir=tmp_path)


def test_unknown_condition_is_rejected():
    with pytest.raises(ValueError, match="condition"):
        prompt_for(TASK, "half-open")
    assert CONDITIONS == ("open", "closed")


def test_trials_without_condition_field_count_as_open():
    assert trial_condition({}) == "open"
    assert trial_condition({"condition": "closed"}) == "closed"


# --- run_eval --condition -----------------------------------------------------------------

CFG = {"models": [MODEL], "trials_per_task": 1, "temperature": 0.0, "max_tokens": 100,
       "request_timeout_seconds": 5, "max_retries": 0,
       "backoff_base_seconds": 0, "backoff_max_seconds": 0}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    for module in (run_eval, regrade, report):
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "RAW_DIR", tmp_path / "results" / "raw")
    monkeypatch.setattr(report, "SUMMARY_MD", tmp_path / "results" / "summary.md")
    monkeypatch.setattr(report, "CHART_PNG", tmp_path / "results" / "pass_rate.png")
    monkeypatch.setattr(report, "TASKS_MD", tmp_path / "results" / "tasks_table.md")
    monkeypatch.setattr(report, "load_tasks", lambda *_a, **_k: [TASK])
    monkeypatch.setattr(run_eval, "STALE_DIR", tmp_path / "results" / "stale")
    monkeypatch.setattr(run_eval, "ERROR_LOG", tmp_path / "results" / "api_errors.jsonl")
    monkeypatch.setattr(run_eval, "load_config", lambda: dict(CFG))
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")

    sent = []
    answer = {"text": "FINAL ANSWER: ₱2,258.88"}

    class Resp:
        status_code, headers, text = 200, {}, ""

        def json(self):
            return {"choices": [{"message": {"content": answer["text"]}, "finish_reason": "stop"}],
                    "usage": {}}

    def fake_post(url, headers, json, timeout):
        sent.append(json["messages"][0]["content"])
        return Resp()

    monkeypatch.setattr(run_eval.requests, "post", fake_post)
    return tmp_path, sent, answer


def run(monkeypatch, *cli):
    monkeypatch.setattr(sys, "argv", ["run_eval.py", "--models", MODEL, "--tasks", "task_01", *cli])
    run_eval.main()


def test_closed_run_sends_closed_prompt_and_saves_condition(sandbox, monkeypatch):
    tmp_path, sent, _ = sandbox
    run(monkeypatch, "--condition", "closed")
    assert sent == [prompt_for(TASK, "closed")]
    path = run_eval.trial_path(MODEL, "closed", "task_01", 1)
    assert "closed" in path.parts                       # condition is part of the results path
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["condition"] == "closed"
    assert rec["prompt"] == prompt_for(TASK, "closed")
    assert rec["prompt_sha256"] == prompt_sha256(prompt_for(TASK, "closed"))
    assert rec["expected_answer"] == "2258.88"          # same answer key as open


def test_default_condition_is_open(sandbox, monkeypatch):
    tmp_path, sent, _ = sandbox
    run(monkeypatch)
    assert sent == [TASK["prompt"]]
    assert run_eval.trial_path(MODEL, "open", "task_01", 1).exists()


def test_conditions_resume_independently(sandbox, monkeypatch):
    tmp_path, sent, _ = sandbox
    run(monkeypatch, "--condition", "open")
    run(monkeypatch, "--condition", "closed")
    assert len(sent) == 2                                # closed is not "already done" because open is
    run(monkeypatch, "--condition", "closed")
    run(monkeypatch, "--condition", "open")
    assert len(sent) == 2                                # both resumed, nothing re-run


def test_open_trial_in_closed_folder_is_stale(sandbox, monkeypatch):
    tmp_path, sent, _ = sandbox
    path = run_eval.trial_path(MODEL, "closed", "task_01", 1)
    path.parent.mkdir(parents=True)
    # A trial whose hash is the OPEN prompt's hash does not count for the closed condition.
    path.write_text(json.dumps({"prompt": TASK["prompt"], "prompt_sha256": prompt_sha256(TASK["prompt"]),
                                "condition": "closed"}), encoding="utf-8")
    assert not run_eval.is_current(path, TASK, "closed")
    run(monkeypatch, "--condition", "closed")
    assert len(sent) == 1
    assert list((tmp_path / "results" / "stale" / run_eval.model_dirname(MODEL) / "closed").rglob("*.json"))


# --- report: open vs closed side by side -------------------------------------------------

def test_report_shows_open_and_closed_side_by_side(sandbox, monkeypatch):
    tmp_path, _, answer = sandbox
    run(monkeypatch, "--condition", "open")              # passes
    answer["text"] = "FINAL ANSWER: ₱2,000.00"
    run(monkeypatch, "--condition", "closed")            # fails
    monkeypatch.setattr(sys, "argv", ["report.py"])
    report.main()
    md = (tmp_path / "results" / "summary.md").read_text(encoding="utf-8")
    assert "## Open vs closed book" in md
    assert f"| `{MODEL}` | 100% (1/1) | 0% (0/1) | -100 pp |" in md
    assert f"| task_01 | medium | 1/1 | 0/1 |" in md        # per task: open column then closed column
    assert f"`{MODEL}` open | `{MODEL}` closed" in md
    assert (tmp_path / "results" / "pass_rate.png").exists()


def test_report_condition_flag_shows_only_that_condition(sandbox, monkeypatch):
    tmp_path, _, answer = sandbox
    run(monkeypatch, "--condition", "open")
    answer["text"] = "FINAL ANSWER: ₱2,000.00"
    run(monkeypatch, "--condition", "closed")
    monkeypatch.setattr(sys, "argv", ["report.py", "--condition", "closed"])
    report.main()
    md = (tmp_path / "results" / "summary.md").read_text(encoding="utf-8")
    assert "Open vs closed" not in md
    assert f"| `{MODEL}` | closed | 0% (0/1)" in md
    assert "| open |" not in md


def test_report_ignores_closed_trial_with_stale_hash(sandbox):
    tmp_path, _, _ = sandbox
    path = tmp_path / "results" / "raw" / "m" / "closed" / "task_01" / "trial_1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"task_id": "task_01", "model": "m", "condition": "closed",
                                "prompt": "an older closed prompt"}), encoding="utf-8")
    kept, ignored = report.load_trials([TASK])
    assert kept == [] and ignored[0][1] == "prompt changed since this trial ran (stale)"


# --- regrade and make_sample follow the condition ----------------------------------------------

def test_regrade_uses_closed_prompt_hash(sandbox, monkeypatch):
    tmp_path, _, _ = sandbox
    path = tmp_path / "results" / "raw" / "m" / "closed" / "task_01" / "trial_1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "task_id": "task_01", "model": "m", "trial": 1, "condition": "closed",
        "prompt": prompt_for(TASK, "closed"), "response": "FINAL ANSWER: P2,258.88",
        "status": "format_failure", "extracted_answer": None, "expected_answer": "2258.88"}),
        encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["regrade.py"])
    regrade.main()
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["status"] == "pass" and rec["condition"] == "closed"


def test_make_sample_copies_both_conditions(tmp_path, monkeypatch):
    monkeypatch.setattr(make_sample, "RAW_DIR", tmp_path / "raw")
    for cond in CONDITIONS:
        path = tmp_path / "raw" / "m" / cond / "task_01" / "trial_1.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"task_id": "task_01", "model": "m", "condition": cond,
                                    "prompt": prompt_for(TASK, cond)}), encoding="utf-8")
    chosen, skipped = make_sample.select_trials([TASK])
    assert sorted(p.parts[-3] for p in chosen) == ["closed", "open"] and skipped == []
