#!/usr/bin/env python3
"""
Script pour ajouter la colonne description à la table services
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from healthcare_api_server.app.core.config import settings

def add_description_column():
    """Ajouter la colonne description à la table services"""
    
    # Utiliser l'URL de base de données depuis la configuration
    database_url = str(settings.DATABASE_URL)
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Vérifier si la colonne existe déjà
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'services' AND column_name = 'description'
            """))
            
            if result.fetchone():
                print("✅ La colonne 'description' existe déjà dans la table services")
                return
            
            # Ajouter la colonne description
            conn.execute(text("""
                ALTER TABLE services 
                ADD COLUMN description TEXT
            """))
            
            conn.commit()
            print("✅ Colonne 'description' ajoutée avec succès à la table services")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de la colonne: {e}")
        raise

if __name__ == "__main__":
    print("🔄 Ajout de la colonne description à la table services...")
    add_description_column()
    print("✅ Script terminé avec succès") 