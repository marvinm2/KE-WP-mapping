# Phase 5: Exports and Dataset Publication - Research

**Researched:** 2026-02-21
**Domain:** GMT file generation, RDF/Turtle export, Zenodo API deposit, Flask caching patterns
**Confidence:** HIGH (core stack confirmed against live docs and codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **GMT term name (col 1):** `KE{ID}_{Name_slug}` format — e.g. `KE55_Decreased_BDNF`
- **Export delivery architecture:** On-demand API endpoints that also write/serve a cached static file
- **Cache refresh:** Manual — admin-only regeneration endpoint triggers file rebuild
- **Authentication for downloads:** Fully public — no login required
- **UI surfaces:** Download links on both existing `/stats` page AND a new `/downloads` page
- **Confidence filtering:** `?min_confidence=High` query param
- **Filename encoding:** Date + confidence in filename (e.g. `KE-WP_2026-02-21_High.gmt`)
- **RDF richness:** Full provenance — approver GitHub username, approval timestamp, suggestion_score, confidence level, UUID
- **RDF vocabularies:** Custom `ke-wp:` namespace + `dcterms:` for provenance metadata
- **RDF file split:** Two files — `ke-wp-mappings.ttl` and `ke-go-mappings.ttl`
- **Zenodo deposit method:** Automated via Zenodo API from within the app; `ZENODO_API_TOKEN` env var
- **Zenodo deposit contents:** Both GMT files + both Turtle files + a README
- **Zenodo versioning trigger:** Admin "Publish new version" button in admin panel
- **DOI display:** Homepage/navbar — visible across entire app

### Claude's Discretion

- Gene identifier format for GMT gene columns (HGNC symbols vs Entrez IDs)
- GMT description field (column 2) content
- RDF provenance encoding mechanism (RDF-star vs named graphs vs reification)
- Downloads page layout and styling (match existing UI)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXPRT-01 | GMT format export for KE-WP mappings, directly loadable by clusterProfiler/fgsea without preprocessing | GMT spec section, gene identifier decision, KE-WP data flow from `mappings` table + WikiPathways SPARQL for pathway gene lists |
| EXPRT-02 | GMT format export for KE-GO mappings | Same GMT spec; gene columns populated from `data/go_bp_gene_annotations.json` (pre-computed, HGNC symbols) |
| EXPRT-03 | RDF/Turtle export of the full curated mapping database | rdflib 6.3.2 already installed; reification pattern section; both KE-WP and KE-GO tables have all required provenance columns |
| EXPRT-04 | Dataset published on Zenodo with a DOI for use as a publication citation | Zenodo REST API workflow section; Python `requests` already in requirements.txt |
</phase_requirements>

---

## Summary

Phase 5 adds four export/publication deliverables to an already-functional Flask app. Two GMT files (KE-WP and KE-GO) are the primary bioinformatics outputs; two Turtle files add semantic web provenance; Zenodo publication gives a citable DOI. All required libraries are already installed (`rdflib 6.3.2`, `requests 2.32.5`). The only new dependency is a `ZENODO_API_TOKEN` environment variable.

The critical design choice is the caching architecture: exports are generated on-demand by hitting an endpoint, written to a static directory, and served from that cache on subsequent requests. Admin regeneration wipes and rewrites the cache. This avoids blocking the main request thread on expensive DB + SPARQL queries for every download.

The KE-WP GMT gene column requires a live WikiPathways SPARQL query per pathway to fetch gene lists (HGNC symbols are in `wp:bdbHgncSymbol` — same query already used in `src/suggestions/pathway.py`). The KE-GO GMT gene column is cheaper: gene lists are already in `data/go_bp_gene_annotations.json`. Both should use HGNC symbols, which is the format clusterProfiler/fgsea and fgsea accept and what the codebase already uses throughout.

**Primary recommendation:** Build exports as a new `src/exporters/gmt_exporter.py` + `src/exporters/zenodo_uploader.py`, add `/exports/` blueprint routes (or extend `main_bp`), cache files to `static/exports/`, and add admin-only regeneration + Zenodo publish routes to `admin_bp`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdflib | 6.3.2 (already installed) | Build RDF graphs, serialize to Turtle | De-facto Python RDF library; `g.serialize(format="turtle")` works out of the box |
| requests | 2.32.5 (already installed) | HTTP calls to Zenodo API | Already in requirements; Zenodo official docs use requests |
| Python stdlib `re`, `unicodedata` | stdlib | Slug generation for GMT col 1 names | No extra dependency needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `io.StringIO` | stdlib | In-memory GMT file assembly before write | Avoids temp files; same pattern as existing `/download` endpoint |
| `pathlib.Path` | stdlib | Cache file path construction | Clean cross-platform path handling |
| `datetime` | stdlib | Date stamp in filenames, RDF timestamps | Already used throughout codebase |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain `requests` for Zenodo | `zenodo-client` PyPI package | `zenodo-client` is a thin wrapper; using `requests` directly keeps dependency count low and gives full control over the new versioning workflow |
| rdflib Graph (simple Turtle) | rdflib ConjunctiveGraph / TriG format | Named graphs require TriG format, not Turtle; decision is reification in plain Turtle (see Architecture Patterns) |
| HGNC symbols in GMT | Entrez IDs in GMT | WikiPathways official GMT uses Entrez IDs, but the entire codebase (SPARQL queries, GO annotations, ke_genes service) uses HGNC symbols; fgsea accepts either if consistent |

**Installation:** No new pip installs needed. Add `ZENODO_API_TOKEN` to `.env.example`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── exporters/
│   ├── gmt_exporter.py       # NEW — KE-WP and KE-GO GMT file generation
│   ├── rdf_exporter.py       # EXISTING — will be REPLACED with new version
│   └── zenodo_uploader.py    # NEW — Zenodo deposit workflow
static/
└── exports/                  # NEW — cache directory for generated files
templates/
└── downloads.html            # NEW — /downloads page
src/blueprints/
├── main.py                   # ADD /downloads route, /exports/gmt/<type> routes
└── admin.py                  # ADD /admin/exports/regenerate, /admin/exports/publish-zenodo
```

### Pattern 1: On-Demand Cache + Serve

**What:** Request hits endpoint → if cached file exists, serve it; if not, generate and cache → serve.

**When to use:** For all four export files (two GMT, two Turtle).

```python
# Source: codebase existing /download pattern + stdlib pathlib
from pathlib import Path
import os

EXPORT_CACHE_DIR = Path("static/exports")

def _get_cached_export(filename: str):
    """Return path to cached file, or None if not cached."""
    path = EXPORT_CACHE_DIR / filename
    return path if path.exists() else None

def _write_export_cache(filename: str, content: str):
    EXPORT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (EXPORT_CACHE_DIR / filename).write_text(content, encoding="utf-8")
```

**Admin regeneration:** DELETE all files in `static/exports/`, then regenerate all four.

### Pattern 2: GMT File Structure

**What:** Tab-separated text, one gene set per row.

**Format (verified against GMT specification):**
```
<name>\t<description>\t<gene1>\t<gene2>\t...
```

**Column 1 (name):** `KE{ID}_{Name_slug}` — locked decision. Slug: strip `KE ` prefix, take numeric ID, slugify the KE title (lowercase, non-alphanumeric → `_`, collapse repeated `_`).

Example: KE ID `KE 55`, title `"Decreased NMDARs, Decreased"` → `KE55_Decreased_NMDARs_Decreased`

```python
import re, unicodedata

def _make_ke_slug(ke_id: str, ke_title: str) -> str:
    """Produce KE{N}_{Title_slug} for GMT col 1."""
    num = re.sub(r'\D', '', ke_id)          # "KE 55" -> "55"
    slug = unicodedata.normalize("NFKD", ke_title)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', slug).strip('_')
    return f"KE{num}_{slug}"
```

**Column 2 (description):** Use the WikiPathway title (for KE-WP) or GO term name (for KE-GO). This is Claude's discretion — a human-readable description matching what tools display as the gene set label.

**Columns 3+ (genes):** HGNC gene symbols (see decision section below).

**Example KE-WP row:**
```
KE55_Decreased_BDNF\tApoptosis\tCAPS3\tBAX\tBCL2\t...
```

**Example KE-GO row:**
```
KE55_Decreased_BDNF\tapoptotic process\tCAPS3\tBAX\tBCL2\t...
```

### Pattern 3: Gene Identifier Decision — HGNC Symbols (Claude's Discretion)

**Recommendation: Use HGNC symbols.**

Evidence:
- WikiPathways official GMT uses Entrez IDs natively, BUT the codebase uses HGNC symbols throughout (`wp:bdbHgncSymbol` in SPARQL queries, `data/go_bp_gene_annotations.json` stores HGNC symbols, `ke_genes.py` returns HGNC symbols).
- fgsea's `gmtPathways()` reads gene names in whatever format the file uses — it just needs consistency between the GMT and the user's ranked gene list.
- clusterProfiler's `enricher()` (generic enrichment) accepts HGNC symbols directly.
- Converting to Entrez IDs would require a lookup table (`mygene` or AnnotationDbi) that is not in the current stack.
- HGNC symbols are human-readable and are the format researchers directly use.
- **Caveat:** clusterProfiler's `enrichWP()` function expects Entrez IDs specifically, but that function targets WikiPathways' own GMT files. Our GMT files are custom; researchers will use `enricher()` or fgsea's `gmtPathways()` instead, which work with any consistent identifier.

**KE-WP genes source:** WikiPathways SPARQL `wp:bdbHgncSymbol` — already queries this in `src/suggestions/pathway.py`. The same query logic can batch across all WP IDs in the `mappings` table. Results should be cached to avoid N×SPARQL calls per export generation.

**KE-GO genes source:** `data/go_bp_gene_annotations.json` — already loaded, maps GO ID → list of HGNC symbols. No SPARQL needed.

### Pattern 4: RDF/Turtle with Reification for Provenance (Claude's Discretion)

**Recommendation: Use classic RDF reification** (not named graphs, not RDF-star).

**Reasoning:**
- The decision says "use whichever pattern rdflib parses cleanly" — reification produces valid standard Turtle that any tool (rdflib, Protégé, online validators) reads without special plugins.
- Named graphs require TriG format (not plain Turtle). The decision says "two separate Turtle files" — TriG cannot be split cleanly per-file without losing the named graph context. Reification stays in plain `.ttl`.
- RDF-star is not yet in any W3C standard (as of early 2026, RDF 1.2 / RDF-star is still in Working Draft status) and rdflib support is partial.
- Reification is verbose but the dataset is small (hundreds of mappings), so verbosity is not a concern.

**rdflib reification pattern:**

```python
# Source: rdflib 6.3.x docs + W3C RDF reification vocabulary
from rdflib import Graph, URIRef, Literal, RDF, Namespace
from rdflib.namespace import DCTERMS, XSD

KEWP = Namespace("https://ke-wp-mapping.org/vocab#")
MAPPING = Namespace("https://ke-wp-mapping.org/mapping/")

g = Graph()
g.bind("ke-wp", KEWP)
g.bind("dcterms", DCTERMS)

mapping_uri = MAPPING[row["uuid"]]

# Core mapping triple
g.add((mapping_uri, RDF.type, KEWP.KeyEventPathwayMapping))
g.add((mapping_uri, KEWP.keyEventId, Literal(row["ke_id"])))
g.add((mapping_uri, KEWP.keyEventName, Literal(row["ke_title"])))
g.add((mapping_uri, KEWP.pathwayId, Literal(row["wp_id"])))
g.add((mapping_uri, KEWP.pathwayTitle, Literal(row["wp_title"])))
g.add((mapping_uri, KEWP.confidenceLevel, Literal(row["confidence_level"])))

# Provenance (directly on the mapping node, using dcterms)
if row.get("approved_by_curator"):
    g.add((mapping_uri, DCTERMS.creator, Literal(row["approved_by_curator"])))
if row.get("approved_at_curator"):
    g.add((mapping_uri, DCTERMS.date, Literal(row["approved_at_curator"], datatype=XSD.dateTime)))
if row.get("suggestion_score") is not None:
    g.add((mapping_uri, KEWP.suggestionScore, Literal(row["suggestion_score"], datatype=XSD.decimal)))

ttl_output = g.serialize(format="turtle")
```

**Note:** The existing `src/exporters/rdf_exporter.py` uses string concatenation without rdflib. Replace it with rdflib `Graph` objects — the serializer handles escaping, prefix declarations, and valid Turtle syntax automatically. The old exporter also lacks UUID, suggestion_score, and approved_at fields.

### Pattern 5: Zenodo API Deposit Workflow

**API base:** `https://zenodo.org/api/` (production), `https://sandbox.zenodo.org/api/` (testing)

**Authentication:** `Authorization: Bearer {ZENODO_API_TOKEN}` header on all requests.

**First-time deposit (no existing record):**

```python
import requests, json

ZENODO_BASE = "https://zenodo.org/api"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
}

# 1. Create empty deposit
r = requests.post(f"{ZENODO_BASE}/deposit/depositions", json={}, headers=headers)
r.raise_for_status()
deposition_id = r.json()["id"]
bucket_url = r.json()["links"]["bucket"]

# 2. Upload each file (bucket API — supports up to 50GB total, 100 files)
for filename, content in files.items():
    r = requests.put(
        f"{bucket_url}/{filename}",
        data=content.encode("utf-8"),
        headers={"Authorization": f"Bearer {api_token}"},
    )
    r.raise_for_status()

# 3. Set metadata
metadata = {
    "metadata": {
        "title": "KE-WP and KE-GO Mapping Database",
        "upload_type": "dataset",
        "description": "...",
        "creators": [{"name": "...", "affiliation": "..."}],
        "keywords": ["key events", "WikiPathways", "Gene Ontology", "AOP"],
        "license": "cc-zero",  # CC0 — matches existing /download CSV header
        "publication_date": "2026-02-21",
    }
}
r = requests.put(
    f"{ZENODO_BASE}/deposit/depositions/{deposition_id}",
    data=json.dumps(metadata),
    headers=headers,
)
r.raise_for_status()

# 4. Publish
r = requests.post(
    f"{ZENODO_BASE}/deposit/depositions/{deposition_id}/actions/publish",
    headers={"Authorization": f"Bearer {api_token}"},
)
r.raise_for_status()
doi = r.json()["doi"]
```

**New version of existing published record:**

```python
# Use the ID of the latest published version
r = requests.post(
    f"{ZENODO_BASE}/deposit/depositions/{existing_id}/actions/newversion",
    headers={"Authorization": f"Bearer {api_token}"},
)
r.raise_for_status()
# The new draft URL is in links.latest_draft
new_draft_url = r.json()["links"]["latest_draft"]
new_id = new_draft_url.rstrip("/").split("/")[-1]
# Then proceed with file upload + metadata update + publish as above
```

**DOI storage:** Store the published DOI in a simple config table or flat JSON file (`data/zenodo_meta.json`) so the navbar/homepage can display it. Do not hardcode.

**Sandbox testing:** Use `https://sandbox.zenodo.org/api/` with a sandbox token. Sandbox deposits are separate from production and free to create/discard.

### Anti-Patterns to Avoid

- **Generating exports synchronously in the request thread:** SPARQL queries for pathway gene lists take 1-10s per pathway. For a full export, this means hundreds of seconds. Use a generate-on-demand-and-cache approach; warn admin that regeneration is slow.
- **Regenerating all 4 files on every download request:** Only regenerate when admin explicitly triggers. Public download routes serve cached files only.
- **Using rdflib ConjunctiveGraph with `format="turtle"`:** This silently drops named graph context in rdflib 6.x. Use a plain `Graph` with reification (as described) or serialize to TriG. Since we need `.ttl` extension and pure Turtle, use plain Graph.
- **Storing `ZENODO_API_TOKEN` in source code or committed `.env`:** Add to `.env.example` only. Require it as an environment variable; gracefully degrade (show "DOI not configured" in UI) when absent.
- **Overwriting the Zenodo concept DOI:** Zenodo produces two DOIs — a "concept DOI" (all versions) and a "version DOI" (specific version). Display the concept DOI in the navbar so citations always resolve to the latest version.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RDF serialization + escaping | Custom string formatting (like current `rdf_exporter.py`) | `rdflib.Graph.serialize(format="turtle")` | rdflib handles Turtle escaping, prefix declarations, blank nodes, datatype annotations |
| Zenodo HTTP client | Custom retry/error wrapper | `requests` with `.raise_for_status()` + simple try/except | Zenodo API is straightforward REST; over-engineering adds risk |
| Slug generation | Regex-only slug | `unicodedata.normalize("NFKD", ...)` + `re.sub` | Unicode accented chars in KE titles need NFD normalization before ASCII encoding |
| Gene-to-pathway lookup | Re-query SPARQL on every export | Cache pathway gene lists to SQLite `sparql_cache` or `static/exports/<wp_id>_genes.json` | SPARQL endpoint has rate limits; re-querying 1000+ pathways on each admin click will timeout |

**Key insight:** The hardest part of this phase is not writing the code — it is the pathway-gene fetch latency. The KE-WP GMT requires fetching gene lists for every mapped WikiPathways ID. That is a batch SPARQL operation. Either use the existing `sparql_cache` table (preferred — already implemented) or cache gene lists to a pre-computed JSON sidecar.

---

## Common Pitfalls

### Pitfall 1: Pathway Gene Lists Not Available at GMT Generation Time

**What goes wrong:** The `mappings` table stores `wp_id` and `wp_title` but not gene lists. GMT generation requires fetching genes per pathway from WikiPathways SPARQL. A full export might need genes for 100-500 unique pathways. SPARQL queries can take 1-10s each. Total generation time: minutes.

**Why it happens:** Gene lists were never needed for stored mapping records — they were only needed at suggestion time.

**How to avoid:**
1. In the GMT generator, batch all unique `wp_id` values and query genes for all at once (WikiPathways SPARQL supports `VALUES` with multiple IDs).
2. The existing `sparql_cache` table in SQLite can store results. Use `hashlib.md5` of the query as the cache key (same pattern as `src/blueprints/v1_api.py` and `src/suggestions/pathway.py`).
3. If SPARQL is unavailable, produce the GMT with empty gene columns and log a warning rather than failing the entire export.

**Warning signs:** Export endpoint times out or takes > 30s on first generation.

### Pitfall 2: Confidence Filter Inconsistency

**What goes wrong:** The `?min_confidence=High` filter needs to match the database's stored `confidence_level` values case-insensitively. The DB stores `high`, `medium`, `low` (lowercase). A `min_confidence=High` filter could return no results if not lowercased.

**Why it happens:** User-facing labels are capitalized; DB values are lowercase.

**How to avoid:** Normalize the `min_confidence` param to lowercase before DB query. The v1 API already does this: `LOWER(confidence_level) = LOWER(?)`.

**Warning signs:** Empty GMT file even when mappings exist.

### Pitfall 3: Zenodo New Version vs. New Record

**What goes wrong:** Creating a new Zenodo deposit each time "Publish" is clicked creates separate unlinked records, each with their own unrelated DOI. This means the concept DOI in the navbar breaks.

**Why it happens:** The new version endpoint (`/actions/newversion`) requires the ID of the _latest published version_, not the original/concept record ID. Getting this wrong creates a new top-level record.

**How to avoid:**
1. Persist the Zenodo deposition ID of the latest published version in `data/zenodo_meta.json` alongside the DOI.
2. On "Publish new version", read the stored ID and use the `/actions/newversion` endpoint.
3. On first publish (no stored ID), use the create-from-scratch flow.

**Warning signs:** New deposits appear in Zenodo dashboard unlinked to previous versions.

### Pitfall 4: GMT File With Zero Genes is Valid But Useless

**What goes wrong:** If SPARQL is unavailable, the KE-WP GMT will have gene columns empty. This is syntactically valid but will produce no enrichment results when researchers use it.

**Why it happens:** No fallback when WikiPathways SPARQL is unavailable.

**How to avoid:**
1. Check if cached gene lists exist before generating; if SPARQL is unavailable and no cache, return a 503 with an informative message rather than serving an empty-gene GMT.
2. Document this dependency in the downloads page: "Gene lists sourced from WikiPathways SPARQL."

### Pitfall 5: rdflib `serialize()` Returns `str` in rdflib >= 6.0

**What goes wrong:** Old rdflib (< 6.0) code writes to a file handle passed to `serialize()`. In rdflib 6.x, `g.serialize(format="turtle")` returns a `str` directly.

**Why it happens:** API changed in rdflib 6.0.

**How to avoid:** Use `content = g.serialize(format="turtle")` and then `Path(output_path).write_text(content)`. The existing `rdf_exporter.py` uses string concatenation, not rdflib, so this is a fresh implementation concern.

**Confirmed:** rdflib 6.3.2 is installed and `serialize()` returns `str`.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### GMT File Writer

```python
# Pattern: generate GMT content as string, then write to cache file
import io

def generate_gmt(mappings, gene_fetcher_fn) -> str:
    """
    mappings: list of dicts with ke_id, ke_title, wp_id (or go_id), wp_title (or go_name)
    gene_fetcher_fn: callable(target_id) -> list[str] of HGNC gene symbols
    """
    out = io.StringIO()
    for row in mappings:
        term_name = _make_ke_slug(row["ke_id"], row["ke_title"])
        description = row.get("wp_title") or row.get("go_name", "")
        genes = gene_fetcher_fn(row.get("wp_id") or row.get("go_id"))
        if not genes:
            continue  # skip gene-less rows per GMT convention
        parts = [term_name, description] + genes
        out.write("\t".join(parts) + "\n")
    return out.getvalue()
```

### rdflib Turtle Export (rdflib 6.3.x)

```python
# Source: rdflib 6.3.x docs (https://rdflib.readthedocs.io/en/6.3.1/)
from rdflib import Graph, URIRef, Literal, RDF, Namespace
from rdflib.namespace import DCTERMS, XSD

def generate_kewp_turtle(mappings) -> str:
    KEWP = Namespace("https://ke-wp-mapping.org/vocab#")
    MAPPING = Namespace("https://ke-wp-mapping.org/mapping/")
    AOP = Namespace("https://aopwiki.org/events/")
    WP = Namespace("https://www.wikipathways.org/pathways/")

    g = Graph()
    g.bind("ke-wp", KEWP)
    g.bind("dcterms", DCTERMS)
    g.bind("aop", AOP)
    g.bind("wp", WP)

    for row in mappings:
        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, KEWP.KeyEventPathwayMapping))
        g.add((uri, KEWP.keyEventId, Literal(row["ke_id"])))
        g.add((uri, KEWP.keyEventName, Literal(row["ke_title"])))
        g.add((uri, KEWP.pathwayId, Literal(row["wp_id"])))
        g.add((uri, KEWP.pathwayTitle, Literal(row["wp_title"])))
        g.add((uri, KEWP.confidenceLevel, Literal(row["confidence_level"])))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        if row.get("approved_by_curator"):
            g.add((uri, DCTERMS.creator, Literal(row["approved_by_curator"])))
        if row.get("approved_at_curator"):
            g.add((uri, DCTERMS.date,
                   Literal(row["approved_at_curator"], datatype=XSD.dateTime)))
        if row.get("suggestion_score") is not None:
            g.add((uri, KEWP.suggestionScore,
                   Literal(float(row["suggestion_score"]), datatype=XSD.decimal)))

    return g.serialize(format="turtle")  # returns str in rdflib >= 6.0
```

### Zenodo Deposit (requests)

```python
# Source: https://developers.zenodo.org/ — official Python examples
import requests, json, os

def zenodo_publish(files: dict, metadata: dict, existing_deposition_id=None) -> dict:
    """
    files: {filename: file_content_str}
    metadata: Zenodo metadata dict (title, creators, etc.)
    existing_deposition_id: int if updating an existing record, None for first publish
    Returns: {"doi": "...", "deposition_id": ...}
    """
    token = os.environ["ZENODO_API_TOKEN"]
    base = "https://zenodo.org/api"
    auth = {"Authorization": f"Bearer {token}"}
    json_headers = {**auth, "Content-Type": "application/json"}

    if existing_deposition_id:
        r = requests.post(
            f"{base}/deposit/depositions/{existing_deposition_id}/actions/newversion",
            headers=auth
        )
        r.raise_for_status()
        draft_url = r.json()["links"]["latest_draft"]
        dep_id = int(draft_url.rstrip("/").split("/")[-1])
        bucket_url = requests.get(draft_url, headers=auth).json()["links"]["bucket"]
    else:
        r = requests.post(f"{base}/deposit/depositions", json={}, headers=json_headers)
        r.raise_for_status()
        dep_id = r.json()["id"]
        bucket_url = r.json()["links"]["bucket"]

    for filename, content in files.items():
        r = requests.put(f"{bucket_url}/{filename}", data=content.encode(), headers=auth)
        r.raise_for_status()

    r = requests.put(
        f"{base}/deposit/depositions/{dep_id}",
        data=json.dumps({"metadata": metadata}),
        headers=json_headers
    )
    r.raise_for_status()

    r = requests.post(
        f"{base}/deposit/depositions/{dep_id}/actions/publish",
        headers=auth
    )
    r.raise_for_status()
    result = r.json()
    return {"doi": result["doi"], "deposition_id": result["id"]}
```

### Slug Generation

```python
import re, unicodedata

def _make_ke_slug(ke_id: str, ke_title: str) -> str:
    """KE55_Decreased_BDNF format for GMT col 1."""
    num = re.sub(r'\D', '', ke_id)   # "KE 55" -> "55"
    title = unicodedata.normalize("NFKD", ke_title)
    title = title.encode("ascii", "ignore").decode("ascii")
    title = re.sub(r'[^a-zA-Z0-9]+', '_', title).strip('_')
    return f"KE{num}_{title}"
```

### Flask Route: Public Download

```python
# Pattern: serve cached file or generate on-demand
from flask import send_file, current_app
from pathlib import Path

@main_bp.route("/exports/gmt/ke-wp")
def download_ke_wp_gmt():
    min_conf = request.args.get("min_confidence", "").lower() or None
    today = datetime.date.today().isoformat()
    tier = min_conf.capitalize() if min_conf else "All"
    filename = f"KE-WP_{today}_{tier}.gmt"
    cache_path = Path("static/exports") / filename

    if not cache_path.exists():
        content = _generate_ke_wp_gmt(min_confidence=min_conf)
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(content)

    return send_file(str(cache_path), as_attachment=True, download_name=filename)
```

### Flask Route: Admin Regenerate

```python
# admin_bp — admin_required decorator guards this
@admin_bp.route("/exports/regenerate", methods=["POST"])
@admin_required
def regenerate_exports():
    import shutil
    cache_dir = Path("static/exports")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir()
    # Trigger generation of all 4 files (or defer to background)
    # Return JSON so admin page can show status
    return jsonify({"status": "ok", "message": "Export cache cleared. Files will regenerate on next download."})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| rdflib `serialize(destination=file)` | `content = g.serialize(format="turtle")` returns str | rdflib 6.0 (2021) | All rdflib >=6 code must use the return value, not file destination |
| Zenodo legacy files API (100MB limit) | Bucket PUT API (50GB limit) | 2023 Zenodo update | Use `links.bucket` PUT endpoint, not `/api/deposit/depositions/{id}/files` POST |
| `ConjunctiveGraph` for named graphs | `Dataset` (ConjunctiveGraph deprecated in rdflib 7) | rdflib 7.0 | Not relevant here — we use plain `Graph` + reification; avoid ConjunctiveGraph entirely |
| WikiPathways GMT with Entrez IDs | HGNC symbols in our custom GMT (decision) | N/A — our format | Our GMT is not the official WikiPathways GMT; document this clearly in the downloads page |

**Deprecated/outdated:**
- `rdf_exporter.py` (existing): Uses string concatenation, lacks UUID/provenance columns added in Phase 2/3, no rdflib. Replace entirely.
- Zenodo `/api/deposit/depositions/{id}/files` POST endpoint: Deprecated in favor of bucket PUT. The old one still works but has 100MB per-file limit.

---

## Open Questions

1. **Pathway gene list caching strategy**
   - What we know: SPARQL queries take 1-10s per pathway; `sparql_cache` table exists; WikiPathways SPARQL supports batch `VALUES` queries.
   - What's unclear: Whether a single `VALUES` query for 100+ pathways is reliably fast or causes SPARQL endpoint timeouts. The existing `_find_pathways_by_genes` in `pathway.py` queries per-gene, not per-pathway.
   - Recommendation: Implement a dedicated `_fetch_pathway_genes_batch(wp_ids: list) -> dict[str, list[str]]` function for GMT generation, separate from the suggestion logic. Test against sandbox data before wiring to the export endpoint.

2. **First Zenodo deposit ID bootstrapping**
   - What we know: The admin presses "Publish" → API creates the first record → DOI is returned.
   - What's unclear: Where to persist the returned `deposition_id` so the "new version" flow works on subsequent clicks. A `data/zenodo_meta.json` file is simplest.
   - Recommendation: `data/zenodo_meta.json` with `{"deposition_id": null, "doi": null, "published_at": null}`. Admin UI shows current DOI and "Publish New Version" button only when `deposition_id` is non-null.

3. **GMT for KE-WP: one row per KE or one row per KE-pathway pair?**
   - What we know: Standard GMT format is one row per gene set. For KE-WP, the natural gene set is per-KE (all pathways' genes for that KE merged).
   - What's unclear: Should each KE-pathway pair be a separate row (resulting in many small gene sets) or should all pathways for a KE be merged into one row? Merging is standard for enrichment analysis where you want to test "is this KE's pathway set enriched?"
   - Recommendation: One row per KE — aggregate genes across all mapped pathways for that KE. This makes the GMT loadable as "KE gene sets" for enrichment. But also investigate whether researchers want per-pathway granularity; if so, one row per KE-pathway pair with `KE55_WP4655_Pathway_Name` naming could work. **This needs clarification before planning/implementation.**

---

## Sources

### Primary (HIGH confidence)

- rdflib 6.3.2 installed (`pip show rdflib`) — confirmed version, confirmed `serialize()` returns str
- `https://developers.zenodo.org/` — official Zenodo REST API docs; Python code examples verified
- Codebase: `src/core/models.py` — confirmed DB columns: `uuid`, `approved_by_curator`, `approved_at_curator`, `suggestion_score`, `confidence_level` on both `mappings` and `ke_go_mappings`
- Codebase: `data/go_bp_gene_annotations.json` — confirmed HGNC symbol format (`GO:xxxxxxx → ['GENE1', 'GENE2', ...]`)
- Codebase: `src/suggestions/pathway.py` — confirmed `wp:bdbHgncSymbol` SPARQL predicate for pathway genes
- Codebase: `requirements.txt` — confirmed `requests==2.32.5`, no rdflib entry (installed in env but not pinned — should add)

### Secondary (MEDIUM confidence)

- [rWikiPathways readPathwayGMT docs](https://r.wikipathways.org/reference/readPathwayGMT.html) — confirms WikiPathways official GMT uses Entrez Gene IDs (our format will differ; use HGNC)
- [fgsea Bioconductor docs](https://bioconductor.org/packages/release/bioc/html/fgsea.html) — confirms `gmtPathways()` reads any consistent gene identifier, HGNC symbols accepted
- [EnrichmentMap GMT format docs](https://enrichmentmap.readthedocs.io/en/latest/FileFormats.html) — confirmed col 1 = name (unique), col 2 = description, col 3+ = tab-separated genes
- [Zenodo manage versions](https://help.zenodo.org/docs/deposit/manage-versions/) — confirms concept DOI vs version DOI distinction
- RDF reification vs named graphs: multiple sources confirm reification is simpler for plain Turtle (no TriG needed), despite verbosity

### Tertiary (LOW confidence)

- GMT description field accepting URL or free text: no authoritative spec found; convention from codebase inspection and tool documentation suggests free-text description is fine and is displayed as label in GSEA/EnrichmentMap

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed and verified against docs
- Architecture: HIGH — patterns match existing codebase conventions exactly
- GMT format: HIGH for structure; MEDIUM for gene identifier choice (HGNC vs Entrez reasoning is solid but untestable without running clusterProfiler/fgsea against real output)
- Zenodo API: HIGH — official docs plus code examples verified
- Pitfalls: HIGH — SPARQL latency issue is directly observable from existing codebase patterns

**Research date:** 2026-02-21
**Valid until:** 2026-04-21 (60 days — Zenodo API is stable; rdflib and clusterProfiler conventions unlikely to shift)

**One open question requiring user input before planning:**
GMT granularity: one row per KE (genes merged across all mapped pathways for that KE) vs. one row per KE-pathway pair. This affects the meaning of the gene set and the term name format. Default recommendation: one row per KE (aggregated), but confirm before implementation.
