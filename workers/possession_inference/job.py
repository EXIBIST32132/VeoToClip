"""Possession worker helpers for the phase-1 baseline pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from libs.possession import (
    BaselinePossessionConfig,
    BaselinePossessionInferenceEngine,
    RuleBasedClipBoundaryDecider,
)
from libs.schemas import BallInteraction, ClipBoundaryRule, PossessionSegment, TrackObservation, WorkerCapability


@dataclass(slots=True)
class PossessionWorkerResult:
    interactions: list[BallInteraction]
    segments: list[PossessionSegment]


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="possession_inference",
        responsibilities=[
            "Infer baseline touches and controlled interactions",
            "Segment possession intervals with explicit timeout rules",
            "Emit inspectable clip candidate intervals with confidence",
        ],
        phase_targets=["phase-1", "phase-4", "phase-5"],
    )


def build_engine(
    config: BaselinePossessionConfig | None = None,
) -> BaselinePossessionInferenceEngine:
    return BaselinePossessionInferenceEngine(config=config)


def run_baseline_inference(
    player_track: Iterable[TrackObservation],
    ball_track: Iterable[TrackObservation],
    rules: ClipBoundaryRule | None = None,
    config: BaselinePossessionConfig | None = None,
) -> PossessionWorkerResult:
    engine = build_engine(config=config)
    interactions, segments = engine.infer(player_track=player_track, ball_track=ball_track)
    if rules is not None:
        segments = RuleBasedClipBoundaryDecider().apply_rules(segments, rules)
    return PossessionWorkerResult(interactions=interactions, segments=segments)
