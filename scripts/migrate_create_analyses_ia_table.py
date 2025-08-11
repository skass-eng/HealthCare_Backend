#!/usr/bin/env python3
"""
MIGRATION - Création de la table analyses_ia pour stocker les résultats d'IA
Migration pour créer une table dédiée aux analyses IA des plaintes
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
    Créer la table analyses_ia pour stocker les résultats d'analyse IA
    """
    # Convertir l'URL de base de données en chaîne
    database_url = str(settings.DATABASE_URL)
    engine = create_engine(database_url)
    
    # SQL pour créer la table analyses_ia
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS analyses_ia (
        id SERIAL PRIMARY KEY,
        plainte_id INTEGER REFERENCES plaintes(id) ON DELETE CASCADE,
        
        -- Analyse de sentiment
        sentiment VARCHAR(50),
        score_sentiment FLOAT,
        confiance_sentiment FLOAT,
        
        -- Classification par service
        service_suggere VARCHAR(255),
        score_service FLOAT,
        confiance_service FLOAT,
        
        -- Priorité IA
        priorite_ia VARCHAR(50),
        score_priorite FLOAT,
        urgence_detectee BOOLEAN DEFAULT FALSE,
        
        -- Résumé et réponse IA
        resume_ia TEXT,
        reponse_suggeree TEXT,
        mots_cles_detectes TEXT[], -- Array de mots-clés
        
        -- Métadonnées d'analyse
        modele_utilise VARCHAR(100),
        version_modele VARCHAR(50),
        temps_traitement FLOAT, -- en secondes
        statut_analyse VARCHAR(50) DEFAULT 'en_cours',
        
        -- Timestamps
        date_analyse TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_mise_a_jour TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        UNIQUE(plainte_id) -- Une seule analyse par plainte
    );
    """
    
    # Indexes pour optimiser les requêtes
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_analyses_ia_plainte_id ON analyses_ia(plainte_id);",
        "CREATE INDEX IF NOT EXISTS idx_analyses_ia_sentiment ON analyses_ia(sentiment);",
        "CREATE INDEX IF NOT EXISTS idx_analyses_ia_service_suggere ON analyses_ia(service_suggere);",
        "CREATE INDEX IF NOT EXISTS idx_analyses_ia_priorite ON analyses_ia(priorite_ia);",
        "CREATE INDEX IF NOT EXISTS idx_analyses_ia_date ON analyses_ia(date_analyse);",
    ]
    
    try:
        with engine.connect() as connection:
            logger.info("🚀 Début de la migration - Création table analyses_ia")
            
            # Créer la table
            logger.info("Création de la table analyses_ia...")
            connection.execute(text(create_table_sql))
            connection.commit()
            logger.info("✅ Table analyses_ia créée avec succès")
            
            # Créer les indexes
            for index_sql in indexes_sql:
                logger.info(f"Création d'index...")
                connection.execute(text(index_sql))
                connection.commit()
                logger.info("✅ Index créé avec succès")
            
            logger.info("✅ Migration terminée avec succès")
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == "__main__":
    run_migration()
