# Phase 0 Product Requirements

## Product objective

Enable a user to upload a full football match video, select one player, review
all automatically detected possession or action clips involving that player, fix
errors quickly, and export the final set cleanly.

This PRD freezes the functional scope for the MVP and maps directly to later
backend, model, and UI work.

## Primary user workflow

1. Create a project from a match video.
2. Select the target player by click, box, mask, or track list.
3. Wait for analysis jobs to produce candidate clips.
4. Review candidate clips on a timeline with evidence overlays.
5. Accept, reject, trim, extend, merge, split, or relabel clips.
6. Correct identity mistakes or mark uncertain intervals.
7. Export selected clips, a batch bundle, or a compilation reel.

Detailed wireflow guidance lives in
[docs/phase-0-product-workflow.md](/Users/jonathanst-georges/Documents/VeoToClip/docs/phase-0-product-workflow.md).

## Functional requirements

### Ingest and project setup

- upload a full match video
- persist project state locally
- show processing stages and recoverable failures

### Target-player selection

The user must be able to select the player using one or more of:

- click on frame
- draw initial box
- draw initial mask
- choose from tracked player list
- provide optional jersey number, team, or color hints

### Automated analysis

The system must:

- detect players and the ball
- track relevant entities across frames
- maintain a selected-player identity hypothesis with explicit confidence
- detect likely touches and possession intervals for that player
- create candidate clips with reasons and scores

### Review and correction

The user must be able to:

- review clips on a timeline
- preview clip evidence with overlays
- accept or reject clips
- trim start and end
- extend start and end with handles
- merge adjacent clips
- split a clip
- relabel the interaction type
- reassign target player for a bad segment
- mark occlusion or uncertainty

### Export

The system must support:

- single clip export
- batch clip export
- merged compilation reel export
- optional metadata sidecar export

## Stored metadata

Each project must preserve:

- source timestamps
- clip timestamps
- confidence scores
- clip reasons
- interaction labels
- player track ID history
- audit trail of manual edits

## Non-functional requirements

- local-first initial deployment
- inspectable artifacts at each stage
- modular interfaces that permit swapping detector, tracker, identity, and
  possession logic
- failure visibility preferred over silent automation
- deterministic export timing

## Success criteria for MVP

The MVP passes when it:

- tracks a selected player through real football footage with usable continuity
- finds most true interaction phases for that player
- keeps false positives manageable through confidence and review
- lets a user fix mistakes without leaving the review workflow
- exports clips with correct timing and metadata

## Explicit non-goals for Phase 0

- claiming production readiness
- optimizing for multi-sport generalization
- building cloud deployment before local correctness
- replacing review UX with opaque automation
