# Phase 0 Risk Register

| ID | Risk | Why it matters | Mitigation | Benchmark / gate owner |
| --- | --- | --- | --- | --- |
| R1 | Selected-player identity switches under occlusion or crossings | Wrong player means wrong clips regardless of downstream quality | Fused identity scorer, `LOCKED/UNCERTAIN/LOST` states, recovery logic, explicit alternate candidates | Bot C, Phase 1 and Phase 3 |
| R2 | Same-team lookalikes make ReID and color cues ambiguous | Football kits and camera distance make teammates hard to disambiguate | Add sparse jersey OCR, overlap refinement, lookalike benchmark slice, manual relock flow | Bot C and Bot F |
| R3 | Ball detector misses or jitters because the ball is small, blurred, or hidden | Touch and possession inference fail without stable ball evidence | Ball-specific benchmark slices, continuity smoothing, uncertainty fallback, debug overlays | Bot B, Bot D, Bot F |
| R4 | Possession logic overfits to naive proximity | Produces false clips and bad boundaries in contested play | Use temporal geometry and state machine, not nearest-center only; add contested and uncertain states | Bot D |
| R5 | Camera cuts and replay inserts break continuity assumptions | Identity and possession can be hallucinated across discontinuities | Add cut and replay tags, hard reset policy, benchmark slices, review warnings | Bot C, Bot D, Bot F |
| R6 | Annotation effort becomes the bottleneck | Without a benchmark harness, model changes become guesswork | Start with small realistic benchmark set, active-learning expansion, versioned schema | Bot F |
| R7 | SAM2 or segmentation refinement is too expensive to run continuously | Full-match runtime can become impractical | Use segmentation only on ambiguous initialization, overlap, and recovery windows | Bot C |
| R8 | Detector stack licensing or runtime constraints block commercialization later | A working prototype may still be unusable in production | Keep detector behind adapter, record licensing assumptions early, avoid framework lock-in | Lead + Bot G |
| R9 | Review UX is too weak to recover from auto errors | Product becomes unusable even if models are decent | Make timeline review, trim, merge, split, relock, and evidence overlays core scope | Bot E |
| R10 | Export timing drifts from reviewed intervals | User loses trust in the final output | Frame-accurate clip request and export-job contracts, export correctness metrics, FFmpeg validation in Phase 5 | Bot B, Bot F |
| R11 | Environment drift blocks reproducibility | Phase gates become unreliable | Keep scaffold dependency-light in Phase 0, add Docker and setup docs in Phase 8 | Bot G |
| R12 | Current dev environment lacks FFmpeg | Export and preview work cannot be validated locally yet | Treat as a known environment limitation until Phase 5 packaging; document requirement now | Lead + Bot G |
