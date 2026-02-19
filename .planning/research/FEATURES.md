# Feature Research

**Domain:** Biological database curation tools / pathway annotation platforms
**Researched:** 2026-02-19
**Confidence:** HIGH

## Context

Two distinct user groups shape this feature landscape:

- **Curators** (AOP domain experts): Approve or reject AI suggestions linking Key Events to WikiPathways and GO Biological Process terms. They need a fast, trustworthy workflow that surfaces the right context at the right moment.
- **Bioinformaticians** (downstream consumers): Pull the curated mapping database into R/Python workflows for pathway enrichment analysis, toxicological screening, AOP network construction. They need reliable, stable, well-documented programmatic access.

Reference databases studied: WikiPathways, Reactome, AOP-Wiki, ChEMBL, UniProt, AOP-DB (EPA), Gene Ontology resource, MSigDB. Tooling studied: rWikiPathways (Bioconductor), clusterProfiler, fgsea, GOATOOLS, AnnotationDbi, BioKC, Web Apollo.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Browse / explore approved mappings | Every annotation database (UniProt, Reactome, GO) provides a searchable table or portal view. Curators and consumers expect to see what has been approved. | LOW | Partially implemented as `/explore` with DataTables. Needs filtering by AOP, KE, pathway, GO term. |
| Filter and search the mapping table | Standard UX in any database portal (ChEMBL, AOP-Wiki, RCSB PDB). Users filter by entity type, organism, confidence level. | LOW | DataTables client-side filtering exists. Server-side filtering needed for scale. |
| Stable, versioned dataset download | WikiPathways ships monthly GMT/RDF releases. Reactome publishes versioned BioPAX dumps. Bioinformaticians pin to a specific release for reproducibility. | LOW-MEDIUM | CSV/JSON/RDF export exists. Needs version stamps and stable release identifiers. |
| CSV and TSV export | Absolute minimum for any annotation database. Every bioinformatics lab uses Excel or pandas for ad hoc analysis. | LOW | CSV exists. TSV should also be supported. |
| JSON export | R `jsonlite` and Python `requests`+`json` are first tools bioinformaticians reach for. JSON is the default API response format across all modern databases (ChEMBL, UniProt, WikiPathways JSON API). | LOW | Implemented. Verify schema is stable and documented. |
| Citable dataset with persistent identifier | Nature Scientific Data and journals expect databases to have a DOI. Downstream papers will cite this database; they need something stable to cite. | LOW-MEDIUM | `/dataset/citation` and `/dataset/datacite` endpoints exist. Need to confirm DOI is registered (Zenodo) and citation format is complete. |
| Dataset version metadata endpoint | Bioinformaticians need to know what version they are consuming. WikiPathways JSON API exposes release dates. | LOW | `/dataset/versions` exists. Needs a changelog-style release notes field. |
| Documented REST API | "Eleven quick tips to build a usable REST API for life sciences" (EMBL-EBI, PLOS Comp Bio 2018) is the community reference. OpenAPI/Swagger docs are expected by any API-consuming bioinformatician. | MEDIUM | Issue #31 (comprehensive REST API) is in the post-v1 backlog. For v1, at minimum the existing endpoints need to be documented. |
| Confidence level on each mapping | AOP-Wiki records evidence strength. Reactome records experimental evidence vs. inference. Curators and consumers need to filter by quality. | LOW | Confidence scores (High/Medium/Low) are captured in the assessment workflow. Need to expose these in the explore view and API. |
| Unique stable identifiers for mappings | Downstream tools and papers need to reference specific KE-WP or KE-GO mappings by ID. ChEMBL, UniProt, Reactome all assign stable accession IDs. | LOW | SQLite row IDs exist. Need to expose mapping IDs in UI and API responses. |
| Indication of which KEs have no mapping yet | Curators need to know coverage gaps. AOP-DB and AOP-Wiki show completeness indicators. | LOW | Not currently visible in the UI. A simple uncovered-KE count or list would suffice. |
| Health check and status endpoint | Any production service exposed to consumers needs a `/health` endpoint so monitoring tools and downstream scripts can confirm availability. | LOW | `/health` implemented. Needs to be documented. |

### Differentiators (Competitive Advantage)

Features that set this tool apart within the AOP/toxicology domain.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| GMT export of KE-pathway mappings | WikiPathways GMT is consumed directly by `clusterProfiler::enrichWP()`, `fgsea`, and GSEA software. A KE-specific GMT file would let toxicologists run pathway enrichment on AOP gene sets without any data wrangling. This is a unique, high-value deliverable that no existing tool offers in this form. | LOW | Map: KE name as term, WikiPathways gene list (from SPARQL) as gene set. One endpoint, massive downstream utility. |
| GMT export of KE-GO mappings | Same logic as above: `clusterProfiler::enrichGO()` accepts custom term-to-gene mappings. A KE-GO GMT lets bioinformaticians test whether an omics experiment hits AOP-relevant GO terms. | LOW | Depends on approved KE-GO mappings. The gene annotation data already exists in `data/go_bp_gene_annotations.json`. |
| AI suggestion engine with explainable scores | Reactome and WikiPathways have no suggestion engine — curators propose manually. Having BioBERT + gene overlap + text scoring, with the score breakdown visible to curators, is a genuine differentiator. Curators can see why a mapping is suggested. | MEDIUM | Score breakdown exists in backend. Needs to be surfaced in the suggestion card UI for curators. |
| AOP context in the curation UI | No other pathway database knows about AOP structure. Showing the curator which AOPs a KE belongs to, what other KEs are adjacent in the pathway, and what mappings already exist for sibling KEs dramatically reduces lookup time. | MEDIUM | KE context panel (issue #99) is now closed/done. Verify it shows adjacent KEs and existing mappings. |
| Dual mapping (WP + GO) with cross-validation signal | A KE mapped to both a WikiPathway and GO terms creates an implicit consistency check — the GO terms should be enriched in the WikiPathway gene list. Exposing this consistency signal as a quality indicator is unique to this tool. | HIGH | Requires post-approval cross-validation logic. v2+ feature. |
| Curator-specific curation statistics | Show each curator how many mappings they have approved, their confidence distribution, and their approval rate for suggestions. Encourages quality and accountability without introducing adversarial dynamics. | MEDIUM | Not currently implemented. Requires per-user attribution on approved mappings. |
| Bulk mapping review for related KEs | AOPs have families of related KEs (same stressor, same organ, adjacent in the AOP graph). Allowing curators to review suggestions for a whole AOP at once, or filter by stressor category, dramatically reduces repetitive context-switching. | HIGH | Not implemented. Requires AOP-level batch view. |
| Machine-readable provenance for each mapping | FAIR data principles (Findable, Accessible, Interoperable, Reusable) require provenance: who curated it, when, what evidence supported it, what AI score was presented. This enables reproducibility auditing for regulatory submissions. | MEDIUM | Timestamps and curator identity are stored. Need to expose in API and export. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time collaborative editing (multiple curators, same KE, simultaneously) | Large-scale databases like AOP-Wiki have many contributors. Seems like a natural scaling feature. | Conflict resolution, locking, and UI complexity are very high. SQLite concurrent writes are already a risk. The curator team for v1 is small. | Proposal workflow with admin review is already the right pattern. If simultaneous edits become a real problem, add a "mapping claimed" lock with a timeout. |
| User-contributed custom KE lists or private mapping sets | Users ask for personal workspaces / draft mappings. | This bifurcates the curated database: public vs. private. Downstream consumers cannot trust any mapping's provenance. Hosting private data introduces GDPR / data governance complexity. | The proposal workflow already gives curators a private-to-approved pipeline. Draft proposals that are not yet submitted are the correct abstraction. |
| Full-text search across pathway descriptions and literature | Reactome has literature search. Seems powerful. | Requires either a search index (Elasticsearch) or slow full-text SQLite queries. Adds operational complexity. For v1, the user base is small enough that structured filters are sufficient. | Faceted filtering by KE, AOP, pathway ID, GO term ID, confidence, and organism covers 95% of use cases. Add full-text search in v2 if curators ask for it. |
| GraphQL API | Some modern bioinformatics APIs use GraphQL (BioThings). Seen as more flexible than REST. | The bioinformatics community standard is REST + OpenAPI. R packages like `rWikiPathways`, `httr`, and Python `requests` are built around REST. GraphQL adds client complexity with no benefit at this data scale. | REST with well-documented filtering parameters (organism, confidence, AOP ID) covers all known query patterns. |
| Automated mapping without human approval | If AI scores are high enough, auto-approve. Reduces curator burden. | Defeats the scientific purpose of the tool. The value of this database is that every mapping is human-validated. Auto-approval would make this indistinguishable from a raw embedding output. | Retain human-in-the-loop. Instead, reduce curator friction: pre-sort the suggestion queue by score, batch review for related KEs. |
| Pathway image rendering in the export | Curators and consumers sometimes ask for GPML or SVG pathway diagrams to be bundled with exports. | GPML is a WikiPathways-specific format; managing its generation and keeping it current adds significant maintenance burden. Images inflate download size. | Link to WikiPathways and GO term pages in exports (external URLs). This is what Reactome does for cross-references — they link, they don't embed. |

---

## Feature Dependencies

```
[GMT Export (KE-WP)]
    └──requires──> [Approved KE-WP Mappings with pathway gene lists]
                       └──requires──> [WikiPathways SPARQL gene list fetching — already implemented]

[GMT Export (KE-GO)]
    └──requires──> [Approved KE-GO Mappings]
                       └──requires──> [go_bp_gene_annotations.json — already loaded]

[Provenance in API]
    └──requires──> [Per-mapping curator attribution stored in DB]
                       └──requires──> [GitHub username stored on approval — check current schema]

[Curator statistics]
    └──requires──> [Per-mapping curator attribution stored in DB]

[Cross-validation signal (WP + GO consistency)]
    └──requires──> [GMT Export (KE-WP)]
    └──requires──> [GMT Export (KE-GO)]
    └──requires──> [Gene overlap computation logic — partial in pathway.py]

[Coverage gap view (uncovered KEs)]
    └──requires──> [ke_metadata.json — already loaded (1561 KEs)]
    └──requires──> [Approved mapping set — already in DB]

[Versioned dataset release]
    └──requires──> [Stable dataset metadata (version, date, DOI)]
    └──enhances──> [CSV/JSON/GMT exports]

[OpenAPI documentation]
    └──enhances──> [All existing API endpoints]
    └──requires──> [Stable endpoint contracts — do not rename routes after documenting]
```

### Dependency Notes

- **GMT export requires approved mappings**: The KE-WP GMT file is only useful once a meaningful number of KE-WP mappings are approved. This is a chicken-and-egg situation: bioinformaticians will not use the tool until the GMT exists, but the GMT cannot exist until curators have used the tool. For v1, seed the GMT with initial curated mappings and document that it will grow.
- **Provenance in API requires DB schema check**: The `mappings` and `ke_go_mappings` tables must store `curator_github` (the GitHub username of the approving admin) at the time of approval. Verify this is captured in `src/blueprints/admin.py` at approval time.
- **OpenAPI conflicts with route instability**: Documenting API endpoints before the routes are stable creates maintenance debt. Finalize routes before writing OpenAPI spec.
- **Bulk AOP review enhances curator statistics**: Both features require per-KE, per-AOP aggregate views of the mapping database. They share the same query infrastructure.

---

## MVP Definition

### Launch With (v1.0.0)

Minimum to deploy and hand off to the research project team and external collaborators.

- [x] Working suggestion engine (BioBERT + gene + text scoring) — DONE
- [x] Curation workflow: submit -> admin review -> approve/reject — DONE
- [x] Explore / browse approved mappings — DONE (basic)
- [ ] Filter explore view by AOP ID, KE ID, pathway ID, GO term, confidence level — NEEDED
- [x] CSV/JSON/RDF export — DONE
- [ ] TSV export — MINOR, add to existing export endpoint
- [ ] GMT export (KE-WP mappings as gene sets) — HIGH VALUE, LOW EFFORT
- [ ] Stable dataset DOI registered on Zenodo — NEEDED for citability
- [ ] Confidence level visible on each mapping in the explore table — NEEDED
- [ ] Mapping IDs exposed in UI and in all API responses — NEEDED for reference
- [ ] At minimum a human-readable API documentation page (the existing `/documentation` section can host this) — NEEDED
- [ ] Coverage gap: a simple count/list of uncovered KEs — LOW EFFORT, HIGH CURATOR VALUE

### Add After Validation (v1.x)

Add once the tool is actively used and patterns emerge.

- [ ] GMT export (KE-GO mappings) — add once KE-GO mapping volume is sufficient
- [ ] OpenAPI/Swagger spec for all endpoints — add once routes are stable post-launch
- [ ] Curator attribution in API responses and exports — requires DB schema addition
- [ ] Curator statistics dashboard (mappings per curator, confidence distribution) — needs user adoption first
- [ ] Versioned dataset releases with changelog notes — once release cadence is established
- [ ] Score breakdown visible on suggestion cards (why was this suggested?) — needs UX design

### Future Consideration (v2+)

Defer until product-market fit and user base are established.

- [ ] Bulk AOP-level curation review — high complexity, needs real usage data to design well
- [ ] ORCID/SURF federation auth — issue #101, important for institutional users
- [ ] Cross-validation signal (WP+GO consistency check) — depends on having both mapping sets populated
- [ ] Literature mining for evidence-based suggestions — issue #27, significant ML work
- [ ] KEGG Pathways integration — issue #25, significant scope expansion
- [ ] GO hierarchy integration for term ranking — issue #80

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Filter explore view by AOP/KE/pathway/confidence | HIGH (curators and consumers both need it) | LOW (DataTables + server-side filters) | P1 |
| GMT export (KE-WP) | HIGH (direct clusterProfiler/fgsea integration) | LOW (mapping query + gene list fetch) | P1 |
| Confidence visible in explore table | HIGH (table stakes for any annotation DB) | LOW (column already in DB) | P1 |
| Stable mapping IDs in UI and API | HIGH (needed for citations and cross-refs) | LOW | P1 |
| Dataset DOI / Zenodo registration | HIGH (required for publication) | MEDIUM (external process, one-time setup) | P1 |
| TSV export | MEDIUM (nice for spreadsheet users) | LOW (add to existing export endpoint) | P2 |
| Coverage gap view (uncovered KEs) | MEDIUM (curator workflow aid) | LOW (join ke_metadata vs. mappings) | P2 |
| API documentation page | HIGH (mandatory for external consumers) | MEDIUM (prose writing + endpoint listing) | P1 |
| OpenAPI/Swagger spec | MEDIUM (useful for programmatic clients) | MEDIUM (route annotation) | P2 |
| GMT export (KE-GO) | HIGH (when KE-GO volume exists) | LOW | P2 |
| Curator attribution in exports | MEDIUM (provenance / FAIR) | LOW-MEDIUM (DB schema + export update) | P2 |
| Score breakdown on suggestion cards | MEDIUM (curator trust-building) | MEDIUM (UI addition to suggestion cards) | P2 |
| Curator statistics dashboard | LOW-MEDIUM (engagement / accountability) | MEDIUM | P3 |
| Versioned dataset releases | MEDIUM (reproducibility) | MEDIUM | P2 |
| Bulk AOP curation review | HIGH (curator efficiency at scale) | HIGH | P3 |
| Cross-validation signal (WP+GO) | MEDIUM (quality signal) | HIGH | P3 |
| ORCID federation auth | MEDIUM (institutional users) | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.0.0 launch
- P2: Should have, add in v1.x after launch
- P3: Nice to have, defer to v2+

---

## Competitor Feature Analysis

| Feature | WikiPathways | Reactome | AOP-Wiki | Our Approach |
|---------|--------------|----------|----------|--------------|
| Browse/search mappings | Yes — pathway browser, text search | Yes — pathway hierarchy browser | Yes — KE list with filters | Explore page with DataTables (needs filter improvement) |
| Export formats | GMT, GPML, RDF, SVG (monthly releases) | BioPAX, SBML, SBGN, JSON (versioned) | XML, RDF/SPARQL (live endpoint) | CSV, JSON, RDF — add GMT |
| REST API | JSON API + SPARQL endpoint + OpenAPI via webservice | REST content service + OpenAPI | SPARQL only | Existing endpoints + need docs |
| R package | rWikiPathways (Bioconductor) | ReactomePA (Bioconductor) | None | Not needed for v1; GMT file enables clusterProfiler directly |
| Python package | None (use REST) | reactome2py | None | Not needed; REST + GMT covers it |
| Confidence/evidence coding | Curator review required; no per-mapping score | Evidence codes + literature references per reaction step | Weight of Evidence scoring for KERs | High/Medium/Low confidence from 4-question assessment — this is solid |
| Dataset citation / DOI | Monthly releases on Zenodo with DOI | Zenodo releases with DOI | AOP-Wiki SPARQL as living endpoint | Planned via /dataset/datacite; needs Zenodo registration |
| Suggestion engine | None — fully manual curation | None — fully manual by PhD biocurators | None | BioBERT + gene + text scoring — UNIQUE |
| AOP context | No AOP concept | No AOP concept | Native AOP structure | KE context panel — UNIQUE differentiator |
| Curation workflow | GitHub PR-based community contribution | Internal curator team + expert reviewer | Wiki-style with community edit | Proposal → admin approve/reject — appropriate for this scale |
| Audit trail | Git history for pathway files | Internal versioning | Wiki history | Timestamps + curator attribution (needs to be surfaced) |

---

## Sources

- [WikiPathways JSON API](https://www.wikipathways.org/json/)
- [WikiPathways 2024: next generation pathway database (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10767877/)
- [rWikiPathways Bioconductor — Pathway Analysis vignette](https://r.wikipathways.org/articles/Pathway-Analysis.html)
- [Reactome Download Data](https://reactome.org/download-data)
- [Reactome Content Service (REST API)](https://reactome.org/dev/content-service)
- [BioPAX in 2024 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11585474/)
- [Eleven quick tips to build a usable REST API for life sciences (PLOS Comp Bio)](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006542)
- [AOP-networkFinder (Bioinformatics Advances 2025)](https://academic.oup.com/bioinformaticsadvances/article/5/1/vbaf007/7972740)
- [Providing AOP-Wiki in Semantic Web Format (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8978481/)
- [A curated gene and biological system annotation of AOPs (Nature Sci Data)](https://www.nature.com/articles/s41597-023-02321-w)
- [BioKC: collaborative platform for curation and annotation (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10972550/)
- [Ten quick tips for biocuration (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6497217/)
- [ChEMBL Data Web Services documentation](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)
- [The UniProt website API (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12230682/)
- [GOATOOLS: Python library for Gene Ontology analyses (Nature Sci Reports)](https://www.nature.com/articles/s41598-018-28948-z)
- [JASPAR RESTful API (Bioinformatics)](https://academic.oup.com/bioinformatics/article/34/9/1612/4747882)
- [Zenodo FAIR data deposition guide](https://fairplus.github.io/the-fair-cookbook/content/recipes/findability/zenodo-deposition.html)
- [Introducing WikiPathways to support AOPs (PubMed)](https://pubmed.ncbi.nlm.nih.gov/30622555/)
- [Comprehensive mapping of AOP-Wiki database (Frontiers Toxicology 2024)](https://www.frontiersin.org/journals/toxicology/articles/10.3389/ftox.2024.1285768/full)

---
*Feature research for: biological pathway curation tool / AOP-KE mapping database*
*Researched: 2026-02-19*
