# Phase 0 Bot D Memo

## Scope

Design the ball interaction, touch detection, and possession inference architecture for a football clip extraction system centered on one user-selected player.

## Research Signals That Matter

- Rule-based temporal logic remains useful when tracking data is inspectable and labels are scarce. The 2020 event-detection work on spatiotemporal soccer data showed that handcrafted temporal rules can recover possession, passes, shots, and tackles, but performance drops sharply when player/ball tracks jitter or overlap heavily.
- Recent work on ball possessor recognition in soccer video moved toward temporal models over possession likelihoods rather than single-frame proximity. The 2025 paper "Temporally Accurate Events Detection Through Ball Possessor Recognition in Soccer" uses smoothed per-player possession likelihoods and temporal convolution / TDNN style modeling, then derives touch events from controller transitions. The key lesson: sub-second temporal accuracy needs time-context, not nearest-player heuristics.
- Official football laws give clean termination conditions for some clip boundaries: out of play when the ball wholly crosses touchline/goal line, and goal when the whole ball crosses the goal line between the posts and under the bar.

## Event Taxonomy

MVP event labels:

- `controlled_first_touch`
- `dribble_continuation`
- `pass_release`
- `shot_release`
- `interception_recovery`
- `loose_ball_recovery`
- `deflection_touch`
- `contested_tackle_touch`
- `goalkeeper_secure_control`
- `out_of_play`
- `goal_scored`
- `uncertain_controller`

Label policy:

- `touch` means meaningful contact or clear control transition, not mere spatial proximity.
- `dribble_continuation` keeps one possession open when repeated close contacts belong to the same player and the ball remains controllable.
- `deflection_touch` is contact without stable control. Default: start candidate clip only if contact exceeds configurable significance threshold.
- `contested_tackle_touch` marks duel windows where controller is unstable. Keep as explicit state, not forced binary control.

## Three Candidate Architectures

### 1. Rule-Based Temporal Geometry State Machine

Inputs:

- player track boxes or masks
- target-player identity confidence
- ball track
- optional pose keypoints or estimated foot zones
- frame timestamp and scene state

Core features per frame or short window:

- ball-to-left-foot / right-foot / lower-body distance
- ball overlap with player mask expansion
- relative velocity between ball and player
- ball speed change before and after candidate contact
- ball direction change after candidate contact
- time ball remains inside controllable radius
- nearest-opponent distance
- aerial indicator from ball trajectory / size / vertical proxy when available
- target identity confidence and track continuity

States:

- `free_ball`
- `candidate_contact`
- `controlled_by_target`
- `controlled_by_other`
- `contested`
- `dead_ball`
- `uncertain`

Transitions:

- enter `candidate_contact` only when geometry and temporal consistency agree for `N_contact` frames
- promote to `controlled_by_target` only when contact evidence plus ball response plus target identity exceed threshold
- remain in `controlled_by_target` through dribble grace windows and short occlusion gaps
- switch to `controlled_by_other` only after sustained contrary evidence
- switch to `contested` when two players have overlapping control evidence
- end possession on dead-ball, goal, other-controller confirmation, or unresolved loose-ball timeout

Strengths:

- best inspectability
- no annotation dependency to start
- easiest to debug with overlays and confidence plots
- deterministic clip boundaries

Weaknesses:

- brittle for deflections, aerial duels, crowded box play, and low-resolution foot contact
- threshold tuning becomes tedious
- harder to generalize across camera styles without calibration

### 2. Lightweight Learned Classifier

Design:

- derive track-centric temporal features over windows of roughly 0.5-2.0 seconds
- predict:
  - `target_touch_probability`
  - `target_control_probability`
  - `controller_class` in `{target, other, none, contested}`
  - `boundary_event` in `{continue, release, out, goal, uncertain}`

Candidate models:

- gradient-boosted trees on engineered temporal features
- 1D temporal CNN / TCN
- small GRU

Features:

- all state-machine geometry features
- short history and future deltas
- track quality indicators
- optional crop embeddings from player tube and ball crop
- optional pose-derived foot-ball relation

Strengths:

- better at nonlinear combinations than threshold stacks
- improves on noisy edge cases once labels exist
- easier to calibrate than a large opaque model

Weaknesses:

- needs labeled data from Phase 1 first
- vulnerable to domain shift across leagues, broadcast styles, and camera zoom
- less transparent unless feature attribution is logged

### 3. Hybrid

Design:

- state machine proposes candidate contacts, control segments, and boundary events
- lightweight classifier rescoring decides:
  - promote or reject candidate contact
  - resolve `target` vs `other` vs `contested`
  - classify termination cause
- confidence fusion sits above both

Strengths:

- keeps deterministic structure
- reduces threshold brittleness
- lowers data need versus end-to-end learning
- best fit for production iteration

Weaknesses:

- more moving parts
- requires careful interface and calibration discipline

## Recommendation

MVP path: **hybrid architecture with a rule-based temporal geometry state machine as the authoritative controller and a learned classifier deferred until Phase 1 labels exist**.

Concrete MVP implementation choice:

1. Build the full state machine first.
2. Emit rich per-frame features and decision traces.
3. Use those traces to create labels and train a small rescoring model in Phase 4b or Phase 7.

Reason:

- Data is the main bottleneck now, not model capacity.
- Failure analysis is critical for a selected-player product.
- A pure learned controller is too early before the benchmark harness exists.
- A pure rule engine is acceptable for baseline but will plateau on contested or noisy sequences.

## Clip Boundary Rules

Clip start:

- first frame where target control state becomes `controlled_by_target`
- backtrack to earliest frame in the accepted contact window
- apply configurable `pre_roll_ms`

Clip continue:

- maintain possession through repeated dribble touches
- allow short ball-air gaps if same target remains most likely receiver and no other controller is established
- allow short occlusion gaps if target identity and ball continuation remain coherent

Clip end:

- another player becomes controller for `N_other_control` frames
- ball goes out of play
- goal scored
- unresolved loose-ball state exceeds `loose_ball_timeout_ms`
- replay or hard camera cut interrupts inference and no robust continuity remains
- user-configured hard cutoff for uncertainty

Default special rules:

- `deflection_touch` alone does not end prior possession unless another controller stabilizes
- `contested` does not immediately end target clip; use grace window
- set-piece restarts start fresh possessions
- goalkeeper secure hold counts as possession transfer

## Confidence Strategy

Keep confidence decomposed. Do not collapse too early.

Per-frame scores:

- `ball_track_confidence`
- `target_identity_confidence`
- `contact_geometry_confidence`
- `control_state_confidence`
- `boundary_confidence`

Per-clip scores:

- `clip_start_confidence`
- `clip_end_confidence`
- `overall_clip_confidence`
- `review_priority_score`

Fusion rule for MVP:

- weighted rule score with explicit minima on ball quality and identity quality
- mark segments `uncertain` instead of forcing a decision when minima fail

Calibration upgrade:

- fit isotonic or Platt calibration on held-out labeled clips after Phase 1 annotation pipeline exists

## Failure Cases To Design For

- ball hidden under feet in crowded midfield
- target and teammate with similar kit and body shape
- jersey number invisible
- target partly occluded during first touch
- airborne ball between two challengers
- one-touch deflection versus controlled reception
- tackles with instant turnover
- throw-ins, corners, free kicks, and keeper catches
- scoreboard or replay graphics obscuring ball
- camera cuts that break temporal continuity
- low-resolution or motion-blurred ball track

## Benchmark Plan

Primary metrics:

- touch detection precision / recall / F1 at `0.2s`, `0.5s`, and `1.0s` tolerance
- controller classification accuracy per frame
- target-possession interval IoU and F1
- false split rate and false merge rate for clip intervals
- clip usefulness score from human review
- uncertainty coverage: fraction of errors flagged low-confidence

Targeted benchmark slices:

- `deflection`
- `crowded_midfield`
- `air_duel`
- `set_piece`
- `keeper_possession`
- `touchline_out`
- `camera_cut`
- `replay_insert`
- `scoreboard_occlusion`
- `reentry_after_exit`

Required debug artifacts:

- ball-target distance plots
- control-state timeline
- controller transition markers
- overlay videos with foot-zone and ball path
- false-positive and false-negative galleries

## Interfaces

```python
class InteractionFeatures(TypedDict):
    frame_index: int
    timestamp_ms: int
    target_track_id: str | None
    target_identity_confidence: float
    ball_track_id: str | None
    ball_track_confidence: float
    foot_ball_distance_px: float | None
    lower_body_overlap_ratio: float | None
    relative_ball_speed: float | None
    ball_heading_delta_deg: float | None
    nearest_opponent_distance_px: float | None
    aerial_probability: float | None
```

```python
class PossessionDecision(TypedDict):
    frame_index: int
    controller: Literal["target", "other", "none", "contested", "uncertain"]
    event_label: str | None
    contact_confidence: float
    control_confidence: float
    boundary_confidence: float
    reasons: list[str]
```

```python
class PossessionInterval(TypedDict):
    interval_id: str
    start_ms: int
    end_ms: int
    controller: Literal["target"]
    start_reason: str
    end_reason: str
    confidence: float
    review_priority: float
```

## MVP Build Order

1. Implement feature extraction from player track, ball track, and target identity track.
2. Implement deterministic state machine with tunable thresholds and full trace logging.
3. Add dead-ball, goal, and camera-cut termination hooks.
4. Build benchmark slices and debugging outputs.
5. Collect labels from failed or uncertain windows.
6. Train a small temporal rescoring model.
7. Insert rescoring only at transition points first, not as a full controller replacement.

## Later Upgrades

- pose-driven foot contact estimation
- segmentation-assisted foot and ball overlap reasoning
- learned controller transition model over all nearby players
- dedicated set-piece mode
- broadcast replay detector feeding inference mask
- field calibration to convert pixels to metric motion features
- active-learning queue from low-confidence intervals

## Bottom Line

Recommended MVP: **deterministic temporal geometry state machine with explicit `contested` and `uncertain` states, rich feature logging, and thresholds tuned against targeted edge-case slices**.

Recommended upgrade path: **hybrid rescoring model trained on the state-machine outputs plus human corrections, then selective replacement of the most brittle transitions such as deflection, aerial duel, and turnover resolution**.

## Sources

- ByteTrack paper: https://arxiv.org/abs/2110.06864
- BoT-SORT paper: https://arxiv.org/abs/2206.14651
- SAM 2 official repository: https://github.com/facebookresearch/sam2
- Recognizing Events in Spatiotemporal Soccer Data (2020): https://www.mdpi.com/2076-3417/10/22/8046
- Temporally Accurate Events Detection Through Ball Possessor Recognition in Soccer (2025): https://www.scitepress.org/Papers/2025/133177/133177.pdf
- IFAB Law 9, Ball in and out of play: https://www.theifab.com/laws/latest/the-ball-in-and-out-of-play/
- IFAB Law 10, determining the outcome of a match: https://www.theifab.com/laws/latest/determining-the-outcome-of-a-match/
