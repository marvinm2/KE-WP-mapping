---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Reactome Integration
status: completed
stopped_at: v1.4 milestone shipped 2026-05-08
last_updated: "2026-05-08T22:50:00.000Z"
last_activity: 2026-05-08
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 27
  completed_plans: 27
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08 after v1.4 completion)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** Planning next milestone (v1.5) — run `/gsd:new-milestone`

## Current Position

Status: v1.4 shipped, deployed, audited, archived
Last activity: 2026-05-08 — milestone tagged + retrospective written
Live: https://molaop-builder.vhp4safety.nl

## Performance Metrics

**Velocity (all milestones):**

- Total plans completed: 106 (v1.0: 28, v1.1: 18, v1.2: 9, v1.3: 12, v1.4: 27 + carryforward)
- Total phases completed: 28
- Latest milestone v1.4: 6 phases / 27 plans / 32 tasks / 35 days / +11K LOC

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table (now ~50 entries spanning v1.0–v1.4). v1.4-specific patterns also in `.planning/RETROSPECTIVE.md` v1.4 section.

### Pending Todos

(carryforward into v1.5 — see PROJECT.md Active section)

- Phase 27 polish — fix WR-01..WR-04 latent edge cases in `ReactomeDiagramEmbed`
- GO/WP sibling cleanup — port C-1 XSS fix, H-2 partial-unique pending index, empty-mappings 503 guard
- Decide `/dataset/*` future (provision Zenodo/DataCite creds or downgrade to 503)
- Resolve dead `/confidence_assessment` route
- Pre-existing `test_login_redirect` / `test_guest_login_page_renders` baseline failures

### Blockers/Concerns

- IC weight calibration (default 0.15) needs domain expert review session (carryover from v1.2)
- ORCID/LS Login/SURFconext need human E2E testing with real OAuth credentials (carryover from v1.2)
- Reactome `flagItems` visual gene highlight not observed — accepted as structural-only per Plan 27-CONTEXT; revisit if v1.5 wants real highlights (likely HGNC↔diagram-entity mapping mismatch)

### Roadmap Evolution

- v1.4 closed 2026-05-08. Phase 28 added late (2026-05-06) when Phase 27 HUMAN-UAT exposed an HGNC-accession-vs-symbol bug from 2025-08-08 in shared SPARQL helper. Phase 28's persistent-ID rewrite restored gene-overlap signals across WP/GO/Reactome services in a single helper change.

## Session Continuity

**Last session:** 2026-05-08
**Stopped at:** v1.4 milestone shipped + audited + tagged + archived
**Resume file:** None
**Next action:** `/gsd:new-milestone` to scope v1.5
