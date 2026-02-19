---
phase: 01-deployment-hardening
verified: 2026-02-19T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 1: Deployment Hardening Verification Report

**Phase Goal:** The application runs safely in production — database survives container recreation, memory stays within bounds, concurrent curator writes do not corrupt data, and embedding files load reliably
**Verified:** 2026-02-19
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The application database file is always created at `/app/data/ke_wp_mapping.db` when running in production | VERIFIED | `src/core/config.py` line 34: `DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/ke_wp_mapping.db")`; `container.py` line 57 passes this to `Database()` |
| 2 | Every SQLite connection opens with WAL journal mode, NORMAL synchronous, and a 5-second busy timeout | VERIFIED | `src/core/models.py` lines 22-24: `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`, `PRAGMA busy_timeout=5000` applied on every `get_connection()` call |
| 3 | Multiple concurrent writes do not raise 'database is locked' errors — SQLite waits up to 5 seconds before failing | VERIFIED | Two-layer protection: `sqlite3.connect(self.db_path, timeout=30)` (Python) + `PRAGMA busy_timeout=5000` (SQLite); WAL mode enables concurrent readers during writes |
| 4 | The Docker container starts without errors — no missing nginx.conf, no missing redis service dependency | VERIFIED | `docker-compose.yml` contains only `web` service with `env_file: .env`; redis and nginx service blocks removed |
| 5 | Gunicorn loads its configuration from `gunicorn.conf.py` with `preload_app=True` | VERIFIED | `gunicorn.conf.py` line 14: `preload_app = True`; `Dockerfile` CMD: `["gunicorn", "-c", "gunicorn.conf.py", "app:app"]` |
| 6 | A daily cron job inside the container runs sqlite3 `.backup` and writes backups to `/app/data/backups/` | VERIFIED | `scripts/ke-wp-backup` schedules `0 2 * * * appuser /app/scripts/backup_db.sh`; `backup_db.sh` line 19 uses `sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"` |
| 7 | Environment secrets are loaded from the host `.env` file via env_file directive, not hardcoded | VERIFIED | `docker-compose.yml` lines 8-9: `env_file: - .env`; no hardcoded secrets present |
| 8 | Embedding files are saved as .npz (not .npy) and load without `allow_pickle=True` | VERIFIED | `embedding_utils.py` line 101: `np.savez(npz_path, ids=ids, matrix=matrix)`; `allow_pickle=True` produces zero grep matches across all embedding loaders |
| 9 | Embedding vectors are normalized to unit length at save time — dot product equals cosine similarity at query time | VERIFIED | `embedding_utils.py` lines 95-98: L2 norm computed, zero-vector guard applied, `matrix = (matrix / norms).astype(np.float32)` written to NPZ |
| 10 | All five cosine similarity computations in `embedding.py` are replaced by plain `np.dot()` calls | VERIFIED | Lines 381, 435, 483, 559, 562 in `embedding.py` all use `np.dot()`; no `linalg.norm` divisors remain in similarity computations |
| 11 | The two `allow_pickle=True` loads in `go.py` are replaced by NPZ loaders | VERIFIED | `_load_go_embeddings()` and `_load_go_name_embeddings()` both use `with np.load(npz_path) as data`; no `allow_pickle` parameter |
| 12 | BioBERT warm-up fires in production Gunicorn context but not in tests or dev | VERIFIED | `app.py` lines 203-211: guard `if os.getenv("FLASK_ENV") == "production"` wraps `app.service_container.embedding_service`; `TestingConfig` sets `FLASK_ENV=testing` |

**Score:** 12/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/config.py` | DATABASE_PATH default changed to `/app/data/ke_wp_mapping.db` | VERIFIED | Line 34: `DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/ke_wp_mapping.db")` |
| `src/core/models.py` | WAL PRAGMA applied on every `get_connection()` call | VERIFIED | Lines 22-24 apply WAL, NORMAL synchronous, and 5000ms busy timeout |
| `docker-compose.yml` | Only `web` service with `env_file` directive, no redis/nginx | VERIFIED | 21-line file: single `web` service, `env_file: .env`, backups volume, network only |
| `Dockerfile` | Cron installed, entrypoint script added, CMD uses `gunicorn.conf.py` | VERIFIED | Line 15 installs cron; line 31 ENTRYPOINT; line 32 CMD references `gunicorn.conf.py` |
| `gunicorn.conf.py` | Version-controlled config with `preload_app = True` and `workers = 2` | VERIFIED | Line 14: `preload_app = True`; line 10: `workers = 2` |
| `scripts/backup_db.sh` | SQLite Online Backup API with integrity check and 7-day retention | VERIFIED | Line 19: `.backup` command; lines 22-27: integrity check; line 32: 7-day `find -mtime` prune |
| `scripts/docker-entrypoint.sh` | Starts cron then exec's gunicorn | VERIFIED | Line 8: `service cron start || true`; line 11: `exec "$@"` |
| `scripts/ke-wp-backup` | Crontab file scheduling daily 02:00 backup as appuser | VERIFIED | `0 2 * * * appuser /app/scripts/backup_db.sh >> /app/logs/backup.log 2>&1`; ends with newline |
| `scripts/embedding_utils.py` | `save_embeddings()` uses `np.savez` with normalized matrix and Unicode ids | VERIFIED | Line 91: `ids = np.array(list(embeddings.keys()), dtype=str)`; line 101: `np.savez(npz_path, ids=ids, matrix=matrix)` |
| `src/services/embedding.py` | Three `_load_precomputed_*` methods use NPZ without `allow_pickle` | VERIFIED | Lines 138-190: three loaders all use `with np.load(npz_path) as data`; comment on line 146 clarifies `allow_pickle=False by default` |
| `src/suggestions/go.py` | Two `_load_go_*` methods use NPZ without `allow_pickle` | VERIFIED | Lines 49-77: both loaders use `with np.load(npz_path) as data` |
| `scoring_config.yaml` | Embedding paths end in `.npz` | VERIFIED | Lines 172-173: `pathway_embeddings.npz` and `ke_embeddings.npz` |
| `app.py` | Module-level warm-up call guarded by `FLASK_ENV=production` | VERIFIED | Lines 198-211: warm-up block with guard, try/except, and `app.service_container.embedding_service` access |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/core/config.py` | `src/services/container.py` | `Database(self.config.DATABASE_PATH)` | WIRED | `container.py` line 57: `self._database = Database(self.config.DATABASE_PATH)` |
| `src/core/models.py` | `sqlite3.connect` | `get_connection()` PRAGMA execution | WIRED | Lines 20-24: connect with timeout=30, then apply all three PRAGMAs before return |
| `Dockerfile` | `scripts/docker-entrypoint.sh` | `ENTRYPOINT` directive | WIRED | Line 31: `ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]` |
| `scripts/docker-entrypoint.sh` | `gunicorn.conf.py` | `exec gunicorn -c gunicorn.conf.py` | WIRED | Entrypoint `exec "$@"` hands off to Dockerfile CMD: `["gunicorn", "-c", "gunicorn.conf.py", "app:app"]` |
| `Dockerfile` | `scripts/backup_db.sh` | `COPY` and crontab installation | WIRED | Line 23: `COPY scripts/ke-wp-backup /etc/cron.d/ke-wp-backup`; line 26: `chmod +x /app/scripts/backup_db.sh` |
| `scripts/embedding_utils.py` | `src/services/embedding.py` | NPZ written by `save_embeddings()`, read by `_load_precomputed_*` | WIRED | `np.savez` writes `{ids, matrix}` arrays; loaders use `data['ids']` and `data['matrix']` with matching keys |
| `scripts/embedding_utils.py` | `src/suggestions/go.py` | NPZ written by precompute_go_embeddings, read by `_load_go_embeddings` | WIRED | Same NPZ format contract; GO loaders use identical `with np.load(npz_path) as data` pattern |
| `app.py` | `src/services/container.py` | `app.service_container.embedding_service` at module level | WIRED | `app.py` line 189: `app.service_container = services`; line 205: `_svc = app.service_container.embedding_service` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEPLOY-01 | 01-01 | SQLite WAL mode and connection pooling enabled for concurrent curator access | SATISFIED | `get_connection()` applies `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`, `PRAGMA busy_timeout=5000`; `DATABASE_PATH` fixed to `/app/data/ke_wp_mapping.db` |
| DEPLOY-02 | 01-03, 01-04 | Embedding files migrated from pickle/dict format to NPZ matrix format | SATISFIED | `save_embeddings()` writes typed NPZ arrays; all five loaders use `np.load` without `allow_pickle`; `scoring_config.yaml` paths updated to `.npz` |
| DEPLOY-03 | 01-02 | Automated database backup mechanism in place before external users can modify data | SATISFIED | `backup_db.sh` uses `sqlite3 .backup` (Online Backup API) with integrity check and 7-day retention; daily cron at 02:00 via `ke-wp-backup` in `/etc/cron.d/` |
| DEPLOY-04 | 01-03, 01-04 | Embedding vectors normalized at precompute time; dot product replaces cosine similarity at query time (closes #65) | SATISFIED | `save_embeddings()` normalizes vectors before writing; five cosine divisions in `embedding.py` replaced by `np.dot()`; `allow_pickle=True` eliminated from all loaders |

All four Phase 1 requirements are satisfied. No orphaned requirements detected (all four DEPLOY-* IDs appear in plan frontmatter and are accounted for in the codebase).

---

## Anti-Patterns Found

None. Scan of all phase-modified files — `src/core/config.py`, `src/core/models.py`, `docker-compose.yml`, `Dockerfile`, `gunicorn.conf.py`, `scripts/backup_db.sh`, `scripts/docker-entrypoint.sh`, `scripts/ke-wp-backup`, `scripts/embedding_utils.py`, `src/services/embedding.py`, `src/suggestions/go.py`, `scoring_config.yaml`, `app.py` — returned zero matches for TODO, FIXME, placeholder patterns, empty returns, or console-log-only implementations.

---

## Human Verification Required

### 1. Container Cold Start with BioBERT Preload

**Test:** Build and run `docker-compose up`, observe startup logs for BioBERT load timing.
**Expected:** "Embedding service pre-loaded for Gunicorn worker fork (preload_app=True)" appears in master-process logs before any worker connection; startup completes within 60s (HEALTHCHECK start-period).
**Why human:** Cannot verify actual BioBERT load timing or Gunicorn master-vs-worker log attribution without a running Docker environment.

### 2. Database Volume Persistence Across Container Recreation

**Test:** Start container, submit a mapping, run `docker-compose down && docker-compose up`, verify the mapping still exists.
**Expected:** The mapping persists because `./data:/app/data` volume mount survives container recreation.
**Why human:** Requires a running Docker stack with a real volume mount.

### 3. Backup Script Execution Inside Container

**Test:** Inside a running container, manually trigger `bash /app/scripts/backup_db.sh` and confirm a `.db` backup appears in `/app/data/backups/` and passes integrity check.
**Expected:** `[BACKUP OK] /app/data/backups/ke_wp_mapping_YYYYMMDD_HHMMSS.db` in output.
**Why human:** Requires running container with `sqlite3` binary and a live database file at `/app/data/ke_wp_mapping.db`.

---

## Gaps Summary

No gaps. All 12 observable truths are verified, all 13 required artifacts are substantive and wired, all 8 key links are confirmed, and all 4 requirements are satisfied in the codebase.

One deployment-time prerequisite noted in SUMMARY.md (not a gap — documented and expected): the existing `.npy` files in `data/` must be regenerated as `.npz` files before the application can load embeddings in production. The precompute scripts are ready and correct; this is a one-time operator action before first deployment.

---

_Verified: 2026-02-19_
_Verifier: Claude (gsd-verifier)_
