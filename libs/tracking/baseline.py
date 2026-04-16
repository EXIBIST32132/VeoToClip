"""Baseline real-video detector and tracker implementations for Phase 1."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import ssl
from typing import Iterable, Iterator

import numpy as np
from scipy.optimize import linear_sum_assignment
import torch
import torchvision

from libs.schemas import (
    BoundingBox,
    Detection,
    FrameReference,
    TrackObservation,
    TrackerFrameOutput,
)
from libs.tracking.interfaces import Detector, Tracker
from libs.video_io.avfoundation import AVFoundationFrameProvider


PLAYER_LABEL = 1
BALL_LABEL = 37


@dataclass(slots=True)
class DetectorConfig:
    """Configuration for the COCO detector baseline."""

    model_name: str = "ssdlite320_mobilenet_v3_large"
    player_confidence_threshold: float = 0.15
    ball_confidence_threshold: float = 0.10
    max_detections_per_frame: int = 50
    device: str | None = None
    allow_insecure_download: bool = True


@dataclass(slots=True)
class TrackerConfig:
    """Configuration for the lightweight multi-object tracker."""

    min_iou: float = 0.15
    max_center_distance_px: float = 140.0
    max_staleness_frames: int = 45
    min_confirmation_hits: int = 1


@dataclass(slots=True)
class TrackingRunConfig:
    """Configuration for running the full detection + tracking pass."""

    sample_fps: float = 2.0
    start_time_s: float = 0.0
    max_frames: int | None = None
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)


@dataclass(slots=True)
class TrackingRunResult:
    """Outputs from a sampled tracking pass."""

    video_asset: dict[str, object]
    tracker_name: str
    detector_name: str
    sampled_frames: int
    track_frames: list[TrackerFrameOutput]
    summary: dict[str, object]


@dataclass(slots=True)
class _TrackState:
    track_id: str
    entity: str
    bbox: BoundingBox
    confidence: float
    source_detection_confidence: float
    last_frame_index: int
    hits: int = 1


class TorchvisionCocoDetector(Detector):
    """Baseline detector using a pretrained torchvision COCO model."""

    _MODEL_BUILDERS = {
        "ssdlite320_mobilenet_v3_large": (
            torchvision.models.detection.ssdlite320_mobilenet_v3_large,
            torchvision.models.detection.SSDLite320_MobileNet_V3_Large_Weights.DEFAULT,
        ),
        "fasterrcnn_mobilenet_v3_large_320_fpn": (
            torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn,
            torchvision.models.detection.FasterRCNN_MobileNet_V3_Large_320_FPN_Weights.DEFAULT,
        ),
    }

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self.name = f"torchvision_{self.config.model_name}_coco"
        self._model = None
        self._preprocess = None
        self._device = torch.device(self._resolve_device())

    def detect(self, frame: tuple[FrameReference, object]) -> Iterable[Detection]:
        reference, image = frame
        array = np.asarray(image)
        if array.ndim != 3 or array.shape[2] < 3:
            msg = "Expected an HxWx3 image array for detection."
            raise ValueError(msg)

        self._ensure_model()
        tensor = torch.from_numpy(np.ascontiguousarray(array[:, :, :3])).permute(2, 0, 1)
        input_tensor = self._preprocess(tensor) if self._preprocess is not None else tensor.float() / 255.0

        with torch.no_grad():
            output = self._model([input_tensor.to(self._device)])[0]

        labels = output["labels"].detach().cpu().tolist()
        scores = output["scores"].detach().cpu().tolist()
        boxes = output["boxes"].detach().cpu().tolist()

        detections: list[Detection] = []
        for label, score, box in zip(labels, scores, boxes):
            entity = None
            threshold = None
            if label == PLAYER_LABEL:
                entity = "player"
                threshold = self.config.player_confidence_threshold
            elif label == BALL_LABEL:
                entity = "ball"
                threshold = self.config.ball_confidence_threshold

            if entity is None or score < threshold:
                continue

            x1, y1, x2, y2 = box
            width = max(0.0, float(x2 - x1))
            height = max(0.0, float(y2 - y1))
            if width <= 0.0 or height <= 0.0:
                continue

            detections.append(
                Detection(
                    entity=entity,
                    confidence=float(score),
                    frame=reference,
                    bbox=BoundingBox(x=float(x1), y=float(y1), width=width, height=height),
                    detector_name=self.name,
                    attributes={"coco_label": "person" if label == PLAYER_LABEL else "sports_ball"},
                )
            )
            if len(detections) >= self.config.max_detections_per_frame:
                break
        return detections

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if self.config.model_name not in self._MODEL_BUILDERS:
            msg = f"Unsupported detector model: {self.config.model_name}"
            raise ValueError(msg)

        builder, weights = self._MODEL_BUILDERS[self.config.model_name]
        if self.config.allow_insecure_download:
            with _temporary_insecure_ssl_context():
                model = builder(weights=weights)
        else:
            model = builder(weights=weights)

        self._model = model.eval().to(self._device)
        self._preprocess = weights.transforms()

    def _resolve_device(self) -> str:
        if self.config.device:
            return self.config.device
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"


class IoUTracker(Tracker):
    """Minimal multi-object tracker for frame-aligned player and ball IDs."""

    def __init__(self, config: TrackerConfig | None = None) -> None:
        self.config = config or TrackerConfig()
        self.name = "iou_linear_assignment"
        self._active_tracks: dict[str, list[_TrackState]] = defaultdict(list)
        self._entity_counters: dict[str, int] = defaultdict(int)

    def update(self, detections: Iterable[Detection]) -> Iterable[TrackObservation]:
        grouped: dict[str, list[Detection]] = defaultdict(list)
        current_frame: FrameReference | None = None
        for detection in detections:
            grouped[detection.entity].append(detection)
            current_frame = detection.frame

        if current_frame is None:
            return []

        visible: list[TrackObservation] = []
        for entity, entity_detections in grouped.items():
            active_tracks = self._prune_stale_tracks(entity, current_frame.frame_index)
            if not active_tracks:
                visible.extend(self._spawn_tracks(entity, entity_detections))
                continue

            assignments, unmatched_tracks, unmatched_detections = self._match(active_tracks, entity_detections)

            for track_index, detection_index in assignments:
                track = active_tracks[track_index]
                detection = entity_detections[detection_index]
                track.bbox = detection.bbox
                track.confidence = detection.confidence
                track.source_detection_confidence = detection.confidence
                track.last_frame_index = current_frame.frame_index
                track.hits += 1
                visible.append(self._to_observation(track, detection.frame))

            for detection_index in unmatched_detections:
                detection = entity_detections[detection_index]
                visible.extend(self._spawn_tracks(entity, [detection]))

        return visible

    def _match(
        self,
        active_tracks: list[_TrackState],
        detections: list[Detection],
    ) -> tuple[list[tuple[int, int]], set[int], set[int]]:
        if not active_tracks or not detections:
            return [], set(range(len(active_tracks))), set(range(len(detections)))

        costs = np.full((len(active_tracks), len(detections)), fill_value=1_000.0, dtype=np.float32)
        for track_index, track in enumerate(active_tracks):
            for detection_index, detection in enumerate(detections):
                iou = _bbox_iou(track.bbox, detection.bbox)
                center_distance = _bbox_center_distance(track.bbox, detection.bbox)
                if iou < self.config.min_iou and center_distance > self.config.max_center_distance_px:
                    continue
                distance_score = max(
                    0.0,
                    1.0 - min(center_distance / self.config.max_center_distance_px, 1.0),
                )
                score = iou + 0.25 * distance_score
                costs[track_index, detection_index] = 1.0 - score

        row_ind, col_ind = linear_sum_assignment(costs)
        assignments: list[tuple[int, int]] = []
        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()
        for track_index, detection_index in zip(row_ind.tolist(), col_ind.tolist()):
            if costs[track_index, detection_index] >= 1.0:
                continue
            assignments.append((track_index, detection_index))
            matched_tracks.add(track_index)
            matched_detections.add(detection_index)

        unmatched_tracks = set(range(len(active_tracks))) - matched_tracks
        unmatched_detections = set(range(len(detections))) - matched_detections
        return assignments, unmatched_tracks, unmatched_detections

    def _prune_stale_tracks(self, entity: str, current_frame_index: int) -> list[_TrackState]:
        survivors = [
            track
            for track in self._active_tracks[entity]
            if current_frame_index - track.last_frame_index <= self.config.max_staleness_frames
        ]
        self._active_tracks[entity] = survivors
        return survivors

    def _spawn_tracks(self, entity: str, detections: list[Detection]) -> list[TrackObservation]:
        visible: list[TrackObservation] = []
        for detection in detections:
            self._entity_counters[entity] += 1
            track = _TrackState(
                track_id=f"{entity}-{self._entity_counters[entity]:05d}",
                entity=entity,
                bbox=detection.bbox,
                confidence=detection.confidence,
                source_detection_confidence=detection.confidence,
                last_frame_index=detection.frame.frame_index,
            )
            self._active_tracks[entity].append(track)
            visible.append(self._to_observation(track, detection.frame))
        return visible

    def _to_observation(self, track: _TrackState, frame: FrameReference) -> TrackObservation:
        return TrackObservation(
            track_id=track.track_id,
            entity=track.entity,
            frame=frame,
            bbox=track.bbox,
            confidence=track.confidence,
            source_detection_confidence=track.source_detection_confidence,
            metadata={"hits": str(track.hits)},
        )


def run_tracking_pass(
    video_path: Path,
    *,
    config: TrackingRunConfig | None = None,
) -> TrackingRunResult:
    """Run the baseline detector + tracker sweep over a sampled real match video."""

    run_config = config or TrackingRunConfig()
    frame_provider = AVFoundationFrameProvider()
    video = frame_provider.open(video_path)
    detector = TorchvisionCocoDetector(run_config.detector)
    tracker = IoUTracker(run_config.tracker)

    track_frames: list[TrackerFrameOutput] = []
    per_track_frames: dict[str, int] = defaultdict(int)
    per_entity_tracks: dict[str, set[str]] = defaultdict(set)
    sampled_frames = 0

    for sampled_frame in frame_provider.sample_frames(
        sample_fps=run_config.sample_fps,
        start_time_s=run_config.start_time_s,
        max_frames=run_config.max_frames,
    ):
        detections = list(detector.detect((sampled_frame.reference, sampled_frame.image)))
        tracks = list(tracker.update(detections))
        track_frames.append(
            TrackerFrameOutput(
                frame=sampled_frame.reference,
                tracker_name=tracker.name,
                tracks=tracks,
            )
        )
        sampled_frames += 1
        for track in tracks:
            per_track_frames[track.track_id] += 1
            per_entity_tracks[track.entity].add(track.track_id)

    summary = {
        "video_asset_id": video.asset_id,
        "sampled_frames": sampled_frames,
        "sample_fps": run_config.sample_fps,
        "start_time_s": run_config.start_time_s,
        "unique_player_tracks": len(per_entity_tracks.get("player", set())),
        "unique_ball_tracks": len(per_entity_tracks.get("ball", set())),
        "top_tracks": [
            {"track_id": track_id, "visible_frames": count}
            for track_id, count in sorted(
                per_track_frames.items(),
                key=lambda item: (-item[1], item[0]),
            )[:10]
        ],
    }
    return TrackingRunResult(
        video_asset=asdict(video),
        tracker_name=tracker.name,
        detector_name=detector.name,
        sampled_frames=sampled_frames,
        track_frames=track_frames,
        summary=summary,
    )


def write_tracking_run(
    result: TrackingRunResult,
    *,
    output_dir: Path,
) -> dict[str, Path]:
    """Persist detector + tracker outputs as JSON artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "tracking_summary.json"
    frames_path = output_dir / "track_frames.jsonl"

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "video_asset": result.video_asset,
                "tracker_name": result.tracker_name,
                "detector_name": result.detector_name,
                "sampled_frames": result.sampled_frames,
                "summary": result.summary,
            },
            handle,
            indent=2,
        )

    with frames_path.open("w", encoding="utf-8") as handle:
        for frame_output in result.track_frames:
            handle.write(
                json.dumps(
                    {
                        "frame": asdict(frame_output.frame),
                        "tracker_name": frame_output.tracker_name,
                        "tracks": [asdict(track) for track in frame_output.tracks],
                    }
                )
            )
            handle.write("\n")

    return {"summary": summary_path, "track_frames": frames_path}


@contextmanager
def _temporary_insecure_ssl_context() -> Iterator[None]:
    """Allow model bootstrap on machines with incomplete certificate chains.

    The project is local-first for now; this keeps torchvision model download
    practical on development machines where Python's trust store is incomplete.
    """

    original_context = ssl._create_default_https_context
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        yield
    finally:
        ssl._create_default_https_context = original_context


def _bbox_iou(left: BoundingBox, right: BoundingBox) -> float:
    left_x2 = left.x + left.width
    left_y2 = left.y + left.height
    right_x2 = right.x + right.width
    right_y2 = right.y + right.height

    inter_x1 = max(left.x, right.x)
    inter_y1 = max(left.y, right.y)
    inter_x2 = min(left_x2, right_x2)
    inter_y2 = min(left_y2, right_y2)

    inter_width = max(0.0, inter_x2 - inter_x1)
    inter_height = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_width * inter_height
    if inter_area <= 0.0:
        return 0.0

    left_area = left.width * left.height
    right_area = right.width * right.height
    union_area = left_area + right_area - inter_area
    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def _bbox_center_distance(left: BoundingBox, right: BoundingBox) -> float:
    left_cx = left.x + left.width / 2.0
    left_cy = left.y + left.height / 2.0
    right_cx = right.x + right.width / 2.0
    right_cy = right.y + right.height / 2.0
    return float(np.hypot(left_cx - right_cx, left_cy - right_cy))
