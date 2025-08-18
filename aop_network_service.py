"""
Network visualization service for AOP pathways.

This service provides functionality to build Cytoscape.js network structures
from AOP-Wiki SPARQL data, following clean service architecture patterns.
Includes gene integration from WikiPathways via KE-WP mappings.
"""
import logging
from typing import Dict, Set, List, Any, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# KE Type classification mapping
KE_TYPE_CLASSIFICATION = {
    "MolecularInitiatingEvent": "mie",
    "AdverseOutcome": "ao",
    "KeyEvent": "intermediate"  # Default for generic KeyEvent
}

# Biological level styling configuration
BIOLOGICAL_LEVEL_STYLES = {
    "Molecular": {"class": "molecular", "priority": 1},
    "Cellular": {"class": "cellular", "priority": 2},
    "Tissue": {"class": "tissue", "priority": 3},
    "Organ": {"class": "organ", "priority": 4},
    "Individual": {"class": "individual", "priority": 5},
    "Population": {"class": "population", "priority": 6}
}


def process_sparql_results(sparql_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict], List[Dict]]:
    """
    Process raw SPARQL results into structured node and edge data.
    
    Args:
        sparql_results: List of SPARQL binding dictionaries
    
    Returns:
        Tuple of (nodes_dict, edges_list) where:
        - nodes_dict: Dictionary mapping KE IDs to node data
        - edges_list: List of edge dictionaries with source/target relationships
    """
    logger.info("Processing SPARQL results into structured data")
    
    nodes = {}
    edges = []
    
    for binding in sparql_results:
        ke_page = binding.get("KEpage", {}).get("value", "")
        ke_title = binding.get("KEtitle", {}).get("value", "")
        ke_label = binding.get("KElabel", {}).get("value", "")
        bio_level = binding.get("biolevel", {}).get("value", "")
        ke_type = binding.get("KEtype", {}).get("value", "")
        
        # Add node if not already present
        if ke_page not in nodes:
            nodes[ke_page] = {
                "id": ke_page,
                "title": ke_title,
                "label": ke_label,
                "bio_level": bio_level,
                "ke_type": ke_type,
                "ke_class": classify_ke_type(ke_type)
            }
        
        # Process relationships
        upstream = binding.get("upstreamKE", {}).get("value", "")
        downstream = binding.get("downstreamKE", {}).get("value", "")
        
        if upstream and upstream != ke_page:
            edges.append({
                "source": upstream,
                "target": ke_page,
                "type": "upstream_to_downstream"
            })
        
        if downstream and downstream != ke_page:
            edges.append({
                "source": ke_page,
                "target": downstream,
                "type": "upstream_to_downstream"
            })
    
    # Remove duplicate edges
    unique_edges = []
    edge_set = set()
    for edge in edges:
        edge_key = (edge["source"], edge["target"])
        if edge_key not in edge_set:
            edge_set.add(edge_key)
            unique_edges.append(edge)
    
    logger.info(f"Processed {len(nodes)} nodes and {len(unique_edges)} unique edges")
    
    return nodes, unique_edges


def classify_ke_type(ke_type: str) -> str:
    """
    Classify Key Event type from SPARQL data (fallback method).
    
    Args:
        ke_type: Raw KE type from SPARQL (e.g., "http://aopkb.org/aop_ontology#MolecularInitiatingEvent")
    
    Returns:
        String classification: "mie", "ao", or "intermediate"
    """
    if not ke_type:
        return "intermediate"
    
    # Extract the class name from the URI
    for ke_class, classification in KE_TYPE_CLASSIFICATION.items():
        if ke_class in ke_type:
            return classification
    
    return "intermediate"


def identify_mie_ao_from_structure(nodes_dict: Dict[str, Dict], edges_list: List[Dict]) -> Dict[str, Dict]:
    """
    Identify MIE and AO nodes based on network topology structure.
    
    MIE nodes have no incoming edges (source nodes).
    AO nodes have no outgoing edges (sink nodes).
    All others are intermediate nodes.
    
    Args:
        nodes_dict: Dictionary mapping KE IDs to node metadata
        edges_list: List of edge dictionaries with source/target relationships
    
    Returns:
        Updated nodes_dict with structure-based ke_class assignments
    """
    logger.info("Identifying MIE/AO from network structure")
    
    # Track incoming and outgoing edges for each node
    incoming_edges = set()
    outgoing_edges = set()
    
    for edge in edges_list:
        source = edge["source"]
        target = edge["target"]
        
        outgoing_edges.add(source)
        incoming_edges.add(target)
    
    # Classify nodes based on edge patterns
    mie_count = 0
    ao_count = 0
    intermediate_count = 0
    
    updated_nodes = {}
    for node_id, node_data in nodes_dict.items():
        has_incoming = node_id in incoming_edges
        has_outgoing = node_id in outgoing_edges
        
        if not has_incoming and has_outgoing:
            # No incoming edges, has outgoing = MIE (source node)
            ke_class = "MIE"
            mie_count += 1
        elif has_incoming and not has_outgoing:
            # Has incoming edges, no outgoing = AO (sink node)
            ke_class = "AO"
            ao_count += 1
        else:
            # Has both or neither = intermediate
            ke_class = "intermediate"
            intermediate_count += 1
        
        # Update node data with structure-based classification
        updated_node = node_data.copy()
        updated_node["ke_class"] = ke_class
        updated_nodes[node_id] = updated_node
    
    logger.info(f"Structure-based classification: {mie_count} MIEs, {ao_count} AOs, {intermediate_count} intermediates")
    
    return updated_nodes


def build_cytoscape_network(
    nodes_dict: Dict[str, Dict], 
    edges_list: List[Dict],
    validate_edges: bool = True,
    use_structure_classification: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build Cytoscape.js network data structure from processed AOP data.
    
    Args:
        nodes_dict: Dictionary mapping KE IDs to node metadata
        edges_list: List of edge dictionaries with source/target relationships
        validate_edges: Whether to filter out edges with invalid references
        use_structure_classification: Whether to use topology-based MIE/AO detection
    
    Returns:
        Dictionary with 'nodes' and 'edges' keys for Cytoscape.js format
    """
    logger.info("Building Cytoscape network structure")
    
    # Apply structure-based classification if requested
    if use_structure_classification:
        nodes_dict = identify_mie_ao_from_structure(nodes_dict, edges_list)
    
    # Build nodes
    cy_nodes = []
    for ke_id, node_data in nodes_dict.items():
        # Get biological level styling
        bio_level = node_data.get("bio_level", "")
        bio_level_info = BIOLOGICAL_LEVEL_STYLES.get(bio_level, {"class": "unknown", "priority": 99})
        
        # Get structure-based classification
        ke_class = node_data.get("ke_class", "intermediate")
        
        # Build CSS classes for styling (matching your other service format)
        classes = []
        classes.append(bio_level_info["class"])
        
        cytoscape_node = {
            "data": {
                "id": ke_id,
                "label": node_data.get("label", node_data.get("title", ke_id)),
                "title": node_data.get("title", ""),
                "bio_level": bio_level,
                "ke_type": ke_class,  # Use structure-based classification
                "ke_class": ke_class,
                "bio_priority": bio_level_info["priority"]
            },
            "classes": " ".join(classes) if classes else ""
        }
        
        cy_nodes.append(cytoscape_node)
    
    # Build edges with validation
    cy_edges = []
    valid_node_ids = set(nodes_dict.keys())
    
    for i, edge in enumerate(edges_list):
        source_id = edge["source"]
        target_id = edge["target"]
        
        # Validate edge references if requested
        if validate_edges:
            if source_id not in valid_node_ids or target_id not in valid_node_ids:
                logger.debug(f"Skipping invalid edge: {source_id} -> {target_id}")
                continue
        
        cytoscape_edge = {
            "data": {
                "id": f"edge_{i}",
                "source": source_id,
                "target": target_id,
                "type": edge.get("type", "relationship")
            }
        }
        
        cy_edges.append(cytoscape_edge)
    
    network = {
        "nodes": cy_nodes,
        "edges": cy_edges
    }
    
    logger.info(f"Network built: {len(cy_nodes)} nodes, {len(cy_edges)} edges")
    
    return network


def build_cytoscape_aop_network(
    aop_id: str,
    sparql_results: List[Dict[str, Any]],
    complete_network: bool = False
) -> Dict[str, Any]:
    """
    Main service function to build complete AOP network for Cytoscape.js visualization.
    
    Args:
        aop_id: AOP identifier URL
        sparql_results: Raw SPARQL query results
        complete_network: Whether this represents a complete network query
    
    Returns:
        Dictionary containing network data and metadata:
        - nodes: List of Cytoscape node objects
        - edges: List of Cytoscape edge objects  
        - node_count: Number of nodes
        - edge_count: Number of edges
        - aop_id: AOP identifier
        - query_type: "complete" or "filtered"
        - metadata: Additional network information
    """
    logger.info(f"Building Cytoscape network for AOP: {aop_id}")
    
    try:
        # Process raw SPARQL data
        nodes_dict, edges_list = process_sparql_results(sparql_results)
        
        # Build Cytoscape network structure with structure-based classification
        network = build_cytoscape_network(
            nodes_dict, 
            edges_list, 
            validate_edges=True, 
            use_structure_classification=True
        )
        
        # Calculate network statistics based on structure-based classification
        mie_count = len([n for n in network["nodes"] if n["data"]["ke_class"] == "MIE"])
        ao_count = len([n for n in network["nodes"] if n["data"]["ke_class"] == "AO"])
        intermediate_count = len([n for n in network["nodes"] if n["data"]["ke_class"] == "intermediate"])
        
        # Build complete response
        response = {
            "aop_id": aop_id,
            "nodes": network["nodes"],
            "edges": network["edges"],
            "node_count": len(network["nodes"]),
            "edge_count": len(network["edges"]),
            "query_type": "complete" if complete_network else "filtered",
            "complete_network": complete_network,
            "metadata": {
                "mie_count": mie_count,
                "ao_count": ao_count,
                "intermediate_count": intermediate_count,
                "biological_levels": list(set(n["data"]["bio_level"] for n in network["nodes"] if n["data"]["bio_level"]))
            }
        }
        
        logger.info(f"Successfully built AOP network: {response['node_count']} nodes, {response['edge_count']} edges")
        logger.debug(f"Network composition: {mie_count} MIEs, {ao_count} AOs, {intermediate_count} intermediates")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to build AOP network for {aop_id}: {str(e)}")
        raise


def validate_network_integrity(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate network data integrity and filter invalid edges.
    
    Args:
        network_data: Network dictionary with nodes and edges
    
    Returns:
        Cleaned network data with validation statistics
    """
    logger.info("Validating network integrity")
    
    if not network_data or "nodes" not in network_data or "edges" not in network_data:
        logger.warning("Invalid network data structure")
        return network_data
    
    # Get valid node IDs
    valid_node_ids = set(node["data"]["id"] for node in network_data["nodes"])
    
    # Filter edges
    valid_edges = []
    filtered_count = 0
    
    for edge in network_data["edges"]:
        source = edge["data"]["source"]
        target = edge["data"]["target"]
        
        if source in valid_node_ids and target in valid_node_ids:
            valid_edges.append(edge)
        else:
            filtered_count += 1
            logger.debug(f"Filtered invalid edge: {source} -> {target}")
    
    # Update network data
    network_data["edges"] = valid_edges
    network_data["edge_count"] = len(valid_edges)
    network_data["filtered_edges"] = filtered_count
    
    if filtered_count > 0:
        logger.info(f"Network validation: filtered {filtered_count} invalid edges")
    
    return network_data


def get_genes_from_mapped_pathways(ke_ids: List[str], mapping_model) -> Dict[str, List[Dict[str, str]]]:
    """
    Get genes from pathways that are mapped to the given Key Events.
    
    Args:
        ke_ids: List of Key Event IDs in the AOP network
        mapping_model: Database model to query KE-WP mappings
    
    Returns:
        Dict mapping pathway_id -> [{"id": gene_id, "label": gene_label}]
    """
    logger.info(f"Getting genes from pathways mapped to {len(ke_ids)} Key Events")
    
    try:
        # 1. Get pathways mapped to these KEs
        # Convert AOP event URLs to simple KE IDs for database lookup
        mapped_pathways = []
        for ke_id in ke_ids:
            # Convert URLs like "https://identifiers.org/aop.events/112" to "KE 112"
            simple_ke_id = ke_id
            if 'aop.events/' in ke_id:
                ke_number = ke_id.split('aop.events/')[-1]
                simple_ke_id = f"KE {ke_number}"
            
            ke_mappings = mapping_model.get_mappings_by_ke(simple_ke_id)
            for mapping in ke_mappings:
                if mapping.get('wp_id') not in [p['wp_id'] for p in mapped_pathways]:
                    mapped_pathways.append({
                        'wp_id': mapping.get('wp_id'),
                        'wp_title': mapping.get('wp_title', ''),
                        'ke_id': ke_id,  # Keep original KE ID for network connections
                        'simple_ke_id': simple_ke_id
                    })
        
        if not mapped_pathways:
            logger.info("No mapped pathways found for KEs")
            return {}
        
        logger.info(f"Found {len(mapped_pathways)} mapped pathways")
        
        # 2. Convert WP IDs to full URIs for SPARQL
        pathway_uris = []
        wp_id_to_info = {}
        
        for pathway in mapped_pathways:
            wp_id = pathway['wp_id']
            # Handle different WP ID formats
            if wp_id.startswith('WP'):
                uri = f"http://identifiers.org/wikipathways/{wp_id}"
            else:
                uri = f"http://identifiers.org/wikipathways/WP{wp_id}"
            
            pathway_uris.append(f"<{uri}>")
            wp_id_to_info[wp_id] = pathway
        
        # 3. Query WikiPathways SPARQL for genes
        sparql_query = f"""
        SELECT DISTINCT ?gene ?geneLabel ?pathway
        WHERE {{
          VALUES ?pathway {{ {" ".join(pathway_uris)} }}
          ?gene dcterms:isPartOf ?pathway .
          ?pathway a wp:Pathway .
          ?gene rdfs:label ?geneLabel .
          FILTER(CONTAINS(STR(?gene), "GeneProduct"))
        }}
        """
        
        # 4. Execute SPARQL query
        sparql_endpoint = "https://sparql.wikipathways.org/sparql"
        headers = {
            'Accept': 'application/sparql-results+json',
            'User-Agent': 'KE-WP-Mapping-Tool/2.2.0'
        }
        
        response = requests.post(
            sparql_endpoint,
            data={'query': sparql_query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"SPARQL query failed: {response.status_code}")
            return {}
        
        results = response.json()
        
        # 5. Process results
        pathway_genes = {}
        
        for binding in results.get('results', {}).get('bindings', []):
            pathway_uri = binding.get('pathway', {}).get('value', '')
            gene_uri = binding.get('gene', {}).get('value', '')
            gene_label = binding.get('geneLabel', {}).get('value', '')
            
            # Extract WP ID from pathway URI
            wp_id = None
            if 'wikipathways' in pathway_uri:
                wp_id = pathway_uri.split('/')[-1]
            
            if wp_id and gene_uri and gene_label:
                if wp_id not in pathway_genes:
                    pathway_genes[wp_id] = []
                
                # Extract gene ID from URI (use last part)
                gene_id = gene_uri.split('/')[-1] if '/' in gene_uri else gene_uri
                
                pathway_genes[wp_id].append({
                    'id': gene_id,
                    'label': gene_label,
                    'uri': gene_uri
                })
        
        total_genes = sum(len(genes) for genes in pathway_genes.values())
        logger.info(f"Retrieved {total_genes} genes from {len(pathway_genes)} pathways")
        
        return pathway_genes
        
    except Exception as e:
        logger.error(f"Failed to get genes from mapped pathways: {str(e)}")
        return {}


def build_gene_enhanced_network(base_network: Dict[str, Any], gene_data: Dict[str, List[Dict[str, str]]], 
                               ke_pathway_mappings: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Add gene nodes and edges to existing AOP network.
    
    Args:
        base_network: Existing KE network from build_cytoscape_aop_network()
        gene_data: Gene data from get_genes_from_mapped_pathways()
        ke_pathway_mappings: Dict mapping KE_ID -> [pathway_ids] for connections
    
    Returns:
        Enhanced network with gene nodes (ellipses) and KE-gene connections
    """
    logger.info("Building gene-enhanced network")
    
    enhanced_nodes = base_network["nodes"].copy()
    enhanced_edges = base_network["edges"].copy()
    
    gene_count = 0
    
    # Add gene nodes and connections
    for pathway_id, genes in gene_data.items():
        for gene in genes:
            gene_node_id = f"gene_{gene['id']}"
            
            # Create gene node (ellipse shape)
            gene_node = {
                "data": {
                    "id": gene_node_id,
                    "label": gene['label'],
                    "type": "gene",
                    "pathway": pathway_id,
                    "uri": gene.get('uri', '')
                },
                "classes": "gene-node"
            }
            enhanced_nodes.append(gene_node)
            gene_count += 1
            
            # Connect gene to KEs that are mapped to this pathway
            for ke_id, mapped_pathways in ke_pathway_mappings.items():
                if pathway_id in mapped_pathways:
                    # Create KE-gene connection via pathway
                    edge_id = f"edge_ke_gene_{ke_id}_{gene['id']}"
                    edge = {
                        "data": {
                            "id": edge_id,
                            "source": ke_id,
                            "target": gene_node_id,
                            "type": "ke_gene_pathway",
                            "pathway": pathway_id
                        },
                        "classes": "ke-gene-edge"
                    }
                    enhanced_edges.append(edge)
    
    # Update network metadata
    enhanced_network = {
        "nodes": enhanced_nodes,
        "edges": enhanced_edges,
        "node_count": len(enhanced_nodes),
        "edge_count": len(enhanced_edges),
        "gene_count": gene_count,
        "includes_genes": True
    }
    
    # Preserve original metadata
    for key in base_network:
        if key not in ["nodes", "edges", "node_count", "edge_count"]:
            enhanced_network[key] = base_network[key]
    
    logger.info(f"Enhanced network: {len(enhanced_nodes)} nodes ({gene_count} genes), {len(enhanced_edges)} edges")
    
    return enhanced_network


def build_ke_pathway_mappings(ke_ids: List[str], mapping_model) -> Dict[str, List[str]]:
    """
    Build mapping of KE IDs to their associated pathway IDs.
    
    Args:
        ke_ids: List of Key Event IDs (may be AOP event URLs)
        mapping_model: Database model to query mappings
    
    Returns:
        Dict mapping KE_ID -> [pathway_ids]
    """
    ke_pathway_map = {}
    
    for ke_id in ke_ids:
        # Convert AOP event URLs to simple KE IDs for database lookup
        simple_ke_id = ke_id
        if 'aop.events/' in ke_id:
            ke_number = ke_id.split('aop.events/')[-1]
            simple_ke_id = f"KE {ke_number}"
        
        mappings = mapping_model.get_mappings_by_ke(simple_ke_id)
        pathway_ids = [mapping.get('wp_id') for mapping in mappings if mapping.get('wp_id')]
        if pathway_ids:
            ke_pathway_map[ke_id] = pathway_ids  # Use original KE ID as key
    
    return ke_pathway_map