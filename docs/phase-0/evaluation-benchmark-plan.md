# Phase 0 Bot F - Evaluation and Benchmark Plan

## Purpose

This document defines the evaluation strategy for a production-grade football
video analysis system that detects and exports possession/action clips for a
user-selected player. The plan is designed to prevent false confidence from
single-video demos and to force measurable progress at each later phase.

The evaluation stack is split into:

1. annotation schema and benchmark assets
2. automatic metrics
3. targeted weak-point benchmark slices
4. phase gates and pass/fail criteria
5. reporting outputs and regression policy

## Evaluation Principles

- Evaluate the full chain, not only isolated models.
- Prefer inspectable metrics tied to user-visible failures.
- Separate offline benchmark quality from interactive UX quality.
- Track both average performance and hard-case performance.
- Every weak point gets a named benchmark slice.
- Any heuristic or model addition must beat the previous baseline on at least
  one benchmark slice without materially harming the others.

## Benchmark Dataset Composition

The benchmark set should be local-first and versioned by manifest, not by
assumption. Each source video must be referenced through a manifest entry with
 licensing status, resolution, fps, duration, and scenario tags.

### Dataset tiers

#### Tier A - Smoke

- 3 to 5 short clips, 20 to 60 seconds each
- used for e2e and CI smoke runs
- includes at least one:
  - simple dribble and pass sequence
  - crowded midfield sequence
  - touchline/out-of-play sequence

#### Tier B - Development benchmark

- 10 to 20 clips, 30 to 120 seconds each
- broadcast footage from multiple matches and broadcast styles
- mix of:
  - stable and aggressive camera pans
  - wide and medium zoom states
  - day/night lighting variance
  - different pitch color and compression quality
- minimum scenario coverage:
  - open-play dribble
  - one-touch pass
  - contested recovery
  - interception
  - aerial duel / ball in flight
  - set piece
  - goalkeeper distribution or possession
  - ball out of play near touchline
  - goal and post-goal celebration

#### Tier C - Hard cases

- 8 to 12 targeted clips, 15 to 90 seconds each
- each clip is tagged to one primary failure mode
- required slices:
  - occlusion
  - camera cut
  - similar-looking teammates
  - jersey number not visible
  - airborne ball
  - set piece crowding
  - replay insertion
  - scoreboard or lower-third overlap
  - poor resolution / motion blur
  - target leaves frame and re-enters

### Minimum MVP benchmark composition

- 16 to 24 total benchmark clips
- at least 4 full-sequence clips longer than 90 seconds
- at least 6 clips with heavy player density
- at least 4 clips with explicit camera cuts
- at least 3 clips where the selected player is visually similar to a teammate
- at least 3 clips with airborne-ball interactions
- at least 3 set-piece clips
- at least 2 clips with replay interruption

## Annotation Schema Needs

The system must support frame-aligned annotations but store interval-level
 semantics where possible to keep annotation effort tractable.

See `docs/phase-0/annotation-schema.md` for the canonical field definitions.

### Required annotation units

1. `video`
2. `frame_sample`
3. `track`
4. `entity_observation`
5. `identity_segment`
6. `interaction_event`
7. `possession_interval`
8. `clip_reference`
9. `manual_review_audit`

### Required annotation categories

#### Entity annotations

- player boxes per key frame or per frame where feasible
- ball boxes per frame where visible
- visibility flags for player and ball
- occlusion flags
- camera-cut markers
- replay interval markers

#### Identity annotations

- target player identity segment
- confidence label for whether identity is visually unambiguous
- cause-of-loss or cause-of-confusion label when identity breaks

#### Interaction annotations

- touch start frame
- touch end frame if sustained
- interaction label:
  - touch
  - dribble continuation
  - pass
  - shot
  - interception
  - deflection
  - tackle / contested recovery
  - loose-ball interaction
- certainty label:
  - clear
  - probable
  - ambiguous

#### Possession interval annotations

- possession start frame
- possession end frame
- end reason:
  - other_player_control
  - out_of_play
  - goal
  - foul_or_whistle
  - unresolved_loose_ball_timeout
  - replay_break
  - camera_cut_unresolved

#### Clip annotations

- acceptable clip interval for end-user export
- preferred handles if the baseline interval should be extended
- accept / reject reason for candidate clips

## Automatic Metrics

Metrics should be reported at three levels:

1. frame or observation level
2. event or interval level
3. user-facing clip level

Each benchmark run should emit:

- aggregate summary JSON
- per-video JSON
- per-slice JSON
- CSV tables for regression plotting
- debug artifact links

### A. Detection and tracking metrics

#### Player tracking quality

- `HOTA`, `DetA`, `AssA`
- `IDF1`
- `MOTA` as a legacy secondary metric, not the decision-maker
- `SelectedPlayerTrackRecall`
  - fraction of ground-truth target-player frames assigned to any predicted
    target-player hypothesis
- `SelectedPlayerIdentityPrecision`
  - fraction of predicted target-player frames that truly belong to the target
- `IdentityContinuityScore`
  - `1 - ((id_switches + fragmented_gaps) / max(1, gt_identity_segments)))`
- `RecoveryLatencyFrames`
  - median and p95 frames from loss to correct reacquisition

#### Ball tracking quality

- `BallTrackRecallVisible`
  - recall on frames where ball is visible and annotatable
- `BallTrackLocalizationErrorPx`
  - center-distance error normalized by frame diagonal
- `BallTrackContinuityScore`
  - penalizes dropouts and reassignments during continuous visible-ball spans
- `BallVisibilityConditionedRecall`
  - recall split by visible, partially occluded, airborne, scoreboard-overlap

### B. Target-player identity lock metrics

This is a first-class evaluation axis, separate from generic MOT.

- `IdentitySegmentF1`
  - IoU-matched segments comparing predicted target-player ownership segments
    against annotated identity segments
- `IdentitySwitchesPerMinute`
- `IdentityUncertaintyCalibration`
  - expected calibration error across confidence buckets for
    `is_target_player(frame)`
- `WrongLockDurationSec`
  - total time system confidently tracks the wrong player
- `CutRecoverySuccessRate`
  - percent of camera-cut events where the correct player is re-locked within
    the allowed recovery budget

### C. Touch / interaction detection metrics

Because timing matters, evaluate with tolerance windows and event classes.

- `TouchEventPrecision`, `TouchEventRecall`, `TouchEventF1`
  - event counted correct if predicted touch start lands within tolerance of the
    annotated touch start and the matched target player is correct
- Tolerance windows:
  - strict: +/- 3 frames
  - relaxed: +/- 7 frames
- `InteractionClassAccuracy`
  - on matched events only
- `FalseTouchsPerMinute`
- `MissedClearTouchesRate`
  - on annotations labeled `clear`
- `AmbiguousTouchAgreement`
  - measured separately on `ambiguous` events to avoid polluting core signal

### D. Possession interval metrics

Possession is the key segmentation layer for clip generation.

- `PossessionIntervalPrecision`, `Recall`, `F1`
  - interval match based on IoU threshold
- IoU thresholds:
  - report @0.3, @0.5, @0.7
- `BoundaryStartErrorFrames`
  - signed and absolute
- `BoundaryEndErrorFrames`
  - signed and absolute
- `EndReasonAccuracy`
  - exact match on termination label
- `FragmentationRate`
  - number of predicted intervals per ground-truth possession
- `OvermergeRate`
  - number of predicted intervals that cover multiple ground-truth possessions

### E. Clip usefulness metrics

These align directly with product quality.

- `ClipAcceptRate`
  - fraction of auto-generated candidate clips that human reviewers would accept
    with no edits
- `ClipMinorEditRate`
  - accepted after trim adjustment within small handle budget
- `ClipHeavyEditRate`
  - accepted only after merge/split or large timing correction
- `ClipRejectRate`
- `ClipCoverageRecall`
  - percent of ground-truth usable clips represented by at least one candidate
- `MedianTrimAdjustmentSec`
  - median absolute user trim delta to produce an acceptable clip
- `CompilationCoherenceScore`
  - optional reviewer score for merged highlight reel ordering and boundaries

### F. Export correctness metrics

Export correctness is deterministic and must be checked automatically.

- `ExportIntervalMatch`
  - exported media duration and timecodes match requested intervals within
    frame-level tolerance
- `ExportFrameAccuracy`
  - first and last exported frames correspond to expected source frames
- `MetadataCompletenessRate`
  - all required sidecar fields present
- `BatchExportSuccessRate`
- `CompilationRenderSuccessRate`

## Targeted Weak-Point Benchmarks

Every known weak point gets a tagged slice and a metric focus. These slices are
not optional; they are required regressions.

### 1. Occlusion benchmark

Goal:
- measure whether identity lock survives partial and full temporary occlusion

Required tags:
- `occlusion_partial`
- `occlusion_heavy`
- `occlusion_reentry`

Focus metrics:
- `IdentityContinuityScore`
- `RecoveryLatencyFrames`
- `WrongLockDurationSec`

### 2. Camera-cut benchmark

Goal:
- measure identity recovery and possession continuity across broadcast cuts

Required tags:
- `camera_cut_live_to_live`
- `camera_cut_zoom_change`
- `camera_cut_follow_pan_reset`

Focus metrics:
- `CutRecoverySuccessRate`
- `IdentitySwitchesPerMinute`
- `PossessionIntervalF1`

### 3. Similar-looking teammates benchmark

Goal:
- test fused identity scorer under same-team appearance ambiguity

Required tags:
- `similar_kit_same_team`
- `jersey_number_hidden`
- `same_lane_overlap`

Focus metrics:
- `SelectedPlayerIdentityPrecision`
- `WrongLockDurationSec`
- confidence calibration by uncertainty bucket

### 4. Airborne-ball benchmark

Goal:
- reduce false touches from nearest-body heuristics during aerial play

Required tags:
- `airborne_cross`
- `airborne_clearance`
- `bounce_second_ball`

Focus metrics:
- `TouchEventPrecision`
- `MissedClearTouchesRate`
- `EndReasonAccuracy`

### 5. Set-piece benchmark

Goal:
- handle crowded formations and restart transitions

Required tags:
- `corner`
- `free_kick`
- `throw_in`
- `goal_kick`

Focus metrics:
- `BallTrackRecallVisible`
- `TouchEventF1`
- `PossessionIntervalF1`

### 6. Replay benchmark

Goal:
- avoid generating duplicate or misleading clips from replay footage

Required tags:
- `replay_inserted`
- `replay_after_goal`
- `replay_split_screen_or_transition`

Focus metrics:
- replay detection precision/recall once implemented
- interim metric:
  - `ReplayLeakRate`
  - percent of exported candidate clips sourced from replay intervals

### 7. Scoreboard / overlay benchmark

Goal:
- quantify ball loss when overlays obscure key regions

Required tags:
- `overlay_ball_occlusion`
- `overlay_player_occlusion`

Focus metrics:
- `BallVisibilityConditionedRecall`
- `WrongLockDurationSec`

### 8. Poor-quality footage benchmark

Goal:
- stress resilience to motion blur, compression, and low resolution

Required tags:
- `motion_blur`
- `low_resolution`
- `compression_artifacts`

Focus metrics:
- all core metrics split by quality tier

## Annotation and Review Workflow

### Ground-truth policy

- Annotate only benchmark videos, not every development asset.
- Use double review on hard slices:
  - occlusion
  - camera cuts
  - contested possession
  - airborne-ball touches
- Resolve disagreements through adjudication notes.

### Annotation efficiency strategy

- Use sparse full-box annotation plus dense interval labels when possible.
- Densify only around:
  - touch boundaries
  - possession boundaries
  - camera cuts
  - identity failure windows
- Store interpolation provenance to distinguish human labels from propagated
  labels.

## Reporting and Regression Policy

Each benchmark run must produce:

- `artifacts/metrics/<run_id>/summary.json`
- `artifacts/metrics/<run_id>/per_video.json`
- `artifacts/metrics/<run_id>/per_slice.json`
- `artifacts/metrics/<run_id>/regression_table.csv`
- `artifacts/debug_videos/<run_id>/...`
- `artifacts/fn_gallery/<run_id>/...`
- `artifacts/fp_gallery/<run_id>/...`

Required report sections:

1. benchmark inputs
2. model and heuristic configuration
3. aggregate metrics
4. per-slice metrics
5. worst failures with linked artifacts
6. gate result
7. recommended next action

## Phase Gates

These gates are deliberately conservative. They are designed to prevent phase
 advancement based on visually convincing but brittle demos.

### Phase 1 gate - Dataset and evaluation harness

PASS only if:

- annotation schema is frozen at v0
- dataset manifest exists with scenario tags
- at least one repeatable benchmark command runs end-to-end
- metrics output JSON and CSV artifacts automatically
- hard slices exist for:
  - occlusion
  - camera cuts
  - similar-looking teammates
  - airborne ball
  - set pieces
  - replay

FAIL if:

- metrics require manual spreadsheet assembly
- benchmark clips are untagged
- there is no clip-level evaluation path

### Phase 2 gate - Detection and tracking baseline

PASS only if:

- tracking metrics run on Tier B benchmark
- per-video overlays are generated
- at least two tracker configurations are compared
- selected-player continuity is reported separately from general MOT
- failures are explainable through artifacts

FAIL if:

- tracker quality is reported only through generic mAP
- no debug overlay or track timeline exists

### Phase 3 gate - Identity locking

PASS only if:

- identity lock beats tracker-only baseline on hard slices
- wrong-lock duration is materially reduced
- confidence calibration is reported
- camera-cut recovery is benchmarked explicitly

FAIL if:

- identity is evaluated only on average and not on similar-kit/cut slices

### Phase 4 gate - Touch and possession inference

PASS only if:

- touch metrics are reported with timing tolerances
- possession interval F1 and boundary errors are reported
- naive proximity-only baseline is outperformed
- airborne-ball and contested-play slices are included

FAIL if:

- the system claims possession from nearest-center heuristics alone

### Phase 5 gate - Clip generation

PASS only if:

- exported intervals match source frames within tolerance
- preview and final render outputs are both validated
- metadata sidecars are complete

FAIL if:

- exported timing is checked only visually

### Phase 6 gate - Review/edit/export UI

PASS only if:

- user edits are persisted and auditable
- clip acceptance metrics can be recomputed after human edits
- export actions are wired to the real backend

FAIL if:

- UI interactions are mock-only or disconnected from pipeline state

## First Milestones for Phase 1 and Phase 2

### Phase 1 milestone

Build the evaluation harness before model iteration:

- finalize annotation JSON schema
- create dataset manifest format and scenario tags
- add benchmark runner CLI
- add baseline report template
- add dummy evaluator tests using fixture annotations

Definition of done:

- `python -m ... benchmark run --manifest ...` produces metric artifacts on a
  small smoke set

### Phase 2 milestone

Stand up the first reproducible tracking benchmark:

- ingest sample clips
- run player and ball detections
- run two tracker variants
- emit track parquet/json outputs
- compute first tracking and continuity metrics
- render overlay videos and track timelines

Definition of done:

- one command produces detections, tracks, metrics, and debug videos for at
  least one Tier A and one Tier B clip

## Recommended Initial Threshold Policy

For early development, use a dual-threshold policy:

- quality target threshold
- regression guardrail threshold

Example:

- if a new method improves hard-slice identity precision by 8 percent but
  reduces global possession interval F1 by 1 percent, review manually rather
  than auto-adopt
- if replay leak rate increases at all, block merge until explained

The exact numeric gates should be frozen after the first real baseline run in
Phase 1, not guessed in Phase 0.
