# Phase 0 Sub-Bot Plan

## Objective

Split Phase 0 into bounded lanes so research, architecture, evaluation, product
workflow, and scaffold work can proceed in parallel without collapsing into one
undifferentiated plan.

## Bot assignments

### Bot A: research and tooling scan

- compare tracking, ReID, ball interaction, and dataset approaches
- produce research-backed default recommendations and alternatives

### Bot B: backend and repository skeleton

- create the repo layout, worker boundaries, interface skeleton, validation
  hooks, and Phase 1/2 milestone docs

### Bot C: tracking and identity architecture

- define selected-player locking, cue fusion, uncertainty states, and recovery
  strategy

### Bot D: possession and touch inference

- define event taxonomy, state machine, clip boundary rules, and hybrid upgrade
  path

### Bot E: UI and review workflow

- define player selection UX, review timeline, correction tools, and export UX

### Bot F: testing, evaluation, and benchmark plan

- define annotation schema, benchmark slices, metrics, and future phase gates

### Bot G: packaging, environment, and docs

- owned by the lead lane in Phase 0 because the repo guidance caps concurrent
  child agents at six
- covers environment assumptions, toolchain risks, project-level docs, and the
  integrated Phase 0 closeout

## Interface ownership

- `libs/schemas`: Lead, Bot B, Bot F
- identity contracts: Bot C
- possession contracts: Bot D
- review-state and audit fields: Bot E
- benchmark manifest and annotation schema: Bot F
- worker boundaries and API manifest: Bot B

## Merge order

1. repository skeleton and validation hooks
2. architecture and product docs
3. evaluation and annotation docs
4. contract refinements in shared schema files
5. integrated Phase 0 report and cleanup

## Likely conflicts

- `libs/schemas/core.py`
- `apps/api/main.py`
- `docs/phase-0/*`
- `tests/*`

## Validation criteria

- required Phase 0 docs exist and align with the chosen architecture
- coded contracts cover the mandatory early interfaces
- scaffold validation passes
- tests pass
- repo state is clean enough to commit without transient artifacts
