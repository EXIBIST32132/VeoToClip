# Benchmark Data Contract

This directory is reserved for benchmark manifests, annotation payloads, and
small local fixtures that can legally live in the repository.

Expected future structure:

```text
data/benchmarks/
  manifests/
    smoke.yaml
    dev.yaml
    hard-cases.yaml
  annotations/
    <video_id>.json
  fixtures/
    synthetic/
```

Manifest fields should include:

- `video_id`
- `source_uri`
- `split`
- `duration_sec`
- `fps`
- `resolution`
- `scenario_tags`
- `license_status`
- `selected_player_hint`

Benchmark assets must be tagged for the weak-point slices defined in
`docs/phase-0/evaluation-benchmark-plan.md`.
