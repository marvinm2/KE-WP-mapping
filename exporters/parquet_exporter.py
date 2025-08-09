"""
Parquet export functionality for big data analytics and research workflows
"""
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ParquetExporter:
    """Export dataset in Apache Parquet format for analytics"""
    
    def __init__(self, database, metadata_manager):
        self.db = database
        self.metadata = metadata_manager
    
    def export(self, include_metadata_columns: bool = True, compression: str = "snappy") -> bytes:
        """Export dataset to Parquet format"""
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ImportError("pandas and pyarrow are required for Parquet export. Install with: pip install pandas pyarrow")
        
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
            
            if not mappings:
                # Create empty DataFrame with correct schema
                df = pd.DataFrame(columns=[
                    'id', 'ke_id', 'ke_title', 'wp_id', 'wp_title',
                    'connection_type', 'confidence_level', 'created_by', 
                    'created_at', 'updated_at'
                ])
            else:
                # Create DataFrame from mappings
                df = pd.DataFrame(mappings)
                
                # Data type optimization
                df = self._optimize_data_types(df)
            
            # Add metadata columns if requested
            if include_metadata_columns:
                df = self._add_metadata_columns(df)
            
            # Create Parquet schema with metadata
            schema = self._create_parquet_schema(df)
            
            # Convert DataFrame to PyArrow Table with schema
            table = pa.Table.from_pandas(df, schema=schema)
            
            # Add custom metadata to the table
            table = table.replace_schema_metadata(self._create_parquet_metadata())
            
            # Write to bytes buffer
            output = io.BytesIO()
            pq.write_table(
                table, 
                output, 
                compression=compression,
                write_statistics=True,
                use_dictionary=True  # Enable dictionary encoding for better compression
            )
            output.seek(0)
            
            logger.info(f"Exported {len(mappings)} mappings to Parquet format with {compression} compression")
            return output.getvalue()
            
        finally:
            conn.close()
    
    def _optimize_data_types(self, df) -> 'pd.DataFrame':
        """Optimize DataFrame data types for efficient storage"""
        import pandas as pd
        
        # Convert string columns to category for better compression
        categorical_columns = ['connection_type', 'confidence_level', 'created_by']
        for col in categorical_columns:
            if col in df.columns and not df[col].isna().all():
                df[col] = df[col].astype('category')
        
        # Convert datetime columns
        datetime_columns = ['created_at', 'updated_at']
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Optimize integer columns
        if 'id' in df.columns:
            df['id'] = df['id'].astype('Int32')  # Use nullable integer
        
        # Ensure string columns are optimized
        string_columns = ['ke_id', 'ke_title', 'wp_id', 'wp_title']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype('string')
        
        return df
    
    def _add_metadata_columns(self, df) -> 'pd.DataFrame':
        """Add metadata columns for enhanced analytics"""
        import pandas as pd
        
        # Add export metadata
        df['export_timestamp'] = datetime.now()
        df['dataset_version'] = self.metadata.metadata.get("version", "1.0.0")
        
        # Extract numeric IDs for analytics
        if 'ke_id' in df.columns:
            df['ke_numeric_id'] = df['ke_id'].str.extract(r'KE\s+(\d+)').astype('Int32')
        
        if 'wp_id' in df.columns:
            df['wp_numeric_id'] = df['wp_id'].str.extract(r'WP(\d+)').astype('Int32')
        
        # Add confidence level as numeric for easier analysis
        confidence_mapping = {'low': 1, 'medium': 2, 'high': 3}
        if 'confidence_level' in df.columns:
            df['confidence_numeric'] = df['confidence_level'].map(confidence_mapping)
        
        # Add connection type as numeric
        connection_mapping = {'undefined': 0, 'other': 1, 'responsive': 2, 'causative': 3}
        if 'connection_type' in df.columns:
            df['connection_numeric'] = df['connection_type'].map(connection_mapping)
        
        # Add derived temporal features
        if 'created_at' in df.columns:
            df['created_year'] = pd.to_datetime(df['created_at'], errors='coerce').dt.year
            df['created_month'] = pd.to_datetime(df['created_at'], errors='coerce').dt.month
            df['created_day_of_week'] = pd.to_datetime(df['created_at'], errors='coerce').dt.dayofweek
        
        # Add text length metrics for analysis
        if 'ke_title' in df.columns:
            df['ke_title_length'] = df['ke_title'].str.len()
        
        if 'wp_title' in df.columns:
            df['wp_title_length'] = df['wp_title'].str.len()
        
        return df
    
    def _create_parquet_schema(self, df) -> 'pa.Schema':
        """Create PyArrow schema with field metadata"""
        import pyarrow as pa
        import pandas as pd
        
        # Get basic schema from DataFrame
        schema = pa.Schema.from_pandas(df)
        
        # Add field-level metadata
        field_metadata = {
            'id': {'description': 'Unique mapping identifier', 'unit': 'count'},
            'ke_id': {'description': 'Key Event identifier from AOP-Wiki', 'format': 'KE XXXX'},
            'ke_title': {'description': 'Full title of the Key Event', 'type': 'free_text'},
            'wp_id': {'description': 'WikiPathways pathway identifier', 'format': 'WPXXXX'},
            'wp_title': {'description': 'Full title of the WikiPathways pathway', 'type': 'free_text'},
            'connection_type': {
                'description': 'Biological relationship type between KE and pathway',
                'values': 'causative,responsive,other,undefined'
            },
            'confidence_level': {
                'description': 'Confidence in mapping based on evidence strength',
                'values': 'low,medium,high'
            },
            'created_by': {'description': 'Username of mapping creator', 'type': 'identifier'},
            'created_at': {'description': 'Mapping creation timestamp', 'format': 'ISO8601'},
            'updated_at': {'description': 'Last modification timestamp', 'format': 'ISO8601'},
            'export_timestamp': {'description': 'Parquet export timestamp', 'format': 'ISO8601'},
            'dataset_version': {'description': 'Dataset version at export time', 'format': 'semantic_version'},
            'ke_numeric_id': {'description': 'Numeric Key Event ID for analytics', 'derived_from': 'ke_id'},
            'wp_numeric_id': {'description': 'Numeric WikiPathway ID for analytics', 'derived_from': 'wp_id'},
            'confidence_numeric': {
                'description': 'Numeric confidence level (1=low, 2=medium, 3=high)',
                'mapping': 'low:1,medium:2,high:3'
            },
            'connection_numeric': {
                'description': 'Numeric connection type (0=undefined, 1=other, 2=responsive, 3=causative)',
                'mapping': 'undefined:0,other:1,responsive:2,causative:3'
            },
            'created_year': {'description': 'Year of mapping creation', 'derived_from': 'created_at'},
            'created_month': {'description': 'Month of mapping creation (1-12)', 'derived_from': 'created_at'},
            'created_day_of_week': {'description': 'Day of week for creation (0=Monday)', 'derived_from': 'created_at'},
            'ke_title_length': {'description': 'Character length of KE title', 'unit': 'characters'},
            'wp_title_length': {'description': 'Character length of pathway title', 'unit': 'characters'}
        }
        
        # Create new schema with metadata
        new_fields = []
        for field in schema:
            metadata = field_metadata.get(field.name, {})
            new_field = field.with_metadata(metadata)
            new_fields.append(new_field)
        
        return pa.schema(new_fields)
    
    def _create_parquet_metadata(self) -> Dict[str, str]:
        """Create table-level metadata for Parquet file"""
        dataset_metadata = self.metadata.get_current_metadata()
        
        # Convert metadata to string format for Parquet
        parquet_metadata = {
            'title': dataset_metadata["titles"][0]["title"],
            'description': next((d["description"] for d in dataset_metadata["descriptions"] 
                               if d["description_type"] == "Abstract"), ""),
            'creator': ', '.join([c["name"] for c in dataset_metadata["creators"]]),
            'publisher': dataset_metadata["publisher"],
            'version': dataset_metadata["version"],
            'publication_year': str(dataset_metadata["publication_year"]),
            'license': dataset_metadata["rights_list"][0]["rights"] if dataset_metadata["rights_list"] else "",
            'license_uri': dataset_metadata["rights_list"][0]["rights_uri"] if dataset_metadata["rights_list"] else "",
            'language': dataset_metadata["language"],
            'subjects': ', '.join([s["subject"] for s in dataset_metadata["subjects"]]),
            'export_timestamp': datetime.now().isoformat(),
            'format': 'Apache Parquet',
            'created_by': 'KE-WP Mapping Platform Export System',
            'schema_version': 'KE-WP-v1.0',
            'data_structure': 'tabular',
            'compression': 'snappy',
            'encoding': 'UTF-8'
        }
        
        # Add related identifiers
        related_urls = [ri["related_identifier"] for ri in dataset_metadata["related_identifiers"]]
        parquet_metadata['related_resources'] = ', '.join(related_urls)
        
        return parquet_metadata
    
    def get_schema_info(self) -> Dict:
        """Get schema information for documentation"""
        return {
            "format": "Apache Parquet",
            "compression": "snappy (default)",
            "features": [
                "Optimized data types for storage efficiency",
                "Dictionary encoding for categorical data",
                "Statistical metadata for query optimization", 
                "Field-level metadata and descriptions",
                "Derived columns for enhanced analytics",
                "Temporal feature extraction",
                "Numeric encodings for categorical variables"
            ],
            "analytics_enhancements": [
                "Numeric IDs extracted from text identifiers",
                "Confidence levels as both categorical and numeric",
                "Connection types as both categorical and numeric",
                "Temporal features (year, month, day of week)",
                "Text length metrics for title analysis",
                "Export metadata for provenance tracking"
            ],
            "recommended_tools": [
                "Apache Spark for large-scale analytics",
                "pandas for data manipulation",
                "Apache Arrow for cross-language compatibility",
                "DuckDB for analytical SQL queries",
                "R arrow package for R integration"
            ]
        }