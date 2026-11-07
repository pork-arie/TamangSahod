"""Build submission.zip from COMMITTED, tracked files only, then check it.

How it works:
  1. `git archive HEAD` writes every tracked file of the last commit into a ZIP.
     Untracked or git-ignored files (.env, results/raw/, caches) can't get in this way.
  2. The ZIP is opened again and checked. If ANY of these are inside, the ZIP is
     deleted and the script stops with an error:
       .env, .git/, __pycache__/, .pytest_cache/, .venv/, results/api_errors.jsonl,
       or any file containing the text "sk-" + "or-" (OpenRouter key prefix)
  3. It prints the file list and the size, and fails if the ZIP is 50 MB or more.

Uncommitted changes are NOT in the ZIP. The script warns you if there are any, so commit first.

  python make_submission.py
"""

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP_PATH = ROOT / "submission.zip"
PREFIX = ROOT.name + "/"            # every file sits inside one top folder in the ZIP
MAX_BYTES = 50 * 1024 * 1024        # 50 MB
KEY_PREFIX = "sk-" + "or-"          # written in two parts so this file itself passes the check
FORBIDDEN_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv"}
FORBIDDEN_FILES = {"results/api_errors.jsonl"}


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def problem_with(name: str, data: bytes):
    """Why this ZIP entry must not be submitted, or None if it is fine.

    name is the path inside the project, e.g. "results/summary.md".
    """
    parts = name.split("/")
    if parts[-1] == ".env":
        return ".env file (secrets)"
    if FORBIDDEN_DIRS & set(parts):
        return f"inside a forbidden folder {sorted(FORBIDDEN_DIRS & set(parts))}"
    if name in FORBIDDEN_FILES:
        return "error log (may contain API responses)"
    if KEY_PREFIX.encode() in data:
        return f"contains '{KEY_PREFIX}' (looks like an API key)"
    return None


def check_zip(path: Path):
    """Return (list of (name, size), list of problems) for the ZIP at path."""
    files, problems = [], []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename.removeprefix(PREFIX)
            files.append((name, info.file_size))
            reason = problem_with(name, z.read(info))
            if reason:
                problems.append(f"{name}: {reason}")
    return files, problems


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore  # so ₱ prints on Windows; Pylance thinks stdout lacks reconfigure()

    dirty = git("status", "--porcelain").rstrip()  # rstrip: keep the leading status columns
    if dirty:
        print("WARNING: you have uncommitted changes. They will NOT be in the ZIP:")
        print("\n".join("  " + line for line in dirty.splitlines()))
        print("  Commit them first if they should be submitted.\n")

    git("archive", "--format=zip", f"--prefix={PREFIX}", "-o", str(ZIP_PATH), "HEAD")
    files, problems = check_zip(ZIP_PATH)
    size = ZIP_PATH.stat().st_size

    if size >= MAX_BYTES:
        problems.append(f"ZIP is {size / 1024 / 1024:.1f} MB; the limit is 50 MB")
    if problems:
        ZIP_PATH.unlink()
        print("ABORTED: submission.zip was deleted because:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print(f"Files in {ZIP_PATH.name} ({len(files)}):")
    for name, file_size in files:
        print(f"  {file_size:>10,} B  {name}")
    print(f"\nOK: {ZIP_PATH.name} is {size / 1024 / 1024:.2f} MB (limit 50 MB), "
          f"built from commit {git('rev-parse', '--short', 'HEAD').strip()}.")


if __name__ == "__main__":
    main()
