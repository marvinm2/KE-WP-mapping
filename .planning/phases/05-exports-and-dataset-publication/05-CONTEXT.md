# Phase 5: Exports and Dataset Publication - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The curated KE-WP and KE-GO mapping database is packaged into downloadable formats that bioinformatics tools (clusterProfiler, fgsea, rdflib) consume directly — two GMT files and two RDF/Turtle files — and registered on Zenodo with a citable DOI via automated API. Creating the mappings themselves and the public read API are already complete; this phase is purely about export packaging and dataset publication.

</domain>

<decisions>
## Implementation Decisions

### GMT file content
- Term name (column 1): `KE{ID}_{Name_slug}` format — e.g. `KE55_Decreased_BDNF` (stable ID + human-readable slug)
- Gene columns: Claude's discretion — use whichever gene identifier (HGNC symbols vs Entrez IDs) is standard for WikiPathways GMT exports and most compatible with clusterProfiler/fgsea out of the box
- KE-GO gene columns: Claude's discretion — populate with genes annotated to the GO term, in whatever form makes the GMT loadable by clusterProfiler/fgsea without preprocessing
- Description field (column 2): Claude's discretion — follow standard bioinformatics GMT convention for this field

### Export delivery
- Architecture: On-demand API endpoints that also write/serve a cached static file
- Cache refresh: Manual — admin-only regeneration endpoint (button or URL) triggers file rebuild
- Authentication: Fully public — no login required to download any export
- UI surfaces: Download links on both the existing `/stats` page AND a new `/downloads` page
- Confidence filtering: Configurable via `?min_confidence=High` query param (extends existing API filter pattern)
- Filename encoding: Date + confidence in filename (e.g. `KE-WP_2026-02-21_High.gmt`) for self-documentation when saved locally
- Downloads page design: Claude's discretion — match existing page style

### RDF/Turtle structure
- Richness: Full provenance included — approver GitHub username, approval timestamp, suggestion_score, confidence level, UUID
- Vocabularies: Custom `ke-wp:` namespace for domain concepts + `dcterms:` for provenance metadata (no assumed ontology semantics)
- Provenance encoding: Claude's discretion — use whichever pattern (RDF-star, named graphs, or reification) rdflib parses cleanly
- File split: Two separate files — `ke-wp-mappings.ttl` and `ke-go-mappings.ttl` (mirrors GMT pattern)

### Zenodo registration
- Deposit method: Automated via Zenodo API — admin triggers from within the app; requires `ZENODO_API_TOKEN` env var
- Deposit contents: Both GMT files + both Turtle files + a README describing the database
- Versioning trigger: Admin-explicit "Publish new version" button in the admin panel
- DOI display location: Homepage/navbar — prominent citation visible across the entire app

### Claude's Discretion
- Gene identifier format for GMT gene columns (HGNC symbols vs Entrez IDs)
- GMT description field content
- RDF provenance encoding mechanism (RDF-star vs named graphs vs reification)
- Downloads page layout and styling (match existing UI)

</decisions>

<specifics>
## Specific Ideas

- Filename convention: `KE-WP_2026-02-21_High.gmt` pattern — date + confidence tier, self-documenting when researchers save locally
- Zenodo deposit includes a README so the record is citation-quality (not just files with no context)
- DOI badge in navbar — curators see the live citation wherever they are in the app

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-exports-and-dataset-publication*
*Context gathered: 2026-02-21*
