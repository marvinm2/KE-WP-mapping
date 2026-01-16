"""
Text processing utilities for KE-WP mapping
Shared functions for text cleaning and normalization
"""

import re
import logging

logger = logging.getLogger(__name__)


def remove_directionality_terms(text: str) -> str:
    """
    Remove directionality terms from KE titles for better semantic matching

    This function strips directional qualifiers (increase, decrease, activation, etc.)
    to focus on the core biological process/entity being described. This improves
    semantic matching by removing directional noise while preserving the biological entity.

    Args:
        text: Input text (typically KE title)

    Returns:
        Cleaned text with directionality terms removed

    Examples:
        >>> remove_directionality_terms("Increase, CYP2E1")
        "CYP2E1"
        >>> remove_directionality_terms("Activation of EGFR signaling")
        "EGFR signaling"
        >>> remove_directionality_terms("Decreased mitochondrial function")
        "mitochondrial function"
    """
    if not text:
        return ""

    # Define directionality terms to remove (case-insensitive)
    directionality_terms = [
        # Directional modifiers
        r'\b(increased?|increasing|increase|elevation|elevated|up-?regulated?|upregulation)\b',
        r'\b(decreased?|decreasing|decrease|reduction|reduced|down-?regulated?|downregulation)\b',
        r'\b(altered?|alteration|changes?|changed|changing|modified?|modification)\b',

        # Action types
        r'\b(activation|activated?|activating|stimulation|stimulated?|stimulating)\b',
        r'\b(inhibition|inhibited?|inhibiting|suppression|suppressed?|suppressing)\b',
        r'\b(antagonism|antagonized?|antagonizing|agonism|agonized?)\b',
        r'\b(induction|induced?|inducing|enhancement|enhanced?|enhancing)\b',
        r'\b(disruption|disrupted?|disrupting|impairment|impaired?|impairing)\b',

        # Process descriptors
        r'\b(formation|formed?|forming|generation|generated?|generating)\b',
        r'\b(accumulation|accumulated?|accumulating|depletion|depleted?|depleting)\b',
        r'\b(release|released?|releasing|secretion|secreted?|secreting)\b',
        r'\b(binding|bound|binds?|interaction|interacting|interacted?)\b',

        # General qualifiers
        r'\b(abnormal|aberrant|excessive|deficient|insufficient|over|under)\b',
        r'\b(loss|gain|lack|absence|presence)\b',
    ]

    # Apply all regex patterns to remove directionality terms
    cleaned_text = text
    for pattern in directionality_terms:
        cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)

    # Clean up extra spaces and normalize
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # If we removed too much (less than 30% of original), return a more conservative cleaning
    if len(cleaned_text) < len(text) * 0.3:
        # More conservative approach - only remove very common directional terms
        conservative_terms = [
            r'\b(increased?|decreased?|elevated?|reduced?)\b',
            r'\b(up-?regulated?|down-?regulated?)\b',
            r'\b(activation|inhibition|stimulation|suppression)\b'
        ]
        cleaned_text = text
        for pattern in conservative_terms:
            cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text if cleaned_text else text
