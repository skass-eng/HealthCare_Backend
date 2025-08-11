#!/usr/bin/env python3
"""
Script de migration pour supprimer la colonne organisation_id de la table services
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import engine
from sqlalchemy import text

def migrate_remove_organisation_id():
    """Supprimer la colonne organisation_id de la table services"""
    
    try:
        with engine.connect() as connection:
            # Vérifier si la colonne organisation_id existe
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'services' 
                AND column_name = 'organisation_id'
            """))
            
            if result.fetchone():
                print("🔧 Suppression de la colonne organisation_id...")
                
                # Supprimer la colonne organisation_id
                connection.execute(text("ALTER TABLE services DROP COLUMN IF EXISTS organisation_id"))
                connection.commit()
                
                print("✅ Colonne organisation_id supprimée avec succès")
            else:
                print("✅ La colonne organisation_id n'existe pas (déjà supprimée)")
                
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Début de la migration: suppression de organisation_id")
    migrate_remove_organisation_id()
    print("✅ Migration terminée") 