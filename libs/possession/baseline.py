"""Baseline possession inference with explicit, inspectable state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Iterable, Literal

from libs.schemas import BallInteraction, BoundingBox, ClipBoundaryRule, PossessionSegment, TrackObservation

PossessionState = Literal["free_ball", "candidate_contact", "controlled_by_target"]


@dataclass(slots=True)
class BaselinePossessionConfig:
    """Config for the initial proximity-driven possession baseline."""

    interaction_radius_scale: float = 0.8
    interaction_radius_px_min: float = 18.0
    lower_body_start_ratio: float = 0.45
    lower_body_margin_px: float = 12.0
    proximity_score_threshold: float = 0.55
    min_contact_frames: int = 2
    control_release_timeout_s: float = 0.6
    max_ball_missing_s: float = 0.45
    min_segment_duration_s: float = 0.2
    dribble_refresh_s: float = 0.75


@dataclass(slots=True)
class FrameDecision:
    """Inspectable per-frame decision output for debugging."""

    frame_index: int
    timestamp_s: float
    state: PossessionState
    has_ball_observation: bool
    proximity_score: float
    close_to_player: bool
    reasons: list[str] = field(default_factory=list)


class BaselinePossessionInferenceEngine:
    """Simple baseline state machine using proximity and temporal smoothing."""

    name = "baseline_proximity_state_machine"

    def __init__(self, config: BaselinePossessionConfig | None = None) -> None:
        self.config = config or BaselinePossessionConfig()
        self.last_trace: list[FrameDecision] = []

    def infer(
        self,
        player_track: Iterable[TrackObservation],
        ball_track: Iterable[TrackObservation],
    ) -> tuple[list[BallInteraction], list[PossessionSegment]]:
        player_observations = sorted(player_track, key=lambda obs: obs.frame.frame_index)
        ball_by_frame = {
            observation.frame.frame_index: observation
            for observation in sorted(ball_track, key=lambda obs: obs.frame.frame_index)
        }

        interactions: list[BallInteraction] = []
        segments: list[PossessionSegment] = []
        self.last_trace = []

        if not player_observations:
            return interactions, segments

        player_track_id = player_observations[0].track_id
        state: PossessionState = "free_ball"
        candidate_start = None
        active_segment_start = None
        segment_interaction_ids: list[str] = []
        close_streak = 0
        last_close = None
        last_ball_seen = None
        last_dribble_timestamp = None
        interaction_index = 0
        segment_index = 0

        for player_observation in player_observations:
            ball_observation = ball_by_frame.get(player_observation.frame.frame_index)
            proximity_score, close_to_player, reasons = _score_proximity(
                player_observation,
                ball_observation,
                self.config,
            )

            if ball_observation is not None:
                last_ball_seen = ball_observation.frame

            if close_to_player:
                close_streak += 1
                if candidate_start is None:
                    candidate_start = player_observation.frame
                last_close = player_observation.frame
            else:
                close_streak = 0
                if state != "controlled_by_target":
                    candidate_start = None

            if state == "free_ball" and close_to_player:
                state = "candidate_contact"
                reasons.append("transition=free_to_candidate")

            if state == "candidate_contact":
                if close_to_player and close_streak >= self.config.min_contact_frames:
                    state = "controlled_by_target"
                    active_segment_start = candidate_start or player_observation.frame
                    interaction_index += 1
                    interaction = _make_interaction(
                        interaction_id=f"{player_track_id}:touch:{interaction_index}",
                        player_track_id=player_track_id,
                        frame=active_segment_start,
                        label="touch",
                        confidence=_interaction_confidence(proximity_score, close_streak, self.config),
                        reasons=reasons + [f"close_streak={close_streak}"],
                    )
                    interactions.append(interaction)
                    segment_interaction_ids = [interaction.interaction_id]
                    last_dribble_timestamp = player_observation.frame.timestamp_s
                    reasons.append("transition=candidate_to_controlled")
                elif not close_to_player:
                    state = "free_ball"
                    reasons.append("transition=candidate_to_free")

            elif state == "controlled_by_target":
                if close_to_player:
                    if (
                        last_dribble_timestamp is not None
                        and player_observation.frame.timestamp_s - last_dribble_timestamp
                        >= self.config.dribble_refresh_s
                    ):
                        interaction_index += 1
                        interaction = _make_interaction(
                            interaction_id=f"{player_track_id}:dribble:{interaction_index}",
                            player_track_id=player_track_id,
                            frame=player_observation.frame,
                            label="dribble",
                            confidence=_interaction_confidence(
                                proximity_score,
                                self.config.min_contact_frames,
                                self.config,
                            ),
                            reasons=reasons + ["dribble_refresh=true"],
                        )
                        interactions.append(interaction)
                        segment_interaction_ids.append(interaction.interaction_id)
                        last_dribble_timestamp = player_observation.frame.timestamp_s
                else:
                    timed_out = (
                        last_close is not None
                        and player_observation.frame.timestamp_s - last_close.timestamp_s
                        >= self.config.control_release_timeout_s
                    )
                    ball_missing_timed_out = (
                        ball_observation is None
                        and last_ball_seen is not None
                        and player_observation.frame.timestamp_s - last_ball_seen.timestamp_s
                        >= self.config.max_ball_missing_s
                    )
                    if timed_out or ball_missing_timed_out:
                        end_frame = last_close or player_observation.frame
                        segment = _make_segment(
                            segment_id=f"{player_track_id}:segment:{segment_index}",
                            player_track_id=player_track_id,
                            start_time_s=active_segment_start.timestamp_s
                            if active_segment_start is not None
                            else end_frame.timestamp_s,
                            end_time_s=end_frame.timestamp_s,
                            confidence=_segment_confidence(
                                segment_interaction_ids,
                                interactions,
                            ),
                            end_reason=(
                                "ball_track_missing_timeout"
                                if ball_missing_timed_out
                                else "ball_proximity_timeout"
                            ),
                            interaction_ids=segment_interaction_ids,
                            min_duration_s=self.config.min_segment_duration_s,
                        )
                        if segment is not None:
                            segments.append(segment)
                            segment_index += 1
                        state = "free_ball"
                        candidate_start = None
                        active_segment_start = None
                        segment_interaction_ids = []
                        last_dribble_timestamp = None
                        reasons.append("transition=controlled_to_free")

            self.last_trace.append(
                FrameDecision(
                    frame_index=player_observation.frame.frame_index,
                    timestamp_s=player_observation.frame.timestamp_s,
                    state=state,
                    has_ball_observation=ball_observation is not None,
                    proximity_score=proximity_score,
                    close_to_player=close_to_player,
                    reasons=reasons,
                )
            )

        if state == "controlled_by_target" and last_close is not None:
            segment = _make_segment(
                segment_id=f"{player_track_id}:segment:{segment_index}",
                player_track_id=player_track_id,
                start_time_s=active_segment_start.timestamp_s
                if active_segment_start is not None
                else last_close.timestamp_s,
                end_time_s=last_close.timestamp_s,
                confidence=_segment_confidence(segment_interaction_ids, interactions),
                end_reason="end_of_track",
                interaction_ids=segment_interaction_ids,
                min_duration_s=self.config.min_segment_duration_s,
            )
            if segment is not None:
                segments.append(segment)

        return interactions, segments


class RuleBasedClipBoundaryDecider:
    """Apply simple pre-roll and post-roll clip handles to possession segments."""

    name = "rule_based_clip_boundary_decider"

    def apply_rules(
        self,
        segments: Iterable[PossessionSegment],
        rules: ClipBoundaryRule,
    ) -> list[PossessionSegment]:
        adjusted_segments: list[PossessionSegment] = []
        for segment in segments:
            adjusted_segments.append(
                PossessionSegment(
                    segment_id=segment.segment_id,
                    player_track_id=segment.player_track_id,
                    start_time_s=max(0.0, segment.start_time_s - rules.pre_roll_s),
                    end_time_s=max(
                        max(0.0, segment.start_time_s - rules.pre_roll_s),
                        segment.end_time_s + rules.post_roll_s,
                    ),
                    confidence=segment.confidence,
                    end_reason=f"{segment.end_reason}+handles",
                    interaction_ids=list(segment.interaction_ids),
                )
            )
        return adjusted_segments


def _make_interaction(
    interaction_id: str,
    player_track_id: str,
    frame,
    label,
    confidence: float,
    reasons: list[str],
) -> BallInteraction:
    return BallInteraction(
        interaction_id=interaction_id,
        player_track_id=player_track_id,
        frame=frame,
        label=label,
        confidence=confidence,
        reasons=reasons,
    )


def _make_segment(
    segment_id: str,
    player_track_id: str,
    start_time_s: float,
    end_time_s: float,
    confidence: float,
    end_reason: str,
    interaction_ids: list[str],
    min_duration_s: float,
) -> PossessionSegment | None:
    if end_time_s < start_time_s:
        return None
    if end_time_s - start_time_s < min_duration_s and not interaction_ids:
        return None
    return PossessionSegment(
        segment_id=segment_id,
        player_track_id=player_track_id,
        start_time_s=start_time_s,
        end_time_s=end_time_s,
        confidence=confidence,
        end_reason=end_reason,
        interaction_ids=list(interaction_ids),
    )


def _interaction_confidence(
    proximity_score: float,
    close_streak: int,
    config: BaselinePossessionConfig,
) -> float:
    streak_score = min(1.0, close_streak / max(1, config.min_contact_frames))
    return min(0.99, 0.45 + (0.35 * proximity_score) + (0.2 * streak_score))


def _segment_confidence(
    interaction_ids: list[str],
    interactions: list[BallInteraction],
) -> float:
    relevant = [item.confidence for item in interactions if item.interaction_id in interaction_ids]
    if not relevant:
        return 0.0
    return round(sum(relevant) / len(relevant), 4)


def _score_proximity(
    player_observation: TrackObservation,
    ball_observation: TrackObservation | None,
    config: BaselinePossessionConfig,
) -> tuple[float, bool, list[str]]:
    reasons: list[str] = []
    if ball_observation is None:
        return 0.0, False, ["ball_missing=true"]

    player_box = player_observation.bbox
    ball_box = ball_observation.bbox
    foot_x = player_box.x + (player_box.width / 2.0)
    foot_y = player_box.y + player_box.height
    ball_x, ball_y = _bbox_center(ball_box)
    distance_px = hypot(ball_x - foot_x, ball_y - foot_y)
    interaction_radius = max(
        config.interaction_radius_px_min,
        max(player_box.width, player_box.height) * config.interaction_radius_scale,
    )
    distance_score = max(0.0, 1.0 - (distance_px / interaction_radius))
    inside_lower_body = _inside_lower_body(player_box, ball_box, config)
    proximity_score = min(1.0, distance_score + (0.25 if inside_lower_body else 0.0))
    close_to_player = proximity_score >= config.proximity_score_threshold

    reasons.extend(
        [
            f"distance_px={distance_px:.2f}",
            f"interaction_radius_px={interaction_radius:.2f}",
            f"distance_score={distance_score:.3f}",
            f"inside_lower_body={str(inside_lower_body).lower()}",
            f"proximity_score={proximity_score:.3f}",
        ]
    )
    return proximity_score, close_to_player, reasons


def _bbox_center(box: BoundingBox) -> tuple[float, float]:
    return box.x + (box.width / 2.0), box.y + (box.height / 2.0)


def _inside_lower_body(
    player_box: BoundingBox,
    ball_box: BoundingBox,
    config: BaselinePossessionConfig,
) -> bool:
    ball_x, ball_y = _bbox_center(ball_box)
    lower_body_top = player_box.y + (player_box.height * config.lower_body_start_ratio)
    left = player_box.x - config.lower_body_margin_px
    right = player_box.x + player_box.width + config.lower_body_margin_px
    bottom = player_box.y + player_box.height + config.lower_body_margin_px
    return left <= ball_x <= right and lower_body_top <= ball_y <= bottom
