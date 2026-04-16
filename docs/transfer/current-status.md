# Current Status

## Purpose

This document is the transfer snapshot for moving the VeoToClip repository to a
more powerful machine so a new Codex instance can finish Phase 1 and then
continue the later phases with real validation.

## Phase status

### Phase 0

- Status: complete
- Gate: `PASS`
- Architecture docs, repo skeleton, evaluation plan, risk register, and initial
  contracts are already in the repo under `docs/phase-0/`.

### Phase 1

- Status: partially implemented, not yet closed
- Gate: not yet earned
- The repo now contains real-video-aware baseline modules, but the full end to
  end sweep run over `FootballVideos/` has not been completed and archived as a
  passing phase report yet.

## What exists now

### Real-video dataset contract

- `FootballVideos/` is treated as a required local dataset for Phase 1.
- The local dataset contains two full match videos:
  - `Varsity Eagles vs Alleyns Jan 31 2026.mp4`
  - `Varsity Eagles vs Brentwood School Feb 11 2026.mp4`
- The folder is intentionally ignored by Git and must be copied separately to
  the new machine.

### Implemented Phase 1 building blocks

- Tracking baseline:
  - [libs/tracking/baseline.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/tracking/baseline.py)
  - [workers/detection_tracking/runtime.py](/Users/jonathanst-georges/Documents/VeoToClip/workers/detection_tracking/runtime.py)
- macOS-native frame provider:
  - [libs/video_io/avfoundation.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/video_io/avfoundation.py)
- Identity sweep baseline:
  - [workers/identity_lock/sweep.py](/Users/jonathanst-georges/Documents/VeoToClip/workers/identity_lock/sweep.py)
  - [workers/identity_lock/job.py](/Users/jonathanst-georges/Documents/VeoToClip/workers/identity_lock/job.py)
  - [scripts/run_identity_sweep.py](/Users/jonathanst-georges/Documents/VeoToClip/scripts/run_identity_sweep.py)
- Possession baseline:
  - [libs/possession/baseline.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/possession/baseline.py)
  - [workers/possession_inference/job.py](/Users/jonathanst-georges/Documents/VeoToClip/workers/possession_inference/job.py)
- Reporting layer:
  - [libs/evaluation/reporting.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/evaluation/reporting.py)
- Visualization helper:
  - [libs/video_io/visualization.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/video_io/visualization.py)

### Tests currently present

- dataset contract:
  - [tests/test_phase1_real_video_dataset_contract.py](/Users/jonathanst-georges/Documents/VeoToClip/tests/test_phase1_real_video_dataset_contract.py)
- artifact gate contract:
  - [tests/integration/test_phase1_sweep_artifact_gate_contract.py](/Users/jonathanst-georges/Documents/VeoToClip/tests/integration/test_phase1_sweep_artifact_gate_contract.py)
- report writer coverage:
  - [tests/integration/test_sweep_report_writer.py](/Users/jonathanst-georges/Documents/VeoToClip/tests/integration/test_sweep_report_writer.py)
- visualization coverage:
  - [tests/test_visualization.py](/Users/jonathanst-georges/Documents/VeoToClip/tests/test_visualization.py)

## Verified state at transfer time

The current repository test suite passes:

```bash
python3 -m unittest discover -s tests -t .
```

Observed result on the source machine:

- `Ran 17 tests ... OK (skipped=5)`

The skips are intentional. They cover the artifact gate that only activates
after real-video sweep outputs exist under `artifacts/`.

## What is still missing before Phase 1 can pass

1. A single command that runs the full real-video sweep end to end.
2. At least one full match processed into:
   - per-player JSON reports
   - aggregate summary
   - debug overlay videos
   - preview clips
   - FP/FN galleries
3. Confirmation that at least 5 players were tested and at least one player
   yielded clips in the real run.
4. A Phase 1 completion report with `PASS` or `FAIL`.

## Important caveat

The current video loader is macOS-specific because it uses AVFoundation. If the
next machine is Linux or Windows, the next Codex bot should either:

- replace the AVFoundation frame provider with an OpenCV or FFmpeg-backed
  implementation, or
- add a second backend and switch by platform.
