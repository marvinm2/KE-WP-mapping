"""
Pathway Suggestion Service
Provides intelligent pathway suggestions based on Key Events using AOP-Wiki and WikiPathways RDF data
"""
import hashlib
import json
import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import requests

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

    def __init__(self, cache_model=None):
        self.cache_model = cache_model
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
            Dictionary containing gene-based and text-based suggestions
        """
        try:
            # Get gene-based suggestions
            genes = self._get_genes_from_ke(ke_id)
            gene_suggestions = []
            if genes:
                gene_suggestions = self._find_pathways_by_genes(genes, limit)

            # Get text-based suggestions
            text_suggestions = self._fuzzy_search_pathways(ke_title, bio_level, limit)

            # Combine and rank all suggestions
            combined_suggestions = self._combine_and_rank_suggestions(
                gene_suggestions, text_suggestions, limit
            )

            return {
                "ke_id": ke_id,
                "ke_title": ke_title,
                "genes_found": len(genes),
                "gene_list": genes,
                "gene_based_suggestions": gene_suggestions,
                "text_based_suggestions": text_suggestions,
                "combined_suggestions": combined_suggestions,
                "total_suggestions": len(combined_suggestions),
            }

        except Exception as e:
            logger.error(f"Error getting pathway suggestions for {ke_id}: {str(e)}")
            return {
                "error": "Failed to generate pathway suggestions",
                "ke_id": ke_id,
                "ke_title": ke_title,
            }

    def _get_genes_from_ke(self, ke_id: str) -> List[str]:
        """
        Extract HGNC gene symbols associated with a Key Event using corrected AOP-Wiki query

        Args:
            ke_id: Key Event ID

        Returns:
            List of HGNC gene symbols
        """
        try:
            sparql_query = f"""
            PREFIX aopo: <http://aopkb.org/aop_ontology#>
            PREFIX edam: <http://edamontology.org/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?keid ?ketitle ?hgnc
            WHERE {{
                ?ke a aopo:KeyEvent; 
                    edam:data_1025 ?object; 
                    dc:title ?ketitle; 
                    rdfs:label ?keid.
                ?object edam:data_2298 ?hgnc.
                FILTER(?keid = "{ke_id}")
            }}
            """

            # Check cache first
            query_hash = hashlib.md5(sparql_query.encode()).hexdigest()
            if self.cache_model:
                cached_response = self.cache_model.get_cached_response(
                    self.aop_wiki_endpoint, query_hash
                )
                if cached_response:
                    logger.info(f"Serving KE genes from cache for {ke_id}")
                    return json.loads(cached_response)

            response = requests.post(
                self.aop_wiki_endpoint,
                data={"query": sparql_query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                genes = []
                
                if "results" in data and "bindings" in data["results"]:
                    for binding in data["results"]["bindings"]:
                        if "hgnc" in binding:
                            gene = binding["hgnc"]["value"]
                            if gene and gene not in genes:
                                genes.append(gene)

                # Cache the results
                if self.cache_model:
                    self.cache_model.cache_response(
                        self.aop_wiki_endpoint, query_hash, json.dumps(genes), 24
                    )

                logger.info(f"Found {len(genes)} genes for KE {ke_id}: {genes}")
                return genes
            else:
                logger.error(
                    f"AOP-Wiki gene query failed: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Error extracting genes from KE {ke_id}: {str(e)}")
            return []

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
            # Create VALUES clause for SPARQL query
            gene_values = " ".join([f'"{gene}"' for gene in genes])

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

                # Sort by gene overlap ratio and limit results
                pathway_results.sort(
                    key=lambda x: (x["gene_overlap_ratio"], x["matching_gene_count"]),
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

                logger.info(f"Found {len(limited_results)} gene-based pathway suggestions")
                return limited_results
            else:
                logger.error(
                    f"WikiPathways gene query failed: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Error finding pathways by genes: {str(e)}")
            return []

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
            gene_symbol = binding.get("geneSymbol", {}).get("value", "")

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
                    "confidence_score": round(min(0.95, overlap_ratio * 0.85 + 0.15), 3),  # Enhanced gene-based scoring
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
            ke_title_no_direction = self._remove_directionality_terms(ke_title)
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
                        }
                    )

            # Sort by similarity and limit results
            scored_pathways.sort(key=lambda x: x["combined_similarity"], reverse=True)
            limited_results = scored_pathways[:limit]

            logger.info(f"Found {len(limited_results)} text-based pathway suggestions")
            return limited_results

        except Exception as e:
            logger.error(f"Error in fuzzy pathway search: {str(e)}")
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

                logger.info(f"Loaded {len(pathways)} pathways for text search")
                return pathways

            else:
                logger.error(
                    f"All pathways query failed: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Error getting all pathways for search: {str(e)}")
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
        
        if union:
            # Standard Jaccard
            basic_jaccard = len(intersection) / len(union)
            
            # Weighted version - give higher weight to important biological terms
            weighted_intersection = sum(
                2.0 if word in important_bio_terms else 1.0 
                for word in intersection
            )
            weighted_union = sum(
                2.0 if word in important_bio_terms else 1.0 
                for word in union
            )
            weighted_jaccard = weighted_intersection / weighted_union
            
            # Combine both approaches for better discrimination
            jaccard_similarity = (basic_jaccard * 0.4 + weighted_jaccard * 0.6)
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
        if jaccard_similarity > 0.7:  # Very high word overlap (raised threshold)
            base_score = jaccard_similarity * 0.65 + seq_similarity * 0.25 + substring_score * 0.1
        elif jaccard_similarity > 0.4:  # Medium word overlap  
            base_score = jaccard_similarity * 0.5 + seq_similarity * 0.3 + substring_score * 0.2
        elif substring_score > 0.6:  # Good substring match (raised threshold)
            base_score = substring_score * 0.6 + jaccard_similarity * 0.25 + seq_similarity * 0.15
        elif seq_similarity > 0.7:  # High character-level similarity
            base_score = seq_similarity * 0.55 + jaccard_similarity * 0.3 + substring_score * 0.15
        else:  # Lower quality matches get penalized more
            base_score = seq_similarity * 0.35 + jaccard_similarity * 0.35 + substring_score * 0.3
            # Apply penalty for weak matches to create more spread
            base_score = base_score * 0.85
        
        # Apply synonym and domain boosts more selectively with diminishing returns
        total_boost = max(synonym_boost, domain_boost)  # Take the better boost
        if total_boost > 0:
            # Smaller boost for already high scores to avoid ceiling effects
            boost_factor = 1.15 if base_score > 0.6 else 1.25
            final_score = min(0.98, base_score * boost_factor + total_boost * 0.2)
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
        
        # Enhanced base confidence with non-linear scaling for better differentiation
        if combined_sim > 0.8:
            base_confidence = 0.48 + (combined_sim - 0.8) * 0.6  # 0.48-0.6 range for top scores
        elif combined_sim > 0.6:
            base_confidence = 0.36 + (combined_sim - 0.6) * 0.6  # 0.36-0.48 range  
        elif combined_sim > 0.4:
            base_confidence = 0.24 + (combined_sim - 0.4) * 0.6  # 0.24-0.36 range
        else:
            base_confidence = combined_sim * 0.6  # Linear for low scores
        
        # Boost for high title similarity (title matches are more reliable)
        if title_sim > 0.8:
            base_confidence += 0.15
        elif title_sim > 0.6:
            base_confidence += 0.1
        elif title_sim > 0.4:
            base_confidence += 0.05
        
        # Boost for consistent title and description similarity
        both_scores_high = (title_sim > 0.5 and desc_sim > 0.5)
        if abs(title_sim - desc_sim) < 0.1 and both_scores_high:
            base_confidence += 0.1  # Consistent high scores across both
        
        # Penalty for very low title similarity even if description is good
        if title_sim < 0.2 and desc_sim > 0.5:
            base_confidence *= 0.8  # Reduce confidence when only description matches
        
        # Biological level adjustments
        if bio_level == "Molecular" and title_sim > 0.7:
            base_confidence += 0.1  # Molecular level title matches are very reliable
        elif bio_level in ["Tissue", "Organ"] and desc_sim > title_sim:
            base_confidence += 0.05  # Higher level matches often rely more on descriptions
        
        # Length and specificity bonus (more granular)
        ke_words = len(ke_title.split())
        pathway_words = len(pathway_title.split())
        
        # Reward descriptive titles with granular scoring
        if ke_words >= 5 and pathway_words >= 5:  # Very descriptive
            base_confidence += 0.08
        elif ke_words >= 3 and pathway_words >= 3:  # Moderately descriptive  
            base_confidence += 0.05
        elif ke_words >= 2 and pathway_words >= 2:  # Minimally descriptive
            base_confidence += 0.02
            
        # Penalize very short or very long mismatches
        length_diff = abs(ke_words - pathway_words)
        if length_diff > 4:  # Very different lengths
            base_confidence *= 0.95
        elif length_diff > 2:  # Somewhat different lengths
            base_confidence *= 0.98
            
        # Similarity score fine-tuning for more differentiation
        if combined_sim > 0.9:  # Excellent match
            base_confidence += 0.05
        elif combined_sim > 0.8:  # Very good match
            base_confidence += 0.03
        elif combined_sim < 0.4:  # Poor match
            base_confidence *= 0.9
            
        # Add small random component for ties (deterministic based on pathway ID hash)
        import hashlib
        pathway_hash = int(hashlib.md5(pathway_title.encode()).hexdigest()[:8], 16)
        random_component = (pathway_hash % 100) * 0.0001  # 0-0.01 range
        base_confidence += random_component
        
        # Ensure confidence stays within reasonable bounds with more precision
        return min(0.98, max(0.08, base_confidence))

    def _apply_biological_level_adjustment(self, base_score: float, text1: str, text2: str, bio_level: str) -> float:
        """Apply biological level-specific adjustments to similarity score"""
        adjusted_score = base_score
        
        if bio_level == "Molecular":
            # Molecular level: boost exact pathway name matches
            if self._is_pathway_name_match(text1, text2):
                adjusted_score *= 1.3
            # Boost gene/protein pathway matches
            elif self._is_gene_protein_pathway_match(text1, text2):
                adjusted_score *= 1.2
                
        elif bio_level == "Cellular":
            # Cellular level: boost process-related matches
            if self._is_cellular_process_match(text1, text2):
                adjusted_score *= 1.2
            # Standard boost for good pathway matches
            elif base_score > 0.5:
                adjusted_score *= 1.1
                
        elif bio_level in ["Tissue", "Organ"]:
            # Tissue/Organ level: boost system-level pathway matches
            if self._is_system_level_match(text1, text2):
                adjusted_score *= 1.3
            # Boost disease-related pathway matches
            elif self._is_disease_pathway_match(text1, text2):
                adjusted_score *= 1.2
        
        return adjusted_score

    def _get_dynamic_threshold(self, ke_title: str, bio_level: str = None) -> float:
        """Get dynamic similarity threshold based on KE characteristics"""
        base_threshold = 0.25
        
        # Well-defined biological processes should have stricter thresholds
        high_specificity_terms = {
            'apoptosis', 'proliferation', 'differentiation', 'inflammation', 'oxidative', 
            'dna damage', 'cell death', 'receptor', 'enzyme', 'kinase', 'phosphatase'
        }
        
        # Broader/complex processes can use lower thresholds
        broad_process_terms = {
            'function', 'dysfunction', 'activity', 'regulation', 'response', 'stress',
            'development', 'growth', 'metabolism', 'transport'
        }
        
        ke_lower = ke_title.lower()
        
        if any(term in ke_lower for term in high_specificity_terms):
            return base_threshold + 0.05  # Stricter for specific processes
        elif any(term in ke_lower for term in broad_process_terms):
            return base_threshold - 0.05  # More lenient for broad processes
            
        # Biological level adjustments
        if bio_level == "Molecular":
            return base_threshold - 0.03  # More lenient for molecular level
        elif bio_level in ["Tissue", "Organ"]:
            return base_threshold - 0.08  # Much more lenient for higher levels
            
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

    def _remove_directionality_terms(self, text: str) -> str:
        """Remove directionality terms from KE titles for better text matching"""
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

    def _combine_and_rank_suggestions(
        self,
        gene_suggestions: List[Dict],
        text_suggestions: List[Dict],
        limit: int,
    ) -> List[Dict]:
        """Combine gene-based and text-based suggestions with hybrid ranking"""
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
            query_no_direction = self._remove_directionality_terms(query)
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
            logger.error(f"Error in pathway search: {str(e)}")
            return []