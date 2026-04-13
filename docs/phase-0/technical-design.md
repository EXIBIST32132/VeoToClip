# Phase 0 Technical Design

## Objective

Freeze the initial production architecture for a football video analysis system
that can take a full match video, let a user select one player, find all
meaningful player-ball interaction phases, and export reviewable clips.

The design bias for MVP is:

- deterministic and inspectable before clever
- local-first before cloud
- modular and swappable before optimized
- benchmark-driven before intuition-driven

## Recommended architecture

```text
input video
-> ingest worker
-> detection + tracking worker
-> identity lock worker
-> possession inference worker
-> clip render worker
-> review UI + export workflow
```

### Module boundaries

- `apps/api`: project lifecycle, manifest, job status, later review APIs
- `apps/web-ui`: upload, player selection, review timeline, manual correction
- `workers/ingest`: probing, frame indexing, project manifests
- `workers/detection_tracking`: player and ball detections plus MOT outputs
- `workers/identity_lock`: selected-player assignment, recovery, explainability
- `workers/possession_inference`: touch detection, control segmentation, clip candidates
- `workers/clip_render`: previews, exports, metadata sidecars, compilation reels
- `libs/*`: stable contracts that keep model and runtime choices swappable

## Core decisions

### Detection and tracking baseline

Recommendation:

- detector family: YOLO-based detector behind an adapter interface
- primary player tracker: `BoT-SORT-ReID`
- fallback and ablation: `ByteTrack`

Why:

- `ByteTrack` is a strong baseline because it associates low-score detections,
  which helps under occlusion and crowding.
- `BoT-SORT` extends the tracker with appearance cues and camera-motion
  compensation, which better matches broadcast football where pans and crossings
  are common.
- the detector stays behind an interface because tool choice may change with
  licensing, runtime, and model-quality tradeoffs.

Rejected as the Phase 0 default:

- tracker-only raw IDs as the identity solution
- segmentation-first long-horizon player tracking
- detector-specific code scattered across workers

### Target-player identification

Three approaches were compared:

1. tracker-only identity locking
2. tracker plus appearance ReID
3. fused scorer over short tracklets using continuity, ReID, team color, motion,
   sparse jersey OCR, and selective segmentation refinement

Chosen approach:

- **fused scorer over short tracklets**

Why it wins:

- tracker-only is too brittle under occlusion, camera cuts, and similar-looking
  teammates
- ReID-only helps, but same-team similarity and changing view angles still
  produce switches
- the fused scorer is calibratable, inspectable, and survives sparse evidence
  better than any single cue

Identity runtime states:

- `LOCKED`
- `UNCERTAIN`
- `LOST`

Segmentation decision:

- use SAM2-style propagation only for ambiguous initialization, overlap
  refinement, and recovery windows
- do not make segmentation the default full-match identity engine

### Ball interaction and possession inference

Three approaches were compared:

1. rule-based temporal geometry and kinematics
2. learned temporal classifier or segmenter
3. trajectory-only possession inference fallback

Chosen MVP path:

- **deterministic temporal geometry state machine first**
- **hybrid rescoring later**

Why it wins:

- rules are debuggable, data-light, and expose clear failure modes
- a pure learned model is premature before the evaluation harness and labels
  exist
- a hybrid path gives the best long-term shape: deterministic proposals now,
  learned disambiguation later for aerial duels, deflections, and contested
  turnovers

Authoritative possession states:

- `free_ball`
- `candidate_contact`
- `controlled_by_target`
- `controlled_by_other`
- `contested`
- `dead_ball`
- `uncertain`

### Clip boundary rules

Clip start:

- earliest accepted target contact or control frame
- backtracked to the beginning of the accepted contact window
- configurable pre-roll applied

Clip end:

- stable other-player control
- ball out of play
- goal scored
- foul or whistle if detected or annotated
- unresolved loose-ball timeout
- replay or hard cut when continuity becomes unreliable

Special handling:

- brief deflections do not automatically become possessions
- contested tackles get a grace window before clip termination
- camera cuts and replay inserts force uncertainty handling rather than silent
  continuation

## Storage and artifact strategy

Phase 0 keeps storage simple and local:

- project manifests and saved state in `data/projects/`
- benchmark manifests in `data/benchmarks/`
- source annotations in `data/annotations/`
- generated outputs in `artifacts/`

Planned artifact types:

- per-frame detections and tracks in JSONL or Parquet
- identity decisions with cue contributions
- possession decisions and interval timelines
- debug overlays and false-positive or false-negative galleries
- export manifests and sidecar metadata

Reason:

- file-backed artifacts are easy to inspect, diff, archive, and migrate to cloud
  storage later
- a database can be introduced once the review workflow and schema have
  stabilized

## Contracts frozen in code

Phase 0 now defines explicit contracts for:

- frame provider: [libs/video_io/interfaces.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/video_io/interfaces.py)
- detector output and tracker output:
  [libs/schemas/core.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/schemas/core.py)
- tracker interfaces: [libs/tracking/interfaces.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/tracking/interfaces.py)
- identity scorer:
  [libs/identity/interfaces.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/identity/interfaces.py)
- possession inference:
  [libs/possession/interfaces.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/possession/interfaces.py)
- clip request, export job, and annotation bundle:
  [libs/schemas/core.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/schemas/core.py)
- evaluation runner:
  [libs/evaluation/interfaces.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/evaluation/interfaces.py)

## Weak points and mandatory benchmarks

Every weak point must map to a benchmark slice:

- same-team lookalikes
- occlusion duration sweep
- camera cuts and replay inserts
- low-resolution or motion blur
- jersey not visible
- airborne balls and aerial duels
- set-piece crowding
- touchline crowding and out-of-play events
- goalkeeper possession
- player exit and re-entry

## Phase 1 milestone

- freeze annotation payload version `0.1.x`
- formalize benchmark manifests and slice tags
- implement schema loaders and evaluation runner stubs
- create a small, repeatable benchmark set and report format

## Phase 2 milestone

- implement video probe and frame access adapters
- benchmark at least `BoT-SORT-ReID` and `ByteTrack`
- persist frame-aligned detections and tracks
- emit overlay videos and timeline artifacts

## Source notes

Research grounding used for this Phase 0 recommendation:

- ByteTrack official repository: https://github.com/FoundationVision/ByteTrack
- BoT-SORT official repository: https://github.com/NirAharon/BoT-SORT
- SAM 2 official repository: https://github.com/facebookresearch/sam2
- SoccerNet benchmark suite: https://www.soccer-net.org/home
- IFAB Law 9: https://www.theifab.com/laws/latest/the-ball-in-and-out-of-play/
- IFAB Law 10: https://www.theifab.com/laws/latest/determining-the-outcome-of-a-match/
- Ultralytics docs and licensing notes: https://docs.ultralytics.com/
- Jersey Number Recognition from low-resolution broadcast video:
  https://arxiv.org/abs/2309.06285
- Domain-Guided Masked Autoencoders for Unique Player Identification:
  https://arxiv.org/abs/2403.11328
- Ball possessor and event timing paper:
  https://www.scitepress.org/Papers/2025/133177/133177.pdf
