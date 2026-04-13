# Phase 0 Bot B: Repository Skeleton Recommendation

## Intent

Establish a reversible, local-first repository layout that separates product surfaces, workers, shared contracts, evaluation assets, and artifacts before heavier framework or model choices are locked in.

## Recommended file tree

```text
.
├── README.md
├── Makefile
├── pyproject.toml
├── .env.example
├── apps/
│   ├── api/
│   │   └── main.py
│   └── web-ui/
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── workers/
│   ├── registry.py
│   ├── ingest/
│   ├── detection_tracking/
│   ├── identity_lock/
│   ├── possession_inference/
│   └── clip_render/
├── libs/
│   ├── schemas/
│   │   └── core.py
│   ├── video_io/
│   │   └── interfaces.py
│   ├── tracking/
│   │   └── interfaces.py
│   ├── identity/
│   │   └── interfaces.py
│   ├── possession/
│   │   └── interfaces.py
│   └── evaluation/
│       └── interfaces.py
├── data/
│   ├── benchmarks/
│   ├── samples/
│   ├── annotations/
│   ├── manifests/
│   └── projects/
├── artifacts/
│   ├── debug_videos/
│   ├── fp_gallery/
│   ├── fn_gallery/
│   ├── metrics/
│   ├── exports/
│   └── previews/
├── docs/
│   ├── architecture/
│   └── phases/
├── scripts/
│   └── validate_scaffold.py
└── tests/
    ├── test_project_layout.py
    └── integration/
        └── test_manifest_contract.py
```

## Boundary decisions

### Keep separate immediately

- `libs/schemas`: canonical data contracts used by apps, workers, and evaluation
- `workers/*`: orchestration and job boundaries, not shared utility dumping grounds
- `libs/evaluation`: metrics and benchmark protocol isolated from model/runtime code
- `artifacts/`: generated outputs only; never mix source data and generated data
- `data/benchmarks`: evaluation-owned manifests and legal small fixtures only
- `data/projects`: local-first saved state distinct from source annotations and manifests

### Keep intentionally lightweight in Phase 0

- no framework lock for the web UI
- no queue or orchestration dependency yet
- no model downloads or large assets committed
- no tracker-specific adapters until benchmark harness exists
- no database choice before local project-state workflows are validated

## Why this layout

- It matches the planned pipeline stages directly, so ownership can split by worker.
- It allows Phase 1 to land annotation/evaluation work without fighting Phase 2 tracking code.
- It keeps interfaces ahead of implementations, which is critical for later tracker and identity swaps.
- It preserves a path to cloud execution later by keeping project data and derived artifacts explicit.

## Merge order for Phase 1 and Phase 2

1. `libs/schemas` and `libs/evaluation` expand first.
2. `data/manifests`, `data/annotations`, and annotation docs land next.
3. Phase 1 evaluation scripts and benchmark fixtures merge before detector/tracker adapters.
4. Phase 2 ingest and tracking worker code merges after benchmark IO contracts settle.
5. API endpoints for job status and artifact browsing land after worker output schemas stabilize.
6. UI wiring should consume stable manifest and artifact contracts, not raw worker internals.

## Likely conflicts

### Phase 1 vs Phase 2

- `libs/schemas/core.py`: annotation and tracking output shape will both push changes here
- `data/manifests/*`: benchmark manifests and ingest manifests may diverge if not normalized early
- `apps/api/main.py`: Phase 1 may want evaluation/report endpoints while Phase 2 wants ingest/tracking endpoints
- `workers/ingest/job.py`: dataset prep and video ingest responsibilities can blur

### Conflict mitigation

- keep annotation schema versioned from the first Phase 1 merge
- add new dataclasses instead of mutating shared fields without version notes
- route API growth through clearly named modules once real endpoints begin
- keep worker outputs file-based and schema-backed before introducing runtime coupling

## First implementation milestone: Phase 1

- freeze `AnnotationProject`, `TouchAnnotation`, and `PossessionAnnotation` schema additions
- add a benchmark manifest format with split tags and edge-case tags
- create annotation import/export scripts
- implement metric stubs and baseline report generation
- make `scripts/validate_scaffold.py` verify benchmark manifest presence once cases exist

## First implementation milestone: Phase 2

- add video probing and frame extraction adapters under `libs/video_io`
- implement detector/tracker adapter contracts under `libs/tracking`
- emit per-frame detection and track outputs to versioned artifact files
- produce overlay videos and track timeline artifacts into `artifacts/debug_videos` and `artifacts/metrics`
- expose artifact browsing via API before building richer UI controls
