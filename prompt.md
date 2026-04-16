# Next Codex Prompt

You are taking over the `VeoToClip` repository on a more powerful machine.

Mission:

- finish Phase 1 with real football video data from `FootballVideos/`
- then continue sequentially through later phases only after each gate passes
- run real tests and real artifact generation
- push truthful progress to GitHub

Start here:

1. Read:
   - `docs/transfer/current-status.md`
   - `docs/transfer/setup-on-new-machine.md`
   - `docs/transfer/finish-plan.md`
   - `docs/phase-0/technical-design.md`
   - `docs/phase-0/evaluation-benchmark-plan.md`
2. Verify the environment:
   - `python3 -m unittest discover -s tests -t .`
   - `find FootballVideos -maxdepth 1 -type f | sort`
3. Inspect the current Phase 1 baseline modules:
   - `libs/tracking/baseline.py`
   - `workers/detection_tracking/runtime.py`
   - `workers/identity_lock/sweep.py`
   - `libs/possession/baseline.py`
   - `libs/evaluation/reporting.py`
   - `libs/video_io/visualization.py`

Immediate objective:

- build or finish the end-to-end real-video sweep runner that:
  - loads a raw football match video
  - detects and tracks players and ball
  - enumerates player tracks
  - treats each player as the selected player
  - runs identity baseline
  - runs possession inference baseline
  - generates clip candidates
  - writes per-player JSON metrics
  - writes aggregate summary JSON
  - writes debug overlay videos
  - writes preview clips
  - writes FP/FN gallery assets

Truth constraints:

- do not claim Phase 1 passed until at least one full match is processed
- do not claim production readiness
- if the macOS AVFoundation backend is a blocker on the new machine, replace it
  with a cross-platform backend before pushing forward
- keep the phase gates honest

Required Phase 1 finish condition:

- one full match processed end to end
- at least five players tested
- at least one player with generated clips
- overlay video exists
- metrics JSON exists

After Phase 1:

- continue one phase at a time
- keep writing phase reports
- keep tests green
- commit with Lore-format messages
- push to `origin`
