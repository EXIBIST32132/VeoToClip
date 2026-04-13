"""Shared schema definitions for early pipeline contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


EntityLabel = Literal["player", "ball", "referee", "unknown"]
SelectionMode = Literal["click", "box", "mask", "track_list"]
IdentityState = Literal["LOCKED", "UNCERTAIN", "LOST"]
ExportMode = Literal["single", "batch", "compilation"]
InteractionLabel = Literal[
    "touch",
    "dribble",
    "pass",
    "shot",
    "interception",
    "deflection",
    "tackle",
    "loose_ball",
]


@dataclass(slots=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class FrameReference:
    frame_index: int
    timestamp_s: float


@dataclass(slots=True)
class VideoAsset:
    asset_id: str
    source_path: str
    frame_rate: float
    duration_s: float
    width: int
    height: int


@dataclass(slots=True)
class ProjectConfig:
    project_id: str
    video: VideoAsset
    target_player_label: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TargetPlayerSelection:
    project_id: str
    mode: SelectionMode
    seed_frame: FrameReference
    selected_track_id: str | None = None
    team_hint: str | None = None
    jersey_hint: str | None = None
    color_hint: str | None = None


@dataclass(slots=True)
class Detection:
    entity: EntityLabel
    confidence: float
    frame: FrameReference
    bbox: BoundingBox
    detector_name: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DetectorFrameOutput:
    frame: FrameReference
    detections: list[Detection]
    detector_name: str


@dataclass(slots=True)
class TrackObservation:
    track_id: str
    entity: EntityLabel
    frame: FrameReference
    bbox: BoundingBox
    confidence: float
    source_detection_confidence: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TrackerFrameOutput:
    frame: FrameReference
    tracker_name: str
    tracks: list[TrackObservation]


@dataclass(slots=True)
class BallInteraction:
    interaction_id: str
    player_track_id: str
    frame: FrameReference
    label: InteractionLabel
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PossessionSegment:
    segment_id: str
    player_track_id: str
    start_time_s: float
    end_time_s: float
    confidence: float
    end_reason: str
    interaction_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClipBoundaryRule:
    pre_roll_s: float = 1.5
    post_roll_s: float = 1.5
    loose_ball_timeout_s: float = 1.25
    controller_switch_hysteresis_frames: int = 4


@dataclass(slots=True)
class ClipCandidate:
    clip_id: str
    source_asset_id: str
    segment_id: str
    start_time_s: float
    end_time_s: float
    confidence: float
    reason: str
    accepted: bool | None = None


@dataclass(slots=True)
class ClipRequest:
    request_id: str
    source_asset_id: str
    player_track_id: str
    segment_id: str
    rules: ClipBoundaryRule
    include_tactical_tail: bool = False


@dataclass(slots=True)
class ExportJob:
    export_id: str
    mode: ExportMode
    clip_ids: list[str]
    destination_dir: str
    include_metadata: bool = True
    include_audit_trail: bool = True


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    actor: str
    action: str
    target_id: str
    timestamp_s: float
    payload: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AnnotationBundle:
    schema_version: str
    video: VideoAsset
    tracks: list[TrackObservation] = field(default_factory=list)
    interactions: list[BallInteraction] = field(default_factory=list)
    possessions: list[PossessionSegment] = field(default_factory=list)
    clips: list[ClipCandidate] = field(default_factory=list)
    audit_trail: list[AuditEvent] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationMetricSpec:
    metric_name: str
    description: str
    higher_is_better: bool
    unit: str


@dataclass(slots=True)
class WorkerCapability:
    name: str
    responsibilities: list[str]
    phase_targets: list[str]
