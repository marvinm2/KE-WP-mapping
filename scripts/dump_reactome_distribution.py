"""
Reactome suggestion calibration script — Phase 30 threshold tuning.

One-shot script that runs ReactomeSuggestionService against 5 calibration KEs
with relaxed thresholds (all gates set to 0.0, max_results=100) to capture
the full similarity distribution. Use the output to pick embedding_min_threshold
from the observed elbow.

Usage:
    python scripts/dump_reactome_distribution.py | tee \
      .planning/phases/30-reactome-suggestion-card-parity-and-threshold-tuning/calibration-distributions.txt

Run from the project root.
"""
from __future__ import annotations

import json
import os
import sys

# Ensure project root is on path so src.* imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.config_loader import ConfigLoader
from src.services.embedding import BiologicalEmbeddingService
from src.suggestions.reactome import ReactomeSuggestionService

# ---------------------------------------------------------------------------
# Calibration KE list
# ---------------------------------------------------------------------------
# KE 55 — Cellular biolevel (carry-over from Phase 26 hybrid-scoring run;
#          soft upper-bound reference, top hybrid ~0.59)
# KE 1003 — Tissue biolevel  (Decreased, Triiodothyronine T3)
# KE 1395 — Organ biolevel   (Liver Cancer)
# KE 129  — Organ biolevel   (Reduction, Gonadotropins, circulating concentrations)
# KE 1193 — Individual biolevel (N/A, Breast Cancer)
#
# KE IDs are in the "KE NNN" format used by AOP-Wiki label field.
# Bio levels span: Cellular / Tissue / Organ / Individual.
# ---------------------------------------------------------------------------
CALIBRATION_KES = [
    {"ke_id": "KE 55",   "biolevel": "Cellular"},
    {"ke_id": "KE 1003", "biolevel": "Tissue"},
    {"ke_id": "KE 1395", "biolevel": "Organ"},
    {"ke_id": "KE 129",  "biolevel": "Organ"},
    {"ke_id": "KE 1193", "biolevel": "Individual"},
]

# Candidate elbow thresholds to summarise.
# NOTE: The score transformation (power_exponent=4.0, scale_factor=0.75,
# output_max=0.95) applied by BiologicalEmbeddingService compresses cosine
# similarity into a narrower high range.  Observed distribution (Phase 30
# calibration run) clusters between 0.45–0.85, so elbow candidates are
# shifted accordingly.  Expected landing zone: 0.80–0.84.
CANDIDATE_THRESHOLDS = [0.85, 0.84, 0.83, 0.82, 0.80, 0.78, 0.76]


def load_ke_metadata() -> dict:
    """Load ke_metadata.json and build a {ke_label -> metadata_dict} index."""
    path = os.path.join(PROJECT_ROOT, "data", "ke_metadata.json")
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    index = {}
    for rec in records:
        label = rec.get("KElabel", "").strip()
        if label:
            index[label] = rec
    return index


def build_embedding_service(config) -> BiologicalEmbeddingService | None:
    """Instantiate BiologicalEmbeddingService using YAML config values."""
    embedding_cfg = getattr(
        config.pathway_suggestion, "embedding_based_matching", None
    )
    if embedding_cfg is None or not getattr(embedding_cfg, "enabled", False):
        print("[WARN] embedding_based_matching.enabled=false in YAML — "
              "Reactome suggestions will be empty.", file=sys.stderr)
        return None

    score_transform = getattr(embedding_cfg, "score_transformation", None)
    score_transform_config = None
    if score_transform:
        score_transform_config = {
            "method": getattr(score_transform, "method", "power"),
            "power_exponent": getattr(score_transform, "power_exponent", 2.5),
            "scale_factor": getattr(score_transform, "scale_factor", 0.75),
            "output_min": getattr(score_transform, "output_min", 0.0),
            "output_max": getattr(score_transform, "output_max", 0.95),
            "skip_precomputed_for_titles": getattr(
                embedding_cfg, "skip_precomputed_for_titles", True
            ),
        }

    entity_extract = getattr(embedding_cfg, "entity_extraction", None)
    entity_extract_config = None
    if entity_extract:
        entity_extract_config = {
            "enabled": getattr(entity_extract, "enabled", True),
            "min_entity_length": getattr(entity_extract, "min_entity_length", 3),
            "include_numbers": getattr(entity_extract, "include_numbers", True),
            "biological_terms_only": getattr(
                entity_extract, "biological_terms_only", False
            ),
        }

    precomputed_path = getattr(
        embedding_cfg, "precomputed_embeddings", "data/pathway_embeddings.npz"
    )
    precomputed_ke_path = getattr(
        embedding_cfg, "precomputed_ke_embeddings", "data/ke_embeddings.npz"
    )

    return BiologicalEmbeddingService(
        model_name=getattr(
            embedding_cfg, "model", "dmis-lab/biobert-base-cased-v1.2"
        ),
        use_gpu=False,  # CPU is fine for a one-shot calibration run
        precomputed_embeddings_path=precomputed_path,
        precomputed_ke_embeddings_path=precomputed_ke_path,
        score_transform_config=score_transform_config,
        title_weight=getattr(embedding_cfg, "title_weight", 0.85),
        entity_extract_config=entity_extract_config,
    )


def relaxed_config(config):
    """Return config with Reactome thresholds zeroed out and max_results uncapped.

    max_results is set high so the full distribution is visible; the per-KE
    sorted list is still printed in full.  The production cap (10) is applied
    separately during threshold selection.
    """
    r = config.reactome_suggestion
    r.embedding_min_threshold = 0.0
    r.min_threshold = 0.0
    r.gene_min_threshold = 0.0
    r.max_results = 10000  # uncapped for calibration
    return config


def main() -> None:
    print("=" * 72)
    print("Reactome Calibration Distribution Dump — Phase 30")
    print("=" * 72)
    print()

    # --- Load real config, then relax for full distribution visibility -----
    config = ConfigLoader.load_config()
    config = relaxed_config(config)

    # --- Load KE metadata -------------------------------------------------
    ke_meta = load_ke_metadata()

    # --- Print chosen calibration KEs -------------------------------------
    print("Calibration KE set:")
    print("-" * 60)
    for entry in CALIBRATION_KES:
        ke_id = entry["ke_id"]
        biolevel = entry["biolevel"]
        meta = ke_meta.get(ke_id, {})
        title = meta.get("KEtitle", "(title not found)")
        print(f"  {ke_id:<10}  [{biolevel:<12}]  {title[:55]}")
    print()

    # --- Build embedding service -------------------------------------------
    print("Initialising BiologicalEmbeddingService ...", flush=True)
    embedding_service = build_embedding_service(config)
    if embedding_service is None:
        sys.exit(1)
    print("Embedding service ready.")
    print()

    # --- Build ReactomeSuggestionService (with relaxed config) ------------
    svc = ReactomeSuggestionService(
        cache_model=None,
        config=config,
        embedding_service=embedding_service,
        ke_override_model=None,
    )

    # --- Per-KE distribution dump -----------------------------------------
    all_results: dict[str, list] = {}

    for entry in CALIBRATION_KES:
        ke_id = entry["ke_id"]
        biolevel = entry["biolevel"]
        meta = ke_meta.get(ke_id, {})
        ke_title = meta.get("KEtitle", "")
        ke_description = meta.get("KEdescription", "")

        print("=" * 72)
        print(f"KE: {ke_id}  [{biolevel}]  {ke_title[:60]}")
        print("=" * 72)

        result = svc.get_reactome_suggestions(
            ke_id=ke_id,
            ke_title=ke_title,
            limit=10000,  # uncapped for full distribution visibility
            method_filter="text",  # embedding-only (v1.5 pure-semantic)
        )

        suggestions = result.get("suggestions", [])
        # get_reactome_suggestions sorts by hybrid_score desc; for text-only
        # method_filter the list is embedding_scores sorted in-service.
        # Sort explicitly for safety.
        suggestions.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)

        genes_found = result.get("genes_found", 0)
        print(f"Genes fetched from AOP-Wiki: {genes_found}")
        print(f"Total pathways above threshold (0.0): {len(suggestions)}")
        print()

        if not suggestions:
            print("  (no suggestions returned — check embeddings / data files)")
            print()
            continue

        # Print sorted distribution
        print(f"  {'Score':>6}  {'Reactome ID':<14}  Pathway name")
        print(f"  {'-'*6}  {'-'*14}  {'-'*40}")
        for s in suggestions:
            score = s.get("hybrid_score", s.get("suggestion_score", 0.0))
            rid = s.get("reactome_id", "")
            name = s.get("pathway_name", "")[:50]
            print(f"  {score:>6.4f}  {rid:<14}  {name}")

        print()

        # Summary brackets
        scores = [s.get("hybrid_score", 0.0) for s in suggestions]
        print("  Summary brackets:")
        for thr in CANDIDATE_THRESHOLDS:
            count = sum(1 for sc in scores if sc >= thr)
            print(f"    >= {thr:.2f}: {count:>4} suggestions")
        print()

        all_results[ke_id] = scores

    # --- Threshold decision -----------------------------------------------
    print("=" * 72)
    print("Threshold decision")
    print("=" * 72)
    print()
    print("Candidate thresholds — per-KE suggestion counts:")
    print()
    header = f"  {'Threshold':>10}  " + "  ".join(f"{e['ke_id']:>8}" for e in CALIBRATION_KES)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for thr in CANDIDATE_THRESHOLDS:
        row = f"  {thr:>10.2f}  "
        for entry in CALIBRATION_KES:
            ke_id = entry["ke_id"]
            scores = all_results.get(ke_id, [])
            count = sum(1 for sc in scores if sc >= thr)
            row += f"  {count:>8}"
        print(row)
    print()

    # Decision rule (see PLAN.md Task 1):
    # Pick the largest threshold in CANDIDATE_THRESHOLDS such that:
    #   - narrow KEs (few genes / specific molecular) yield <= 5 suggestions
    #   - broad KEs (organ/individual level) yield >= 3 suggestions before the cap
    #   - max_results=10 is the binding constraint for broad KEs
    #
    # Note: the score transformation (power_exponent=4.0, scale_factor=0.75)
    # compresses cosine similarity into a high range (0.45–0.85).  The
    # effective threshold must therefore be much higher than the 0.30–0.50
    # range described in the plan's CONTEXT (which assumed a linear scale).
    # Expected landing zone after calibration: 0.80–0.84.
    #
    # Bio-level heuristic:
    #   KE 55  (Cellular)  — medium breadth; benchmark
    #   KE 1003 (Tissue)   — narrow (specific hormone measurement)
    #   KE 1395 (Organ)    — potentially narrow despite organ-level bio
    #   KE 129  (Organ)    — broad (broad hormonal axis)
    #   KE 1193 (Individual)— broad/disease-level
    #
    # Apply rule programmatically: prefer the threshold where the narrowest KE
    # (KE 1003, Tissue) stays <= 5 and at least one broad KE yields >= 3.
    chosen_threshold = None
    chosen_rationale = ""
    narrow_kes = ["KE 55", "KE 1003"]  # cellular / tissue — specific events
    broad_kes = ["KE 1395", "KE 129", "KE 1193"]  # organ / individual

    for thr in CANDIDATE_THRESHOLDS:
        narrow_counts = {
            ke: sum(1 for sc in all_results.get(ke, []) if sc >= thr)
            for ke in narrow_kes
        }
        broad_counts = {
            ke: sum(1 for sc in all_results.get(ke, []) if sc >= thr)
            for ke in broad_kes
        }
        narrow_max = max(narrow_counts.values()) if narrow_counts else 0
        broad_max = max(broad_counts.values()) if broad_counts else 0

        # Require:
        #   - narrow KEs: max count <= 5 (not noisy)
        #   - broad KEs:  at least one KE yields >= 5 suggestions, so max_results=10
        #                 is the binding constraint (not the floor)
        #   This distinguishes the 0.83 elbow (KE 129 gives 20 -> capped to 10)
        #   from 0.85 (KE 129 gives 4 -> floor prevents curated-10 experience).
        if narrow_max <= 5 and broad_max >= 5:
            chosen_threshold = thr
            boundary_kes = [
                ke for ke in broad_kes
                if broad_counts[ke] <= 10
            ]
            chosen_rationale = (
                f"narrow KEs {narrow_kes} yield {list(narrow_counts.values())} suggestions; "
                f"broad KEs {broad_kes} yield {list(broad_counts.values())} — "
                f"boundary KEs at production cap (10): {boundary_kes}"
            )
            break

    if chosen_threshold is None:
        # Fallback: pick 0.83 as the empirically observed elbow from Phase 30
        chosen_threshold = 0.83
        chosen_rationale = (
            "No threshold met all criteria cleanly — defaulting to 0.83 "
            "(empirically observed elbow from Phase 30 calibration run)"
        )

    print(f"Chosen embedding_min_threshold: {chosen_threshold:.2f}")
    print(f"Rationale: {chosen_rationale}")
    print()
    print("Apply this value to scoring_config.yaml::reactome_suggestion:")
    print(f"  embedding_min_threshold: {chosen_threshold:.2f}")
    print(f"  min_threshold: {chosen_threshold:.2f}  # coupled to embedding_min_threshold")
    print(f"  max_results: 10  # capped for curated top-N")
    print(f"  gene_min_threshold: 0.0  # display-only chip (v1.5)")
    print()
    print("NOTE: These thresholds are calibrated for the post-transformation score range")
    print("  (power_exponent=4.0, scale_factor=0.75, output_max=0.95).")
    print("  If the score transformation config changes, re-run this script.")
    print()
    print("See Task 2 of 30-01-PLAN.md for the exact edit instructions.")


if __name__ == "__main__":
    main()
