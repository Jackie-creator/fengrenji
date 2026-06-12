"""Real-call demo: analyse product photos with the Claude vision layer.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...   # or put it in .env
    python scripts/analyze_example.py photos/front.jpg photos/inside.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.vision.base import ImageInput, get_analyzer


def main() -> None:
    load_dotenv()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    images = [ImageInput.from_file(p) for p in sys.argv[1:]]
    print(f"分析 {len(images)} 张照片……")
    result = get_analyzer("claude").analyze(images)
    print(result.model_dump_json(indent=2))
    print(f"\n识别结果：{result.category.value}（置信度 {result.confidence:.0%}）")
    print(f"说明：{result.notes_for_user}")


if __name__ == "__main__":
    main()
