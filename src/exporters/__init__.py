"""
Data export handlers for multiple formats
Supports JSON, RDF, Excel, Parquet, and other research data formats
"""
from .json_exporter import JSONExporter
from .rdf_exporter import RDFExporter
from .excel_exporter import ExcelExporter
from .parquet_exporter import ParquetExporter

__all__ = [
    'JSONExporter',
    'RDFExporter', 
    'ExcelExporter',
    'ParquetExporter'
]


class ExportManager:
    """Central manager for all export operations"""
    
    def __init__(self, database, metadata_manager):
        self.db = database
        self.metadata = metadata_manager
        self.exporters = {
            'json': JSONExporter(database, metadata_manager),
            'jsonld': JSONExporter(database, metadata_manager),
            'rdf': RDFExporter(database, metadata_manager),
            'turtle': RDFExporter(database, metadata_manager),
            'excel': ExcelExporter(database, metadata_manager),
            'parquet': ParquetExporter(database, metadata_manager)
        }
    
    def get_available_formats(self):
        """Get list of available export formats"""
        return list(self.exporters.keys())
    
    def export(self, format_name, **kwargs):
        """Export data in specified format"""
        if format_name not in self.exporters:
            raise ValueError(f"Unsupported export format: {format_name}")
        
        exporter = self.exporters[format_name]
        
        # Handle format variations
        if format_name == 'jsonld':
            return exporter.export_json_ld(**kwargs)
        elif format_name == 'turtle':
            return exporter.export_turtle(**kwargs)
        else:
            return exporter.export(**kwargs)
    
    def get_content_type(self, format_name):
        """Get appropriate content type for format"""
        content_types = {
            'json': 'application/json',
            'jsonld': 'application/ld+json',
            'rdf': 'application/rdf+xml',
            'turtle': 'text/turtle',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'parquet': 'application/octet-stream'
        }
        return content_types.get(format_name, 'application/octet-stream')
    
    def get_file_extension(self, format_name):
        """Get appropriate file extension for format"""
        extensions = {
            'json': 'json',
            'jsonld': 'jsonld',
            'rdf': 'rdf',
            'turtle': 'ttl',
            'excel': 'xlsx',
            'parquet': 'parquet'
        }
        return extensions.get(format_name, 'txt')