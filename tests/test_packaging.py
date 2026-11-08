"""Tests for make_sample.py and make_submission.py (Part F). No git or network needed."""

import json
import sys
import zipfile

import pytest

import make_sample
import make_submission
from tasks import load_tasks

TASK = load_tasks("task_01")[0]
KEY = "sk-" + "or-"  # split so this test file never contains a key-like string


# --- make_submission: what is refused --------------------------------------------

@pytest.mark.parametrize("name", [
    ".env", "sub/.env",
    ".git/config", "__pycache__/grader.cpython-314.pyc", "tests/__pycache__/x.pyc",
    ".pytest_cache/v/cache", ".venv/bin/python",
    "results/api_errors.jsonl",
])
def test_forbidden_paths_are_refused(name):
    assert make_submission.problem_with(name, b"") is not None


def test_key_like_string_is_refused():
    assert make_submission.problem_with("config.yaml", f"key: {KEY}v1-abc".encode()) is not None


@pytest.mark.parametrize("name", [".env.example", "results/summary.md", "tasks/task_01/task.json",
                                  "results/sample/m/task_01/trial_1.json"])
def test_normal_files_are_allowed(name):
    assert make_submission.problem_with(name, b"plain text") is None


def test_check_zip_reports_files_and_problems(tmp_path):
    path = tmp_path / "s.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(make_submission.PREFIX + "README.md", "hello")
        z.writestr(make_submission.PREFIX + ".env", "OPENROUTER_API_KEY=x")
    files, problems = make_submission.check_zip(path)
    assert [n for n, _ in files] == ["README.md", ".env"]
    assert len(problems) == 1 and problems[0].startswith(".env")


def test_env_example_has_no_key_like_string():
    text = (make_submission.ROOT / ".env.example").read_text(encoding="utf-8")
    assert KEY not in text


# --- make_sample ----------------------------------------------------------------------

@pytest.fixture
def sample_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(make_sample, "ROOT", tmp_path)
    monkeypatch.setattr(make_sample, "RAW_DIR", tmp_path / "results" / "raw")
    monkeypatch.setattr(make_sample, "SAMPLE_DIR", tmp_path / "results" / "sample")
    return tmp_path


def write_raw(root, name, prompt, extra=""):
    path = root / "results" / "raw" / "m" / "open" / "task_01" / f"trial_{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"task_id": "task_01", "model": "m", "prompt": prompt,
                                "response": extra}), encoding="utf-8")


def test_sample_copies_current_skips_stale_and_key_like(sample_sandbox):
    write_raw(sample_sandbox, "1", TASK["prompt"])
    write_raw(sample_sandbox, "2", "an older prompt")
    write_raw(sample_sandbox, "3", TASK["prompt"], extra=KEY + "leaked")
    chosen, skipped = make_sample.select_trials([TASK])
    assert [p.name for p in chosen] == ["trial_1.json"]
    assert sorted(r for _, r in skipped) == ["contains an API-key-like string; NOT copied",
                                             "stale (prompt changed)"]


def test_sample_skips_drafts_by_default(sample_sandbox, monkeypatch):
    write_raw(sample_sandbox, "1", TASK["prompt"])
    monkeypatch.setattr(sys, "argv", ["make_sample.py"])
    monkeypatch.setattr(make_sample, "load_tasks", lambda _: [dict(TASK, verified=False)])
    with pytest.raises(SystemExit, match="No verified tasks"):
        make_sample.main()


def test_sample_mirrors_raw_and_keeps_gitkeep(sample_sandbox, monkeypatch):
    sample = sample_sandbox / "results" / "sample"
    (sample / "old_model").mkdir(parents=True)
    (sample / "old_model" / "junk.json").write_text("{}", encoding="utf-8")
    (sample / ".gitkeep").write_text("", encoding="utf-8")
    write_raw(sample_sandbox, "1", TASK["prompt"])
    monkeypatch.setattr(sys, "argv", ["make_sample.py"])
    monkeypatch.setattr(make_sample, "load_tasks", lambda _: [dict(TASK, verified=True)])
    make_sample.main()
    assert (sample / "m" / "open" / "task_01" / "trial_1.json").exists()
    assert (sample / ".gitkeep").exists()
    assert not (sample / "old_model").exists()  # old contents are cleared
