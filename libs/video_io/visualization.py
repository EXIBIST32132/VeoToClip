"""Baseline debug overlay rendering for football video pipeline artifacts.

These helpers are intentionally stateless so detection/tracking, identity,
and possession workers can compose them without sharing runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import cv2
import numpy as np

from libs.schemas import BallInteraction, BoundingBox, FrameReference, TrackObservation


Color = tuple[int, int, int]
DEFAULT_FONT = cv2.FONT_HERSHEY_SIMPLEX

PLAYER_COLOR: Color = (64, 196, 255)
SELECTED_PLAYER_COLOR: Color = (0, 255, 0)
BALL_COLOR: Color = (0, 165, 255)
INTERACTION_ZONE_COLOR: Color = (255, 80, 80)
TEXT_BG_COLOR: Color = (18, 18, 18)
FRAME_ACCENT_COLOR: Color = (255, 255, 255)


@dataclass(slots=True)
class OverlayStyle:
    """Styling knobs for baseline overlays."""

    player_color: Color = PLAYER_COLOR
    selected_player_color: Color = SELECTED_PLAYER_COLOR
    ball_color: Color = BALL_COLOR
    interaction_zone_color: Color = INTERACTION_ZONE_COLOR
    label_text_color: Color = (255, 255, 255)
    label_background_color: Color = TEXT_BG_COLOR
    frame_accent_color: Color = FRAME_ACCENT_COLOR
    track_thickness: int = 2
    selected_track_thickness: int = 3
    interaction_zone_thickness: int = 2
    label_scale: float = 0.5
    label_thickness: int = 1
    interaction_zone_radius_px: int = 42
    history_length: int = 12


@dataclass(slots=True)
class FrameOverlayContext:
    """Context inputs needed to render one debug frame."""

    frame_ref: FrameReference | None = None
    selected_track_id: str | None = None
    selected_identity_confidence: float | None = None
    track_confidences: Mapping[str, float] = field(default_factory=dict)
    track_histories: Mapping[str, Sequence[tuple[int, int]]] = field(default_factory=dict)
    interaction_track_ids: frozenset[str] = frozenset()
    possession_state: str | None = None
    interaction_zone_centers: Mapping[str, tuple[int, int]] = field(default_factory=dict)
    interaction_zone_radius_px: int | None = None


def ensure_color_frame(frame: np.ndarray) -> np.ndarray:
    """Normalize a frame into uint8 BGR for OpenCV drawing."""

    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected a grayscale or BGR image frame.")

    if frame.dtype == np.uint8:
        return frame.copy()

    clipped = np.clip(frame, 0, 255)
    return clipped.astype(np.uint8, copy=False).copy()


def compute_box_anchor(bbox: BoundingBox) -> tuple[int, int]:
    """Return the center point of the bounding box."""

    return int(round(bbox.x + bbox.width / 2.0)), int(round(bbox.y + bbox.height / 2.0))


def compute_interaction_zone(
    player_bbox: BoundingBox,
    ball_bbox: BoundingBox | None = None,
    radius_px: int = 42,
) -> tuple[tuple[int, int], int]:
    """Estimate the ball interaction zone near the player's feet.

    The baseline zone is centered near the lower body. When the ball is known,
    bias the zone toward the ball to make contact candidates easier to inspect.
    """

    base_center_x = player_bbox.x + (player_bbox.width * 0.5)
    base_center_y = player_bbox.y + (player_bbox.height * 0.88)

    if ball_bbox is not None:
        ball_center_x = ball_bbox.x + (ball_bbox.width * 0.5)
        ball_center_y = ball_bbox.y + (ball_bbox.height * 0.5)
        base_center_x = (base_center_x * 0.7) + (ball_center_x * 0.3)
        base_center_y = (base_center_y * 0.7) + (ball_center_y * 0.3)

    return (int(round(base_center_x)), int(round(base_center_y))), int(radius_px)


def draw_track_histories(
    canvas: np.ndarray,
    track_histories: Mapping[str, Sequence[tuple[int, int]]],
    *,
    selected_track_id: str | None = None,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Draw motion trails for recent track history."""

    resolved_style = style or OverlayStyle()
    for track_id, history in track_histories.items():
        if len(history) < 2:
            continue
        points = history[-resolved_style.history_length :]
        color = (
            resolved_style.selected_player_color
            if track_id == selected_track_id
            else resolved_style.player_color
        )
        for start, end in zip(points, points[1:]):
            cv2.line(canvas, start, end, color, 1, lineType=cv2.LINE_AA)
    return canvas


def draw_tracks(
    canvas: np.ndarray,
    tracks: Iterable[TrackObservation],
    *,
    selected_track_id: str | None = None,
    track_confidences: Mapping[str, float] | None = None,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Draw player and ball bounding boxes with labels."""

    resolved_style = style or OverlayStyle()
    confidence_lookup = track_confidences or {}

    for track in tracks:
        is_selected = track.track_id == selected_track_id
        is_ball = track.entity == "ball"

        color = resolved_style.player_color
        thickness = resolved_style.track_thickness
        if is_selected:
            color = resolved_style.selected_player_color
            thickness = resolved_style.selected_track_thickness
        elif is_ball:
            color = resolved_style.ball_color

        top_left = (int(round(track.bbox.x)), int(round(track.bbox.y)))
        bottom_right = (
            int(round(track.bbox.x + track.bbox.width)),
            int(round(track.bbox.y + track.bbox.height)),
        )
        cv2.rectangle(canvas, top_left, bottom_right, color, thickness, lineType=cv2.LINE_AA)

        label_bits = [track.entity, track.track_id]
        if track.track_id in confidence_lookup:
            label_bits.append(f"{confidence_lookup[track.track_id]:.2f}")
        else:
            label_bits.append(f"{track.confidence:.2f}")
        label = " | ".join(label_bits)
        _draw_label(
            canvas,
            label,
            origin=(top_left[0], max(18, top_left[1] - 6)),
            background_color=color,
            text_color=resolved_style.label_text_color,
            scale=resolved_style.label_scale,
            thickness=resolved_style.label_thickness,
        )
    return canvas


def draw_interaction_zones(
    canvas: np.ndarray,
    player_tracks: Iterable[TrackObservation],
    *,
    ball_track: TrackObservation | None = None,
    active_track_ids: frozenset[str] | None = None,
    zone_centers: Mapping[str, tuple[int, int]] | None = None,
    radius_px: int | None = None,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Draw candidate interaction zones around tracked players."""

    resolved_style = style or OverlayStyle()
    resolved_radius = radius_px or resolved_style.interaction_zone_radius_px
    active_ids = active_track_ids or frozenset()
    center_lookup = zone_centers or {}
    ball_bbox = ball_track.bbox if ball_track is not None else None

    for track in player_tracks:
        if track.entity != "player":
            continue
        center = center_lookup.get(track.track_id)
        if center is None:
            center, _ = compute_interaction_zone(
                track.bbox,
                ball_bbox=ball_bbox,
                radius_px=resolved_radius,
            )
        is_active = track.track_id in active_ids
        zone_color = (
            resolved_style.selected_player_color if is_active else resolved_style.interaction_zone_color
        )
        zone_thickness = (
            resolved_style.selected_track_thickness
            if is_active
            else resolved_style.interaction_zone_thickness
        )
        cv2.circle(canvas, center, resolved_radius, zone_color, zone_thickness, lineType=cv2.LINE_AA)
    return canvas


def draw_interactions(
    canvas: np.ndarray,
    interactions: Iterable[BallInteraction],
    tracks: Mapping[str, TrackObservation],
    *,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Mark active interactions at the owning player's location."""

    resolved_style = style or OverlayStyle()
    for interaction in interactions:
        track = tracks.get(interaction.player_track_id)
        if track is None:
            continue
        center, _ = compute_interaction_zone(track.bbox)
        cv2.circle(canvas, center, 8, resolved_style.selected_player_color, -1, lineType=cv2.LINE_AA)
        _draw_label(
            canvas,
            f"{interaction.label}:{interaction.confidence:.2f}",
            origin=(center[0] + 10, center[1] - 6),
            background_color=resolved_style.selected_player_color,
            text_color=resolved_style.label_text_color,
            scale=resolved_style.label_scale,
            thickness=resolved_style.label_thickness,
        )
    return canvas


def annotate_frame_header(
    canvas: np.ndarray,
    *,
    frame_ref: FrameReference | None = None,
    selected_track_id: str | None = None,
    identity_confidence: float | None = None,
    possession_state: str | None = None,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Draw a compact header with frame and pipeline context."""

    resolved_style = style or OverlayStyle()
    status_parts: list[str] = []
    if frame_ref is not None:
        status_parts.append(f"f={frame_ref.frame_index}")
        status_parts.append(f"t={frame_ref.timestamp_s:.2f}s")
    if selected_track_id is not None:
        status_parts.append(f"selected={selected_track_id}")
    if identity_confidence is not None:
        status_parts.append(f"id_conf={identity_confidence:.2f}")
    if possession_state is not None:
        status_parts.append(f"state={possession_state}")

    if not status_parts:
        return canvas

    _draw_label(
        canvas,
        "  ".join(status_parts),
        origin=(12, 22),
        background_color=resolved_style.label_background_color,
        text_color=resolved_style.frame_accent_color,
        scale=0.55,
        thickness=1,
    )
    return canvas


def render_debug_frame(
    frame: np.ndarray,
    tracks: Iterable[TrackObservation],
    *,
    context: FrameOverlayContext | None = None,
    interactions: Iterable[BallInteraction] | None = None,
    style: OverlayStyle | None = None,
) -> np.ndarray:
    """Compose all baseline overlays for a single frame."""

    resolved_style = style or OverlayStyle()
    resolved_context = context or FrameOverlayContext()
    canvas = ensure_color_frame(frame)
    tracks_list = list(tracks)
    track_lookup = {track.track_id: track for track in tracks_list}
    ball_track = next((track for track in tracks_list if track.entity == "ball"), None)

    draw_track_histories(
        canvas,
        resolved_context.track_histories,
        selected_track_id=resolved_context.selected_track_id,
        style=resolved_style,
    )
    draw_tracks(
        canvas,
        tracks_list,
        selected_track_id=resolved_context.selected_track_id,
        track_confidences=resolved_context.track_confidences,
        style=resolved_style,
    )
    draw_interaction_zones(
        canvas,
        tracks_list,
        ball_track=ball_track,
        active_track_ids=resolved_context.interaction_track_ids,
        zone_centers=resolved_context.interaction_zone_centers,
        radius_px=resolved_context.interaction_zone_radius_px,
        style=resolved_style,
    )
    if interactions is not None:
        draw_interactions(canvas, interactions, track_lookup, style=resolved_style)
    annotate_frame_header(
        canvas,
        frame_ref=resolved_context.frame_ref,
        selected_track_id=resolved_context.selected_track_id,
        identity_confidence=resolved_context.selected_identity_confidence,
        possession_state=resolved_context.possession_state,
        style=resolved_style,
    )
    return canvas


def write_overlay_video(
    output_path: str | Path,
    frames: Iterable[np.ndarray],
    *,
    frame_rate: float,
    codec: str = "mp4v",
) -> Path:
    """Write a sequence of overlay frames to disk."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    iterator = iter(frames)
    try:
        first_frame = next(iterator)
    except StopIteration as exc:
        raise ValueError("At least one frame is required to write an overlay video.") from exc

    first_canvas = ensure_color_frame(first_frame)
    height, width = first_canvas.shape[:2]
    writer = cv2.VideoWriter(
        str(output),
        cv2.VideoWriter_fourcc(*codec),
        frame_rate,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer for {output}.")

    try:
        writer.write(first_canvas)
        for frame in iterator:
            canvas = ensure_color_frame(frame)
            if canvas.shape[:2] != (height, width):
                raise ValueError("All frames must have the same dimensions.")
            writer.write(canvas)
    finally:
        writer.release()

    return output


def _draw_label(
    canvas: np.ndarray,
    text: str,
    *,
    origin: tuple[int, int],
    background_color: Color,
    text_color: Color,
    scale: float,
    thickness: int,
) -> None:
    (text_width, text_height), baseline = cv2.getTextSize(text, DEFAULT_FONT, scale, thickness)
    x, y = origin
    top_left = (x - 4, max(0, y - text_height - baseline - 4))
    bottom_right = (x + text_width + 4, y + baseline + 2)
    cv2.rectangle(canvas, top_left, bottom_right, background_color, -1, lineType=cv2.LINE_AA)
    cv2.putText(
        canvas,
        text,
        (x, y),
        DEFAULT_FONT,
        scale,
        text_color,
        thickness,
        lineType=cv2.LINE_AA,
    )
