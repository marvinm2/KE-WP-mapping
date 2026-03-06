"""
Pre-compute GO hierarchy data with IC scores, depths, and ancestors

Downloads go-basic.obo, parses biological_process terms, computes
Information Content from the gene annotation corpus, and writes
data/go_hierarchy.json for use by the GO suggestion scoring pipeline.

Usage:
    python scripts/precompute_go_hierarchy.py [--force]

Output:
    data/go_hierarchy.json - Per-term hierarchy data (depth, IC, ancestors)
"""

import argparse
import json
import logging
import math
import os
import sys
from collections import defaultdict, deque
from urllib.request import urlretrieve, Request, urlopen

# Setup project path (same pattern as precompute_go_embeddings.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

GO_BASIC_OBO_URL = "https://purl.obolibrary.org/obo/go/go-basic.obo"
GO_BASIC_OBO_LOCAL = "data/go-basic.obo"
ANNOTATIONS_PATH = "data/go_bp_gene_annotations.json"
OUTPUT_PATH = "data/go_hierarchy.json"

BP_ROOT = "GO:0008150"


def download_go_obo(url=GO_BASIC_OBO_URL, local_path=GO_BASIC_OBO_LOCAL, force=False):
    """Download go-basic.obo if not already present or if force=True."""
    if os.path.exists(local_path) and not force:
        logger.info(f"Using existing OBO file: {local_path}")
        return local_path

    logger.info(f"Downloading go-basic.obo from {url}...")
    req = Request(url, headers={'User-Agent': 'KE-WP-Mapping/1.0'})
    with urlopen(req) as response, open(local_path, 'wb') as out_file:
        out_file.write(response.read())
    size_mb = os.path.getsize(local_path) / 1024 / 1024
    logger.info(f"Downloaded to {local_path} ({size_mb:.1f} MB)")
    return local_path


def parse_obo_file(obo_path):
    """
    Parse go-basic.obo and extract all biological_process terms.

    Returns:
        tuple: (terms_dict, obsolete_remap_dict)
            terms_dict: {go_id: {name, namespace, is_a[], part_of[]}}
            obsolete_remap: {obsolete_id: replacement_id}
    """
    logger.info(f"Parsing OBO file: {obo_path}")

    terms = {}
    obsolete_terms = []
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
                    'is_a': [],
                    'part_of': [],
                    'is_obsolete': False,
                    'replaced_by': None,
                    'consider': [],
                }
                continue

            if line == '' or line.startswith('['):
                if in_term and current_term and current_term['id']:
                    if current_term['namespace'] == 'biological_process':
                        if current_term['is_obsolete']:
                            obsolete_terms.append(current_term)
                        else:
                            go_id = current_term['id']
                            terms[go_id] = {
                                'name': current_term['name'],
                                'namespace': current_term['namespace'],
                                'is_a': current_term['is_a'],
                                'part_of': current_term['part_of'],
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
            elif line.startswith('is_a: '):
                # Strip comment after !
                parent_id = line[6:].split(' ! ')[0].strip()
                current_term['is_a'].append(parent_id)
            elif line.startswith('relationship: part_of '):
                part_id = line[22:].split(' ! ')[0].strip()
                current_term['part_of'].append(part_id)
            elif line == 'is_obsolete: true':
                current_term['is_obsolete'] = True
            elif line.startswith('replaced_by: '):
                current_term['replaced_by'] = line[13:].strip()
            elif line.startswith('consider: '):
                current_term['consider'].append(line[10:].strip())

    # Build obsolete remap dict
    remap = {}
    skipped = 0
    for term in obsolete_terms:
        obs_id = term['id']
        if term['replaced_by'] and term['replaced_by'] in terms:
            remap[obs_id] = term['replaced_by']
        elif term['consider']:
            # Use first consider term that exists in our active terms
            found = False
            for candidate in term['consider']:
                if candidate in terms:
                    remap[obs_id] = candidate
                    found = True
                    break
            if not found:
                logger.warning(f"Obsolete term {obs_id} ({term['name']}): no valid replacement found")
                skipped += 1
        else:
            logger.warning(f"Obsolete term {obs_id} ({term['name']}): no replaced_by or consider fields")
            skipped += 1

    logger.info(f"Parsed {len(terms)} active biological_process terms")
    logger.info(f"Found {len(obsolete_terms)} obsolete BP terms")
    logger.info(f"Remapped {len(remap)} obsolete terms, skipped {skipped} with no replacement")

    return terms, remap


def build_parents_map(terms):
    """Build parents map from is_a + part_of relationships."""
    parents = defaultdict(set)
    for go_id, data in terms.items():
        for parent_id in data['is_a']:
            if parent_id in terms:
                parents[go_id].add(parent_id)
        for parent_id in data['part_of']:
            if parent_id in terms:
                parents[go_id].add(parent_id)
    return parents


def compute_ancestors(terms, parents_map):
    """
    Compute transitive closure of ancestors for each term.

    Uses memoized recursive traversal with cycle guard.
    """
    ancestors_cache = {}
    in_progress = set()  # cycle guard

    def _get_ancestors(go_id):
        if go_id in ancestors_cache:
            return ancestors_cache[go_id]

        if go_id in in_progress:
            logger.warning(f"Cycle detected at {go_id}, breaking")
            return set()

        in_progress.add(go_id)
        result = set()
        for parent in parents_map.get(go_id, set()):
            result.add(parent)
            result.update(_get_ancestors(parent))
        in_progress.discard(go_id)

        ancestors_cache[go_id] = result
        return result

    logger.info("Computing transitive ancestors...")
    for go_id in terms:
        _get_ancestors(go_id)

    return ancestors_cache


def compute_depths(terms, parents_map):
    """
    Compute minimum depth from root (GO:0008150) via BFS.

    Returns dict: {go_id: depth}
    """
    logger.info("Computing depths via BFS from root...")

    # Build children map for BFS
    children = defaultdict(set)
    for go_id, parent_ids in parents_map.items():
        for pid in parent_ids:
            children[pid].add(go_id)

    depths = {}
    queue = deque([(BP_ROOT, 0)])
    depths[BP_ROOT] = 0

    while queue:
        current, depth = queue.popleft()
        for child in children.get(current, set()):
            if child not in depths or depth + 1 < depths[child]:
                depths[child] = depth + 1
                queue.append((child, depth + 1))

    # Terms not reachable from root get depth -1 (should be rare in go-basic.obo)
    unreachable = 0
    for go_id in terms:
        if go_id not in depths:
            depths[go_id] = -1
            unreachable += 1

    if unreachable > 0:
        logger.warning(f"{unreachable} terms not reachable from root {BP_ROOT}")

    max_depth = max(d for d in depths.values() if d >= 0)
    logger.info(f"Depth range: 0 to {max_depth}")

    return depths


def compute_ic_scores(terms, ancestors_cache, annotations_path, remap):
    """
    Compute Information Content scores from gene annotation corpus.

    IC(t) = -log2(freq(t) / freq(root))
    Normalized to [0, 1] by dividing by max IC.
    Root forced to IC = 0.0.
    """
    logger.info(f"Loading annotation corpus from {annotations_path}...")
    with open(annotations_path, 'r') as f:
        raw_annotations = json.load(f)

    # Apply obsolete term remapping to annotations
    annotations = defaultdict(set)
    remapped_count = 0
    for go_id, genes in raw_annotations.items():
        effective_id = remap.get(go_id, go_id)
        if effective_id != go_id:
            remapped_count += 1
        if effective_id in terms:
            annotations[effective_id].update(genes)

    logger.info(f"Remapped {remapped_count} annotation entries via obsolete term remap")
    logger.info(f"Annotations cover {len(annotations)} active terms")

    # Propagate annotations upward: each gene annotated to t is also
    # implicitly annotated to all ancestors of t
    logger.info("Propagating annotations upward through hierarchy...")
    propagated = defaultdict(set)
    for go_id, genes in annotations.items():
        propagated[go_id].update(genes)
        for ancestor in ancestors_cache.get(go_id, set()):
            propagated[ancestor].update(genes)

    # Compute IC
    root_freq = len(propagated.get(BP_ROOT, set()))
    if root_freq == 0:
        logger.error("Root term has no annotations after propagation!")
        root_freq = 1  # avoid division by zero

    logger.info(f"Root term {BP_ROOT} has {root_freq} unique genes after propagation")

    raw_ic = {}
    for go_id in terms:
        freq = len(propagated.get(go_id, set()))
        if freq == 0:
            # Terms with no annotations get maximum IC (most specific/rare)
            raw_ic[go_id] = None  # placeholder, set after max computation
        else:
            raw_ic[go_id] = -math.log2(freq / root_freq)

    # Force root IC = 0.0 (log2(1) = 0)
    raw_ic[BP_ROOT] = 0.0

    # Find max IC among computed values for normalization
    computed_ics = [v for v in raw_ic.values() if v is not None]
    max_ic = max(computed_ics) if computed_ics else 1.0

    # Normalize to [0, 1]
    ic_scores = {}
    for go_id, ic_val in raw_ic.items():
        if ic_val is None:
            ic_scores[go_id] = 1.0  # no annotations = max specificity
        else:
            ic_scores[go_id] = ic_val / max_ic if max_ic > 0 else 0.0

    # Force root to exactly 0.0
    ic_scores[BP_ROOT] = 0.0

    # Stats
    non_zero = sum(1 for v in ic_scores.values() if v > 0)
    logger.info(f"IC scores computed: {len(ic_scores)} terms, {non_zero} with IC > 0")
    logger.info(f"IC range: 0.0 to {max(ic_scores.values()):.4f} (normalized)")

    return ic_scores


def build_hierarchy_json(terms, ancestors_cache, depths, ic_scores):
    """Build the final hierarchy JSON structure."""
    hierarchy = {}
    for go_id, data in terms.items():
        hierarchy[go_id] = {
            'name': data['name'],
            'namespace': data['namespace'],
            'depth': depths.get(go_id, -1),
            'ic_score': round(ic_scores.get(go_id, 0.0), 6),
            'ancestors': sorted(list(ancestors_cache.get(go_id, set()))),
            'is_obsolete': False,
        }
    return hierarchy


def main():
    parser = argparse.ArgumentParser(
        description='Pre-compute GO hierarchy data with IC scores'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Force re-download of go-basic.obo'
    )
    args = parser.parse_args()

    # Download OBO
    obo_path = download_go_obo(force=args.force)

    # Parse
    terms, remap = parse_obo_file(obo_path)

    # Build hierarchy structures
    parents_map = build_parents_map(terms)
    ancestors_cache = compute_ancestors(terms, parents_map)
    depths = compute_depths(terms, parents_map)

    # Compute IC scores
    ic_scores = compute_ic_scores(terms, ancestors_cache, ANNOTATIONS_PATH, remap)

    # Build output
    hierarchy = build_hierarchy_json(terms, ancestors_cache, depths, ic_scores)

    # Write output
    logger.info(f"Writing {len(hierarchy)} terms to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)

    size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    logger.info(f"Output: {OUTPUT_PATH} ({size_mb:.1f} MB)")
    logger.info("Done.")


if __name__ == '__main__':
    main()
