# PITFALLS.md

**Research type:** Project Research — Pitfalls dimension
**Domain:** Bioinformatics curation tools / biological database APIs
**Transition:** Prototype to v1.0 production
**Date:** 2026-02-19

---

## Purpose

This document catalogs critical mistakes that bioinformatics curation tools and biological database APIs commonly make when going from prototype to production. Each pitfall includes warning signs detectable in the current codebase, specific prevention strategies, and the phase where it should be addressed.

---

## Pitfall 1: API Endpoints Without Versioning Bake In Breaking Changes

**What goes wrong:** Research scripts that cite a paper's DOI will forever reference the API URL as written. The moment you rename a field (`confidence` → `confidence_level`), change a response shape, or add pagination where none existed, every downstream R/Python script silently breaks. In biology, scripts are shared in supplementary material and run years after publication.

**Warning signs in this codebase:**
- `api_bp = Blueprint("api", __name__)` with no `url_prefix`. Routes like `/suggest_pathways/<ke_id>` and `/suggest_go_terms/<ke_id>` exist at root level without a `/v1/` prefix.
- The R examples file (`examples/r_examples.R`) references `/api/v1/mappings` (lines 40, 51, 67) — an endpoint that does not yet exist in `src/blueprints/api.py`. The examples are already out of sync with the actual implementation.
- `get_all_mappings()` in `src/core/models.py` (lines 301, 706) returns all rows with no pagination support. When the dataset grows, adding `limit`/`offset` will change the response contract.

**Prevention strategy:**
1. Register the REST API blueprint with `url_prefix="/api/v1"` before v1.0 ships. Keep the current unversioned routes as aliases that return a deprecation header during a transition window.
2. Establish a stable response schema contract (JSON field names, types, presence) and document it in the API docs before publishing the paper DOI.
3. Never rename a field — add the new name alongside the old one, and deprecate the old with a documented sunset date.
4. Implement an `/api/v1/` discovery endpoint that returns the schema version so scripts can self-check compatibility.

**Phase:** Must be addressed before any external collaborators access the API — Phase 1 / v1.0 API work.

---

## Pitfall 2: Gunicorn Sync Workers × BioBERT × No Preload = 4x Memory on Startup

**What goes wrong:** The current Dockerfile runs `gunicorn --workers 4 --worker-class sync`. Each sync worker forks from the master *after* the app is imported, which means each of the 4 workers loads its own full copy of BioBERT weights and all `.npy` embedding arrays. On a 4GB RAM host this is immediately fatal — BioBERT alone is ~400MB per process, plus ~190MB in embeddings, times 4 workers = ~2.4GB just for model weights, before serving any requests.

Even if RAM is abundant, startup becomes a rolling restart problem: each worker independently initializes `BiologicalEmbeddingService`, triggering the `allow_pickle=True` numpy loads for GO embeddings (75.8MB + 75.9MB), and each parallel worker startup will fight for disk I/O.

**Warning signs in this codebase:**
- `Dockerfile` line 25: `gunicorn --workers 4 --worker-class sync` with no `--preload-app` flag.
- `src/services/embedding.py` `__init__` method (lines 66–135): all embedding files loaded eagerly on construction; `BiologicalEmbeddingService` is constructed inside `ServiceContainer` which is constructed in `create_app()`. Without `--preload-app`, this runs 4 times.
- `HEALTHCHECK --start-period=20s` in Dockerfile line 23 — almost certainly too short for 4 independent model loads.

**Prevention strategy:**
1. Add `--preload-app` to the gunicorn command. This loads the Flask app (and the embedding model) once in the master process; workers then fork and share the memory pages copy-on-write. The 4GB RAM requirement becomes realistic instead of theoretical.
2. Increase `--start-period` to 120s (model initialization can take 30-60 seconds on cold start even with CPU-only PyTorch).
3. Add `--max-requests 1000 --max-requests-jitter 50` to recycle workers periodically, preventing long-running memory accumulation.
4. Validate in CI: add a memory usage assertion in the Docker health check smoke test (total RSS after startup should be < 2GB).

**Phase:** Deployment configuration — fix before first Docker production run.

---

## Pitfall 3: SQLite Without WAL Mode Locks the Database Under Gunicorn Multi-Worker

**What goes wrong:** SQLite's default journal mode is DELETE (rollback journal), which holds an exclusive lock on the entire database file during every write. With 4 Gunicorn sync workers, any concurrent write from one worker (proposal submission, cache update, rate limit record) blocks all reads on other workers until the write completes. Under AOP workshop traffic — 20-30 curators submitting simultaneously — this manifests as 5xx errors with "database is locked" messages.

**Warning signs in this codebase:**
- `src/core/models.py` line 20: `sqlite3.connect(self.db_path)` — no `timeout` argument, no WAL PRAGMA, no `isolation_level` override.
- No `PRAGMA journal_mode=WAL` anywhere in `Database.init_db()` (line 24). The `get_connection()` method has no connection pragmas at all.
- `src/services/rate_limiter.py` writes to SQLite on every request (rate limit tracking). Under multi-worker gunicorn, these concurrent writes are the first thing to deadlock.
- `CONCERNS.md` notes: "SQLite supports ~10-20 concurrent writers before lock contention" — but the fix listed ("increase timeout and WAL mode (already enabled?)") is not actually implemented.

**Prevention strategy:**
1. Add WAL mode and busy timeout to `Database.get_connection()`:
   ```python
   conn = sqlite3.connect(self.db_path, timeout=30)
   conn.execute("PRAGMA journal_mode=WAL")
   conn.execute("PRAGMA busy_timeout=10000")
   conn.row_factory = sqlite3.Row
   ```
2. Set these pragmas in `Database.init_db()` as well so they persist across the database lifecycle.
3. Consider moving rate limiting out of SQLite entirely (the existing `memory://` fallback in `RateLimiter` is per-worker and doesn't share state between workers — rate limit bypasses are possible in multi-worker mode). A simple Redis-backed rate limiter is the correct fix for production.
4. Add an integration test that writes to the database from 3 concurrent threads to catch lock contention in CI.

**Phase:** Pre-deployment hardening — fix before any production traffic.

---

## Pitfall 4: Pre-computed Embedding Files Baked Into the Docker Image Create Operational Debt

**What goes wrong:** The Dockerfile uses `COPY . .` which copies `data/*.npy` and `data/*.json` (190MB of binary files) into the image layer. This has compounding consequences: (a) every code change requires rebuilding a 190MB+ layer; (b) GO term annotations go stale as the Gene Ontology database updates quarterly, but there is no signal that the baked-in files are outdated; (c) embedding regeneration (which requires running `precompute_go_embeddings.py`) produces files that don't match the old image — rolling back a Docker image also rolls back the embedding data model; (d) different deployments (dev, staging, prod) may use embeddings from different dates, producing different suggestion results for the same input.

**Warning signs in this codebase:**
- `Dockerfile` line 18: `COPY . .` — no exclusion of `data/` directory.
- `data/go_bp_metadata.json` contains GO term synonyms. `CONCERNS.md` notes: "GO embeddings may not cover all terms in live GO database if new terms are added."
- No embedding file version stamp or generation timestamp in any metadata file.
- `src/services/embedding.py` line 129: `'data/pathway_title_embeddings.npy'` is hardcoded relative to the working directory — path resolution will silently fail if the working directory changes in deployment.

**Prevention strategy:**
1. Add `data/*.npy` and `data/*.json` to `.dockerignore`. Mount them as a Docker volume at runtime: `docker run -v /host/data:/app/data`. This decouples the model data lifecycle from the code release cycle.
2. Store a generation timestamp and GO database version in a sidecar `data/manifest.json` file. Validate on startup that the manifest exists and that the GO version matches the expected version for the release.
3. Make all embedding file paths configurable through environment variables / `ServiceContainer` initialization parameters, not hardcoded strings. This allows staging to point to a different data directory than production.
4. Add a `make refresh-embeddings` target to the Makefile that re-runs all precomputation scripts and regenerates the manifest.

**Phase:** Before any production deployment — this is a data architecture decision that is harder to change after the fact.

---

## Pitfall 5: Biological Curator UX Failure — Non-experts Abandon on Ambiguous Feedback

**What goes wrong:** Toxicologists are scientific experts, not software users. They tolerate ambiguity in a biological assay; they do not tolerate ambiguity in a form submission. The most common UX failure mode in scientific curation tools is: a curator submits a mapping, sees no visible state change, and submits again — creating duplicate proposals. Or they see a cryptic error code (`503 Service Unavailable`) when a SPARQL endpoint times out and assume the tool is broken.

**Warning signs in this codebase:**
- `src/blueprints/api.py` line 169: successful submit returns `{"message": "Entry added successfully."}` — but there is no duplicate detection at submission time (noted in `CONCERNS.md`: "No Duplicate Mapping Detection at Submission").
- `src/core/models.py` `create_proposal()`: does not check for an existing pending proposal for the same KE-WP pair before inserting.
- Error messages returned to the UI (`"Service timeout - please try again"`) give no guidance on what "try again" means or whether the curator's work was lost.
- No audit trail of admin approve/reject actions (noted in `CONCERNS.md`): curators cannot see why a proposal was rejected, which causes them to resubmit the same mapping repeatedly.

**Prevention strategy:**
1. Before inserting any proposal, check for an existing approved mapping AND an existing pending proposal for the same `(ke_id, wp_id)` or `(ke_id, go_id)` pair. Return a specific message: "This mapping already exists and is approved" or "A proposal for this mapping is pending admin review."
2. Return proposal status in the submission response so the frontend can show "Pending review" state immediately after submission, not just "Entry added."
3. When an admin rejects a proposal, require a rejection reason field (minimum 10 chars). Display the reason to the curator on their proposal history page.
4. Replace generic error messages with curator-specific language: instead of "503 Service Unavailable," show "The gene database is temporarily unreachable. Your mapping selection is preserved — try again in a few minutes." Keep the curator's KE and pathway selection intact across the error.

**Phase:** UX polish phase — before any external curator onboarding.

---

## Pitfall 6: Scientific API Consumers Expect Stable, Machine-Readable Identifiers — Not Display Strings

**What goes wrong:** R and Python bioinformatics workflows join datasets on identifiers. If the API returns `ke_title` as the join key and the KE title changes in AOP-Wiki (e.g., "Inhibition of cholinesterase" → "Inhibition of acetylcholinesterase"), every downstream joined dataset silently breaks. This is a known failure mode in the UniProt/Reactome ecosystem, where gene names change.

**Warning signs in this codebase:**
- `src/core/models.py` `create_mapping()` stores `ke_title` and `wp_title` as text strings in the database. If the AOP-Wiki or WikiPathways updates the title, the stored value is a historical snapshot.
- The mappings table primary key is an autoincrement integer `id`, but the R examples reference mappings by `mapping_id`. A mapping can be deleted and re-inserted with a different integer ID, breaking downstream references.
- The API returns `ke_id` (e.g., `"KE:123"`) and `wp_id` (e.g., `"WP456"`) as strings — these are the stable identifiers — but field naming is inconsistent: `ke_id` vs `go_id` vs `wp_id` with different prefix conventions.
- `go_id` in the GO mappings table may be stored as `"GO:0006955"` or `"GO_0006955"` depending on what the SPARQL endpoint returns — no normalization is enforced.

**Prevention strategy:**
1. Always return both stable identifier (`ke_id`, `wp_id`, `go_id`) and display string (`ke_title`, `wp_title`, `go_name`) in API responses. Document that identifiers are stable, titles may change.
2. Add a `mapping_uuid` column (UUID4) to both mapping tables. Expose this as the stable external reference in API responses. Integer IDs are internal implementation details.
3. Normalize `go_id` on insert to always use colon format (`GO:0006955`). Add a database constraint or application-level check.
4. In the API documentation, add a data versioning statement: "All mappings are annotated with a `created_at` timestamp. Consumers should track this to detect updates."

**Phase:** API design — must be decided before the REST API is published.

---

## Pitfall 7: ML Score Instability Makes Curation Non-Reproducible

**What goes wrong:** A toxicologist curates KE→pathway mappings on Monday using suggestion scores. On Tuesday, an admin regenerates embeddings with a new GO synonym set (as just happened with commit `611bc9b` — adding EXACT synonyms changed all GO name embeddings). Now the same KE produces different suggestion scores and a different ranked list. The curator who planned to continue their work on Tuesday now sees different top-10 suggestions — potentially missing mappings they intended to review. Reproducibility is a publication requirement.

**Warning signs in this codebase:**
- `src/services/embedding.py` line 275: `@lru_cache(maxsize=1000)` on `encode()` — the cache is in-process only. Restarting the app clears the cache; scores will differ if the model is reloaded.
- The recent commit `611bc9b` ("Include EXACT synonyms in GO name embeddings, set 60/40 name/def weight") changed the embedding generation logic. Any GO suggestion scores from before this commit are not comparable to scores after.
- `scoring_config.yaml` controls weights but there is no version field in the config. Changing `gene_weight` from 0.35 to 0.40 retroactively changes how the suggestion engine would have scored all existing proposals.
- `CONCERNS.md` notes: "Silent Embedding Fallback to Zeros" — if encoding fails, `encode()` returns a zero vector, producing a zero similarity score. This is indistinguishable from a true zero-similarity result.

**Prevention strategy:**
1. Store the `scoring_config.yaml` version hash (or a version string like `v2.3`) alongside every proposal at submission time. If the scoring config changes, existing proposals retain their original score provenance.
2. Add a `model_version` field to proposals: store the git commit hash or a `data/manifest.json` version at proposal creation time. This allows the paper to state exactly which model version produced which suggestions.
3. Never silently return zero vectors on encoding failure. Raise `ServiceError` and surface it to the UI as "Suggestion service temporarily unavailable" rather than returning zero-scored (but present) results.
4. When embeddings are regenerated, increment a version counter in `data/manifest.json`. Log a startup warning if the manifest version differs from the version at which current approved mappings were generated.

**Phase:** Before any data used in a publication is generated — this is a data provenance requirement.

---

## Pitfall 8: SQLite File Path at Docker Restart Loses All Curated Data

**What goes wrong:** The database file defaults to `ke_wp_mapping.db` at the working directory (`/app/ke_wp_mapping.db` inside the container). If the container is removed and re-created (e.g., for a version upgrade), the database file is destroyed unless it is on a mounted volume. Months of curation work disappears on the first `docker compose up --build`.

**Warning signs in this codebase:**
- `Dockerfile` line 19: `COPY . .` — the workdir is `/app` and the app writes `ke_wp_mapping.db` to `/app/ke_wp_mapping.db` inside the container.
- `src/core/config.py` line 46: `DATABASE_PATH = os.getenv("DATABASE_PATH", "ke_wp_mapping.db")` — the default path is relative to the working directory.
- `docker-compose.yml` exists but its volume configuration was not inspected — if `ke_wp_mapping.db` is not listed as a volume mount, data loss will occur on container recreation.
- No backup or export-on-shutdown mechanism exists.

**Prevention strategy:**
1. Change the default `DATABASE_PATH` to an absolute path at a volume-mountable location: `/app/data/ke_wp_mapping.db`. Ensure this is explicitly mounted as a Docker volume.
2. Add a startup check: if `DATABASE_PATH` resolves to a path inside the container that is not a mounted volume, log a `WARNING: database at {path} is not persisted — data will be lost on container restart`.
3. Implement a nightly export cronjob or a `/admin/backup` endpoint that writes a timestamped CSV/JSON dump to a mounted backup directory.
4. Test the full "destroy and recreate container" scenario in the deployment runbook before going live.

**Phase:** Deployment hardening — critical fix before any external users submit data.

---

## Pitfall 9: Research API Consumers Hit Unexplained Rate Limits

**What goes wrong:** A bioinformatician writing a Python loop to fetch suggestions for all 1561 KEs hits the SPARQL rate limit (500 req/hour configured in `RateLimiter`) after a few minutes. They receive a `429 Too Many Requests` response with the message "Service timeout - please try again" — which is the wrong error message (that is the SPARQL timeout message). There are no `Retry-After` headers, no explanation of the limit, and no bulk endpoint to avoid the problem altogether. The bioinformatician assumes the tool is broken and contacts the paper authors.

**Warning signs in this codebase:**
- `src/blueprints/api.py` line 254-255: `logger.error("SPARQL request timeout")` followed by `return jsonify({"error": "Service timeout - please try again"}), 503` — but rate limit responses are `429` from the decorator. The error messages between timeout (503) and rate limit (429) are easy to confuse.
- No `Retry-After` header is set on 429 responses.
- `suggest_pathways` (line 584) and `suggest_go_terms` (line 1175) are decorated with `@sparql_rate_limit`. Fetching suggestions for 1561 KEs in sequence will hit this limit in under 4 hours even at 1 request per 10 seconds.
- No bulk endpoint exists for fetching multiple suggestions in a single request.

**Prevention strategy:**
1. Set `Retry-After` header on all 429 responses: `response.headers["Retry-After"] = str(reset_seconds)`.
2. Fix the error message semantics: timeout = 503 "Gene database temporarily unavailable"; rate limit = 429 "Rate limit exceeded. See X-RateLimit-Reset header for reset time."
3. Add a bulk suggestions endpoint: `POST /api/v1/suggestions/batch` accepting a list of `ke_id` values (max 50). This allows research scripts to be efficient without hammering individual endpoints.
4. Add public documentation of rate limits in the API docs, including example code for respectful polling (`time.sleep()` examples in R and Python).
5. Consider providing the full pre-computed suggestion dataset as a downloadable file (CSV/JSON) so bulk consumers never need to call the suggestion API at all.

**Phase:** API design and documentation — before external publication.

---

## Pitfall 10: Export Format Fragility Breaks Downstream Bioinformatics Pipelines

**What goes wrong:** The Parquet and Excel exporters are listed as available but have optional dependencies (`openpyxl`, `pyarrow`). If these are not installed in the production Docker image, the export endpoint returns 500 errors that look like server crashes. More importantly, the export column names are derived from the database schema field names (`ke_id`, `wp_id`, `connection_type`) — which will change if the schema is refactored. A researcher's BioConductor package that reads `ke_wp_dataset.parquet` expecting the column `ke_id` breaks silently if the column is renamed.

**Warning signs in this codebase:**
- `src/blueprints/main.py` line 316: `logger.error("Missing dependencies for %s export: %s"...)` — `ImportError` on optional exports is caught and returned as 500, not 422.
- `src/exporters/excel_exporter.py` and `src/exporters/parquet_exporter.py` exist but their dependency availability in the production Docker image is not explicitly verified.
- No schema version field in the exported JSON/Parquet files. If the mapping table gains a new column, old R code reading the export will fail or silently ignore the new data.
- The CSV download (`src/blueprints/main.py` line 101) builds column names from Python string literals — these are not tested against the database schema to ensure they match.

**Prevention strategy:**
1. Add `pyarrow` and `openpyxl` to `requirements.txt` unconditionally, not as optional dependencies. In a Docker deployment, every advertised export format must work reliably.
2. Add an export schema version header to all export files: `ke_wp_schema_version: "1.0"` in JSON, a metadata column in Parquet, a comment row in CSV. Increment this on any column rename or addition.
3. Freeze the column names in exported files by mapping database field names to stable export column names in an explicit mapping dict. Changing the database column name does not automatically change the export column name.
4. Add integration tests that: (a) download an export, (b) read it back with pandas/R, (c) assert specific column names are present. Run these in CI.

**Phase:** Export stabilization — before any data export is cited in supplementary material.

---

## Pitfall 11: Pickle-based Embedding Loading Is a Deployment Security and Portability Risk

**What goes wrong:** `np.load(..., allow_pickle=True)` deserializes arbitrary Python objects embedded in the `.npy` file. If an attacker replaces the embedding files in the volume mount (or in a compromised Docker build), they achieve remote code execution in the server process. More practically, `allow_pickle=True` breaks across numpy major versions — numpy 2.0+ changed pickling behavior — and will fail silently or raise cryptic errors when dependencies are upgraded.

**Warning signs in this codebase:**
- `src/services/embedding.py` lines 142, 152, 162: all three `_load_precomputed_*` methods use `np.load(path, allow_pickle=True).item()`. The `.item()` call means the `.npy` file stores a Python `dict`, not a plain numpy array.
- `CONCERNS.md` security section confirms this vulnerability and notes: "current mitigation: embeddings are local files committed to git" — but moving to Docker volume mounts (Pitfall 4) removes this mitigation.
- No checksum verification exists for any of the 8 files in `data/`.

**Prevention strategy:**
1. Switch embedding storage from pickled `.npy` dict format to `.npz` (compressed numpy archive) with named arrays, which never requires `allow_pickle`. Rewrite the precomputation scripts to save with `np.savez_compressed(path, embeddings=array, ke_ids=ids_array)` and load with `np.load(path, allow_pickle=False)`.
2. Store an `sha256` checksum for each embedding file in `data/manifest.json`. Verify on startup:
   ```python
   if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["checksums"][filename]:
       raise RuntimeError(f"Embedding file {filename} failed integrity check")
   ```
3. Store embedding metadata (ke_id → index mapping) as a separate `data/ke_ids.json` array, not pickled inside the `.npy` file.

**Phase:** Security hardening — before Docker volume mounts are used in production.

---

## Pitfall 12: GitHub OAuth Excludes Collaborators Without GitHub Accounts

**What goes wrong:** The primary authentication mechanism is GitHub OAuth. International collaborators, toxicology regulators, and non-developer scientists commonly do not have GitHub accounts. The workshop guest code system exists but is admin-managed and has usage limits — it cannot scale to an open scientific community. Reviewers of the published paper who want to verify the tool will hit a login wall.

**Warning signs in this codebase:**
- `src/blueprints/auth.py`: the two auth paths are GitHub OAuth and admin-issued guest codes. There is no self-service registration.
- `GuestCodeModel.validate_code()` (line 971) checks `max_uses` — a guest code expires after a fixed number of uses, meaning codes distributed in a paper supplement will stop working.
- The explore page and API read endpoints are not listed as public in the blueprints — authentication may be required even for read-only access to the curated dataset.
- Workshop guest codes require GitHub OAuth *or* guest code — but the guest code form itself requires navigating the UI, which may time out for one-time paper reviewers.

**Prevention strategy:**
1. Make all read-only API endpoints (`GET /api/v1/mappings`, `/export/<format>`, `/health`) publicly accessible without authentication. Curation (submit, propose) requires login; consuming the data should not.
2. Make the explore page accessible to unauthenticated users. Only the submit/proposal UI requires login.
3. For guest codes distributed in paper supplements, remove the `max_uses` limit or set it very high (10,000+). The code is for identification, not access control.
4. Consider adding an email-based registration path (email + magic link) as a fallback for collaborators without GitHub accounts.

**Phase:** Access design — must be settled before paper submission so the supplement can include accurate instructions.

---

## Pitfall 13: No Audit Trail for Curation Decisions Undermines Scientific Reproducibility

**What goes wrong:** A published database must explain *why* each mapping exists. "KE:123 was mapped to WP456 with high confidence" is not scientifically useful without knowing who made that judgment, when, what alternatives were considered, and whether the mapping was proposed by the AI suggestion engine or by a human. Without this, readers cannot assess curation quality and the database cannot be re-curated by a different team.

**Warning signs in this codebase:**
- `src/core/models.py` `create_mapping()` stores `created_by` (GitHub username) and `created_at` — minimum provenance.
- But there is no field recording whether the mapping originated from a BioBERT suggestion (and at what score) or was entered manually.
- `ProposalModel.update_proposal_status()` (line 577) stores `admin_notes` but this field is optional and not displayed to curators.
- `CONCERNS.md`: "No Audit Trail for Admin Actions — no logging of which admin approved/rejected proposals."
- The `scoring_config.yaml` version is not stored with the mapping — a different scoring configuration could have produced a different top-10, meaning the curator's choice was partially algorithm-dependent.

**Prevention strategy:**
1. Add a `suggestion_score` column and `suggestion_method` column to the mappings table: store the `hybrid_score` and method string (`"biobert_suggestion"` vs `"manual_entry"`) at the time of submission.
2. Add an `approved_by` and `approved_at` column to the mappings table, populated when a proposal transitions to approved.
3. Make `admin_notes` on proposal approval/rejection required (minimum 20 characters). Surface this note to curators in their proposal history.
4. Store `scoring_config_version` at proposal submission time — even a simple git short-hash of `scoring_config.yaml` is sufficient for reproducibility.

**Phase:** Data model — add these columns before any curated data is used in publication figures.

---

## Summary Table

| # | Pitfall | Domain | Phase |
|---|---------|--------|-------|
| 1 | API without versioning locks in breaking changes | API design | Pre-publication |
| 2 | Gunicorn sync workers × BioBERT without preload = 4x memory | ML deployment | Pre-deployment |
| 3 | SQLite without WAL mode deadlocks under multi-worker | Database | Pre-deployment |
| 4 | Embedding files baked into Docker image | Data architecture | Before first Docker run |
| 5 | Curator UX failures: ambiguous feedback, no duplicate guard | Curation UX | Before external users |
| 6 | API returns display strings, not stable identifiers | API design | Before API publication |
| 7 | ML score instability makes curation non-reproducible | ML / Data provenance | Before publication data |
| 8 | SQLite file lost on container recreation | Deployment | Before external users |
| 9 | Rate limits with no Retry-After, no bulk endpoint | API design | Before API publication |
| 10 | Export format fragility breaks downstream pipelines | Data export | Before supplementary data |
| 11 | Pickle-based embedding loading: security + portability | Security | Before volume mounts |
| 12 | GitHub OAuth excludes non-developer scientists | Access design | Before paper submission |
| 13 | No audit trail for curation decisions | Data provenance | Before publication data |

---

*Research date: 2026-02-19*
