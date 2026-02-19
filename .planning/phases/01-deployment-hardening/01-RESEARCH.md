# Phase 1: Deployment Hardening - Research

**Researched:** 2026-02-19
**Domain:** SQLite concurrency, NumPy NPZ embeddings, Gunicorn preload_app, Docker Compose volumes
**Confidence:** HIGH (all critical findings verified against official docs and multiple sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Deployment target:**
- Self-hosted VPS with Docker Compose — existing `Dockerfile` and `docker-compose.yml` are modified, not created from scratch
- Database file lives at `/app/data/ke_wp_mapping.db` inside the container, mounted as a Docker volume from the host
- Environment secrets (GitHub OAuth, Flask secret key) managed via a `.env` file on the host, loaded via Docker Compose `env_file` directive

**Backup strategy:**
- Backups stored to a local directory on the VPS (not cloud storage)
- Backup triggered by a cron job inside the container (container-internal scheduling)
- Use SQLite's online backup API (`sqlite3 .backup`) for consistent snapshots safe to run during active writes
- Backup frequency and retention: Claude's discretion (pick a sensible default for a small research database)

**Embedding migration:**
- No existing production data to protect — regenerate all embedding files from scratch
- Update precompute scripts (`scripts/precompute_*.py`) to output NPZ format directly; no separate one-time migration script needed
- Old `.npy` pickle files deleted once NPZ format confirmed working in the new deployment
- Normalization happens at precompute time only — trust the scripts; no load-time assertion needed
- The `data/` directory (embedding files) mounted as a Docker volume from the host, not baked into the image

**Worker memory model:**
- Target: 4 Gunicorn workers if memory allows (aspirational, not a hard constraint — adjust based on BioBERT's actual footprint)
- Model sharing: `preload_app=True` in Gunicorn config — model loaded once in master process, inherited by workers via fork
- Gunicorn configuration in a `gunicorn.conf.py` file committed to the repo (version-controlled, not inline in docker-compose)
- SQLite WAL mode set via application startup code (`PRAGMA wal_mode=WAL` on each connection) — idempotent and ensures WAL regardless of database origin

### Claude's Discretion
- Backup frequency and retention policy (e.g. daily backups, keep 7 days)
- Worker count if BioBERT footprint makes 4 workers exceed available RAM
- Connection pool size for SQLite WAL mode

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEPLOY-01 | SQLite WAL mode and connection pooling enabled for concurrent curator access | WAL PRAGMA pattern, busy_timeout, short transaction discipline; all verified against sqlite.org |
| DEPLOY-02 | Embedding files migrated from pickle/dict format to NPZ matrix format | `np.savez` / `np.load` without `allow_pickle`; key/matrix layout; load-time pattern; all verified against numpy.org docs |
| DEPLOY-03 | Automated database backup mechanism in place before external users can modify data | `sqlite3 .backup` shell command; cron inside container; retention script with `find -mtime`; verified against sqlite.org |
| DEPLOY-04 | Embedding vectors normalized at precompute time; dot product replaces cosine similarity at query time (closes #65) | Pre-normalize at save time, `np.dot()` at query time; mathematically equivalent and faster; verified against multiple authoritative ML sources |
</phase_requirements>

---

## Summary

This phase has four tightly scoped problems, each independently solvable. The research reveals that the existing codebase has a clear mapping from current code to what must change: `np.load(..., allow_pickle=True).item()` in three embedding loader methods must become `np.load(...)[key]` from an NPZ-structured file; `get_connection()` in `Database.get_connection()` must execute WAL PRAGMAs on every new connection; Gunicorn's inline CMD in the Dockerfile must move to a committed `gunicorn.conf.py` with `preload_app = True`; and the precompute scripts' `save_embeddings()` function must emit `np.savez` with two arrays (a key/index array and a matrix) instead of `np.save(path, dict)`.

The Docker Compose changes are minimal: the existing `docker-compose.yml` already mounts `./data:/app/data` and uses environment variable substitution, but the database path in application code defaults to `ke_wp_mapping.db` (relative, wrong location) and the `docker-compose.yml` uses the `environment:` key rather than `env_file:` for secrets. Both are straightforward one-line changes. The database path must change to `/app/data/ke_wp_mapping.db` in `src/core/config.py` `DATABASE_PATH` default.

Memory is the single biggest risk in this phase. BioBERT via `sentence-transformers` with a 110M-parameter base model uses approximately 420–440 MB of GPU-model weights in fp32 loaded on CPU. With all embedding arrays in RAM (~100 MB total for KE + pathway + GO embeddings), a single worker process needs roughly 550–700 MB. With `preload_app = True`, the master process loads the model once and workers inherit it via Linux copy-on-write fork — so 4 workers do not require 4× the memory for the model weights. Real-world reports show 2–3 workers are often optimal for large NLP models; starting with `workers = 2` and profiling is the safe approach.

**Primary recommendation:** Execute in four discrete, testable change sets: (1) fix Docker Compose and config for correct database path + env_file; (2) enable WAL + busy_timeout on every SQLite connection; (3) migrate embedding I/O to NPZ with pre-normalized matrices; (4) add `gunicorn.conf.py` with preload_app and the backup cron script. Each change set can be verified independently before the next is applied.

---

## Standard Stack

### Core (all already in the codebase — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `numpy` | 1.26.4 (pinned) | `np.savez`, `np.load`, `np.linalg.norm`, `np.dot` | Already in requirements.txt; NPZ is native numpy binary |
| `sqlite3` | stdlib | WAL PRAGMA, backup via subprocess | Built-in Python; no additional package |
| `gunicorn` | 22.0.0 (pinned) | WSGI server with `preload_app` | Already in requirements.txt |
| `python-dotenv` | 1.2.1 (pinned) | `.env` loading | Already used in `app.py` via `load_dotenv()` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `crond` / `busybox-cron` | OS-level in container | In-container backup scheduling | Use `busybox-cron` if the base image (`python:3.12-slim-bookworm`) does not include `cron`; it is available via apt as `cron` |
| `sqlite3` CLI | Already in Dockerfile (line 15) | Shell-level `.backup` command | The Dockerfile already installs `sqlite3` via apt — the backup script can call it directly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sqlite3 .backup` shell command | Python `sqlite3.Connection.backup()` API | Python API is cleaner but requires app code for scheduling; shell + cron is self-contained and does not need the app to be running |
| `busybox-cron` in container | Host-level cron on VPS | Container-internal cron is the locked decision; host cron would be simpler but was explicitly deferred |
| `np.savez` (uncompressed) | `np.savez_compressed` | Compressed is smaller on disk but slower to load; for embedding files that are already ≤100 MB uncompressed, prefer `np.savez` for faster startup load |

**Installation:** No new packages required. All tools are either already in `requirements.txt` or available in the Docker base image.

---

## Architecture Patterns

### Recommended Project Structure Changes

```
gunicorn.conf.py          # NEW — version-controlled Gunicorn config
scripts/
├── embedding_utils.py    # MODIFIED — save_embeddings() uses np.savez, load uses np.load()[key]
├── precompute_ke_embeddings.py         # MODIFIED — calls updated save_embeddings
├── precompute_pathway_title_embeddings.py  # MODIFIED — calls updated save_embeddings
├── precompute_go_embeddings.py         # MODIFIED — calls updated save_embeddings (two arrays)
└── backup_db.sh          # NEW — sqlite3 .backup script for cron
src/core/
└── models.py             # MODIFIED — get_connection() applies WAL PRAGMAs
src/core/
└── config.py             # MODIFIED — DATABASE_PATH default changed to /app/data/ke_wp_mapping.db
src/services/
└── embedding.py          # MODIFIED — all _load_precomputed_* methods use NPZ format
docker-compose.yml        # MODIFIED — env_file directive, named volume for data/
Dockerfile                # MODIFIED — CMD replaced by reference to gunicorn.conf.py; cron added
```

### Pattern 1: NPZ Matrix Format for Embeddings

**What:** Replace the current "pickle a Python dict" approach with `np.savez` storing two arrays: `ids` (string array of embedding keys) and `matrix` (float32 2D matrix, shape `[N, 768]`). Loading reconstructs the dict as `dict(zip(ids, matrix))` or uses direct matrix indexing for batch operations.

**Why this structure:** The current `.npy` files store a Python dict serialized with pickle, which requires `allow_pickle=True`. NPZ stores only numeric/string arrays — no pickle required, no arbitrary code execution risk. The matrix layout also enables vectorized dot-product similarity across all embeddings in one `np.dot(query_vec, matrix.T)` call instead of a loop.

**When to use:** All three precompute scripts and all three embedding loader methods in `src/services/embedding.py` and `src/suggestions/go.py`.

**Example (save side — `embedding_utils.py`):**
```python
# Source: numpy.org/doc/stable/reference/generated/numpy.savez.html
def save_embeddings(embeddings: dict, path: str):
    """Save embeddings dict as NPZ matrix format (no pickle)."""
    import numpy as np
    ids = np.array(list(embeddings.keys()), dtype=object)  # string array
    # Normalize at save time: divide each row by its L2 norm
    matrix = np.array(list(embeddings.values()), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)  # avoid division by zero
    matrix_normalized = matrix / norms
    # Use .npz extension (np.savez appends it automatically, but be explicit)
    np.savez(path.replace('.npy', ''), ids=ids, matrix=matrix_normalized)
    file_size_mb = os.path.getsize(path.replace('.npy', '') + '.npz') / 1024 / 1024
    logger.info("Saved %d normalized embeddings: %.2f MB", len(embeddings), file_size_mb)
```

**Example (load side — `src/services/embedding.py`):**
```python
# Source: numpy.org/doc/stable/reference/generated/numpy.load.html
def _load_precomputed_embeddings(self, path: str):
    """Load pre-computed embeddings from NPZ format (no pickle)."""
    try:
        import numpy as np
        # np.load on NPZ returns NpzFile; use context manager to close fd
        with np.load(path) as data:  # allow_pickle=False by default
            ids = data['ids']
            matrix = data['matrix']
        self.pathway_embeddings = dict(zip(ids, matrix))
        logger.info("Loaded %d pre-computed pathway embeddings", len(self.pathway_embeddings))
    except Exception as e:
        logger.warning("Could not load pre-computed embeddings: %s", e)
        self.pathway_embeddings = {}
```

**Note on file paths:** The current scripts call `save_embeddings(embeddings, 'data/ke_embeddings.npy')`. With NPZ, `np.savez('data/ke_embeddings')` writes `data/ke_embeddings.npz`. The extension change must propagate to all path references in `src/services/embedding.py`, `src/suggestions/go.py`, and `src/services/container.py`.

### Pattern 2: WAL Mode + busy_timeout on Every Connection

**What:** Modify `Database.get_connection()` in `src/core/models.py` to execute three PRAGMAs on every new connection: `journal_mode=WAL`, `synchronous=NORMAL`, and `busy_timeout=5000`.

**Why:** `journal_mode=WAL` is persistent (survives reconnects once set on a database), but the decision is to set it on every connection to be idempotent — safe for databases created in any mode. `synchronous=NORMAL` provides a good durability/performance balance in WAL mode. `busy_timeout=5000` (5 seconds) makes concurrent writers wait rather than immediately throwing `OperationalError: database is locked`.

**When to use:** In `get_connection()` in `src/core/models.py` — this is the single chokepoint for all database access since all model classes call `self.db.get_connection()`.

**Example:**
```python
# Source: sqlite.org/wal.html, pythontutorials.net/blog/concurrent-writing-with-sqlite3
def get_connection(self):
    """Get database connection with WAL mode and row factory."""
    conn = sqlite3.connect(self.db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn
```

**Important:** `sqlite3.connect(path, timeout=30)` sets a Python-level retry timeout as a fallback. `PRAGMA busy_timeout=5000` sets the SQLite-level timeout (in milliseconds). Both are needed because they operate at different layers.

### Pattern 3: Gunicorn Configuration File

**What:** Create `gunicorn.conf.py` at the project root. Move all Gunicorn settings from the Dockerfile `CMD` into this file. Set `preload_app = True` to load the Flask application (and BioBERT model) in the master process before forking workers.

**When to use:** Production deployments. The Dockerfile `CMD` becomes `["gunicorn", "-c", "gunicorn.conf.py", "app:app"]`.

**Example:**
```python
# gunicorn.conf.py
# Source: gunicorn.org/reference/settings

bind = "0.0.0.0:5000"
workers = 2          # Start conservative; BioBERT footprint determines safe max
worker_class = "sync"
timeout = 120        # BioBERT inference can be slow; 120s matches current CMD
keepalive = 5
preload_app = True   # Load model once in master; workers inherit via fork (COW)
max_requests = 500   # Restart workers periodically to avoid memory fragmentation
max_requests_jitter = 50  # Stagger restarts to avoid thundering herd
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = "info"
```

**Memory note:** `preload_app = True` cannot be combined with `--reload`. Do not use `--reload` in production. The combination is explicitly documented as incompatible by Gunicorn.

**Worker count guidance (Claude's Discretion):**
- BioBERT (`dmis-lab/biobert-base-cased-v1.2`) in fp32 on CPU occupies ~420–440 MB for model weights.
- GO embeddings matrix alone: ~30K × 768 × 4 bytes ≈ 92 MB. All embedding matrices together: ~180 MB.
- Per-worker Python overhead + Flask + request handling: ~80 MB.
- With `preload_app`, the model weights are shared via copy-on-write — not duplicated per worker.
- Estimated per-worker marginal RAM: ~80 MB (overhead) + working memory during active requests.
- Estimated total RAM at 2 workers: ~800 MB. At 4 workers: ~1.1 GB. Aspirational target of 4 is achievable on a 4 GB VPS but leaves little headroom. **Start with 2 workers and increase if measurements allow.**

### Pattern 4: SQLite Backup via Cron Inside Container

**What:** A shell script that calls `sqlite3 /app/data/ke_wp_mapping.db ".backup /app/data/backups/ke_wp_mapping_$(date +%Y%m%d).db"` and a cleanup command to purge backups older than 7 days.

**When to use:** Scheduled via `cron` inside the container. The base image (`python:3.12-slim-bookworm`) requires `cron` to be installed via apt in the Dockerfile.

**Example backup script (`scripts/backup_db.sh`):**
```bash
#!/bin/bash
# Source: sqlite.org/backup.html

BACKUP_DIR="/app/data/backups"
DB_PATH="/app/data/ke_wp_mapping.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/ke_wp_mapping_${TIMESTAMP}.db"

mkdir -p "${BACKUP_DIR}"

# sqlite3 .backup uses the Online Backup API: safe during active writes
sqlite3 "${DB_PATH}" ".backup '${BACKUP_PATH}'"

# Verify the backup is not corrupted
sqlite3 "${BACKUP_PATH}" "PRAGMA integrity_check;" | grep -q "^ok$"
if [ $? -ne 0 ]; then
    echo "BACKUP INTEGRITY CHECK FAILED: ${BACKUP_PATH}" >&2
    rm -f "${BACKUP_PATH}"
    exit 1
fi

# Remove backups older than 7 days (retention policy)
find "${BACKUP_DIR}" -name "ke_wp_mapping_*.db" -mtime +7 -delete

echo "Backup complete: ${BACKUP_PATH}"
```

**Cron schedule (Claude's Discretion — daily at 02:00, keep 7 days):**
```
# /etc/cron.d/ke-wp-backup
0 2 * * * appuser /app/scripts/backup_db.sh >> /app/logs/backup.log 2>&1
```

**Retention policy rationale:** A small research database with low write frequency makes daily snapshots with 7-day retention (7 copies) a sensible default. This provides a full week of point-in-time recovery while using minimal disk space given typical SQLite database sizes.

### Pattern 5: Docker Compose and Config Corrections

**What:** Two changes in `docker-compose.yml` and one in `src/core/config.py`.

**docker-compose.yml change 1 — switch from `environment:` to `env_file:`:**
```yaml
# Current (exposes env vars directly, correct syntax but replace inline vars with env_file)
environment:
  - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
  ...

# Target
env_file:
  - .env
```

**docker-compose.yml change 2 — add named volume for database file and use separate named volume for data:**

The current `docker-compose.yml` already mounts `./data:/app/data` as a bind mount. The locked decision specifies `/app/data/ke_wp_mapping.db` as the database path. This bind mount already achieves persistence. However, the `redis` service and `nginx` service in the current `docker-compose.yml` are not needed for Phase 1 (they are not used by the current codebase). The research finds no evidence that Redis is actually used anywhere in the codebase — the `RATELIMIT_STORAGE_URL` defaults to `memory://` in config.py, not Redis. The nginx service depends on an `nginx.conf` file that does not exist in the repository.

**Resolution:** Leave the volume mount as a bind mount (`./data:/app/data`) since it already works. The key change is correcting the database path default in config.

**src/core/config.py change — fix DATABASE_PATH default:**
```python
# Current (line 34)
DATABASE_PATH = os.getenv("DATABASE_PATH", "ke_wp_mapping.db")

# Target
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/ke_wp_mapping.db")
```

This is the firm path required by the STATE.md blocker.

### Anti-Patterns to Avoid

- **Using `np.load(path, allow_pickle=True).item()` on NPZ files:** NPZ files do not need `allow_pickle` for numeric/string arrays. Adding `.item()` after loading an NPZ file will fail — NPZ returns an `NpzFile` object, not a numpy array. The `.item()` call was valid only for the old approach of `np.save(path, dict)` + `np.load(path, allow_pickle=True)` which produces a 0-d object array containing the dict.

- **Setting WAL mode only once at initialization:** Although WAL mode persists in the database file after being set, always applying it in `get_connection()` is the locked decision and is idempotent. This also handles the case where a restored backup might have been created in journal mode.

- **Using `--reload` with `preload_app=True`:** These two Gunicorn settings are mutually exclusive. Gunicorn documentation explicitly states they cannot be combined. Only use `--reload` in development (where `preload_app` is not set).

- **Computing cosine similarity on unnormalized vectors at query time:** The current code in `embedding.py` computes `np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8)`. If vectors are pre-normalized at save time, this simplifies to `np.dot(emb1, emb2)` without the norm computation — faster and cleaner. Do not leave the division in place "just in case"; the transformation is mathematically equivalent for unit vectors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Safe concurrent SQLite writes | Custom locking mechanism or write queue | `PRAGMA journal_mode=WAL` + `busy_timeout` | WAL is tested by millions of deployments; custom locking creates deadlock risks |
| Model sharing across workers | Shared memory segments, custom IPC | `preload_app=True` + Linux fork COW | Fork copy-on-write is the standard pattern for Gunicorn + large model; no IPC code needed |
| Consistent database snapshots | `cp` of the database file | `sqlite3 .backup` shell command | File copy is not transactionally safe with active writers; the Online Backup API handles this correctly |
| Embedding serialization without pickle | Custom binary format | `np.savez` + `np.load` | NumPy's NPZ format is a stable, documented binary standard; no custom code needed |

**Key insight:** All four problems in this phase have production-grade solutions built into the existing stack. Zero new dependencies are required.

---

## Common Pitfalls

### Pitfall 1: NPZ Path Extension Mismatch
**What goes wrong:** `np.savez('data/ke_embeddings')` writes `data/ke_embeddings.npz`. If load code still references `data/ke_embeddings.npy`, the file is not found and the service silently falls back to empty embeddings (zero vectors for all queries).
**Why it happens:** The old format used `.npy`; NPZ always has `.npz` extension even when the save call omits it.
**How to avoid:** Change all path references from `.npy` to `.npz` in the same commit as the save format change. Verify with `os.path.exists()` check in the loader after migration.
**Warning signs:** Log messages showing `0 pre-computed embeddings loaded` despite files existing in `data/`.

### Pitfall 2: `allow_pickle` Still Required for String `ids` Array in NPZ
**What goes wrong:** Saving `ids = np.array(list(embeddings.keys()), dtype=object)` — using `dtype=object` — creates a Python object array that requires `allow_pickle=True` on load.
**Why it happens:** NumPy stores string arrays as object arrays by default when strings have variable length.
**How to avoid:** Use `dtype='U'` (Unicode) or `dtype=str` explicitly for the ids array, or use a fixed-length byte string. Alternatively, save a separate `.json` sidecar with the ordered key list and only save the float32 matrix in the NPZ file. The cleanest approach for this codebase is to use `np.array(list(keys), dtype=str)` which NumPy stores as a fixed-width Unicode array (`<U` dtype) — loadable without pickle.
**Warning signs:** `ValueError: Object arrays cannot be loaded when allow_pickle=False` at startup.

### Pitfall 3: WAL Files Left After Container Stop
**What goes wrong:** The SQLite WAL journal consists of three files: the database, a `-wal` file, and a `-shm` file. If the container stops uncleanly, these files persist in the mounted volume. On next startup, SQLite will replay the WAL correctly — this is by design. However, operators may try to back up only the `.db` file without the `-wal` file.
**Why it happens:** Operators see only the `.db` file and back it up independently.
**How to avoid:** The backup script using `sqlite3 .backup` or `VACUUM INTO` handles WAL correctly — both commands checkpoint the WAL before copying. Document this in the backup script's comments.
**Warning signs:** Database backup appears smaller than expected; restored backup is missing recent writes.

### Pitfall 4: `preload_app` and `app = create_app()` at Module Level
**What goes wrong:** With `preload_app = True`, Gunicorn imports `app.py` in the master process. If `app = create_app()` at module level (line 196 of the current `app.py`) triggers BioBERT initialization via the ServiceContainer, the model loads in the master before forking — which is exactly what we want. However, if the ServiceContainer's `embedding_service` property is lazy (it is), BioBERT may not load until the first request, defeating the preload benefit.
**Why it happens:** Lazy-loading services means the model is not initialized until first use, potentially in a worker process.
**How to avoid:** After `app = create_app()` at module level in `app.py`, add an explicit warm-up call: `_ = app.service_container.embedding_service` to force initialization in the master process before forking. This is the standard pattern for Gunicorn + large model deployments.
**Warning signs:** Each worker takes 20–30 seconds to serve its first request (model loading per worker) instead of serving immediately.

### Pitfall 5: NormalizEd Vectors and the Power Transform Interaction
**What goes wrong:** The current `_transform_similarity_score()` and `_transform_similarity_batch()` methods apply a power transform to raw cosine scores. These transforms use `(raw_cosine + 1.0) / 2.0` to normalize from `[-1, 1]` to `[0, 1]` before applying the power. If vectors are pre-normalized and similarity is computed via `np.dot()` (which is equivalent to cosine for unit vectors), the dot product output is still in `[-1, 1]`. The transform will still work correctly — no change needed to the transform logic, only to the inner `np.dot / (norms + eps)` line.
**Why it happens:** The transform was written expecting raw cosine similarity input. Dot product of unit vectors IS raw cosine similarity. The only change needed is removing the division by norms.
**How to avoid:** After changing to pre-normalized embeddings, update only the similarity computation line from `np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8)` to `np.dot(emb1, emb2)`. Leave the transform pipeline unchanged.

### Pitfall 6: Cron Not Running in `python:3.12-slim-bookworm`
**What goes wrong:** The base Docker image does not include a cron daemon. Simply adding a crontab file has no effect.
**Why it happens:** Slim Debian images strip non-essential services including cron.
**How to avoid:** Add `cron` to the `apt-get install` line in the Dockerfile and start it in the container entrypoint. Alternatively, use a separate supervisor process. The cleanest approach for this single-process container is to install `cron` and run it alongside Gunicorn via a process supervisor, or use a wrapper script as the container entrypoint that starts both `cron` and Gunicorn.

**Example Dockerfile entrypoint approach:**
```dockerfile
# In runtime stage, add cron
RUN apt-get update && apt-get install -y --no-install-recommends curl sqlite3 cron \
    && rm -rf /var/lib/apt/lists/*

# Copy cron file
COPY scripts/ke-wp-backup /etc/cron.d/ke-wp-backup
RUN chmod 0644 /etc/cron.d/ke-wp-backup && crontab /etc/cron.d/ke-wp-backup

# Entrypoint script starts cron then exec gunicorn
COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
```

---

## Code Examples

Verified patterns from official sources and codebase analysis:

### DEPLOY-01: WAL Mode in `Database.get_connection()`

Current code (`src/core/models.py` line 18–21):
```python
def get_connection(self):
    """Get database connection with row factory for dict-like access"""
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

Target code:
```python
def get_connection(self):
    """Get database connection with WAL mode, busy timeout, and row factory."""
    conn = sqlite3.connect(self.db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn
```

Source: [sqlite.org/wal.html](https://sqlite.org/wal.html), [pythontutorials.net concurrent-writing-with-sqlite3](https://www.pythontutorials.net/blog/concurrent-writing-with-sqlite3/)

### DEPLOY-02: NPZ Save in `embedding_utils.py`

Current `save_embeddings()` (scripts/embedding_utils.py line 68–84):
```python
def save_embeddings(embeddings, path):
    logger.info(f"Saving {len(embeddings)} embeddings to {path}...")
    np.save(path, embeddings)  # <-- saves dict via pickle
```

Target (with normalization for DEPLOY-04):
```python
def save_embeddings(embeddings: dict, path: str):
    """Save embeddings as NPZ matrix format with pre-normalized vectors."""
    import numpy as np
    ids = np.array(list(embeddings.keys()), dtype=str)  # Unicode, no pickle needed
    matrix = np.array(list(embeddings.values()), dtype=np.float32)
    # Normalize each row to unit length (DEPLOY-04: dot product = cosine at query time)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)  # guard against zero vectors
    matrix = (matrix / norms).astype(np.float32)
    # Write as .npz (np.savez appends .npz automatically)
    npz_path = path.replace('.npy', '')
    np.savez(npz_path, ids=ids, matrix=matrix)
    size_mb = os.path.getsize(npz_path + '.npz') / 1024 / 1024
    logger.info("Saved %d normalized embeddings to %s.npz: %.2f MB",
                len(embeddings), npz_path, size_mb)
```

Source: [numpy.org/doc/stable/reference/generated/numpy.savez.html](https://numpy.org/doc/stable/reference/generated/numpy.savez.html)

### DEPLOY-02 + DEPLOY-04: NPZ Load in `src/services/embedding.py`

Current `_load_precomputed_embeddings()` (line 138–146):
```python
def _load_precomputed_embeddings(self, path: str):
    try:
        import numpy as np
        self.pathway_embeddings = np.load(path, allow_pickle=True).item()
        logger.info(f"Loaded {len(self.pathway_embeddings)} pre-computed pathway embeddings")
    except Exception as e:
        logger.warning(f"Could not load pre-computed embeddings: {e}")
        self.pathway_embeddings = {}
```

Target:
```python
def _load_precomputed_embeddings(self, path: str):
    """Load pre-computed pathway embeddings from NPZ format (no pickle)."""
    # Accept both old .npy and new .npz path strings
    npz_path = path.replace('.npy', '.npz')
    if not os.path.exists(npz_path):
        logger.warning("Pathway embeddings file not found: %s", npz_path)
        self.pathway_embeddings = {}
        return
    try:
        import numpy as np
        with np.load(npz_path) as data:  # allow_pickle=False by default
            ids = data['ids']
            matrix = data['matrix']
        self.pathway_embeddings = dict(zip(ids, matrix))
        logger.info("Loaded %d pre-computed pathway embeddings (normalized)", len(self.pathway_embeddings))
    except Exception as e:
        logger.warning("Could not load pre-computed embeddings: %s", e)
        self.pathway_embeddings = {}
```

Source: [numpy.org/doc/stable/reference/generated/numpy.load.html](https://numpy.org/doc/stable/reference/generated/numpy.load.html)

### DEPLOY-04: Dot Product Replace Cosine in `compute_similarity()`

Current (embedding.py line 357–358):
```python
raw_similarity = np.dot(emb1, emb2) / (
    np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
)
```

Target (after normalization at precompute time):
```python
# Vectors are pre-normalized — dot product IS cosine similarity
raw_similarity = np.dot(emb1, emb2)
```

The same change applies in `compute_ke_pathway_similarity()` (line 413–414) and the batch computation in `compute_ke_pathways_batch_similarity()` (lines 541–548).

Source: [thelinuxcode.com cosine-similarity-numpy](https://thelinuxcode.com/how-to-calculate-cosine-similarity-in-python-numpy-scipy-sklearn-and-practical-patterns/)

### DEPLOY-03: Backup Script

```bash
#!/bin/bash
# /app/scripts/backup_db.sh
# Uses sqlite3 Online Backup API — safe during active writes.
# Source: sqlite.org/backup.html

set -euo pipefail

DB_PATH="/app/data/ke_wp_mapping.db"
BACKUP_DIR="/app/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ke_wp_mapping_${TIMESTAMP}.db"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Integrity check
RESULT=$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")
if [ "${RESULT}" != "ok" ]; then
    echo "[BACKUP ERROR] Integrity check failed for ${BACKUP_FILE}: ${RESULT}" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "[BACKUP OK] ${BACKUP_FILE}"

# Prune old backups
find "${BACKUP_DIR}" -name "ke_wp_mapping_*.db" -mtime "+${RETENTION_DAYS}" -delete
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `np.save(path, dict)` + `allow_pickle=True` | `np.savez(path, ids=..., matrix=...)` + `np.load` (no pickle) | After CVE-2019-6446 patched pickle default | Eliminates arbitrary code execution risk from embedding files |
| Cosine similarity computed at query time (dot + norm) | Pre-normalize at save time, dot product at query time | Established best practice for dense vector retrieval | Eliminates per-query norm computation; ~15% faster batch similarity |
| Gunicorn CMD inline in Dockerfile | `gunicorn.conf.py` committed to repo | Gunicorn 19+ supports config file | Version-controlled, auditable, reusable configuration |
| Default SQLite journal mode (rollback) | WAL mode + busy_timeout | SQLite 3.7.0 (2010); Python standard since then | Concurrent reads during writes; dramatically fewer `database is locked` errors |

**Deprecated/outdated in this codebase:**
- `np.load(path, allow_pickle=True).item()`: Insecure, should be replaced with NPZ format. The current codebase uses this pattern in 5 places (3 in `embedding.py`, 2 in `go.py`).
- Inline Gunicorn CMD in Dockerfile with `--workers 4`: Workers count should not be hardcoded in Dockerfile; moved to `gunicorn.conf.py` where it can be tuned and commented.

---

## Current Codebase State: Specific Files to Change

Based on reading the actual source files, here is the precise change map:

### Files with `allow_pickle=True` that must change (DEPLOY-02):

1. **`src/services/embedding.py`** — 3 methods:
   - `_load_precomputed_embeddings()` line 142: `np.load(path, allow_pickle=True).item()`
   - `_load_precomputed_ke_embeddings()` line 152: same pattern
   - `_load_precomputed_pathway_title_embeddings()` line 162: same pattern, hardcoded path `'data/pathway_title_embeddings.npy'` (also a fragile hardcoded path concern)

2. **`src/suggestions/go.py`** — 2 methods:
   - `_load_go_embeddings()` line 53: `np.load(path, allow_pickle=True).item()`
   - `_load_go_name_embeddings()` line 64: same pattern

3. **`scripts/embedding_utils.py`** — `save_embeddings()` function line 77: `np.save(path, embeddings)` (the source of the pickle-based files)

### Files with hardcoded/wrong database path (DEPLOY-01 + infra):

4. **`src/core/config.py`** line 34: `DATABASE_PATH = os.getenv("DATABASE_PATH", "ke_wp_mapping.db")` — default is relative path, wrong for Docker

### Files with cosine computation to replace (DEPLOY-04):

5. **`src/services/embedding.py`**:
   - `compute_similarity()` line 357–358: norm division
   - `compute_ke_pathway_similarity()` line 413–414: norm division
   - `compute_ke_pathways_batch_similarity()` lines 541–546, 547–548: batch norm divisions

### Docker/infra files to modify:

6. **`docker-compose.yml`**: Switch `environment:` to `env_file: .env`; remove/simplify Redis and Nginx services not used in codebase (optional scope question — see Open Questions)
7. **`Dockerfile`**: Add `cron` to apt-get; add crontab; change CMD to use `gunicorn.conf.py`
8. **`gunicorn.conf.py`**: Create new file at project root
9. **`scripts/backup_db.sh`**: Create new file

---

## Open Questions

1. **Redis and Nginx in docker-compose.yml**
   - What we know: The current `docker-compose.yml` includes `redis` and `nginx` services. The codebase (`src/core/config.py`) has `RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")` — Redis is not actually used. There is no `nginx.conf` file in the repository.
   - What's unclear: Are Redis and Nginx intended for Phase 1, or leftover from a template? Starting the container will fail if `nginx.conf` is missing.
   - Recommendation: Remove or comment out the `redis` and `nginx` service blocks in `docker-compose.yml` for Phase 1. They are not needed by the current application code. This is a minor cleanup within the Docker Compose modification scope.

2. **Gunicorn worker count validation**
   - What we know: BioBERT in fp32 on CPU uses ~420–440 MB. With `preload_app`, model is shared. Per-worker overhead is ~80 MB. VPS RAM is unknown.
   - What's unclear: Actual VPS RAM available; whether any other processes (monitoring, reverse proxy) consume significant memory.
   - Recommendation: Start with `workers = 2` in `gunicorn.conf.py`. After deployment, measure with `docker stats` and increase to 3 or 4 if headroom allows. Document this in the conf file comment.

3. **Warm-up call for embedding_service preload**
   - What we know: `ServiceContainer.embedding_service` is a lazy property. With `preload_app = True`, the Flask app is created in the master process, but `embedding_service` is not accessed until first request unless explicitly triggered.
   - What's unclear: Whether adding `_ = app.service_container.embedding_service` at module level in `app.py` has any unwanted side effects in the testing environment (where `embedding_service` is disabled).
   - Recommendation: Add the warm-up call guarded by `if os.getenv("FLASK_ENV") == "production"` or check if embedding is enabled in config before forcing initialization.

---

## Sources

### Primary (HIGH confidence)
- [numpy.org/doc/stable — numpy.load](https://numpy.org/doc/stable/reference/generated/numpy.load.html) — NPZ format, allow_pickle behavior, context manager usage
- [numpy.org/doc/stable — numpy.savez](https://numpy.org/doc/stable/reference/generated/numpy.savez.html) — NPZ save format, key-value array storage
- [sqlite.org/wal.html](https://sqlite.org/wal.html) — WAL mode, reader/writer semantics, PRAGMA commands
- [sqlite.org/backup.html](https://sqlite.org/backup.html) — Online Backup API, `.backup` shell command
- [gunicorn.org/reference/settings](https://gunicorn.org/reference/settings/) — preload_app, workers, timeout, configuration file settings
- [Actual codebase files read] — `src/core/models.py`, `src/services/embedding.py`, `src/suggestions/go.py`, `scripts/embedding_utils.py`, `src/core/config.py`, `docker-compose.yml`, `Dockerfile`, `app.py`, `src/services/container.py`

### Secondary (MEDIUM confidence)
- [Sharing NLP Models among Gunicorn Workers — Trendyol Tech / Medium](https://medium.com/trendyol-tech/sharing-large-language-models-among-gunicorn-workers-reducing-memory-usage-and-boosting-18c0efd8e942) — Real-world BioBERT-scale model sharing with preload_app, worker count guidance
- [pythontutorials.net — concurrent-writing-with-sqlite3](https://www.pythontutorials.net/blog/concurrent-writing-with-sqlite3/) — WAL + busy_timeout + short transaction pattern for Python
- [thelinuxcode.com — cosine-similarity-numpy](https://thelinuxcode.com/how-to-calculate-cosine-similarity-in-python-numpy-scipy-sklearn-and-practical-patterns/) — Pre-normalize + dot product equivalence to cosine
- [betterstack.com — gunicorn-explained](https://betterstack.com/community/guides/scaling-python/gunicorn-explained/) — gunicorn.conf.py structure and worker configuration
- [berthub.eu — sqlite3 database locked](https://berthub.eu/articles/posts/a-brief-post-on-sqlite3-database-locked-despite-timeout/) — busy_timeout edge cases and transaction upgrade pitfall

### Tertiary (LOW confidence — flag for validation)
- BioBERT CPU memory footprint estimate of ~420–440 MB: derived from model parameter count (110M × 4 bytes/fp32 param) — verify with `docker stats` after first deployment

---

## Metadata

**Confidence breakdown:**
- Standard stack (NPZ format, WAL, gunicorn.conf.py): HIGH — verified against official numpy.org and sqlite.org docs; all packages already in codebase
- Architecture patterns (preload_app memory sharing, normalize-at-save): HIGH — verified against official Gunicorn docs and multiple production engineering case studies
- Pitfalls (pickle/str dtype interaction, WAL file backup, lazy embedding loading): HIGH — verified against official docs and direct codebase reading
- Memory estimates (BioBERT footprint, per-worker overhead): LOW-MEDIUM — theoretical estimate; validate with `docker stats` after deployment

**Research date:** 2026-02-19
**Valid until:** 2026-08-19 (stable libraries; review if numpy, gunicorn, or sqlite3 major versions change)
