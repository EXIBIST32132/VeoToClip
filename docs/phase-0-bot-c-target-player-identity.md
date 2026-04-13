# Phase 0 Bot C: Target-Player Identification Architecture Memo

## Recommendation

Use a **fused identity scorer over short tracklets**, not tracker IDs alone and not jersey OCR alone.

Default stack:

1. **Detector + MOT baseline**
   - `BoT-SORT-ReID` as the primary player tracker for baseline experiments.
   - `ByteTrack` retained as the simpler fallback baseline.
2. **Identity fusion layer**
   - Scores every visible player track candidate against the selected player using:
     - tracker continuity
     - appearance embedding similarity
     - team-color compatibility
     - motion continuity
     - optional jersey OCR evidence
     - segmentation-refined crop quality / overlap evidence
3. **Recovery layer**
   - Reacquires identity after occlusion, exits, and cuts by searching candidate tracks over a bounded time window.
4. **Human override**
   - When confidence drops below threshold, surface alternates in the UI instead of silently committing.

This is the most production-viable choice because football broadcast footage has frequent occlusion, same-team lookalikes, camera motion, and many frames where jersey digits are unreadable. The architecture needs multiple weak cues that fail differently rather than one "best" cue.

## Alternatives Compared

### A. Tracker-only identity locking

Definition:

- user clicks a player
- selected MOT track ID becomes the target player
- identity follows that ID until it breaks

Pros:

- simplest implementation
- low latency
- good on clean, continuous views

Cons:

- brittle to occlusion, crossing players, and camera cuts
- tracker ID switches become target-player switches
- no principled recovery after loss

Decision:

- keep only as the control baseline, not the production default

### B. Tracker + global appearance ReID

Definition:

- track with MOT
- stitch interrupted tracklets using appearance embeddings from player crops

Pros:

- better than tracker-only on re-entry and moderate occlusion
- well aligned with `BoT-SORT` design, which explicitly combines motion and appearance with camera-motion compensation

Cons:

- same-team players often have near-identical kits
- broadcast scale changes and blur degrade embeddings
- appearance alone struggles when the back/front view changes

Decision:

- necessary but insufficient on its own

### C. Fused scorer with sparse high-value cues

Definition:

- combine MOT continuity, appearance, team-color, motion, optional jersey OCR, and segmentation refinement in a calibrated scorer

Pros:

- degrades gracefully when one cue disappears
- supports explicit uncertainty states
- makes recovery explainable and inspectable
- best fit for broadcast football, where evidence is intermittent

Cons:

- more engineering complexity
- requires calibration and benchmark-driven weighting

Decision:

- **chosen architecture**

### D. Segmentation-first / mask-propagation-first identity

Definition:

- initialize the player with a point/box/mask and propagate the mask through the match

Pros:

- very strong for precise spatial support in short sequences
- helpful when nearby players overlap heavily

Cons:

- too expensive and drift-prone as the primary full-match identity mechanism
- weak across long gaps and hard cuts without a broader retrieval layer

Decision:

- use as a **refinement and recovery tool**, not the primary identity engine

## Why BoT-SORT-ReID First, ByteTrack Second

`ByteTrack` is a strong baseline because it recovers low-score detections and reduces fragmentation by associating nearly every detection box, including low-confidence boxes that often appear under occlusion. That makes it valuable as a robust baseline for football crowding. `BoT-SORT` extends the tracking layer with appearance cues plus camera-motion compensation, which is closer to what broadcast football needs when the camera pans and players cross. For Bot C, that makes `BoT-SORT-ReID` the better primary baseline to benchmark first, with `ByteTrack` kept as the simpler ablation and fallback.

## Fused Identity Scorer

### Inputs

For each candidate track at frame `t` or segment `s`:

- `track_id`
- current and recent boxes
- detector confidence history
- tracker association metadata
- appearance embeddings from masked and unmasked crops
- team-color descriptor
- motion state
- OCR jersey evidence when available
- segmentation overlap / mask quality features

### Cue design

1. **Tracker continuity**
   - strongest cue while the target remains on one stable track
   - includes track age, missed-frame count, recent association cost, and ID-switch indicators

2. **Appearance embeddings**
   - compute on torso/full-player crops
   - maintain a target identity memory bank with multiple prototypes:
     - front view
     - back view
     - side view
     - near / medium / far scale
   - use segmentation-masked crops when overlap is high

3. **Team color**
   - coarse but cheap discriminator
   - compute dominant upper-body / short-color descriptors in normalized color space
   - mainly used to reject impossible cross-team matches and downweight ambiguous same-team matches

4. **Motion continuity**
   - predict position and velocity in image coordinates and optionally pitch coordinates later
   - useful through brief occlusion and frame-edge exits
   - weaker after hard cuts

5. **Jersey OCR**
   - high precision, low recall
   - treat as **sparse positive evidence**
   - do not treat missing OCR as negative evidence
   - use orientation-aware keyframe selection before OCR, since jersey digits are unreadable in most frames

6. **Segmentation refinement**
   - invoke on demand around:
     - tight player crossings
     - partial overlap
     - ambiguous click initialization
     - recovery windows after loss
   - outputs better crops, overlap estimates, and foot/body support for downstream possession logic

### Scoring model

Use a calibrated segment-level score, not raw per-frame argmax:

```text
identity_logit =
  w_track * track_continuity +
  w_app * appearance_similarity +
  w_team * team_color_compatibility +
  w_motion * motion_consistency +
  w_ocr * jersey_evidence +
  w_seg * segmentation_quality +
  bias
```

Implementation guidance:

- start with a weighted linear model or gradient-boosted ranker on engineered features
- aggregate over a short temporal window, e.g. `0.5-2.0s`
- calibrate outputs to probabilities on the benchmark split
- store per-cue contributions for UI explainability

Do not start with an end-to-end deep identity model. The project needs inspectability and fast iteration over weak cues.

## Identity State Machine

Three runtime states are sufficient for MVP:

1. `LOCKED`
   - one candidate clearly dominant
   - score above `lock_threshold`
   - margin over second-best candidate above `margin_threshold`

2. `UNCERTAIN`
   - target likely visible but ambiguous
   - keep provisional assignment
   - surface warning and alternates

3. `LOST`
   - no candidate above `recover_threshold`
   - stop hard claims about target identity
   - open bounded recovery search

Transition rules:

- `LOCKED -> UNCERTAIN` when score drops, overlap rises, or alternate margin collapses
- `UNCERTAIN -> LOST` after sustained ambiguity window
- `LOST -> LOCKED` only after recovery score and persistence checks pass across multiple frames

## Failure Recovery

### 1. Short occlusion recovery

Use tracker continuity + motion prediction first.

- if the same track resumes within a short gap, preserve identity unless a stronger conflicting cue appears

### 2. Long occlusion / frame exit recovery

Search over candidate tracklets in a bounded window:

- compare appearance prototype similarity
- enforce team-color compatibility
- apply spatial-motion priors
- seek sparse jersey OCR confirmation

### 3. Camera-cut recovery

Treat hard cuts as a different mode:

- reset motion prior aggressively
- rely more on appearance, team-color, and OCR
- if confidence remains low, request user confirmation instead of hallucinating continuity

### 4. Ambiguous same-team cluster recovery

Run segmentation refinement and candidate reranking when:

- players overlap
- boxes are nearly coincident
- embeddings are too similar

### 5. Human correction integration

Manual user reassignment should:

- create a new labeled identity anchor
- update the prototype memory bank
- mark surrounding interval as supervised truth for later evaluation

## Interfaces

### `TargetIdentityAnchor`

```python
class TargetIdentityAnchor(TypedDict):
    project_id: str
    source_frame: int
    init_mode: Literal["click", "box", "mask", "track_select"]
    box_xyxy: tuple[float, float, float, float] | None
    mask_rle: str | None
    team_hint: str | None
    jersey_hint: str | None
    color_hint: str | None
```

### `TrackObservation`

```python
class TrackObservation(TypedDict):
    frame_index: int
    track_id: str
    bbox_xyxy: tuple[float, float, float, float]
    detection_confidence: float
    tracker_confidence: float | None
    crop_uri: str
    mask_uri: str | None
```

### `IdentityCueVector`

```python
class IdentityCueVector(TypedDict):
    track_continuity: float
    appearance_similarity: float
    team_color_compatibility: float
    motion_consistency: float
    jersey_ocr_match: float | None
    segmentation_quality: float | None
    occlusion_ratio: float | None
```

### `IdentityDecision`

```python
class IdentityDecision(TypedDict):
    frame_index: int
    selected_track_id: str | None
    state: Literal["LOCKED", "UNCERTAIN", "LOST"]
    confidence: float
    margin_to_runner_up: float | None
    cue_vector: IdentityCueVector
    alternates: list[dict]
    explanation: list[str]
```

### `RecoveryRequest`

```python
class RecoveryRequest(TypedDict):
    lost_start_frame: int
    search_end_frame: int
    last_known_track_id: str | None
    last_known_box_xyxy: tuple[float, float, float, float] | None
    reason: Literal["occlusion", "exit", "cut", "ambiguous_crossing"]
```

## Confidence Logic

Confidence must represent **probability that the currently assigned track is the user-selected player**, not generic tracker confidence.

Rules:

- calibrate on held-out football footage using isotonic regression or Platt scaling
- maintain both:
  - `assignment_confidence`
  - `visibility_confidence`
- high assignment confidence with low visibility confidence should still warn the UI
- expose confidence at:
  - frame level
  - segment level
  - clip level summary

Recommended thresholds for initial tuning:

- `lock_threshold`: conservative
- `recover_threshold`: higher than lock threshold after a loss event
- `manual_review_threshold`: below this, candidate clips touching the interval are flagged by default

Exact numeric values should be chosen only after Phase 1 benchmark calibration.

## Explainability Requirements

Every locked or recovered interval should be inspectable with:

- selected track overlay
- top-2 alternate candidates
- cue contribution bars
- OCR evidence frames when present
- segmentation snapshots when refinement was invoked
- timeline of `LOCKED/UNCERTAIN/LOST` states

This is necessary for debugging and for human correction in Phase 6.

## Weak Points and Targeted Benchmarks

Each weak point gets a dedicated benchmark slice in Phase 1.

1. **Same-team ambiguity**
   - scenario: two teammates with similar build and kit cross paths
   - metric: ID continuity F1 through overlap window

2. **Jersey unavailable**
   - scenario: front-facing player, blur, or distant broadcast scale
   - metric: identity accuracy with OCR feature ablated

3. **Occlusion duration sweep**
   - scenario: target hidden for `0.5s`, `1s`, `2s`, `4s`
   - metric: correct reacquisition rate and false reacquisition rate

4. **Camera-cut recovery**
   - scenario: broadcast cut to a new angle or replay return
   - metric: post-cut target reacquisition accuracy within first `N` frames

5. **Exit and re-entry**
   - scenario: player leaves frame at edge and re-enters later
   - metric: tracklet stitching precision/recall

6. **Crowded set-piece cluster**
   - scenario: corner, free kick, goalmouth crowd
   - metric: ambiguity duration and manual-review rate

7. **Low-resolution / motion blur**
   - scenario: compression, zoomed-out play, rapid pan
   - metric: cue degradation analysis by factor

8. **Partial visibility**
   - scenario: only torso or lower body visible
   - metric: identity accuracy by visible-body fraction bin

9. **Initialization ambiguity**
   - scenario: user click near overlapping players
   - metric: successful initialization rate with and without segmentation refinement

10. **Lookalike alternates**
   - scenario: similar teammate and similar motion path
   - metric: confidence calibration error and runner-up margin distribution

## MVP Build Order

1. Baseline with `ByteTrack` and tracker-only selection.
2. Add `BoT-SORT-ReID` comparison.
3. Add fused scorer with track + appearance + team color + motion.
4. Add sparse jersey OCR on keyframes.
5. Add segmentation refinement for ambiguous windows.
6. Calibrate confidence and wire explainability outputs.

This order keeps the system benchmarkable at each step and makes it obvious whether each cue actually improves identity continuity.

## Bottom Line

For production-grade football clip extraction, the target-player identification system should be a **calibrated, explainable, fused identity layer over MOT tracklets**. `BoT-SORT-ReID` is the best first baseline because it already combines motion and appearance and handles camera motion better than tracker-only baselines; `ByteTrack` remains the ablation and fallback. Jersey OCR should be treated as intermittent high-precision evidence, and segmentation should be invoked selectively for ambiguous overlap and recovery windows rather than used as the main long-horizon tracker.

## Sources

- ByteTrack paper: https://arxiv.org/abs/2110.06864
- BoT-SORT paper: https://arxiv.org/abs/2206.14651
- SAM 2 paper page: https://proceedings.iclr.cc/paper_files/paper/2025/hash/45c1f6a8cbf2da59ebf2c802b4f742cd-Abstract-Conference.html
- Jersey Number Recognition using Keyframe Identification from Low-Resolution Broadcast Videos: https://arxiv.org/abs/2309.06285
- Domain-Guided Masked Autoencoders for Unique Player Identification: https://arxiv.org/abs/2403.11328
