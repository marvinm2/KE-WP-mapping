# Scoring Configuration Reference

This document provides comprehensive documentation for all scoring parameters in `scoring_config.yaml`.

**Last Updated**: 2026-01-13
**Configuration Version**: 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Pathway Suggestion Scoring](#pathway-suggestion-scoring)
3. [KE-Pathway Assessment Scoring](#ke-pathway-assessment-scoring)
4. [Parameter Interactions](#parameter-interactions)
5. [Use Cases and Examples](#use-cases-and-examples)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The scoring system consists of two main components:

1. **Pathway Suggestion Scoring** (Backend): Calculates confidence scores for automatically suggested pathways based on gene overlap and text similarity
2. **KE-Pathway Assessment Scoring** (Frontend): Evaluates user-provided mappings through a multi-question assessment workflow

Both systems are fully configurable via `scoring_config.yaml`.

---

## Pathway Suggestion Scoring

### Gene-Based Scoring (Refined with Pathway Specificity)

Gene-based scoring calculates confidence when genes associated with a Key Event are found in a WikiPathways pathway. The refined formula incorporates **pathway specificity** to penalize matches in large, generic pathways and reward matches in smaller, specific pathways.

**Parameters** (`pathway_suggestion.gene_scoring`):

```yaml
gene_scoring:
  overlap_weight: 0.4                    # Weight for KE gene overlap ratio
  specificity_weight: 0.4                # Weight for pathway specificity
  specificity_scaling_factor: 10.0       # Scales specificity (0.01 → 0.1, 0.10 → 1.0)
  base_boost: 0.15                       # Baseline confidence boost
  min_genes_for_high_confidence: 3       # KE gene count penalty threshold
  low_gene_penalty: 0.8                  # Penalty for KEs with < 3 genes
  max_confidence: 0.95                   # Maximum confidence cap
```

**Refined Formula**:
```
1. overlap_ratio = matching_genes / ke_genes
2. specificity = matching_genes / pathway_total_genes
3. specificity_boost = min(1.0, specificity × specificity_scaling_factor)
4. base_confidence = (overlap_ratio × overlap_weight) +
                     (specificity_boost × specificity_weight) + base_boost
5. ke_gene_penalty = 1.0 if ke_genes >= min_genes_for_high_confidence, else low_gene_penalty
6. confidence = min(max_confidence, base_confidence × ke_gene_penalty)
```

**Examples**:

| KE Genes | Matching | Pathway Genes | Overlap | Specificity | Confidence | Note |
|----------|----------|---------------|---------|-------------|------------|------|
| 1 | 1 | 100 | 100% | 1% | **0.472** | Low confidence: 1 gene + large pathway |
| 5 | 5 | 50 | 100% | 10% | **0.95** | High confidence: good match + specificity |
| 8 | 4 | 50 | 50% | 8% | **0.67** | Medium: partial overlap |
| 11 | 7 | 87 | 64% | 8% | **0.726** | Good: high overlap, some specificity |
| 2 | 1 | 20 | 50% | 5% | **0.328** | Low: only 2 KE genes (penalty) |

**Calculation Breakdown (1 KE gene, 1/100 pathway genes)**:
```
overlap_ratio = 1/1 = 1.0
specificity = 1/100 = 0.01
specificity_boost = min(1.0, 0.01 × 10) = 0.1
base_confidence = (1.0 × 0.4) + (0.1 × 0.4) + 0.15 = 0.59
ke_gene_penalty = 0.8 (only 1 gene)
confidence = 0.59 × 0.8 = 0.472
```

**Tuning Guidelines**:
- **Increase `overlap_weight`** (0.4 → 0.5): Emphasize KE gene coverage more
- **Increase `specificity_weight`** (0.4 → 0.5): Penalize large pathways more strongly
- **Increase `specificity_scaling_factor`** (10.0 → 15.0): Amplify pathway size penalty
- **Increase `base_boost`** (0.15 → 0.20): Raise all confidence scores
- **Decrease `min_genes_for_high_confidence`** (3 → 2): Be more lenient with low-gene KEs
- **Increase `low_gene_penalty`** (0.8 → 0.9): Reduce penalty for 1-2 gene KEs

**Key Improvements**:
- **Pathway Size Matters**: 1-gene match in 500-gene pathway → ~0.45 confidence (was 0.95)
- **Small Pathway Bonus**: Matching genes in smaller pathways → higher confidence
- **Gene Count Penalty**: 1-2 gene KEs are penalized (insufficient evidence)
- **Balanced Scoring**: Combines KE perspective (overlap) and pathway perspective (specificity)

**Impact**: Gene-based suggestions now show more nuanced confidence scores that reflect both gene overlap quality and pathway specificity. UI displays both KE gene ratios (e.g., "3/8 KE genes") and pathway gene ratios (e.g., "3/50 pathway genes").

### Text Similarity Scoring

Text similarity analyzes how well a pathway title/description matches the Key Event title.

**Key Parameters** (`pathway_suggestion.text_similarity`):

```yaml
text_similarity:
  important_bio_terms_weight: 2.0  # Weight multiplier for biological terms

  high_overlap_weights:            # When similarity > 0.5
    jaccard: 0.65                  # Jaccard coefficient weight
    sequence: 0.25                 # Sequence matcher weight
    substring: 0.10                # Substring score weight

  medium_overlap_weights:          # When 0.3 < similarity ≤ 0.5
    jaccard: 0.50
    sequence: 0.30
    substring: 0.20

  low_overlap_weights:             # When similarity ≤ 0.3
    jaccard: 0.40
    sequence: 0.35
    substring: 0.25
```

**Important Biological Terms** (weighted 2× by default):
- pathway, protein, gene, receptor, enzyme, metabolism
- signaling, regulation, transcription, expression
- cell, cellular, tissue, organ, biological

**Combined Similarity Formula**:
```
title_sim = weighted_average(jaccard, sequence, substring) for title
desc_sim = weighted_average(jaccard, sequence, substring) for description
combined = (title_sim × 0.7) + (desc_sim × 0.3)
```

**Confidence Score Tiers**:

```yaml
confidence_scoring:
  tier_high:           # When combined_sim > 0.8
    threshold: 0.8
    base: 0.48
    multiplier: 0.6
    # Formula: 0.48 + (combined_sim - 0.8) × 0.6

  tier_medium:         # When 0.6 < combined_sim ≤ 0.8
    threshold: 0.6
    base: 0.30
    multiplier: 0.6

  tier_low:            # When 0.4 < combined_sim ≤ 0.6
    threshold: 0.4
    base: 0.18
    multiplier: 0.6

  tier_minimal:        # When combined_sim ≤ 0.4
    threshold: 0.0
    base: 0.08
    multiplier: 0.25
```

**Examples**:
- Similarity 0.90 (high): `0.48 + (0.90 - 0.8) × 0.6` = **0.54**
- Similarity 0.70 (medium): `0.30 + (0.70 - 0.6) × 0.6` = **0.36**
- Similarity 0.50 (low): `0.18 + (0.50 - 0.4) × 0.6` = **0.24**
- Similarity 0.25 (minimal): `0.08 + 0.25 × 0.25` = **0.1425**

### Biological Level Adjustments

Confidence scores are adjusted based on the Key Event's biological level.

**Parameters** (`pathway_suggestion.biological_level_adjustments`):

```yaml
biological_level_adjustments:
  molecular:
    boost: 0.10        # +10% confidence for molecular KEs
    rationale: "Molecular KEs closely match pathway mechanisms"

  cellular:
    boost: 0.05        # +5% confidence for cellular KEs

  tissue:
    boost: 0.00        # No adjustment for tissue KEs

  organ:
    boost: -0.03       # -3% confidence for organ KEs

  individual:
    boost: -0.05       # -5% confidence for individual KEs

  population:
    boost: -0.08       # -8% confidence for population KEs
```

**Rationale**: Molecular and cellular events are more directly represented in pathway models than higher-level phenotypic outcomes.

### Dynamic Thresholds

Controls the minimum confidence required for a pathway to appear in suggestions.

**Parameters** (`pathway_suggestion.dynamic_thresholds`):

```yaml
dynamic_thresholds:
  base_threshold: 0.25         # Default minimum confidence

  adjustments_by_specificity:
    high_specificity_terms:    # Specific processes (stricter)
      boost: 0.05              # Threshold → 0.30
      terms: ["apoptosis", "proliferation", "differentiation"]

    broad_terms:               # General processes (more lenient)
      boost: -0.05             # Threshold → 0.20
      terms: ["function", "activity", "regulation"]
```

**Effect**: Determines how many suggestions appear:
- **Lower threshold** (0.20): More suggestions, including borderline matches
- **Higher threshold** (0.30): Fewer, higher-confidence suggestions only

### Final Confidence Bounds

**Parameters** (`pathway_suggestion.confidence_final_bounds`):

```yaml
confidence_final_bounds:
  minimum: 0.08    # Floor - no score goes below this
  maximum: 0.98    # Ceiling - no score goes above this
```

**Purpose**: Prevents extreme values and maintains score interpretability.

---

## KE-Pathway Assessment Scoring

The assessment workflow guides users through 4 questions to evaluate a KE-pathway mapping.

### Question 2: Evidence Basis

**Parameters** (`ke_pathway_assessment.evidence_quality`):

```yaml
evidence_quality:
  known: 3        # Known, documented connection
  likely: 2       # Likely based on knowledge
  possible: 1     # Possible but uncertain
  uncertain: 0    # No clear basis
```

**Interpretation**: Based on user's existing knowledge (no forced research required).

### Question 3: Pathway Specificity

**Parameters** (`ke_pathway_assessment.pathway_specificity`):

```yaml
pathway_specificity:
  specific: 2     # Pathway is specific to this KE
  includes: 1     # Pathway includes this KE among others
  loose: 0        # Pathway is only loosely related
```

**Purpose**: Identifies pathways that are too broad and may need refinement.

### Question 4: KE Coverage

**Parameters** (`ke_pathway_assessment.ke_coverage`):

```yaml
ke_coverage:
  complete: 1.5   # Pathway captures complete KE mechanism
  keysteps: 1.0   # Pathway captures key steps only
  minor: 0.5      # Pathway captures minor aspects
```

**Purpose**: Identifies gaps in pathway representation of the KE.

### Biological Level Bonus

**Parameters** (`ke_pathway_assessment.biological_level`):

```yaml
biological_level:
  bonus: 1.0      # Bonus points for molecular/cellular/tissue KEs
  qualifying_levels:
    - molecular
    - cellular
    - tissue
```

**Rationale**: Molecular-level KEs are closer to pathway mechanisms than phenotypic outcomes.

### Confidence Thresholds

**Parameters** (`ke_pathway_assessment.confidence_thresholds`):

```yaml
confidence_thresholds:
  high: 5.0       # Score ≥ 5.0 → High confidence
  medium: 2.5     # Score ≥ 2.5 → Medium confidence
                  # Score < 2.5 → Low confidence
```

**Maximum Score**: 6.5 points (3 + 2 + 1.5 + 1.0 bonus)

**Scoring Formula**:
```
base_score = evidence_quality + pathway_specificity + ke_coverage
final_score = base_score + (biological_level_bonus if applicable)

if final_score ≥ 5.0: confidence = "high"
elif final_score ≥ 2.5: confidence = "medium"
else: confidence = "low"
```

**Examples**:
- Known + Specific + Complete + Molecular: `3 + 2 + 1.5 + 1 = 7.5` → **High** (capped at 6.5)
- Likely + Includes + Key steps + No bonus: `2 + 1 + 1.0 = 4.0` → **Medium**
- Possible + Loose + Minor + No bonus: `1 + 0 + 0.5 = 1.5` → **Low**

---

## Parameter Interactions

### Gene vs Text Scoring Balance

When both gene-based and text-based suggestions exist for the same pathway:
- **Gene-based takes priority** in the combined results
- Gene confidence is typically higher (0.15-0.95 range)
- Text confidence is typically lower (0.08-0.60 range)

**Balancing Strategy**:
- To emphasize genes: Increase `gene_scoring.multiplier` and `gene_scoring.base_boost`
- To balance with text: Increase `text_similarity.important_bio_terms_weight`

### Threshold vs Confidence Relationship

```
dynamic_threshold ← controls → number of suggestions
confidence_scoring ← controls → suggestion quality/ranking
```

- **High threshold + High confidence parameters**: Very few, very confident suggestions
- **Low threshold + High confidence parameters**: Many suggestions, well-ranked
- **High threshold + Low confidence parameters**: Few suggestions, conservative scores
- **Low threshold + Low confidence parameters**: Many suggestions, low scores

### Assessment Score Distribution

The 4-question assessment produces scores roughly distributed as:
- **High (≥5.0)**: ~20-30% of mappings (strong evidence + good specificity)
- **Medium (2.5-5.0)**: ~50-60% of mappings (moderate quality)
- **Low (<2.5)**: ~10-20% of mappings (weak or uncertain)

**Adjusting Distribution**:
- More High ratings: Lower `high` threshold (5.0 → 4.5)
- Fewer Low ratings: Lower `medium` threshold (2.5 → 2.0)
- Stricter overall: Increase both thresholds

---

## Use Cases and Examples

### Use Case 1: Demo/Presentation Mode

**Goal**: Show more suggestions to demonstrate system capabilities.

**Changes**:
```yaml
pathway_suggestion:
  gene_scoring:
    base_boost: 0.20        # Up from 0.15

  dynamic_thresholds:
    base_threshold: 0.18    # Down from 0.25

  confidence_final_bounds:
    minimum: 0.05           # Down from 0.08
```

**Effect**: More pathways appear in suggestions, including borderline matches.

### Use Case 2: Research Mode (Conservative)

**Goal**: Only show high-confidence, well-validated suggestions.

**Changes**:
```yaml
pathway_suggestion:
  gene_scoring:
    base_boost: 0.12        # Down from 0.15

  dynamic_thresholds:
    base_threshold: 0.35    # Up from 0.25

  text_similarity:
    important_bio_terms_weight: 1.5  # Down from 2.0
```

**Effect**: Fewer suggestions, but higher quality and more reliable.

### Use Case 3: Gene-Focused Analysis

**Goal**: Prioritize gene overlap heavily over text matching.

**Changes**:
```yaml
pathway_suggestion:
  gene_scoring:
    multiplier: 0.92        # Up from 0.85
    base_boost: 0.22        # Up from 0.15
    max_confidence: 0.98    # Up from 0.95

  dynamic_thresholds:
    base_threshold: 0.20    # Down from 0.25
```

**Effect**: Gene-based suggestions dominate results, partial overlaps still shown.

### Use Case 4: Lenient Assessment

**Goal**: More mappings qualify as "high confidence".

**Changes**:
```yaml
ke_pathway_assessment:
  confidence_thresholds:
    high: 4.0              # Down from 5.0
    medium: 2.0            # Down from 2.5

  biological_level:
    bonus: 1.2             # Up from 1.0
```

**Effect**: ~40-50% of mappings reach "high" confidence instead of ~20-30%.

### Use Case 5: Strict Curation

**Goal**: High bar for accepting mappings, identify weak ones.

**Changes**:
```yaml
ke_pathway_assessment:
  evidence_quality:
    known: 3.5             # Up from 3
    likely: 2.2            # Up from 2

  confidence_thresholds:
    high: 5.5              # Up from 5.0
    medium: 3.0            # Up from 2.5
```

**Effect**: Fewer "high" ratings, clearer distinction between quality levels.

---

## Troubleshooting

### No Suggestions Appearing

**Possible Causes**:
1. **Threshold too high**: Check `dynamic_thresholds.base_threshold`
2. **No genes found**: KE may lack gene associations in AOP-Wiki
3. **Text similarity too low**: KE title doesn't match pathway terminology

**Solutions**:
```yaml
# Lower threshold temporarily
dynamic_thresholds:
  base_threshold: 0.15    # Try 0.15 instead of 0.25

# Check if gene-based matching is working
# Test with KE 1508 (CYP2E1) - should find 8 pathways
```

### Too Many Suggestions

**Possible Causes**:
1. **Threshold too low**: Many borderline matches appearing
2. **Base boost too high**: Even poor matches get inflated scores

**Solutions**:
```yaml
# Raise threshold
dynamic_thresholds:
  base_threshold: 0.30    # Up from 0.25

# Reduce base boost
gene_scoring:
  base_boost: 0.12        # Down from 0.15
```

### Gene-Based Scores Too Low

**Check**:
1. Is `gene_scoring.multiplier` too low?
2. Is `gene_scoring.base_boost` too low?
3. Are genes being found? (Check browser console/logs)

**Solutions**:
```yaml
gene_scoring:
  multiplier: 0.90        # Up from 0.85
  base_boost: 0.20        # Up from 0.15
```

### Assessment Always Shows "Low" Confidence

**Check**:
1. Are thresholds too high?
2. Is biological level bonus applying?
3. Are users selecting "uncertain" / "loose" / "minor" frequently?

**Solutions**:
```yaml
confidence_thresholds:
  high: 4.5              # Down from 5.0
  medium: 2.0            # Down from 2.5

biological_level:
  bonus: 1.2             # Up from 1.0
```

### Config Changes Not Reflected

**Checklist**:
1. ✅ Saved `scoring_config.yaml`?
2. ✅ Valid YAML syntax? Test with: `python -c "import yaml; yaml.safe_load(open('scoring_config.yaml'))"`
3. ✅ Restarted Flask? `pkill -f "python.*app.py" && python app.py &`
4. ✅ Cleared browser cache? (Ctrl+Shift+R)
5. ✅ Check browser console for "Scoring config loaded" message

**Validation**:
```bash
# Test YAML syntax
python -c "import yaml; print(yaml.safe_load(open('scoring_config.yaml')))"

# Check Flask logs
tail -f /tmp/flask_test.log | grep -i config

# Test API endpoint
curl http://localhost:5000/api/scoring-config | python -m json.tool
```

---

## Advanced Topics

### Custom Biological Terms

To add domain-specific terms to the important terms list, edit:

```yaml
text_similarity:
  important_bio_terms_weight: 2.0
  custom_important_terms:
    - "inflammation"
    - "oxidative"
    - "mitochondrial"
```

**Note**: Requires code modification in `pathway_suggestions.py` to implement.

### Combining Multiple KEs

For analyzing pathways relevant to multiple KEs:
1. Lower `base_threshold` to see broader suggestions
2. Increase `gene_scoring.multiplier` to reward multi-KE gene overlaps
3. Test with pathway search rather than single KE suggestions

### Performance Considerations

**Caching**:
- SPARQL queries cached for 24 hours
- Frontend config cached for 5 minutes
- Changing config requires Flask restart

**Impact of Parameter Changes**:
- Threshold changes: Immediate effect on suggestion count
- Confidence formula changes: Affects ranking/display
- No performance penalty from config complexity

---

## Configuration File Template

See the actual `scoring_config.yaml` file for the complete configuration with inline comments and default values.

---

## Version History

- **v1.0.0** (2026-01-13): Initial configurable scoring system
  - 65+ parameters externalized
  - Gene-based pathway matching fixed
  - Full frontend/backend integration

---

## Support

For issues or questions:
1. Check Flask logs: `tail -f /tmp/flask_test.log`
2. Validate YAML: `python -c "import yaml; yaml.safe_load(open('scoring_config.yaml'))"`
3. Review CLAUDE.md "Scoring Configuration System" section
4. Test with known working KE (e.g., KE 1508 - CYP2E1)

---

**Last Updated**: 2026-01-13
**Configuration Version**: 1.0.0
**Application Version**: v2.3.0
