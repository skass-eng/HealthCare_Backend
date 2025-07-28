#!/usr/bin/env python3
"""
Script pour nettoyer l'enum StatutPlainteEnum en supprimant les anciennes valeurs
après la migration des données
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import settings

def cleanup_enum():
    """Nettoyer l'enum StatutPlainteEnum en supprimant les anciennes valeurs"""
    
    # Créer la connexion à la base de données
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            print("🧹 Nettoyage de l'enum StatutPlainteEnum...")
            
            # Vérifier les valeurs actuelles
            result = conn.execute(text("SELECT unnest(enum_range(NULL::statutplainteenum)) as values;"))
            current_values = [row[0] for row in result]
            print(f"📊 Valeurs actuelles: {current_values}")
            
            # Créer un nouvel enum avec seulement les 4 valeurs souhaitées
            print("🔄 Création du nouvel enum...")
            
            # Créer le nouvel enum
            conn.execute(text("CREATE TYPE statutplainteenum_new AS ENUM ('RECU', 'EN_COURS', 'TRAITE', 'CLOTURE');"))
            
            # Mettre à jour la colonne pour utiliser le nouvel enum
            conn.execute(text("ALTER TABLE plaintes ALTER COLUMN statut TYPE statutplainteenum_new USING statut::text::statutplainteenum_new;"))
            
            # Supprimer l'ancien enum
            conn.execute(text("DROP TYPE statutplainteenum;"))
            
            # Renommer le nouvel enum
            conn.execute(text("ALTER TYPE statutplainteenum_new RENAME TO statutplainteenum;"))
            
            # Valider les changements
            conn.commit()
            
            print("✅ Enum nettoyé avec succès!")
            
            # Vérifier les valeurs finales
            result = conn.execute(text("SELECT unnest(enum_range(NULL::statutplainteenum)) as values;"))
            final_values = [row[0] for row in result]
            print(f"📊 Valeurs finales: {final_values}")
            
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage de l'enum: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    cleanup_enum() 