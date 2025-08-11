#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour HealthCare AI
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import SessionLocal, engine
from shared.models import Base, Organisation, Service
from datetime import datetime

def init_database():
    """Initialiser la base de données avec les données de base"""
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Vérifier si l'organisation existe déjà
        organisation = db.query(Organisation).filter(Organisation.id == 1).first()
        
        if not organisation:
            # Créer l'organisation de base
            organisation = Organisation(
                id=1,  # Forcer l'ID à 1
                nom="Centre Hospitalier Universitaire",
                code_etablissement="CHU001",
                est_actif=True,
                configuration={
                    "delai_reponse_standard": 30,
                    "services_actifs": ["CARDIOLOGIE", "URGENCES", "PEDIATRIE", "CHIRURGIE"],
                    "workflow_automatique": True
                }
            )
            db.add(organisation)
            db.commit()
            db.refresh(organisation)
            print(f"✅ Organisation créée: {organisation.nom} (ID: {organisation.id})")
        else:
            print(f"✅ Organisation existante: {organisation.nom} (ID: {organisation.id})")
        
        # Créer quelques services de base
        services_data = [
            {
                "nom": "Cardiologie",
                "code_service": "CARDIO",
                "categorie": "CARDIOLOGIE",
                "description": "Service de cardiologie et maladies cardiovasculaires"
            },
            {
                "nom": "Urgences",
                "code_service": "URG",
                "categorie": "URGENCES",
                "description": "Service d'urgences médicales"
            },
            {
                "nom": "Pédiatrie",
                "code_service": "PED",
                "categorie": "PEDIATRIE",
                "description": "Service de pédiatrie"
            }
        ]
        
        for service_data in services_data:
            # Vérifier si le service existe déjà
            existing_service = db.query(Service).filter(
                Service.code_service == service_data["code_service"]
            ).first()
            
            if not existing_service:
                service = Service(
                    nom=service_data["nom"],
                    code_service=service_data["code_service"],
                    categorie=service_data["categorie"],
                    description=service_data["description"],
                    est_actif=True,
                    configuration={
                        "responsable": f"Dr. {service_data['nom']}",
                        "telephone": "01 23 45 67 89",
                        "email": f"{service_data['code_service'].lower()}@chu-paris.fr"
                    }
                )
                db.add(service)
                print(f"✅ Service créé: {service.nom}")
            else:
                print(f"✅ Service existant: {existing_service.nom}")
        
        db.commit()
        print("✅ Base de données initialisée avec succès")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()