# VeoToClip

Phase 0 repository for a production-oriented football video analysis and clip
extraction system.

The product goal is narrow and concrete: a user uploads a full match video,
selects one player, reviews every automatically detected possession or action
sequence for that player, corrects mistakes, and exports clean clips.

Phase 0 freezes the architecture before deeper model work. It does not claim a
production implementation. It does provide:

- a local-first repository skeleton
- coded interface contracts for the core pipeline stages
- Phase 0 architecture, PRD, evaluation, risk, and roadmap docs
- a dependency-light API manifest server and static review-surface placeholder
- validation scripts and smoke tests

## Quick start

```bash
make validate
make test
make serve-api
```

Useful commands:

```bash
python3 scripts/validate_scaffold.py --tree
python3 -m apps.api.main
python3 -m http.server 4173 -d apps/web-ui
```

The API is intentionally dependency-free in Phase 0 and exposes `/health` and
`/manifest` for scaffold inspection.

## Key Phase 0 deliverables

- [Technical design](docs/phase-0/technical-design.md)
- [Product requirements](docs/phase-0/product-requirements.md)
- [Product workflow UX](docs/phase-0-product-workflow.md)
- [Evaluation plan](docs/phase-0/evaluation-benchmark-plan.md)
- [Risk register](docs/phase-0/risk-register.md)
- [Final phased roadmap](docs/phase-0/final-phased-roadmap.md)
- [Phase 0 bot plan](docs/phase-0/sub-bot-plan.md)

## Architecture snapshot

- Detector baseline: YOLO-family detector behind an adapter interface
- Primary player tracker: `BoT-SORT-ReID`
- Tracker fallback and ablation: `ByteTrack`
- Target-player locking: fused identity scorer over short tracklets
- Ball interaction inference: deterministic temporal geometry state machine
  first, learned rescoring later
- Clip extraction and export: FFmpeg in later phases, behind render contracts
- Storage posture: local-first project manifests and artifact directories now,
  cloud-friendly boundaries later

## Repository map

- `apps/`: API and web review surface
- `workers/`: pipeline-stage workers
- `libs/`: shared contracts and interfaces
- `data/`: manifests, samples, annotations, and saved project state
- `artifacts/`: generated debug videos, metrics, previews, and exports
- `docs/`: Phase 0 decisions and phase handoff plans
- `tests/`: scaffold and contract smoke tests

See [docs/architecture/phase-0-bot-b.md](docs/architecture/phase-0-bot-b.md)
for the initial tree rationale and merge-order notes.
