"""
RDF and Turtle export functionality for KE-WP mapping dataset
Provides semantic web compatible exports using standard vocabularies
"""
import logging
from typing import Dict, List
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)


class RDFExporter:
    """Export dataset in RDF/XML and Turtle formats"""
    
    def __init__(self, database, metadata_manager):
        self.db = database
        self.metadata = metadata_manager
        
        # Define namespaces and vocabularies
        self.namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/',
            'schema': 'https://schema.org/',
            'void': 'http://rdfs.org/ns/void#',
            'prov': 'http://www.w3.org/ns/prov#',
            'aop': 'http://aopwiki.org/vocab#',
            'wp': 'http://vocabularies.wikipathways.org/',
            'kewp': 'https://ke-wp-mapping.org/vocab#',
            'dataset': 'https://ke-wp-mapping.org/dataset/',
            'mapping': 'https://ke-wp-mapping.org/mapping/'
        }
    
    def export(self, format_type: str = "rdf") -> str:
        """Export dataset in RDF format"""
        if format_type.lower() == "turtle":
            return self.export_turtle()
        else:
            return self.export_rdf_xml()
    
    def export_rdf_xml(self) -> str:
        """Export dataset in RDF/XML format"""
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
            
            # Build RDF/XML
            rdf_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
            rdf_lines.append('<rdf:RDF')
            
            # Add namespace declarations
            for prefix, uri in self.namespaces.items():
                rdf_lines.append(f'  xmlns:{prefix}="{uri}"')
            
            rdf_lines.append('>')
            
            # Add dataset metadata
            rdf_lines.extend(self._generate_dataset_metadata_rdf())
            
            # Add individual mappings
            for mapping in mappings:
                rdf_lines.extend(self._generate_mapping_rdf(mapping))
            
            rdf_lines.append('</rdf:RDF>')
            
            return '\n'.join(rdf_lines)
            
        finally:
            conn.close()
    
    def export_turtle(self) -> str:
        """Export dataset in Turtle format"""
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
            
            # Build Turtle format
            turtle_lines = []
            
            # Add namespace prefixes
            for prefix, uri in self.namespaces.items():
                turtle_lines.append(f'@prefix {prefix}: <{uri}> .')
            turtle_lines.append('')
            
            # Add dataset metadata
            turtle_lines.extend(self._generate_dataset_metadata_turtle())
            turtle_lines.append('')
            
            # Add individual mappings
            for mapping in mappings:
                turtle_lines.extend(self._generate_mapping_turtle(mapping))
                turtle_lines.append('')
            
            return '\n'.join(turtle_lines)
            
        finally:
            conn.close()
    
    def _generate_dataset_metadata_rdf(self) -> List[str]:
        """Generate RDF/XML for dataset metadata"""
        metadata = self.metadata.get_current_metadata()
        lines = []
        
        lines.append('  <!-- Dataset Metadata -->')
        lines.append('  <void:Dataset rdf:about="https://ke-wp-mapping.org/dataset">')
        lines.append(f'    <dcterms:title>{escape(metadata["titles"][0]["title"])}</dcterms:title>')
        
        # Add descriptions
        for desc in metadata["descriptions"]:
            if desc["description_type"] == "Abstract":
                lines.append(f'    <dcterms:description>{escape(desc["description"])}</dcterms:description>')
        
        lines.append(f'    <dcterms:publisher>{escape(metadata["publisher"])}</dcterms:publisher>')
        lines.append(f'    <dcterms:created rdf:datatype="http://www.w3.org/2001/XMLSchema#gYear">{metadata["publication_year"]}</dcterms:created>')
        lines.append(f'    <dcterms:language>{metadata["language"]}</dcterms:language>')
        lines.append(f'    <schema:version>{escape(metadata["version"])}</schema:version>')
        
        # Add creators
        for creator in metadata["creators"]:
            if creator["name_type"] == "Organizational":
                lines.append(f'    <dcterms:creator>')
                lines.append(f'      <foaf:Organization>')
                lines.append(f'        <foaf:name>{escape(creator["name"])}</foaf:name>')
                lines.append(f'      </foaf:Organization>')
                lines.append(f'    </dcterms:creator>')
            else:
                lines.append(f'    <dcterms:creator>')
                lines.append(f'      <foaf:Person>')
                lines.append(f'        <foaf:name>{escape(creator["name"])}</foaf:name>')
                lines.append(f'      </foaf:Person>')
                lines.append(f'    </dcterms:creator>')
        
        # Add subjects/keywords
        for subject in metadata["subjects"]:
            lines.append(f'    <dcterms:subject>{escape(subject["subject"])}</dcterms:subject>')
        
        # Add rights
        if metadata["rights_list"]:
            rights = metadata["rights_list"][0]
            lines.append(f'    <dcterms:rights rdf:resource="{rights["rights_uri"]}"/>')
            lines.append(f'    <dcterms:license rdf:resource="{rights["rights_uri"]}"/>')
        
        # Add void statistics
        lines.append(f'    <void:triples rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{len(metadata.get("sizes", []))}</void:triples>')
        
        # Add related identifiers
        for related in metadata["related_identifiers"]:
            lines.append(f'    <dcterms:relation rdf:resource="{escape(related["related_identifier"])}"/>')
        
        lines.append('  </void:Dataset>')
        
        return lines
    
    def _generate_mapping_rdf(self, mapping: Dict) -> List[str]:
        """Generate RDF/XML for individual mapping"""
        lines = []
        mapping_id = mapping["id"]
        
        lines.append(f'  <!-- Mapping {mapping_id} -->')
        lines.append(f'  <kewp:PathwayMapping rdf:about="https://ke-wp-mapping.org/mapping/{mapping_id}">')
        lines.append(f'    <dcterms:identifier rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{mapping_id}</dcterms:identifier>')
        
        # Key Event
        ke_url = f"https://aopwiki.org/events/{mapping['ke_id'].replace('KE ', '')}"
        lines.append(f'    <kewp:hasKeyEvent>')
        lines.append(f'      <aop:KeyEvent rdf:about="{ke_url}">')
        lines.append(f'        <dcterms:identifier>{escape(mapping["ke_id"])}</dcterms:identifier>')
        lines.append(f'        <dcterms:title>{escape(mapping["ke_title"])}</dcterms:title>')
        lines.append(f'      </aop:KeyEvent>')
        lines.append(f'    </kewp:hasKeyEvent>')
        
        # WikiPathways
        wp_url = f"https://www.wikipathways.org/pathways/{mapping['wp_id']}.html"
        lines.append(f'    <kewp:hasPathway>')
        lines.append(f'      <wp:Pathway rdf:about="{wp_url}">')
        lines.append(f'        <dcterms:identifier>{escape(mapping["wp_id"])}</dcterms:identifier>')
        lines.append(f'        <dcterms:title>{escape(mapping["wp_title"])}</dcterms:title>')
        lines.append(f'      </wp:Pathway>')
        lines.append(f'    </kewp:hasPathway>')
        
        # Mapping properties
        lines.append(f'    <kewp:confidenceLevel rdf:resource="https://ke-wp-mapping.org/vocab#{mapping["confidence_level"]}"/>')
        lines.append(f'    <kewp:connectionType rdf:resource="https://ke-wp-mapping.org/vocab#{mapping["connection_type"]}"/>')
        
        # Provenance
        if mapping.get("created_by"):
            lines.append(f'    <prov:wasAttributedTo>')
            lines.append(f'      <prov:Agent>')
            lines.append(f'        <foaf:name>{escape(mapping["created_by"])}</foaf:name>')
            lines.append(f'      </prov:Agent>')
            lines.append(f'    </prov:wasAttributedTo>')
        
        if mapping.get("created_at"):
            lines.append(f'    <prov:generatedAtTime rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">{mapping["created_at"]}</prov:generatedAtTime>')
        
        if mapping.get("updated_at"):
            lines.append(f'    <dcterms:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">{mapping["updated_at"]}</dcterms:modified>')
        
        lines.append('  </kewp:PathwayMapping>')
        
        return lines
    
    def _generate_dataset_metadata_turtle(self) -> List[str]:
        """Generate Turtle for dataset metadata"""
        metadata = self.metadata.get_current_metadata()
        lines = []
        
        lines.append('# Dataset Metadata')
        lines.append('dataset: a void:Dataset ;')
        lines.append(f'  dcterms:title "{metadata["titles"][0]["title"]}" ;')
        
        # Add descriptions
        for desc in metadata["descriptions"]:
            if desc["description_type"] == "Abstract":
                lines.append(f'  dcterms:description "{desc["description"]}" ;')
        
        lines.append(f'  dcterms:publisher "{metadata["publisher"]}" ;')
        lines.append(f'  dcterms:created "{metadata["publication_year"]}"^^xsd:gYear ;')
        lines.append(f'  dcterms:language "{metadata["language"]}" ;')
        lines.append(f'  schema:version "{metadata["version"]}" ;')
        
        # Add creators
        creator_lines = []
        for creator in metadata["creators"]:
            if creator["name_type"] == "Organizational":
                creator_lines.append(f'    [ a foaf:Organization ; foaf:name "{creator["name"]}" ]')
            else:
                creator_lines.append(f'    [ a foaf:Person ; foaf:name "{creator["name"]}" ]')
        
        if creator_lines:
            lines.append('  dcterms:creator')
            lines.extend(creator_lines[:-1])  # All but last
            lines.append(creator_lines[-1] + ' ;')  # Last with semicolon
        
        # Add subjects
        subject_lines = [f'    "{subject["subject"]}"' for subject in metadata["subjects"]]
        if subject_lines:
            lines.append('  dcterms:subject')
            lines.extend(subject_lines[:-1])  # All but last with comma
            lines.append(subject_lines[-1] + ' ;')  # Last with semicolon
        
        # Add rights
        if metadata["rights_list"]:
            rights = metadata["rights_list"][0]
            lines.append(f'  dcterms:rights <{rights["rights_uri"]}> ;')
            lines.append(f'  dcterms:license <{rights["rights_uri"]}> ;')
        
        # Add related resources
        for related in metadata["related_identifiers"]:
            lines.append(f'  dcterms:relation <{related["related_identifier"]}> ;')
        
        # Remove last semicolon and add period
        if lines[-1].endswith(' ;'):
            lines[-1] = lines[-1][:-2] + ' .'
        
        return lines
    
    def _generate_mapping_turtle(self, mapping: Dict) -> List[str]:
        """Generate Turtle for individual mapping"""
        lines = []
        mapping_id = mapping["id"]
        
        lines.append(f'# Mapping {mapping_id}')
        lines.append(f'mapping:{mapping_id} a kewp:PathwayMapping ;')
        lines.append(f'  dcterms:identifier {mapping_id} ;')
        
        # Key Event
        ke_id_clean = mapping['ke_id'].replace('KE ', '')
        lines.append(f'  kewp:hasKeyEvent [')
        lines.append(f'    a aop:KeyEvent ;')
        lines.append(f'    dcterms:identifier "{mapping["ke_id"]}" ;')
        lines.append(f'    dcterms:title "{mapping["ke_title"]}" ;')
        lines.append(f'    owl:sameAs <https://aopwiki.org/events/{ke_id_clean}>')
        lines.append(f'  ] ;')
        
        # WikiPathways
        lines.append(f'  kewp:hasPathway [')
        lines.append(f'    a wp:Pathway ;')
        lines.append(f'    dcterms:identifier "{mapping["wp_id"]}" ;')
        lines.append(f'    dcterms:title "{mapping["wp_title"]}" ;')
        lines.append(f'    owl:sameAs <https://www.wikipathways.org/pathways/{mapping["wp_id"]}.html>')
        lines.append(f'  ] ;')
        
        # Mapping properties
        lines.append(f'  kewp:confidenceLevel kewp:{mapping["confidence_level"]} ;')
        lines.append(f'  kewp:connectionType kewp:{mapping["connection_type"]} ;')
        
        # Provenance
        if mapping.get("created_by"):
            lines.append(f'  prov:wasAttributedTo [')
            lines.append(f'    a prov:Agent ;')
            lines.append(f'    foaf:name "{mapping["created_by"]}"')
            lines.append(f'  ] ;')
        
        if mapping.get("created_at"):
            lines.append(f'  prov:generatedAtTime "{mapping["created_at"]}"^^xsd:dateTime ;')
        
        if mapping.get("updated_at"):
            lines.append(f'  dcterms:modified "{mapping["updated_at"]}"^^xsd:dateTime ;')
        
        # Remove last semicolon and add period
        if lines[-1].endswith(' ;'):
            lines[-1] = lines[-1][:-2] + ' .'
        
        return lines