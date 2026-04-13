# Phase 0 Bot F - Annotation Schema Draft

## Format

Canonical annotation payloads should be JSON for authoring and interchange.
Runtime analytics can materialize Parquet views derived from the same schema.

Top-level object:

```json
{
  "schema_version": "0.1.0",
  "video": {},
  "tracks": [],
  "identity_segments": [],
  "interaction_events": [],
  "possession_intervals": [],
  "clip_references": [],
  "review_audit": []
}
```

## Video

```json
{
  "video_id": "match_001_clip_003",
  "source_uri": "data/samples/...",
  "fps": 25.0,
  "frame_count": 3125,
  "width": 1920,
  "height": 1080,
  "duration_sec": 125.0,
  "broadcast_type": "broadcast",
  "scenario_tags": [
    "crowded_midfield",
    "camera_cut",
    "airborne_cross"
  ]
}
```

## Track

Represents an entity track hypothesis in ground truth or reviewed system output.

```json
{
  "track_id": "gt_player_17",
  "entity_type": "player",
  "team_id": "home",
  "jersey_number": "17",
  "is_goalkeeper": false,
  "target_candidate": true,
  "observations": [
    {
      "frame_index": 102,
      "bbox_xywh": [812, 331, 96, 212],
      "visibility": "visible",
      "occlusion": "none",
      "source": "manual"
    }
  ]
}
```

Ball track example:

```json
{
  "track_id": "gt_ball_1",
  "entity_type": "ball",
  "observations": [
    {
      "frame_index": 102,
      "bbox_xywh": [944, 487, 18, 18],
      "visibility": "visible",
      "airborne": false,
      "source": "manual"
    }
  ]
}
```

## Identity Segment

Defines when a specific visible player track corresponds to the selected player.

```json
{
  "identity_segment_id": "idseg_001",
  "target_player_id": "target_home_17",
  "start_frame": 80,
  "end_frame": 265,
  "resolved_track_id": "gt_player_17",
  "ambiguity": "clear",
  "recovery_context": "post_cut",
  "notes": "target re-enters after short occlusion"
}
```

## Interaction Event

```json
{
  "event_id": "event_012",
  "target_player_id": "target_home_17",
  "event_type": "touch",
  "subtype": "pass",
  "start_frame": 184,
  "end_frame": 188,
  "certainty": "clear",
  "ball_track_id": "gt_ball_1",
  "body_region": "foot",
  "context_tags": [
    "under_pressure",
    "ground_ball"
  ]
}
```

## Possession Interval

```json
{
  "possession_id": "poss_004",
  "target_player_id": "target_home_17",
  "start_frame": 184,
  "end_frame": 241,
  "start_reason": "first_touch",
  "end_reason": "other_player_control",
  "certainty": "probable",
  "event_refs": [
    "event_012",
    "event_013"
  ],
  "context_tags": [
    "open_play"
  ]
}
```

## Clip Reference

Represents the user-facing clip ground truth or reviewed clip decision.

```json
{
  "clip_id": "clip_004",
  "derived_from_possession_id": "poss_004",
  "source_start_frame": 179,
  "source_end_frame": 248,
  "acceptability": "accept_with_minor_trim",
  "preferred_preroll_frames": 5,
  "preferred_postroll_frames": 7,
  "notes": "good clip, end should breathe slightly after pass"
}
```

## Review Audit

```json
{
  "audit_id": "audit_090",
  "actor": "annotator_1",
  "timestamp": "2026-04-13T14:00:00Z",
  "entity": "clip_004",
  "action": "trim_end",
  "old_value": 241,
  "new_value": 248,
  "reason": "receiver control visible after two frames"
}
```

## Enumerations

### Visibility

- `visible`
- `partial`
- `hidden`
- `out_of_frame`

### Occlusion

- `none`
- `player_occlusion`
- `overlay_occlusion`
- `crowd_occlusion`

### Event types

- `touch`
- `dribble_continuation`
- `pass`
- `shot`
- `interception`
- `deflection`
- `tackle_recovery`
- `loose_ball_interaction`

### Possession end reasons

- `other_player_control`
- `out_of_play`
- `goal`
- `foul_or_whistle`
- `unresolved_loose_ball_timeout`
- `replay_break`
- `camera_cut_unresolved`

### Acceptability

- `accept`
- `accept_with_minor_trim`
- `accept_with_major_edit`
- `reject`
