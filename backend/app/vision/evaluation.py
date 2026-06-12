"""Evaluation metrics for the vision layer.

Compares analyzer predictions against hand-labelled expectations. This is
the iteration loop that replaces "training": label photos -> run evaluation
-> tune prompt/examples -> re-run, watching the aggregate metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import AnalysisResult


@dataclass(frozen=True)
class SampleScore:
    name: str
    category_correct: bool
    slots_left_error: int
    slots_right_error: int
    bill_correct: bool
    zipper_correct: bool
    edge_finish_correct: bool


def score_sample(name: str, expected: AnalysisResult, predicted: AnalysisResult) -> SampleScore:
    return SampleScore(
        name=name,
        category_correct=predicted.category == expected.category,
        slots_left_error=abs(
            predicted.structure.card_slots_left - expected.structure.card_slots_left
        ),
        slots_right_error=abs(
            predicted.structure.card_slots_right - expected.structure.card_slots_right
        ),
        bill_correct=predicted.structure.has_bill_compartment
        == expected.structure.has_bill_compartment,
        zipper_correct=predicted.structure.has_zipper_pocket
        == expected.structure.has_zipper_pocket,
        edge_finish_correct=predicted.structure.edge_finish == expected.structure.edge_finish,
    )


def summarize(scores: list[SampleScore]) -> dict[str, float]:
    """Aggregate metrics over all scored samples."""
    n = len(scores)
    if n == 0:
        raise ValueError("no samples scored")
    return {
        "samples": float(n),
        "category_accuracy": sum(s.category_correct for s in scores) / n,
        "slots_mae": sum(s.slots_left_error + s.slots_right_error for s in scores) / (2 * n),
        "bill_accuracy": sum(s.bill_correct for s in scores) / n,
        "zipper_accuracy": sum(s.zipper_correct for s in scores) / n,
        "edge_finish_accuracy": sum(s.edge_finish_correct for s in scores) / n,
    }


def format_report(scores: list[SampleScore]) -> str:
    """Human-readable evaluation report."""
    lines = []
    for s in scores:
        flag = "✓" if s.category_correct else "✗"
        lines.append(
            f"{flag} {s.name}: 品类{'对' if s.category_correct else '错'}, "
            f"卡位误差 L{s.slots_left_error}/R{s.slots_right_error}, "
            f"钞票仓{'对' if s.bill_correct else '错'}, "
            f"拉链{'对' if s.zipper_correct else '错'}, "
            f"收边{'对' if s.edge_finish_correct else '错'}"
        )
    m = summarize(scores)
    lines.append("-" * 60)
    lines.append(
        f"共 {int(m['samples'])} 组 ｜ 品类准确率 {m['category_accuracy']:.0%} ｜ "
        f"卡位平均误差 {m['slots_mae']:.2f} ｜ 钞票仓 {m['bill_accuracy']:.0%} ｜ "
        f"拉链 {m['zipper_accuracy']:.0%} ｜ 收边 {m['edge_finish_accuracy']:.0%}"
    )
    return "\n".join(lines)
