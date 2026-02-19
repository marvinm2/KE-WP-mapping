# Codebase Concerns

**Analysis Date:** 2026-02-19

## Tech Debt

**Pickle-based Embedding Serialization:**
- Issue: Pre-computed embeddings loaded using `np.load(..., allow_pickle=True)` in `src/services/embedding.py` lines 142, 152, 162
- Files: `src/services/embedding.py` (_load_precomputed_embeddings, _load_precomputed_ke_embeddings, _load_precomputed_pathway_title_embeddings)
- Impact: Security vulnerability (arbitrary code execution risk if embedding files are compromised), performance overhead from pickling, breaks numpy compatibility guarantees
- Fix approach: Migrate to SafeEmbeddings loader that validates embedding structure before deserialization, or switch to `.npz` (compressed binary) format with explicit field validation. Validate file integrity with checksums.

**Global Module Variables in API Blueprint:**
- Issue: Global state management for models in `src/blueprints/api.py` lines 39-48 (mapping_model, proposal_model, cache_model, etc.)
- Files: `src/blueprints/api.py` with setter function `set_models()` lines 51-66
- Impact: Makes testing harder (requires global state setup), race conditions in concurrent requests if models are mutable, tight coupling between blueprint and container
- Fix approach: Use Flask's application context (`g` object) or dependency injection decorator instead of module-level globals. Pass models as parameters to request handlers.

**Missing Data Validation on Uploaded Embeddings:**
- Issue: No integrity checks on pre-computed embedding files after loading in `src/services/embedding.py`
- Files: `src/services/embedding.py` lines 119-130, 138-166
- Impact: Silent failures if embedding files are corrupted or truncated, producing incorrect similarity scores without warnings
- Fix approach: Add shape/dtype validation after loading, compute file checksums during precomputation scripts and verify on load

**Hardcoded File Paths in Embedding Service:**
- Issue: Path to pathway title embeddings hardcoded as `'data/pathway_title_embeddings.npy'` in `src/services/embedding.py` line 129
- Files: `src/services/embedding.py`
- Impact: Path resolution issues in different deployment environments (Docker, testing), not configurable via ServiceContainer
- Fix approach: Pass all embedding file paths through config/container initialization, make relative to PROJECT_ROOT with fallback

**Module-level Cache with Inconsistent TTL:**
- Issue: Module-level `_config_cache` in `src/blueprints/api.py` lines 32-35 with 5-minute TTL
- Files: `src/blueprints/api.py`
- Impact: Stale scoring config after updates, no cache invalidation mechanism, different TTL than database cache if any
- Fix approach: Centralize cache handling through ServiceContainer, use consistent TTL across all caches, add manual invalidation endpoint

## Known Bugs

**Embedding Pre-computation Script Limitations:**
- Symptoms: GO embeddings may not cover all terms in live GO database if new terms are added
- Files: `scripts/precompute_go_embeddings.py` (not in src/ but critical)
- Trigger: New GO terms added to SPARQL endpoint after precomputation
- Workaround: Re-run precomputation scripts periodically (documented in CLAUDE.md)
- Fix approach: Implement incremental embedding precomputation to handle updates without full re-run

**Entity Extraction May Lose Context:**
- Symptoms: Extracted biological entities in `src/services/embedding.py` line 343-344 may remove important text, reducing embedding specificity
- Files: `src/services/embedding.py` (_extract_entities calls)
- Trigger: KE titles with predominantly non-entity content (e.g., "Increased expression")
- Workaround: Entity extraction disabled by default in config
- Fix approach: Profile embedding quality impact with/without entity extraction on validation set

**Silent Embedding Fallback to Zeros:**
- Symptoms: If encoding fails, service returns zero vector in `src/services/embedding.py` line 291
- Files: `src/services/embedding.py` encode() method
- Trigger: Out-of-memory errors on large batch encoding, unicode issues in text
- Workaround: Smaller batch sizes can mitigate, but zero vector produces false negatives
- Fix approach: Log encoding failures with text snippet for debugging, return null/error indicator instead of zero vector

## Security Considerations

**Pickle Deserialization Vulnerability:**
- Risk: Arbitrary code execution if pickled embedding files are replaced with malicious payloads
- Files: `src/services/embedding.py` lines 142, 152, 162 (_load_precomputed_* methods)
- Current mitigation: Embeddings are local files committed to git, not downloaded at runtime
- Recommendations:
  1. Use `allow_pickle=False` and switch to `.npz` format for all embeddings
  2. Add cryptographic signature verification for embedding files
  3. Store embeddings in read-only location with integrity checks

**Environment Variable Management:**
- Risk: Secrets (.env) may leak if accidentally committed; no evidence of .env validation
- Files: Configuration loaded via `python-dotenv` in app initialization
- Current mitigation: `.env` is in `.gitignore`, not readable in CLAUDE.md
- Recommendations:
  1. Add startup validation that all required secrets are present
  2. Log which env vars are missing (without showing values) on startup failure
  3. Consider secret rotation mechanism for long-running deployments

**SPARQL Endpoint Injection:**
- Risk: Endpoint URLs hardcoded in suggestion services, could be exploited if config is compromised
- Files: `src/suggestions/pathway.py` lines 29-30, `src/suggestions/go.py` (similar pattern)
- Current mitigation: Endpoints are fixed to official services
- Recommendations:
  1. Make endpoints configurable through config validation
  2. Validate endpoint URLs against allowlist during service initialization
  3. Add request signing/authentication if endpoints change

**Module-level Cache Poisoning:**
- Risk: Scoring config cache in `src/blueprints/api.py` can be poisoned if ConfigLoader returns malicious data
- Files: `src/blueprints/api.py` lines 32-35, config caching mechanism
- Current mitigation: ConfigLoader validates schema
- Recommendations:
  1. Add integrity validation to cached objects
  2. Set cache size limits to prevent memory exhaustion
  3. Add cache eviction for any validation failures

## Performance Bottlenecks

**Batch Similarity Computation Memory Usage:**
- Problem: `compute_ke_pathways_batch_similarity()` in `src/services/embedding.py` loads ALL pathway embeddings into memory (line 509-534)
- Files: `src/services/embedding.py` lines 476-574
- Cause: Converting entire pathway list to numpy arrays before vectorized dot product
- Current behavior: ~1000 pathways × 768 dimensions = 3MB per request, OK for current scale
- Improvement path:
  1. Implement streaming similarity computation in chunks (e.g., 100 pathways at a time)
  2. Add early stopping if top-K scores are found and remaining scores can't exceed
  3. Cache pre-computed embeddings in memory with LRU eviction for frequently-used pathways

**Entity Extraction on Every Embedding:**
- Problem: `_extract_entities()` called separately for KE and each pathway in `compute_ke_pathways_batch_similarity()` (lines 498, 526)
- Files: `src/services/embedding.py` lines 501-527
- Cause: Entity extraction is applied per-text, not amortized across requests
- Improvement path:
  1. Pre-compute entity-extracted versions of KE/pathway titles during precomputation
  2. Cache extraction results by text hash with TTL
  3. Profile impact of entity extraction on final score quality to justify the overhead

**SPARQL Query Caching TTL:**
- Problem: Cache TTL hardcoded at database schema level, no way to adjust per query type
- Files: `src/core/models.py` (cache table design) and SPARQL endpoints usage
- Cause: Gene queries and ontology queries may have different staleness tolerance
- Improvement path:
  1. Add configurable TTL per query type (gene queries: 24h, ontology: 7d)
  2. Implement cache warming for frequently-accessed queries
  3. Monitor cache hit rates and adjust TTLs based on staleness vs hit rate

**LRU Cache Size Limit (1000 items):**
- Problem: Embedding encode() method uses `@lru_cache(maxsize=1000)` in `src/services/embedding.py` line 275
- Files: `src/services/embedding.py` line 275
- Cause: Fixed cache size may be too small for production with many unique texts or too large for memory-constrained environments
- Improvement path:
  1. Make cache size configurable via ServiceContainer
  2. Monitor cache hit rate and resize dynamically
  3. Consider two-level cache: in-memory (1000) + disk-backed (unlimited)

**Pre-computed Data Load on Startup:**
- Problem: All embedding files loaded into memory on ServiceContainer initialization, even if requests don't use all of them
- Files: `src/services/container.py` (initialization) and `src/services/embedding.py` (loading)
- Cause: Eager loading strategy in BiologicalEmbeddingService constructor
- Improvement path:
  1. Implement lazy loading: only load embedding files when first needed
  2. Add configuration option to load only specific embeddings (e.g., pathway-only for some deployments)
  3. Monitor memory usage in production and implement disk-backed cache for less-used embeddings

## Fragile Areas

**Multi-signal Scoring Hybrid Logic:**
- Files: `src/suggestions/scoring.py` (combine_scored_items function, lines 13-105), `src/suggestions/pathway.py` (_combine_multi_signal_suggestions)
- Why fragile:
  1. Hard-coded signal weights (gene=0.35, text=0.25, embedding=0.40) repeated across files
  2. Multi-evidence bonus (0.05) applied mechanically without per-signal validation
  3. No way to enable/disable individual signals without code changes
  4. Score cap (0.98) and threshold (0.15) duplicated across different scoring functions
- Safe modification:
  1. Centralize ALL scoring parameters in `scoring_config.yaml` with schema validation
  2. Load weights/thresholds through ConfigLoader at service initialization
  3. Add scoring debug mode that logs per-signal scores for each result
- Test coverage: Query-based tests exist but no tests for weight sensitivity or threshold edge cases

**Embedding Service Score Transformation:**
- Files: `src/services/embedding.py` (lines 187-273: _transform_similarity_score and _transform_similarity_batch)
- Why fragile:
  1. Power exponent (4.0) hard-coded, highly sensitive to small changes (0.1 exponent = 10-20% score shift)
  2. No validation that transformed scores stay within claimed [output_min, output_max] bounds
  3. Batch transformation assumes identical distribution as single-item transformation
  4. Skip-precomputed flag (line 513) inverts the normal logic, confusing to readers
- Safe modification:
  1. Always validate bounds after transformation with explicit assertions
  2. Add unit tests comparing single vs batch transformation output
  3. Add CLI tool to visualize score distribution before/after transformation
  4. Document why power transformation is necessary (BioBERT score clustering) with examples
- Test coverage: No tests for score transformation bounds or batch consistency

**Global Admin Users Validation:**
- Files: `src/core/config.py` (ADMIN_USERS config), `src/blueprints/admin.py` (is_admin check), `src/blueprints/main.py`
- Why fragile:
  1. Admin status cached in context processor, expires only on app reload
  2. No way to revoke admin without restarting
  3. ADMIN_USERS is comma-separated string, easy to parse incorrectly (no test coverage visible)
  4. is_admin context processor may not work in all request contexts
- Safe modification:
  1. Load admin users from database instead of config
  2. Add explicit is_admin() function calls with logging instead of context processor
  3. Add tests for comma-separated parsing, empty string, and whitespace handling
- Test coverage: test_app.py exists but no visible admin-specific tests

**Pathway Metadata and KE Metadata Loading:**
- Files: `src/suggestions/pathway.py` (uses ke_metadata, pathway_metadata passed from container), `src/blueprints/main.py`
- Why fragile:
  1. Metadata files (data/ke_metadata.json, data/pathway_metadata.json) loaded on startup, no validation
  2. If metadata files are missing, dropdown functionality silently fails
  3. No versioning or integrity check for metadata alignment with actual SPARQL data
  4. Metadata update requires app restart
- Safe modification:
  1. Add startup validation that metadata files exist and parse correctly
  2. Log metadata shape (number of KEs, pathways) on startup for sanity checking
  3. Implement hot-reload for metadata on file change (or endpoint to reload)
  4. Store metadata version in file and validate compatibility
- Test coverage: test_app.py may test some imports but not metadata completeness

## Scaling Limits

**SQLite Database Concurrency:**
- Current capacity: Single-file SQLite supports ~10-20 concurrent writers before lock contention
- Limit: Beyond 50-100 concurrent active users with write operations, database locks will cause timeouts
- Scaling path:
  1. For <100 users: Keep SQLite, increase timeout and WAL mode (already enabled?)
  2. For 100-1000 users: Migrate to PostgreSQL with connection pooling
  3. Add write queue for submissions if spike loads detected

**Pre-computed Embedding Size:**
- Current capacity:
  - KE embeddings: 1561 KEs × 768 dims = ~5MB
  - Pathway embeddings: 1012 pathways × 768 dims = ~3MB
  - GO embeddings: ~30K terms × 768 dims = ~90MB
- Limit: Total ~100MB in memory; can scale to ~1-2GB before memory pressure on standard server
- Scaling path:
  1. Implement embedding quantization (fp32 → int8) for 4x compression
  2. Add lazy-loading per category (load only on first request)
  3. Consider approximate similarity search (faiss, annoy) for faster 10K+ term searches

**Session Storage:**
- Current: Flask session middleware (likely in-memory or SQLite)
- Limit: With 10K+ concurrent users, session storage becomes bottleneck
- Scaling path:
  1. Switch to Redis-backed sessions for distributed deployments
  2. Implement session cleanup for inactive users

**SPARQL Rate Limiting:**
- Current: 500 requests/hour limit per endpoint (src/services/rate_limiter.py)
- Limit: High-traffic periods could hit limit and degrade UX
- Scaling path:
  1. Implement request batching for SPARQL queries
  2. Add response caching layer (Redis)
  3. Monitor rate limit hits and pre-fetch frequently-used data

## Dependencies at Risk

**Sentence-Transformers & PyTorch:**
- Risk: Large dependencies (~500MB PyTorch download), may have security updates
- Impact: Slow deployments, potential breaking changes in transformers API
- Migration plan:
  1. Explore lighter alternatives (DistilBERT, MiniLM) for faster loading
  2. Consider ONNX export of BioBERT for lighter runtime
  3. Monitor security advisories for transformers/pytorch

**Authlib:**
- Risk: OAuth library with moderate maintenance activity
- Impact: GitHub OAuth flow breaking if API changes
- Migration plan:
  1. Add fallback guest authentication (already implemented for workshops)
  2. Monitor GitHub OAuth API deprecations
  3. Consider custompython-requests based OAuth if authlib unmaintained

**External SPARQL Endpoints:**
- Risk: AOP-Wiki and WikiPathways SPARQL endpoints are external dependencies
- Impact: Service degradation if endpoints go offline or change format
- Mitigation: Pre-computed metadata and embeddings reduce runtime dependency
- Plan:
  1. Monitor endpoint health with periodic ping
  2. Implement graceful degradation when endpoints unavailable
  3. Cache SPARQL responses aggressively (24h+ for stable data)

## Missing Critical Features

**No Data Validation on Pre-computed Files:**
- Problem: Embedding files loaded without shape/type verification
- Blocks: Can't safely update embeddings without manual validation
- Fix: Add embedding file schema validation at load time

**No Embedding File Integrity Checks:**
- Problem: No way to detect corrupted or out-of-date embedding files
- Blocks: Production deployments can't self-heal from file corruption
- Fix: Add checksums to embedding files and validate on startup

**No Audit Trail for Admin Actions:**
- Problem: No logging of which admin approved/rejected proposals
- Blocks: Can't trace proposal history or admin decision rationale
- Fix: Add audit table tracking admin actions with timestamps and reasons

**No Duplicate Mapping Detection at Submission:**
- Problem: User can submit identical KE-WP pairs if they exist in different formats
- Blocks: Dataset can accumulate duplicates without admin intervention
- Fix: Implement fuzzy matching for KE/pathway names during submission check

## Test Coverage Gaps

**Embedding Service Transformation:**
- What's not tested: Score transformation bounds validation, batch vs single consistency, edge cases (zero similarity, max similarity)
- Files: `src/services/embedding.py` (_transform_similarity_score, _transform_similarity_batch)
- Risk: Silent score inflation/deflation if transformation parameters are misconfigured
- Priority: High (affects all pathway suggestions)

**Multi-signal Scoring Edge Cases:**
- What's not tested: Weight sum validation (should equal 1.0), single-signal results, zero-score items, score cap enforcement
- Files: `src/suggestions/scoring.py` (combine_scored_items)
- Risk: Unexpected score ranges or rankings from weight misconfiguration
- Priority: High (affects ranking quality)

**Rate Limiter Concurrency:**
- What's not tested: Multiple rapid requests from same IP, concurrent limit calculation
- Files: `src/services/rate_limiter.py`
- Risk: Race conditions allowing limit bypass under load
- Priority: Medium

**Admin Authentication:**
- What's not tested: Admin context processor in all request types, ADMIN_USERS parsing edge cases
- Files: `src/blueprints/admin.py`, `src/blueprints/main.py`
- Risk: Unauthorized admin access or broken admin UI
- Priority: High

**KE/Pathway Metadata Completeness:**
- What's not tested: Missing metadata entries, parsing failures, version mismatches
- Files: `src/suggestions/pathway.py`, `src/blueprints/main.py`
- Risk: Silent dropdown failures if metadata is incomplete
- Priority: Medium

---

*Concerns audit: 2026-02-19*
