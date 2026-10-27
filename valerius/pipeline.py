"""The supervision loop: intake -> redact -> rules -> Muse Spark -> second pass -> (act, learn).

The rules set a floor. Muse Spark and the second pass can only raise risk.
If a model fails or the two passes disagree, the case goes to a human.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import judge as judge_mod
from . import redact, rules
from .types import Assessment, Message, Risk

# Public Muse Spark 1.3 Standard prices, USD per 1M tokens (dev.meta.ai/models, Oct 2026).
PRICE_IN, PRICE_OUT = 1.25, 4.25


@dataclass
class Result:
    message: Message                 # redacted copy
    assessment: Assessment
    redactions: dict[str, int] = field(default_factory=dict)
    first: judge_mod.Verdict | None = None
    second: judge_mod.Verdict | None = None
    disagreement: bool = False

    @property
    def risk(self) -> Risk:
        r = self.assessment.floor
        for v in (self.first, self.second):
            if v is not None and v.ok:
                r = rules.raise_only(r, v.risk)
        return r

    @property
    def unverified(self) -> list[str]:
        gaps = list(self.assessment.incomplete)
        for v in (self.first, self.second):
            if v is not None and not v.ok:
                gaps.append(f"{v.source} could not give a verdict ({v.error})")
        return gaps

    @property
    def needs_human(self) -> bool:
        return self.disagreement or bool(self.unverified)

    @property
    def hold(self) -> bool:
        return self.risk >= Risk.HIGH or self.needs_human

    def standard_cost_usd(self) -> float:
        """Muse Spark tokens priced at Standard rates (what a real deployment would pay)."""
        if self.first is None:
            return 0.0
        return (self.first.prompt_tokens * PRICE_IN + self.first.completion_tokens * PRICE_OUT) / 1e6


def run(msg: Message, *, use_models: bool = False,
        judge_chat: judge_mod.ChatFn | None = None, second_chat: judge_mod.ChatFn | None = None) -> Result:
    clean_text, counts = redact.redact(msg.text)
    clean = replace(msg, text=clean_text)
    result = Result(message=clean, assessment=rules.check(clean), redactions=counts)
    if use_models:
        result.first = judge_mod.judge(clean, result.assessment, judge_chat)
        result.second = judge_mod.second_pass(clean, result.assessment, result.first, second_chat)
        result.disagreement = judge_mod.disagree(result.first, result.second)
    return result


def explain(result: Result) -> str:
    """Plain-text summary with evidence, used by the CLI and tests."""
    a = result.assessment
    lines = [f"Risk: {result.risk.name}" + ("  -> HOLD" if result.hold else "") +
             (f"  (rules floor: {a.floor.name})" if result.first is not None else "")]
    for f in a.findings:
        ev = "; ".join(e.label() for e in f.evidence)
        lines.append(f"  - rule: {f.reason} [{f.rule}, {f.risk.name}]" + (f": {ev}" if ev else ""))
    for v in (result.first, result.second):
        if v is None:
            continue
        if v.ok:
            q = "; ".join(f'"{x}"' for x in v.quotes)
            lines.append(f"  - {v.source}: {v.risk.name}, {'; '.join(v.reasons)}" + (f" | quotes: {q}" if q else "") +
                         (f" | {v.seconds:.1f}s" if v.seconds else ""))
            if v.dropped_quotes:
                lines.append(f"    (dropped {len(v.dropped_quotes)} quote(s) not found in the message)")
    if result.disagreement:
        lines.append("  - the two reviews disagree -> a human decides")
    for gap in result.unverified:
        lines.append(f"  - could not verify: {gap} -> hold")
    if result.redactions:
        lines.append("  redacted: " + ", ".join(f"{k} x{v}" for k, v in sorted(result.redactions.items())))
    return "\n".join(lines)
