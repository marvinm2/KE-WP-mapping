"""
Pathway Suggestion Service
Provides intelligent pathway suggestions based on Key Events using AOP-Wiki and WikiPathways RDF data
"""
import hashlib
import json
import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List

import requests
from config_loader import ConfigLoader
from ke_gene_service import get_genes_from_ke
from scoring_utils import combine_scored_items
from text_utils import remove_directionality_terms

logger = logging.getLogger(__name__)

# Pathway name standardization dictionary for common terminology differences
PATHWAY_SYNONYMS = {
    # Wnt signaling variations
    "wnt": ["wnt signaling", "wnt/beta-catenin", "canonical wnt", "wnt pathway", "wnt signalling"],
    "wnt pathway": ["wnt signaling", "wnt/beta-catenin", "canonical wnt", "wnt signalling"],
    "wnt signaling": ["wnt pathway", "wnt/beta-catenin", "canonical wnt", "wnt signalling"],
    
    # PPAR variations
    "ppar": ["ppar signaling", "ppar-alpha", "ppar-gamma", "ppar-delta", "peroxisome proliferator"],
    "ppar alpha": ["ppar-alpha pathway", "ppar signaling", "ppara", "peroxisome proliferator alpha"],
    "ppar-alpha": ["ppar alpha", "ppar signaling", "ppara pathway"],
    
    # NF-kB variations
    "nf-kb": ["nf-kappa b", "nfκb signaling", "nfkb", "nuclear factor kappa b"],
    "nfkb": ["nf-kb", "nf-kappa b", "nfκb signaling", "nuclear factor kappa b"],
    "nuclear factor": ["nf-kb", "nf-kappa b", "nfκb signaling"],
    
    # TGF-beta variations
    "tgf-beta": ["tgf-β", "tgfb signaling", "transforming growth factor", "tgf beta"],
    "tgf beta": ["tgf-beta", "tgf-β", "tgfb signaling", "transforming growth factor"],
    "transforming growth": ["tgf-beta", "tgf-β", "tgfb signaling"],
    
    # p53 variations
    "p53": ["p53 signaling", "tp53", "p53 pathway", "tumor protein 53"],
    "tp53": ["p53", "p53 signaling", "p53 pathway", "tumor protein 53"],
    
    # Apoptosis variations
    "apoptosis": ["programmed cell death", "cell death", "apoptotic"],
    "cell death": ["apoptosis", "programmed cell death", "apoptotic"],
    
    # Cell cycle variations
    "cell cycle": ["cell division", "mitosis", "meiosis", "cell proliferation"],
    "cell division": ["cell cycle", "mitosis", "cell proliferation"],
    
    # Immune response variations
    "immune": ["immunity", "immunological", "inflammatory", "inflammation"],
    "inflammatory": ["immune", "immunity", "inflammation", "inflammatory response"],
    "inflammation": ["immune", "inflammatory", "inflammatory response"],
    
    # Metabolism variations
    "metabolism": ["metabolic", "biosynthesis", "catabolism", "anabolism"],
    "metabolic": ["metabolism", "biosynthesis", "catabolism"],
    "glucose": ["glycolysis", "gluconeogenesis", "glucose metabolism"],
    "fatty acid": ["lipid", "fat metabolism", "lipogenesis", "lipolysis"],
}


class PathwaySuggestionService:
    """Service for generating pathway suggestions based on Key Events"""

    def __init__(self, cache_model=None, config=None, embedding_service=None):
        self.cache_model = cache_model
        self.config = config or ConfigLoader.get_default_config()
        self.embedding_service = embedding_service
        self.aop_wiki_endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"
        self.wikipathways_endpoint = "https://sparql.wikipathways.org/sparql"

    def get_pathway_suggestions(
        self, ke_id: str, ke_title: str, bio_level: str = None, limit: int = 10
    ) -> Dict[str, any]:
        """
        Get comprehensive pathway suggestions for a Key Event

        Args:
            ke_id: Key Event ID (e.g., "Event:123")
            ke_title: Key Event title for text-based matching
            bio_level: Biological level of the KE (Molecular, Cellular, Tissue, etc.)
            limit: Maximum number of suggestions to return

        Returns:
            Dictionary containing gene-based, text-based, and embedding-based suggestions
        """
        try:
            logger.info("Getting pathway suggestions for %s", ke_id)

            # Get gene-based suggestions
            genes = self._get_genes_from_ke(ke_id)
            gene_suggestions = []
            if genes:
                gene_suggestions = self._find_pathways_by_genes(genes, limit)
                logger.info("Found %d gene-based suggestions", len(gene_suggestions))

            # Get text-based suggestions
            text_suggestions = self._fuzzy_search_pathways(ke_title, bio_level, limit)
            logger.info("Found %d text-based suggestions", len(text_suggestions))

            # Get embedding-based suggestions (NEW)
            embedding_suggestions = []
            if self.embedding_service:
                ke_description = ""  # Fetch from AOP-Wiki if available in future
                embedding_suggestions = self._get_embedding_based_suggestions(
                    ke_id, ke_title, ke_description, bio_level, limit
                )
                logger.info("Found %d embedding-based suggestions", len(embedding_suggestions))

            # Combine all three with hybrid scoring
            combined_suggestions = self._combine_multi_signal_suggestions(
                gene_suggestions, text_suggestions, embedding_suggestions, limit
            )

            return {
                "ke_id": ke_id,
                "ke_title": ke_title,
                "genes_found": len(genes),
                "gene_list": genes,
                "gene_based_suggestions": gene_suggestions,
                "text_based_suggestions": text_suggestions,
                "embedding_based_suggestions": embedding_suggestions,
                "combined_suggestions": combined_suggestions,
                "total_suggestions": len(combined_suggestions),
            }

        except Exception as e:
            logger.error("Error getting pathway suggestions for %s: %s", ke_id, e)
            return {
                "error": "Failed to generate pathway suggestions",
                "ke_id": ke_id,
                "ke_title": ke_title,
            }

    def _get_genes_from_ke(self, ke_id: str) -> List[str]:
        """Extract HGNC gene symbols associated with a Key Event"""
        return get_genes_from_ke(ke_id, self.aop_wiki_endpoint, self.cache_model)

    def _find_pathways_by_genes(
        self, genes: List[str], limit: int = 20
    ) -> List[Dict[str, any]]:
        """
        Find WikiPathways containing specific genes

        Args:
            genes: List of HGNC gene symbols
            limit: Maximum number of pathways to return

        Returns:
            List of pathway dictionaries with gene overlap information
        """
        if not genes:
            return []

        try:
            # Create VALUES clause for SPARQL query with URIs (WikiPathways uses identifiers.org URIs)
            gene_values = " ".join([f'<https://identifiers.org/hgnc.symbol/{gene}>' for gene in genes])

            sparql_query = f"""
            PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?pathway ?title ?description ?pathwayID ?geneProduct ?geneSymbol
            WHERE {{
                ?pathway a wp:Pathway ;
                         dc:title ?title ;
                         dcterms:identifier ?pathwayID ;
                         wp:organismName "Homo sapiens" .
                ?geneProduct dcterms:isPartOf ?pathway ;
                             wp:bdbHgncSymbol ?geneSymbol .
                OPTIONAL {{ ?pathway dcterms:description ?description }}
                VALUES ?geneSymbol {{ {gene_values} }}
            }}
            ORDER BY ?pathway
            """

            # Check cache first
            query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
            if self.cache_model:
                cached_response = self.cache_model.get_cached_response(
                    self.wikipathways_endpoint, query_hash
                )
                if cached_response:
                    logger.info("Serving gene-based pathways from cache")
                    return json.loads(cached_response)

            response = requests.post(
                self.wikipathways_endpoint,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                pathway_results = self._process_gene_pathway_results(data, genes)

                # Get total gene counts for all pathways
                pathway_ids = [p["pathwayID"] for p in pathway_results]
                pathway_gene_counts = self._get_pathway_gene_counts(pathway_ids)

                # Add total gene counts and recalculate confidence scores
                for pathway in pathway_results:
                    pathway_id = pathway["pathwayID"]
                    pathway_gene_count = pathway_gene_counts.get(pathway_id, 100)  # Default fallback
                    pathway["pathway_total_genes"] = pathway_gene_count

                    # Calculate pathway specificity
                    pathway["pathway_specificity"] = round(
                        pathway["matching_gene_count"] / pathway_gene_count if pathway_gene_count > 0 else 0.0,
                        3
                    )

                    # Recalculate confidence with refined formula
                    pathway["confidence_score"] = round(
                        self._calculate_gene_confidence(
                            matching_count=pathway["matching_gene_count"],
                            ke_gene_count=len(genes),
                            pathway_gene_count=pathway_gene_count
                        ),
                        3
                    )

                # Sort by confidence score and limit results
                pathway_results.sort(
                    key=lambda x: x["confidence_score"],
                    reverse=True,
                )

                limited_results = pathway_results[:limit]

                # Cache the results
                if self.cache_model:
                    self.cache_model.cache_response(
                        self.wikipathways_endpoint,
                        query_hash,
                        json.dumps(limited_results),
                        24,
                    )

                logger.info("Found %d gene-based pathway suggestions", len(limited_results))
                return limited_results
            else:
                logger.error(
                    "WikiPathways gene query failed: %s - %s", response.status_code, response.text
                )
                return []

        except Exception as e:
            logger.error("Error finding pathways by genes: %s", e)
            return []

    def _get_pathway_gene_counts(self, pathway_ids: List[str]) -> Dict[str, int]:
        """
        Get total gene count for each pathway

        Args:
            pathway_ids: List of WikiPathways IDs

        Returns:
            Dict mapping pathway_id -> total_gene_count
        """
        if not pathway_ids:
            return {}

        try:
            # Build VALUES clause for pathway IDs
            pathway_values = " ".join([f'"{pid}"' for pid in pathway_ids])

            sparql_query = f"""
            PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
            PREFIX dcterms: <http://purl.org/dc/terms/>

            SELECT ?pathwayID (COUNT(DISTINCT ?geneSymbol) as ?geneCount)
            WHERE {{
                ?pathway a wp:Pathway ;
                         dcterms:identifier ?pathwayID ;
                         wp:organismName "Homo sapiens" .
                ?geneProduct dcterms:isPartOf ?pathway ;
                             wp:bdbHgncSymbol ?geneSymbol .
                VALUES ?pathwayID {{ {pathway_values} }}
            }}
            GROUP BY ?pathwayID
            """

            # Check cache first
            query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
            if self.cache_model:
                cached_response = self.cache_model.get_cached_response(
                    self.wikipathways_endpoint, query_hash
                )
                if cached_response:
                    logger.info("Serving pathway gene counts from cache")
                    return json.loads(cached_response)

            response = requests.post(
                self.wikipathways_endpoint,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                gene_counts = {}

                if "results" in data and "bindings" in data["results"]:
                    for binding in data["results"]["bindings"]:
                        pathway_id = binding.get("pathwayID", {}).get("value", "")
                        gene_count = binding.get("geneCount", {}).get("value", "0")

                        if pathway_id:
                            gene_counts[pathway_id] = int(gene_count)

                # Cache the results
                if self.cache_model:
                    self.cache_model.cache_response(
                        self.wikipathways_endpoint,
                        query_hash,
                        json.dumps(gene_counts),
                        24,
                    )

                logger.info("Retrieved gene counts for %d pathways", len(gene_counts))
                return gene_counts
            else:
                logger.error(
                    "WikiPathways gene count query failed: %s - %s", response.status_code, response.text
                )
                return {}

        except Exception as e:
            logger.error("Error getting pathway gene counts: %s", e)
            return {}

    def _calculate_gene_confidence(
        self,
        matching_count: int,
        ke_gene_count: int,
        pathway_gene_count: int
    ) -> float:
        """
        Calculate gene-based confidence with specificity and gene count penalties

        Args:
            matching_count: Number of matching genes
            ke_gene_count: Total KE genes
            pathway_gene_count: Total pathway genes

        Returns:
            Confidence score (0.0-1.0)
        """
        if ke_gene_count == 0 or pathway_gene_count == 0:
            return 0.0

        config = self.config.pathway_suggestion.gene_scoring

        # 1. Overlap ratio (from KE perspective)
        overlap_ratio = matching_count / ke_gene_count

        # 2. Pathway specificity (from pathway perspective)
        specificity = matching_count / pathway_gene_count

        # 3. Scale specificity for meaningful contribution
        specificity_boost = min(1.0, specificity * config.specificity_scaling_factor)

        # 4. Combine overlap and specificity
        base_confidence = (
            overlap_ratio * config.overlap_weight +
            specificity_boost * config.specificity_weight +
            config.base_boost
        )

        # 5. Apply KE gene count penalty
        ke_gene_penalty = (
            1.0 if ke_gene_count >= config.min_genes_for_high_confidence
            else config.low_gene_penalty
        )

        # 6. Final confidence with cap
        confidence = min(config.max_confidence, base_confidence * ke_gene_penalty)

        return confidence

    def _process_gene_pathway_results(
        self, sparql_data: Dict, input_genes: List[str]
    ) -> List[Dict[str, any]]:
        """Process SPARQL results and calculate gene overlap statistics"""
        pathway_map = {}

        if "results" not in sparql_data or "bindings" not in sparql_data["results"]:
            return []

        for binding in sparql_data["results"]["bindings"]:
            pathway_id = binding.get("pathwayID", {}).get("value", "")
            pathway_title = binding.get("title", {}).get("value", "")
            pathway_desc = binding.get("description", {}).get("value", "")
            gene_symbol_uri = binding.get("geneSymbol", {}).get("value", "")

            # Extract gene symbol from URI (e.g., https://identifiers.org/hgnc.symbol/CYP2E1 -> CYP2E1)
            gene_symbol = gene_symbol_uri.split('/')[-1] if gene_symbol_uri else ""

            if not pathway_id or not pathway_title:
                continue

            if pathway_id not in pathway_map:
                pathway_map[pathway_id] = {
                    "pathwayID": pathway_id,
                    "pathwayTitle": pathway_title,
                    "pathwayDescription": pathway_desc,
                    "matching_genes": set(),
                    "suggestion_type": "gene_based",
                }

            if gene_symbol:
                pathway_map[pathway_id]["matching_genes"].add(gene_symbol)

        # Calculate overlap statistics
        results = []
        for pathway_data in pathway_map.values():
            matching_genes = list(pathway_data["matching_genes"])
            matching_count = len(matching_genes)
            overlap_ratio = matching_count / len(input_genes) if input_genes else 0

            results.append(
                {
                    "pathwayID": pathway_data["pathwayID"],
                    "pathwayTitle": pathway_data["pathwayTitle"],
                    "pathwayDescription": pathway_data["pathwayDescription"],
                    "pathwayLink": f"https://www.wikipathways.org/index.php/Pathway:{pathway_data['pathwayID']}",
                    "pathwaySvgUrl": f"https://www.wikipathways.org/wikipathways-assets/pathways/{pathway_data['pathwayID']}/{pathway_data['pathwayID']}.svg",
                    "matching_genes": matching_genes,
                    "matching_gene_count": matching_count,
                    "gene_overlap_ratio": round(overlap_ratio, 3),
                    "suggestion_type": "gene_based",
                    "pathway_total_genes": 0,  # Placeholder, filled in _find_pathways_by_genes
                    "pathway_specificity": 0.0,  # Placeholder, calculated after we have totals
                    "confidence_score": 0.0,  # Placeholder, calculated in _find_pathways_by_genes with refined formula
                    "match_types": ["gene"],  # For UI badge display
                    "primary_evidence": "gene_overlap"  # For UI primary evidence label
                }
            )

        return results

    def _fuzzy_search_pathways(
        self, ke_title: str, bio_level: str = None, limit: int = 20
    ) -> List[Dict[str, any]]:
        """
        Perform fuzzy text-based search for pathways

        Args:
            ke_title: Key Event title to match against
            limit: Maximum number of results

        Returns:
            List of pathway dictionaries with similarity scores
        """
        try:
            # First, get all pathway titles and descriptions
            pathways = self._get_all_pathways_for_search()

            if not pathways:
                return []

            # Calculate text similarity for each pathway
            scored_pathways = []
            # Remove directionality terms from KE title for better matching
            ke_title_no_direction = remove_directionality_terms(ke_title)
            ke_title_clean = self._clean_text(ke_title_no_direction)

            for pathway in pathways:
                title_similarity = self._calculate_text_similarity(
                    ke_title_clean, self._clean_text(pathway["pathwayTitle"]), bio_level
                )
                
                desc_similarity = 0
                if pathway.get("pathwayDescription"):
                    desc_similarity = self._calculate_text_similarity(
                        ke_title_clean, self._clean_text(pathway["pathwayDescription"]), bio_level
                    )

                # Combined similarity score (title weighted higher)
                combined_similarity = (title_similarity * 0.7) + (desc_similarity * 0.3)

                # Dynamic threshold based on biological context
                min_threshold = self._get_dynamic_threshold(ke_title_clean, bio_level)
                if combined_similarity > min_threshold:
                    # Calculate more sophisticated confidence score
                    confidence_score = self._calculate_confidence_score(
                        title_similarity, desc_similarity, combined_similarity, 
                        ke_title_clean, pathway["pathwayTitle"], bio_level
                    )
                    
                    scored_pathways.append(
                        {
                            **pathway,
                            "title_similarity": round(title_similarity, 3),
                            "description_similarity": round(desc_similarity, 3),
                            "combined_similarity": round(combined_similarity, 3),
                            "suggestion_type": "text_based",
                            "confidence_score": round(confidence_score, 3),
                            "pathwaySvgUrl": f"https://www.wikipathways.org/wikipathways-assets/pathways/{pathway['pathwayID']}/{pathway['pathwayID']}.svg",
                            "match_types": ["text"],  # For UI badge display
                            "primary_evidence": "text_similarity"  # For UI primary evidence label
                        }
                    )

            # Sort by similarity and limit results
            scored_pathways.sort(key=lambda x: x["combined_similarity"], reverse=True)
            limited_results = scored_pathways[:limit]

            logger.info("Found %d text-based pathway suggestions", len(limited_results))
            return limited_results

        except Exception as e:
            logger.error("Error in fuzzy pathway search: %s", e)
            return []

    def _get_all_pathways_for_search(self) -> List[Dict[str, str]]:
        """Get all pathways with titles and descriptions for text search"""
        try:
            sparql_query = """
            PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX dcterms: <http://purl.org/dc/terms/>

            SELECT DISTINCT ?pathwayID ?pathwayTitle ?pathwayDescription
            WHERE {
                ?pathwayRev a wp:Pathway ; 
                            dc:title ?pathwayTitle ; 
                            dcterms:identifier ?pathwayID ;
                            wp:organismName "Homo sapiens" .
                OPTIONAL { ?pathwayRev dcterms:description ?pathwayDescription }
            }
            """

            # Check cache first
            query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
            cache_key = f"all_pathways_search"
            
            if self.cache_model:
                cached_response = self.cache_model.get_cached_response(
                    cache_key, query_hash
                )
                if cached_response:
                    logger.info("Serving all pathways from cache for text search")
                    return json.loads(cached_response)

            response = requests.post(
                self.wikipathways_endpoint,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=60,  # Longer timeout for comprehensive query
            )

            if response.status_code == 200:
                data = response.json()
                pathways = []
                seen_pathway_ids = set()

                if "results" in data and "bindings" in data["results"]:
                    for binding in data["results"]["bindings"]:
                        pathway_id = binding.get("pathwayID", {}).get("value", "")
                        pathway_title = binding.get("pathwayTitle", {}).get("value", "")
                        pathway_desc = binding.get("pathwayDescription", {}).get("value", "")

                        # Deduplicate by pathway ID
                        if pathway_id and pathway_title and pathway_id not in seen_pathway_ids:
                            pathways.append(
                                {
                                    "pathwayID": pathway_id,
                                    "pathwayTitle": pathway_title,
                                    "pathwayDescription": pathway_desc,
                                    "pathwayLink": f"https://www.wikipathways.org/index.php/Pathway:{pathway_id}",
                                    "pathwaySvgUrl": f"https://www.wikipathways.org/wikipathways-assets/pathways/{pathway_id}/{pathway_id}.svg",
                                }
                            )
                            seen_pathway_ids.add(pathway_id)

                # Cache the results for longer (6 hours)
                if self.cache_model:
                    self.cache_model.cache_response(
                        cache_key, query_hash, json.dumps(pathways), 6
                    )

                logger.info("Loaded %d pathways for text search", len(pathways))
                return pathways

            else:
                logger.error(
                    "All pathways query failed: %s - %s", response.status_code, response.text
                )
                return []

        except Exception as e:
            logger.error("Error getting all pathways for search: %s", e)
            return []

    def _calculate_text_similarity(self, text1: str, text2: str, bio_level: str = None) -> float:
        """Calculate text similarity using multiple methods with biological level awareness"""
        if not text1 or not text2:
            return 0.0

        # Convert to lowercase for comparison
        text1 = text1.lower()
        text2 = text2.lower()

        # Check for exact pathway matches first (especially important for molecular level)
        exact_match_score = self._check_exact_pathway_match(text1, text2, bio_level)
        if exact_match_score > 0:
            return exact_match_score

        # Sequence matching (character-based similarity)
        seq_similarity = SequenceMatcher(None, text1, text2).ratio()

        # Enhanced word-based Jaccard similarity with weighting
        words1 = set(word.lower() for word in text1.split() if len(word) > 2)  # Filter short words
        words2 = set(word.lower() for word in text2.split() if len(word) > 2)
        
        # Create weighted scoring for different word types
        important_bio_terms = {
            'pathway', 'protein', 'gene', 'enzyme', 'receptor', 'signaling', 'signalling',
            'kinase', 'phosphatase', 'transcription', 'metabolism', 'apoptosis', 'autophagy',
            'inflammation', 'immune', 'oxidative', 'mitochondrial', 'activation', 'inhibition'
        }

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        term_weight = self.config.pathway_suggestion.text_similarity.important_bio_terms_weight

        if union:
            # Standard Jaccard
            basic_jaccard = len(intersection) / len(union)

            # Weighted version - give higher weight to important biological terms
            weighted_intersection = sum(
                term_weight if word in important_bio_terms else 1.0
                for word in intersection
            )
            weighted_union = sum(
                term_weight if word in important_bio_terms else 1.0
                for word in union
            )
            weighted_jaccard = weighted_intersection / weighted_union

            # Combine both approaches for better discrimination
            basic_weight = self.config.pathway_suggestion.text_similarity.high_overlap_weights.get('jaccard', 0.4)
            weighted_weight = self.config.pathway_suggestion.text_similarity.high_overlap_weights.get('sequence', 0.6)
            jaccard_similarity = (basic_jaccard * (1 - weighted_weight) + weighted_jaccard * weighted_weight)
        else:
            jaccard_similarity = 0

        # Enhanced substring matching with variable scores based on context
        substring_score = self._calculate_substring_score(text1, text2)

        # Check for synonym matches
        synonym_boost = self._check_pathway_synonyms(text1, text2)
        
        # Check for domain-specific biological concept matches
        domain_boost = self._check_domain_specific_matches(text1, text2)

        # Enhanced combined scoring with more differentiation
        # Weight different methods based on their effectiveness
        cfg = self.config.pathway_suggestion.text_similarity

        high_overlap = cfg.high_overlap_weights
        if jaccard_similarity > high_overlap.get('threshold', 0.7):
            base_score = (jaccard_similarity * high_overlap.get('jaccard', 0.65) +
                         seq_similarity * high_overlap.get('sequence', 0.25) +
                         substring_score * high_overlap.get('substring', 0.1))
        else:
            medium_overlap = cfg.medium_overlap_weights
            if jaccard_similarity > medium_overlap.get('threshold', 0.4):
                base_score = (jaccard_similarity * medium_overlap.get('jaccard', 0.5) +
                             seq_similarity * medium_overlap.get('sequence', 0.3) +
                             substring_score * medium_overlap.get('substring', 0.2))
            else:
                good_substring = cfg.good_substring_weights
                if substring_score > good_substring.get('threshold', 0.6):
                    base_score = (substring_score * good_substring.get('substring', 0.6) +
                                 jaccard_similarity * good_substring.get('jaccard', 0.25) +
                                 seq_similarity * good_substring.get('sequence', 0.15))
                else:
                    high_sequence = cfg.high_sequence_weights
                    if seq_similarity > high_sequence.get('threshold', 0.7):
                        base_score = (seq_similarity * high_sequence.get('sequence', 0.55) +
                                     jaccard_similarity * high_sequence.get('jaccard', 0.3) +
                                     substring_score * high_sequence.get('substring', 0.15))
                    else:
                        low_quality = cfg.low_quality_weights
                        base_score = (seq_similarity * low_quality.get('sequence', 0.35) +
                                     jaccard_similarity * low_quality.get('jaccard', 0.35) +
                                     substring_score * low_quality.get('substring', 0.3))
                        base_score = base_score * low_quality.get('penalty', 0.85)

        # Apply synonym and domain boosts more selectively with diminishing returns
        total_boost = max(synonym_boost, domain_boost)
        if total_boost > 0:
            threshold = cfg.boost_threshold
            boost_factor = cfg.high_score_boost_factor if base_score > threshold else cfg.low_score_boost_factor
            final_score = min(0.98, base_score * boost_factor + total_boost * cfg.boost_contribution)
        else:
            final_score = base_score
        
        # Apply biological level adjustments
        if bio_level:
            final_score = self._apply_biological_level_adjustment(final_score, text1, text2, bio_level)

        return min(1.0, final_score)

    def _check_exact_pathway_match(self, text1: str, text2: str, bio_level: str = None) -> float:
        """Check for exact pathway name matches, especially important for molecular level KEs"""
        # Only apply exact matching for molecular and cellular levels to avoid over-matching
        if bio_level not in ["Molecular", "Cellular"]:
            return 0.0
            
        # Extract key pathway terms
        key_terms1 = self._extract_pathway_key_terms(text1)
        key_terms2 = self._extract_pathway_key_terms(text2)
        
        # Check for exact matches of key pathway terms (require longer matches for better precision)
        for term1 in key_terms1:
            for term2 in key_terms2:
                if term1 == term2 and len(term1) > 6:  # Require even longer matches for precision
                    # Additional check: ensure it's a meaningful pathway match, not just a common word
                    if term1 in PATHWAY_SYNONYMS or any(term1 in syns for syns in PATHWAY_SYNONYMS.values()):
                        # High score for exact pathway matches
                        if bio_level == "Molecular":
                            return 0.95  # Very high confidence for molecular level exact matches
                        elif bio_level == "Cellular":
                            return 0.85  # High confidence for cellular level
        
        return 0.0

    def _extract_pathway_key_terms(self, text: str) -> List[str]:
        """Extract key pathway terms from text"""
        # Remove common stop words and directionality terms
        stop_words = {
            "pathway", "signaling", "signalling", "regulation", "system", "network",
            "process", "response", "activity", "function", "mechanism", "cascade"
        }
        
        words = text.lower().split()
        key_terms = []
        
        # Extract multi-word pathway names
        for i in range(len(words)):
            # Single important words
            if words[i] not in stop_words and len(words[i]) > 2:
                key_terms.append(words[i])
            
            # Two-word combinations
            if i < len(words) - 1:
                two_word = f"{words[i]} {words[i+1]}"
                if not any(stop in two_word for stop in stop_words):
                    key_terms.append(two_word)
        
        return key_terms

    def _calculate_substring_score(self, text1: str, text2: str) -> float:
        """Calculate sophisticated substring matching score"""
        # Exact substring match
        if text1 in text2 or text2 in text1:
            # Higher score for longer matches relative to text length
            shorter_len = min(len(text1), len(text2))
            longer_len = max(len(text1), len(text2))
            length_ratio = shorter_len / longer_len
            return 0.6 + (length_ratio * 0.3)  # Score between 0.6-0.9
        
        # Check for significant word overlaps with improved scoring
        words1 = text1.split()
        words2 = text2.split()
        
        # Find meaningful common words with length and importance weighting
        common_words = []
        important_biological_terms = {
            'protein', 'gene', 'enzyme', 'receptor', 'kinase', 'phosphatase', 
            'transcription', 'translation', 'metabolism', 'apoptosis', 'autophagy',
            'inflammation', 'immune', 'oxidative', 'mitochondrial', 'cellular',
            'molecular', 'binding', 'activation', 'inhibition', 'degradation'
        }
        
        for word1 in words1:
            if word1 in words2:
                # Weight longer words more heavily
                if len(word1) > 5:  # Longer threshold for more specificity
                    common_words.append((word1, 1.0))
                elif len(word1) > 3 and word1 in important_biological_terms:
                    common_words.append((word1, 0.8))  # Important bio terms get good weight
                elif len(word1) > 3:
                    common_words.append((word1, 0.6))
        
        if common_words:
            # Score based on weighted proportion of significant words
            significant_words1 = [w for w in words1 if len(w) > 3]
            significant_words2 = [w for w in words2 if len(w) > 3]
            total_significant = max(len(significant_words1), len(significant_words2))
            
            if total_significant > 0:
                # Use weighted scoring for better differentiation
                weighted_matches = sum(weight for word, weight in common_words)
                weighted_ratio = weighted_matches / total_significant
                # Apply non-linear scaling for better spread
                return min(0.6, weighted_ratio * 0.7) ** 0.8  # Score up to ~0.55
        
        return 0.0

    def _check_pathway_synonyms(self, text1: str, text2: str) -> float:
        """Check for pathway synonym matches and return boost score"""
        boost = 0.0
        
        for key_term, synonyms in PATHWAY_SYNONYMS.items():
            # Check if key term is in text1 and any synonym is in text2
            if key_term in text1:
                for synonym in synonyms:
                    if synonym in text2:
                        boost = max(boost, 0.3)  # Significant boost for synonym matches
                        break
            
            # Check reverse: key term in text2, synonyms in text1
            if key_term in text2:
                for synonym in synonyms:
                    if synonym in text1:
                        boost = max(boost, 0.3)
                        break
        
        return boost

    def _check_domain_specific_matches(self, text1: str, text2: str) -> float:
        """Check for domain-specific biological concept matches that might be missed by general similarity"""
        boost = 0.0
        
        # Immune system concepts
        immune_concepts = {
            ('t cell', 'immune', 'lymphocyte', 'cd4', 'cd8'): 
                ['immune', 'immunological', 'lymphocyte', 'tcell', 't-cell', 'adaptive immunity'],
            ('inflammation', 'inflammatory'): 
                ['inflammation', 'inflammatory', 'cytokine', 'interleukin', 'nf-kb', 'nfkb'],
            ('macrophage', 'monocyte'): 
                ['macrophage', 'monocyte', 'innate immunity', 'phagocytosis']
        }
        
        # Metabolic concepts
        metabolic_concepts = {
            ('metabolism', 'metabolic', 'fatty acid', 'glucose'): 
                ['metabolism', 'metabolic', 'glycolysis', 'gluconeogenesis', 'lipid', 'fatty acid'],
            ('oxidative stress', 'reactive oxygen', 'ros'): 
                ['oxidative', 'antioxidant', 'reactive oxygen', 'ros', 'glutathione', 'catalase']
        }
        
        # Cell cycle and death concepts  
        cell_concepts = {
            ('apoptosis', 'cell death', 'programmed death'): 
                ['apoptosis', 'programmed cell death', 'caspase', 'p53', 'bcl2'],
            ('proliferation', 'cell division', 'growth'): 
                ['proliferation', 'cell cycle', 'mitosis', 'cyclin', 'growth factor'],
            ('differentiation', 'development'): 
                ['differentiation', 'development', 'stem cell', 'lineage']
        }
        
        # Renal/kidney concepts
        renal_concepts = {
            ('renal', 'kidney', 'tubular', 'nephron'): 
                ['renal', 'kidney', 'nephron', 'glomerular', 'tubular', 'transport', 'filtration']
        }
        
        all_concepts = {**immune_concepts, **metabolic_concepts, **cell_concepts, **renal_concepts}
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        for concept_group, pathway_terms in all_concepts.items():
            # Check if text1 has concept terms and text2 has pathway terms
            concept_match = any(concept in text1_lower for concept in concept_group)
            pathway_match = any(term in text2_lower for term in pathway_terms)
            
            if concept_match and pathway_match:
                boost = max(boost, 0.25)  # Substantial boost for domain matches
                
            # Check reverse
            concept_match_rev = any(concept in text2_lower for concept in concept_group)
            pathway_match_rev = any(term in text1_lower for term in pathway_terms)
            
            if concept_match_rev and pathway_match_rev:
                boost = max(boost, 0.25)
        
        return boost

    def _calculate_confidence_score(self, title_sim: float, desc_sim: float, combined_sim: float,
                                   ke_title: str, pathway_title: str, bio_level: str = None) -> float:
        """Calculate a more sophisticated confidence score based on multiple factors"""

        cfg = self.config.pathway_suggestion.confidence_scoring

        # Enhanced base confidence with non-linear scaling for better differentiation
        tier_high = cfg.tier_high
        if combined_sim > tier_high['threshold']:
            base_confidence = tier_high['base'] + (combined_sim - tier_high['threshold']) * tier_high['multiplier']
        else:
            tier_medium = cfg.tier_medium
            if combined_sim > tier_medium['threshold']:
                base_confidence = tier_medium['base'] + (combined_sim - tier_medium['threshold']) * tier_medium['multiplier']
            else:
                tier_low = cfg.tier_low
                if combined_sim > tier_low['threshold']:
                    base_confidence = tier_low['base'] + (combined_sim - tier_low['threshold']) * tier_low['multiplier']
                else:
                    tier_minimum = cfg.tier_minimum
                    base_confidence = combined_sim * tier_minimum['multiplier']

        # Boost for high title similarity (title matches are more reliable)
        title_boosts = cfg.title_boosts
        if title_sim > title_boosts['very_high']['threshold']:
            base_confidence += title_boosts['very_high']['boost']
        elif title_sim > title_boosts['high']['threshold']:
            base_confidence += title_boosts['high']['boost']
        elif title_sim > title_boosts['medium']['threshold']:
            base_confidence += title_boosts['medium']['boost']

        # Boost for consistent title and description similarity
        consistency = cfg.consistency
        both_scores_high = (title_sim > consistency['min_score'] and desc_sim > consistency['min_score'])
        if abs(title_sim - desc_sim) < consistency['threshold'] and both_scores_high:
            base_confidence += consistency['boost']

        # Penalty for very low title similarity even if description is good
        penalty = cfg.low_title_penalty
        if title_sim < penalty['title_threshold'] and desc_sim > penalty['desc_threshold']:
            base_confidence *= penalty['multiplier']

        # Biological level adjustments
        bio_level_cfg = cfg.biological_level
        if bio_level == "Molecular" and title_sim > bio_level_cfg['molecular_title_threshold']:
            base_confidence += bio_level_cfg['molecular_boost']
        elif bio_level in ["Tissue", "Organ"] and desc_sim > title_sim:
            base_confidence += bio_level_cfg['higher_level_boost']

        # Length and specificity bonus (more granular)
        ke_words = len(ke_title.split())
        pathway_words = len(pathway_title.split())

        # Reward descriptive titles with granular scoring
        length_bonuses = cfg.length_bonuses
        if ke_words >= length_bonuses['very_descriptive']['word_threshold'] and pathway_words >= length_bonuses['very_descriptive']['word_threshold']:
            base_confidence += length_bonuses['very_descriptive']['boost']
        elif ke_words >= length_bonuses['moderately_descriptive']['word_threshold'] and pathway_words >= length_bonuses['moderately_descriptive']['word_threshold']:
            base_confidence += length_bonuses['moderately_descriptive']['boost']
        elif ke_words >= length_bonuses['minimally_descriptive']['word_threshold'] and pathway_words >= length_bonuses['minimally_descriptive']['word_threshold']:
            base_confidence += length_bonuses['minimally_descriptive']['boost']

        # Penalize very short or very long mismatches
        length_diff = abs(ke_words - pathway_words)
        length_penalties = cfg.length_penalties
        if length_diff > length_penalties['very_different']['diff_threshold']:
            base_confidence *= length_penalties['very_different']['multiplier']
        elif length_diff > length_penalties['somewhat_different']['diff_threshold']:
            base_confidence *= length_penalties['somewhat_different']['multiplier']

        # Similarity score fine-tuning for more differentiation
        sim_adj = cfg.similarity_adjustments
        if combined_sim > sim_adj['excellent']['threshold']:
            base_confidence += sim_adj['excellent']['boost']
        elif combined_sim > sim_adj['very_good']['threshold']:
            base_confidence += sim_adj['very_good']['boost']
        elif combined_sim < sim_adj['poor']['threshold']:
            base_confidence *= sim_adj['poor']['multiplier']

        # Add small random component for ties (deterministic based on pathway ID hash)
        pathway_hash = int(hashlib.md5(pathway_title.encode()).hexdigest()[:8], 16)
        random_component = (pathway_hash % 100) / 10000 * cfg.random_component_max
        base_confidence += random_component

        # Ensure confidence stays within reasonable bounds with more precision
        return min(cfg.max_confidence, max(cfg.min_confidence, base_confidence))

    def _apply_biological_level_adjustment(self, base_score: float, text1: str, text2: str, bio_level: str) -> float:
        """Apply biological level-specific adjustments to similarity score"""
        adjusted_score = base_score

        bio_mult = self.config.pathway_suggestion.biological_level_multipliers

        if bio_level == "Molecular":
            # Molecular level: boost exact pathway name matches
            if self._is_pathway_name_match(text1, text2):
                adjusted_score *= bio_mult.molecular['pathway_name_match']
            # Boost gene/protein pathway matches
            elif self._is_gene_protein_pathway_match(text1, text2):
                adjusted_score *= bio_mult.molecular['gene_protein_match']

        elif bio_level == "Cellular":
            # Cellular level: boost process-related matches
            if self._is_cellular_process_match(text1, text2):
                adjusted_score *= bio_mult.cellular['cellular_process_match']
            # Standard boost for good pathway matches
            elif base_score > bio_mult.cellular['good_pathway_threshold']:
                adjusted_score *= bio_mult.cellular['good_pathway_match']

        elif bio_level in ["Tissue", "Organ"]:
            # Tissue/Organ level: boost system-level pathway matches
            if self._is_system_level_match(text1, text2):
                adjusted_score *= bio_mult.tissue_organ['system_level_match']
            # Boost disease-related pathway matches
            elif self._is_disease_pathway_match(text1, text2):
                adjusted_score *= bio_mult.tissue_organ['disease_pathway_match']

        return adjusted_score

    def _get_dynamic_threshold(self, ke_title: str, bio_level: str = None) -> float:
        """Get dynamic similarity threshold based on KE characteristics"""
        cfg = self.config.pathway_suggestion.dynamic_thresholds
        base_threshold = cfg.base_threshold

        high_spec = cfg.high_specificity_terms
        broad_proc = cfg.broad_process_terms

        ke_lower = ke_title.lower()

        if any(term in ke_lower for term in high_spec['terms']):
            return base_threshold + high_spec['adjustment']
        elif any(term in ke_lower for term in broad_proc['terms']):
            return base_threshold + broad_proc['adjustment']

        # Biological level adjustments
        bio_level_adj = cfg.biological_level_adjustments
        if bio_level == "Molecular":
            return base_threshold + bio_level_adj.get('molecular', 0)
        elif bio_level in ["Tissue", "Organ"]:
            tissue_adj = bio_level_adj.get('tissue', 0)
            organ_adj = bio_level_adj.get('organ', 0)
            return base_threshold + max(tissue_adj, organ_adj)

        return base_threshold

    def _is_pathway_name_match(self, text1: str, text2: str) -> bool:
        """Check if texts represent pathway name matches"""
        pathway_indicators = ["pathway", "signaling", "signalling", "cascade", "network"]
        return any(indicator in text1 and indicator in text2 for indicator in pathway_indicators)

    def _is_gene_protein_pathway_match(self, text1: str, text2: str) -> bool:
        """Check if one text mentions a gene/protein and other mentions corresponding pathway"""
        # This is a simplified check - in a full implementation, we'd use a gene/protein database
        gene_protein_patterns = [
            ("ppar", "ppar"), ("wnt", "wnt"), ("nf", "nf"), ("tgf", "tgf"), ("p53", "p53"),
            ("egfr", "egf"), ("vegf", "vegf"), ("jak", "jak"), ("stat", "stat")
        ]
        
        for gene_pattern, pathway_pattern in gene_protein_patterns:
            if gene_pattern in text1.lower() and pathway_pattern in text2.lower():
                return True
            if pathway_pattern in text1.lower() and gene_pattern in text2.lower():
                return True
        return False

    def _is_cellular_process_match(self, text1: str, text2: str) -> bool:
        """Check if texts represent cellular process matches"""
        cellular_processes = [
            "apoptosis", "cell death", "cell cycle", "cell division", "differentiation",
            "proliferation", "migration", "adhesion", "signal transduction"
        ]
        return any(process in text1.lower() and process in text2.lower() for process in cellular_processes)

    def _is_system_level_match(self, text1: str, text2: str) -> bool:
        """Check if texts represent system-level matches"""
        system_terms = [
            "immune system", "nervous system", "cardiovascular", "respiratory",
            "digestive", "endocrine", "metabolic system", "development"
        ]
        return any(term in text1.lower() and term in text2.lower() for term in system_terms)

    def _is_disease_pathway_match(self, text1: str, text2: str) -> bool:
        """Check if texts represent disease pathway matches"""
        disease_terms = [
            "cancer", "tumor", "diabetes", "alzheimer", "parkinson", "heart disease",
            "hypertension", "inflammation", "infection", "autoimmune"
        ]
        return any(term in text1.lower() and term in text2.lower() for term in disease_terms)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison"""
        if not text:
            return ""

        # Remove special characters and normalize whitespace
        cleaned = re.sub(r"[^\w\s]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip().lower()


    def _get_embedding_based_suggestions(
        self,
        ke_id: str,
        ke_title: str,
        ke_description: str,
        bio_level: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get pathway suggestions using BioBERT semantic embeddings

        Now computes separate title and description similarities using the
        embedding service's compute_ke_pathway_similarity() method.

        Args:
            ke_id: Key Event ID
            ke_title: Key Event title (will be cleaned of directionality terms)
            ke_description: Key Event description
            bio_level: Biological level (Molecular, Cellular, etc.)
            limit: Maximum suggestions to return

        Returns:
            List of pathway suggestions with separate embedding scores
        """
        if not self.embedding_service:
            logger.warning("Embedding service not available")
            return []

        try:
            logger.info("Computing embedding-based suggestions for %s", ke_id)

            # IMPORTANT: Strip directionality terms from title before computing embeddings
            ke_title_clean = remove_directionality_terms(ke_title)
            logger.debug(f"Cleaned KE title: '{ke_title}' -> '{ke_title_clean}'")

            # Get all pathways
            all_pathways = self._get_all_pathways_for_search()

            # Use batch processing for efficiency (computes all embeddings in vectorized manner)
            batch_results = self.embedding_service.compute_ke_pathways_batch_similarity(
                ke_id=ke_id,
                ke_title=ke_title_clean,  # Use cleaned title
                ke_description=ke_description,
                pathways=all_pathways
            )

            # Apply minimum threshold and format suggestions
            embedding_config = getattr(
                self.config.pathway_suggestion,
                'embedding_based_matching',
                None
            )
            min_threshold = getattr(embedding_config, 'min_threshold', 0.3) if embedding_config else 0.3

            suggestions = []
            for result in batch_results:
                confidence = result['combined_similarity']

                if confidence >= min_threshold:
                    suggestion = {
                        'pathwayID': result['pathwayID'],
                        'pathwayTitle': result['pathwayTitle'],
                        'pathwayDescription': result.get('pathwayDescription', ''),
                        'pathwayLink': result.get('pathwayLink', ''),
                        'pathwaySvgUrl': result.get('pathwaySvgUrl', ''),
                        'confidence_score': confidence,
                        'embedding_similarity': result['combined_similarity'],
                        'title_similarity': result['title_similarity'],
                        'description_similarity': result['description_similarity'],
                        'suggestion_type': 'embedding_based',
                        'match_types': ['embedding'],  # For UI badge display
                        'primary_evidence': 'semantic_similarity'  # For UI primary evidence label
                    }
                    suggestions.append(suggestion)

            # Sort by confidence descending
            suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)

            logger.info("Found %d embedding-based suggestions", len(suggestions))

            return suggestions[:limit]

        except Exception as e:
            logger.error("Embedding-based suggestion failed: %s", e)
            return []

    def _combine_multi_signal_suggestions(
        self,
        gene_suggestions: List[Dict],
        text_suggestions: List[Dict],
        embedding_suggestions: List[Dict],
        limit: int
    ) -> List[Dict]:
        """
        Combine three scoring signals with transparent hybrid scoring

        Returns:
            List of suggestions with all scores visible
        """
        # Get weights from config
        hybrid_weights = getattr(
            self.config.pathway_suggestion,
            'hybrid_weights',
            None
        )

        gene_weight = getattr(hybrid_weights, 'gene', 0.35) if hybrid_weights else 0.35
        text_weight = getattr(hybrid_weights, 'text', 0.35) if hybrid_weights else 0.35
        embedding_weight = getattr(hybrid_weights, 'embedding', 0.30) if hybrid_weights else 0.30

        final_threshold = self.config.pathway_suggestion.dynamic_thresholds.base_threshold

        combined = combine_scored_items(
            scored_lists={
                'gene': gene_suggestions,
                'text': text_suggestions,
                'embedding': embedding_suggestions,
            },
            id_field='pathwayID',
            weights={'gene': gene_weight, 'text': text_weight, 'embedding': embedding_weight},
            score_field_map={
                'gene': 'confidence_score',
                'text': 'confidence_score',
                'embedding': 'confidence_score',
            },
            multi_evidence_bonus=0.05,
            min_threshold=final_threshold,
            max_score=0.98,
        )

        # WP-specific post-processing: build scores dict, primary_evidence, embedding_details
        for pathway in combined:
            sig = pathway.pop('signal_scores', {})
            gene_score = sig.get('gene', 0.0)
            text_score = sig.get('text', 0.0)
            emb_score = sig.get('embedding', 0.0)

            pathway['scores'] = {
                'gene_confidence': gene_score,
                'text_confidence': text_score,
                'embedding_similarity': emb_score,
                'final_score': pathway['hybrid_score'],
            }

            # Determine primary evidence source
            max_signal = max(gene_score, text_score, emb_score)
            if max_signal == gene_score and gene_score > 0:
                pathway['primary_evidence'] = 'gene_overlap'
            elif max_signal == emb_score and emb_score > 0:
                pathway['primary_evidence'] = 'semantic_similarity'
            else:
                pathway['primary_evidence'] = 'text_similarity'

            # Add embedding_details from per-signal data (avoids field collision
            # where text signal's title_similarity overwrites embedding's)
            if 'embedding' in pathway.get('match_types', []):
                emb_data = pathway.get('_signal_data', {}).get('embedding', {})
                pathway['embedding_details'] = {
                    'title_similarity': emb_data.get('title_similarity', 0),
                    'description_similarity': emb_data.get('description_similarity', 0),
                    'combined': emb_data.get('embedding_similarity', 0)
                }

            # Clean up internal per-signal data
            pathway.pop('_signal_data', None)

        return combined[:limit]

    def _combine_and_rank_suggestions(
        self,
        gene_suggestions: List[Dict],
        text_suggestions: List[Dict],
        limit: int,
    ) -> List[Dict]:
        """Combine gene-based and text-based suggestions with hybrid ranking (Legacy method)"""
        all_suggestions = []
        seen_pathways = set()

        # Add gene-based suggestions (higher priority)
        for suggestion in gene_suggestions:
            pathway_id = suggestion["pathwayID"]
            if pathway_id not in seen_pathways:
                suggestion["final_score"] = suggestion["confidence_score"]
                all_suggestions.append(suggestion)
                seen_pathways.add(pathway_id)

        # Add text-based suggestions that aren't already included
        for suggestion in text_suggestions:
            pathway_id = suggestion["pathwayID"]
            if pathway_id not in seen_pathways:
                suggestion["final_score"] = suggestion["confidence_score"]
                all_suggestions.append(suggestion)
                seen_pathways.add(pathway_id)

        # Sort by final score and limit results
        all_suggestions.sort(key=lambda x: x["final_score"], reverse=True)
        return all_suggestions[:limit]

    def search_pathways(
        self, query: str, threshold: float = 0.4, limit: int = 20
    ) -> List[Dict[str, any]]:
        """
        Enhanced search functionality with fuzzy matching

        Args:
            query: Search query string
            threshold: Minimum similarity threshold (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of matching pathways with relevance scores
        """
        try:
            pathways = self._get_all_pathways_for_search()
            # Remove directionality terms from query for better matching
            query_no_direction = remove_directionality_terms(query)
            query_clean = self._clean_text(query_no_direction)

            if not query_clean:
                return []

            results = []
            for pathway in pathways:
                title_similarity = self._calculate_text_similarity(
                    query_clean, self._clean_text(pathway["pathwayTitle"])
                )
                
                desc_similarity = 0
                if pathway.get("pathwayDescription"):
                    desc_similarity = self._calculate_text_similarity(
                        query_clean, self._clean_text(pathway["pathwayDescription"])
                    )

                max_similarity = max(title_similarity, desc_similarity)
                
                if max_similarity >= threshold:
                    results.append(
                        {
                            **pathway,
                            "title_similarity": round(title_similarity, 3),
                            "description_similarity": round(desc_similarity, 3),
                            "relevance_score": round(max_similarity, 3),
                            "pathwaySvgUrl": f"https://www.wikipathways.org/wikipathways-assets/pathways/{pathway['pathwayID']}/{pathway['pathwayID']}.svg",
                        }
                    )

            # Sort by relevance and limit results
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error("Error in pathway search: %s", e)
            return []