import logging

from app.modules.verification.checks import Report, verify_answer
from app.modules.verification.ledger import EvidenceLedger

logger = logging.getLogger(__name__)

# Activity status shown in the dashboard timeline for each verdict.
_STATUS = {"verified": "completed", "review": "partial", "rejected": "failed", "unverified": "partial"}


def verification_activity(answer: str, ledger: EvidenceLedger, *, question: str, references: dict) -> dict:
    """The `verify_answer` step of the tool timeline, with the check's result in `output`.

    The check is advisory: a failure inside it must never keep the answer from the user.
    """
    try:
        report = verify_answer(answer, ledger.records, question=question, references=references)
    except Exception:
        logger.exception("Answer verification failed")
        report = Report("non évalué")
    output = report.to_dict()
    return {"id": "verify-answer", "tool": "verify_answer", "input": {}, "status": _STATUS[output["code"]],
            "output": output}
