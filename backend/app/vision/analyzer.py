"""Claude adapter for the vision analysis layer.

Design constraints (from the product spec):
- the model must output ONLY structured JSON matching schemas.AnalysisResult;
- if a known-size reference object (ID-1 bank card 85.6x54 mm, common coins)
  is visible, estimate overall dimensions from it; otherwise dimensions stay
  null — fabricating dimensions is forbidden;
- the response is parsed tolerantly (markdown fences stripped); on a parse
  or validation failure the request is retried once with a corrective
  message before giving up.

Few-shot examples: if the configured examples directory contains labelled
samples (see dataset.py for the format), they are injected as prior
user/assistant turns so the model can imitate calibrated judgements. The
last example block carries a cache_control breakpoint so the static prefix
(system prompt + examples, including the heavy image payloads) is served
from the prompt cache on repeated calls.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .base import ImageInput, VisionAnalysisError, VisionAnalyzer
from .dataset import load_samples
from .schemas import AnalysisResult

#: Model pinned by the product spec for the MVP vision layer.
DEFAULT_VISION_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1500
DEFAULT_TIMEOUT_S = 120.0
DEFAULT_EXAMPLES_DIR = Path(__file__).parent / "examples"

SYSTEM_PROMPT = """\
You are a leathercraft pattern-making expert analysing photos of a finished
leather product. The photos may show: exterior front/back, the opened
interior, a side/thickness view, and optionally a scale reference object.

Identify the product and extract its structure. Respond with ONLY a JSON
object — no prose, no markdown fences — matching exactly this schema:

{
  "category": "card_holder" | "bifold_wallet" | "zipper_pouch" | "unsupported",
  "confidence": <float 0.0-1.0>,
  "estimated_dimensions_mm": {"width": <float|null>, "height": <float|null>, "depth": <float|null>},
  "scale_reference_detected": <bool>,
  "structure": {
    "card_slots_left": <int>,
    "card_slots_right": <int>,
    "has_bill_compartment": <bool>,
    "has_zipper_pocket": <bool>,
    "edge_finish": "burnished" | "folded" | "bound" | "unknown"
  },
  "notes_for_user": "<Chinese description of recognised structure and uncertainties>",
  "closest_template": "card_holder" | "bifold_wallet" | "zipper_pouch" | null
}

Category definitions:
- card_holder: a flat card case — front/back panels with 1-3 stacked card
  slots, no fold, no bill compartment.
- bifold_wallet: a short wallet folding in half, with a full-width bill
  compartment and card slots on the left and/or right interior.
- zipper_pouch: a flat coin pouch closed by a zipper (either a zipper window
  on the front panel or a zipper sandwiched in the top seam).
- unsupported: anything else (long wallets, bags, key cases, watch straps,
  irregular shaped items...). When unsupported, set closest_template to the
  most similar of the 3 supported templates and explain in notes_for_user
  (in Chinese) that the category is not yet supported.

Rules:
1. Dimensions: ONLY estimate estimated_dimensions_mm if a known-size object
   is visible (ID-1 bank card = 85.6 x 54 mm, or a recognisable coin). Set
   scale_reference_detected accordingly. If no reference is visible, leave
   width/height/depth as null — NEVER guess or fabricate dimensions.
2. Count card slots by their visible staggered top edges, per side
   (card_slots_left = left interior, card_slots_right = right interior; for
   a card_holder put the total in card_slots_left).
3. edge_finish: burnished = cut edge painted/polished (slightly rounded,
   uniform dark line); folded = edge folded over (visible rounded hem,
   stitch line set back from the edge); bound = wrapped with a separate
   strip. Use "unknown" when the photos do not show the edges clearly.
4. confidence reflects category identification only. Below 0.5 means you
   are mostly guessing.
5. notes_for_user must be Chinese, brief, and honest about uncertainties
   (e.g. blurred interior, slots partially hidden).
6. Output the JSON object only.\
"""

#: Instruction attached to the user's photos in every request.
USER_INSTRUCTION = "请分析这些皮具照片，按 schema 输出 JSON。"

#: Sent when the first response failed to parse/validate.
RETRY_INSTRUCTION = (
    "你上一条回复无法解析为符合 schema 的 JSON（错误：{error}）。"
    "请重新输出，只输出 JSON 对象本身，不要任何其他文字或代码块围栏。"
)


def strip_json_fences(text: str) -> str:
    """Extract the JSON object from a possibly fenced / prose-wrapped reply.

    Handles ```json ... ``` fences and leading/trailing prose by slicing
    from the first '{' to the last '}'.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return text[start : end + 1]


def _image_block(image: ImageInput) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image.media_type,
            "data": base64.standard_b64encode(image.data).decode("ascii"),
        },
    }


class ClaudeVisionAnalyzer(VisionAnalyzer):
    def __init__(
        self,
        client: Any | None = None,
        model: str = DEFAULT_VISION_MODEL,
        examples_dir: str | Path | None = DEFAULT_EXAMPLES_DIR,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = client
        self.model = model
        self.examples_dir = Path(examples_dir) if examples_dir else None
        self.max_tokens = max_tokens

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic  # deferred so tests never need a real key

            # Reads ANTHROPIC_API_KEY from the environment (see .env.example).
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise VisionAnalysisError(
                    "ANTHROPIC_API_KEY is not set; copy .env.example to .env "
                    "and fill in your key"
                )
            self._client = anthropic.Anthropic(timeout=DEFAULT_TIMEOUT_S)
        return self._client

    # -- prompt assembly ----------------------------------------------------

    def _few_shot_messages(self) -> list[dict[str, Any]]:
        """Labelled samples from the examples directory as prior turns."""
        if self.examples_dir is None:
            return []
        messages: list[dict[str, Any]] = []
        for sample in load_samples(self.examples_dir):
            messages.append(
                {
                    "role": "user",
                    "content": [
                        *(_image_block(img) for img in sample.images),
                        {"type": "text", "text": USER_INSTRUCTION},
                    ],
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": sample.expected.model_dump_json(exclude_none=False),
                        }
                    ],
                }
            )
        if messages:
            # Cache breakpoint after the static example prefix: repeated
            # requests reuse system prompt + all example images at ~0.1x cost.
            messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        return messages

    def _build_messages(self, images: list[ImageInput]) -> list[dict[str, Any]]:
        return [
            *self._few_shot_messages(),
            {
                "role": "user",
                "content": [
                    *(_image_block(img) for img in images),
                    {"type": "text", "text": USER_INSTRUCTION},
                ],
            },
        ]

    # -- analysis -----------------------------------------------------------

    def analyze(self, images: list[ImageInput]) -> AnalysisResult:
        if not images:
            raise ValueError("at least one image is required")

        messages = self._build_messages(images)
        raw = self._call(messages)
        try:
            return self._parse(raw)
        except (ValueError, ValidationError) as first_error:
            # One corrective retry, as specified: feed back the bad output
            # and the parse error, ask for plain JSON again.
            messages = messages + [
                {"role": "assistant", "content": [{"type": "text", "text": raw}]},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": RETRY_INSTRUCTION.format(error=first_error)}
                    ],
                },
            ]
            raw = self._call(messages)
            try:
                return self._parse(raw)
            except (ValueError, ValidationError) as second_error:
                raise VisionAnalysisError(
                    f"model output failed validation twice: {second_error}"
                ) from second_error

    def _call(self, messages: list[dict[str, Any]]) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": SYSTEM_PROMPT}],
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        if not text.strip():
            raise VisionAnalysisError("model returned an empty response")
        return text

    @staticmethod
    def _parse(raw: str) -> AnalysisResult:
        return AnalysisResult.model_validate(json.loads(strip_json_fences(raw)))
