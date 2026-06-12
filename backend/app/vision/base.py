"""Provider-agnostic vision analyzer interface.

The rest of the application only depends on this module and on
`schemas.AnalysisResult`. Swapping Claude for another provider (e.g. a
fine-tuned vision model on Microsoft Foundry or Vertex AI) means writing one
new adapter and registering it here — geometry engine, API and frontend stay
untouched.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .schemas import AnalysisResult

#: Maps file suffixes to media types accepted by vision APIs.
IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


@dataclass(frozen=True)
class ImageInput:
    """One photo to analyse, as raw bytes plus its media type."""

    data: bytes
    media_type: str

    @classmethod
    def from_file(cls, path: str | Path) -> "ImageInput":
        path = Path(path)
        media_type = IMAGE_MEDIA_TYPES.get(path.suffix.lower())
        if media_type is None:
            raise ValueError(f"unsupported image type: {path.suffix} ({path})")
        return cls(data=path.read_bytes(), media_type=media_type)


class VisionAnalysisError(RuntimeError):
    """Raised when the backend cannot produce a valid AnalysisResult."""


class VisionAnalyzer(ABC):
    """Analyse product photos into a structured AnalysisResult."""

    @abstractmethod
    def analyze(self, images: list[ImageInput]) -> AnalysisResult:
        """Run one analysis over all photos of a single product."""


def get_analyzer(provider: str = "claude") -> VisionAnalyzer:
    """Factory: return the configured vision backend."""
    if provider == "claude":
        from .analyzer import ClaudeVisionAnalyzer

        return ClaudeVisionAnalyzer()
    raise ValueError(f"unknown vision provider: {provider}")
