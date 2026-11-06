"""Grade a model response against a task's expected peso amount.

Rules:
  * Only the LAST occurrence of "FINAL ANSWER:" counts. Numbers anywhere else
    in the response (the working) are ignored.
  * Before parsing, light formatting is removed: markdown (**bold**, `code`)
    and LaTeX wrappers (\\boxed{...}, \\text{...}, \\(...\\), $...$, 2{,}258).
  * The text after "FINAL ANSWER:" on that line must then be exactly ONE amount:
      - optional currency marker before it: ₱, PHP, Php, P, or P.
        ("P" only counts when directly followed by the number, so a word like
        "Pay" is never read as a peso sign)
      - optional currency word after it: PHP or pesos
      - optional ONE short parenthetical label with no digits: "(total pay)"
      - optional final period
    Anything else is a "format_failure", not a wrong answer. We would rather
    report a format problem than guess which number the model meant.
  * Commas must be valid thousands separators ("2,258.88" ok, "22,58.88" not).
  * Missing decimals are fine: "₱2259" -> 2259.00, "PHP 2258.9" -> 2258.90.
  * Pass if |answer - expected| <= tolerance. Comparison uses Decimal so that
    float rounding can never turn an exact-tolerance answer into a false fail.

Statuses: "pass", "fail" (wrong amount), "format_failure" (no parsable final answer).
Score: 1 for pass, 0 otherwise.

For format failures, "format_reason" says why:
  no_final_line     there is no "FINAL ANSWER:" anywhere
  empty_answer      the final line has no amount after it
  multiple_amounts  the final line has more than one number
  malformed_number  one number, but badly written (e.g. "22,58.88", "2,258.885")
  extra_text        one valid number, plus words/symbols we don't accept
"""

import re
from decimal import Decimal

DEFAULT_TOLERANCE = Decimal("0.01")

# Finds every "FINAL ANSWER:" (any case) and captures the rest of that line.
_FINAL_LINE = re.compile(r"FINAL\s+ANSWER\s*:(?P<rest>[^\r\n]*)", re.IGNORECASE)

# A valid amount: plain digits ("2258.88") or valid thousands groups ("2,258.88"),
# with 0-2 decimal places.
_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?"

# The whole cleaned final line must match this.
_AMOUNT_LINE = re.compile(
    rf"""^
    (?:₱|PHP|Php|php|P\.?)?\s*      # optional currency marker; "P" must touch (or space-touch) the number
    (?P<num>{_NUMBER})
    \s*(?:PHP|php|pesos)?           # optional currency word after
    (?:\s*\([^()\d]{{1,40}}\))?     # optional ONE short label in parentheses, no digits
    \s*\.?                          # tolerate a sentence-ending period
    $""",
    re.VERBOSE,
)

# Any run of digits (with commas/periods inside). Used only to explain failures.
_NUMBER_TOKEN = re.compile(r"\d(?:[\d,.]*\d)?")

# LaTeX commands whose argument we keep: \boxed{X} -> X, \text{X} -> X, ...
_LATEX_WRAPPER = re.compile(r"\\(?:boxed|text|textbf|mathrm|mathbf)\s*\{([^{}]*)\}")


def _clean(text: str) -> str:
    """Remove markdown and LaTeX decoration around the answer."""
    text = text.replace("{,}", ",")             # LaTeX thousands separator: 2{,}258.88
    previous = None
    while previous != text:                     # unwrap nested wrappers from the inside out
        previous = text
        text = _LATEX_WRAPPER.sub(r"\1", text)
    text = re.sub(r"\\[()\[\]]", "", text)     # \( \) \[ \]
    text = re.sub(r"[*_`$]", "", text)          # markdown bold/italic/code, $...$
    return text.strip()


def parse_final_answer(response):
    """Return (amount, None) on success, or (None, format_reason) on failure."""
    if not response:
        return None, "no_final_line"
    matches = list(_FINAL_LINE.finditer(response))
    if not matches:
        return None, "no_final_line"

    rest = _clean(matches[-1].group("rest"))

    m = _AMOUNT_LINE.match(rest)
    if m:
        return Decimal(m.group("num").replace(",", "")), None

    # Not accepted. Work out the most useful reason.
    numbers = _NUMBER_TOKEN.findall(rest)
    if not numbers:
        leftover = re.sub(r"₱|PHP|Php|php|P\.?|pesos|[\s.:]", "", rest)
        return None, "empty_answer" if not leftover else "extra_text"
    if len(numbers) > 1:
        return None, "multiple_amounts"
    if not re.fullmatch(_NUMBER, numbers[0]):
        return None, "malformed_number"
    return None, "extra_text"


def extract_answer(response):
    """Return the amount (Decimal) from the last FINAL ANSWER line, or None."""
    return parse_final_answer(response)[0]


def grade(response: str, expected, tolerance=DEFAULT_TOLERANCE) -> dict:
    """Grade one response.

    Returns {"status", "score", "extracted", "expected", "format_reason"}.
    format_reason is None unless status is "format_failure".
    """
    expected = Decimal(str(expected))
    tolerance = Decimal(str(tolerance))
    answer, reason = parse_final_answer(response)

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
        "format_reason": reason,
    }


if __name__ == "__main__":
    # Quick manual use: python grader.py 2258.88 < response.txt
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    text = sys.stdin.read()
    print(grade(text, sys.argv[1]))
