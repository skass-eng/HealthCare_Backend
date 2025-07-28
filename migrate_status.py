#!/usr/bin/env python3
"""
Script de migration pour mettre à jour les statuts des plaintes
de l'ancien système (8 statuts) vers le nouveau système (4 statuts)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models_unified import Base, Plainte, StatutPlainteEnum
from config import settings

def migrate_status():
    """Migrer les statuts des plaintes vers le nouveau système"""
    
    # Créer la connexion à la base de données
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        try:
            print("🚀 Début de la migration des statuts...")
            
            # Mapping des anciens statuts vers les nouveaux
            status_mapping = {
                'NOUVELLE': 'RECU',
                'EN_ATTENTE_INFORMATION': 'RECU',
                'EN_COURS': 'EN_COURS',
                'EN_COURS_TRAITEMENT': 'EN_COURS',
                'TRAITEE': 'TRAITE',
                'RESOLUE': 'TRAITE',
                'FERMEE': 'CLOTURE',
                'ARCHIVEE': 'CLOTURE'
            }
            
            # Compter les plaintes par ancien statut
            print("📊 Statistiques avant migration:")
            for old_status in status_mapping.keys():
                count = db.query(Plainte).filter(Plainte.statut == old_status).count()
                if count > 0:
                    print(f"  - {old_status}: {count} plaintes")
            
            # Effectuer la migration
            total_migrated = 0
            for old_status, new_status in status_mapping.items():
                # Mettre à jour les plaintes avec l'ancien statut
                result = db.execute(
                    text("UPDATE plaintes SET statut = :new_status WHERE statut = :old_status"),
                    {"new_status": new_status, "old_status": old_status}
                )
                migrated_count = result.rowcount
                if migrated_count > 0:
                    print(f"✅ Migré {migrated_count} plaintes de '{old_status}' vers '{new_status}'")
                    total_migrated += migrated_count
            
            # Valider les changements
            db.commit()
            
            print(f"\n🎉 Migration terminée! {total_migrated} plaintes migrées.")
            
            # Afficher les nouvelles statistiques
            print("\n📊 Statistiques après migration:")
            for status in ['RECU', 'EN_COURS', 'TRAITE', 'CLOTURE']:
                count = db.query(Plainte).filter(Plainte.statut == status).count()
                print(f"  - {status}: {count} plaintes")
            
        except Exception as e:
            print(f"❌ Erreur lors de la migration: {e}")
            db.rollback()
            raise
        finally:
            db.close()

if __name__ == "__main__":
    migrate_status() 