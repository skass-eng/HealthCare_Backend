#!/usr/bin/env python3
"""
ENDPOINT DE TEST - Création de plainte JSON simple
Pour les tests d'intégration avec l'architecture modulaire
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime
from uuid import uuid4

from ..db.database import get_db
from shared.models import Plainte, Service, User, StatutPlainte, PrioritePlainte
from shared.schemas import PlainteCreate
from pydantic import BaseModel
from typing import Optional

# Schéma simplifié pour les tests
class TestPlainteResponse(BaseModel):
    id: int
    numero: str
    titre: str
    nom_plaignant: Optional[str] = None
    prenom_plaignant: Optional[str] = None
    email_plaignant: Optional[str] = None
    telephone_plaignant: Optional[str] = None
    description: str
    statut: str
    priorite: str
    date_creation: datetime
    analyse_ia_en_cours: bool = False
    task_id: Optional[str] = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["Test - API Modulaire"])

# Import du système modulaire
try:
    from healthcare_worker_server.app.tasks.celery_tasks import process_complaint_complete
    MODULAR_WORKER_AVAILABLE = True
    logger.info("Worker modulaire disponible pour endpoint de test")
except ImportError:
    MODULAR_WORKER_AVAILABLE = False
    logger.warning("Worker modulaire non disponible - endpoint de test en mode simulation")

@router.post("/plainte", response_model=TestPlainteResponse)
async def create_test_complaint(
    plainte_data: PlainteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint de test pour créer une plainte avec données JSON
    et déclencher le traitement modulaire complet
    """
    try:
        logger.info(f"🧪 [TEST] Création plainte: {plainte_data.nom_plaignant}")
        
        # Génération du numéro de plainte unique
        import time
        current_year = datetime.now().year
        timestamp = int(time.time() * 1000) % 10000  # 4 derniers chiffres du timestamp
        numero_plainte = f"PL_{current_year}_{timestamp:04d}"
        
        # Vérifier l'unicité
        attempt = 0
        while db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first():
            attempt += 1
            numero_plainte = f"PL_{current_year}_{timestamp + attempt:04d}"
            if attempt > 100:  # Protection contre boucle infinie
                raise HTTPException(status_code=500, detail="Impossible de générer un numéro unique")
        
        # Recherche du service (ou service par défaut)
        service = None
        if hasattr(plainte_data, 'service') and plainte_data.service:
            service = db.query(Service).filter(Service.nom == plainte_data.service).first()
        
        if not service:
            service = db.query(Service).first()  # Service par défaut
            if not service:
                # Créer un service par défaut si aucun n'existe
                service = Service(
                    nom="Général",
                    description="Service général pour les plaintes"
                )
                db.add(service)
                db.flush()
        
        # Création de la plainte
        plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=plainte_data.titre,
            nom_plaignant=plainte_data.nom_plaignant,
            prenom_plaignant=plainte_data.prenom_plaignant,
            email_plaignant=plainte_data.email_plaignant,
            telephone_plaignant=plainte_data.telephone_plaignant,
            description=plainte_data.description,
            service_id=service.id,
            statut=StatutPlainte.RECU,
            priorite=PrioritePlainte.MOYEN,
            date_creation=datetime.now(),
            date_incident=datetime.now()
        )
        
        db.add(plainte)
        db.commit()
        db.refresh(plainte)
        
        logger.info(f"✅ [TEST] Plainte créée: {plainte.numero_plainte} (ID: {plainte.id})")
        
        # Déclenchement du traitement modulaire si disponible
        if MODULAR_WORKER_AVAILABLE:
            logger.info(f"🚀 [TEST] Déclenchement du traitement modulaire pour plainte {plainte.id}")
            
            # Marquer l'analyse comme en cours
            plainte.analyse_ia_en_cours = True
            db.commit()
            
            # Déclencher le traitement complet en arrière-plan
            task_result = process_complaint_complete.delay(
                plainte_id=plainte.id
            )
            
            logger.info(f"🎯 [TEST] Tâche modulaire déclenchée: {task_result.id}")
            
            # Retourner la réponse avec indication du traitement en cours
            return TestPlainteResponse(
                id=plainte.id,
                numero=plainte.numero_plainte,
                titre=plainte.titre,
                nom_plaignant=plainte.nom_plaignant,
                prenom_plaignant=plainte.prenom_plaignant,
                email_plaignant=plainte.email_plaignant,
                telephone_plaignant=plainte.telephone_plaignant,
                description=plainte.description,
                statut=plainte.statut.value,
                priorite=plainte.priorite.value,
                date_creation=plainte.date_creation,
                analyse_ia_en_cours=True,
                task_id=str(task_result.id)
            )
        else:
            logger.warning(f"⚠️ [TEST] Worker modulaire non disponible - plainte créée sans traitement IA")
            
            return TestPlainteResponse(
                id=plainte.id,
                numero=plainte.numero_plainte,
                titre=plainte.titre,
                nom_plaignant=plainte.nom_plaignant,
                prenom_plaignant=plainte.prenom_plaignant,
                email_plaignant=plainte.email_plaignant,
                telephone_plaignant=plainte.telephone_plaignant,
                description=plainte.description,
                statut=plainte.statut.value,
                priorite=plainte.priorite.value,
                date_creation=plainte.date_creation,
                analyse_ia_en_cours=False
            )
            
    except Exception as e:
        logger.error(f"❌ [TEST] Erreur lors de la création de la plainte: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la plainte: {str(e)}")

@router.get("/plainte/{plainte_id}", response_model=TestPlainteResponse)
async def get_test_complaint(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer les détails d'une plainte créée via l'endpoint de test
    """
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    
    return TestPlainteResponse(
        id=plainte.id,
        numero=plainte.numero_plainte,
        titre=plainte.titre,
        nom_plaignant=plainte.nom_plaignant,
        prenom_plaignant=plainte.prenom_plaignant,
        email_plaignant=plainte.email_plaignant,
        telephone_plaignant=plainte.telephone_plaignant,
        description=plainte.description,
        statut=plainte.statut.value,
        priorite=plainte.priorite.value,
        date_creation=plainte.date_creation,
        analyse_ia_en_cours=getattr(plainte, 'analyse_ia_en_cours', False)
    )
