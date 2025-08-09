"""
DataCite-compliant dataset metadata management for KE-WP Mapping dataset
Implements FAIR data principles with comprehensive metadata tracking
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class Creator:
    """Dataset creator information following DataCite Creator schema"""
    name: str
    name_type: str = "Personal"  # Personal or Organizational
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name_identifiers: List[Dict[str, str]] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)


@dataclass
class Contributor:
    """Dataset contributor information following DataCite Contributor schema"""
    name: str
    contributor_type: str  # ContactPerson, DataCurator, DataManager, etc.
    name_type: str = "Personal"
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name_identifiers: List[Dict[str, str]] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)


@dataclass
class Subject:
    """Subject/keyword information following DataCite Subject schema"""
    subject: str
    subject_scheme: Optional[str] = None
    scheme_uri: Optional[str] = None
    value_uri: Optional[str] = None
    classification_code: Optional[str] = None


@dataclass
class RelatedIdentifier:
    """Related identifier information following DataCite RelatedIdentifier schema"""
    related_identifier: str
    related_identifier_type: str  # DOI, URL, etc.
    relation_type: str  # IsSupplementTo, References, etc.
    resource_type_general: Optional[str] = None


@dataclass
class GeoLocation:
    """Geographic location information following DataCite GeoLocation schema"""
    geo_location_place: Optional[str] = None
    geo_location_point: Optional[Dict[str, float]] = None  # {latitude, longitude}
    geo_location_box: Optional[Dict[str, float]] = None  # {westBoundLongitude, eastBoundLongitude, southBoundLatitude, northBoundLatitude}


@dataclass
class FundingReference:
    """Funding information following DataCite FundingReference schema"""
    funder_name: str
    funder_identifier: Optional[str] = None
    funder_identifier_type: Optional[str] = None
    award_number: Optional[str] = None
    award_title: Optional[str] = None


@dataclass
class DatasetVersion:
    """Dataset version information for tracking changes"""
    version: str
    version_date: datetime
    description: str
    record_count: int
    changes: List[str] = field(default_factory=list)
    created_by: Optional[str] = None


class DatasetMetadata:
    """
    Comprehensive dataset metadata management following DataCite and FAIR principles
    """
    
    def __init__(self, database):
        self.db = database
        self.metadata = self._initialize_base_metadata()
        self.versions = []
        self._create_version_table()
    
    def _create_version_table(self):
        """Create dataset versions table if it doesn't exist"""
        conn = self.db.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    version_date TIMESTAMP NOT NULL,
                    description TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    changes TEXT,  -- JSON array of changes
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT  -- JSON metadata snapshot
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dataset_versions_date 
                ON dataset_versions(version_date)
            """)
            
            conn.commit()
            logger.info("Dataset versions table initialized")
        except Exception as e:
            logger.error(f"Error creating dataset versions table: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_base_metadata(self) -> Dict:
        """Initialize base metadata structure following DataCite schema"""
        return {
            "identifier": {
                "identifier": "",  # Will be populated with DOI when available
                "identifier_type": "DOI"
            },
            "creators": [
                Creator(
                    name="KE-WP Mapping Community",
                    name_type="Organizational",
                    affiliations=["Adverse Outcome Pathway Research Community"]
                )
            ],
            "titles": [
                {
                    "title": "Key Event to WikiPathways Mapping Dataset",
                    "title_type": "Main Title"
                },
                {
                    "title": "A curated dataset mapping Adverse Outcome Pathway Key Events to WikiPathways biological pathways",
                    "title_type": "Subtitle"
                }
            ],
            "publisher": "KE-WP Mapping Platform",
            "publication_year": datetime.now().year,
            "subjects": [
                Subject("Adverse Outcome Pathways", "keyword", None, None),
                Subject("WikiPathways", "keyword", None, None),
                Subject("Biological Pathways", "keyword", None, None),
                Subject("Key Events", "keyword", None, None),
                Subject("Systems Biology", "keyword", None, None),
                Subject("Toxicology", "keyword", None, None),
                Subject("FAIR Data", "keyword", None, None)
            ],
            "contributors": [],
            "dates": [
                {
                    "date": datetime.now().isoformat(),
                    "date_type": "Created"
                }
            ],
            "language": "en",
            "resource_type": {
                "resource_type_general": "Dataset",
                "resource_type": "Biological Pathway Mapping Dataset"
            },
            "alternate_identifiers": [],
            "related_identifiers": [
                RelatedIdentifier(
                    "https://aopwiki.org/",
                    "URL",
                    "References",
                    "Website"
                ),
                RelatedIdentifier(
                    "https://www.wikipathways.org/",
                    "URL", 
                    "References",
                    "Website"
                )
            ],
            "sizes": [],  # Will be populated dynamically
            "formats": ["application/json", "text/csv", "application/vnd.ms-excel", "application/parquet"],
            "version": "1.0.0",
            "rights_list": [
                {
                    "rights": "Creative Commons Attribution 4.0 International",
                    "rights_uri": "https://creativecommons.org/licenses/by/4.0/",
                    "rights_identifier": "CC-BY-4.0",
                    "rights_identifier_scheme": "SPDX"
                }
            ],
            "descriptions": [
                {
                    "description": "This dataset contains curated mappings between Key Events from the Adverse Outcome Pathway (AOP) framework and biological pathways from WikiPathways. Each mapping includes confidence assessments and connection type classifications to support toxicological research and systems biology applications.",
                    "description_type": "Abstract"
                },
                {
                    "description": "Data collection methodology: Mappings are created through expert curation using a guided confidence assessment workflow that evaluates biological relevance, evidence strength, pathway specificity, and functional independence. All submissions undergo validation and community review.",
                    "description_type": "Methods"
                }
            ],
            "geo_locations": [],
            "funding_references": [],
            "schema_version": "http://datacite.org/schema/kernel-4"
        }
    
    def get_current_metadata(self) -> Dict:
        """Get current dataset metadata with dynamic values"""
        # Update dynamic fields
        conn = self.db.get_connection()
        try:
            # Get current record count
            cursor = conn.execute("SELECT COUNT(*) as count FROM mappings")
            record_count = cursor.fetchone()["count"]
            
            # Get creation date range
            cursor = conn.execute("""
                SELECT MIN(created_at) as earliest, MAX(created_at) as latest 
                FROM mappings WHERE created_at IS NOT NULL
            """)
            date_range = cursor.fetchone()
            
            # Update metadata
            metadata = self.metadata.copy()
            metadata["sizes"] = [f"{record_count} mapping records"]
            
            if date_range["earliest"] and date_range["latest"]:
                # Update date information
                metadata["dates"] = [
                    {
                        "date": date_range["earliest"],
                        "date_type": "Created"
                    },
                    {
                        "date": date_range["latest"],
                        "date_type": "Updated"
                    },
                    {
                        "date": datetime.now().isoformat(),
                        "date_type": "Accessed"
                    }
                ]
            
            # Convert dataclass objects to dicts for JSON serialization
            metadata["creators"] = [asdict(creator) for creator in metadata["creators"]]
            metadata["subjects"] = [asdict(subject) for subject in metadata["subjects"]]
            metadata["related_identifiers"] = [asdict(ri) for ri in metadata["related_identifiers"]]
            metadata["contributors"] = [asdict(contrib) for contrib in metadata["contributors"]]
            
            return metadata
            
        finally:
            conn.close()
    
    def create_version(self, version: str, description: str, changes: List[str], created_by: Optional[str] = None) -> bool:
        """Create a new dataset version"""
        conn = self.db.get_connection()
        try:
            # Get current record count
            cursor = conn.execute("SELECT COUNT(*) as count FROM mappings")
            record_count = cursor.fetchone()["count"]
            
            # Get current metadata snapshot
            metadata_snapshot = self.get_current_metadata()
            
            # Create version record
            conn.execute("""
                INSERT INTO dataset_versions 
                (version, version_date, description, record_count, changes, created_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                version,
                datetime.now(),
                description,
                record_count,
                json.dumps(changes),
                created_by,
                json.dumps(metadata_snapshot, default=str)
            ))
            
            conn.commit()
            logger.info(f"Created dataset version {version}: {description}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating dataset version: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_versions(self) -> List[Dict]:
        """Get all dataset versions"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("""
                SELECT version, version_date, description, record_count, changes, created_by
                FROM dataset_versions 
                ORDER BY version_date DESC
            """)
            
            versions = []
            for row in cursor.fetchall():
                version_data = dict(row)
                if version_data["changes"]:
                    version_data["changes"] = json.loads(version_data["changes"])
                else:
                    version_data["changes"] = []
                versions.append(version_data)
            
            return versions
            
        finally:
            conn.close()
    
    def get_version_metadata(self, version: str) -> Optional[Dict]:
        """Get metadata for a specific version"""
        conn = self.db.get_connection()
        try:
            cursor = conn.execute("""
                SELECT metadata FROM dataset_versions WHERE version = ?
            """, (version,))
            
            row = cursor.fetchone()
            if row and row["metadata"]:
                return json.loads(row["metadata"])
            return None
            
        finally:
            conn.close()
    
    def export_datacite_xml(self) -> str:
        """Export metadata in DataCite XML format"""
        metadata = self.get_current_metadata()
        
        # Basic DataCite XML structure
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">')
        
        # Identifier
        if metadata["identifier"]["identifier"]:
            xml.append(f'  <identifier identifierType="{metadata["identifier"]["identifier_type"]}">{metadata["identifier"]["identifier"]}</identifier>')
        
        # Creators
        xml.append('  <creators>')
        for creator in metadata["creators"]:
            xml.append('    <creator>')
            xml.append(f'      <creatorName nameType="{creator["name_type"]}">{creator["name"]}</creatorName>')
            if creator.get("given_name") and creator.get("family_name"):
                xml.append(f'      <givenName>{creator["given_name"]}</givenName>')
                xml.append(f'      <familyName>{creator["family_name"]}</familyName>')
            xml.append('    </creator>')
        xml.append('  </creators>')
        
        # Titles
        xml.append('  <titles>')
        for title in metadata["titles"]:
            title_type = f' titleType="{title["title_type"]}"' if title.get("title_type") else ""
            xml.append(f'    <title{title_type}>{title["title"]}</title>')
        xml.append('  </titles>')
        
        # Publisher and Year
        xml.append(f'  <publisher>{metadata["publisher"]}</publisher>')
        xml.append(f'  <publicationYear>{metadata["publication_year"]}</publicationYear>')
        
        # Resource Type
        xml.append(f'  <resourceType resourceTypeGeneral="{metadata["resource_type"]["resource_type_general"]}">{metadata["resource_type"]["resource_type"]}</resourceType>')
        
        xml.append('</resource>')
        
        return '\n'.join(xml)
    
    def export_json_ld(self) -> str:
        """Export metadata in JSON-LD format for schema.org"""
        metadata = self.get_current_metadata()
        
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": metadata["titles"][0]["title"],
            "description": next(desc["description"] for desc in metadata["descriptions"] if desc["description_type"] == "Abstract"),
            "creator": [
                {
                    "@type": "Organization" if creator["name_type"] == "Organizational" else "Person",
                    "name": creator["name"]
                } for creator in metadata["creators"]
            ],
            "publisher": {
                "@type": "Organization",
                "name": metadata["publisher"]
            },
            "datePublished": str(metadata["publication_year"]),
            "keywords": [subject["subject"] for subject in metadata["subjects"]],
            "license": metadata["rights_list"][0]["rights_uri"] if metadata["rights_list"] else None,
            "inLanguage": metadata["language"],
            "size": metadata["sizes"][0] if metadata["sizes"] else None,
            "encodingFormat": metadata["formats"],
            "version": metadata["version"]
        }
        
        return json.dumps(json_ld, indent=2, ensure_ascii=False)
    
    def generate_citation(self, format_type: str = "apa") -> str:
        """Generate citation in specified format"""
        metadata = self.get_current_metadata()
        
        if format_type.lower() == "apa":
            creators = ", ".join([creator["name"] for creator in metadata["creators"]])
            title = metadata["titles"][0]["title"]
            year = metadata["publication_year"]
            publisher = metadata["publisher"]
            
            citation = f"{creators} ({year}). {title}. {publisher}."
            
            if metadata["identifier"]["identifier"]:
                citation += f" https://doi.org/{metadata['identifier']['identifier']}"
            
            return citation
        
        elif format_type.lower() == "bibtex":
            creators = " and ".join([creator["name"] for creator in metadata["creators"]])
            
            bibtex = f"""@dataset{{ke_wp_mappings_{metadata['publication_year']},
    author = {{{creators}}},
    title = {{{metadata['titles'][0]['title']}}},
    publisher = {{{metadata['publisher']}}},
    year = {{{metadata['publication_year']}}},
    version = {{{metadata['version']}}}"""
            
            if metadata["identifier"]["identifier"]:
                bibtex += f",\n    doi = {{{metadata['identifier']['identifier']}}}"
                
            bibtex += "\n}"
            
            return bibtex
        
        else:
            raise ValueError(f"Unsupported citation format: {format_type}")