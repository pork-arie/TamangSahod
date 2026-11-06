"""Tests for resume/stale handling, per-model max_tokens, the cost cap, regrade and report filtering.

No real API calls: requests.post is replaced by a fake, and all files go to a temp folder.
"""

import json
import sys

import pytest

import regrade
import report
import run_eval
from tasks import load_tasks, prompt_sha256

TASK = load_tasks("task_01")[0]
MODEL = "test/model"

CFG = {
    "models": [MODEL], "trials_per_task": 2, "temperature": 0.0,
    "max_tokens": 4096, "max_tokens_overrides": {"test/reasoner": 16384},
    "request_timeout_seconds": 5, "max_retries": 0,
    "backoff_base_seconds": 0, "backoff_max_seconds": 0,
}


class FakeResponse:
    def __init__(self, text, cost=0.5):
        self.status_code = 200
        self.headers = {}
        self._body = {"model": MODEL, "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                      "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": cost}}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every results path at a temp folder and fake the API."""
    for module in (run_eval, regrade, report):
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "RAW_DIR", tmp_path / "results" / "raw")
    monkeypatch.setattr(run_eval, "STALE_DIR", tmp_path / "results" / "stale")
    monkeypatch.setattr(run_eval, "ERROR_LOG", tmp_path / "results" / "api_errors.jsonl")
    monkeypatch.setattr(run_eval, "load_config", lambda: dict(CFG))
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key-for-tests")

    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        return FakeResponse("work...\nFINAL ANSWER: ₱2,258.88")

    monkeypatch.setattr(run_eval.requests, "post", fake_post)
    return tmp_path, calls


def run_main(monkeypatch, *cli):
    monkeypatch.setattr(sys, "argv", ["run_eval.py", "--models", MODEL, "--tasks", "task_01", *cli])
    run_eval.main()


def saved(tmp_path, trial=1, model=MODEL):
    path = tmp_path / "results" / "raw" / run_eval.model_dirname(model) / "task_01" / f"trial_{trial}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# --- per-model max_tokens --------------------------------------------------

def test_max_tokens_default_and_override():
    assert run_eval.max_tokens_for("any/model", CFG) == 4096
    assert run_eval.max_tokens_for("test/reasoner", CFG) == 16384
    assert run_eval.max_tokens_for("any/model", {"max_tokens": 1000}) == 1000  # no overrides key


def test_override_is_sent_and_saved(sandbox, monkeypatch):
    tmp_path, calls = sandbox
    monkeypatch.setattr(sys, "argv", ["run_eval.py", "--models", "test/reasoner", "--tasks", "task_01",
                                      "--trials", "1"])
    run_eval.main()
    assert calls[0]["max_tokens"] == 16384
    assert saved(tmp_path, model="test/reasoner")["settings"] == {"temperature": 0.0, "max_tokens": 16384}


# --- what each trial record stores --------------------------------------------

def test_record_has_hash_answer_key_and_settings(sandbox, monkeypatch):
    tmp_path, _ = sandbox
    run_main(monkeypatch, "--trials", "1")
    rec = saved(tmp_path)
    assert rec["prompt_sha256"] == prompt_sha256(TASK["prompt"])
    assert rec["expected_answer"] == "2258.88"
    assert rec["settings"] == {"temperature": 0.0, "max_tokens": 4096}
    assert rec["status"] == "pass" and rec["format_reason"] is None
    assert "fake-key-for-tests" not in json.dumps(rec)  # the key is never saved


# --- resume and stale handling -------------------------------------------------

def test_resume_skips_trials_with_matching_prompt(sandbox, monkeypatch):
    tmp_path, calls = sandbox
    run_main(monkeypatch, "--trials", "2")
    assert len(calls) == 2
    run_main(monkeypatch, "--trials", "2")
    assert len(calls) == 2  # nothing re-run


def test_changed_prompt_moves_old_trial_to_stale_and_reruns(sandbox, monkeypatch):
    tmp_path, calls = sandbox
    run_main(monkeypatch, "--trials", "1")
    path = tmp_path / "results" / "raw" / run_eval.model_dirname(MODEL) / "task_01" / "trial_1.json"
    old = json.loads(path.read_text(encoding="utf-8"))
    old["prompt_sha256"] = "0" * 64                    # pretend it ran with an older prompt
    path.write_text(json.dumps(old), encoding="utf-8")

    run_main(monkeypatch, "--trials", "1")
    assert len(calls) == 2                              # re-ran
    stale = list((tmp_path / "results" / "stale").rglob("trial_1.*.json"))
    assert len(stale) == 1                              # old result kept, not deleted
    assert saved(tmp_path)["prompt_sha256"] == prompt_sha256(TASK["prompt"])


def test_legacy_trial_without_hash_uses_saved_prompt(tmp_path):
    # Trials saved before prompt_sha256 existed still have the full prompt text.
    path = tmp_path / "trial_1.json"
    path.write_text(json.dumps({"prompt": TASK["prompt"]}), encoding="utf-8")
    assert run_eval.is_current(path, TASK)
    path.write_text(json.dumps({"prompt": TASK["prompt"] + " edited"}), encoding="utf-8")
    assert not run_eval.is_current(path, TASK)


def test_unreadable_trial_is_treated_as_stale(tmp_path):
    path = tmp_path / "trial_1.json"
    path.write_text("{ half-written", encoding="utf-8")
    assert not run_eval.is_current(path, TASK)


# --- cost cap -------------------------------------------------------------------

def test_max_cost_stops_new_trials(sandbox, monkeypatch):
    tmp_path, calls = sandbox                           # each fake call reports $0.50
    run_main(monkeypatch, "--trials", "5", "--max-cost-usd", "1.00")
    assert len(calls) == 2                              # 0.50 + 0.50 reaches the 1.00 cap


def test_no_cost_cap_runs_everything(sandbox, monkeypatch):
    tmp_path, calls = sandbox
    run_main(monkeypatch, "--trials", "3")
    assert len(calls) == 3


# --- regrade ---------------------------------------------------------------------

def _write_trial(tmp_path, response, status, extracted, prompt=None):
    path = tmp_path / "results" / "raw" / "m" / "task_01" / "trial_1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"task_id": "task_01", "model": "m", "trial": 1, "prompt": prompt or TASK["prompt"],
              "response": response, "status": status, "extracted_answer": extracted,
              "expected_answer": "2258.88", "passed": status == "pass", "score": int(status == "pass")}
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_regrade_applies_current_grader(sandbox, monkeypatch):
    tmp_path, _ = sandbox
    # Graded format_failure by the OLD grader (no "P" prefix support); the current one passes it.
    path = _write_trial(tmp_path, "FINAL ANSWER: P2,258.88", "format_failure", None)
    monkeypatch.setattr(sys, "argv", ["regrade.py"])
    regrade.main()
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["status"] == "pass" and rec["passed"] is True and rec["extracted_answer"] == "2258.88"
    assert rec["previous_grade"]["status"] == "format_failure"
    assert rec["prompt_sha256"] == prompt_sha256(TASK["prompt"])


def test_regrade_dry_run_writes_nothing(sandbox, monkeypatch):
    tmp_path, _ = sandbox
    path = _write_trial(tmp_path, "FINAL ANSWER: P2,258.88", "format_failure", None)
    before = path.read_text(encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["regrade.py", "--dry-run"])
    regrade.main()
    assert path.read_text(encoding="utf-8") == before


def test_regrade_skips_stale_trials(sandbox, monkeypatch):
    tmp_path, _ = sandbox
    path = _write_trial(tmp_path, "FINAL ANSWER: P2,258.88", "format_failure", None,
                        prompt="an older prompt")
    before = path.read_text(encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["regrade.py"])
    regrade.main()
    assert path.read_text(encoding="utf-8") == before


# --- report filtering ------------------------------------------------------------

def test_report_ignores_stale_and_unknown_tasks(sandbox):
    tmp_path, _ = sandbox
    raw = tmp_path / "results" / "raw" / "m"
    for task_id, prompt, name in [("task_01", TASK["prompt"], "current"),
                                  ("task_01", "an older prompt", "stale"),
                                  ("task_99", "whatever", "unknown")]:
        p = raw / task_id / f"trial_{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"task_id": task_id, "model": "m", "prompt": prompt}), encoding="utf-8")

    kept, ignored = report.load_trials([TASK])
    assert len(kept) == 1 and kept[0]["prompt"] == TASK["prompt"]
    reasons = sorted(reason for _, reason in ignored)
    assert reasons == ["prompt changed since this trial ran (stale)", "task no longer exists"]


def test_report_warns_on_mixed_settings():
    trials = [{"model": "m", "settings": {"max_tokens": 4096}},
              {"model": "m", "settings": {"max_tokens": 16384}},
              {"model": "n", "settings": {"max_tokens": 4096}}]
    warnings = report.settings_warnings(trials)
    assert len(warnings) == 1 and warnings[0].startswith("m:")
