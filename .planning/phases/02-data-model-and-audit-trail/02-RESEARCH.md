# Phase 2: Data Model and Audit Trail - Research

**Researched:** 2026-02-20
**Domain:** SQLite schema migration, UUID assignment, duplicate detection, provenance display
**Confidence:** HIGH — all findings are grounded in the live codebase; no speculative external libraries required

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Confidence level capture
- Set by the curator at proposal submit time (not by admin at approval)
- Three options: High / Medium / Low
- Required field — proposal cannot be submitted without selecting a confidence level
- Presented as select buttons, added to the existing 4-question form interface alongside the current proposal questions

#### Duplicate detection UX
- Both approved mappings AND pending proposals block re-submission — strictest policy
- Applies to both KE-WP and KE-GO mapping types equally
- Live check — triggered as soon as the KE and pathway/GO term are selected (before curator completes the form)
- When blocked, show an inline preview of the existing mapping/proposal (not just a text error)
- If a pending proposal is blocking, the curator can flag it as stale for admin review directly from the inline preview
- If an approved mapping exists, the curator can submit a revision proposal (flags the existing mapping for update, goes back to admin review)

#### UUID assignment and lifecycle
- UUID assigned at proposal time — every proposal gets a stable UUID immediately on creation
- UUIDs are visible in the admin UI and in all API output; not shown to regular curators in the standard browse/proposal views
- UUIDs are always reserved — never reused even if a proposal is rejected or deleted (old UUIDs return 404/410)

#### Provenance display
- Curator GitHub username and approval timestamp shown in both the browse table and the detail view
- Browse table display style: Claude's discretion (inline columns vs tooltip — pick what fits the existing layout)
- BioBERT suggestion score stored with each proposal but only visible in the admin view and API output (not in the curator browse table)
- GitHub username auto-captured from the GitHub OAuth session at proposal submission time — curator does not enter it manually

### Claude's Discretion
- URL routing strategy for individual mapping records (UUID-based `/mappings/{uuid}` vs integer IDs in URLs)
- Browse table column layout for provenance (inline Curator/Date columns vs hover tooltip)
- Exact inline preview component design for duplicate detection warning

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CURAT-01 | Each approved mapping records the approving curator and timestamp (provenance/audit trail) | `approved_by` + `approved_at` already exist on `ke_go_proposals`; need to add to `proposals` table via migration, then copy to `mappings` tables at approval time |
| CURAT-02 | Duplicate mapping detection prevents submitting the same KE→pathway or KE→GO pair twice | `/check` and `/check_go_entry` already exist but only check approved mappings; need to also query pending proposals and return structured payload for inline preview |
| CURAT-03 | Confidence level (High/Medium/Low) stored with each approved mapping and visible in browse table | `confidence_level` column already exists on `mappings` and `ke_go_mappings`; what is missing is (a) capturing curator-set confidence on NEW proposals and (b) the "required field" enforcement in the submission flow — the schema and DB already support this |
| EXPLO-04 | All API and explore-page responses include stable, permanent mapping IDs | Need to add `uuid` TEXT UNIQUE NOT NULL column to `mappings` and `ke_go_mappings`, generated at insert time using Python stdlib `uuid.uuid4()` |
</phase_requirements>

---

## Summary

Phase 2 adds four orthogonal capabilities to a mature, working codebase. The database schema and Python model layer (`src/core/models.py`) are the central concern: three new columns on existing tables (`uuid`, `approved_by_curator`, `approved_at_curator` on mappings; `suggestion_score` and `confidence_level` on proposals), all added via the existing auto-migration pattern already established in `Database._migrate_*` helpers. No new tables are needed.

The proposal workflow today collects `connection_type` and `confidence_level` at assessment time and passes them to `/submit` (for new mappings) or `/submit_proposal` (for change proposals). The new confidence-at-proposal-time requirement means curators must explicitly pick High / Medium / Low on the **new mapping submission form** (index.html, Step 3/4), and that choice is stored directly on the proposal record. The 4-question assessment already computes a recommended confidence level — the new select-button group will be a required confirmation of that recommendation, not a replacement for it. The existing `.btn-option` / `.btn-group` CSS classes in `main.css` are exactly the right pattern to reuse.

Duplicate detection for new mappings currently runs after the curator finishes the 4-step assessment (via `/check` on form submit). The decision requires it to fire **live**, as soon as both KE and pathway/GO term are selected (before Step 3). The `/check` and `/check_go_entry` endpoints need to be enriched to also query pending proposals, and the frontend needs a new inline warning component that can host two CTAs (flag stale / submit revision).

UUID generation uses Python's standard-library `uuid.uuid4()` — no additional dependencies. The UUID is stored in the mapping record at creation time, and proposals reference the mapping's UUID for API/admin use.

**Primary recommendation:** Work in this order — (1) schema migrations, (2) server-side enforcement, (3) frontend duplicate-check enrichment, (4) provenance display. Each step is independently testable.

---

## Standard Stack

### Core
| Component | Version/Source | Purpose | Why Standard |
|-----------|---------------|---------|--------------|
| Python `uuid` stdlib | Python 3.x builtin | UUID4 generation | No dependency, cryptographically random, universally accepted |
| SQLite `ALTER TABLE ... ADD COLUMN` | SQLite 3.x | Adding columns to live DB | Already used in `_migrate_proposals_admin_fields` and `_migrate_mappings_updated_by_field` |
| Marshmallow `Schema` | Already installed (`src/core/schemas.py`) | Input validation for new fields | All existing schemas use this; just extend existing schema classes |
| Flask session | Already in use | GitHub username capture | `session.get('user', {}).get('username')` pattern is established throughout codebase |
| `.btn-option` / `.btn-group` CSS | `static/css/main.css` | Confidence select-button UI | Already used for all 4 assessment steps — identical visual language |

### Supporting
| Component | Source | Purpose | When to Use |
|-----------|--------|---------|-------------|
| DataTables (existing CDN) | `explore.html` | Browse table with new columns | Already loaded; adding columns is pure HTML/Jinja change |
| jQuery AJAX | Already loaded | Live duplicate check triggering | `$.post('/check', ...)` pattern is already used at line 456 of `main.js` |
| Jinja2 `tojson` filter | Flask builtin | Passing mapping data to inline preview | Already used in `explore.html` for `data-entry` attribute pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uuid.uuid4()` (random) | `uuid.uuid5()` (name-based) | uuid5 would allow regenerating UUIDs deterministically from ke_id+wp_id, but random uuid4 is simpler and avoids collisions if data is ever corrected |
| Inline tooltip for provenance in browse table | Extra full columns | Extra columns are always visible and accessible; tooltips require hover interaction and fail on mobile/keyboard nav — inline columns recommended |
| JS live check on selection change | Debounced `oninput` | Selection change on a `<select>` or suggestion click is already a discrete event; no debounce needed |

---

## Architecture Patterns

### Recommended Project Structure Changes

No new files required except possibly a new endpoint in `api_bp`. Changes are confined to:

```
src/core/models.py             # New migration methods, new columns, enriched check_* methods
src/core/schemas.py            # Extend MappingSchema, GoMappingSchema, ProposalSchema
src/blueprints/api.py          # Enrich /check and /check_go_entry; add /flag_proposal_stale
src/blueprints/admin.py        # Show UUID + suggestion_score in proposal detail view
templates/index.html           # Add confidence select-button group to Step 3
templates/explore.html         # Add Curator + Approved At columns; provenance inline
static/js/main.js              # Wire live duplicate check; add inline preview component
```

### Pattern 1: Auto-Migration (existing pattern — extend it)

**What:** `Database.init_db()` calls private `_migrate_*` methods that run `PRAGMA table_info(table)` to check existing columns and `ALTER TABLE ... ADD COLUMN` for any missing ones. This runs on every startup — idempotent.

**When to use:** Every new column this phase requires must go through a migration method, not into `CREATE TABLE IF NOT EXISTS` (which only runs once).

**Example (from existing code in `src/core/models.py`):**
```python
def _migrate_mappings_updated_by_field(self, conn):
    cursor = conn.execute("PRAGMA table_info(mappings)")
    columns = [row[1] for row in cursor.fetchall()]
    if "updated_by" not in columns:
        conn.execute("ALTER TABLE mappings ADD COLUMN updated_by TEXT")
```

**New migration method to add (pattern to follow):**
```python
def _migrate_mappings_uuid_and_provenance(self, conn):
    cursor = conn.execute("PRAGMA table_info(mappings)")
    columns = [row[1] for row in cursor.fetchall()]
    new_fields = {
        "uuid": "TEXT",
        "approved_by_curator": "TEXT",
        "approved_at_curator": "TIMESTAMP",
    }
    for field, col_type in new_fields.items():
        if field not in columns:
            conn.execute(f"ALTER TABLE mappings ADD COLUMN {field} {col_type}")
    # Backfill uuid for existing rows
    conn.execute("""
        UPDATE mappings SET uuid = lower(hex(randomblob(4))) || '-' ||
        lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) ||
        '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
        substr(lower(hex(randomblob(2))),2) || '-' ||
        lower(hex(randomblob(6)))
        WHERE uuid IS NULL
    """)
    # Add unique index after backfill
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mappings_uuid ON mappings(uuid)")
```

Note: New inserts should use Python `uuid.uuid4()` in `create_mapping()`, not SQL. The SQL backfill above is only for existing rows.

**Critical:** Call the new migration methods from `init_db()` before `conn.commit()`.

### Pattern 2: UUID Assignment at Proposal Time

**What:** When `ProposalModel.create_proposal()` creates a record, also generate and store a UUID for the *mapping that will result if approved*. The proposal carries the UUID that will be assigned to the mapping upon approval.

**Why this approach:** The decisions say "UUID assigned at proposal time — every proposal gets a stable UUID immediately on creation." This means:
1. `proposals.uuid` column stores the UUID reserved for this proposal's outcome
2. When admin approves, the mapping's UUID is set from the proposal's reserved UUID
3. For new-mapping proposals (no existing `mapping_id`), a new UUID is generated at proposal creation
4. For revision proposals on existing mappings, the mapping already has a UUID — the proposal stores the existing mapping's UUID (no change)

**Example:**
```python
import uuid as uuid_lib

def create_proposal(self, ...):
    reserved_uuid = str(uuid_lib.uuid4())
    cursor = conn.execute("""
        INSERT INTO proposals (..., uuid) VALUES (?, ..., ?)
    """, (..., reserved_uuid))
```

### Pattern 3: Enriched Duplicate Check Response

**What:** `/check` currently returns `{"pair_exists": True, "message": "..."}`. Enrich it to also check `proposals` table for pending proposals on the same pair, and return the full preview payload.

**New response shape:**
```json
{
  "pair_exists": true,
  "blocking_type": "approved_mapping",  // or "pending_proposal"
  "existing": {
    "ke_id": "KE 55",
    "wp_id": "WP123",
    "confidence_level": "high",
    "approved_by": "marvinlabs",
    "approved_at": "2025-01-15",
    "uuid": "abc123-..."
  },
  "actions": ["submit_revision"]  // or ["flag_stale"] for pending proposals
}
```

**Frontend side:** In `main.js`, the live check fires when KE + pathway are both selected (not on form submit). The response drives inline rendering of a warning card with action buttons below the pathway selection area, before Steps 3-4 are shown.

### Pattern 4: Confidence Select-Button as Required Form Field

**What:** Add a "Confidence Level" step to the assessment form (Step 3 / between assessment and submit). Use `.btn-group` + `.btn-option` CSS classes, matching the exact pattern of the 4 existing assessment step buttons.

**Why a dedicated step, not hidden field:** The 4-question assessment already auto-populates `#confidence_level` as a hidden field. The new requirement is that the curator must **explicitly confirm** a confidence level (it's a required field, proposal cannot submit without it). The select-button group replaces the hidden field with a visible required interaction, and the auto-computed recommendation is pre-selected as a default.

**HTML pattern (from existing assessment steps):**
```html
<div class="assessment-step" data-step="confidence">
    <h4>Confidence Level <span class="required">*</span></h4>
    <p>Select the confidence level for this mapping:</p>
    <div class="btn-group" data-step="confidence">
        <button type="button" class="btn-option" data-value="high">High</button>
        <button type="button" class="btn-option" data-value="medium">Medium</button>
        <button type="button" class="btn-option" data-value="low">Low</button>
    </div>
</div>
```

The auto-assessment result pre-selects the recommended option (JS: add `selected` class to the matching button after evaluation).

### Pattern 5: Provenance Display in Browse Table

**Recommendation: Inline columns** (not tooltip).

**Rationale:** The explore table already has 7 columns (KE ID, KE Title, WP ID, WP Title, Connection Type, Confidence Level, Timestamp, Actions). The Timestamp column currently shows `created_at`. Replacing "Timestamp" with two columns "Curator" and "Approved" fits without breaking layout — DataTables handles overflow via horizontal scroll already. Tooltips are inaccessible on mobile and keyboard-only navigation and would hide data by default.

**Implementation:** In `explore()` route, `get_all_mappings()` already returns `created_by` and `created_at`. To return `approved_by_curator` and `approved_at_curator` from the new columns, no JOIN is needed — they live on the `mappings` row directly.

```html
<!-- In explore.html thead -->
<th>Curator</th>
<th>Approved</th>

<!-- In explore.html tbody -->
<td>{{ row['approved_by_curator'] or row['created_by'] or '—' }}</td>
<td>{{ (row['approved_at_curator'] or row['created_at'] or '').split('.')[0] }}</td>
```

### Pattern 6: Stale Flagging Endpoint

**What:** A new `/api/flag_proposal_stale` endpoint (POST) that sets a `is_stale` boolean column on a `proposals` or `ke_go_proposals` record. Authenticated curator can mark a blocking pending proposal as stale; this queues it for admin review.

**Why a new endpoint rather than repurposing existing:** The existing `/admin/proposals/<id>/reject` is admin-only. Stale flagging is a curator action.

**Access control:** Any authenticated, logged-in user (not just admin) can flag a proposal as stale. Rate-limited via `submission_rate_limit`.

### Anti-Patterns to Avoid
- **Don't add UUID to `CREATE TABLE IF NOT EXISTS` without a migration:** The tables already exist in production. The `IF NOT EXISTS` clause only creates the table if it doesn't exist — it does not add new columns to an existing table. Always use `ALTER TABLE` via `_migrate_*` methods.
- **Don't generate UUID in SQL triggers:** The codebase uses plain Python model methods, not triggers. Keep UUID generation in `create_mapping()` and `create_proposal()` Python methods.
- **Don't add `NOT NULL` constraint to new UUID column without backfill:** SQLite requires a DEFAULT or existing data for `NOT NULL` on `ALTER TABLE ADD COLUMN`. Either use `NOT NULL DEFAULT ''` temporarily (then backfill) or omit `NOT NULL` and enforce in Python code only.
- **Don't query proposals for duplicate check in a separate client request:** The enriched `/check` endpoint should do the proposal lookup server-side in a single response. Do not chain two client AJAX calls.
- **Don't display UUID in the curator-facing browse table:** The decision is explicit that UUIDs are admin/API-only. Keep the explore table free of UUIDs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom random string | `import uuid; str(uuid.uuid4())` | Stdlib, no install, RFC 4122 compliant, already available everywhere in the app |
| Column existence check before ALTER | Parsing CREATE TABLE SQL | `PRAGMA table_info(table_name)` | Already the established pattern in `_migrate_proposals_admin_fields` — returns `[row[1] for row in cursor]` as column names |
| Duplicate detection query | Separate client-side check via JS | Server-side enrichment of `/check` endpoint | Single round-trip, atomic read, no race condition between check and submit |
| Confidence level validation | Custom JS validation | Marshmallow `validate.OneOf(["high", "medium", "low"])` | Already used in `MappingSchema.confidence_level` — just ensure the field is `required=True` |

**Key insight:** The existing migration infrastructure, schema validation, and endpoint patterns already do 80% of the work. This phase is primarily about adding the right columns, wiring existing patterns to new fields, and enriching two existing endpoints.

---

## Common Pitfalls

### Pitfall 1: SQLite ALTER TABLE Limitations
**What goes wrong:** SQLite's `ALTER TABLE` only supports `ADD COLUMN` (no rename, no drop, no change type). Attempting `ALTER TABLE mappings ADD COLUMN uuid TEXT NOT NULL` on a table with existing rows fails because existing rows would have NULL in a NOT NULL column.
**Why it happens:** SQLite is stricter than PostgreSQL/MySQL on `NOT NULL` without a DEFAULT.
**How to avoid:** Add the column as nullable (`TEXT`), backfill existing rows with generated UUIDs, then enforce NOT NULL at the Python layer only (raise if None). Do not attempt to add NOT NULL constraint retroactively.
**Warning signs:** `OperationalError: Cannot add a NOT NULL column with default value NULL`

### Pitfall 2: New Mapping vs. Proposal Flow Confusion
**What goes wrong:** There are two submission paths: (a) `/submit` creates a new `mappings` row directly (for new KE-WP pairs), and (b) `/submit_proposal` creates a `proposals` row referencing an existing `mappings.id` (for change proposals). UUID assignment and confidence capture must be implemented in both paths.
**Why it happens:** The current `submit_proposal` endpoint is for change proposals only, not for new mapping creation. The new-mapping path goes directly through `/submit`, which creates the `mappings` row — that's where UUID must be generated.
**How to avoid:** Trace both code paths clearly in the plan. For `/submit` → `MappingModel.create_mapping()`: generate UUID here. For `/submit_proposal` → `ProposalModel.create_proposal()`: generate UUID here (reserved for the eventual mapping if proposal approved). When admin approves a proposal via `/admin/proposals/<id>/approve`, copy the proposal's reserved UUID to the newly created or updated mapping row.
**Warning signs:** Approved mappings missing UUID, or UUIDs changing between proposal and approval.

### Pitfall 3: Duplicate Check Race Condition Window
**What goes wrong:** The live duplicate check fires when KE + pathway are selected. The curator then spends time on the 4-question assessment (several minutes possible). By the time they submit, another curator may have submitted the same pair. The `/submit` endpoint's `UNIQUE(ke_id, wp_id)` constraint handles this at the DB layer (returns None), but the error message to the user is generic.
**Why it happens:** Optimistic client-side check doesn't guarantee state at submission time.
**How to avoid:** The existing `IntegrityError` catch in `MappingModel.create_mapping()` already returns `None` on duplicate. The API returns `{"error": "The KE-WP pair already exists in the dataset."}` with 400. The frontend already handles this error (`showMessage`). This is acceptable — the live check is a UX courtesy, the DB constraint is the true gate. Document this in the plan as intentional.

### Pitfall 4: Pending Proposal vs. Approved Mapping Confusion in Check Response
**What goes wrong:** The new `/check` response must distinguish between "blocked by approved mapping" and "blocked by pending proposal" because the available actions differ (submit revision vs. flag stale). If the response is ambiguous, the frontend renders the wrong CTAs.
**How to avoid:** Add a `blocking_type` field to the check response: `"approved_mapping"` or `"pending_proposal"`. Include enough data in the `existing` object for the inline preview to render without a second API call. Test both blocking cases explicitly.

### Pitfall 5: GitHub Username Not Available for Guest Users
**What goes wrong:** Guest users (authenticated via workshop access codes) have a `username` like `"guest-workshop2025"` in their session. This gets stored as `approved_by_curator` / `created_by`. The provenance display shows `"guest-workshop2025"` in the browse table — not a real GitHub username.
**How to avoid:** This is acceptable by design (guest users exist). The display should show the stored username as-is. The detail view and admin view can differentiate by checking if the username starts with `"guest-"`. Document this in the plan. No special handling needed unless explicitly requested.
**Warning signs:** If the plan tries to add GitHub API lookup for username display — that's over-engineering.

### Pitfall 6: Two Parallel Tables (mappings + ke_go_mappings) — Must Apply Symmetrically
**What goes wrong:** Every schema change for KE-WP mappings must be mirrored for KE-GO mappings. The decisions state duplicate detection applies equally to both mapping types. The `ke_go_mappings` table and `ke_go_proposals` table need identical new columns.
**How to avoid:** The plan must explicitly list tasks for both tables. The `ke_go_proposals` table already has `approved_by` / `approved_at` / `rejected_by` / `rejected_at` columns (note: `proposals` table does NOT have these yet — confirmed in `models.py`). So `proposals` needs to catch up via migration.

---

## Code Examples

Verified patterns from the live codebase:

### UUID Generation (stdlib — no install needed)
```python
# Source: Python stdlib, confirmed working in Python 3.x
import uuid

def create_mapping(self, ke_id, ke_title, wp_id, wp_title, ...):
    mapping_uuid = str(uuid.uuid4())
    cursor = conn.execute("""
        INSERT INTO mappings (ke_id, ke_title, wp_id, wp_title, ..., uuid)
        VALUES (?, ?, ?, ?, ..., ?)
    """, (ke_id, ke_title, wp_id, wp_title, ..., mapping_uuid))
```

### Migration Column Check (existing pattern)
```python
# Source: src/core/models.py, _migrate_proposals_admin_fields (lines 195-233)
cursor = conn.execute("PRAGMA table_info(mappings)")
columns = [row[1] for row in cursor.fetchall()]
if "uuid" not in columns:
    conn.execute("ALTER TABLE mappings ADD COLUMN uuid TEXT")
```

### GitHub Username from Session (existing pattern)
```python
# Source: src/blueprints/api.py line 145, src/blueprints/admin.py line 247
github_username = session.get("user", {}).get("username", "unknown")
```

### Check Mapping + Pending Proposals (new enriched check)
```python
# New: check both approved mappings AND pending proposals
def check_mapping_exists_with_proposals(self, ke_id: str, wp_id: str) -> Dict:
    conn = self.db.get_connection()
    try:
        # Check approved mapping
        cursor = conn.execute(
            "SELECT uuid, confidence_level, approved_by_curator, approved_at_curator "
            "FROM mappings WHERE ke_id = ? AND wp_id = ?",
            (ke_id, wp_id)
        )
        mapping = cursor.fetchone()
        if mapping:
            return {
                "pair_exists": True,
                "blocking_type": "approved_mapping",
                "existing": dict(mapping),
                "actions": ["submit_revision"],
            }

        # Check pending proposals
        cursor = conn.execute(
            "SELECT id, uuid, proposed_confidence, github_username, created_at "
            "FROM proposals "
            "WHERE ke_id = ? AND wp_id = ? AND status = 'pending'",
            (ke_id, wp_id)
        )
        # Note: current proposals table has mapping_id, not ke_id/wp_id directly
        # Need JOIN or denormalize ke_id/wp_id onto proposals for this query
        ...
    finally:
        conn.close()
```

Note: The current `proposals` table links via `mapping_id` to `mappings`, not directly by `ke_id`/`wp_id`. For new mappings (no `mapping_id` yet), pending proposals cannot be found this way. The plan must address this: either store `ke_id`/`wp_id` directly on `proposals`, or check pending new-mapping proposals via a separate query path. Storing `ke_id`/`wp_id` directly on `proposals` is the cleaner approach.

### Confidence Select-Button Pattern (from existing assessment step CSS)
```css
/* Source: static/css/main.css lines 354-380 — already defined, no new CSS needed */
.btn-group { display: flex; flex-wrap: wrap; gap: 10px; }
.btn-option { padding: 12px 20px; border: 2px solid var(--color-border-light); ... }
.btn-option.selected { background-color: var(--color-primary-blue); color: white; }
```

### Admin Approval Writing Provenance to Mapping (existing flow to extend)
```python
# Source: src/blueprints/admin.py, approve_proposal (lines 214-306)
# Currently calls: mapping_model.update_mapping(mapping_id, ...)
# Need to also pass: approved_by_curator=admin_username, approved_at_curator=now

# Extended MappingModel.update_mapping() call:
mapping_model.update_mapping(
    mapping_id=mapping_id,
    connection_type=proposal["proposed_connection_type"],
    confidence_level=proposal["proposed_confidence"],
    updated_by=admin_username,
    approved_by_curator=admin_username,   # NEW
    approved_at_curator=datetime.utcnow(), # NEW
)
```

### URL Routing for Stable Mapping Records (Claude's Discretion)

**Recommendation: UUID-based URLs** — `/mappings/<uuid>` for individual mapping detail pages.

**Rationale:**
- The decision states UUIDs are stable identifiers that "will not change after publication." UUID-based URLs make that contract visible in the URL itself.
- Integer IDs in URLs expose internal DB row order and change meaning if rows are deleted/re-inserted.
- The admin UI can also use UUID-based URLs for the detail view (maps to `/admin/mappings/<uuid>`).
- For internal admin endpoints where UUID is not yet established (e.g., `/admin/proposals/<id>`), keep integer IDs — those are proposal row IDs, not mapping identifiers.

```python
# New route in main_bp or api_bp:
@main_bp.route("/mappings/<string:mapping_uuid>")
def mapping_detail(mapping_uuid):
    mapping = mapping_model.get_mapping_by_uuid(mapping_uuid)
    if not mapping:
        abort(404)
    return render_template("mapping_detail.html", mapping=mapping)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| Approval audit fields only on `ke_go_proposals` | Add same fields to `proposals` table via migration | Brings both proposal tables to parity — required for CURAT-01 |
| `/check` returns simple boolean exists | Enriched `/check` returns blocking type + preview data | Enables inline duplicate preview UX |
| Confidence auto-computed, stored as hidden field | Confidence explicitly selected by curator as required step | Satisfies CURAT-03 "required field" locked decision |
| No stable identifier | UUID on every mapping and proposal | Satisfies EXPLO-04 |

**Asymmetry to be aware of:** `ke_go_proposals` already has `approved_by` / `approved_at` / `rejected_by` / `rejected_at` columns (visible in `init_db()` at lines 124-145 of `models.py`). The `proposals` table (KE-WP) only has these added via `_migrate_proposals_admin_fields`. When writing the new migration for provenance columns on the `mappings` table, verify what already exists to avoid double-adding.

---

## Open Questions

1. **Where to store ke_id/wp_id on new-mapping proposals for pending-proposal duplicate check**
   - What we know: Current `proposals` table links via `mapping_id → mappings.id`. For a brand-new pair, there is no mapping yet, so `mapping_id` is NULL on proposals for new mappings.
   - What's unclear: How does the current system handle the case where a curator submits a NEW KE-WP pair? Looking at `api.py /submit` — it creates the mapping directly, no proposal. Looking at `api.py /submit_proposal` — it requires an existing `mapping_id`. So currently, ALL new-mapping submissions go directly to `/submit` (no proposal, no admin review).
   - Implication for duplicate detection: Pending proposals are ONLY change proposals on existing mappings. A brand-new pair submitted via `/submit` goes straight to the DB. So the pending-proposal check for new submissions only needs to look at change proposals on the same mapping (which does have a `mapping_id`). No need to store `ke_id`/`wp_id` on proposals.
   - Recommendation: Verify this reading of the code is correct before implementing the enriched check. The plan should explicitly state this assumption.

2. **Suggestion score storage location**
   - What we know: Suggestion scores are BioBERT hybrid scores computed at suggestion time. The decision says to store them "with each proposal."
   - What's unclear: The suggestion score is only available at the moment the curator picks a suggested pathway — it's not sent back to the server currently. Adding it means the frontend must capture the score from the suggestion card and include it in the form submission.
   - Recommendation: Add `suggestion_score REAL` column to both `proposals` and `ke_go_proposals`. Modify the frontend to pass `suggestion_score` as a hidden form field, populated when the curator clicks a suggestion card. If curator uses manual search/browse (no suggestion selected), `suggestion_score` is NULL.

3. **Revision proposal flow — what exactly gets created**
   - What we know: "If an approved mapping exists, the curator can submit a revision proposal (flags the existing mapping for update, goes back to admin review)." This is a change proposal on an existing mapping — exactly what `/submit_proposal` already does.
   - What's unclear: Does the inline preview's "Submit Revision" CTA pre-fill the proposal form with the existing mapping's values? The UX should be: click "Submit Revision" → proposal modal opens pre-filled with the current mapping's confidence/connection type → curator edits and submits.
   - Recommendation: Plan should specify that "Submit Revision" from the inline preview triggers the same proposal modal flow as the existing "Propose Change" button on the explore table, pre-populated with current values. No new endpoint needed — reuse `/submit_proposal`.

---

## Sources

### Primary (HIGH confidence)
- Live codebase — `src/core/models.py` — full schema, migration pattern, all model methods
- Live codebase — `src/blueprints/api.py` — `/check`, `/submit`, `/submit_proposal`, `/check_go_entry`, `/submit_go_mapping` endpoint implementations
- Live codebase — `src/blueprints/admin.py` — approval flow, `approved_by`/`approved_at` handling
- Live codebase — `src/core/schemas.py` — Marshmallow schema patterns, `confidence_level` validation
- Live codebase — `static/js/main.js` — duplicate check flow (line 456), assessment step structure (lines 865-939)
- Live codebase — `static/css/main.css` — `.btn-option`, `.btn-group` classes (lines 354-380)
- Live codebase — `templates/explore.html` — browse table column structure
- Live codebase — `templates/index.html` — 4-step assessment form structure
- Python stdlib docs — `uuid.uuid4()` — confirmed available, no install needed

### Secondary (MEDIUM confidence)
- SQLite documentation — `ALTER TABLE ADD COLUMN` behavior with NOT NULL constraints (well-known SQLite limitation, consistent across versions)
- SQLite `PRAGMA table_info` — column introspection, confirmed by existing usage in codebase

### Tertiary (LOW confidence)
None — all findings are grounded in live code, no unverified external sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are already in the codebase
- Architecture: HIGH — patterns directly observed in live code
- Pitfalls: HIGH — derived from reading actual code paths and SQLite behavior
- Open questions: MEDIUM — two of three questions are self-answerable by careful code reading; flagged for plan-time verification

**Research date:** 2026-02-20
**Valid until:** Stable — this is a mature, slow-moving Flask/SQLite codebase. Research valid indefinitely unless schema or blueprint structure changes.
