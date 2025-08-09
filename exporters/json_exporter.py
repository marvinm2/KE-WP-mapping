"""
JSON and JSON-LD export functionality for KE-WP mapping dataset
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class JSONExporter:
    """Export dataset in JSON and JSON-LD formats"""
    
    def __init__(self, database, metadata_manager):
        self.db = database
        self.metadata = metadata_manager
    
    def export(self, include_metadata: bool = True, include_provenance: bool = True) -> str:
        """Export dataset in comprehensive JSON format"""
        conn = self.db.get_connection()
        try:
            # Get all mappings
            cursor = conn.execute("""
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type, 
                       confidence_level, created_by, created_at, updated_at
                FROM mappings 
                ORDER BY created_at DESC
            """)
            mappings = [dict(row) for row in cursor.fetchall()]
            
            # Build comprehensive JSON structure
            export_data = {
                "dataset_info": {
                    "name": "Key Event to WikiPathways Mapping Dataset",
                    "description": "Curated mappings between AOP Key Events and WikiPathways biological pathways",
                    "export_timestamp": datetime.now().isoformat(),
                    "version": self.metadata.metadata.get("version", "1.0.0"),
                    "record_count": len(mappings),
                    "license": "CC-BY-4.0"
                },
                "data_schema": {
                    "fields": [
                        {
                            "name": "id",
                            "type": "integer",
                            "description": "Unique mapping identifier"
                        },
                        {
                            "name": "ke_id", 
                            "type": "string",
                            "description": "Key Event identifier from AOP-Wiki (format: KE XXXX)",
                            "example": "KE 1234"
                        },
                        {
                            "name": "ke_title",
                            "type": "string", 
                            "description": "Title/name of the Key Event"
                        },
                        {
                            "name": "wp_id",
                            "type": "string",
                            "description": "WikiPathways identifier (format: WPXXXX)",
                            "example": "WP1234"
                        },
                        {
                            "name": "wp_title",
                            "type": "string",
                            "description": "Title/name of the WikiPathways pathway"
                        },
                        {
                            "name": "connection_type",
                            "type": "string",
                            "description": "Type of biological relationship",
                            "allowed_values": ["causative", "responsive", "other", "undefined"],
                            "definitions": {
                                "causative": "Pathway causes the Key Event to occur",
                                "responsive": "Pathway responds to the Key Event",
                                "other": "Other defined relationship",
                                "undefined": "Relationship type not determined"
                            }
                        },
                        {
                            "name": "confidence_level",
                            "type": "string", 
                            "description": "Confidence in the mapping based on evidence strength",
                            "allowed_values": ["low", "medium", "high"],
                            "definitions": {
                                "high": "Direct biological link with strong experimental evidence",
                                "medium": "Partial or indirect relationship with moderate evidence",
                                "low": "Weak or speculative connection with limited evidence"
                            }
                        },
                        {
                            "name": "created_by",
                            "type": "string",
                            "description": "Username of the person who created this mapping"
                        },
                        {
                            "name": "created_at",
                            "type": "datetime",
                            "description": "Timestamp when mapping was created (ISO 8601 format)"
                        },
                        {
                            "name": "updated_at", 
                            "type": "datetime",
                            "description": "Timestamp when mapping was last updated (ISO 8601 format)"
                        }
                    ]
                },
                "mappings": mappings
            }
            
            # Add comprehensive metadata if requested
            if include_metadata:
                export_data["metadata"] = self.metadata.get_current_metadata()
            
            # Add provenance information if requested
            if include_provenance:
                export_data["provenance"] = self._get_provenance_info()
            
            # Add statistics
            export_data["statistics"] = self._generate_statistics(mappings)
            
            return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
            
        finally:
            conn.close()
    
    def export_json_ld(self, include_metadata: bool = True) -> str:
        """Export dataset in JSON-LD format for semantic web compatibility"""
        conn = self.db.get_connection()
        try:
            # Get all mappings
            cursor = conn.execute("""
                SELECT id, ke_id, ke_title, wp_id, wp_title, connection_type, 
                       confidence_level, created_by, created_at, updated_at
                FROM mappings 
                ORDER BY created_at DESC
            """)
            mappings = [dict(row) for row in cursor.fetchall()]
            
            # Build JSON-LD structure with schema.org and custom vocabularies
            json_ld = {
                "@context": {
                    "@vocab": "https://schema.org/",
                    "aop": "http://aopwiki.org/vocab#",
                    "wp": "http://vocabularies.wikipathways.org/",
                    "ke": "aop:KeyEvent",
                    "pathway": "wp:Pathway",
                    "mapping": "aop:PathwayMapping",
                    "confidence": "aop:confidenceLevel",
                    "connection": "aop:connectionType"
                },
                "@type": "Dataset",
                "@id": "https://ke-wp-mapping.org/dataset",
                "name": "Key Event to WikiPathways Mapping Dataset",
                "description": "Curated mappings between AOP Key Events and WikiPathways biological pathways with confidence assessments and connection type classifications",
                "datePublished": datetime.now().isoformat(),
                "version": self.metadata.metadata.get("version", "1.0.0"),
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "creator": {
                    "@type": "Organization",
                    "name": "KE-WP Mapping Community"
                },
                "publisher": {
                    "@type": "Organization", 
                    "name": "KE-WP Mapping Platform"
                },
                "keywords": [
                    "Adverse Outcome Pathways",
                    "WikiPathways", 
                    "Key Events",
                    "Biological Pathways",
                    "Systems Biology",
                    "Toxicology"
                ],
                "temporalCoverage": self._get_temporal_coverage(),
                "size": f"{len(mappings)} mapping records",
                "encodingFormat": ["application/ld+json", "application/json"],
                "distribution": [
                    {
                        "@type": "DataDownload",
                        "encodingFormat": "application/ld+json",
                        "contentUrl": "https://ke-wp-mapping.org/export/jsonld"
                    },
                    {
                        "@type": "DataDownload", 
                        "encodingFormat": "application/json",
                        "contentUrl": "https://ke-wp-mapping.org/export/json"
                    },
                    {
                        "@type": "DataDownload",
                        "encodingFormat": "text/csv", 
                        "contentUrl": "https://ke-wp-mapping.org/download"
                    }
                ],
                "hasPart": []
            }
            
            # Add individual mappings as structured data
            for mapping in mappings:
                mapping_ld = {
                    "@type": "mapping",
                    "@id": f"https://ke-wp-mapping.org/mapping/{mapping['id']}",
                    "identifier": str(mapping["id"]),
                    "keyEvent": {
                        "@type": "ke",
                        "@id": f"https://aopwiki.org/events/{mapping['ke_id'].replace('KE ', '')}",
                        "identifier": mapping["ke_id"],
                        "name": mapping["ke_title"]
                    },
                    "pathway": {
                        "@type": "pathway", 
                        "@id": f"https://www.wikipathways.org/pathways/{mapping['wp_id']}.html",
                        "identifier": mapping["wp_id"],
                        "name": mapping["wp_title"]
                    },
                    "confidence": mapping["confidence_level"],
                    "connection": mapping["connection_type"],
                    "creator": mapping.get("created_by"),
                    "dateCreated": mapping.get("created_at"),
                    "dateModified": mapping.get("updated_at")
                }
                json_ld["hasPart"].append(mapping_ld)
            
            # Add metadata if requested
            if include_metadata:
                json_ld["additionalProperty"] = [
                    {
                        "@type": "PropertyValue",
                        "name": "datasetMetadata",
                        "value": self.metadata.get_current_metadata()
                    }
                ]
            
            return json.dumps(json_ld, indent=2, ensure_ascii=False, default=str)
            
        finally:
            conn.close()
    
    def _get_provenance_info(self) -> Dict:
        """Generate provenance information for the dataset"""
        conn = self.db.get_connection()
        try:
            # Get creation and update statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_mappings,
                    COUNT(DISTINCT created_by) as unique_contributors,
                    MIN(created_at) as earliest_creation,
                    MAX(created_at) as latest_creation,
                    MAX(updated_at) as latest_update
                FROM mappings
                WHERE created_at IS NOT NULL
            """)
            stats = dict(cursor.fetchone())
            
            # Get contributor statistics
            cursor = conn.execute("""
                SELECT created_by, COUNT(*) as contribution_count
                FROM mappings 
                WHERE created_by IS NOT NULL
                GROUP BY created_by
                ORDER BY contribution_count DESC
            """)
            contributors = [dict(row) for row in cursor.fetchall()]
            
            return {
                "methodology": "Expert curation using guided confidence assessment workflow",
                "data_sources": [
                    {
                        "name": "AOP-Wiki",
                        "url": "https://aopwiki.org/",
                        "description": "Source of Key Event definitions and biological context"
                    },
                    {
                        "name": "WikiPathways", 
                        "url": "https://www.wikipathways.org/",
                        "description": "Source of biological pathway information and diagrams"
                    }
                ],
                "curation_process": [
                    "Key Event selection from AOP-Wiki database",
                    "Pathway identification from WikiPathways database", 
                    "Biological relevance assessment",
                    "Evidence strength evaluation",
                    "Confidence level determination",
                    "Connection type classification",
                    "Community review and validation"
                ],
                "quality_control": [
                    "Input validation using structured schemas",
                    "Duplicate detection and prevention",
                    "Expert review process for high-impact mappings",
                    "Community feedback and correction mechanisms"
                ],
                "statistics": stats,
                "contributors": contributors
            }
            
        finally:
            conn.close()
    
    def _generate_statistics(self, mappings: List[Dict]) -> Dict:
        """Generate statistical summary of the dataset"""
        if not mappings:
            return {}
        
        # Confidence level distribution
        confidence_dist = {}
        for mapping in mappings:
            conf = mapping.get("confidence_level", "unknown")
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
        
        # Connection type distribution
        connection_dist = {}
        for mapping in mappings:
            conn = mapping.get("connection_type", "unknown")
            connection_dist[conn] = connection_dist.get(conn, 0) + 1
        
        # Temporal distribution
        years = {}
        for mapping in mappings:
            if mapping.get("created_at"):
                try:
                    year = mapping["created_at"][:4]
                    years[year] = years.get(year, 0) + 1
                except (TypeError, IndexError):
                    continue
        
        # Contributor statistics
        contributors = {}
        for mapping in mappings:
            contrib = mapping.get("created_by", "anonymous")
            contributors[contrib] = contributors.get(contrib, 0) + 1
        
        return {
            "total_mappings": len(mappings),
            "confidence_distribution": confidence_dist,
            "connection_type_distribution": connection_dist,
            "temporal_distribution": years,
            "contributor_distribution": dict(sorted(contributors.items(), key=lambda x: x[1], reverse=True)),
            "top_contributors": dict(list(sorted(contributors.items(), key=lambda x: x[1], reverse=True))[:10])
        }
    
    def _get_temporal_coverage(self) -> str:
        """Get temporal coverage of the dataset"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("""
                SELECT MIN(created_at) as start_date, MAX(created_at) as end_date
                FROM mappings 
                WHERE created_at IS NOT NULL
            """)
            result = cursor.fetchone()
            
            if result["start_date"] and result["end_date"]:
                start = result["start_date"][:10]  # Extract date part
                end = result["end_date"][:10]
                return f"{start}/{end}"
            
            return datetime.now().strftime("%Y-%m-%d")
            
        finally:
            conn.close()