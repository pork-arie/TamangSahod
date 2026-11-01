"""Run the eval: send each task prompt to each model, k times, grade, and save.

Examples:
  python run_eval.py                                  # everything from config.yaml
  python run_eval.py --models openai/gpt-4o --tasks task_01 --trials 3
  python run_eval.py --models a/x,b/y --tasks all

Each trial is saved as its own JSON file:
  results/raw/<model>/<task_id>/trial_<n>.json
If that file already exists, the trial is skipped. That is how resuming works.

API problems (rate limits, timeouts, 5xx, malformed responses) are retried with
exponential backoff. If retries run out, the trial is logged to
results/api_errors.jsonl and NOT saved. It is never counted as a model
failure, and the next run will try it again.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from grader import grade
from tasks import load_tasks

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "results" / "raw"
ERROR_LOG = ROOT / "results" / "api_errors.jsonl"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# HTTP codes worth retrying: request timeout, rate limit, and server-side errors.
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class ApiError(Exception):
    """The API call failed for reasons that are not the model's fault.

    fatal=True means retrying cannot help (bad key, bad model id, no credit),
    so the remaining trials for that model are skipped.
    """

    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal


def load_config(path=ROOT / "config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def model_dirname(model: str) -> str:
    """'openai/gpt-4o' -> 'openai__gpt-4o' (safe as a folder name on every OS)."""
    return model.replace("/", "__").replace(":", "_")


def trial_path(model: str, task_id: str, trial: int) -> Path:
    return RAW_DIR / model_dirname(model) / task_id / f"trial_{trial}.json"


def call_model(api_key, model, prompt, cfg):
    """Send one chat request with retries. Returns (response_json, latency_seconds)."""
    headers = {
        "Authorization": f"Bearer {api_key}",  # the key is only ever sent here, never printed
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "usage": {"include": True},  # ask OpenRouter to report token counts + cost
    }

    last_error = None
    retry_after = 0  # seconds the server asked us to wait (Retry-After header), if any
    for attempt in range(cfg["max_retries"] + 1):
        if attempt > 0:
            wait = min(cfg["backoff_max_seconds"], cfg["backoff_base_seconds"] * 2 ** (attempt - 1))
            wait = max(wait, retry_after)  # never retry sooner than the server asked
            wait += random.uniform(0, 1)  # jitter so parallel runs don't retry in lockstep
            print(f"    retry {attempt}/{cfg['max_retries']} in {wait:.1f}s ({last_error})")
            time.sleep(wait)

        start = time.monotonic()
        try:
            resp = requests.post(API_URL, headers=headers, json=body,
                                 timeout=cfg["request_timeout_seconds"])
        except requests.RequestException as e:  # DNS, connection reset, timeout...
            last_error = f"network: {type(e).__name__}"
            continue
        latency = time.monotonic() - start

        if resp.status_code in RETRYABLE_STATUS:
            last_error = f"HTTP {resp.status_code}"
            try:
                retry_after = min(float(resp.headers.get("Retry-After", 0)), 300)
            except ValueError:  # header can also be a date string; fall back to backoff
                retry_after = 0
            continue
        if resp.status_code != 200:
            # 400/401/402/404 etc. are config problems (bad model id, no credit,
            # bad key). Retrying will not help, so stop immediately.
            raise ApiError(f"HTTP {resp.status_code}: {resp.text[:300]}", fatal=True)

        try:
            data = resp.json()
        except ValueError:
            last_error = "invalid JSON body"
            continue
        # OpenRouter can return HTTP 200 with an "error" object (e.g. upstream provider failure).
        if "error" in data:
            last_error = f"provider error: {str(data['error'])[:200]}"
            continue
        if not data.get("choices"):
            last_error = "response had no choices"
            continue
        return data, latency

    raise ApiError(f"gave up after {cfg['max_retries']} retries: {last_error}")


def run_trial(api_key, model, task, trial, cfg):
    """Call the model once, grade it, and return the record to save."""
    data, latency = call_model(api_key, model, task["prompt"], cfg)
    choice = data["choices"][0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    usage = data.get("usage") or {}
    result = grade(content, task["expected_answer"], task["tolerance"])

    return {
        "task_id": task["id"],
        "model": model,
        "served_model": data.get("model"),     # exact model/version OpenRouter actually used
        "provider": data.get("provider"),
        "trial": trial,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "settings": {"temperature": cfg["temperature"], "max_tokens": cfg["max_tokens"]},
        "prompt": task["prompt"],
        "response": content,                   # the only text the grader sees
        "reasoning": message.get("reasoning"), # hidden thinking, if the model/provider returns it
        "finish_reason": choice.get("finish_reason"),  # "length" = cut off by max_tokens
        "expected_answer": result["expected"],
        "extracted_answer": result["extracted"],
        "status": result["status"],            # pass | fail | format_failure
        "passed": result["status"] == "pass",
        "score": result["score"],
        "latency_seconds": round(latency, 3),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cost_usd": usage.get("cost"),      # reported by OpenRouter when usage.include=true
        },
    }


def save_json(path: Path, record: dict):
    """Write to a temp file then rename, so an interrupted run never leaves a half-written trial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def log_api_error(model, task_id, trial, message):
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model, "task_id": task_id, "trial": trial, "error": message,
        }) + "\n")


def parse_args(cfg):
    p = argparse.ArgumentParser(description="Run the PH payroll eval via OpenRouter.")
    p.add_argument("--models", help="comma-separated OpenRouter model ids (default: config.yaml)")
    p.add_argument("--tasks", default="all", help='"all" or comma-separated task ids')
    p.add_argument("--trials", type=int, default=cfg["trials_per_task"], help="trials per task per model")
    args = p.parse_args()
    args.models = [m.strip() for m in args.models.split(",")] if args.models else cfg["models"]
    return args


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # so ₱ prints on Windows consoles too
    cfg = load_config()
    args = parse_args(cfg)
    tasks = load_tasks(args.tasks)

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")

    totals = {"new": 0, "skipped": 0, "api_errors": 0, "prompt_tokens": 0,
              "completion_tokens": 0, "cost_usd": 0.0, "cost_missing": 0}

    for model in args.models:
        print(f"\n=== {model} ===")
        model_broken = False
        for task in tasks:
            for trial in range(1, args.trials + 1):
                path = trial_path(model, task["id"], trial)
                if path.exists():
                    totals["skipped"] += 1
                    continue
                if model_broken:
                    break
                print(f"  {task['id']} trial {trial} ...", end=" ", flush=True)
                try:
                    record = run_trial(api_key, model, task, trial, cfg)
                except ApiError as e:
                    print("API ERROR (not counted; rerun to retry)")
                    log_api_error(model, task["id"], trial, str(e))
                    totals["api_errors"] += 1
                    if e.fatal:
                        print(f"    {e}\n    -> skipping remaining trials for {model}")
                        model_broken = True
                    continue

                save_json(path, record)
                totals["new"] += 1
                u = record["usage"]
                totals["prompt_tokens"] += u["prompt_tokens"] or 0
                totals["completion_tokens"] += u["completion_tokens"] or 0
                if u["cost_usd"] is None:
                    totals["cost_missing"] += 1
                else:
                    totals["cost_usd"] += u["cost_usd"]
                truncated = " (truncated: hit max_tokens)" if record["finish_reason"] == "length" else ""
                print(f"{record['status']:<15} got={record['extracted_answer']} "
                      f"({record['latency_seconds']}s){truncated}")

    print("\n--- Run summary (this run only) ---")
    print(f"new trials:        {totals['new']}")
    print(f"skipped (resumed): {totals['skipped']}")
    print(f"API errors:        {totals['api_errors']}" + ("  -> see results/api_errors.jsonl" if totals["api_errors"] else ""))
    print(f"prompt tokens:     {totals['prompt_tokens']:,}")
    print(f"completion tokens: {totals['completion_tokens']:,}")
    cost_note = f"  ({totals['cost_missing']} trial(s) had no cost reported)" if totals["cost_missing"] else ""
    print(f"cost (USD):        ${totals['cost_usd']:.4f}{cost_note}")
    print("\nNext: python report.py")


if __name__ == "__main__":
    main()
