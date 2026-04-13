"""Detector and tracker protocols kept implementation-agnostic."""

from __future__ import annotations

from typing import Iterable, Protocol

from libs.schemas import Detection, FrameReference, TrackObservation


class Detector(Protocol):
    name: str

    def detect(self, frame: tuple[FrameReference, object]) -> Iterable[Detection]:
        ...


class Tracker(Protocol):
    name: str

    def update(self, detections: Iterable[Detection]) -> Iterable[TrackObservation]:
        ...
