"""
Pre-compute BioBERT embeddings for GO Biological Process terms

Downloads the GO OBO file, parses biological_process terms,
generates BioBERT embeddings, and saves metadata.

Usage:
    python scripts/precompute_go_embeddings.py

Output:
    go_bp_name_embeddings.npy - NumPy dictionary {go_id: embedding_vector} (name only)
    go_bp_embeddings.npy - NumPy dictionary {go_id: embedding_vector} (name + definition)
    go_bp_metadata.json - {go_id: {name, definition, is_a[], part_of[]}}
"""

import os
import re
import json
import logging
from urllib.request import urlretrieve

from embedding_utils import setup_project_path, init_embedding_service, compute_embeddings_batch, save_embeddings

setup_project_path()

from src.utils.text import remove_directionality_terms, extract_entities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GO_OBO_URL = "http://purl.obolibrary.org/obo/go.obo"
GO_OBO_LOCAL = "data/go.obo"


def download_go_obo(url=GO_OBO_URL, local_path=GO_OBO_LOCAL):
    """Download GO OBO file if not already present"""
    if os.path.exists(local_path):
        logger.info(f"Using existing OBO file: {local_path}")
        return local_path

    logger.info(f"Downloading GO OBO file from {url}...")
    urlretrieve(url, local_path)
    logger.info(f"Downloaded to {local_path}")
    return local_path


def parse_obo_file(obo_path):
    """
    Parse GO OBO file and extract biological_process terms

    Returns:
        dict: {go_id: {name, definition, is_a[], part_of[]}}
    """
    logger.info(f"Parsing OBO file: {obo_path}")

    terms = {}
    current_term = None
    in_term = False

    with open(obo_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            if line == '[Term]':
                in_term = True
                current_term = {
                    'id': None,
                    'name': None,
                    'namespace': None,
                    'definition': '',
                    'is_a': [],
                    'part_of': [],
                    'synonyms': [],
                    'is_obsolete': False
                }
                continue

            if line == '' or line.startswith('['):
                if in_term and current_term and current_term['id']:
                    # Save term if it's a biological_process and not obsolete
                    if (current_term['namespace'] == 'biological_process'
                            and not current_term['is_obsolete']):
                        go_id = current_term['id']
                        terms[go_id] = {
                            'name': current_term['name'],
                            'definition': current_term['definition'],
                            'is_a': current_term['is_a'],
                            'part_of': current_term['part_of'],
                            'synonyms': current_term['synonyms']
                        }
                in_term = False
                current_term = None
                continue

            if not in_term or current_term is None:
                continue

            if line.startswith('id: '):
                current_term['id'] = line[4:]
            elif line.startswith('name: '):
                current_term['name'] = line[6:]
            elif line.startswith('namespace: '):
                current_term['namespace'] = line[11:]
            elif line.startswith('def: '):
                # Extract definition text from quotes
                match = re.match(r'def: "(.+?)"', line)
                if match:
                    current_term['definition'] = match.group(1)
            elif line.startswith('is_a: '):
                # Extract parent GO ID
                parent_id = line[6:].split(' ! ')[0].strip()
                current_term['is_a'].append(parent_id)
            elif line.startswith('relationship: part_of '):
                part_id = line[22:].split(' ! ')[0].strip()
                current_term['part_of'].append(part_id)
            elif line.startswith('synonym: '):
                # synonym: "alt name" EXACT|BROAD|NARROW|RELATED [...]
                m = re.match(r'synonym: "(.+?)"\s+(EXACT|BROAD|NARROW|RELATED)', line)
                if m:
                    current_term['synonyms'].append({
                        'text': m.group(1),
                        'type': m.group(2)
                    })
            elif line == 'is_obsolete: true':
                current_term['is_obsolete'] = True

    logger.info(f"Parsed {len(terms)} biological_process GO terms")
    return terms


def precompute_go_embeddings(
    embeddings_path='data/go_bp_embeddings.npy',
    name_embeddings_path='data/go_bp_name_embeddings.npy',
    metadata_path='data/go_bp_metadata.json'
):
    """
    Parse GO OBO file and pre-compute BioBERT embeddings for all BP terms.

    Produces two embedding files:
    - name_embeddings_path: name-only embeddings (like pathway titles)
    - embeddings_path: combined name+definition embeddings (like pathway descriptions)
    """
    # Download OBO file
    obo_path = download_go_obo()

    # Parse GO terms
    go_terms = parse_obo_file(obo_path)

    # Save metadata
    logger.info(f"Saving metadata to {metadata_path}...")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(go_terms, f, indent=2)
    logger.info(f"Metadata saved: {os.path.getsize(metadata_path) / 1024 / 1024:.2f} MB")

    # Initialize embedding service
    embedding_service = init_embedding_service()

    # Build name-only items {id: cleaned_name}
    name_items = {}
    for go_id, term_data in go_terms.items():
        name = term_data['name']
        name_items[go_id] = extract_entities(remove_directionality_terms(name))

    logger.info("Computing name-only embeddings...")
    name_embeddings = compute_embeddings_batch(embedding_service, name_items, label="GO BP names")
    save_embeddings(name_embeddings, name_embeddings_path)

    # Build combined name+definition items {id: cleaned_text}
    combined_items = {}
    for go_id, term_data in go_terms.items():
        name = term_data['name']
        definition = term_data.get('definition', '')
        text = f"{name}. {definition}" if definition else name
        combined_items[go_id] = extract_entities(remove_directionality_terms(text))

    logger.info("Computing combined (name+definition) embeddings...")
    combined_embeddings = compute_embeddings_batch(embedding_service, combined_items, label="GO BP terms")
    save_embeddings(combined_embeddings, embeddings_path)


if __name__ == '__main__':
    precompute_go_embeddings()
