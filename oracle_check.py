"""Oracle check: prove every task is solvable and the grader accepts correct answers.

For each task this runs three checks:
  1. The task's expected_answer, written as a perfect final line, is graded "pass".
  2. The reference calculator (run on the task's reference_inputs) gives the
     same amount as expected_answer, and that output is graded "pass" too.
  3. A deliberately wrong answer (expected + ₱1.00) is graded "fail", which
     shows the grader is not just passing everything.

Run:  python oracle_check.py      (exit code 0 = all good, 1 = something failed)
"""

import sys
from decimal import Decimal

from grader import grade
from reference.calculator import compute_from_inputs
from tasks import load_tasks


def check_task(task):
    """Return a list of problem strings for one task (empty list = all checks passed)."""
    problems = []
    expected = Decimal(str(task["expected_answer"]))
    tol = task["tolerance"]

    # 1. expected answer passes the grader
    perfect = f"Working...\nFINAL ANSWER: ₱{expected:,.2f}"
    if grade(perfect, expected, tol)["status"] != "pass":
        problems.append("expected_answer was NOT accepted by the grader")

    # 2. reference calculator agrees and passes
    if "reference_inputs" not in task:
        problems.append("no reference_inputs; cannot cross-check with the calculator")
    else:
        calc = compute_from_inputs(task["reference_inputs"])
        if abs(calc - expected) > Decimal(str(tol)):
            problems.append(f"calculator gives {calc}, task expects {expected}")
        if grade(f"FINAL ANSWER: ₱{calc:,.2f}", expected, tol)["status"] != "pass":
            problems.append("calculator output was NOT accepted by the grader")

    # 3. a wrong answer fails
    wrong = f"FINAL ANSWER: ₱{expected + 1:,.2f}"
    if grade(wrong, expected, tol)["status"] != "fail":
        problems.append("grader accepted a wrong answer (expected + 1.00)")

    return problems


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # so ₱ prints on Windows consoles too
    tasks = load_tasks("all")
    all_ok = True
    for task in tasks:
        problems = check_task(task)
        mark = "OK  " if not problems else "FAIL"
        print(f"[{mark}] {task['id']}  expected ₱{Decimal(str(task['expected_answer'])):,.2f}")
        for p in problems:
            print(f"        - {p}")
        all_ok = all_ok and not problems
    print(f"\n{len(tasks)} task(s) checked: {'ALL PASSED' if all_ok else 'FAILURES FOUND'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
