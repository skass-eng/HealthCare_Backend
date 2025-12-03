#!/usr/bin/env python3
"""
Script de migration pour ajouter les colonnes reponse_manuelle et date_reponse
à la table plaintes.

Exécution: python scripts/add_reponse_columns.py
"""

import sys
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import text
from healthcare_api_server.app.db.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Ajouter les colonnes reponse_manuelle et date_reponse à la table plaintes"""
    
    with engine.connect() as conn:
        # Vérifier si la colonne reponse_manuelle existe déjà
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'plaintes' AND column_name = 'reponse_manuelle'
        """))
        
        if result.fetchone():
            logger.info("✅ La colonne 'reponse_manuelle' existe déjà")
        else:
            logger.info("🔄 Ajout de la colonne 'reponse_manuelle'...")
            conn.execute(text("""
                ALTER TABLE plaintes 
                ADD COLUMN reponse_manuelle TEXT
            """))
            logger.info("✅ Colonne 'reponse_manuelle' ajoutée avec succès")
        
        # Vérifier si la colonne date_reponse existe déjà
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'plaintes' AND column_name = 'date_reponse'
        """))
        
        if result.fetchone():
            logger.info("✅ La colonne 'date_reponse' existe déjà")
        else:
            logger.info("🔄 Ajout de la colonne 'date_reponse'...")
            conn.execute(text("""
                ALTER TABLE plaintes 
                ADD COLUMN date_reponse TIMESTAMP
            """))
            logger.info("✅ Colonne 'date_reponse' ajoutée avec succès")
        
        conn.commit()
        logger.info("🎉 Migration terminée avec succès!")

if __name__ == "__main__":
    migrate()
