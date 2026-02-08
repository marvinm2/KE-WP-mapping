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


# Unified stopword set (union of all previous implementations)
_ENTITY_STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'into', 'that', 'this',
    'are', 'was', 'were', 'via', 'any', 'its', 'has', 'have',
}

# Directionality terms to skip during entity extraction
_ENTITY_DIRECTIONALITY = {
    'increase', 'decrease', 'activation', 'inhibition', 'induction', 'reduction',
    'elevated', 'reduced', 'upregulation', 'downregulation',
}

# Known biological terms for bio_only filtering
_BIOLOGICAL_TERMS = {
    'gene', 'protein', 'enzyme', 'receptor', 'kinase', 'phosphatase',
    'pathway', 'signaling', 'transcription', 'expression', 'regulation',
    'apoptosis', 'proliferation', 'differentiation', 'metabolism',
    'oxidative', 'stress', 'inflammation', 'immune', 'cancer', 'tumor',
    'cell', 'cellular', 'mitochondria', 'nucleus', 'membrane', 'cytoplasm',
    'dna', 'rna', 'mrna', 'chromosome', 'histone', 'epigenetic',
    'insulin', 'glucose', 'lipid', 'fatty', 'cholesterol', 'steroid',
    'hormone', 'neurotransmitter', 'cytokine', 'chemokine', 'interleukin',
    'activation', 'inhibition', 'binding', 'phosphorylation', 'methylation',
}


def extract_entities(
    text: str,
    min_length: int = 3,
    include_numbers: bool = True,
    bio_only: bool = False,
    extra_stopwords: set = None
) -> str:
    """
    Extract biological entities from text for more specific embedding.

    Removes stopwords and directionality terms, keeping only significant tokens.
    Optionally filters to known biological terms only.

    Args:
        text: Input text (KE title, pathway name, GO term, etc.)
        min_length: Minimum token length to keep
        include_numbers: Whether to keep tokens containing digits
        bio_only: If True, only keep known biological terms and gene-like identifiers
        extra_stopwords: Additional stopwords to skip

    Returns:
        Space-separated string of extracted entities, or original text if no entities found
    """
    if not text:
        return ""

    # Build combined skip set
    skip = _ENTITY_STOPWORDS | _ENTITY_DIRECTIONALITY
    if extra_stopwords:
        skip = skip | extra_stopwords

    # Tokenize: split on non-alphanumeric, keeping alphanumeric tokens
    if include_numbers:
        tokens = re.findall(r'[A-Za-z0-9]+', text)
    else:
        tokens = re.findall(r'[A-Za-z]+', text)

    entities = []
    for token in tokens:
        if len(token) < min_length:
            continue

        token_lower = token.lower()

        if token_lower in skip:
            continue

        if bio_only:
            if token_lower in _BIOLOGICAL_TERMS:
                entities.append(token)
            elif include_numbers and re.match(r'^[A-Z]+[0-9]+', token):
                entities.append(token)
        else:
            entities.append(token)

    if not entities:
        return text

    return ' '.join(entities)
