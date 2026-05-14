"""
Publish (or version-bump) the curated KE → WikiPathways / GO / Reactome
mapping database to Zenodo.

Assembles three per-resource ZIP archives (KE-WikiPathways.zip, KE-GO.zip,
KE-Reactome.zip), each containing GMT files split by confidence level
(All / High / Medium / Low) plus a Turtle file with full curation
provenance, alongside a README that quantifies per-tier mapping counts
and explains the confidence rubric.

If the concept DOI in data/zenodo_meta.json already exists, a new
version is minted under it (inherited files from the previous version
are deleted first, so the new release contains only the intended
shape). Otherwise the first version is created and the concept DOI
captured.

Usage
-----
    docker exec <container> python /app/scripts/publish_zenodo.py [opts]

Options
-------
    --dry-run        Build the deposit in memory and print what would
                     happen; do NOT touch Zenodo or modify meta file.
    --sandbox        Use https://sandbox.zenodo.org instead of production.
                     Requires ZENODO_SANDBOX_API_TOKEN env var.
    --force          Publish even when per-resource mapping counts are
                     unchanged since the last recorded deposit.
    --min-delta N    Skip the publish if the total approved-mapping count
                     across all three resources differs by less than N
                     rows from the last recorded deposit. Default: 1.

Exit codes
----------
    0   Publish completed, or skipped because nothing has changed.
    1   Configuration error (missing token, app context, etc.).
    2   Zenodo API error during publish.
    3   Another invocation is holding the lock.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import io
import json
import logging
import os
import sys
import traceback
import zipfile
from collections import Counter
from pathlib import Path
from typing import Optional

import requests

DEFAULT_META_PATH = Path("data/zenodo_meta.json")
LOCK_PATH = Path("/tmp/molaop-zenodo-publish.lock")
PROD_BASE = "https://zenodo.org/api"
SANDBOX_BASE = "https://sandbox.zenodo.org/api"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("publish_zenodo")


# ---------- counts + change detection ----------

def _counts(rows: list) -> dict:
    c = Counter((r.get("confidence_level") or "").lower() for r in rows)
    return {
        "All": len(rows),
        "High": c.get("high", 0),
        "Medium": c.get("medium", 0),
        "Low": c.get("low", 0),
    }


def _changes_significant(current: dict, last: Optional[dict], min_delta: int) -> bool:
    if not last:
        return True
    delta = abs(current["wp"]["All"] - last.get("wp", {}).get("All", 0)) \
          + abs(current["go"]["All"] - last.get("go", {}).get("All", 0)) \
          + abs(current["reactome"]["All"] - last.get("reactome", {}).get("All", 0))
    log.info("Mapping-count delta since last deposit: %d (threshold: %d)", delta, min_delta)
    return delta >= min_delta


# ---------- deposit assembly ----------

def _build_resource_zip(prefix: str, gmt_fn, ttl_fn, mappings: list, today: str, gmt_kwargs=None) -> bytes:
    buf = io.BytesIO()
    gmt_kwargs = gmt_kwargs or {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, conf in [("All", None), ("High", "high"), ("Medium", "medium"), ("Low", "low")]:
            content = gmt_fn(mappings, min_confidence=conf, **gmt_kwargs)
            if content:
                zf.writestr(f"{prefix}/{prefix}_{today}_{label}.gmt", content)
        ttl_content = ttl_fn(mappings)
        if ttl_content:
            zf.writestr(f"{prefix}/{prefix.lower()}-mappings.ttl", ttl_content)
    return buf.getvalue()


def _build_readme(today: str, wp_n: dict, go_n: dict, rx_n: dict) -> bytes:
    return (
        f"""# Molecular AOP Builder — Curated KE → WikiPathways / GO / Reactome Mappings

**Published:** {today}
**Source application:** https://molaop-builder.vhp4safety.nl
**Repository:** https://github.com/marvinm2/KE-WP-mapping
**License:** CC0 1.0 Universal (public domain dedication)

This deposit contains the current curated mappings between Key Events (KEs) of the Adverse Outcome Pathway framework and three molecular-pathway / ontology resources. Each mapping has been proposed by a curator, scored by a BioBERT-based suggestion engine, assessed against a structured confidence rubric, and approved by an administrator before inclusion in the dataset.

## Contents

The deposit is organised as three per-resource ZIP archives plus this README:

| Archive                  | Resource                                              | Approved mappings (this version) |
|--------------------------|-------------------------------------------------------|----------------------------------|
| `KE-WikiPathways.zip`     | WikiPathways pathways (`WP####`)                      | **{wp_n['All']}** total · {wp_n['High']} High · {wp_n['Medium']} Medium · {wp_n['Low']} Low |
| `KE-GO.zip`               | Gene Ontology Biological Process / Molecular Function | **{go_n['All']}** total · {go_n['High']} High · {go_n['Medium']} Medium · {go_n['Low']} Low |
| `KE-Reactome.zip`         | Reactome pathways (`R-HSA-#######`)                   | **{rx_n['All']}** total · {rx_n['High']} High · {rx_n['Medium']} Medium · {rx_n['Low']} Low |

Each archive expands to a folder containing:

- `*_{{YYYY-MM-DD}}_{{Level}}.gmt` — Gene Matrix Transposed (GMT) gene-set files, one row per KE → pathway/GO mapping. Gene identifiers are HGNC symbols. Loadable directly by clusterProfiler (`enricher()`) and fgsea (`gmtPathways()`).
- `*-mappings.ttl` — RDF / Turtle serialisation with full provenance for every approved mapping for that resource: proposer, approving curator, approval timestamp, BioBERT suggestion score, confidence level, connection type. Suitable for SPARQL queries and ontology integration.

## Confidence levels

Each mapping is assessed by the approving curator against a structured rubric covering relationship type, evidence basis, KE-specificity, and mechanism coverage. The rubric produces an integer score (0–7.5 with a biological-level bonus) which is then bucketed into one of three named levels; **All** is the unfiltered superset:

- **All** — the unfiltered set of approved mappings, irrespective of confidence. Use this when you want maximum coverage and will filter or weight downstream yourself.
- **High** — direct and specific biological link with strong experimental evidence. Recommended for downstream pathway-enrichment analyses where false positives are costly.
- **Medium** — partial or indirect biological relationship with moderate evidence. Useful as a broader hypothesis set.
- **Low** — weak, speculative, or unclear biological connection. Included for completeness; downstream users should treat with caution.

A `_<Level>.gmt` file appears only if there is at least one mapping at that level at the time of deposit. Missing levels indicate zero mappings in that bucket.

## Identifiers

- Key Event IDs follow AOP-Wiki canonical numbering (e.g. `KE 1234`)
- WikiPathways IDs follow `WP####`
- Gene Ontology IDs follow OBO Foundry CURIEs (`GO:#######`)
- Reactome IDs follow stable identifiers (`R-HSA-#######`)
- Every mapping carries a stable UUID, visible in the RDF/Turtle export and in the `/api/v1/...` REST endpoints on the live builder.

## Citation

If you use these mappings, please cite this Zenodo record (the concept DOI always resolves to the latest version) and acknowledge the upstream resources: AOP-Wiki, WikiPathways, the Gene Ontology Consortium / UniProt-GOA, and Reactome.
"""
    ).encode("utf-8")


def _build_metadata(today: str) -> dict:
    return {
        "title": "Molecular AOP Builder — Curated KE → WikiPathways / GO / Reactome Mappings",
        "upload_type": "dataset",
        "description": (
            "Curated database of Key Event (KE) mappings to three molecular-pathway and ontology "
            "resources: WikiPathways (KE-WikiPathways), Gene Ontology Biological Process and "
            "Molecular Function (KE-GO), and Reactome (KE-Reactome). Mappings are bundled in three "
            "per-resource ZIP archives, each containing GMT gene-set files split by confidence "
            "level (All / High / Medium / Low) for clusterProfiler and fgsea, and RDF/Turtle for "
            "SPARQL and linked-data consumption. Each mapping carries a stable UUID and full "
            "curation provenance (proposer, approving curator, approval timestamp, BioBERT "
            "suggestion score, confidence level, connection type). "
            "Produced by the Molecular AOP Builder at https://molaop-builder.vhp4safety.nl ; "
            "source at https://github.com/marvinm2/KE-WP-mapping ."
        ),
        "creators": [{
            "name": "Martens, Marvin",
            "affiliation": "Department of Translational Genomics, Maastricht University",
            "orcid": "0000-0003-2230-0840",
        }],
        "keywords": [
            "Adverse Outcome Pathway", "AOP", "Key Event", "WikiPathways", "Gene Ontology",
            "Reactome", "toxicology", "pathway analysis", "GMT", "RDF", "BioBERT", "curation",
        ],
        "license": "cc-zero",
        "publication_date": today,
        "version": today,
        "access_right": "open",
    }


# ---------- Zenodo I/O ----------

def _zenodo_new_or_newversion(base: str, h_auth: dict, h_json: dict, existing_id: Optional[int]):
    """Return (deposition_id, bucket_url) — either fresh or a new-version draft."""
    if existing_id:
        log.info("Creating new Zenodo version from deposition %s", existing_id)
        r = requests.post(f"{base}/deposit/depositions/{existing_id}/actions/newversion",
                          headers=h_auth, timeout=30)
        r.raise_for_status()
        draft_url = r.json()["links"]["latest_draft"]
        dep_id = int(draft_url.rstrip("/").split("/")[-1])
        r2 = requests.get(draft_url, headers=h_auth, timeout=30)
        r2.raise_for_status()
        draft = r2.json()
        # Delete every inherited file so the new version only contains what we upload.
        inherited = draft.get("files", [])
        log.info("Inherited %d file(s) from previous version — deleting", len(inherited))
        for f in inherited:
            fid, fname = f["id"], f["filename"]
            dr = requests.delete(f"{base}/deposit/depositions/{dep_id}/files/{fid}",
                                 headers=h_auth, timeout=30)
            if dr.status_code not in (204, 200):
                raise RuntimeError(f"Failed to delete inherited file {fname}: {dr.status_code} {dr.text[:200]}")
        return dep_id, draft["links"]["bucket"]
    else:
        log.info("Creating first-ever Zenodo deposit (no existing concept)")
        r = requests.post(f"{base}/deposit/depositions", json={}, headers=h_json, timeout=30)
        r.raise_for_status()
        body = r.json()
        return body["id"], body["links"]["bucket"]


def _upload_files(bucket_url: str, files: dict, h_auth: dict) -> None:
    for fname, data in files.items():
        if isinstance(data, str):
            data = data.encode("utf-8")
        log.info("Uploading %s (%d bytes)", fname, len(data))
        r = requests.put(f"{bucket_url}/{fname}", data=data, headers=h_auth, timeout=600)
        r.raise_for_status()


# ---------- meta file persistence ----------

def _write_meta(meta_path: Path, payload: dict) -> Path:
    """Try to write the meta file; on EACCES fall back to /tmp/ and log loudly."""
    try:
        meta_path.write_text(json.dumps(payload, indent=2) + "\n")
        return meta_path
    except PermissionError:
        fallback = Path("/tmp/zenodo_meta_pending.json")
        fallback.write_text(json.dumps(payload, indent=2) + "\n")
        log.error(
            "Could not write %s (EACCES). Saved to %s — operator must copy it to "
            "%s on the host (or to /mnt/gluster/docker/molaop-builder/data/zenodo_meta.json "
            "if the host filesystem differs from the container view). #158 follow-up.",
            meta_path, fallback, meta_path,
        )
        return fallback


# ---------- main ----------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="Assemble but do not publish")
    p.add_argument("--sandbox", action="store_true", help="Use sandbox.zenodo.org")
    p.add_argument("--force", action="store_true", help="Publish even if no counts changed")
    p.add_argument("--min-delta", type=int, default=1, help="Min total row-count change to trigger publish (default 1)")
    p.add_argument("--meta-path", type=Path, default=DEFAULT_META_PATH, help="Path to zenodo_meta.json")
    args = p.parse_args()

    # Acquire lock first to avoid concurrent runs.
    try:
        lock_fp = open(LOCK_PATH, "w")
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError) as e:
        log.error("Could not acquire lock %s — another publish in progress? %s", LOCK_PATH, e)
        return 3

    try:
        # Token + base URL
        if args.sandbox:
            base = SANDBOX_BASE
            token = os.environ.get("ZENODO_SANDBOX_API_TOKEN")
            tok_var = "ZENODO_SANDBOX_API_TOKEN"
        else:
            base = PROD_BASE
            token = os.environ.get("ZENODO_API_TOKEN")
            tok_var = "ZENODO_API_TOKEN"
        if not args.dry_run and not token:
            log.error("%s is not set — cannot publish", tok_var)
            return 1
        h_auth = {"Authorization": f"Bearer {token}"} if token else {}
        h_json = {**h_auth, "Content-Type": "application/json"} if token else {}

        # Boot the Flask app to get access to the model layer
        sys.path.insert(0, "/app")  # in case launched outside /app
        try:
            from app import create_app
        except Exception as e:
            log.error("Could not import create_app: %s", e)
            return 1
        app = create_app()
        with app.app_context():
            from src.blueprints import admin as a
            from src.exporters.gmt_exporter import (
                generate_ke_wp_gmt, generate_ke_go_gmt, generate_ke_reactome_gmt,
            )
            from src.exporters.rdf_exporter import (
                generate_ke_wp_turtle, generate_ke_go_turtle, generate_ke_reactome_turtle,
            )

            wp = a.mapping_model.get_all_mappings() if a.mapping_model else []
            go = a.go_mapping_model.get_all_mappings() if a.go_mapping_model else []
            rx = a.reactome_mapping_model.get_all_mappings() if a.reactome_mapping_model else []
            wp_n, go_n, rx_n = _counts(wp), _counts(go), _counts(rx)
            today = datetime.date.today().isoformat()
            current_counts = {"wp": wp_n, "go": go_n, "reactome": rx_n}

            log.info(
                "Current counts — WP: %d (H:%d M:%d L:%d) | GO: %d (H:%d M:%d L:%d) | "
                "Reactome: %d (H:%d M:%d L:%d)",
                wp_n["All"], wp_n["High"], wp_n["Medium"], wp_n["Low"],
                go_n["All"], go_n["High"], go_n["Medium"], go_n["Low"],
                rx_n["All"], rx_n["High"], rx_n["Medium"], rx_n["Low"],
            )

            # Load previous meta + skip-if-unchanged gate
            existing_meta = {}
            if args.meta_path.exists():
                try:
                    existing_meta = json.loads(args.meta_path.read_text())
                except Exception as e:
                    log.warning("Could not parse %s — treating as empty: %s", args.meta_path, e)
            existing_id = existing_meta.get("deposition_id")
            last_counts = existing_meta.get("counts")

            if not args.force and not _changes_significant(current_counts, last_counts, args.min_delta):
                log.info("[SKIP] Mapping counts unchanged since last deposit — nothing to do")
                return 0

            # Build deposit contents
            files = {
                "KE-WikiPathways.zip": _build_resource_zip(
                    "KE-WikiPathways", generate_ke_wp_gmt, generate_ke_wp_turtle, wp, today,
                    gmt_kwargs={"cache_model": a.cache_model_ref},
                ),
                "KE-GO.zip":       _build_resource_zip("KE-GO", generate_ke_go_gmt, generate_ke_go_turtle, go, today),
                "KE-Reactome.zip": _build_resource_zip("KE-Reactome", generate_ke_reactome_gmt, generate_ke_reactome_turtle, rx, today),
                "README.md":       _build_readme(today, wp_n, go_n, rx_n),
            }
            for name, blob in files.items():
                log.info("Assembled %s (%d bytes)", name, len(blob))

            metadata = _build_metadata(today)

            if args.dry_run:
                log.info("[DRY-RUN] Would publish a new version under existing_id=%s with %d file(s).",
                         existing_id, len(files))
                log.info("[DRY-RUN] Metadata title:   %s", metadata["title"])
                log.info("[DRY-RUN] Metadata version: %s", metadata["version"])
                log.info("[DRY-RUN] Endpoint:         %s", base)
                return 0

            # Real publish
            try:
                dep_id, bucket_url = _zenodo_new_or_newversion(base, h_auth, h_json, existing_id)
                log.info("Draft id=%s  bucket=%s", dep_id, bucket_url)
                _upload_files(bucket_url, files, h_auth)
                r = requests.put(
                    f"{base}/deposit/depositions/{dep_id}",
                    data=json.dumps({"metadata": metadata}),
                    headers=h_json, timeout=30,
                )
                r.raise_for_status()
                r = requests.post(
                    f"{base}/deposit/depositions/{dep_id}/actions/publish",
                    headers=h_auth, timeout=60,
                )
                r.raise_for_status()
                result = r.json()
            except requests.HTTPError as e:
                log.error("Zenodo API error: %s — body: %s", e, getattr(e.response, "text", "")[:500])
                return 2

            # Persist updated meta
            new_meta = {
                "deposition_id": result["id"],
                "doi": result["doi"],
                "concept_doi": result.get("conceptdoi", existing_meta.get("concept_doi")),
                "published_at": today,
                "version": metadata["version"],
                "counts": current_counts,
            }
            written_to = _write_meta(args.meta_path, new_meta)

            log.info("[DONE] DOI=%s  concept=%s  version=%s  meta=%s",
                     new_meta["doi"], new_meta["concept_doi"], new_meta["version"], written_to)
            return 0
    except Exception:
        log.error("Unhandled exception:\n%s", traceback.format_exc())
        return 1
    finally:
        try:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
            lock_fp.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
