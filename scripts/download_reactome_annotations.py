"""
Download and process Reactome gene annotations for Homo sapiens.

Downloads the Reactome GMT file, parses it for Homo sapiens pathways,
excludes Disease branch descendants via the Content Service API,
filters by gene count (3-500), normalizes stable IDs, and saves
the output as data/reactome_gene_annotations.json.

Usage:
    python scripts/download_reactome_annotations.py [--output PATH] [--force]

    --output PATH  Override output file path
    --force        Re-download GMT even if cached locally

Output:
    data/reactome_gene_annotations.json  - {stId: [gene_symbols]}
    data/reactome_filtered_stids.json    - [stId, ...] (sorted list for embedding script)
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from urllib.request import urlretrieve

import requests

sys.path.insert(0, os.path.abspath('.'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reactome GMT download source
GMT_URL = "https://download.reactome.org/current/ReactomePathways.gmt.zip"
GMT_ZIP_LOCAL = "data/ReactomePathways.gmt.zip"
GMT_LOCAL = "data/ReactomePathways.gmt"

# Reactome Content Service
CONTENT_SERVICE = "https://reactome.org/ContentService"

# Disease branch root — descendants are excluded from output
DISEASE_ROOT = "R-HSA-1643685"

# Gene count filter bounds
MIN_GENES = 3
MAX_GENES = 500

# Output file paths
OUTPUT_PATH = "data/reactome_gene_annotations.json"
FILTERED_STIDS_PATH = "data/reactome_filtered_stids.json"


def download_gmt(url=GMT_URL, zip_path=GMT_ZIP_LOCAL, gmt_path=GMT_LOCAL, force=False):
    """
    Download and extract ReactomePathways.gmt if not already present.

    Args:
        url: URL to the GMT zip file
        zip_path: Local path for the downloaded zip archive
        gmt_path: Local path for the extracted GMT file
        force: Re-download even if gmt_path already exists

    Returns:
        str: Path to the extracted GMT file
    """
    if not force and os.path.exists(gmt_path):
        logger.info("Using existing GMT file: %s", gmt_path)
        return gmt_path

    logger.info("Downloading GMT from %s ...", url)
    urlretrieve(url, zip_path)
    logger.info("Downloaded zip to %s", zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # The zip contains a single .gmt file
        gmt_names = [n for n in zf.namelist() if n.endswith('.gmt')]
        if not gmt_names:
            raise ValueError(f"No .gmt file found in {zip_path}")
        gmt_name = gmt_names[0]
        logger.info("Extracting %s ...", gmt_name)
        with zf.open(gmt_name) as src, open(gmt_path, 'wb') as dst:
            dst.write(src.read())

    logger.info("Extracted to %s", gmt_path)
    return gmt_path


def parse_gmt_file(gmt_path):
    """
    Parse ReactomePathways.gmt and return gene annotations for Homo sapiens.

    GMT column format:
        col 0: pathway display name
        col 1: stableId (e.g., R-HSA-12345 or R-HSA-12345.3)
        col 2: "Reactome Pathway" (literal string or URL — skip)
        col 3+: HGNC gene symbols

    Filters:
        - Only Homo sapiens pathways (stableId prefix R-HSA-)
        - Version suffix stripped: R-HSA-12345.3 -> R-HSA-12345

    Args:
        gmt_path: Path to the extracted GMT file

    Returns:
        dict: {stId: sorted_list_of_gene_symbols}
    """
    logger.info("Parsing GMT file: %s", gmt_path)
    annotations = {}
    skipped_species = 0
    skipped_short = 0

    # Log first few lines for column layout verification
    with open(gmt_path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 3:
                parts = line.strip().split('\t')
                logger.info("GMT col check [line %d]: col0=%r, col1=%r, col2=%r, genes=%d",
                            i, parts[0][:40] if parts else '', parts[1] if len(parts) > 1 else '',
                            parts[2] if len(parts) > 2 else '', max(0, len(parts) - 3))

    with open(gmt_path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')

            # Need at least: name, stableId, description
            if len(parts) < 3:
                skipped_short += 1
                continue

            # col 1 = stableId (NOT col 0 which is display name)
            stable_id = parts[1]

            # Filter to Homo sapiens only (D-09)
            if not stable_id.startswith('R-HSA-'):
                skipped_species += 1
                continue

            # Strip version suffix if present: R-HSA-12345.3 -> R-HSA-12345 (D-06, RDATA-05)
            stable_id = stable_id.split('.')[0]

            # Genes start at col 3 (col 2 is "Reactome Pathway" or URL)
            genes = [g.strip() for g in parts[3:] if g.strip()]
            annotations[stable_id] = sorted(set(genes))

    logger.info("Parsed %d Homo sapiens pathways (skipped: %d other species, %d short lines)",
                len(annotations), skipped_species, skipped_short)
    return annotations


def fetch_disease_descendants():
    """
    Fetch all stIds under the Disease branch (R-HSA-1643685) via Content Service.

    The containedEvents endpoint returns descendants but NOT the root itself —
    so we always add DISEASE_ROOT to the exclusion set manually.

    Returns:
        set: All stIds (version-free) to exclude (includes root)
    """
    url = f"{CONTENT_SERVICE}/data/pathway/{DISEASE_ROOT}/containedEvents"
    logger.info("Fetching disease descendants from %s ...", url)

    resp = requests.get(url, headers={"Accept": "application/json"}, timeout=60)
    resp.raise_for_status()
    events = resp.json()

    # Always include root itself — containedEvents does NOT return the root (Pitfall 3)
    disease_ids = {DISEASE_ROOT}

    for event in events:
        stid = event.get('stId', '')
        if stid:
            # Strip version suffix just in case (defensive)
            disease_ids.add(stid.split('.')[0])

    logger.info("Disease branch: %d pathways to exclude", len(disease_ids))
    return disease_ids


def filter_annotations(raw_annotations, disease_ids, min_genes=MIN_GENES, max_genes=MAX_GENES):
    """
    Filter raw annotations by disease exclusion and gene count bounds.

    Args:
        raw_annotations: dict {stId: [gene_symbols]}
        disease_ids: set of stIds to exclude (Disease branch)
        min_genes: minimum gene count (inclusive)
        max_genes: maximum gene count (inclusive)

    Returns:
        dict: Filtered {stId: [gene_symbols]}
    """
    filtered = {}
    n_disease = 0
    n_genecount = 0

    for stid, genes in raw_annotations.items():
        if stid in disease_ids:
            n_disease += 1
            continue
        if not (min_genes <= len(genes) <= max_genes):
            n_genecount += 1
            continue
        filtered[stid] = genes

    logger.info(
        "Filter results: %d kept (from %d raw) | excluded: %d disease branch, %d gene count out of bounds",
        len(filtered), len(raw_annotations), n_disease, n_genecount
    )
    return filtered


def download_reactome_annotations(output_path=OUTPUT_PATH, force=False):
    """
    Main pipeline: download GMT -> parse -> fetch disease descendants -> filter -> save.

    Args:
        output_path: Path for the gene annotations JSON output
        force: Re-download GMT even if cached

    Returns:
        dict: Filtered gene annotations {stId: [gene_symbols]}
    """
    # Step 1: Download and extract GMT
    gmt_path = download_gmt(force=force)

    # Step 2: Parse GMT for Homo sapiens gene annotations
    raw_annotations = parse_gmt_file(gmt_path)
    logger.info("Total Homo sapiens pathways from GMT: %d", len(raw_annotations))

    # Step 3: Fetch Disease branch descendants for exclusion (D-07)
    disease_ids = fetch_disease_descendants()

    # Step 4: Filter by disease exclusion + gene count (D-07, D-08)
    filtered = filter_annotations(raw_annotations, disease_ids, min_genes=MIN_GENES, max_genes=MAX_GENES)

    # Step 5: Save gene annotations JSON
    logger.info("Saving gene annotations to %s ...", output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, indent=2)

    file_size_mb = os.path.getsize(output_path) / 1024 / 1024
    logger.info("Saved %d pathways: %.2f MB", len(filtered), file_size_mb)

    # Step 6: Save filtered stId list for embedding script (Plan 02)
    filtered_stids = sorted(filtered.keys())
    with open(FILTERED_STIDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(filtered_stids, f, indent=2)
    logger.info("Saved %d filtered stIds to %s", len(filtered_stids), FILTERED_STIDS_PATH)

    # Step 7: Log summary statistics
    total_unique_genes = len(set(g for genes in filtered.values() for g in genes))
    logger.info("Summary: %d pathways | %d unique gene symbols", len(filtered), total_unique_genes)

    # Print 3 sample entries for verification (same pattern as GO script)
    sample_ids = list(filtered.keys())[:3]
    for stid in sample_ids:
        genes = filtered[stid]
        logger.info("Sample %s: %d genes - %s...", stid, len(genes), genes[:5])

    return filtered


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download and process Reactome gene annotations for Homo sapiens'
    )
    parser.add_argument(
        '--output', default=OUTPUT_PATH,
        help=f'Output file path for gene annotations JSON (default: {OUTPUT_PATH})'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Re-download GMT file even if cached locally'
    )
    args = parser.parse_args()

    download_reactome_annotations(output_path=args.output, force=args.force)
