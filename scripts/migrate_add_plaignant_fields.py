#!/usr/bin/env python3
"""
MIGRATION - Ajout des champs plaignant à la table plaintes
Migration pour ajouter les nouveaux champs plaignant nécessaires pour la création de plaintes
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from healthcare_api_server.app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """
    Ajouter les champs plaignant à la table plaintes
    """
    # Convertir l'URL de base de données en chaîne
    database_url = str(settings.DATABASE_URL)
    engine = create_engine(database_url)
    
    # Liste des colonnes à ajouter
    columns_to_add = [
        "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS nom_plaignant VARCHAR(255);",
        "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS prenom_plaignant VARCHAR(255);",
        "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS email_plaignant VARCHAR(255);",
        "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS telephone_plaignant VARCHAR(50);",
        "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS mode_reception VARCHAR(50) DEFAULT 'manuel';"
    ]
    
    try:
        with engine.connect() as connection:
            logger.info("🚀 Début de la migration - Ajout des champs plaignant")
            
            for sql in columns_to_add:
                try:
                    logger.info(f"Exécution: {sql}")
                    connection.execute(text(sql))
                    connection.commit()
                    logger.info("✅ Colonne ajoutée avec succès")
                except Exception as e:
                    if "already exists" in str(e):
                        logger.info("ℹ️ Colonne déjà existante, ignorée")
                    else:
                        logger.error(f"❌ Erreur lors de l'ajout de la colonne: {e}")
                        raise
            
            logger.info("✅ Migration terminée avec succès")
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == "__main__":
    run_migration()
