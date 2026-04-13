"""Interface contracts for frame access and media probing."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from libs.schemas import FrameReference, VideoAsset


class FrameProvider(Protocol):
    """Yield decoded frames or frame references from a canonical video asset."""

    def open(self, source: Path) -> VideoAsset:
        ...

    def read_frame(self, frame_index: int) -> tuple[FrameReference, object]:
        ...
