# Final Phased Roadmap

## Phase 0

- freeze architecture, PRD, evaluation plan, risk register, repo skeleton
- define contracts and handoff milestones

## Phase 1

- implement annotation schema and benchmark harness
- assemble a realistic benchmark set with hard-case slices
- automate metrics and report generation

## Phase 2

- implement video ingest plus player and ball detection or tracking baseline
- compare at least two tracking strategies
- emit inspectable tracking artifacts

## Phase 3

- implement selected-player identity locking and recovery
- add confidence, explainability, and manual override hooks

## Phase 4

- implement touch and possession inference
- add clip boundary decisions and confidence calibration

## Phase 5

- materialize preview and final clips
- support single, batch, and compilation export with metadata

## Phase 6

- build the review or edit or export UI against real backend data
- persist project state and manual audit history

## Phase 7

- run the quality-improvement loop
- expand hard-case dataset, tune thresholds, improve runtime

## Phase 8

- package, dockerize, document, and harden deployment
- add crash-safe resumable jobs and operator guidance

## Phase 9

- pursue optional advanced capabilities only after the MVP quality bar is met

## Progression rule

No phase advances on narrative alone. Each phase must end with:

- code in a clean structure
- passing tests
- demoable output
- written status summary
- known limitations
- explicit `PASS` or `FAIL`
