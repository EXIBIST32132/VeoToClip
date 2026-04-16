"""Structured report writers for player sweep evaluation artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from statistics import fmean
from typing import Any, Iterable, Sequence

from libs.identity.interfaces import IdentityAssignment
from libs.schemas import BallInteraction, ClipCandidate, PossessionSegment, TrackObservation, VideoAsset


REPORT_SCHEMA_VERSION = "phase-1-sweep-report.v1"
IDENTITY_STATES = ("LOCKED", "UNCERTAIN", "LOST")


@dataclass(slots=True)
class PlayerSweepInput:
    """Raw per-player outputs from the sweep pipeline before report summarization."""

    player_track_id: str
    track_observations: Sequence[TrackObservation] = field(default_factory=tuple)
    identity_assignments: Sequence[IdentityAssignment] = field(default_factory=tuple)
    interactions: Sequence[BallInteraction] = field(default_factory=tuple)
    possession_segments: Sequence[PossessionSegment] = field(default_factory=tuple)
    clips: Sequence[ClipCandidate] = field(default_factory=tuple)
    failure_flags: Sequence[str] = field(default_factory=tuple)
    debug_artifact_paths: Sequence[Path] = field(default_factory=tuple)
    preview_artifact_paths: Sequence[Path] = field(default_factory=tuple)
    notes: Sequence[str] = field(default_factory=tuple)


@dataclass(slots=True)
class IdentityConfidenceSummary:
    observation_count: int
    average_confidence: float
    min_confidence: float
    max_confidence: float
    average_visibility_confidence: float
    average_margin_to_runner_up: float | None
    locked_ratio: float
    uncertain_ratio: float
    lost_ratio: float
    state_counts: dict[str, int]
    final_state: str | None


@dataclass(slots=True)
class ClipIntervalReport:
    clip_id: str
    segment_id: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    confidence: float
    reason: str
    accepted: bool | None


@dataclass(slots=True)
class PlayerSweepReport:
    schema_version: str
    generated_at: str
    video_asset_id: str
    video_source_path: str
    player_track_id: str
    total_frames_visible: int
    visibility_time_range_s: tuple[float, float] | None
    identity_confidence_summary: IdentityConfidenceSummary
    number_of_detected_touches: int
    interaction_counts_by_label: dict[str, int]
    number_of_generated_clips: int
    average_clip_duration_s: float
    clip_intervals: list[ClipIntervalReport]
    failure_flags: list[str]
    confidence_metrics: dict[str, float | None]
    debug_artifact_paths: list[str]
    preview_artifact_paths: list[str]
    notes: list[str]


@dataclass(slots=True)
class VideoSweepReport:
    schema_version: str
    generated_at: str
    video_asset_id: str
    video_source_path: str
    total_players_tested: int
    total_detected_touches: int
    total_generated_clips: int
    average_clip_duration_s: float
    average_identity_confidence: float | None
    players_with_generated_clips: int
    players_with_failures: int
    player_report_paths: dict[str, str]
    player_summaries: list[dict[str, Any]]
    top_players_by_clip_count: list[dict[str, Any]]


@dataclass(slots=True)
class AggregateSweepReport:
    schema_version: str
    generated_at: str
    total_videos_processed: int
    total_players_tested: int
    total_detected_touches: int
    total_generated_clips: int
    average_clip_duration_s: float
    videos_with_failures: int
    per_video_summaries: list[dict[str, Any]]


@dataclass(slots=True)
class WrittenVideoSweepReport:
    report_directory: Path
    summary_path: Path
    player_report_paths: dict[str, Path]
    report: VideoSweepReport


def build_player_report(video: VideoAsset, sweep_input: PlayerSweepInput) -> PlayerSweepReport:
    """Summarize a single selected-player sweep run into a structured report."""

    visibility_time_range = _visibility_time_range(sweep_input.track_observations)
    identity_summary = _summarize_identity(sweep_input.identity_assignments)
    clip_intervals = _build_clip_intervals(sweep_input.clips)
    interaction_counts = _count_interactions(sweep_input.interactions)
    failure_flags = _derive_failure_flags(sweep_input)
    average_clip_duration = _mean(clip.duration_s for clip in clip_intervals)

    return PlayerSweepReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=_utcnow(),
        video_asset_id=video.asset_id,
        video_source_path=video.source_path,
        player_track_id=sweep_input.player_track_id,
        total_frames_visible=_count_visible_frames(sweep_input.track_observations),
        visibility_time_range_s=visibility_time_range,
        identity_confidence_summary=identity_summary,
        number_of_detected_touches=len(sweep_input.interactions),
        interaction_counts_by_label=interaction_counts,
        number_of_generated_clips=len(clip_intervals),
        average_clip_duration_s=average_clip_duration,
        clip_intervals=clip_intervals,
        failure_flags=failure_flags,
        confidence_metrics=_build_confidence_metrics(
            sweep_input.identity_assignments,
            sweep_input.interactions,
            sweep_input.possession_segments,
            sweep_input.clips,
        ),
        debug_artifact_paths=[str(path) for path in sweep_input.debug_artifact_paths],
        preview_artifact_paths=[str(path) for path in sweep_input.preview_artifact_paths],
        notes=list(sweep_input.notes),
    )


def build_video_report(video: VideoAsset, player_reports: Iterable[PlayerSweepReport]) -> VideoSweepReport:
    """Aggregate per-player reports into a per-video summary."""

    reports = sorted(player_reports, key=lambda report: report.player_track_id)
    clip_durations = [report.average_clip_duration_s for report in reports if report.number_of_generated_clips]
    identity_confidences = [
        report.identity_confidence_summary.average_confidence
        for report in reports
        if report.identity_confidence_summary.observation_count
    ]

    player_summaries = [
        {
            "player_track_id": report.player_track_id,
            "total_frames_visible": report.total_frames_visible,
            "number_of_detected_touches": report.number_of_detected_touches,
            "number_of_generated_clips": report.number_of_generated_clips,
            "average_clip_duration_s": report.average_clip_duration_s,
            "failure_flags": report.failure_flags,
            "identity_final_state": report.identity_confidence_summary.final_state,
            "identity_average_confidence": report.identity_confidence_summary.average_confidence,
        }
        for report in reports
    ]
    top_players = sorted(
        player_summaries,
        key=lambda summary: (
            summary["number_of_generated_clips"],
            summary["number_of_detected_touches"],
            summary["total_frames_visible"],
        ),
        reverse=True,
    )[:5]

    return VideoSweepReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=_utcnow(),
        video_asset_id=video.asset_id,
        video_source_path=video.source_path,
        total_players_tested=len(reports),
        total_detected_touches=sum(report.number_of_detected_touches for report in reports),
        total_generated_clips=sum(report.number_of_generated_clips for report in reports),
        average_clip_duration_s=_mean(clip_durations),
        average_identity_confidence=_mean(identity_confidences, none_if_empty=True),
        players_with_generated_clips=sum(1 for report in reports if report.number_of_generated_clips > 0),
        players_with_failures=sum(1 for report in reports if report.failure_flags),
        player_report_paths={},
        player_summaries=player_summaries,
        top_players_by_clip_count=top_players,
    )


def build_aggregate_report(video_reports: Iterable[VideoSweepReport]) -> AggregateSweepReport:
    """Aggregate multiple per-video summaries into a cross-video report."""

    reports = list(video_reports)
    clip_durations = [report.average_clip_duration_s for report in reports if report.total_generated_clips]

    per_video_summaries = [
        {
            "video_asset_id": report.video_asset_id,
            "video_source_path": report.video_source_path,
            "total_players_tested": report.total_players_tested,
            "total_detected_touches": report.total_detected_touches,
            "total_generated_clips": report.total_generated_clips,
            "players_with_generated_clips": report.players_with_generated_clips,
            "players_with_failures": report.players_with_failures,
        }
        for report in reports
    ]

    return AggregateSweepReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=_utcnow(),
        total_videos_processed=len(reports),
        total_players_tested=sum(report.total_players_tested for report in reports),
        total_detected_touches=sum(report.total_detected_touches for report in reports),
        total_generated_clips=sum(report.total_generated_clips for report in reports),
        average_clip_duration_s=_mean(clip_durations),
        videos_with_failures=sum(1 for report in reports if report.players_with_failures > 0),
        per_video_summaries=per_video_summaries,
    )


class SweepReportWriter:
    """Write per-player, per-video, and multi-video sweep reports to JSON artifacts."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def write_video_report(
        self,
        video: VideoAsset,
        player_inputs: Iterable[PlayerSweepInput],
    ) -> WrittenVideoSweepReport:
        report_directory = self.output_root / _slugify(Path(video.source_path).stem or video.asset_id)
        player_directory = report_directory / "players"
        player_directory.mkdir(parents=True, exist_ok=True)

        player_reports: list[PlayerSweepReport] = []
        player_report_paths: dict[str, Path] = {}
        for sweep_input in sorted(player_inputs, key=lambda item: item.player_track_id):
            player_report = build_player_report(video, sweep_input)
            player_reports.append(player_report)
            player_path = player_directory / f"{_slugify(sweep_input.player_track_id)}.json"
            self._write_json(player_path, player_report)
            player_report_paths[player_report.player_track_id] = player_path

        video_report = build_video_report(video, player_reports)
        video_report.player_report_paths = {
            track_id: str(path.relative_to(report_directory))
            for track_id, path in sorted(player_report_paths.items())
        }

        summary_path = report_directory / "summary.json"
        self._write_json(summary_path, video_report)
        return WrittenVideoSweepReport(
            report_directory=report_directory,
            summary_path=summary_path,
            player_report_paths=player_report_paths,
            report=video_report,
        )

    def write_aggregate_report(
        self,
        video_reports: Iterable[WrittenVideoSweepReport | VideoSweepReport],
        output_path: Path | None = None,
    ) -> Path:
        reports = [
            written.report if isinstance(written, WrittenVideoSweepReport) else written
            for written in video_reports
        ]
        aggregate_report = build_aggregate_report(reports)
        destination = output_path or self.output_root / "aggregate-summary.json"
        self._write_json(destination, aggregate_report)
        return destination

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _summarize_identity(assignments: Sequence[IdentityAssignment]) -> IdentityConfidenceSummary:
    if not assignments:
        return IdentityConfidenceSummary(
            observation_count=0,
            average_confidence=0.0,
            min_confidence=0.0,
            max_confidence=0.0,
            average_visibility_confidence=0.0,
            average_margin_to_runner_up=None,
            locked_ratio=0.0,
            uncertain_ratio=0.0,
            lost_ratio=0.0,
            state_counts={state: 0 for state in IDENTITY_STATES},
            final_state=None,
        )

    confidences = [assignment.confidence for assignment in assignments]
    visibilities = [assignment.visibility_confidence for assignment in assignments]
    margins = [
        assignment.margin_to_runner_up
        for assignment in assignments
        if assignment.margin_to_runner_up is not None
    ]
    state_counts = {state: 0 for state in IDENTITY_STATES}
    for assignment in assignments:
        state_counts[assignment.state] = state_counts.get(assignment.state, 0) + 1

    total = float(len(assignments))
    return IdentityConfidenceSummary(
        observation_count=len(assignments),
        average_confidence=_mean(confidences),
        min_confidence=min(confidences),
        max_confidence=max(confidences),
        average_visibility_confidence=_mean(visibilities),
        average_margin_to_runner_up=_mean(margins, none_if_empty=True),
        locked_ratio=state_counts.get("LOCKED", 0) / total,
        uncertain_ratio=state_counts.get("UNCERTAIN", 0) / total,
        lost_ratio=state_counts.get("LOST", 0) / total,
        state_counts=state_counts,
        final_state=assignments[-1].state,
    )


def _build_clip_intervals(clips: Sequence[ClipCandidate]) -> list[ClipIntervalReport]:
    intervals = [
        ClipIntervalReport(
            clip_id=clip.clip_id,
            segment_id=clip.segment_id,
            start_time_s=clip.start_time_s,
            end_time_s=clip.end_time_s,
            duration_s=max(0.0, clip.end_time_s - clip.start_time_s),
            confidence=clip.confidence,
            reason=clip.reason,
            accepted=clip.accepted,
        )
        for clip in sorted(clips, key=lambda clip: (clip.start_time_s, clip.end_time_s, clip.clip_id))
    ]
    return intervals


def _count_interactions(interactions: Sequence[BallInteraction]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for interaction in interactions:
        counts[interaction.label] = counts.get(interaction.label, 0) + 1
    return dict(sorted(counts.items()))


def _derive_failure_flags(sweep_input: PlayerSweepInput) -> list[str]:
    flags = set(sweep_input.failure_flags)
    if not sweep_input.track_observations:
        flags.add("no_visible_frames")
    if not sweep_input.identity_assignments:
        flags.add("missing_identity_results")
    if sweep_input.identity_assignments and all(
        assignment.state == "LOST" for assignment in sweep_input.identity_assignments
    ):
        flags.add("identity_never_locked")
    if not sweep_input.interactions:
        flags.add("no_interactions_detected")
    if not sweep_input.clips:
        flags.add("no_clips_generated")
    return sorted(flags)


def _build_confidence_metrics(
    identity_assignments: Sequence[IdentityAssignment],
    interactions: Sequence[BallInteraction],
    possession_segments: Sequence[PossessionSegment],
    clips: Sequence[ClipCandidate],
) -> dict[str, float | None]:
    identity_confidences = [assignment.confidence for assignment in identity_assignments]
    interaction_confidences = [interaction.confidence for interaction in interactions]
    possession_confidences = [segment.confidence for segment in possession_segments]
    clip_confidences = [clip.confidence for clip in clips]

    return {
        "mean_identity_confidence": _mean(identity_confidences, none_if_empty=True),
        "mean_visibility_confidence": _mean(
            (assignment.visibility_confidence for assignment in identity_assignments),
            none_if_empty=True,
        ),
        "mean_interaction_confidence": _mean(interaction_confidences, none_if_empty=True),
        "mean_possession_confidence": _mean(possession_confidences, none_if_empty=True),
        "mean_clip_confidence": _mean(clip_confidences, none_if_empty=True),
        "max_clip_confidence": max(clip_confidences) if clip_confidences else None,
    }


def _count_visible_frames(observations: Sequence[TrackObservation]) -> int:
    return len({observation.frame.frame_index for observation in observations})


def _visibility_time_range(observations: Sequence[TrackObservation]) -> tuple[float, float] | None:
    if not observations:
        return None
    timestamps = sorted(observation.frame.timestamp_s for observation in observations)
    return (timestamps[0], timestamps[-1])


def _mean(values: Iterable[float], *, none_if_empty: bool = False) -> float | None:
    items = list(values)
    if not items:
        return None if none_if_empty else 0.0
    return float(fmean(items))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return slug.strip("-") or "report"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _json_ready(payload: Any) -> Any:
    if hasattr(payload, "__dataclass_fields__"):
        return _json_ready(asdict(payload))
    if isinstance(payload, Path):
        return str(payload)
    if isinstance(payload, dict):
        return {str(key): _json_ready(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_json_ready(value) for value in payload]
    return payload
