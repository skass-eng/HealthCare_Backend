#!/usr/bin/env python3
"""
Migration: Renommer colonne analyse_ia en analyse_ia_legacy
Ajout de la nouvelle table analyses_ia déjà créée
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text, MetaData, inspect
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au PYTHONPATH pour les imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:odyssee2024@localhost:5432/healthcare_complaints_db"

def main():
    """
    Migration principale
    """
    try:
        # Créer le moteur de base de données
        engine = create_engine(DATABASE_URL)
        
        # Vérifier la connexion
        with engine.connect() as conn:
            logger.info("✅ Connexion à la base de données établie")
            
            # Vérifier si la colonne analyse_ia existe
            inspector = inspect(engine)
            columns = inspector.get_columns('plaintes')
            column_names = [col['name'] for col in columns]
            
            if 'analyse_ia' in column_names:
                logger.info("🔄 Renommage de la colonne analyse_ia en analyse_ia_legacy")
                
                # Renommer la colonne
                conn.execute(text("""
                    ALTER TABLE plaintes 
                    RENAME COLUMN analyse_ia TO analyse_ia_legacy;
                """))
                
                conn.commit()
                logger.info("✅ Colonne renommée avec succès")
                
            elif 'analyse_ia_legacy' in column_names:
                logger.info("ℹ️ La colonne analyse_ia_legacy existe déjà")
            else:
                logger.info("ℹ️ Aucune colonne analyse_ia trouvée, création de analyse_ia_legacy")
                
                # Créer la colonne si elle n'existe pas
                conn.execute(text("""
                    ALTER TABLE plaintes 
                    ADD COLUMN IF NOT EXISTS analyse_ia_legacy JSONB DEFAULT '{}';
                """))
                
                conn.commit()
                logger.info("✅ Colonne analyse_ia_legacy créée")
            
            # Vérifier que la table analyses_ia existe
            tables = inspector.get_table_names()
            if 'analyses_ia' not in tables:
                logger.warning("⚠️ La table analyses_ia n'existe pas encore")
                logger.info("Veuillez exécuter la migration migrate_create_analyses_ia_table.py d'abord")
            else:
                logger.info("✅ Table analyses_ia trouvée")
            
            # Vérifier les colonnes finales
            final_columns = inspector.get_columns('plaintes')
            final_column_names = [col['name'] for col in final_columns]
            
            logger.info("📋 Colonnes dans la table plaintes:")
            for col in final_column_names:
                if 'analyse' in col.lower():
                    logger.info(f"   - {col}")
            
            logger.info("🎉 Migration terminée avec succès!")
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == "__main__":
    main()
