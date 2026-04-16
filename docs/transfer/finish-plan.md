# Finish Plan

## Immediate objective

Finish Phase 1 on the stronger machine using real football match videos and
produce the actual sweep artifacts required by the gate.

## First commands the next Codex bot should run

1. Confirm the environment and dataset:

```bash
git status --short --branch
python3 -m unittest discover -s tests -t .
find FootballVideos -maxdepth 1 -type f | sort
```

2. Read the current implementation surfaces:

- `docs/phase-0/`
- `docs/transfer/current-status.md`
- `libs/tracking/baseline.py`
- `workers/detection_tracking/runtime.py`
- `workers/identity_lock/sweep.py`
- `libs/possession/baseline.py`
- `libs/evaluation/reporting.py`
- `libs/video_io/visualization.py`

## What the next bot must build or finish first

### 1. End-to-end runner

Create or finish a single orchestrator that:

- loads a real match video
- runs baseline detection and tracking
- enumerates player tracks
- runs the sweep identity baseline per player
- runs possession inference per player
- generates clip candidates per player
- writes metrics and artifact outputs

### 2. Artifact writing

The real run must produce:

- `artifacts/debug_videos/...`
- `artifacts/metrics/...`
- `artifacts/previews/...`
- `artifacts/fp_gallery/...`
- `artifacts/fn_gallery/...`

### 3. Phase 1 gate evidence

The run must prove:

- at least one full video processed end to end
- at least five players tested automatically
- at least one player produced clips
- at least one overlay video exists
- metrics JSON is readable

## Recommended engineering order

1. Make the video backend cross-platform if needed.
2. Write the real-video sweep runner.
3. Run the sweep on one full match at a transparent sampled FPS.
4. Fix any schema or artifact-shape issues exposed by the tests.
5. Run the artifact gate tests again.
6. Write `docs/phase-1/phase-1-report.md`.
7. Only then mark Phase 1 as `PASS`.

## After Phase 1

Continue strictly phase by phase:

1. Phase 2: stronger tracking baseline and debug outputs
2. Phase 3: real identity locking and recovery
3. Phase 4: better touch and possession inference
4. Phase 5: real clip materialization
5. Phase 6: review UI
6. Phase 7: quality improvement loop
7. Phase 8: packaging and deployment

Do not skip gates.

## Push policy

Do not push a fake success state.

Push only when:

- tests pass
- the current phase report is written
- the working tree is clean
- the commit message follows the Lore protocol
