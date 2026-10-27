"""The supervision loop. Day 1: intake -> redact -> rules.

Later stages plug in here: Muse Spark verdict, second pass on Muse Spark Open,
act (hold, approval link, receipt) and learn. Each later stage may only raise
the risk set by the rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import redact, rules
from .types import Assessment, Message, Risk


@dataclass
class Result:
    message: Message                 # redacted copy
    assessment: Assessment
    redactions: dict[str, int] = field(default_factory=dict)

    @property
    def risk(self) -> Risk:
        return self.assessment.floor

    @property
    def hold(self) -> bool:
        return self.assessment.needs_hold


def run(msg: Message) -> Result:
    clean_text, counts = redact.redact(msg.text)
    clean = replace(msg, text=clean_text)
    return Result(message=clean, assessment=rules.check(clean), redactions=counts)


def explain(result: Result) -> str:
    """Plain-text summary with evidence, used by the CLI and tests."""
    a = result.assessment
    lines = [f"Risk: {a.floor.name}" + ("  -> HOLD" if result.hold else "")]
    for f in a.findings:
        ev = "; ".join(e.label() for e in f.evidence)
        lines.append(f"  - {f.reason} [{f.rule}, {f.risk.name}]" + (f": {ev}" if ev else ""))
    for gap in a.incomplete:
        lines.append(f"  - could not verify: {gap} -> hold")
    if result.redactions:
        lines.append("  redacted: " + ", ".join(f"{k} x{v}" for k, v in sorted(result.redactions.items())))
    return "\n".join(lines)
