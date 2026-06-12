"""Tests for evaluation metrics and the dataset loader."""

import json

import pytest

from app.vision.dataset import load_samples
from app.vision.evaluation import format_report, score_sample, summarize
from app.vision.schemas import AnalysisResult

LABEL = {
    "category": "zipper_pouch",
    "confidence": 0.9,
    "scale_reference_detected": False,
    "structure": {
        "card_slots_left": 0,
        "card_slots_right": 0,
        "has_bill_compartment": False,
        "has_zipper_pocket": True,
        "edge_finish": "burnished",
    },
    "notes_for_user": "拉链零钱包。",
}


def result(**overrides) -> AnalysisResult:
    payload = json.loads(json.dumps(LABEL))
    for key, value in overrides.items():
        if key in payload.get("structure", {}):
            payload["structure"][key] = value
        else:
            payload[key] = value
    return AnalysisResult.model_validate(payload)


class TestScoring:
    def test_perfect_prediction(self):
        score = score_sample("s1", result(), result())
        assert score.category_correct
        assert score.slots_left_error == 0
        assert score.edge_finish_correct

    def test_category_and_slot_errors_detected(self):
        predicted = result(category="card_holder", card_slots_left=2)
        score = score_sample("s1", result(), predicted)
        assert not score.category_correct
        assert score.slots_left_error == 2

    def test_summary_metrics(self):
        scores = [
            score_sample("a", result(), result()),
            score_sample("b", result(), result(category="card_holder", card_slots_left=1)),
        ]
        metrics = summarize(scores)
        assert metrics["category_accuracy"] == pytest.approx(0.5)
        # 1 slot error across 2 samples x 2 sides = 0.25 MAE.
        assert metrics["slots_mae"] == pytest.approx(0.25)

    def test_report_renders(self):
        report = format_report([score_sample("a", result(), result())])
        assert "品类准确率 100%" in report

    def test_empty_scores_rejected(self):
        with pytest.raises(ValueError):
            summarize([])


class TestDatasetLoader:
    def test_loads_labelled_samples_only(self, tmp_path):
        good = tmp_path / "sample_01"
        good.mkdir()
        (good / "photo.jpg").write_bytes(b"fake-jpeg")
        (good / "expected.json").write_text(json.dumps(LABEL), encoding="utf-8")
        (tmp_path / "unlabelled").mkdir()  # skipped: no expected.json

        samples = load_samples(tmp_path)
        assert len(samples) == 1
        assert samples[0].name == "sample_01"
        assert samples[0].images[0].media_type == "image/jpeg"
        assert samples[0].expected.structure.has_zipper_pocket

    def test_label_without_images_rejected(self, tmp_path):
        bad = tmp_path / "sample_01"
        bad.mkdir()
        (bad / "expected.json").write_text(json.dumps(LABEL), encoding="utf-8")
        with pytest.raises(ValueError):
            load_samples(tmp_path)

    def test_missing_dir_returns_empty(self, tmp_path):
        assert load_samples(tmp_path / "nope") == []
