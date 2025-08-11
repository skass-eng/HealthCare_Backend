#!/usr/bin/env python3
"""
Script de migration pour recréer la table services
Version: 2.0.0 - Architecture ODYSSEE - Modèle simplifié
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import SessionLocal, engine
from shared.models import Base, Service, Organisation
from sqlalchemy import text
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_services_table():
    """Recréer la table services avec le nouveau modèle simplifié"""
    
    db = SessionLocal()
    
    try:
        logger.info("🚀 Début de la migration de la table services...")
        
        # 1. Supprimer l'ancienne table services si elle existe
        logger.info("📋 Suppression de l'ancienne table services...")
        db.execute(text("DROP TABLE IF EXISTS services CASCADE"))
        db.commit()
        logger.info("✅ Ancienne table services supprimée")
        
        # 2. Recréer la table avec le nouveau modèle
        logger.info("📋 Création de la nouvelle table services...")
        Base.metadata.create_all(bind=engine, tables=[Service.__table__])
        logger.info("✅ Nouvelle table services créée")
        
        # 3. Créer l'organisation de base si elle n'existe pas
        logger.info("🏢 Vérification/création de l'organisation de base...")
        organisation = db.query(Organisation).filter(Organisation.id == 1).first()
        
        if not organisation:
            organisation = Organisation(
                id=1,
                nom="Centre Hospitalier Universitaire",
                code_etablissement="CHU001",
                est_actif=True,
                configuration={
                    "delai_reponse_standard": 30,
                    "services_actifs": [],
                    "workflow_automatique": True
                }
            )
            db.add(organisation)
            db.commit()
            db.refresh(organisation)
            logger.info(f"✅ Organisation créée: {organisation.nom} (ID: {organisation.id})")
        else:
            logger.info(f"✅ Organisation existante: {organisation.nom} (ID: {organisation.id})")
        
        # 4. Créer quelques services de test
        logger.info("🏥 Création de services de test...")
        
        services_test = [
            {
                "nom": "Cardiologie",
                "code_service": "CARDIO",
                "categorie": "SPECIALITE",
                "configuration": {
                    "email_contact": "cardiologie@chu-paris.fr",
                    "telephone_contact": "01 23 45 67 90"
                }
            },
            {
                "nom": "Urgences",
                "code_service": "URG",
                "categorie": "URGENCE",
                "configuration": {
                    "email_contact": "urgences@chu-paris.fr",
                    "telephone_contact": "01 23 45 67 91"
                }
            },
            {
                "nom": "Pédiatrie",
                "code_service": "PED",
                "categorie": "SPECIALITE",
                "configuration": {
                    "email_contact": "pediatrie@chu-paris.fr",
                    "telephone_contact": "01 23 45 67 92"
                }
            },
            {
                "nom": "Chirurgie",
                "code_service": "CHIR",
                "categorie": "CHIRURGIE",
                "configuration": {
                    "email_contact": "chirurgie@chu-paris.fr",
                    "telephone_contact": "01 23 45 67 93"
                }
            },
            {
                "nom": "Laboratoire",
                "code_service": "LABO",
                "categorie": "LABORATOIRE",
                "configuration": {
                    "email_contact": "laboratoire@chu-paris.fr",
                    "telephone_contact": "01 23 45 67 94"
                }
            }
        ]
        
        services_crees = []
        for service_data in services_test:
            service = Service(
                organisation_id=organisation.id,
                nom=service_data["nom"],
                code_service=service_data["code_service"],
                categorie=service_data["categorie"],
                configuration=service_data["configuration"],
                est_actif=True
            )
            db.add(service)
            services_crees.append(service)
        
        db.commit()
        logger.info(f"✅ {len(services_crees)} services de test créés")
        
        # 5. Vérifier la structure de la table
        logger.info("🔍 Vérification de la structure de la table...")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'services' 
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        logger.info("📋 Structure de la table services:")
        for column in columns:
            logger.info(f"   - {column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
        
        # 6. Vérifier les données
        services_count = db.query(Service).count()
        logger.info(f"📊 Nombre total de services: {services_count}")
        
        logger.info("🎉 Migration terminée avec succès!")
        
        return {
            "success": True,
            "message": "Migration terminée avec succès",
            "services_crees": len(services_crees),
            "total_services": services_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Architecture ODYSSEE    ║
    ║           Migration Services Table            ║
    ║                                               ║
    ║  Recréation de la table services v2.0.0      ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    try:
        result = migrate_services_table()
        print(f"\n✅ Migration réussie!")
        print(f"📊 Services créés: {result['services_crees']}")
        print(f"📊 Total services: {result['total_services']}")
        print("\n🌐 L'API est maintenant prête à recevoir des requêtes!")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        sys.exit(1) 