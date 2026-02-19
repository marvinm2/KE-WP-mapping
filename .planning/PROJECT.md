# KE-WP / KE-GO Mapping Tool

## What This Is

A web-based curation tool that lets toxicologists and AOP researchers select Key Events (KEs) from Adverse Outcome Pathways (AOPs) and semi-automatically build a curated database of KE→WikiPathways and KE→GO term mappings. The tool suggests mappings using BioBERT embeddings and multi-signal scoring; curators approve or reject each suggestion. The resulting database is accessible via API and file exports for downstream bioinformatics analysis.

## Core Value

Curators can efficiently produce a high-quality, reusable KE-pathway/GO mapping database that external tools can consume for toxicological pathway analysis.

## Requirements

### Validated

<!-- Shipped and confirmed working in the existing prototype. -->

- ✓ Pre-loaded KE list (1561 Key Events from AOP-Wiki) — existing
- ✓ AI-powered KE→WikiPathways suggestion engine (BioBERT embeddings + gene + text + ontology signals) — existing
- ✓ AI-powered KE→GO Biological Process suggestion engine (gene annotation + embedding signals) — existing
- ✓ Human curation workflow: submit proposal → admin approve/reject — existing
- ✓ SQLite persistence for approved KE-WP and KE-GO mappings — existing
- ✓ GitHub OAuth authentication + guest access codes — existing
- ✓ Admin dashboard for proposal review — existing
- ✓ Basic explore page (browse approved mappings) — existing
- ✓ File exports: CSV, JSON, Parquet — existing
- ✓ SPARQL caching, rate limiting, CSRF protection — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] Polished curation UX — streamlined KE selection, suggestion review, and submission flow
- [ ] Enhanced explore/browse — filter and search approved mappings by KE, AOP, pathway, GO term
- [ ] Structured REST API — documented endpoints for programmatic access to the curated database
- [ ] Curation quality tools — bulk review, edit/update existing mappings, confidence indicators
- [ ] Production deployment — containerized, stable, accessible to external collaborators

### Out of Scope

<!-- Explicit boundaries. -->

- KE→Gene direct mappings — not a primary output; genes are used internally as a matching signal only
- Real-time AOP-Wiki sync — KE metadata is pre-loaded; live querying is a future concern
- User-contributed pathway databases beyond WikiPathways/GO — focus on established ontologies for v1
- Mobile native app — web-first

## Context

This is a maturing prototype. The core suggestion engine (BioBERT embeddings, multi-signal scoring) and curation workflow (proposals, admin approval) are fully functional. The codebase uses Flask blueprints with a service container for dependency injection. Pre-computed embeddings live in `data/` (~230MB). SQLite is the database.

The primary gap between prototype and v1.0 is quality of the curation experience (UI/UX), completeness of the access layer (REST API + exports), and workflow tooling for maintaining the mapping database at scale.

Target milestone: tool deployed and actively used in a published research project.

## Constraints

- **Tech stack**: Python/Flask — no framework migration
- **Database**: SQLite for v1 — migration to PostgreSQL is a future concern
- **Embeddings**: Pre-computed BioBERT; regeneration requires scripts in `scripts/`
- **Auth**: GitHub OAuth for curators; guest codes for workshop participants
- **Deployment**: Docker/Gunicorn; minimum 4GB RAM for embedding service

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| BioBERT embeddings for semantic matching | Domain-specific biological text encoder outperforms general models | ✓ Good — <1s response after precompute |
| Multi-signal scoring (gene + embedding + text + ontology) | Combines complementary signals for higher precision | ✓ Good — 23x speedup with batch processing |
| Pre-curated KE list vs live SPARQL | Avoids latency and rate-limit issues with AOP-Wiki | ✓ Good — reliable, fast dropdowns |
| SQLite for v1 | Sufficient for curator team scale; simplifies deployment | — Pending (watch for concurrent-write limits) |
| GitHub OAuth | Low-friction auth for scientific community | ✓ Good |

---
*Last updated: 2026-02-19 after initialization*
