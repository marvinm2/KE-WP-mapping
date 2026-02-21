"""
Zenodo API deposit and versioning workflow.
Requires ZENODO_API_TOKEN environment variable.
Uses the Zenodo bucket PUT API (not the deprecated /files POST endpoint).
"""
import json
import logging
import os
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

ZENODO_BASE = "https://zenodo.org/api"


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
    return {
        "title": "KE-WP and KE-GO Mapping Database",
        "upload_type": "dataset",
        "description": (
            "Curated database of Key Event (KE) to WikiPathways (KE-WP) and "
            "Key Event to Gene Ontology Biological Process (KE-GO) mappings. "
            "Gene sets are provided in GMT format for use with clusterProfiler and fgsea. "
            "Full provenance (curator, approval timestamp, confidence level, suggestion score) "
            "is provided in RDF/Turtle format."
        ),
        "creators": [{"name": "KE-WP Mapping Curators"}],
        "keywords": ["key events", "WikiPathways", "Gene Ontology", "AOP", "toxicology", "GMT", "RDF"],
        "license": "cc-zero",
        "publication_date": published_at or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "access_right": "open",
    }
