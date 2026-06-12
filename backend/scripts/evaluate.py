"""Evaluate the vision analyzer against a labelled dataset.

Usage:
    python scripts/evaluate.py path/to/dataset

Dataset format: one subdirectory per sample, each containing the product
photos plus an expected.json (hand-labelled AnalysisResult) — see
app/vision/dataset.py. Keep evaluation samples separate from the few-shot
examples in app/vision/examples/, otherwise you are grading the model on
its own crib sheet.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.vision.base import VisionAnalysisError, get_analyzer
from app.vision.dataset import load_samples
from app.vision.evaluation import format_report, score_sample


def main() -> None:
    load_dotenv()
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    samples = load_samples(sys.argv[1])
    if not samples:
        print(f"在 {sys.argv[1]} 下没有找到带 expected.json 的样本目录")
        sys.exit(1)

    analyzer = get_analyzer("claude")
    scores = []
    for sample in samples:
        try:
            predicted = analyzer.analyze(sample.images)
        except VisionAnalysisError as e:
            print(f"✗ {sample.name}: 分析失败（{e}）")
            continue
        scores.append(score_sample(sample.name, sample.expected, predicted))

    if scores:
        print(format_report(scores))


if __name__ == "__main__":
    main()
