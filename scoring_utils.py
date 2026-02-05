"""
Shared scoring utilities for combining multi-signal suggestions.

Used by both PathwaySuggestionService (WP) and GoSuggestionService (GO)
for merging and weighting scored items from multiple evidence sources.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def combine_scored_items(
    scored_lists: Dict[str, List[Dict]],
    id_field: str,
    weights: Dict[str, float],
    score_field_map: Dict[str, str],
    multi_evidence_bonus: float = 0.05,
    min_threshold: float = 0.15,
    max_score: float = 0.98,
) -> List[Dict]:
    """
    Merge and weight scored items from multiple evidence sources.

    Takes N named lists of scored items, merges them by a shared ID field,
    computes a weighted hybrid score, and returns the merged list sorted
    by hybrid_score descending.

    Args:
        scored_lists: Named lists of scored items,
            e.g. {"gene": [...], "text": [...], "embedding": [...]}
        id_field: Key to merge on ("pathwayID" for WP, "go_id" for GO)
        weights: Weight per signal, e.g. {"gene": 0.35, "text": 0.25, "embedding": 0.40}
        score_field_map: Maps signal name to the score field in each item,
            e.g. {"gene": "confidence_score", "text": "confidence_score", "embedding": "confidence_score"}
        multi_evidence_bonus: Bonus added when >= 2 signals have non-zero scores
        min_threshold: Minimum hybrid_score to include in results
        max_score: Maximum hybrid_score cap

    Returns:
        Merged list sorted by hybrid_score descending, each item containing:
        - All fields from the first signal that introduces the item (first writer wins)
        - 'signal_scores': dict of {signal_name: score} for each signal
        - 'hybrid_score': the final weighted+bonus score
        - 'match_types': list of signal names that contributed non-zero scores
        - '_signal_data': dict of {signal_name: original_item_dict} for per-signal access
    """
    item_map = {}

    for signal_name, items in scored_lists.items():
        score_field = score_field_map[signal_name]

        for item in items:
            item_id = item[id_field]
            score = item.get(score_field, 0.0)

            if item_id not in item_map:
                # First time seeing this ID - init with item data
                item_map[item_id] = {
                    **item,
                    'signal_scores': {s: 0.0 for s in weights},
                    'match_types': [],
                }

            entry = item_map[item_id]

            # Record this signal's score
            entry['signal_scores'][signal_name] = score
            if score > 0.0 and signal_name not in entry['match_types']:
                entry['match_types'].append(signal_name)

            # Store per-signal item data so callers can access
            # signal-specific fields (e.g. embedding's title_similarity
            # vs text's title_similarity) without field collisions.
            entry.setdefault('_signal_data', {})[signal_name] = item

    # Calculate hybrid scores
    results = []
    for item_id, entry in item_map.items():
        scores = entry['signal_scores']

        # Weighted sum
        hybrid = sum(
            scores[signal_name] * weights[signal_name]
            for signal_name in weights
        )

        # Multi-evidence bonus
        active_signals = sum(1 for s in scores.values() if s > 0.0)
        if active_signals >= 2:
            hybrid += multi_evidence_bonus

        # Apply cap
        hybrid = min(hybrid, max_score)

        if hybrid < min_threshold:
            continue

        entry['hybrid_score'] = round(hybrid, 4)
        results.append(entry)

    # Sort by hybrid_score descending
    results.sort(key=lambda x: x['hybrid_score'], reverse=True)

    return results
