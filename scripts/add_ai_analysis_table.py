#!/usr/bin/env python3
"""
Script de migration pour ajouter la table ai_analysis_results
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from shared.models import Base, AIAnalysisResult

# Configuration de la base de données
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/healthcare_plaintes"
)

def create_ai_analysis_table():
    """Créer la table ai_analysis_results si elle n'existe pas"""
    
    print("🚀 Création de la table ai_analysis_results...")
    
    engine = create_engine(DATABASE_URL)
    
    # Vérifier si la table existe déjà
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ai_analysis_results'
            );
        """))
        exists = result.scalar()
        
        if exists:
            print("✅ La table ai_analysis_results existe déjà")
            return
    
    # Créer la table
    try:
        AIAnalysisResult.__table__.create(engine)
        print("✅ Table ai_analysis_results créée avec succès!")
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        
        # Alternative: créer avec SQL brut
        print("🔄 Tentative avec SQL brut...")
        
        create_sql = """
        CREATE TABLE IF NOT EXISTS ai_analysis_results (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR(100) UNIQUE NOT NULL,
            total_plaintes_analysees INTEGER DEFAULT 0,
            nombre_services INTEGER DEFAULT 0,
            model_used VARCHAR(100),
            analyses_par_service JSONB,
            causes_globales JSONB,
            services_critiques JSONB,
            status VARCHAR(50) DEFAULT 'completed',
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            duree_secondes FLOAT
        );
        
        CREATE INDEX IF NOT EXISTS idx_ai_analysis_date ON ai_analysis_results(completed_at);
        CREATE INDEX IF NOT EXISTS idx_ai_analysis_status ON ai_analysis_results(status);
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()
            print("✅ Table créée avec SQL brut!")

if __name__ == "__main__":
    create_ai_analysis_table()
