# Setup On New Machine

## Goal

Bring this repository up on a stronger machine, restore access to the real
football videos, and finish the real-data Phase 1 sweep and later phases.

## Transfer checklist

1. Clone the repository.
2. Copy the local-only assets separately:
   - `FootballVideos/`
   - any local model weights you want to reuse
3. Verify Python 3.11+ is available.
4. Create a virtual environment.
5. Install the runtime needed for the current baseline.
6. Run the test suite.
7. Run the real-video sweep.

## Recommended bootstrap commands

```bash
git clone https://github.com/EXIBIST32132/VeoToClip.git
cd VeoToClip
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install numpy scipy torch torchvision opencv-python-headless
```

If you want to preserve the current macOS-native path, also install:

```bash
python3 -m pip install pyobjc-framework-AVFoundation pyobjc-framework-Quartz pyobjc-framework-CoreMedia pyobjc-core
```

## Platform note

The current tracking path depends on:

- `torch`
- `torchvision`
- `numpy`
- `scipy`
- PyObjC AVFoundation bindings on macOS

If the target machine is not macOS, the recommended first engineering action is
to replace or augment:

- [libs/video_io/avfoundation.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/video_io/avfoundation.py)

with a cross-platform OpenCV or FFmpeg backend and update:

- [libs/video_io/__init__.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/video_io/__init__.py)
- [libs/tracking/baseline.py](/Users/jonathanst-georges/Documents/VeoToClip/libs/tracking/baseline.py)

## Required local assets

The following folder is required locally but intentionally not tracked:

```text
FootballVideos/
```

The next Codex bot should confirm the presence of at least:

- `Varsity Eagles vs Alleyns Jan 31 2026.mp4`
- `Varsity Eagles vs Brentwood School Feb 11 2026.mp4`

## Validation after setup

Run:

```bash
python3 -m unittest discover -s tests -t .
```

Then inspect:

- `docs/transfer/current-status.md`
- `docs/transfer/finish-plan.md`
- `prompt.md`

## Git remote

The intended remote is:

```text
https://github.com/EXIBIST32132/VeoToClip.git
```

If `origin` is not configured after clone, run:

```bash
git remote add origin https://github.com/EXIBIST32132/VeoToClip.git
```
