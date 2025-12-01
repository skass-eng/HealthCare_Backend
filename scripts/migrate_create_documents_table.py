#!/usr/bin/env python3
"""
Script de migration pour créer la table documents_plaintes
Cette table permet de lier les fichiers attachés aux plaintes
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from shared.models import Base, DocumentPlainte
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/healthcare_db"
)

def run_migration():
    """Exécute la migration pour créer la table documents_plaintes"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # Vérifier si la table existe déjà
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'documents_plaintes'
                )
            """))
            table_exists = result.scalar()
        
        if table_exists:
            logger.info("✅ La table 'documents_plaintes' existe déjà")
            return True
        
        # Créer la table
        logger.info("🔄 Création de la table 'documents_plaintes'...")
        
        # SQL de création de la table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS documents_plaintes (
            id SERIAL PRIMARY KEY,
            plainte_id BIGINT NOT NULL REFERENCES plaintes(id) ON DELETE CASCADE,
            nom_fichier VARCHAR(255) NOT NULL,
            nom_stockage VARCHAR(500) NOT NULL,
            chemin_fichier VARCHAR(1000) NOT NULL,
            type_fichier VARCHAR(20) DEFAULT 'AUTRE',
            taille_fichier BIGINT,
            mime_type VARCHAR(100),
            description TEXT,
            est_piece_jointe_originale BOOLEAN DEFAULT TRUE,
            date_upload TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            date_modification TIMESTAMP
        );
        
        -- Index pour performance
        CREATE INDEX IF NOT EXISTS idx_document_plainte ON documents_plaintes(plainte_id);
        CREATE INDEX IF NOT EXISTS idx_document_type ON documents_plaintes(type_fichier);
        
        -- Commentaires
        COMMENT ON TABLE documents_plaintes IS 'Documents attachés aux plaintes';
        COMMENT ON COLUMN documents_plaintes.nom_fichier IS 'Nom original du fichier uploadé';
        COMMENT ON COLUMN documents_plaintes.nom_stockage IS 'Nom du fichier sur le disque (avec préfixe plainte)';
        COMMENT ON COLUMN documents_plaintes.chemin_fichier IS 'Chemin complet vers le fichier';
        COMMENT ON COLUMN documents_plaintes.est_piece_jointe_originale IS 'True si uploadé lors de la création de la plainte';
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        logger.info("✅ Table 'documents_plaintes' créée avec succès!")
        
        # Vérifier la création
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'documents_plaintes'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            logger.info("📋 Colonnes de la table:")
            for col_name, col_type in columns:
                logger.info(f"   - {col_name}: {col_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
