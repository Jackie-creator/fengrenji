"""Tests for the Claude vision adapter using a fake client (no API calls)."""

import base64
import json

import pytest

from app.vision.analyzer import ClaudeVisionAnalyzer, strip_json_fences
from app.vision.base import ImageInput, VisionAnalysisError
from app.vision.schemas import Category

VALID_JSON = json.dumps(
    {
        "category": "card_holder",
        "confidence": 0.85,
        "estimated_dimensions_mm": {"width": None, "height": None, "depth": None},
        "scale_reference_detected": False,
        "structure": {
            "card_slots_left": 3,
            "card_slots_right": 0,
            "has_bill_compartment": False,
            "has_zipper_pocket": False,
            "edge_finish": "burnished",
        },
        "notes_for_user": "三卡位卡包。",
        "closest_template": None,
    }
)


class FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [FakeBlock(text)]


class FakeMessages:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.outputs.pop(0))


class FakeClient:
    def __init__(self, *outputs: str) -> None:
        self.messages = FakeMessages(list(outputs))


def make_analyzer(*outputs: str) -> ClaudeVisionAnalyzer:
    return ClaudeVisionAnalyzer(client=FakeClient(*outputs), examples_dir=None)


PHOTO = ImageInput(data=b"\x89PNG-fake-bytes", media_type="image/png")


class TestFenceStripping:
    def test_plain_json(self):
        assert strip_json_fences('{"a": 1}') == '{"a": 1}'

    def test_markdown_fenced(self):
        assert strip_json_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_prose_wrapped(self):
        text = '好的，以下是分析结果：\n{"a": {"b": 2}}\n希望对你有帮助。'
        assert strip_json_fences(text) == '{"a": {"b": 2}}'

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            strip_json_fences("抱歉，我无法识别这些照片。")


class TestAnalyze:
    def test_clean_json_parses(self):
        result = make_analyzer(VALID_JSON).analyze([PHOTO])
        assert result.category == Category.CARD_HOLDER
        assert result.structure.card_slots_left == 3

    def test_fenced_json_parses(self):
        result = make_analyzer(f"```json\n{VALID_JSON}\n```").analyze([PHOTO])
        assert result.category == Category.CARD_HOLDER

    def test_message_construction(self):
        analyzer = make_analyzer(VALID_JSON)
        analyzer.analyze([PHOTO, PHOTO])
        call = analyzer.client.messages.calls[0]
        assert call["model"] == "claude-sonnet-4-6"
        assert call["system"][0]["text"].startswith("You are a leathercraft")
        # All photos in ONE user message, base64-encoded, instruction last.
        (message,) = call["messages"]
        assert message["role"] == "user"
        image_blocks = [b for b in message["content"] if b["type"] == "image"]
        assert len(image_blocks) == 2
        assert image_blocks[0]["source"]["data"] == base64.standard_b64encode(
            PHOTO.data
        ).decode("ascii")
        assert message["content"][-1]["type"] == "text"

    def test_retry_once_on_invalid_output(self):
        # First reply unparseable, second valid -> success with 2 API calls,
        # and the retry request carries the bad output + corrective message.
        analyzer = make_analyzer("我看不出来这是什么。", VALID_JSON)
        result = analyzer.analyze([PHOTO])
        assert result.category == Category.CARD_HOLDER
        calls = analyzer.client.messages.calls
        assert len(calls) == 2
        retry_messages = calls[1]["messages"]
        assert retry_messages[-2]["role"] == "assistant"
        assert "无法解析" in retry_messages[-1]["content"][0]["text"]

    def test_retry_on_schema_violation(self):
        # Parseable JSON but invalid schema also triggers the retry.
        bad = json.dumps({"category": "spaceship", "confidence": 0.9})
        result = make_analyzer(bad, VALID_JSON).analyze([PHOTO])
        assert result.category == Category.CARD_HOLDER

    def test_gives_up_after_second_failure(self):
        analyzer = make_analyzer("不是 JSON", "还不是 JSON")
        with pytest.raises(VisionAnalysisError):
            analyzer.analyze([PHOTO])

    def test_empty_image_list_rejected(self):
        with pytest.raises(ValueError):
            make_analyzer(VALID_JSON).analyze([])


class TestFewShot:
    def test_examples_injected_with_cache_breakpoint(self, tmp_path):
        sample = tmp_path / "sample_01"
        sample.mkdir()
        (sample / "front.png").write_bytes(b"\x89PNG-example")
        (sample / "expected.json").write_text(VALID_JSON, encoding="utf-8")

        analyzer = ClaudeVisionAnalyzer(client=FakeClient(VALID_JSON), examples_dir=tmp_path)
        analyzer.analyze([PHOTO])

        messages = analyzer.client.messages.calls[0]["messages"]
        # example user turn + example assistant turn + real user turn
        assert [m["role"] for m in messages] == ["user", "assistant", "user"]
        example_answer = messages[1]["content"][-1]
        assert json.loads(example_answer["text"])["category"] == "card_holder"
        # Cache breakpoint sits on the last block of the example prefix.
        assert example_answer["cache_control"] == {"type": "ephemeral"}

    def test_no_examples_dir_means_single_turn(self):
        analyzer = make_analyzer(VALID_JSON)
        analyzer.analyze([PHOTO])
        assert len(analyzer.client.messages.calls[0]["messages"]) == 1
