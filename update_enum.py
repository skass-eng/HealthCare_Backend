#!/usr/bin/env python3
"""
Script pour mettre à jour l'enum StatutPlainteEnum dans PostgreSQL
avant la migration des données
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import settings

def update_enum():
    """Mettre à jour l'enum StatutPlainteEnum dans PostgreSQL"""
    
    # Créer la connexion à la base de données
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            print("🚀 Mise à jour de l'enum StatutPlainteEnum...")
            
            # Désactiver les contraintes de clés étrangères temporairement
            conn.execute(text("SET session_replication_role = replica;"))
            
            # Ajouter les nouvelles valeurs à l'enum
            print("📝 Ajout des nouvelles valeurs à l'enum...")
            conn.execute(text("ALTER TYPE statutplainteenum ADD VALUE IF NOT EXISTS 'RECU';"))
            conn.execute(text("ALTER TYPE statutplainteenum ADD VALUE IF NOT EXISTS 'TRAITE';"))
            conn.execute(text("ALTER TYPE statutplainteenum ADD VALUE IF NOT EXISTS 'CLOTURE';"))
            
            # Réactiver les contraintes
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            
            # Valider les changements
            conn.commit()
            
            print("✅ Enum mis à jour avec succès!")
            
            # Vérifier les valeurs disponibles
            result = conn.execute(text("SELECT unnest(enum_range(NULL::statutplainteenum)) as values;"))
            values = [row[0] for row in result]
            print(f"📊 Valeurs disponibles dans l'enum: {values}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour de l'enum: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    update_enum() 