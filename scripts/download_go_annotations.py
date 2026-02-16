"""
Download and process GO gene annotations for human

Downloads the UniProt-GOA human annotations file, parses GAF format,
filters to Biological Process annotations, and maps gene symbols.

Usage:
    python scripts/download_go_annotations.py

Output:
    go_bp_gene_annotations.json - {go_id: [gene_symbols]}
"""

import sys
import os
import json
import gzip
import logging
from urllib.request import urlretrieve
from collections import defaultdict

sys.path.insert(0, os.path.abspath('.'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UniProt-GOA human annotations
GOA_URL = "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/goa_human.gaf.gz"
GOA_LOCAL = "data/goa_human.gaf.gz"


def download_goa_file(url=GOA_URL, local_path=GOA_LOCAL):
    """Download GOA file if not already present"""
    if os.path.exists(local_path):
        logger.info(f"Using existing GOA file: {local_path}")
        return local_path

    logger.info(f"Downloading GOA file from {url}...")
    urlretrieve(url, local_path)
    logger.info(f"Downloaded to {local_path}")
    return local_path


def parse_gaf_file(gaf_path):
    """
    Parse GAF (Gene Association Format) file

    GAF format columns:
    0: DB
    1: DB_Object_ID (UniProt ID)
    2: DB_Object_Symbol (Gene symbol)
    3: Qualifier
    4: GO_ID
    5: DB:Reference
    6: Evidence Code
    7: With/From
    8: Aspect (P=Biological Process, F=Molecular Function, C=Cellular Component)
    9: DB_Object_Name
    10: DB_Object_Synonym
    11: DB_Object_Type
    12: Taxon
    13: Date
    14: Assigned_By

    Returns:
        dict: {go_id: set(gene_symbols)} for Biological Process only
    """
    logger.info(f"Parsing GAF file: {gaf_path}")

    go_gene_map = defaultdict(set)
    total_lines = 0
    bp_lines = 0

    opener = gzip.open if gaf_path.endswith('.gz') else open

    with opener(gaf_path, 'rt', encoding='utf-8') as f:
        for line in f:
            # Skip comment lines
            if line.startswith('!'):
                continue

            total_lines += 1
            fields = line.strip().split('\t')

            if len(fields) < 15:
                continue

            aspect = fields[8]
            # Only keep Biological Process annotations
            if aspect != 'P':
                continue

            bp_lines += 1

            go_id = fields[4]
            gene_symbol = fields[2]
            qualifier = fields[3]

            # Skip negative annotations (NOT)
            if 'NOT' in qualifier:
                continue

            if gene_symbol and go_id:
                go_gene_map[go_id].add(gene_symbol)

    logger.info(f"Parsed {total_lines} total lines, {bp_lines} BP annotations")
    logger.info(f"Found {len(go_gene_map)} unique GO BP terms with gene annotations")

    return go_gene_map


def download_go_annotations(output_path='data/go_bp_gene_annotations.json'):
    """
    Download and process GO gene annotations for human BP terms
    """
    # Download GOA file
    gaf_path = download_goa_file()

    # Parse GAF file
    go_gene_map = parse_gaf_file(gaf_path)

    # Convert sets to sorted lists for JSON serialization
    go_gene_annotations = {}
    for go_id, genes in go_gene_map.items():
        go_gene_annotations[go_id] = sorted(list(genes))

    # Save to JSON
    logger.info(f"Saving gene annotations to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(go_gene_annotations, f, indent=2)

    file_size = os.path.getsize(output_path) / 1024 / 1024
    logger.info(f"Gene annotations saved: {file_size:.2f} MB")

    # Print statistics
    total_genes = set()
    for genes in go_gene_annotations.values():
        total_genes.update(genes)

    logger.info(f"GO BP terms with annotations: {len(go_gene_annotations)}")
    logger.info(f"Unique gene symbols: {len(total_genes)}")

    # Print sample
    sample_ids = list(go_gene_annotations.keys())[:3]
    for go_id in sample_ids:
        genes = go_gene_annotations[go_id]
        logger.info(f"Sample {go_id}: {len(genes)} genes - {genes[:5]}...")


if __name__ == '__main__':
    download_go_annotations()
