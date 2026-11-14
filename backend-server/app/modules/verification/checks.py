"""Check that the figures in a chat answer come from the evidence of the same question.

Pure functions, no network and no model. Verdict, from worst to best:
`rejeté` (a stated figure has no source), `à réserve` (a figure is only a difference between two
sourced values, or a bare small integer has no source), `validé`, and `non évalué` (the answer
could not be read).
"""

from dataclasses import dataclass
from typing import Any

from app.modules.verification.ledger import ToolRecord
from app.modules.verification.numbers import (
    Claim,
    SourceNumber,
    answer_claims,
    collect_sources,
    parse_finance_answer,
)

EPSILON = 1e-9
MAX_FOUND = 3
# Language-neutral codes for the dashboard, which is not written in French.
VERDICT_CODES = {"validé": "verified", "à réserve": "review", "rejeté": "rejected", "non évalué": "unverified"}


@dataclass(frozen=True)
class Found:
    origin: str  # tool, question or reference
    source: str  # tool call and path of the number
    value: float
    via: str  # exact, scaled (a ratio shown as a percentage) or derived (difference of two values)
    operands: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimResult:
    text: str
    location: str
    status: str  # ok, derived, unmatched, weak_unmatched
    found: tuple[Found, ...] = ()


@dataclass(frozen=True)
class Report:
    verdict: str
    results: tuple[ClaimResult, ...] = ()

    @property
    def unmatched(self) -> tuple[ClaimResult, ...]:
        return tuple(r for r in self.results if r.status in ("unmatched", "weak_unmatched"))

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "code": VERDICT_CODES[self.verdict],
            "checked": len(self.results),
            "unmatched": [{"text": r.text, "location": r.location, "status": r.status} for r in self.unmatched],
            "derived": [{"text": r.text, "location": r.location,
                         "operands": [list(f.operands) for f in r.found]} for r in self.results if r.status == "derived"],
        }


def _compatible(claim: Claim, source: SourceNumber) -> bool:
    if claim.currency and source.currency and claim.currency != source.currency:
        return False
    if claim.unit == "percent":
        return source.kind in {"percent", "other", "ratio"}
    if claim.unit == "points":
        return source.kind in {"points", "percent", "other"}
    if claim.unit == "amount":
        return source.kind in {"amount", "other"}
    return True


def _factors(claim: Claim, source: SourceNumber) -> list[tuple[float, str]]:
    if claim.unit != "percent":
        return [(1.0, "exact")]
    factors = []
    if source.kind in {"percent", "other"}:
        factors.append((1.0, "exact"))
    if source.kind in {"ratio", "other"} and abs(source.value) <= 1:
        factors.append((100.0, "scaled"))
    return factors


def _direct_matches(claim: Claim, sources: list[SourceNumber]) -> list[Found]:
    matches: dict[str, Found] = {}
    for magnitude, tolerance in claim.values:
        for source in sources:
            if not _compatible(claim, source):
                continue
            for factor, via in _factors(claim, source):
                value = source.value * factor
                if (claim.sign == "+" and value < 0) or (claim.sign == "-" and value > 0):
                    continue
                if abs(abs(value) - magnitude) <= tolerance + EPSILON:
                    matches.setdefault(source.display, Found(source.origin, source.display, source.value, via))
    ordered = sorted(matches.values(), key=lambda f: f.origin != "tool")
    return ordered[:MAX_FOUND]


def _is(claim: Claim, value: float, *, signed: bool = False) -> bool:
    if signed and ((claim.sign == "+" and value < 0) or (claim.sign == "-" and value > 0)):
        return False
    return any(abs(abs(value) - magnitude) <= tolerance + EPSILON for magnitude, tolerance in claim.values)


def _points_gaps(claim: Claim, sources: list[SourceNumber]) -> list[Found]:
    """A figure stated in points can be the gap between two sourced percentages of the same tool call."""
    if claim.unit != "points":
        return []
    pool = [s for s in sources
            if s.origin == "tool" and s.kind in {"percent", "points"} and s.path[-1:] != ("(text)",)]
    groups: dict[tuple, list[SourceNumber]] = {}
    for source in pool:
        groups.setdefault((source.name, "parent", source.path[:-1]), []).append(source)
        groups.setdefault((source.name, "key", source.path[-1:]), []).append(source)
    matches = []
    for members in groups.values():
        for i, first in enumerate(members):
            for second in members[i + 1:]:
                gap = abs(first.value - second.value)
                if _is(claim, gap):
                    matches.append(Found("tool", f"{first.display} − {second.display}", gap, "derived",
                                         tuple(sorted((first.display, second.display)))))
    return matches


def _before_after_changes(claim: Claim, sources: list[SourceNumber]) -> list[Found]:
    """The change between a tool's `before` and `after` values. Needs at least one decimal, since
    whole numbers would match too many gaps by chance."""
    if claim.unit != "points" and any(tolerance > 0.05 + EPSILON for _, tolerance in claim.values):
        return []
    pool = {(s.name, s.path): s for s in sources if s.origin == "tool" and s.path[-1:] != ("(text)",)}
    matches = []
    for (name, path), before in pool.items():
        if "before" not in path:
            continue
        index = path.index("before")
        after = pool.get((name, (*path[:index], "after", *path[index + 1:])))
        if after is not None and _is(claim, after.value - before.value, signed=True):
            matches.append(Found("tool", f"{after.display} − {before.display}", after.value - before.value, "derived",
                                 (before.display, after.display)))
    return matches


def _question_arithmetic(claim: Claim, sources: list[SourceNumber]) -> list[Found]:
    """Simple arithmetic on the figures the user wrote in the question, such as 15 % of 2 000 $."""
    operands = {s.value: s for s in sources if s.origin == "question"}
    if not 1 <= len(operands) <= 6:
        return []
    values = list(operands)
    candidates = [((a,), a / 100) for a in values]
    for a in values:
        for b in values:
            if a == b:
                continue
            candidates += [((a, b), a + b), ((a, b), abs(a - b)), ((a, b), a * b), ((a, b), a * b / 100)]
            if b:
                candidates.append(((a, b), a / b))
    return [Found("question", "question", result, "derived", tuple(f"question · {v:g}" for v in used))
            for used, result in candidates if _is(claim, result)]


def _derived_matches(claim: Claim, sources: list[SourceNumber]) -> list[Found]:
    # The most specific explanation first: the dashboard names the first operands.
    found = [*_before_after_changes(claim, sources), *_question_arithmetic(claim, sources), *_points_gaps(claim, sources)]
    return found[:MAX_FOUND]


def verify_answer(answer_text: str, records: tuple[ToolRecord, ...] | list[ToolRecord], *,
                  question: str = "", references: dict[str, Any] | None = None) -> Report:
    """Check every figure of a FinanceAnswer against tool results, the question and saved reference data.

    Records whose status is `failed` are not sources: they hold no valid figure.
    """
    answer = parse_finance_answer(answer_text)
    if answer is None:
        return Report("non évalué")

    sources: list[SourceNumber] = []
    for record in records:
        if record.status == "failed":
            continue
        name = f"{record.tool}#{record.call_id}"
        for item in record.evidence:
            sources += collect_sources(item, origin="tool", name=name)
    if question:
        sources += collect_sources(question, origin="question", name="question")
    for label, data in (references or {}).items():
        sources += collect_sources(data, origin="reference", name=label)

    results = []
    for location, claim in answer_claims(answer):
        found = _direct_matches(claim, sources)
        if found:
            status = "ok"
        elif claim.strong and (found := _derived_matches(claim, sources)):
            status = "derived"
        else:
            status = "unmatched" if claim.strong else "weak_unmatched"
        results.append(ClaimResult(claim.text, location, status, tuple(found)))

    statuses = {r.status for r in results}
    if "unmatched" in statuses:
        verdict = "rejeté"
    elif statuses & {"derived", "weak_unmatched"}:
        verdict = "à réserve"
    else:
        verdict = "validé"
    return Report(verdict, tuple(results))
