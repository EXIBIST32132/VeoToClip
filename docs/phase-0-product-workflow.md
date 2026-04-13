# Phase 0 Product Workflow and Review UX

## Scope

This document defines the product workflow and review UX for a football video analysis tool that:

- ingests a full match video
- locks onto one user-selected player
- finds candidate possession and action clips for that player
- lets the user review, correct, and export those clips

It is intentionally wireflow-level. It defines screens, states, controls, and data contracts, not visual styling.

## Product Principles

1. Identity first. The product should treat "which player is this?" as the primary user decision before clip review begins.
2. Review before export. Auto-found clips are always drafts until the user accepts them.
3. Make uncertainty visible. Identity confidence, touch confidence, and clip confidence must be visible in the review UI.
4. Preserve edit history. Every manual correction must create an audit event.
5. Keep corrections cheap. The user should be able to fix most errors without leaving the timeline.
6. Use source-linked evidence. Every candidate clip should link back to source frames and the evidence used to create it.

## Core Workflow

### 1. Create Project

User actions:

- upload a match video or select an existing source
- enter a project name
- optionally set default clip handles and possession-end rules

System behavior:

- create a project record immediately
- start ingest and analysis jobs in the background
- show processing progress by stage

Required UI:

- upload area
- source metadata summary
- processing status list
- cancel/retry action

### 2. Select Target Player

User actions:

- click a player in a video frame
- draw an initial box or mask around the player
- choose from a detected player list
- optionally provide jersey number, team color, or role hints

System behavior:

- resolve the initial selection to a track candidate
- lock the selected player using a fused identity score
- show confidence and likely alternates

Required UI:

- frozen frame picker with scrub controls
- detected player list for the current frame
- hint panel for jersey number, team, and color
- confirmation step before clip generation starts

Selection rules:

- one primary target player per project run
- selection can be revised later, but revisions must be explicit
- if the system is uncertain, it must ask for confirmation instead of silently choosing

Selection decision tree:

- if a player is clicked, seed the target with that track candidate
- if a box or mask is drawn, use it as the seed and resolve to the best matching track
- if a track is chosen from the list, lock that track and mark the selection as user-confirmed
- if jersey number or team hints are provided, use them to re-rank candidates rather than override the seed blindly
- if confidence stays below threshold, show the top 3 alternatives and block clip generation until the user confirms one

### 3. Review Candidate Clips

User actions:

- inspect an auto-generated timeline of candidate possession/action clips
- play a clip preview
- jump from a clip to its source evidence
- accept or reject a clip

System behavior:

- group candidate clips into a review queue
- sort by time and confidence
- display reason labels for why each clip was created

Required UI:

- timeline with clip markers
- clip list or grid with confidence chips
- source frame jump link for each clip
- accept/reject controls on each clip card

Review timeline behavior:

- show the full match timeline at the top and the candidate clips below it
- group dense sequences into clusters so the user can review bursts of related clips faster
- color-code candidates by confidence band and interaction type
- show rejected clips in a collapsed history lane so they are recoverable
- allow a filter for low-confidence, unreviewed, or identity-uncertain clips

### 4. Correct Clips

User actions:

- trim clip start/end by frame or by seconds
- extend clip start/end
- merge adjacent clips
- split one clip into two
- relabel a clip event
- mark a clip as false positive

System behavior:

- recalculate the clip interval in the project state
- keep the original AI draft and the final edited version in audit history
- update derived export metadata

Required UI:

- trim handles in the preview player
- nudge controls for frame-accurate edits
- merge and split actions in the clip menu
- reason selector for correction types

Correction interaction model:

- dragging the left handle changes start time
- dragging the right handle changes end time
- keyboard nudges should move by one frame or one second depending on user preference
- merge should require adjacent clips and show the combined interval before commit
- split should create two draft clips and preserve the source evidence links for both

### 5. Export

User actions:

- export selected clips individually
- export all accepted clips as a batch
- export a compilation reel
- download metadata sidecars

System behavior:

- render final clips with the chosen handles and encoding preset
- create per-clip and batch manifests
- preserve timestamps and clip reasons

Required UI:

- export drawer or modal
- format and preset selectors
- clip selection summary
- job status and download links

Export flow:

- the user chooses single clip, batch, or compilation mode
- the system shows the exact set of clips that will be rendered
- the user can choose to include metadata sidecars and audit logs
- the system queues renders and keeps the project editable while export runs
- completed exports stay linked to the source project for re-download

## Wireflow-Level Screens

### Screen A: Project Home

Purpose:

- start a new analysis run
- resume an existing project

Primary elements:

- video upload entry
- recent projects list
- processing queue

Transition:

- upload completes -> source ingest state

### Screen B: Player Selection

Purpose:

- choose the target player from one or more visible frames

Primary elements:

- scrubber
- paused frame with overlay
- selectable player boxes
- hint fields for jersey number and team
- confirm selection button

Transition:

- confirm selection -> analysis results dashboard

### Screen C: Analysis Dashboard

Purpose:

- show processing status and candidate clip generation progress

Primary elements:

- stage progress list
- identity confidence summary
- clip generation count
- warnings for low-confidence periods

Transition:

- first candidates available -> review timeline

### Screen D: Review Timeline

Purpose:

- review all candidate clips in temporal order

Primary elements:

- horizontal timeline with markers
- clip cards
- filter controls
- sort by confidence or time

Transition:

- click clip -> clip detail drawer

### Screen E: Clip Detail

Purpose:

- inspect the clip, evidence, and correction controls

Primary elements:

- preview player
- source evidence strip
- confidence explanation panel
- trim and extend controls
- accept/reject controls

Transition:

- save edit -> timeline updates immediately

### Screen F: Export Center

Purpose:

- export accepted clips and the compilation reel

Primary elements:

- selected clips summary
- export options
- metadata toggle
- job progress

Transition:

- render complete -> download available

## Explainability Overlay Requirements

The overlay should explain why a player was tracked and why a clip was created.

Must show:

- selected player track path
- ball position and distance indicator
- current identity confidence
- contact or interaction marker
- possession phase boundary marker
- alternate player suggestion when identity is uncertain

Nice to have:

- mini confidence trend over the clip
- key evidence frames for identity locking
- ball velocity change cue at interaction moments

Overlay interaction rules:

- overlays must be toggleable without pausing playback
- clicking an evidence marker should jump to the source frame
- low-confidence identity spans should be shaded rather than hidden
- the overlay should visually distinguish hard evidence from inferred evidence

The overlay should never replace the underlying video. It should be togglable and should degrade gracefully when a cue is unavailable.

## Manual Correction Tools

The review UI must support these corrections without leaving the project:

- accept clip
- reject clip
- trim start
- trim end
- extend start
- extend end
- merge adjacent clips
- split a clip at the playhead
- relabel event type
- reassign target player for a segment
- mark identity loss or occlusion
- mark replay segment
- mark camera cut

Correction rules:

- every correction must be undoable within the session
- every correction must be written to the audit trail
- corrections should update downstream exports immediately

## Export Requirements

Export must support:

- single clip download
- batch zip download
- compilation reel export
- metadata sidecar export in JSON or CSV

Export metadata must include:

- source video name
- source start and end timestamps
- clip start and end timestamps
- selected player identity history
- confidence scores
- clip reason labels
- manual edit audit events

Suggested naming:

- `matchname_playername_clip_###.mp4`
- `matchname_playername_compilation.mp4`
- `matchname_playername_clips.json`

Export acceptance rules:

- exported media must match the approved clip intervals exactly
- batch export must preserve clip order unless the user explicitly reorders it
- if any render fails, successful clips remain downloadable
- export metadata must use the edited timeline, not the original draft timeline

## Data Contracts The UI Needs

The UI should receive these objects from the backend.

### Project

- project id
- source video id
- upload status
- analysis status
- default clip handles
- possession-end rule set

### Target Player Session

- selected frame reference
- locked track id
- confidence score
- alternate candidates
- hint inputs used
- identity history

### Clip Candidate

- clip id
- start timestamp
- end timestamp
- event type
- confidence score
- reason labels
- linked source evidence
- accepted or rejected state
- edit history

### Audit Event

- event id
- actor type
- timestamp
- action type
- old value
- new value
- reason note

## Empty And Error States

### No Player Selected

- explain that selection is required before clip generation
- show the selection methods instead of an empty dashboard

### Low Confidence Identity

- show a warning
- surface alternate candidates
- allow manual re-selection

### No Clip Found

- show zero-result state
- offer a timeline review of the full match segment
- allow the user to widen possession-end rules or switch selection method

### Export Failure

- keep accepted edits saved
- show retry for the failed export job
- keep rendered clips separate from project state

## Phase 0 Product Requirements

1. The user can upload or open a match video and create a project.
2. The user can select one target player by click, box, track list, or hints.
3. The UI can show candidate clips on a review timeline.
4. The user can inspect evidence for each clip.
5. The user can accept, reject, trim, extend, merge, split, and relabel clips.
6. The user can correct identity mistakes mid-project.
7. The user can export selected clips individually or as a batch.
8. The system keeps an audit trail for all manual corrections.
9. The UI exposes confidence and uncertainty for both identity and clip boundaries.

## Phase 0 Gate Criteria For Bot E

- review workflow supports selection, correction, and export without dead ends
- every manual action maps to a backend data event
- timeline and export flows are fully source-linked
- uncertainty is visible and actionable
- the spec is ready to hand to implementation without design interpretation

## Next Implementation Milestones

### Phase 1

- define the project state schema
- define the clip candidate schema
- define the audit event schema
- build a minimal review list and clip drawer against mock data

### Phase 2

- wire the selection UI to actual tracked player candidates
- wire clip review actions to real stored project state
- wire export to a deterministic render job
