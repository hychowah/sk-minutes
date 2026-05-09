- Purpose: Universal repository map for humans and LLMs
- Scope: Reading order, authority hierarchy, status-source ownership, top-level map, and warnings about temporary or stale docs; excludes implementation details not present in the repo
- Status: Active
- Last validated: 2026-05-09
- Source of truth for: Session-start reading order, authority hierarchy, status-source map, top-level documentation map

# Repository Index

This is the first file a new human or LLM session should read.

## Session-Start Reading Order

1. [INDEX.md](INDEX.md)
2. [AGENTS.md](AGENTS.md)
3. [KNOWLEDGE.md](KNOWLEDGE.md)
4. [DEVNOTES.md](DEVNOTES.md)
5. [docs/devnotes/README.md](docs/devnotes/README.md), only if older historical devnotes context is needed
6. Active execution plan, if one exists
7. Relevant stable reference docs, if they exist
8. Only then expand into code

## Authority Hierarchy

1. [DEVNOTES.md](DEVNOTES.md) for the most recent verified repository state
2. Active execution plan for scoped task progress and handoff, if one exists
3. [docs/tech-debt.md](docs/tech-debt.md) for unresolved issues and cleanup priorities
4. Stable reference docs, if they exist later, for long-lived structure
5. [KNOWLEDGE.md](KNOWLEDGE.md) for reusable lessons and constraints
6. [README.md](README.md) for setup and usage
7. [AGENTS.md](AGENTS.md) for process rules
8. Archived notes and completed plans for history only

## Current Status Sources

- Recent verified truth: [DEVNOTES.md](DEVNOTES.md)
- Historical devnotes archive: [docs/devnotes/README.md](docs/devnotes/README.md)
- Roadmap status: complete for the current local-first scope; maintained through this index, [DEVNOTES.md](DEVNOTES.md), and [docs/tech-debt.md](docs/tech-debt.md).
- Active scoped work: none currently
- Most recent completed scoped work: [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md)
- Reusable technical lessons: [KNOWLEDGE.md](KNOWLEDGE.md)
- Unresolved debt: [docs/tech-debt.md](docs/tech-debt.md)
- Stable structure: [docs/README.md](docs/README.md) and [docs/tech-debt.md](docs/tech-debt.md)
- Setup and usage: [README.md](README.md)

## Top-Level Repo Map

- [README.md](README.md): human-facing entry point
- [INDEX.md](INDEX.md): repository map and authority rules
- [AGENTS.md](AGENTS.md): LLM operating rules
- [KNOWLEDGE.md](KNOWLEDGE.md): reusable lessons and constraints
- [DEVNOTES.md](DEVNOTES.md): rolling recent verified work log
- [docs/devnotes/README.md](docs/devnotes/README.md): archive index and rollover rules for historical devnotes
- [sample/](sample): committed example outputs copied from a validated real-audio run
- [docs/README.md](docs/README.md): stable landing page for repository docs under `docs/`
- [docs/tech-debt.md](docs/tech-debt.md): unresolved debt register
- [docs/plans/README.md](docs/plans/README.md): execution plan usage rules
- [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md): historical completed MP-004 startup investigation plan
- [docs/plans/completed/workflow-contract-and-interface-coherence.md](docs/plans/completed/workflow-contract-and-interface-coherence.md): historical completed workflow/interface cleanup plan
- [docs/plans/_EXEC_PLAN_TEMPLATE.md](docs/plans/_EXEC_PLAN_TEMPLATE.md): scoped work template

## Important Commands

- `python -m minutes show-config`
- `python -m pytest tests/test_normalization_flow.py`
- `python -m minutes process-file C:\path\to\audio.wav`
- `python -m minutes show-transcript <job_id>`
- `python -m minutes show-transcript <job_id> --speaker-attributed`
- `python -m minutes show-summary <job_id>`
- `python -m minutes show-summary <job_id> --json`
- `python -m minutes summarize-job <job_id>`
- `python scripts/measure_local.py startup-path --iterations 3`
- `python scripts/measure_local.py control-plane --job-count 250 --iterations 5`
- `python scripts/measure_local.py control-plane --job-count 250 --iterations 5 --scenario summary-stale`

## Temporary And Low-Trust Docs

- Active execution plans are task-scoped and temporary.
- Completed plans are historical only.
- Archived devnotes under [docs/devnotes/README.md](docs/devnotes/README.md) are historical only.
- Local scratch files should not be treated as canonical truth.
- No active execution plan currently exists.
- Most recent completed plan: [docs/plans/completed/mp-004-startup-hotspot-investigation.md](docs/plans/completed/mp-004-startup-hotspot-investigation.md)

## Stable Vs Temporary Documents

Stable documents in this repository currently include:

- [README.md](README.md)
- [INDEX.md](INDEX.md)
- [AGENTS.md](AGENTS.md)
- [KNOWLEDGE.md](KNOWLEDGE.md)
- [DEVNOTES.md](DEVNOTES.md)
- [docs/devnotes/README.md](docs/devnotes/README.md)
- [docs/README.md](docs/README.md)
- [docs/tech-debt.md](docs/tech-debt.md)
- [docs/plans/README.md](docs/plans/README.md)

Temporary documents in this repository currently include:

- Task-local planning or migration notes, if created later

## Glossary

- Execution plan: A temporary, task-scoped document for work spanning multiple sessions or commits.
- Active work: The currently in-progress scoped task, if one exists.
- Archived: Historical material that must not be treated as current truth.
- Source of truth: The single document that owns one type of live information.
- Validated: Confirmed against the current repository state on the date shown in the file header.
