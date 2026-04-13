"""Contracts for interaction inference and clip boundary decisions."""

from __future__ import annotations

from typing import Iterable, Protocol

from libs.schemas import BallInteraction, ClipBoundaryRule, PossessionSegment, TrackObservation


class PossessionInferenceEngine(Protocol):
    name: str

    def infer(
        self,
        player_track: Iterable[TrackObservation],
        ball_track: Iterable[TrackObservation],
    ) -> tuple[list[BallInteraction], list[PossessionSegment]]:
        ...


class ClipBoundaryDecider(Protocol):
    name: str

    def apply_rules(
        self,
        segments: Iterable[PossessionSegment],
        rules: ClipBoundaryRule,
    ) -> list[PossessionSegment]:
        ...
