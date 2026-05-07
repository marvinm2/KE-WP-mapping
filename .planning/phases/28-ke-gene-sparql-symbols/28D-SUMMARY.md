---
phase: 28
plan: D
subsystem: planning-docs
tags: [docs, roadmap, requirements, planning]
requires: []
provides:
  - "ROADMAP Phase 28 entry rewritten for persistent-IDs design"
  - "KEGENE-01 requirement added to REQUIREMENTS.md with traceability"
affects:
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
tech_stack:
  added: []
  patterns:
    - "Documentation lockstep: ROADMAP success criteria mirror plan-file objectives"
    - "Requirement-to-phase traceability via single source-of-truth table"
key_files:
  created:
    - .planning/phases/28-ke-gene-sparql-symbols/28D-SUMMARY.md
  modified:
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "ROADMAP success criteria reformulated as 7 testable assertions covering helper return type, API shape, all three downstream consumers, Phase 27 backward-compat, and cache-bust mechanism"
  - "KEGENE-01 wording covers both internal (helper return type + downstream non-empty signals) and external (genes_full API field) contracts in one statement"
  - "Helper Library section placed after Viewer (existing v1.4 sections preserved); requirement count bumped 17 -> 18"
metrics:
  duration_seconds: 165
  tasks_completed: 2
  files_modified: 2
  files_created: 1
  completed_at: "2026-05-07"
---

# Phase 28 Plan D: ROADMAP & REQUIREMENTS Lockstep Summary

Documentation half of Phase 28: rewrote the ROADMAP Phase 28 entry per CONTEXT D-08 (current entry framed the work as a symbols-only fix; redefined phase delivers persistent identifier triples) and added the new `KEGENE-01` requirement to REQUIREMENTS.md with traceability. Closes the loop between research findings (locked persistent-IDs design) and the rest of the GSD planning surface so Phase 29+ planning sees an accurate state.

## Artifacts Touched

| File | Edit type | Region |
| ---- | --------- | ------ |
| `.planning/ROADMAP.md` | rewrite | Summary line in v1.4 block (line ~74); full Phase 28 detail block (lines ~146-162); progress-table row (line ~195) |
| `.planning/REQUIREMENTS.md` | additions + replacements | new `### Helper Library` section after Viewer; new Traceability row after RVIEW-01; coverage block 17 → 18; footer date 2026-03-11 → 2026-05-07 |

## Diff Regions

### ROADMAP.md — Edit 1: Summary line (v1.4 block)

Was:

```
- [ ] **Phase 28: KE Gene SPARQL Returns Symbols** — Fix shared `ke_genes.py` SPARQL helper to return HGNC symbols (not numeric accession IDs) so flagItems and gene-overlap scoring work across Reactome, WP, and GO suggestion services
```

Now:

```
- [ ] **Phase 28: KE Gene SPARQL Returns Persistent Identifiers** — Rewrite shared ke_genes.py SPARQL helper to return strict {ncbi, hgnc, symbol} triples from a single non-federated AOP-Wiki query; carry persistent IDs through three suggestion services and add genes_full to /ke_genes/<ke_id> while preserving Phase 27 frontend's genes field
```

### ROADMAP.md — Edit 2: Phase 28 detail block

Title: `### Phase 28: KE Gene SPARQL Returns Symbols` → `### Phase 28: KE Gene SPARQL Returns Persistent Identifiers`

Goal: rewritten to describe the strict-triple `{ncbi, hgnc, symbol}` design, single non-federated SPARQL query, dict-shape downstream consumers, and `genes_full` API addition with `genes` backward-compat for Phase 27.

Requirements: `TBD (to be added during planning - likely a new KEGENE-01 requirement)` → `KEGENE-01`.

Context bullets reformulated to highlight: (1) a325411 regression date, (2) silent gene-overlap zeroing, (3) persistent-IDs rationale (HGNC renames like C11orf95→ZFTA), (4) live SPARQL probe results from 2026-05-07 (96.4% coverage; 100% on test KEs).

Success Criteria expanded from 6 symbols-focused assertions to 7 testable assertions:
1. Helper returns `List[Dict[str, str]]` strict-shape, partials dropped silently (D-04).
2. `/ke_genes/<ke_id>` returns both `genes` (legacy) and `genes_full` (new).
3. WP `_find_pathways_by_genes` returns non-empty results for overlapping KEs.
4. Reactome `_compute_gene_overlap_scores` produces non-zero `gene_overlap`.
5. GO `_compute_gene_overlap_scores_for` produces non-zero gene-driven scores.
6. Phase 27 `flagItems()` continues receiving symbol strings (no frontend regression).
7. SPARQL response cache auto-invalidates via version-comment trick (no DB migration).

Plans: `TBD` → explicit list of 4 plans (28A through 28D) with one-line objectives each.

### ROADMAP.md — Edit 3: Progress-table row

Was: `| 28. KE Gene SPARQL Returns Symbols | v1.4 | 0/0 | Not Started | — |`

Now: `| 28. KE Gene SPARQL Returns Persistent Identifiers | v1.4 | 0/4 | Not Started | — |`

### REQUIREMENTS.md — Edit 1: New Helper Library section

Inserted after `### Viewer / RVIEW-01`, before `## Future Requirements`:

```markdown
### Helper Library

- [ ] **KEGENE-01**: `get_genes_from_ke()` returns a strict-shape `List[Dict[str, str]]` with fields `{ncbi, hgnc, symbol}` (NCBI Gene ID + HGNC accession + HGNC symbol), sourced from a single non-federated AOP-Wiki SPARQL query; the public `GET /ke_genes/<ke_id>` adds a `genes_full` dict-list field while preserving `genes` as `[symbol]` for Phase 27 backward-compat; downstream gene-overlap signals across Reactome, WP, and GO suggestion services become non-empty for KEs with overlapping genes
```

### REQUIREMENTS.md — Edit 2: Traceability table row

Appended after `RVIEW-01 | Phase 27 | Pending`:

```
| KEGENE-01 | Phase 28 | Pending |
```

### REQUIREMENTS.md — Edit 3: Coverage block

Was: `v1.4 requirements: 17 total / Mapped to phases: 17`

Now: `v1.4 requirements: 18 total / Mapped to phases: 18`

### REQUIREMENTS.md — Edit 4: Footer date

Was: `*Last updated: 2026-03-11 after roadmap creation (all 17 requirements mapped)*`

Now: `*Last updated: 2026-05-07 after Phase 28 redefinition (KEGENE-01 added; all 18 requirements mapped)*`

(`*Requirements defined: 2026-03-11*` line preserved unchanged.)

## KEGENE-01 — Final Wording

> **KEGENE-01**: `get_genes_from_ke()` returns a strict-shape `List[Dict[str, str]]` with fields `{ncbi, hgnc, symbol}` (NCBI Gene ID + HGNC accession + HGNC symbol), sourced from a single non-federated AOP-Wiki SPARQL query; the public `GET /ke_genes/<ke_id>` adds a `genes_full` dict-list field while preserving `genes` as `[symbol]` for Phase 27 backward-compat; downstream gene-overlap signals across Reactome, WP, and GO suggestion services become non-empty for KEs with overlapping genes

Wording rationale: covers both the internal contract (helper return type + downstream non-empty signals across all three suggestion services) and the external contract (`genes_full` API field with explicit Phase 27 backward-compat clause) in one verifiable statement; matches the Success Criteria block in the ROADMAP entry without restating each criterion.

## Decisions Made

1. **Plan list shape** — used a four-bullet `Plans:` list mirroring the convention of completed phases (e.g. Phase 23, 24, 25), rather than the older `**Plans**: TBD` style. Each bullet has a one-line objective extracted from the plan-file `<objective>` blocks.
2. **Helper Library as new section heading** — chose a dedicated `### Helper Library` section over folding KEGENE-01 into an existing section (e.g. Suggestion Engine), because the helper is shared by three services and lives outside the suggestion-engine module hierarchy.
3. **Traceability row append-only** — preserved the historical insertion order of all 17 prior rows; KEGENE-01 added at the end. Status marked `Pending` (consistent with RVIEW-01's status convention while its plan is in flight).
4. **Footer date semantics** — kept `*Requirements defined: 2026-03-11*` unchanged (records initial definition); updated `*Last updated*` to today and named the trigger event ("Phase 28 redefinition").

## Deviations from Plan

None — plan executed exactly as written. All four edits in REQUIREMENTS.md and three edits in ROADMAP.md applied as specified; all acceptance grep checks passed on first run.

## Verification

All Task 1 acceptance criteria PASS:
- `Phase 28: KE Gene SPARQL Returns Persistent Identifiers` present in ROADMAP.md
- `Requirements**: KEGENE-01` linked
- Four `28[A-D]-PLAN.md` references (count = 4)
- Progress row shows `0/4 | Not Started`
- Old title `KE Gene SPARQL Returns Symbols` (anchored) fully removed
- Prior milestone summaries (v1.0 MVP, v1.3 GO Assessment Quality) intact

All Task 2 acceptance criteria PASS:
- KEGENE-01 present 3 times (definition, traceability row, plus appears as part of one frontmatter line)
- `### Helper Library` section heading present
- `| KEGENE-01 | Phase 28 | Pending |` row exact-match
- `v1.4 requirements: 18 total` and `Mapped to phases: 18`
- Existing requirements (RVIEW-01, REXP-04) and deferred sections (Future Requirements, Out of Scope) intact

Cross-file consistency PASS: KEGENE-01 referenced in both ROADMAP.md (Requirements field) and REQUIREMENTS.md (definition + traceability).

## Commits

- `a24fc2e` — docs(28): rewrite ROADMAP Phase 28 entry
- `692b5cf` — docs(28): add KEGENE-01 to REQUIREMENTS

## Self-Check: PASSED

- File `.planning/ROADMAP.md` exists and contains rewritten Phase 28 block.
- File `.planning/REQUIREMENTS.md` exists and contains KEGENE-01 in three locations (section, traceability, frontmatter-style line).
- Commit `a24fc2e` exists in `git log`.
- Commit `692b5cf` exists in `git log`.
- Grep acceptance criteria all pass on disk.
