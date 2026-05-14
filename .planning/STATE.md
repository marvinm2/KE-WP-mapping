---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: User & Admin Experience
status: WP HTTP submit + admin approve path now persists step1..step4 -> proposed_* -> bulk-export SELECT end-to-end with HTTP round-trip test coverage
stopped_at: Completed 34-assessment-metadata-schema-parity/34-03-PLAN.md
last_updated: "2026-05-14T15:44:25.109Z"
last_activity: 2026-05-14 — Plan 34-03 complete (WP /submit + admin approve wired for step1..step4; 3 HTTP round-trip tests green; 317 tests pass, 51% coverage)
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-14 for v1.6 scoping)

**Core value:** Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.
**Current focus:** v1.6 User & Admin Experience — milestone scoped 2026-05-14, requirements + roadmap locked.

## Current Position

Phase: 34 — Assessment Metadata Schema Parity (3/4 plans complete; Plan 04 already summarized on disk)
Plan: 34-03 just completed; 34-04 already has a SUMMARY on disk (executed earlier — staged v1_api.py changes pending separate commit)
Status: WP HTTP submit + admin approve path now persists step1..step4 -> proposed_* -> bulk-export SELECT end-to-end with HTTP round-trip test coverage
Last activity: 2026-05-14 — Plan 34-03 complete (WP /submit + admin approve wired for step1..step4; 3 HTTP round-trip tests green; 317 tests pass, 51% coverage)

```
[████████████████████████████████░░░░░░] 33/39 phases
v1.0 ✅  v1.1 ✅  v1.2 ✅  v1.3 ✅  v1.4 ✅  v1.5 ✅  v1.6 🚧
```

## Performance Metrics

**Velocity (all shipped milestones):**

- Total plans completed: 148 (v1.0: 28, v1.1: 18, v1.2: 9, v1.3: 12, v1.4: 27, v1.5: 21 + carryforward)
- Total phases completed: 33
- Latest milestone v1.5: 5 phases / 21 plans / 44 tasks / 2 days / +4.9K LOC across 42 files

**v1.6 plan-count target (TBD):**

- Phase 34 likely 3-4 plans (schema migrations × 4 tables + serializer + analyser-contract paired PR)
- Phase 35 likely 3 plans or split into 3 sub-phases (OAuth track, landing+stats+version track, OECD precompute track)
- Phase 36 largest plan count expected — many file surfaces touched in one cohesive sweep
- Phase 37 small (3 success criteria, sibling-parity port only)
- Phase 38 medium (bulk-approve backend + 3 admin templates + shared JS extraction)
- Phase 39 medium (density CSS + login state + previews + carry items)

## Accumulated Context

### Decisions (v1.6 roadmap)

**Adopted from research synthesis (HIGH confidence, convergent across ARCHITECTURE.md and PITFALLS.md):**

- **6-phase shape** derived from research; schema-first → parallel ops → renames/merges → sibling-parity UI → admin click reduction → polish.
- **No new frameworks:** existing Flask blueprints / SQLite WAL / authlib OIDC / Cytoscape.js + AOPGraphCore IIFE / VHP4Safety CSS tokens cover all 72 requirements. Optional adds only: `beautifulsoup4` (HTML fallback if AOP-Wiki XML lacks `<oecd-status>`), CountUp.js (optional landing animation), one new precompute artifact `data/aop_oecd_status.json` (~100 KB).
- **Mandatory 301 redirect on `/aop-network`:** ~10 weeks of inbound links; route registration must stay even after rename. Regression test enforces.
- **DB-level CHECK constraint on identity:** `CHECK (identity LIKE '%:%')` enforces provider-prefixed identity invariant at schema layer; complements grep audit for `lstrip('github:')` and single-provider parsing.
- **Login state in Flask session only:** never localStorage (cross-user leak on workshop laptops), never URL hash (defeats SURFconext exact-match `redirect_uri`).
- **Bulk approve reuses single-INSERT carry-fields path:** v1.4 H-1 invariant preserved — loop over existing `create_approved_mapping` per proposal in one transaction; NOT a parallel bulk-SQL path. Fault-injection test required (bulk-approve 5, force 3rd fail, assert all 5 still pending).
- **Density-pass CSS scoping discipline:** every selector parent-scoped. v1.4 `09426fa` global-`button` cascade incident is the precedent. `cy.resize(); cy.fit()` after container changes; before/after screenshots at 1920/1366/768.
- **AOP Explorer gene-badge lazy fetch (not eager):** per-node-tap fetch via shared AOPGraphCore options, mirroring inline-mapper pattern.
- **OECD status sourcing:** XML-dump-first (`xml.etree.ElementTree` stdlib) with HTML scrape fallback only if XML lacks `<oecd-status>`. 30-min investigation front-loaded in Phase 35c.
- **SURFconext feature flag (`SURF_ENABLED`):** absorbs 1-2 week production approval gate without blocking other Phase 35 work.

**Carryover decisions from earlier milestones (still active):**

All ~65 decisions in PROJECT.md Key Decisions table (spanning v1.0–v1.5) remain in force. Milestone-specific patterns in `.planning/RETROSPECTIVE.md` per-milestone sections.

### Pending Todos

**v1.6 planning prerequisites:**

- Run `/gsd:plan-phase 34` to decompose Phase 34 into atomic plans (Phase 19 KE-GO migration is literal template).
- Front-load 30-min investigation of `aop-wiki-xml-2026-04-01.gz` for `<oecd-status>` field before committing to bs4 (Phase 35c prerequisite).
- Verify molAOP-analyser `services/api_service.py` parser mode (strict vs lax) before Phase 34 API serializer change (cross-tool contract).
- Curator-comms note 24-48h before Phase 35 landing-page deploy (bookmark URL changes for mapper users).
- Coordinate with slaenen on SURFconext production tenant approval (1-2 weeks lead time; ship behind `SURF_ENABLED` flag).
- TLS chain pre-deploy `curl -vI` on all OAuth redirect URIs (cert expiry > 30 days) before Phase 35a cutover.
- Curator rubric review during Phase 37 design: KE-Reactome 4-question text equals KE-WP wording verbatim, or per-resource variants?
- Workshop-laptop login-state UX validation during Phase 39 acceptance (A drafts → A logs out → B logs in → no draft visible).

**Standing carry-forward (mirrored in PROJECT.md Active section):**

- IC weight calibration session with domain expert (open since v1.2)
- RVIEWHL-01 (v2): visible gene highlight on Reactome diagram canvas
- v1.5 audit §6 non-blocking items absorbed into Phase 39 (DEBT-01, DEBT-02)

### Blockers / Concerns

- None blocking. SURFconext production approval is the only externally-gated dependency; mitigated via feature flag (Phase 35a).

### Risks Tracked (with phase guards)

- **4th-recurrence bulk-export SELECT drift** (Pitfall 23) — guarded explicitly in Phase 34 success criterion 2 (round-trip test on `get_all_mappings`).
- **`/aop-network` route removal** (Pitfall 2) — guarded explicitly in Phase 36 success criterion 1 (regression test `test_aop_network_redirects_to_explorer` mandated).
- **CSS cascade incident** (Pitfall 5) — guarded explicitly in Phase 39 success criterion 1 (parent-scoped selectors + before/after screenshots at three breakpoints).
- **Login state cross-user leak on shared workshop laptops** (Pitfalls 8, 9) — guarded explicitly in Phase 39 success criterion 3 (Flask session only; never localStorage; never URL hash).
- **AOP-Wiki RDF has no OECD predicate** (Pitfall 25, negative finding verified 2026-05-14) — mitigated by XML-dump-first investigation in Phase 35c.
- **Bulk-approve atomicity drift** (Pitfall 18, v1.4 H-1) — guarded explicitly in Phase 38 success criterion 1 (fault-injection test mandated).

### Roadmap Evolution

- v1.0–v1.5 shipped per `.planning/milestones/`.
- v1.6 scoped 2026-05-14 from curator+admin freeform input plus a live Playwright audit (mapper, explore, AOP Network, Downloads, Stats, login modal). Theme: user-facing polish + admin friction reduction + cross-resource parity.
- v1.6 roadmap created 2026-05-14: 6 phases (34–39), 72 requirements mapped, schema-first build order convergent with research recommendation.

## Session Continuity

**Last session:** 2026-05-14T15:44:25.101Z
**Stopped at:** Completed 34-assessment-metadata-schema-parity/34-03-PLAN.md
**Resume file:** None
**Next action:** `/gsd:plan-phase 34` to decompose Phase 34 into atomic plans following the Phase 19 KE-GO migration template.

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 34-assessment-metadata-schema-parity P01 | 6min | 3 tasks | 4 files |
| Phase 34-assessment-metadata-schema-parity P02 | 11min | 3 tasks | 3 files |
| Phase 34-assessment-metadata-schema-parity P04 | 7min | 3 tasks | 4 files |
| Phase 34-assessment-metadata-schema-parity P03 | 7min | 4 tasks | 4 files |

## Decisions

- [Phase 34-assessment-metadata-schema-parity]: proposals/ke_reactome_proposals do NOT get assessment_version — version decided at approval time (CONTEXT.md)
- [Phase 34-assessment-metadata-schema-parity]: REACTOME_PROPOSAL_CARRY_FIELDS extended in Plan 01 but wired in create_approved_mapping deferred to Plan 02 for isolated review
- [Phase 34-assessment-metadata-schema-parity]: ReactomeMappingModel.create_approved_mapping refactored to proposal_id signature: loads proposal row internally, REACTOME_PROPOSAL_CARRY_FIELDS drives INSERT column list (resolves v1.4 dead-constant tech debt, ASMT-10)
- [Phase 34-assessment-metadata-schema-parity]: confidence_level column alias in Reactome carry: ke_reactome_proposals uses 'new_pair_confidence_level' not 'confidence_level'; resolved via inline alias map in create_approved_mapping without changing REACTOME_PROPOSAL_CARRY_FIELDS constant
- [Phase 34-assessment-metadata-schema-parity]: Reactome serializer gained top-level connection_type for full sibling parity with WP (required to convert the existing forbidden-list test to a positive assertion)
- [Phase 34-assessment-metadata-schema-parity]: Phase 34 CSV columns appended at END of column lists (not interleaved) — preserves column-positional consumer back-compat at the cost of slight semantic awkwardness
- [Phase 34-assessment-metadata-schema-parity]: Analyser-repo KE-MAPPING-API-REFERENCE.md edited in place but NOT committed from builder repo — paired PR is a follow-up per molAOP_services cross-tool checklist
- [Phase 34-assessment-metadata-schema-parity]: Drop-None filter at form->schema boundary in WP /submit handler: preserve Marshmallow's required=False optional-field semantics by filtering None values out of submit_data before validate_request_data
- [Phase 34-assessment-metadata-schema-parity]: Four KE_WP_*_OPTIONS module-level constants in src/core/schemas.py — single source of truth for the canonical option-key whitelists, importable for the v1 API reference doc
- [Phase 34-assessment-metadata-schema-parity]: WP admin approve threads four assessment kwargs through BOTH create_mapping AND both update_mapping callsites — defense-in-depth for the assessment_version classifier on the new-pair provenance write path
