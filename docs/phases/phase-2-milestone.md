# Phase 2 Initial Milestone

## Objective

Produce a reproducible player and ball detection/tracking baseline with inspectable outputs.

## Bot split recommendation

- Bot B: ingest worker and artifact layout
- Bot C: detector/tracker adapters and identity-readiness hooks
- Bot F: tracking metrics and debug artifact validation

## Deliverables

- video ingest and probe pipeline
- player and ball detection output schema usage
- tracker adapter comparison harness
- overlay video generation
- metrics artifact emission

## Validation gate

- sample videos produce frame-aligned detection and tracking outputs
- overlay videos and timelines make failures inspectable
- at least one tracking benchmark command is repeatable
