"""Grade a model response against a task's expected peso amount.

Rules:
  * Only the LAST occurrence of "FINAL ANSWER:" counts. Numbers anywhere else
    in the response (the working) are ignored.
  * The text after "FINAL ANSWER:" on that line must be exactly ONE amount,
    optionally with a currency marker (₱, PHP, Php) and light markdown
    (**bold**, `code`). Anything else (two amounts, words, a range, a missing
    amount) is a "format_failure", not a wrong answer. We would rather report a
    format problem than guess which number the model meant.
  * Commas must be valid thousands separators ("2,258.88" ok, "22,58.88" not).
  * Missing decimals are fine: "₱2259" -> 2259.00, "PHP 2258.9" -> 2258.90.
  * Pass if |answer - expected| <= tolerance. Comparison uses Decimal so that
    float rounding can never turn an exact-tolerance answer into a false fail.

Statuses: "pass", "fail" (wrong amount), "format_failure" (no parsable final answer).
Score: 1 for pass, 0 otherwise.
"""

import re
from decimal import Decimal, InvalidOperation

DEFAULT_TOLERANCE = Decimal("0.01")

# Finds every "FINAL ANSWER:" (any case) and captures the rest of that line.
_FINAL_LINE = re.compile(r"FINAL\s+ANSWER\s*:(?P<rest>[^\r\n]*)", re.IGNORECASE)

# The amount itself. Either a plain number ("2258.88") or one with valid
# thousands separators ("2,258.88"). Up to 2 decimal places, or 1-2 digits.
_AMOUNT = re.compile(
    r"""^
    (?:₱|PHP|Php|php)?\s*              # optional currency marker before
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?   # 2,258.88 / 1,000
          |\d+(?:\.\d{1,2})?)                  # 2258.88 / 2259 / 2258.9
    \s*(?:PHP|php|pesos)?              # optional currency word after
    \.?                                # tolerate a sentence-ending period
    $""",
    re.VERBOSE,
)

# Markdown/LaTeX-ish decoration that models commonly wrap the answer in.
_DECORATION = re.compile(r"[*_`]|\\\(|\\\)|\$")


def extract_answer(response: str):
    """Return the amount (Decimal) from the last FINAL ANSWER line, or None."""
    if not response:
        return None
    matches = list(_FINAL_LINE.finditer(response))
    if not matches:
        return None

    rest = matches[-1].group("rest")
    rest = _DECORATION.sub("", rest).strip()

    m = _AMOUNT.match(rest)
    if not m:
        return None
    try:
        return Decimal(m.group("num").replace(",", ""))
    except InvalidOperation:  # pragma: no cover - regex already guarantees digits
        return None


def grade(response: str, expected, tolerance=DEFAULT_TOLERANCE) -> dict:
    """Grade one response. Returns {"status", "score", "extracted", "expected"}."""
    expected = Decimal(str(expected))
    tolerance = Decimal(str(tolerance))
    answer = extract_answer(response)

    if answer is None:
        status = "format_failure"
    elif abs(answer - expected) <= tolerance:
        status = "pass"
    else:
        status = "fail"

    return {
        "status": status,
        "score": 1 if status == "pass" else 0,
        "extracted": None if answer is None else str(answer),
        "expected": str(expected),
    }


if __name__ == "__main__":
    # Quick manual use: python grader.py 2258.88 < response.txt
    import sys

    text = sys.stdin.read()
    print(grade(text, sys.argv[1]))
