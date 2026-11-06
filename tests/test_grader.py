"""Grader tests: no false passes, no false fails.

Each case is (model output, expected status). Expected amount is ₱2,258.88 unless noted.
"""

import pytest

from grader import extract_answer, grade

EXPECTED = "2258.88"


@pytest.mark.parametrize("response, status", [
    # --- correct answers in every accepted spelling -> pass
    ("FINAL ANSWER: ₱2,258.88", "pass"),
    ("FINAL ANSWER: ₱2258.88", "pass"),
    ("FINAL ANSWER: PHP 2,258.88", "pass"),
    ("FINAL ANSWER: PHP2258.88", "pass"),
    ("FINAL ANSWER: Php 2,258.88", "pass"),
    ("FINAL ANSWER: ₱ 2,258.88", "pass"),
    ("FINAL ANSWER: 2258.88", "pass"),
    ("FINAL ANSWER: ₱2,258.88.", "pass"),               # trailing period
    ("FINAL ANSWER: 2,258.88 PHP", "pass"),
    ("**FINAL ANSWER: ₱2,258.88**", "pass"),            # markdown bold
    ("FINAL ANSWER: **₱2,258.88**", "pass"),
    ("`FINAL ANSWER: ₱2,258.88`", "pass"),
    ("final answer: ₱2,258.88", "pass"),                # case-insensitive label
    ("FINAL ANSWER:₱2,258.88", "pass"),                 # no space
    ("FINAL ANSWER: ₱2,258.88   ", "pass"),             # trailing spaces
    ("Working\r\nFINAL ANSWER: ₱2,258.88\r\n", "pass"), # Windows line endings
    ("FINAL ANSWER: ₱2,258.89", "pass"),                # exactly at tolerance (0.01)
    ("FINAL ANSWER: ₱2,258.87", "pass"),

    # --- many numbers in the working; only the final line counts
    ("80 x 2.6 = 208\n640 x 2.6 = 1,664.00\n594.88\nTotal 2,258.88\nFINAL ANSWER: ₱2,258.88", "pass"),
    ("The total is ₱2,258.88.\nFINAL ANSWER: ₱2,204.80", "fail"),   # right number in text, wrong final
    ("FINAL ANSWER: ₱2,258.88\nWait, I made a mistake.\nFINAL ANSWER: ₱2,529.28", "fail"),  # last wins
    ("FINAL ANSWER: ₱2,529.28\nCorrection:\nFINAL ANSWER: ₱2,258.88", "pass"),

    # --- wrong amounts -> fail (not format_failure)
    ("FINAL ANSWER: PHP 2258.9", "fail"),               # 2258.90 is 0.02 off
    ("FINAL ANSWER: ₱2,258.90", "fail"),
    ("FINAL ANSWER: ₱2,258.86", "fail"),
    ("FINAL ANSWER: ₱2259", "fail"),                    # missing decimals parsed as 2259.00
    ("FINAL ANSWER: ₱225,888", "fail"),                 # valid commas, wrong magnitude
    ("FINAL ANSWER: ₱0.00", "fail"),

    # --- no usable final answer -> format_failure
    ("Total pay is ₱2,258.88", "format_failure"),       # correct number but no FINAL ANSWER line
    ("", "format_failure"),
    ("FINAL ANSWER:", "format_failure"),
    ("FINAL ANSWER: ₱", "format_failure"),
    ("FINAL ANSWER:\n₱2,258.88", "format_failure"),     # amount not on the same line
    ("FINAL ANSWER: ₱2,258.88 or ₱2,529.28", "format_failure"),  # two amounts: refuse to guess
    ("FINAL ANSWER: approximately ₱2,258.88", "format_failure"),
    ("FINAL ANSWER: ₱22,58.88", "format_failure"),      # invalid thousands grouping
    ("FINAL ANSWER: ₱2.258,88", "format_failure"),      # European format, ambiguous
    ("FINAL ANSWER: ₱2,258.885", "format_failure"),     # 3 decimals
    ("FINAL ANSWER: -₱2,258.88", "format_failure"),
    ("FINAL ANSWER: ₱2258.88\nFINAL ANSWER: N/A", "format_failure"),  # last one is unusable
    ("FINAL ANSWER = ₱2,258.88", "format_failure"),     # wrong separator
])
def test_grade(response, status):
    result = grade(response, EXPECTED)
    assert result["status"] == status, f"{response!r} -> {result}"
    assert result["score"] == (1 if status == "pass" else 0)


# ---------------------------------------------------------------------------
# Part A additions: "P" prefix, LaTeX wrappers, trailing label, format_reason
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("response", [
    # "P" / "P." peso prefix, common in the Philippines
    "FINAL ANSWER: P2,258.88",
    "FINAL ANSWER: P 2,258.88",
    "FINAL ANSWER: P.2,258.88",
    "FINAL ANSWER: P. 2,258.88",
    "FINAL ANSWER: **P2,258.88**",
    # LaTeX wrappers
    r"FINAL ANSWER: \boxed{2258.88}",
    r"FINAL ANSWER: \boxed{2,258.88}",
    r"FINAL ANSWER: \boxed{2{,}258.88}",
    r"FINAL ANSWER: $\text{₱}2,258.88$",
    r"FINAL ANSWER: \(\text{₱}2,258.88\)",
    r"FINAL ANSWER: $\boxed{\text{₱}2{,}258.88}$",
    r"FINAL ANSWER: \boxed{\text{PHP } 2,258.88}",
    # one short trailing label with no digits
    "FINAL ANSWER: ₱2,258.88 (total pay)",
    "FINAL ANSWER: ₱2,258.88 (total pay).",
    "FINAL ANSWER: P2,258.88 (Maria's total pay)",
    "FINAL ANSWER: ₱2,258.88 (two thousand...)",
])
def test_new_accepted_forms_pass(response):
    result = grade(response, EXPECTED)
    assert result["status"] == "pass", f"{response!r} -> {result}"
    assert result["format_reason"] is None


@pytest.mark.parametrize("response, reason", [
    # the new rules must not create false passes
    ("FINAL ANSWER: P2,258.88 or P2,529.28", "multiple_amounts"),
    (r"FINAL ANSWER: \boxed{2,258.88} or \boxed{2,529.28}", "multiple_amounts"),
    ("FINAL ANSWER: ₱2,258.88 (₱1,664.00 + ₱594.88)", "multiple_amounts"),  # digits in the label
    ("FINAL ANSWER: ₱2,258.88 (for 10 hours)", "multiple_amounts"),
    ("FINAL ANSWER: P2,258.88 (total pay for December 30th)", "multiple_amounts"),  # any digit -> rejected
    ("FINAL ANSWER: ₱2,258.88 (total) (approx)", "extra_text"),              # only ONE label allowed
    ("FINAL ANSWER: Pay is 2,258.88", "extra_text"),                        # "Pay" is not a "P" prefix
    ("FINAL ANSWER: PP2,258.88", "extra_text"),
    ("FINAL ANSWER: p2,258.88", "extra_text"),                              # lowercase p is not accepted
    ("FINAL ANSWER: approximately ₱2,258.88", "extra_text"),
    ("FINAL ANSWER: N/A", "extra_text"),
    ("Pay is 2,258.88", "no_final_line"),
    ("Total pay is P2,258.88", "no_final_line"),
    ("FINAL ANSWER = ₱2,258.88", "no_final_line"),
    ("", "no_final_line"),
    ("FINAL ANSWER:", "empty_answer"),
    ("FINAL ANSWER: ₱", "empty_answer"),
    ("FINAL ANSWER: P.", "empty_answer"),
    (r"FINAL ANSWER: \boxed{}", "empty_answer"),
    ("FINAL ANSWER:\n₱2,258.88", "empty_answer"),
    ("FINAL ANSWER: ₱22,58.88", "malformed_number"),
    ("FINAL ANSWER: ₱2.258,88", "malformed_number"),
    ("FINAL ANSWER: ₱2,258.885", "malformed_number"),
    ("FINAL ANSWER: P2,258.885", "malformed_number"),
])
def test_format_failure_reasons(response, reason):
    result = grade(response, EXPECTED)
    assert result["status"] == "format_failure", f"{response!r} -> {result}"
    assert result["format_reason"] == reason, f"{response!r} -> {result}"
    assert result["score"] == 0


def test_p_prefix_wrong_amount_is_fail_not_format():
    # A parsable but wrong answer must be "fail", with no format_reason.
    result = grade("FINAL ANSWER: P2,529.28", EXPECTED)
    assert result["status"] == "fail" and result["format_reason"] is None


def test_extracted_values_are_exact():
    assert str(extract_answer("FINAL ANSWER: ₱2,258.88")) == "2258.88"
    assert str(extract_answer("FINAL ANSWER: PHP 2258.9")) == "2258.9"
    assert str(extract_answer("FINAL ANSWER: ₱2259")) == "2259"
    assert extract_answer("no answer here") is None
    assert extract_answer(None) is None


def test_tolerance_boundary_has_no_float_error():
    # With floats, abs(2258.89 - 2258.88) = 0.010000000000218 > 0.01 -> false fail.
    # Decimal comparison must accept it.
    assert grade("FINAL ANSWER: ₱2,258.89", 2258.88, 0.01)["status"] == "pass"
    assert grade("FINAL ANSWER: ₱2,258.90", 2258.88, 0.01)["status"] == "fail"


def test_custom_tolerance():
    assert grade("FINAL ANSWER: ₱2,259.00", 2258.88, 0.50)["status"] == "pass"
    assert grade("FINAL ANSWER: ₱2,259.00", 2258.88, 0)["status"] == "fail"
    assert grade("FINAL ANSWER: ₱2,258.88", 2258.88, 0)["status"] == "pass"


def test_result_fields():
    r = grade("FINAL ANSWER: ₱2,258.88", 2258.88)
    assert r == {"status": "pass", "score": 1, "extracted": "2258.88", "expected": "2258.88",
                 "format_reason": None}
    r = grade("nothing", 2258.88)
    assert r["extracted"] is None and r["status"] == "format_failure"
    assert r["format_reason"] == "no_final_line"
