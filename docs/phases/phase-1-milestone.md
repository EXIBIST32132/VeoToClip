# Phase 1 Initial Milestone

## Objective

Stand up the repeatable dataset and evaluation harness before integrating real detectors or trackers.

## Bot split recommendation

- Bot A: dataset sourcing and edge-case manifest design
- Bot B: annotation schema and tooling skeleton
- Bot F: evaluation metrics, report template, and automation harness

## Deliverables

- versioned annotation schema extension
- benchmark manifest with tagged cases
- evaluation runner stub and report template
- annotation import/export utilities
- one command that validates manifests and runs empty-or-baseline metrics

## Validation gate

- benchmark cases discoverable automatically
- schema validation works on sample annotations
- evaluation command exits cleanly and produces a machine-readable report
