import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolRecord:
    """What one tool call returned to the model, kept for checking the final answer."""

    call_id: str
    tool: str
    status: str
    arguments: dict
    evidence: list[dict]


class EvidenceLedger:
    """Collects every tool result of one question, in call order, including failed calls."""

    def __init__(self):
        self._records: list[ToolRecord] = []

    def record(self, call_id: str, tool: str, status: str, arguments: dict, evidence: list[dict]) -> None:
        # A JSON round trip freezes the evidence as the model received it, so later edits
        # to the original objects cannot change what the checker reads.
        self._records.append(ToolRecord(call_id, tool, status, json.loads(json.dumps(arguments)),
                                        json.loads(json.dumps(evidence))))

    @property
    def records(self) -> tuple[ToolRecord, ...]:
        return tuple(self._records)

    def __len__(self) -> int:
        return len(self._records)
