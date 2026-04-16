"""Baseline sweep builder for per-player identity evaluation.

This module stays deliberately simple for Phase 1. It assumes upstream
detector/tracker lanes have already enumerated player `TrackObservation`
records. For each player track it:

1. builds a stable `TargetPlayerSelection`
2. emits an explicit but trivial `IdentityAssignment`
3. prepares a possession/clip run request for downstream workers

The scorer is intentionally transparent. It does not claim production-grade
player re-identification. Its purpose is to give the Phase 1 sweep harness a
deterministic, inspectable baseline that can exercise the rest of the pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import hypot
from statistics import mean
from typing import Iterable, Sequence
from uuid import uuid4

from libs.identity.interfaces import (
    IdentityAssignment,
    IdentityCandidate,
    IdentityCueScores,
    IdentityScorer,
)
from libs.schemas import (
    ClipBoundaryRule,
    FrameReference,
    IdentityState,
    TargetPlayerSelection,
    TrackObservation,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _safe_mean(values: Sequence[float], default: float = 0.0) -> float:
    return mean(values) if values else default


def _frame_span(observations: Sequence[TrackObservation]) -> int:
    if not observations:
        return 0
    return observations[-1].frame.frame_index - observations[0].frame.frame_index + 1


def _bbox_area(observation: TrackObservation) -> float:
    return max(observation.bbox.width, 0.0) * max(observation.bbox.height, 0.0)


def _center(observation: TrackObservation) -> tuple[float, float]:
    return (
        observation.bbox.x + (observation.bbox.width / 2.0),
        observation.bbox.y + (observation.bbox.height / 2.0),
    )


def _diagonal(observation: TrackObservation) -> float:
    return hypot(max(observation.bbox.width, 0.0), max(observation.bbox.height, 0.0))


def _most_common_metadata_fraction(
    observations: Sequence[TrackObservation],
    keys: Sequence[str],
) -> float:
    observed: list[str] = []
    for observation in observations:
        for key in keys:
            value = observation.metadata.get(key)
            if value:
                observed.append(f"{key}:{value}")
                break
    if not observed:
        return 0.5
    counts: dict[str, int] = {}
    for value in observed:
        counts[value] = counts.get(value, 0) + 1
    return max(counts.values()) / len(observed)


@dataclass(slots=True)
class PlayerTrackSummary:
    player_track_id: str
    total_frames_visible: int
    frame_span: int
    first_frame_index: int
    last_frame_index: int
    first_timestamp_s: float
    last_timestamp_s: float
    visible_duration_s: float
    average_detection_confidence: float
    average_bbox_area: float
    visibility_ratio: float
    continuity_ratio: float
    motion_consistency: float
    failure_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class PlayerSweepRequest:
    request_id: str
    source_asset_id: str
    player_track_id: str
    selection: TargetPlayerSelection
    seed_frame: FrameReference
    evaluation_window_start_s: float
    evaluation_window_end_s: float
    clip_boundary_rule: ClipBoundaryRule
    identity_state: IdentityState
    identity_confidence: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class PlayerSweepReport:
    player_track_id: str
    track_summary: PlayerTrackSummary
    identity_assignment: IdentityAssignment
    sweep_request: PlayerSweepRequest

    def to_dict(self) -> dict[str, object]:
        return {
            "player_track_id": self.player_track_id,
            "track_summary": self.track_summary.to_dict(),
            "identity_assignment": asdict(self.identity_assignment),
            "sweep_request": self.sweep_request.to_dict(),
        }


class BaselineIdentityScorer(IdentityScorer):
    """Transparent fallback scorer for Phase 1 sweep testing.

    Score construction:
    - tracker continuity: continuity of the selected track itself
    - appearance similarity: average detection confidence proxy
    - team color similarity: metadata consistency proxy
    - motion consistency: abrupt-jump penalty proxy

    Alternatives are ranked with intentionally weak cross-track heuristics so
    downstream diagnostics can surface runner-ups without pretending re-ID is
    solved already.
    """

    name = "baseline_identity_scorer_v1"

    def assign(
        self,
        selected_track_seed: TrackObservation,
        candidate_tracks: Iterable[TrackObservation],
    ) -> IdentityAssignment:
        grouped = _group_player_tracks(candidate_tracks)
        selected_id = selected_track_seed.track_id
        selected_track = grouped.get(selected_id, [])

        if not selected_track:
            explanation = [
                "selected track id was not present in the provided candidate tracks",
                "identity assignment is forced into LOST state",
            ]
            return IdentityAssignment(
                selected_track_id=None,
                state="LOST",
                confidence=0.0,
                visibility_confidence=0.0,
                margin_to_runner_up=None,
                cue_scores=None,
                alternates=[],
                explanation=explanation,
            )

        summary = summarize_track(selected_track)
        cue_scores = _build_primary_cue_scores(summary)
        selected_score = _weighted_score(cue_scores)

        alternates = _build_alternates(
            selected_track=selected_track,
            grouped_tracks=grouped,
            primary_summary=summary,
        )
        runner_up_score = alternates[0].confidence if alternates else 0.0
        margin = selected_score - runner_up_score
        state = _state_from_score(selected_score, margin)
        explanation = list(cue_scores.explanation)
        explanation.append(
            "confidence is a weighted baseline over continuity, confidence proxy, team-hint consistency, motion, and visibility"
        )
        if alternates:
            explanation.append(
                f"top alternate={alternates[0].track_id} at {alternates[0].confidence:.3f}"
            )

        return IdentityAssignment(
            selected_track_id=selected_id,
            state=state,
            confidence=selected_score,
            visibility_confidence=cue_scores.visibility_confidence,
            margin_to_runner_up=margin,
            cue_scores=cue_scores,
            alternates=alternates,
            explanation=explanation,
        )


class BaselineIdentitySweepBuilder:
    """Builds per-player sweep reports from enumerated track candidates."""

    def __init__(
        self,
        *,
        source_asset_id: str,
        clip_boundary_rule: ClipBoundaryRule | None = None,
        scorer: IdentityScorer | None = None,
        min_visible_frames: int = 3,
    ) -> None:
        self.source_asset_id = source_asset_id
        self.clip_boundary_rule = clip_boundary_rule or ClipBoundaryRule()
        self.scorer = scorer or BaselineIdentityScorer()
        self.min_visible_frames = min_visible_frames

    def build(self, track_candidates: Iterable[TrackObservation]) -> list[PlayerSweepReport]:
        grouped = _group_player_tracks(track_candidates)
        reports: list[PlayerSweepReport] = []

        for track_id in sorted(grouped):
            observations = grouped[track_id]
            summary = summarize_track(observations)
            if summary.total_frames_visible < self.min_visible_frames:
                summary.failure_flags.append("insufficient_visible_frames")

            seed = _seed_observation(observations)
            assignment = self.scorer.assign(seed, _flatten_grouped_tracks(grouped))
            selection = TargetPlayerSelection(
                project_id=self.source_asset_id,
                mode="track_list",
                seed_frame=seed.frame,
                selected_track_id=track_id,
                team_hint=_first_metadata_value(observations, ["team_id", "team_color"]),
                jersey_hint=_first_metadata_value(observations, ["jersey_number", "jersey_hint"]),
                color_hint=_first_metadata_value(observations, ["team_color", "kit_color"]),
            )
            request = PlayerSweepRequest(
                request_id=f"sweep-{track_id}-{uuid4().hex[:8]}",
                source_asset_id=self.source_asset_id,
                player_track_id=track_id,
                selection=selection,
                seed_frame=seed.frame,
                evaluation_window_start_s=summary.first_timestamp_s,
                evaluation_window_end_s=summary.last_timestamp_s,
                clip_boundary_rule=self.clip_boundary_rule,
                identity_state=assignment.state,
                identity_confidence=assignment.confidence,
                notes=_build_request_notes(summary, assignment),
            )
            reports.append(
                PlayerSweepReport(
                    player_track_id=track_id,
                    track_summary=summary,
                    identity_assignment=assignment,
                    sweep_request=request,
                )
            )

        return reports


def summarize_track(observations: Sequence[TrackObservation]) -> PlayerTrackSummary:
    if not observations:
        raise ValueError("expected at least one observation to summarize a track")

    ordered = sorted(observations, key=lambda item: item.frame.frame_index)
    total = len(ordered)
    span = _frame_span(ordered)
    avg_confidence = _safe_mean([item.confidence for item in ordered])
    avg_area = _safe_mean([_bbox_area(item) for item in ordered])
    visibility_ratio = _clamp(total / span) if span else 0.0
    continuity_ratio = _continuity_ratio(ordered)
    motion_consistency = _motion_consistency(ordered)
    start = ordered[0].frame
    end = ordered[-1].frame
    visible_duration = max(0.0, end.timestamp_s - start.timestamp_s)
    failure_flags: list[str] = []

    if visibility_ratio < 0.5:
        failure_flags.append("sparse_track")
    if motion_consistency < 0.4:
        failure_flags.append("motion_jitter")
    if avg_confidence < 0.45:
        failure_flags.append("low_detection_confidence")

    return PlayerTrackSummary(
        player_track_id=ordered[0].track_id,
        total_frames_visible=total,
        frame_span=span,
        first_frame_index=start.frame_index,
        last_frame_index=end.frame_index,
        first_timestamp_s=start.timestamp_s,
        last_timestamp_s=end.timestamp_s,
        visible_duration_s=visible_duration,
        average_detection_confidence=avg_confidence,
        average_bbox_area=avg_area,
        visibility_ratio=visibility_ratio,
        continuity_ratio=continuity_ratio,
        motion_consistency=motion_consistency,
        failure_flags=failure_flags,
    )


def _group_player_tracks(
    track_candidates: Iterable[TrackObservation],
) -> dict[str, list[TrackObservation]]:
    grouped: dict[str, list[TrackObservation]] = {}
    for observation in track_candidates:
        if observation.entity != "player":
            continue
        grouped.setdefault(observation.track_id, []).append(observation)
    for track_id in grouped:
        grouped[track_id].sort(key=lambda item: item.frame.frame_index)
    return grouped


def _flatten_grouped_tracks(grouped: dict[str, list[TrackObservation]]) -> list[TrackObservation]:
    flattened: list[TrackObservation] = []
    for observations in grouped.values():
        flattened.extend(observations)
    return flattened


def _seed_observation(observations: Sequence[TrackObservation]) -> TrackObservation:
    return max(
        observations,
        key=lambda item: (item.confidence, -item.frame.frame_index),
    )


def _first_metadata_value(observations: Sequence[TrackObservation], keys: Sequence[str]) -> str | None:
    for observation in observations:
        for key in keys:
            value = observation.metadata.get(key)
            if value:
                return value
    return None


def _continuity_ratio(observations: Sequence[TrackObservation]) -> float:
    if len(observations) < 2:
        return 1.0
    frame_gaps = [
        current.frame.frame_index - previous.frame.frame_index
        for previous, current in zip(observations, observations[1:])
    ]
    missing_frames = sum(max(gap - 1, 0) for gap in frame_gaps)
    total_possible = max(_frame_span(observations) - 1, 1)
    return _clamp(1.0 - (missing_frames / total_possible))


def _motion_consistency(observations: Sequence[TrackObservation]) -> float:
    if len(observations) < 2:
        return 1.0
    jump_penalties: list[float] = []
    for previous, current in zip(observations, observations[1:]):
        distance = hypot(_center(current)[0] - _center(previous)[0], _center(current)[1] - _center(previous)[1])
        scale = max((_diagonal(previous) + _diagonal(current)) / 2.0, 1.0)
        jump_penalties.append(distance / scale)
    average_jump = _safe_mean(jump_penalties)
    return _clamp(1.0 - (average_jump / 3.0))


def _build_primary_cue_scores(summary: PlayerTrackSummary) -> IdentityCueScores:
    sample_support = _clamp(summary.total_frames_visible / 4.0)
    supported_continuity = min(summary.continuity_ratio, sample_support)
    supported_motion = min(summary.motion_consistency, sample_support)
    appearance_proxy = _clamp((summary.average_detection_confidence * 0.75) + 0.1)
    team_consistency = 0.5
    explanation = [
        f"tracker continuity derived from visible density={summary.continuity_ratio:.3f}",
        f"sample support scales single-track confidence={sample_support:.3f}",
        f"appearance similarity uses detection confidence proxy={appearance_proxy:.3f}",
        "team color similarity is neutral unless upstream metadata is present",
        f"motion consistency penalizes abrupt center jumps={summary.motion_consistency:.3f}",
    ]
    if summary.failure_flags:
        explanation.append(f"failure flags={','.join(summary.failure_flags)}")

    return IdentityCueScores(
        tracker_continuity=supported_continuity,
        appearance_similarity=appearance_proxy,
        team_color_similarity=team_consistency,
        motion_consistency=supported_motion,
        visibility_confidence=_visibility_confidence(summary),
        explanation=explanation,
    )


def _visibility_confidence(summary: PlayerTrackSummary) -> float:
    sample_support = _clamp(summary.total_frames_visible / 4.0)
    return _clamp(
        (summary.average_detection_confidence * 0.45)
        + (summary.visibility_ratio * 0.20)
        + (summary.continuity_ratio * 0.10)
        + (sample_support * 0.25)
    )


def _weighted_score(cues: IdentityCueScores) -> float:
    return _clamp(
        (cues.tracker_continuity * 0.40)
        + (cues.appearance_similarity * 0.20)
        + (cues.team_color_similarity * 0.10)
        + (cues.motion_consistency * 0.15)
        + (cues.visibility_confidence * 0.15)
    )


def _build_alternates(
    *,
    selected_track: Sequence[TrackObservation],
    grouped_tracks: dict[str, list[TrackObservation]],
    primary_summary: PlayerTrackSummary,
    max_alternates: int = 3,
) -> list[IdentityCandidate]:
    selected_id = selected_track[0].track_id
    alternates: list[IdentityCandidate] = []
    selected_start = selected_track[0].frame.frame_index
    selected_end = selected_track[-1].frame.frame_index

    for track_id, observations in grouped_tracks.items():
        if track_id == selected_id:
            continue
        summary = summarize_track(observations)
        overlap = _temporal_overlap_ratio(
            selected_start=selected_start,
            selected_end=selected_end,
            other_start=observations[0].frame.frame_index,
            other_end=observations[-1].frame.frame_index,
        )
        size_similarity = _size_similarity(primary_summary.average_bbox_area, summary.average_bbox_area)
        team_similarity = _most_common_metadata_fraction(
            observations,
            keys=["team_id", "team_color", "kit_color"],
        )
        cues = IdentityCueScores(
            tracker_continuity=0.0,
            appearance_similarity=_clamp((summary.average_detection_confidence * 0.5) + (size_similarity * 0.5)),
            team_color_similarity=team_similarity,
            motion_consistency=_clamp((summary.motion_consistency * 0.6) + (overlap * 0.4)),
            visibility_confidence=_visibility_confidence(summary),
            explanation=[
                f"alternate overlap ratio={overlap:.3f}",
                f"alternate size similarity={size_similarity:.3f}",
                f"alternate team-hint consistency={team_similarity:.3f}",
            ],
        )
        confidence = _weighted_score(cues)
        alternates.append(
            IdentityCandidate(
                track_id=track_id,
                score=confidence,
                confidence=confidence,
                cue_scores=cues,
            )
        )

    alternates.sort(key=lambda item: item.confidence, reverse=True)
    return alternates[:max_alternates]


def _temporal_overlap_ratio(
    *,
    selected_start: int,
    selected_end: int,
    other_start: int,
    other_end: int,
) -> float:
    overlap_start = max(selected_start, other_start)
    overlap_end = min(selected_end, other_end)
    if overlap_end < overlap_start:
        return 0.0
    overlap = overlap_end - overlap_start + 1
    union_start = min(selected_start, other_start)
    union_end = max(selected_end, other_end)
    union = max(union_end - union_start + 1, 1)
    return _clamp(overlap / union)


def _size_similarity(primary_area: float, other_area: float) -> float:
    if primary_area <= 0.0 or other_area <= 0.0:
        return 0.5
    ratio = min(primary_area, other_area) / max(primary_area, other_area)
    return _clamp(ratio)


def _state_from_score(score: float, margin: float) -> IdentityState:
    if score >= 0.70 and margin >= 0.15:
        return "LOCKED"
    if score >= 0.45:
        return "UNCERTAIN"
    return "LOST"


def _build_request_notes(
    summary: PlayerTrackSummary,
    assignment: IdentityAssignment,
) -> list[str]:
    notes = [
        f"seed_track={summary.player_track_id}",
        f"identity_state={assignment.state}",
        f"identity_confidence={assignment.confidence:.3f}",
        f"visible_frames={summary.total_frames_visible}",
        "prepared for downstream possession inference and clip segmentation",
    ]
    if summary.failure_flags:
        notes.append(f"failure_flags={','.join(summary.failure_flags)}")
    return notes


__all__ = [
    "BaselineIdentityScorer",
    "BaselineIdentitySweepBuilder",
    "PlayerSweepReport",
    "PlayerSweepRequest",
    "PlayerTrackSummary",
    "summarize_track",
]
