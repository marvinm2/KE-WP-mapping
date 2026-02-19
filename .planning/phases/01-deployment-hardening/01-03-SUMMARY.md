---
phase: 01-deployment-hardening
plan: 03
subsystem: infra
tags: [numpy, embeddings, npz, biobert, cosine-similarity, security]

# Dependency graph
requires: []
provides:
  - "NPZ embedding file format with pre-normalized vectors (no pickle deserialization)"
  - "save_embeddings() utility writing typed-array NPZ files"
  - "All five embedding loaders migrated to np.load NPZ without allow_pickle"
  - "Five cosine similarity computations replaced by equivalent dot product"
affects:
  - "01-04-PLAN and beyond: embedding files on disk must be regenerated as .npz before deployment"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NPZ matrix format: save as {ids: Unicode array, matrix: float32 normalized} — no pickle required on load"
    - "Pre-normalization at save time: dot product of loaded vectors is mathematically equivalent to cosine similarity"
    - "save_embeddings() is the single shared utility for all precompute scripts — never call np.save() directly"

key-files:
  created: []
  modified:
    - scripts/embedding_utils.py
    - src/services/embedding.py
    - src/suggestions/go.py
    - scoring_config.yaml
    - scripts/precompute_ke_embeddings.py
    - scripts/precompute_pathway_title_embeddings.py
    - scripts/precompute_go_embeddings.py
    - scripts/precompute_pathway_embeddings.py

key-decisions:
  - "Use dtype=str (Unicode) for ids array in NPZ — dtype=object would require pickle on load, defeating the purpose"
  - "Pre-normalize vectors at save time so np.dot() at query time equals cosine similarity — no per-query norm computation"
  - "Guard zero vectors in normalization with np.where(norms == 0.0, 1.0, norms) to avoid NaN"
  - "precompute_pathway_embeddings.py rewired to use save_embeddings() — was the only script calling np.save() directly"

patterns-established:
  - "NPZ loader pattern: `with np.load(npz_path) as data: ids = data['ids']; matrix = data['matrix']` — no allow_pickle"
  - "Path normalization: loaders call path.replace('.npy', '.npz') to handle old-style path strings"

requirements-completed:
  - DEPLOY-02
  - DEPLOY-04

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 01 Plan 03: Embedding NPZ Migration Summary

**Pickle-free NPZ embedding format with pre-normalized vectors eliminates arbitrary deserialization risk and removes per-query norm computation from all five similarity paths**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T21:37:08Z
- **Completed:** 2026-02-19T21:41:33Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Replaced `np.save` (pickle-based dict) with `np.savez` (typed arrays: Unicode ids + float32 matrix) in the shared `save_embeddings()` utility
- Eliminated all five `allow_pickle=True` calls across `embedding.py` (3) and `go.py` (2)
- Replaced five cosine norm divisions in `embedding.py` with direct `np.dot()` calls — valid because vectors are unit-normalized at save time
- Updated `scoring_config.yaml` and all four precompute script default paths from `.npy` to `.npz`
- Fixed `precompute_pathway_embeddings.py` which was calling `np.save()` directly instead of `save_embeddings()`

## Task Commits

Each task was committed atomically:

1. **Task 1: Update save_embeddings() to NPZ with pre-normalized matrix and update scoring_config.yaml paths** - `4d6dfd0` (feat)
2. **Task 2: Update all embedding loaders to NPZ format and replace cosine with dot product** - `ae2c96a` (feat)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `scripts/embedding_utils.py` — `save_embeddings()` now writes NPZ with Unicode ids and unit-normalized float32 matrix
- `src/services/embedding.py` — Three loaders migrated to NPZ; five cosine norm divisions replaced by `np.dot()`; hardcoded pathway_title path updated to `.npz`
- `src/suggestions/go.py` — Two GO loaders migrated to NPZ; default paths updated to `.npz`
- `scoring_config.yaml` — `precomputed_embeddings` and `precomputed_ke_embeddings` paths updated from `.npy` to `.npz`
- `scripts/precompute_ke_embeddings.py` — Default output path and docstring updated to `.npz`
- `scripts/precompute_pathway_title_embeddings.py` — Default output path and docstring updated to `.npz`
- `scripts/precompute_go_embeddings.py` — Default output paths and docstring updated to `.npz`
- `scripts/precompute_pathway_embeddings.py` — Rewired from `np.save()` to `save_embeddings()`; default path and docstring updated to `.npz`

## Decisions Made

- **Unicode dtype for ids:** Using `dtype=str` (which maps to NumPy `<Uxxx`) for the ids array. `dtype=object` would require `allow_pickle=True` on load, defeating the purpose of the migration.
- **Pre-normalization:** Normalizing vectors at save time inside `save_embeddings()` means the loaders receive pre-normalized vectors, and `np.dot()` is mathematically equal to cosine similarity without any per-query computation.
- **Zero-vector guard:** `np.where(norms == 0.0, 1.0, norms)` prevents division-by-zero on degenerate vectors.
- **Path transparency:** Loaders call `path.replace('.npy', '.npz')` so old-style path strings in config/args work without forcing callers to change immediately.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] precompute_pathway_embeddings.py called np.save() directly**
- **Found during:** Task 2 (precompute script audit)
- **Issue:** This script bypassed `save_embeddings()` and called `np.save(output_path, embeddings)` directly, writing the old pickle-based dict format. It would have produced a `.npy` file incompatible with the new NPZ loaders.
- **Fix:** Rewired to `from scripts.embedding_utils import save_embeddings` and replaced the `np.save()` call and surrounding logging with `save_embeddings(embeddings, output_path)`. Also removed the now-unused `import numpy as np` (it was only used for `np.save`).
- **Files modified:** `scripts/precompute_pathway_embeddings.py`
- **Verification:** Script imports cleanly; round-trip test using `save_embeddings` passes.
- **Committed in:** `ae2c96a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary for consistency — the script would have silently written the old format and caused a load failure at runtime.

## Issues Encountered

None — the migration was straightforward. The verification tests (NPZ dtype check, normalization check, round-trip test) all passed on the first attempt. All 45 existing tests continue to pass.

## User Setup Required

**Embedding files must be regenerated.** The existing `.npy` files in `data/` are in the old pickle-based dict format and will not load with the new NPZ loaders. Before deploying, run:

```bash
python scripts/precompute_ke_embeddings.py
python scripts/precompute_pathway_title_embeddings.py
python scripts/precompute_go_embeddings.py
python scripts/precompute_pathway_embeddings.py
```

This produces the new `.npz` files. The old `.npy` files can be deleted after regeneration.

## Next Phase Readiness

- Embedding security hardening complete — no arbitrary pickle deserialization in the embedding pipeline
- Dot product optimization ready — performance gain realized after embedding files are regenerated
- Precompute scripts are consistent: all four now use `save_embeddings()` and produce `.npz` output
- Embedding files on disk must be regenerated before the application can load embeddings in production

---
*Phase: 01-deployment-hardening*
*Completed: 2026-02-19*
