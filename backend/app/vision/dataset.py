"""Loader for labelled photo sets (provider-neutral format).

A dataset directory contains one subdirectory per sample:

    dataset/
    ├── sample_01/
    │   ├── front.jpg          # any number of photos, any names
    │   ├── inside.jpg
    │   └── expected.json      # hand-labelled AnalysisResult
    └── sample_02/ ...

The same format serves three purposes: few-shot examples injected into the
prompt, the evaluation set for prompt iteration, and — should we ever
fine-tune a model on another platform — training data (image + instruction
-> JSON answer pairs convert 1:1 to fine-tuning JSONL).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .base import IMAGE_MEDIA_TYPES, ImageInput
from .schemas import AnalysisResult

LABEL_FILENAME = "expected.json"


@dataclass(frozen=True)
class LabelledSample:
    name: str
    images: list[ImageInput]
    expected: AnalysisResult


def load_samples(dataset_dir: str | Path) -> list[LabelledSample]:
    """Load every labelled sample under `dataset_dir`, sorted by name.

    Subdirectories without an expected.json are skipped silently so the
    directory can hold notes or work-in-progress samples.
    """
    dataset_dir = Path(dataset_dir)
    samples: list[LabelledSample] = []
    if not dataset_dir.is_dir():
        return samples

    for sample_dir in sorted(p for p in dataset_dir.iterdir() if p.is_dir()):
        label_path = sample_dir / LABEL_FILENAME
        if not label_path.is_file():
            continue
        expected = AnalysisResult.model_validate(json.loads(label_path.read_text(encoding="utf-8")))
        images = [
            ImageInput.from_file(p)
            for p in sorted(sample_dir.iterdir())
            if p.suffix.lower() in IMAGE_MEDIA_TYPES
        ]
        if not images:
            raise ValueError(f"sample {sample_dir} has a label but no images")
        samples.append(LabelledSample(name=sample_dir.name, images=images, expected=expected))
    return samples
