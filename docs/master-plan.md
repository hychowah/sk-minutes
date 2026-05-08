- Purpose: Stable repository-level direction and sequencing for major workstreams
- Scope: Long-lived priorities, sequencing, completion signals, and decision gates; excludes live task status, recent verified work logs, and temporary handoff details
- Status: Active
- Last validated: 2026-05-08
- Source of truth for: Repository-level roadmap and workstream sequencing

# Master Plan

This document defines the repository's long-lived workstreams and their intended order.

It does not replace [DEVNOTES.md](../DEVNOTES.md) for recent verified truth, [tech-debt.md](tech-debt.md) for unresolved debt, or scoped execution plans under [plans/](plans) for temporary task handoff.

## Planning Rules

- Keep this document stable and directional.
- Update it when priorities, sequencing, or completion signals change.
- Do not use it as a task log or daily progress journal.
- Link to owner documents instead of copying live details.

## Principles

- Preserve the local-first tool shape unless product scope clearly changes.
- Prefer one owner per workflow rule, interface contract, and live status surface.
- Measure performance bottlenecks before redesigning foundations.
- Delay concurrency-oriented infrastructure until the target product shape requires it.

## Workstreams

| ID | Workstream | Goal | Why It Matters | Completion Signal | Primary Owner Docs |
| --- | --- | --- | --- | --- | --- |
| MP-001 | Core Local Pipeline | Keep the normalization, transcription, diarization, speaker-attributed transcript, and summary pipeline working end-to-end for a single-user local workstation flow. | This is the foundation for every higher-level interface and performance change. | The main staged flow remains validated through focused regression tests and the real-audio opt-in path. | [DEVNOTES.md](../DEVNOTES.md), [tests/test_normalization_flow.py](../tests/test_normalization_flow.py), [tests/test_real_audio_integration.py](../tests/test_real_audio_integration.py) |
| MP-002 | Workflow Contract Cleanup | Give stage selection, stage naming, and execution semantics one clear owner. | The current pipeline grows brittle when the worker, orchestrator, CLI, API, and tests each infer workflow rules separately. | Stage progression and job eligibility are defined in one shared place, and `status` versus workflow progress semantics are no longer overloaded. | [DEVNOTES.md](../DEVNOTES.md), [src/minutes/pipeline/__init__.py](../src/minutes/pipeline/__init__.py), [src/minutes/orchestrator.py](../src/minutes/orchestrator.py), [src/minutes/worker.py](../src/minutes/worker.py) |
| MP-003 | Operator Interface Coherence | Make CLI, API, docs, and diagnostics tell the same story. | Operators should not need to reverse-engineer state roots, job lookup, or artifact access from multiple inconsistent surfaces. | README, CLI, API, and diagnostic scripts expose coherent discovery and retrieval paths with matching defaults and terminology. | [README.md](../README.md), [DEVNOTES.md](../DEVNOTES.md), [src/minutes/cli.py](../src/minutes/cli.py), [src/minutes/api/routes_jobs.py](../src/minutes/api/routes_jobs.py), [scripts/doctor.ps1](../scripts/doctor.ps1) |
| MP-004 | Performance Measurement And Hotspot Removal | Add measurement first, then remove the highest-value local bottlenecks. | The main expected costs are model cold starts, speaker-segment retranscription, whole-transcript summary requests, and linear store scans, but they are not yet benchmarked. | The repo has a lightweight measurement path for the major hotspots, and the dominant local bottlenecks have a verified mitigation. | [DEVNOTES.md](../DEVNOTES.md), [tech-debt.md](tech-debt.md), [src/minutes/adapters/transcriber_sensevoice.py](../src/minutes/adapters/transcriber_sensevoice.py), [src/minutes/orchestrator.py](../src/minutes/orchestrator.py), [src/minutes/storage/file_store.py](../src/minutes/storage/file_store.py) |
| MP-005 | Retrieval And Query Layer Cleanup | Reduce duplicated artifact lookup and retrieval behavior across interface layers. | The CLI and API currently repeat retrieval logic and error handling, which will become more expensive as artifact types grow. | Transcript, summary, and future artifact retrieval rules are implemented through shared application-level queries instead of duplicated transport logic. | [DEVNOTES.md](../DEVNOTES.md), [src/minutes/cli.py](../src/minutes/cli.py), [src/minutes/api/routes_jobs.py](../src/minutes/api/routes_jobs.py) |
| MP-006 | Storage And Execution Model Hardening | Revisit the file store and inline execution model only if the product target expands beyond single-user local use. | Stronger queueing and storage would add complexity too early unless concurrency or service operation becomes real. | A storage or execution-model migration is justified by measured bottlenecks or an explicit product-scope change. | [AGENTS.md](../AGENTS.md), [DEVNOTES.md](../DEVNOTES.md), [tech-debt.md](tech-debt.md) |

## Sequencing

1. Maintain MP-001 as the non-regression baseline.
2. Continue MP-002 until workflow ownership and semantics are explicit enough to stop leaking across layers.
3. Continue MP-003 so operator-facing surfaces become consistent while MP-002 is still fresh.
4. Start MP-004 measurement before larger performance refactors.
5. Use MP-004 results to prioritize the first real performance fixes.
6. Take on MP-005 once the workflow contract is stable enough to share retrieval logic cleanly.
7. Treat MP-006 as conditional rather than committed work.

## Decision Gates

- Do not broaden infrastructure based on suspicion alone; require a measured bottleneck or a product-scope decision.
- Do not move live status into this document; keep recent truth in [DEVNOTES.md](../DEVNOTES.md).
- Do not let temporary scoped plans become repository-wide truth; move stable conclusions back into owner docs.