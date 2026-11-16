"""Find the numbers a chat answer states, and the numbers its evidence contains.

Pure functions, no network. `extract_claims` reads free text (French or English
number formats). `parse_finance_answer` reads the OpenUI expression the chat returns.
`collect_sources` walks any JSON value and keeps the path of every number.
"""

import json
import math
import re
from dataclasses import dataclass

SPACES = "\u00a0\u202f\u2009 "
CURRENCY_CODES = {"USD", "CAD", "EUR", "GBP", "CHF", "JPY", "AUD", "CNY", "MXN"}
SYMBOL_CURRENCY = {"$": None, "€": "EUR", "£": "GBP", "¥": None}
PREFIX_CURRENCY = {"US$": "USD", "CA$": "CAD", "C$": "CAD", "A$": "AUD"}

_MONTHS_FR = r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|janv\.?|févr\.?|avr\.?|juil\.?|sept\.?|oct\.?|nov\.?|déc\.?"
_MONTHS_EN = r"January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"

# Text that contains digits but states no figure: numbered lists, citations, dates, index names.
_MASKS = [
    re.compile(r"(?m)^[ \t]*\d+[.)][ \t]"),
    re.compile(r"\[\d+(?:\s*[,\-–]\s*\d+)*\]"),
    re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"),
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),
    re.compile(rf"\b\d{{1,2}}(?:er)?\s+(?:{_MONTHS_FR})(?:\s+\d{{4}})?", re.I),
    re.compile(rf"\b(?:{_MONTHS_EN})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b", re.I),
    re.compile(r"(?:S&P(?:/TSX)?|Nasdaq|NASDAQ|Dow|TSX|Russell|CAC|DAX|FTSE|MSCI)\s?\d+"),
    # Illustrations offered to the reader ("for example 40 % in AAPL") state no result.
    re.compile(r"(?:par exemple|for example|for instance|e\.g\.|ex\.)[^\n]*?(?=\s[—–]\s|\.\s|\n|$)", re.I),
]

_NUMBER = re.compile(
    r"(?<![\w.,])(?P<sign>[+\-−])?"
    r"(?P<token>\d{1,3}(?:[\u00a0\u202f\u2009 ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)*)"
)
_PERCENT = re.compile(r"\s?(?:%|pour\s?cent|percent|per cent)", re.I)
_POINTS_LONG = re.compile(r"\s?(?:points?\s+de\s+pourcentage|percentage\s+points?|pp)\b", re.I)
_POINTS = re.compile(r"\s?(?:points?|pts?)\b", re.I)
_DURATION = re.compile(
    r"[\s-]?(?:ans?|années?|years?|yrs?|mois|months?|semaines?|weeks?|jours?|days?|heures?|hours?|minutes?|mins?|"
    r"trimestres?|quarters?|ytd)\b|(?:h|mo|y|d|w)\b",
    re.I,
)
_MULTIPLIER_WORD = re.compile(r"\s?(milliards?|millions?)\b", re.I)
_MULTIPLIER_SHORT = re.compile(r"\s?(Md|M|k)(?![A-Za-z])")
_CODES = "|".join(sorted(CURRENCY_CODES))
_CURRENCY_BEFORE = re.compile(rf"(?:(US\$|CA\$|C\$|A\$|{_CODES})|([$€£¥]))\s?$")
_CURRENCY_AFTER = re.compile(rf"\s?(?:(US\$|CA\$|C\$|A\$|{_CODES})\b|([$€£¥])|(dollars?|euros?))", re.I)
_MULTIPLIERS = {"k": 1e3, "m": 1e6, "md": 1e9, "million": 1e6, "millions": 1e6, "milliard": 1e9, "milliards": 1e9}


@dataclass(frozen=True)
class Claim:
    """A figure stated in text. `values` holds every reading of an ambiguous format as (value, tolerance)."""

    text: str
    unit: str  # percent, points, amount or bare
    values: tuple[tuple[float, float], ...]
    sign: str | None
    currency: str | None
    strong: bool  # False for a bare small integer such as "3 lines", which is only a weak claim


def _readings(token: str) -> list[tuple[float, int]]:
    """Possible (value, decimals) readings of a digit string. "1,255" is 1.255 in French and 1255 in English."""
    s = "".join(c for c in token if c not in SPACES)
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        last = max(s.rfind("."), s.rfind(","))
        whole = re.sub(r"[.,]", "", s[:last])
        fraction = s[last + 1:]
        return [(float(f"{whole}.{fraction}"), len(fraction))]
    separator = "." if has_dot else "," if has_comma else None
    if separator is None:
        return [(float(s), 0)]
    parts = s.split(separator)
    if len(parts) > 2:
        return [(float("".join(parts)), 0)] if all(len(p) == 3 for p in parts[1:]) else []
    whole, fraction = parts
    decimal = (float(f"{whole}.{fraction}"), len(fraction))
    if len(fraction) == 3 and 1 <= len(whole) <= 3 and not whole.startswith("0"):
        return [decimal, (float(whole + fraction), 0)]
    return [decimal]


def _currency_code(code: str | None, symbol: str | None, word: str | None) -> str | None:
    if code:
        return PREFIX_CURRENCY.get(code.upper(), code.upper())
    if symbol:
        return SYMBOL_CURRENCY.get(symbol)
    if word and word.lower().startswith("euro"):
        return "EUR"
    return None


def extract_claims(text: str) -> list[Claim]:
    """Every figure stated in `text`, except citations, dates, list numbers, years and period lengths."""
    masked = text
    for pattern in _MASKS:
        masked = pattern.sub(lambda m: " " * len(m.group()), masked)
    claims = []
    for match in _NUMBER.finditer(masked):
        token = match.group("token")
        readings = _readings(token)
        if not readings:
            continue
        sign = {"+": "+", "-": "-", "−": "-"}.get(match.group("sign") or "")
        after = masked[match.end(): match.end() + 30]
        before = masked[max(0, match.start() - 6): match.start()]
        explicit_separator = any(c in token for c in SPACES + ".,")

        unit, currency, scale, consumed, text_start = "bare", None, 1.0, 0, match.start()
        points_long = False
        if found := _PERCENT.match(after):
            unit = "percent"
        elif found := _POINTS_LONG.match(after):
            unit, points_long = "points", True
        elif found := _POINTS.match(after):
            unit = "points"
        else:
            found = None
        if found:
            consumed = found.end()
        else:
            rest = after
            if multiplier := _MULTIPLIER_WORD.match(rest):
                scale, consumed, rest = _MULTIPLIERS[multiplier.group(1).lower()], multiplier.end(), rest[multiplier.end():]
            elif multiplier := _MULTIPLIER_SHORT.match(rest):
                tail = rest[multiplier.end():]
                if _CURRENCY_BEFORE.search(before) or _CURRENCY_AFTER.match(tail):
                    scale, consumed, rest = _MULTIPLIERS[multiplier.group(1).lower()], multiplier.end(), tail
            leading = _CURRENCY_BEFORE.search(before)
            trailing = _CURRENCY_AFTER.match(rest)
            if leading:
                unit, currency = "amount", _currency_code(*leading.groups(), None)
                text_start -= len(leading.group())
            elif trailing:
                unit, currency = "amount", _currency_code(*trailing.groups())
            if unit == "bare" and scale == 1.0 and _DURATION.match(after):
                continue
        if unit == "bare" and not sign and not explicit_separator and len(token) == 4 and 1900 <= int(token) <= 2100:
            continue  # a year

        values = tuple((value * scale, 0.5 * 10 ** -decimals * scale) for value, decimals in readings)
        strong = (explicit_separator or scale != 1.0 or unit in ("percent", "amount")
                  or (unit == "points" and bool(sign or points_long)))
        # Structural values (nothing, a whole, a maximum) say little: "0 %", "100 %", "out of 1,00".
        if all(v == 0 or (unit == "percent" and v == 100) or (unit == "bare" and v == 1) for v, _ in values):
            strong = False
        claims.append(Claim(masked[text_start: match.end() + consumed].strip(), unit, values, sign, currency, strong))
    return claims


def parse_finance_answer(text: str) -> dict | None:
    """The four arguments of `root = FinanceAnswer(title, explanation, headers, rows)`, or None."""
    start = re.search(r"root\s*=\s*FinanceAnswer\(", text)
    if not start:
        return None
    depth, in_string, escaped = 1, False, False
    for index in range(start.end(), len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                break
    else:
        return None
    try:
        arguments = json.loads("[" + text[start.end(): index] + "]")
    except ValueError:
        return None
    if len(arguments) != 4:
        return None
    title, explanation, headers, rows = arguments
    if not (isinstance(title, str) and isinstance(explanation, str) and isinstance(headers, list)
            and isinstance(rows, list) and all(isinstance(r, list) for r in rows)):
        return None
    return {"title": title, "explanation": explanation, "headers": headers, "rows": rows}


def answer_claims(answer: dict) -> list[tuple[str, Claim]]:
    """(location, claim) for every figure in a parsed FinanceAnswer."""
    cells = [("title", answer["title"]), ("explanation", answer["explanation"])]
    cells += [(f"headers[{i}]", h) for i, h in enumerate(answer["headers"])]
    cells += [(f"rows[{r}][{c}]", cell) for r, row in enumerate(answer["rows"]) for c, cell in enumerate(row)]
    return [(location, claim) for location, cell in cells if isinstance(cell, str) for claim in extract_claims(cell)]


@dataclass(frozen=True)
class SourceNumber:
    value: float
    path: tuple[str, ...]
    origin: str  # tool, question or reference
    name: str  # the tool call, or the reference label
    kind: str  # percent, points, ratio, amount, count, other
    currency: str | None

    @property
    def display(self) -> str:
        text = ""
        for part in self.path:
            text += part if part.startswith("[") or not text else "." + part
        label = self.name.split("#")[0]  # the call id keeps calls apart but means nothing to a reader
        return f"{label} · {text}" if text else label


_AMOUNT_KEYS = {"price", "value", "previousclose", "baseline", "pricechange", "dailychange", "high", "low",
                "firstclose", "lastclose", "close", "open", "amount", "converted"}
_COUNT_KEYS = {"count", "quantity", "observations", "tradingdays", "lines", "effectivelines", "hours", "years"}
_TEXT_KINDS = {"percent": "percent", "points": "points", "amount": "amount", "bare": "other"}
_SKIPPED_KEYS = {"time", "timestamp"}


def _kind(key: str | None, currency: str | None) -> str:
    k = (key or "").lower()
    if "percent" in k:
        return "percent"
    if "point" in k:
        return "points"
    if "herfindahl" in k:
        return "ratio"
    if k in _COUNT_KEYS:
        return "count"
    if currency or k in _AMOUNT_KEYS or k.endswith("cad"):
        return "amount"
    return "other"


def collect_sources(value, *, origin: str, name: str) -> list[SourceNumber]:
    """Every number in a JSON value, with its path. Numbers written inside strings are included."""
    found: list[SourceNumber] = []

    def walk(node, path, key, currency):
        if node is None or isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            if math.isfinite(node):
                # An exchange rate sits next to a currency but is a ratio between two currencies.
                own = None if (key or "").lower() == "rate" or "perunit" in (key or "").lower() else currency
                found.append(SourceNumber(float(node), path, origin, name, _kind(key, own), own))
        elif isinstance(node, str):
            for claim in extract_claims(node):
                for magnitude, _ in claim.values:
                    signed = -magnitude if claim.sign == "-" else magnitude
                    found.append(SourceNumber(signed, (*path, "(text)"), origin, name, _TEXT_KINDS[claim.unit],
                                              claim.currency or currency))
        elif isinstance(node, dict):
            own = node.get("currency") if isinstance(node.get("currency"), str) else currency
            for child_key, child in node.items():
                if child_key in _SKIPPED_KEYS:
                    continue
                child_currency = own
                if child_key == "converted" and isinstance(node.get("target"), str):
                    child_currency = node["target"]
                elif child_key in CURRENCY_CODES:
                    child_currency = child_key
                elif str(child_key).lower().endswith("cad"):
                    child_currency = "CAD"
                walk(child, (*path, str(child_key)), str(child_key), child_currency)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, (*path, f"[{index}]"), key, currency)

    walk(value, (), None, None)
    return found
