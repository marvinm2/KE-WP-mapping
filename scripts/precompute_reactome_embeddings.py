"""
Pre-compute BioBERT embeddings for Reactome pathway names and descriptions.

Fetches pathway metadata (names, HTML-stripped descriptions) from the Reactome
Content Service API for all filtered Homo sapiens pathways produced by
download_reactome_annotations.py, then generates dual BioBERT embedding sets:
  - name-only embeddings (reactome_pathway_name_embeddings.npz)
  - name+description embeddings (reactome_pathway_embeddings.npz)

This mirrors the precompute_go_embeddings.py pattern and produces files loadable
by BiologicalEmbeddingService with standard 'ids'/'matrix' keys.

Usage:
    python scripts/precompute_reactome_embeddings.py
    python scripts/precompute_reactome_embeddings.py \\
        --metadata-path data/reactome_pathway_metadata.json \\
        --embeddings-path data/reactome_pathway_embeddings \\
        --name-embeddings-path data/reactome_pathway_name_embeddings

Prerequisites:
    Run download_reactome_annotations.py first to produce:
        data/reactome_gene_annotations.json
        data/reactome_filtered_stids.json

Output:
    data/reactome_pathway_metadata.json       - {stId: {name, description}}
    data/reactome_pathway_embeddings.npz      - name+description BioBERT embeddings
    data/reactome_pathway_name_embeddings.npz - name-only BioBERT embeddings
"""

import argparse
import html
import json
import logging
import os
import re
import socket
import ssl
import sys
import time

import requests
from tqdm import tqdm

from embedding_utils import setup_project_path, init_embedding_service, compute_embeddings_batch, save_embeddings

setup_project_path()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reactome Content Service base URL
CONTENT_SERVICE = "https://reactome.org/ContentService"

# Input files produced by Plan 01 (download_reactome_annotations.py)
ANNOTATIONS_PATH = "data/reactome_gene_annotations.json"
FILTERED_STIDS_PATH = "data/reactome_filtered_stids.json"

# Output file paths (.npz extension added automatically by save_embeddings)
METADATA_PATH = "data/reactome_pathway_metadata.json"
EMBEDDINGS_PATH = "data/reactome_pathway_embeddings"       # .npz added by save_embeddings
NAME_EMBEDDINGS_PATH = "data/reactome_pathway_name_embeddings"  # .npz added by save_embeddings

# API batching parameters
BATCH_SIZE = 100
BATCH_DELAY = 0.2  # seconds between API batches (polite pacing — no documented rate limit)


# ---------------------------------------------------------------------------
# Helper: Content Service HTTP with IP fallback
# ---------------------------------------------------------------------------

def _post_content_service(path, data, timeout=60):
    """
    POST to the Reactome Content Service, falling back to a raw IP connection
    if the hostname-based HTTPS times out (network routing issue in some environments).

    Args:
        path: URL path (e.g. "/ContentService/data/query/ids")
        data: POST body as bytes or string
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response (list or dict)
    """
    url = f"https://reactome.org{path}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
        "User-Agent": "Python/3 ReactomePipeline/1.0",
    }

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
        logger.warning("Direct HTTPS POST failed (%s), trying via resolved IP ...", e)

    # Fallback: resolve hostname, connect via IP with SNI override
    try:
        addrs = socket.getaddrinfo("reactome.org", 443, socket.AF_INET)
        ip = addrs[0][4][0]
    except Exception:
        raise RuntimeError("Cannot resolve reactome.org — check network connectivity")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Encode body
    body_bytes = data.encode("utf-8") if isinstance(data, str) else data
    content_length = len(body_bytes)

    with socket.create_connection((ip, 443), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname="reactome.org") as ssock:
            request = (
                f"POST {path} HTTP/1.1\r\n"
                f"Host: reactome.org\r\n"
                f"Accept: application/json\r\n"
                f"Content-Type: text/plain\r\n"
                f"Content-Length: {content_length}\r\n"
                f"User-Agent: Python/3 ReactomePipeline/1.0\r\n"
                f"Connection: close\r\n\r\n"
            )
            ssock.sendall(request.encode("utf-8") + body_bytes)

            raw = b""
            while True:
                chunk = ssock.recv(65536)
                if not chunk:
                    break
                raw += chunk

    # Parse HTTP response
    header_end = raw.find(b"\r\n\r\n")
    if header_end == -1:
        raise RuntimeError("Malformed HTTP response from Reactome (no header boundary)")
    body = raw[header_end + 4:]

    # Decode chunked transfer encoding if applicable
    headers_raw = raw[:header_end].decode("utf-8", errors="replace")
    if "Transfer-Encoding: chunked" in headers_raw:
        decoded = b""
        while body:
            crlf = body.find(b"\r\n")
            if crlf == -1:
                break
            size = int(body[:crlf], 16)
            if size == 0:
                break
            chunk_data = body[crlf + 2: crlf + 2 + size]
            decoded += chunk_data
            body = body[crlf + 2 + size + 2:]
        body = decoded

    import json as _json
    return _json.loads(body.decode("utf-8"))


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def load_filtered_stids():
    """
    Load the list of filtered Reactome pathway stIds from Plan 01 output.

    Tries reactome_filtered_stids.json first (simple sorted list), then falls
    back to the keys of reactome_gene_annotations.json.

    Returns:
        list: stId strings (e.g. ["R-HSA-109581", ...])

    Raises:
        FileNotFoundError: If neither input file exists (run
            download_reactome_annotations.py first).
    """
    if os.path.exists(FILTERED_STIDS_PATH):
        logger.info("Loading filtered stIds from %s", FILTERED_STIDS_PATH)
        with open(FILTERED_STIDS_PATH, encoding="utf-8") as f:
            stids = json.load(f)
        logger.info("Loaded %d filtered stIds", len(stids))
        return stids

    if os.path.exists(ANNOTATIONS_PATH):
        logger.info(
            "%s not found; falling back to keys of %s",
            FILTERED_STIDS_PATH, ANNOTATIONS_PATH,
        )
        with open(ANNOTATIONS_PATH, encoding="utf-8") as f:
            annotations = json.load(f)
        stids = sorted(annotations.keys())
        logger.info("Derived %d stIds from gene annotations", len(stids))
        return stids

    raise FileNotFoundError(
        f"Neither '{FILTERED_STIDS_PATH}' nor '{ANNOTATIONS_PATH}' found. "
        "Run download_reactome_annotations.py first."
    )


def strip_html(text):
    """
    Remove HTML tags and decode HTML entities from Reactome summation text.

    Keeps full text without truncation (D-04 decision).

    Args:
        text: Raw HTML string from the Content Service summation field

    Returns:
        str: Plain text with normalized whitespace
    """
    # Remove HTML tags, replacing each with a space to prevent word merging
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities: &amp; -> &, &lt; -> <, &nbsp; -> space, etc.
    text = html.unescape(text)
    # Normalize whitespace (collapse multiple spaces, strip leading/trailing)
    return " ".join(text.split())


def fetch_metadata_batch(stids, batch_size=BATCH_SIZE):
    """
    Fetch pathway metadata from the Reactome Content Service in batches.

    Uses POST /data/query/ids with comma-separated stIds to retrieve pathway
    displayName and summation (HTML description) for each batch. Applies polite
    rate pacing (BATCH_DELAY seconds between batches) and retries on HTTP errors.

    Args:
        stids: List of pathway stId strings to fetch
        batch_size: Number of stIds per batch POST request

    Returns:
        dict: {stId: {"name": str, "description": str}} — description is HTML-stripped
    """
    metadata = {}
    batches = [stids[i: i + batch_size] for i in range(0, len(stids), batch_size)]
    path = "/ContentService/data/query/ids"

    logger.info(
        "Fetching metadata for %d pathways in %d batches (batch_size=%d) ...",
        len(stids), len(batches), batch_size,
    )

    for batch in tqdm(batches, desc="Fetching metadata batches"):
        ids_param = ",".join(batch)

        # Attempt batch POST; retry once on HTTP error (429 / 5xx)
        for attempt in range(2):
            try:
                result = _post_content_service(path, ids_param, timeout=60)
                break
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if attempt == 0 and status in (429, 500, 502, 503, 504):
                    logger.warning(
                        "Batch HTTP error %d, sleeping 30s before retry ...", status
                    )
                    time.sleep(30)
                else:
                    logger.warning("Batch fetch failed: %s — skipping batch", e)
                    result = []
                    break
            except Exception as e:
                if attempt == 0:
                    logger.warning("Batch error: %s — retrying after 30s ...", e)
                    time.sleep(30)
                else:
                    logger.warning("Batch error on retry: %s — skipping batch", e)
                    result = []
                    break

        # Parse objects returned by the API
        for obj in result:
            if not isinstance(obj, dict):
                continue
            stid = obj.get("stId", "")
            if not stid:
                continue
            name = obj.get("displayName", "")
            # summation is a list of objects (Pitfall 6: NOT a single string)
            summation_list = obj.get("summation", [])
            raw_desc = (
                summation_list[0].get("text", "")
                if summation_list and isinstance(summation_list[0], dict)
                else ""
            )
            description = strip_html(raw_desc)
            metadata[stid] = {"name": name, "description": description}

        time.sleep(BATCH_DELAY)

    # Cross-check: log any stIds missing from API response (Pitfall 5)
    missing = set(stids) - set(metadata.keys())
    missing_pct = len(missing) / len(stids) * 100 if stids else 0
    if missing_pct > 5:
        logger.warning(
            "High miss rate: %d/%d stIds not returned by API (%.1f%%) — "
            "possible retired or redirected pathways",
            len(missing), len(stids), missing_pct,
        )
    elif missing:
        logger.info(
            "%d stIds not found in API response (%.1f%%) — "
            "likely retired pathways",
            len(missing), missing_pct,
        )

    logger.info("Fetched metadata for %d pathways", len(metadata))
    return metadata


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def precompute_reactome_embeddings(
    metadata_path=METADATA_PATH,
    embeddings_path=EMBEDDINGS_PATH,
    name_embeddings_path=NAME_EMBEDDINGS_PATH,
):
    """
    Full pipeline: load stIds -> fetch metadata -> save JSON -> compute dual embeddings.

    Steps:
        A. Load filtered stIds from Plan 01 output files
        B. Fetch pathway names and descriptions from Content Service API
        C. Save pathway metadata as JSON
        D. Initialize BioBERT embedding service
        E. Compute name-only embeddings, save NPZ
        F. Compute name+description embeddings, save NPZ
        G. Print summary statistics

    Args:
        metadata_path: Output path for metadata JSON
        embeddings_path: Output path for combined name+description NPZ
        name_embeddings_path: Output path for name-only NPZ
    """
    # Step A: Load filtered stIds from Plan 01 output
    stids = load_filtered_stids()
    logger.info("Loaded %d filtered pathway stIds", len(stids))

    # Step B: Fetch metadata from Content Service API
    metadata = fetch_metadata_batch(stids)

    # Step C: Save metadata JSON
    logger.info("Saving metadata to %s ...", metadata_path)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    file_size_mb = os.path.getsize(metadata_path) / 1024 / 1024
    logger.info("Metadata saved: %d entries, %.2f MB", len(metadata), file_size_mb)

    # Step D: Initialize BioBERT embedding service
    embedding_service = init_embedding_service()

    # Step E: Build name-only items and compute embeddings
    name_items = {sid: meta["name"] for sid, meta in metadata.items()}
    logger.info("Computing name-only embeddings for %d pathways ...", len(name_items))
    name_embeddings = compute_embeddings_batch(
        embedding_service, name_items, "Reactome names"
    )
    save_embeddings(name_embeddings, name_embeddings_path)

    # Step F: Build combined name+description items and compute embeddings
    combined_items = {}
    for sid, meta in metadata.items():
        name = meta["name"]
        desc = meta.get("description", "")
        # Include description if non-empty; otherwise use name alone (keeps full text per D-04)
        combined_items[sid] = f"{name}. {desc}" if desc else name

    logger.info(
        "Computing name+description embeddings for %d pathways ...", len(combined_items)
    )
    combined_embeddings = compute_embeddings_batch(
        embedding_service, combined_items, "Reactome pathways"
    )
    save_embeddings(combined_embeddings, embeddings_path)

    # Step G: Summary statistics
    with_desc = sum(1 for v in metadata.values() if v.get("description"))
    without_desc = len(metadata) - with_desc
    all_words = " ".join(
        v.get("description", "") for v in metadata.values()
    ).split()
    unique_words = len(set(w.lower() for w in all_words))

    logger.info(
        "Summary: %d pathways total | %d with descriptions | %d without | "
        "%d unique words in descriptions",
        len(metadata), with_desc, without_desc, unique_words,
    )

    # Print 3 sample entries for visual verification
    sample_ids = list(metadata.keys())[:3]
    for sid in sample_ids:
        meta = metadata[sid]
        desc_preview = meta.get("description", "")[:80]
        if len(meta.get("description", "")) > 80:
            desc_preview += "..."
        logger.info("Sample %s: name=%r | desc=%r", sid, meta["name"], desc_preview)

    logger.info("Reactome embedding precompute complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Pre-compute BioBERT embeddings for Reactome pathway names and descriptions. "
            "Requires data/reactome_filtered_stids.json (produced by "
            "download_reactome_annotations.py)."
        )
    )
    parser.add_argument(
        "--metadata-path",
        default=METADATA_PATH,
        help=f"Output path for pathway metadata JSON (default: {METADATA_PATH})",
    )
    parser.add_argument(
        "--embeddings-path",
        default=EMBEDDINGS_PATH,
        help=f"Output path for combined name+description NPZ (default: {EMBEDDINGS_PATH})",
    )
    parser.add_argument(
        "--name-embeddings-path",
        default=NAME_EMBEDDINGS_PATH,
        help=f"Output path for name-only NPZ (default: {NAME_EMBEDDINGS_PATH})",
    )
    args = parser.parse_args()

    precompute_reactome_embeddings(
        metadata_path=args.metadata_path,
        embeddings_path=args.embeddings_path,
        name_embeddings_path=args.name_embeddings_path,
    )
