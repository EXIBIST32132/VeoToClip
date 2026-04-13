"""Selected-player identity scoring protocols."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from libs.schemas import IdentityState, TrackObservation


@dataclass(slots=True)
class IdentityCueScores:
    tracker_continuity: float
    appearance_similarity: float
    team_color_similarity: float
    motion_consistency: float
    jersey_hint_match: float = 0.0
    segmentation_quality: float | None = None
    visibility_confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IdentityCandidate:
    track_id: str
    score: float
    confidence: float
    cue_scores: IdentityCueScores


@dataclass(slots=True)
class IdentityAssignment:
    selected_track_id: str | None
    state: IdentityState
    confidence: float
    visibility_confidence: float
    margin_to_runner_up: float | None
    cue_scores: IdentityCueScores | None
    alternates: list[IdentityCandidate] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


class IdentityScorer(Protocol):
    name: str

    def assign(
        self,
        selected_track_seed: TrackObservation,
        candidate_tracks: Iterable[TrackObservation],
    ) -> IdentityAssignment:
        ...
