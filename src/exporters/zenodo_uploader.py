"""
Zenodo API deposit and versioning workflow.
Requires ZENODO_API_TOKEN environment variable.
Uses the Zenodo bucket PUT API (not the deprecated /files POST endpoint).
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

ZENODO_BASE = "https://zenodo.org/api"

# #158 follow-up: container user lacks write bit on the gluster-backed
# /app/data mount. Successful Zenodo publishes must never appear to fail
# just because we can't persist the local meta file — fall back to /tmp/
# and log loudly so the operator can copy it across.
META_FALLBACK_PATH = Path("/tmp/zenodo_meta_pending.json")


def persist_meta_with_fallback(meta_path, payload: dict) -> Path:
    """Write zenodo_meta.json with an EACCES fallback to /tmp/.

    Returns the actual Path written. On PermissionError the payload is
    persisted to META_FALLBACK_PATH and an error log instructs the operator
    to copy it back into place (uid alignment on the gluster mount is the
    upstream fix; see issue #158).
    """
    path = Path(meta_path)
    body = json.dumps(payload, indent=2) + "\n"
    try:
        path.write_text(body)
        return path
    except PermissionError:
        META_FALLBACK_PATH.write_text(body)
        logger.error(
            "Could not write %s (EACCES). Saved to %s — operator must copy "
            "it to %s on the host (or to "
            "/mnt/gluster/docker/molaop-builder/data/zenodo_meta.json if the "
            "host filesystem differs from the container view). #158 follow-up.",
            path, META_FALLBACK_PATH, path,
        )
        return META_FALLBACK_PATH


def zenodo_publish(files: dict, metadata: dict, existing_deposition_id: int = None) -> dict:
    """
    Publish or update a Zenodo dataset record.

    Args:
        files: {filename: content_str} — files to upload (GMT + Turtle + README)
        metadata: Zenodo metadata dict (title, creators, description, etc.)
        existing_deposition_id: int if updating an existing published record; None for first publish

    Returns:
        {"doi": "10.5281/zenodo.XXXXXXX", "deposition_id": XXXXXXX, "concept_doi": "..."}

    Raises:
        EnvironmentError: ZENODO_API_TOKEN not set
        requests.HTTPError: Zenodo API returned non-2xx
    """
    token = os.environ.get("ZENODO_API_TOKEN")
    if not token:
        raise EnvironmentError("ZENODO_API_TOKEN environment variable is not set")

    auth_header = {"Authorization": f"Bearer {token}"}
    json_header = {**auth_header, "Content-Type": "application/json"}

    if existing_deposition_id:
        # New version of existing record
        logger.info("Creating new Zenodo version from deposition %s", existing_deposition_id)
        r = requests.post(
            f"{ZENODO_BASE}/deposit/depositions/{existing_deposition_id}/actions/newversion",
            headers=auth_header,
            timeout=30,
        )
        r.raise_for_status()
        draft_url = r.json()["links"]["latest_draft"]
        dep_id = int(draft_url.rstrip("/").split("/")[-1])
        # Get bucket URL for new draft
        r2 = requests.get(draft_url, headers=auth_header, timeout=30)
        r2.raise_for_status()
        bucket_url = r2.json()["links"]["bucket"]
    else:
        # First-time deposit
        logger.info("Creating new Zenodo deposit")
        r = requests.post(
            f"{ZENODO_BASE}/deposit/depositions",
            json={},
            headers=json_header,
            timeout=30,
        )
        r.raise_for_status()
        dep_id = r.json()["id"]
        bucket_url = r.json()["links"]["bucket"]

    # Upload each file via bucket PUT API
    for filename, content in files.items():
        logger.info("Uploading %s to Zenodo bucket", filename)
        r = requests.put(
            f"{bucket_url}/{filename}",
            data=content.encode("utf-8") if isinstance(content, str) else content,
            headers=auth_header,
            timeout=120,
        )
        r.raise_for_status()

    # Set metadata
    r = requests.put(
        f"{ZENODO_BASE}/deposit/depositions/{dep_id}",
        data=json.dumps({"metadata": metadata}),
        headers=json_header,
        timeout=30,
    )
    r.raise_for_status()

    # Publish
    logger.info("Publishing Zenodo deposit %s", dep_id)
    r = requests.post(
        f"{ZENODO_BASE}/deposit/depositions/{dep_id}/actions/publish",
        headers=auth_header,
        timeout=60,
    )
    r.raise_for_status()
    result = r.json()
    doi = result["doi"]
    concept_doi = result.get("conceptdoi", doi)
    logger.info("Published DOI: %s (concept: %s)", doi, concept_doi)
    return {"doi": doi, "deposition_id": result["id"], "concept_doi": concept_doi}


def _build_zenodo_metadata(published_at: str = None) -> dict:
    pub_date = published_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "title": "Molecular AOP Builder — Curated KE → WikiPathways / GO / Reactome Mappings",
        "upload_type": "dataset",
        "description": (
            "Curated database of Key Event (KE) mappings to three molecular-pathway and ontology "
            "resources: WikiPathways (KE-WikiPathways), Gene Ontology Biological Process and "
            "Molecular Function (KE-GO), and Reactome (KE-Reactome). Mappings are bundled in three "
            "per-resource ZIP archives (KE-WikiPathways.zip, KE-GO.zip, KE-Reactome.zip), each "
            "containing GMT gene-set files split by confidence level (All / High / Medium / Low) "
            "for clusterProfiler and fgsea, and RDF/Turtle for SPARQL and linked-data consumption. "
            "Each mapping carries a stable UUID and full curation provenance (proposer, approving "
            "curator, approval timestamp, BioBERT suggestion score, confidence level, connection "
            "type). Produced by the Molecular AOP Builder at https://molaop-builder.vhp4safety.nl ; "
            "source at https://github.com/marvinm2/KE-WP-mapping ."
        ),
        "creators": [
            {
                "name": "Martens, Marvin",
                "affiliation": "Department of Translational Genomics, Maastricht University",
                "orcid": "0000-0003-2230-0840",
            },
        ],
        "keywords": [
            "Adverse Outcome Pathway", "AOP", "Key Event", "WikiPathways", "Gene Ontology",
            "Reactome", "toxicology", "pathway analysis", "GMT", "RDF", "BioBERT", "curation",
        ],
        "license": "cc-zero",
        "publication_date": pub_date,
        "version": pub_date,
        "access_right": "open",
    }
