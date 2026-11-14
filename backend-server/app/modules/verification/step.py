import logging
from dataclasses import replace

from app.modules.verification.checks import Report, verify_answer
from app.modules.verification.judge import JudgeUnavailable, judge_answer, judge_enabled
from app.modules.verification.ledger import EvidenceLedger
from app.modules.verification.numbers import parse_finance_answer

logger = logging.getLogger(__name__)

STEP_ID = "verify-answer"
# Activity status shown in the dashboard timeline for each verdict.
_STATUS = {"verified": "completed", "review": "partial", "rejected": "failed", "unverified": "partial"}


def verification_started() -> dict:
    """Sent before the check runs: the second stage calls a model and can take a few seconds."""
    return {"id": STEP_ID, "tool": "verify_answer", "input": {}, "status": "running"}


def _with_judge(report: Report, answer: str, ledger: EvidenceLedger, question: str) -> Report:
    parsed = parse_finance_answer(answer)
    if parsed is None or not judge_enabled():
        return report
    try:
        findings = tuple(judge_answer(parsed, ledger.records, question=question))
    except JudgeUnavailable as error:
        logger.warning("Answer judge unavailable: %s", error)
        return replace(report, judge="unavailable")
    # Stage 2 is a model's reading: it can raise a verified answer to a review, never reject one.
    verdict = "à réserve" if findings and report.verdict == "validé" else report.verdict
    return replace(report, verdict=verdict, findings=findings, judge="done")


def verification_activity(answer: str, ledger: EvidenceLedger, *, question: str, references: dict) -> dict:
    """The finished `verify_answer` step of the tool timeline, with the check's result in `output`.

    The check is advisory: a failure inside it must never keep the answer from the user.
    """
    try:
        report = verify_answer(answer, ledger.records, question=question, references=references)
        report = _with_judge(report, answer, ledger, question)
    except Exception:
        logger.exception("Answer verification failed")
        report = Report("non évalué")
    output = report.to_dict()
    return {"id": STEP_ID, "tool": "verify_answer", "input": {}, "status": _STATUS[output["code"]], "output": output}
