"""
Migration script to move data from CSV to SQLite database
"""
import pandas as pd
import os
from models import Database, MappingModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_csv_to_db():
    """Migrate existing CSV data to SQLite database"""
    if not os.path.exists("dataset.csv"):
        logger.info("No CSV file found, skipping migration")
        return
    
    # Initialize database
    db = Database()
    mapping_model = MappingModel(db)
    
    try:
        # Read CSV data
        df = pd.read_csv("dataset.csv")
        logger.info(f"Found {len(df)} records in CSV")
        
        migrated_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            # Handle different CSV formats that might exist
            ke_id = row.get('KE_ID', '')
            ke_title = row.get('KE_Title', row.get('ke_title', ''))
            wp_id = row.get('WP_ID', '')
            wp_title = row.get('WP_Title', row.get('wp_title', ''))
            connection_type = row.get('Connection_Type', row.get('connection_type', 'undefined'))
            confidence_level = row.get('Confidence_Level', row.get('confidence_level', 'low'))
            
            # Skip if essential data is missing
            if not all([ke_id, wp_id]):
                logger.warning(f"Skipping row with missing data: KE={ke_id}, WP={wp_id}")
                skipped_count += 1
                continue
            
            # Try to create mapping
            mapping_id = mapping_model.create_mapping(
                ke_id=ke_id,
                ke_title=ke_title or f"KE {ke_id}",
                wp_id=wp_id,
                wp_title=wp_title or f"WP {wp_id}",
                connection_type=connection_type,
                confidence_level=confidence_level,
                created_by="csv_migration"
            )
            
            if mapping_id:
                migrated_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"Migration completed: {migrated_count} migrated, {skipped_count} skipped")
        
        # Create backup of CSV
        if migrated_count > 0:
            backup_name = "dataset.csv.backup"
            os.rename("dataset.csv", backup_name)
            logger.info(f"CSV backed up as {backup_name}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_csv_to_db()