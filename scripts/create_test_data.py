#!/usr/bin/env python3
"""
SCRIPT DE CRÉATION DE DONNÉES DE TEST - HealthCare AI Architecture ODYSSEE
Création d'organisations et services de test pour le développement
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
import logging
from datetime import datetime

# Ajouter le chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import SessionLocal
from shared.models import Organisation, Service, User, UserRole
from sqlalchemy.orm import sessionmaker

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Créer des données de test pour le développement"""
    
    # Créer une session de base de données
    db = SessionLocal()
    
    try:
        logger.info("🚀 Création des données de test...")
        
        # 1. Créer des organisations de test
        organisations = [
            {
                "nom": "Centre Hospitalier Universitaire de Paris",
                "code_etablissement": "CHU-PARIS-001",
                "configuration": {
                    "delai_reponse_standard": 30,
                    "services_actifs": ["CARDIOLOGIE", "URGENCES", "PEDIATRIE"],
                    "workflow_automatique": True
                }
            },
            {
                "nom": "Hôpital Général de Lyon",
                "code_etablissement": "HOP-LYON-002",
                "configuration": {
                    "delai_reponse_standard": 25,
                    "services_actifs": ["CHIRURGIE", "NEUROLOGIE", "GYNECOLOGIE"],
                    "workflow_automatique": True
                }
            },
            {
                "nom": "Clinique Spécialisée de Marseille",
                "code_etablissement": "CLIN-MARSEILLE-003",
                "configuration": {
                    "delai_reponse_standard": 20,
                    "services_actifs": ["DERMATOLOGIE", "ORTHOPEDIE", "PSYCHIATRIE"],
                    "workflow_automatique": True
                }
            }
        ]
        
        created_organisations = []
        for org_data in organisations:
            # Vérifier si l'organisation existe déjà
            existing_org = db.query(Organisation).filter(
                Organisation.code_etablissement == org_data["code_etablissement"]
            ).first()
            
            if existing_org:
                logger.info(f"✅ Organisation existante: {existing_org.nom}")
                created_organisations.append(existing_org)
            else:
                org = Organisation(**org_data)
                db.add(org)
                db.commit()
                db.refresh(org)
                created_organisations.append(org)
                logger.info(f"✅ Organisation créée: {org.nom}")
        
        # 2. Créer des services pour chaque organisation
        services_data = [
            # Services pour CHU Paris
            {"nom": "Cardiologie", "code_service": "CARDIO", "categorie": "SPECIALITE"},
            {"nom": "Urgences", "code_service": "URG", "categorie": "URGENCE"},
            {"nom": "Pédiatrie", "code_service": "PED", "categorie": "SPECIALITE"},
            {"nom": "Radiologie", "code_service": "RADIO", "categorie": "IMAGERIE"},
            {"nom": "Laboratoire", "code_service": "LABO", "categorie": "LABORATOIRE"},
            
            # Services pour Hôpital Lyon
            {"nom": "Chirurgie Générale", "code_service": "CHIR", "categorie": "CHIRURGIE"},
            {"nom": "Neurologie", "code_service": "NEURO", "categorie": "SPECIALITE"},
            {"nom": "Gynécologie", "code_service": "GYNECO", "categorie": "SPECIALITE"},
            {"nom": "Pharmacie", "code_service": "PHARMA", "categorie": "PHARMACIE"},
            {"nom": "Administration", "code_service": "ADMIN", "categorie": "ADMINISTRATIF"},
            
            # Services pour Clinique Marseille
            {"nom": "Dermatologie", "code_service": "DERMATO", "categorie": "SPECIALITE"},
            {"nom": "Orthopédie", "code_service": "ORTHO", "categorie": "SPECIALITE"},
            {"nom": "Psychiatrie", "code_service": "PSYCH", "categorie": "SPECIALITE"},
            {"nom": "Consultation", "code_service": "CONSULT", "categorie": "CONSULTATION"},
            {"nom": "Direction", "code_service": "DIR", "categorie": "ADMINISTRATIF"}
        ]
        
        # Répartir les services entre les organisations
        services_per_org = 5
        for i, org in enumerate(created_organisations):
            start_idx = i * services_per_org
            end_idx = start_idx + services_per_org
            
            for service_data in services_data[start_idx:end_idx]:
                # Vérifier si le service existe déjà
                existing_service = db.query(Service).filter(
                    Service.code_service == service_data["code_service"],
                    Service.organisation_id == org.id
                ).first()
                
                if existing_service:
                    logger.info(f"✅ Service existant: {existing_service.nom}")
                else:
                    service = Service(
                        organisation_id=org.id,
                        **service_data,
                        configuration={
                            "email_contact": f"{service_data['code_service'].lower()}@{org.code_etablissement.lower()}.fr",
                            "telephone_contact": "01.23.45.67.89"
                        }
                    )
                    db.add(service)
                    logger.info(f"✅ Service créé: {service.nom} pour {org.nom}")
            
            db.commit()
        
        # 3. Créer un utilisateur de test si nécessaire
        existing_user = db.query(User).filter(User.email == "admin@test.com").first()
        if not existing_user:
            user = User(
                nom="Admin",
                prenom="Test",
                nom_complet="Admin Test",
                email="admin@test.com",
                type_utilisateur=UserRole.ADMIN,
                organisation_id=created_organisations[0].id,
                est_actif=True
            )
            db.add(user)
            db.commit()
            logger.info("✅ Utilisateur de test créé: admin@test.com")
        
        logger.info("🎉 Données de test créées avec succès !")
        
        # Afficher un résumé
        org_count = db.query(Organisation).count()
        service_count = db.query(Service).count()
        user_count = db.query(User).count()
        
        logger.info(f"📊 Résumé:")
        logger.info(f"   - Organisations: {org_count}")
        logger.info(f"   - Services: {service_count}")
        logger.info(f"   - Utilisateurs: {user_count}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des données de test: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()