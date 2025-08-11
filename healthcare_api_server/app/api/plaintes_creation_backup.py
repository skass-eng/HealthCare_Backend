#!/usr/bin/env python3
"""
API CRÉATION PLAINTES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour la création et les informations nécessaires à la création des plaintes
Utilisé par la page http://localhost:3000/plaintes/nouvelles
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, File, UploadFile, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func, case
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta
import json
import os

from ..db.database import get_db
from shared.models import Plainte, User, Service, Analyse, StatutPlainte, PrioritePlainte, AnalyseIA
from shared.schemas import (
    PlainteCreate, PlainteUpdate, PlainteResponse,
    AnalyseTaskRequest, TaskStatus, PaginatedResponse, AnalyseResponse
)
# from ..core.auth import get_current_user  # Désactivé pour le développement
from ..services.task_manager import trigger_analyse_plainte
# from ..services.worker_tasks import trigger_analyse_plainte_complete  # Ancien système simulé
from celery_worker_v2 import trigger_plainte_analysis  # Nouveau système Celery avec PDF

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaintes/creation", tags=["Plaintes - Création"])

@router.get("/total", response_model=int)
def get_total_complaints_for_year(
    year: int = Query(datetime.now().year),
    db: Session = Depends(get_db)
):
    """
    Récupérer le nombre total de plaintes pour l'année spécifiée.
    Utilisé pour générer le titre automatique des nouvelles plaintes.
    """
    try:
        total_complaints = db.query(func.count(Plainte.id)).filter(
            func.extract('year', Plainte.date_creation) == year
        ).scalar()
        
        return total_complaints or 0
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du total des plaintes: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/users", response_model=List[dict])
def get_users_for_assignment(db: Session = Depends(get_db)):
    """
    Récupérer la liste des utilisateurs pour l'assignation des plaintes.
    """
    try:
        users = db.query(User).filter(
            User.actif == True
        ).options(
            selectinload(User.service)
        ).all()
        
        return [
            {
                "id": str(user.id),
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "service": user.service.nom if user.service else None,
                "full_name": f"{user.prenom} {user.nom}"
            }
            for user in users
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/services", response_model=List[dict])
def get_services_for_assignment(
    actif_seulement: bool = Query(True, description="Récupérer seulement les services actifs"),
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des services pour l'assignation des plaintes.
    """
    try:
        query = db.query(Service)
        if actif_seulement:
            query = query.filter(Service.actif == True)
        
        services = query.all()
        
        return [
            {
                "id": str(service.id),
                "nom": service.nom,
                "description": service.description,
                "actif": service.actif
            }
            for service in services
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des services: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/service-defaut", response_model=dict)
def get_default_service(db: Session = Depends(get_db)):
    """
    Récupérer le service par défaut pour les nouvelles plaintes.
    Retourne le premier service actif trouvé.
    """
    try:
        service_defaut = db.query(Service).filter(
            Service.actif == True
        ).first()
        
        if not service_defaut:
            raise HTTPException(status_code=404, detail="Aucun service actif trouvé")
        
        return {
            "id": str(service_defaut.id),
            "nom": service_defaut.nom,
            "description": service_defaut.description,
            "actif": service_defaut.actif
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du service par défaut: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/nouvelle", response_model=PlainteResponse)
async def create_new_complaint(
    # Données du plaignant
    nom_plaignant: str = Form(...),
    prenom_plaignant: str = Form(...),
    email_plaignant: str = Form(...),
    telephone_plaignant: str = Form(...),
    adresse_plaignant: str = Form(...),
    
    # Détails de la plainte
    objet: str = Form(...),
    description: str = Form(...),
    date_incident: str = Form(...),
    lieu_incident: str = Form(...),
    temoins: str = Form(None),
    actions_prises: str = Form(None),
    
    # Assignation
    service_concerne_id: str = Form(...),
    utilisateur_assigne_id: str = Form(None),
    priorite: str = Form("normale"),
    
    # Documents optionnels
    documents: List[UploadFile] = File(None),
    
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle plainte avec tous les détails nécessaires.
    Gère également l'upload de documents et le déclenchement de l'analyse IA.
    """
    try:
        logger.info(f"🚀 Création d'une nouvelle plainte pour {prenom_plaignant} {nom_plaignant}")
        logger.info(f"📊 service_concerne_id reçu: '{service_concerne_id}'")
        logger.info(f"📊 utilisateur_assigne_id reçu: '{utilisateur_assigne_id}'")
        
        # Validation des UUIDs
        try:
            service_uuid = UUID(service_concerne_id)
            user_uuid = UUID(utilisateur_assigne_id) if utilisateur_assigne_id else None
        except ValueError:
            logger.error(f"❌ IDs invalides: service='{service_concerne_id}', user='{utilisateur_assigne_id}'")
            raise HTTPException(status_code=400, detail="IDs de service ou utilisateur invalides")
        
        # Vérifications d'existence
        service = db.query(Service).filter(Service.id == service_uuid).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        if user_uuid:
            user = db.query(User).filter(User.id == user_uuid).first()
            if not user:
                raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Conversion de la date
        try:
            date_incident_parsed = datetime.strptime(date_incident, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD attendu)")
        
        # Génération du numéro de plainte
        current_year = datetime.now().year
        total_count = db.query(func.count(Plainte.id)).filter(
            func.extract('year', Plainte.date_creation) == current_year
        ).scalar() or 0
        
        numero_plainte = f"PL_{current_year}_{str(total_count + 1).zfill(4)}"
        
        # Traitement des documents
        documents_paths = []
        if documents:
            upload_dir = "data/documents"
            os.makedirs(upload_dir, exist_ok=True)
            
            for doc in documents:
                if doc.filename:
                    file_path = os.path.join(upload_dir, f"{numero_plainte}_{doc.filename}")
                    with open(file_path, "wb") as buffer:
                        content = await doc.read()
                        buffer.write(content)
                    documents_paths.append(file_path)
                    logger.info(f"📄 Document sauvegardé: {file_path}")
        
        # Création de la plainte
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            nom_plaignant=nom_plaignant,
            prenom_plaignant=prenom_plaignant,
            email_plaignant=email_plaignant,
            telephone_plaignant=telephone_plaignant,
            adresse_plaignant=adresse_plaignant,
            objet=objet,
            description=description,
            date_incident=date_incident_parsed,
            lieu_incident=lieu_incident,
            temoins=temoins,
            actions_prises=actions_prises,
            service_concerne_id=service_uuid,
            utilisateur_assigne_id=user_uuid,
            priorite=PrioritePlainte(priorite),
            statut=StatutPlainte.en_cours,
            documents_joints=json.dumps(documents_paths) if documents_paths else None,
            date_creation=datetime.now(),
            date_modification=datetime.now()
        )
        
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte créée: {new_plainte.numero_plainte} (ID: {new_plainte.id})")
        
        # Création de l'enregistrement d'analyse IA
        analyse_ia = AnalyseIA(
            plainte_id=new_plainte.id,
            statut_analyse="en_attente",
            date_creation=datetime.now()
        )
        db.add(analyse_ia)
        db.commit()
        
        # Déclenchement de l'analyse IA via Celery
        try:
            # Utiliser le nouveau système Celery avec génération PDF
            task_result = trigger_plainte_analysis(new_plainte.id)
            logger.info(f"🚀 Tâche Celery déclenchée pour plainte {new_plainte.id}: Task={task_result['task_id']}")
        except Exception as e:
            logger.warning(f"Worker Celery non disponible pour plainte {new_plainte.id}: {e}")
            # Simuler une analyse simple si le worker n'est pas disponible
            if analyse_ia:
                analyse_ia.sentiment = "neutre"
                analyse_ia.categorie_principale = "generale"
                analyse_ia.mots_cles = json.dumps(["plainte", "service"])
                analyse_ia.statut_analyse = "complete_simulation"
                db.commit()
        
        # Préparer la réponse
        response_data = {
            "id": str(new_plainte.id),
            "numero_plainte": new_plainte.numero_plainte,
            "nom_plaignant": new_plainte.nom_plaignant,
            "prenom_plaignant": new_plainte.prenom_plaignant,
            "email_plaignant": new_plainte.email_plaignant,
            "telephone_plaignant": new_plainte.telephone_plaignant,
            "adresse_plaignant": new_plainte.adresse_plaignant,
            "objet": new_plainte.objet,
            "description": new_plainte.description,
            "date_incident": new_plainte.date_incident.isoformat(),
            "lieu_incident": new_plainte.lieu_incident,
            "temoins": new_plainte.temoins,
            "actions_prises": new_plainte.actions_prises,
            "service_concerne_id": str(new_plainte.service_concerne_id),
            "utilisateur_assigne_id": str(new_plainte.utilisateur_assigne_id) if new_plainte.utilisateur_assigne_id else None,
            "priorite": new_plainte.priorite.value,
            "statut": new_plainte.statut.value,
            "documents_joints": json.loads(new_plainte.documents_joints) if new_plainte.documents_joints else [],
            "date_creation": new_plainte.date_creation.isoformat(),
            "date_modification": new_plainte.date_modification.isoformat()
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de la plainte: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.post("/analyser/{plainte_id}")
async def trigger_complaint_analysis(
    plainte_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Déclencher manuellement l'analyse d'une plainte existante.
    """
    try:
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Vérifier ou créer l'enregistrement d'analyse IA
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        if not analyse_ia:
            analyse_ia = AnalyseIA(
                plainte_id=plainte_id,
                statut_analyse="en_attente",
                date_creation=datetime.now()
            )
            db.add(analyse_ia)
            db.commit()
        
        try:
            # Utiliser le système Celery au lieu de l'ancien code
            from celery_worker_v2 import trigger_plainte_analysis
            task_result = trigger_plainte_analysis(plainte_id)
            logger.info(f"🚀 Tâche Celery déclenchée pour plainte {plainte_id}: Task={task_result['task_id']}")
        except Exception as e:
            logger.warning(f"Worker Celery non disponible pour plainte {plainte_id}: {e}")
            # Simuler une analyse simple si le worker n'est pas disponible
            if analyse_ia:
                analyse_ia.sentiment = "neutre"
                analyse_ia.categorie_principale = "generale"
                analyse_ia.mots_cles = json.dumps(["plainte", "service"])
                analyse_ia.statut_analyse = "complete_simulation"
                analyse_ia.date_modification = datetime.now()
                db.commit()
        
        return {
            "message": "Analyse déclenchée avec succès",
            "plainte_id": str(plainte_id),
            "status": "triggered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement de l'analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.get("/statut-analyse/{plainte_id}")
def get_analysis_status(
    plainte_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Récupérer le statut de l'analyse d'une plainte.
    """
    try:
        # Récupérer l'analyse IA
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        if not analyse_ia:
            raise HTTPException(status_code=404, detail="Analyse non trouvée")
        
        return {
            "plainte_id": str(plainte_id),
            "statut_analyse": analyse_ia.statut_analyse,
            "sentiment": analyse_ia.sentiment,
            "categorie_principale": analyse_ia.categorie_principale,
            "mots_cles": json.loads(analyse_ia.mots_cles) if analyse_ia.mots_cles else [],
            "score_urgence": analyse_ia.score_urgence,
            "resume_automatique": analyse_ia.resume_automatique,
            "recommandations": json.loads(analyse_ia.recommandations) if analyse_ia.recommandations else [],
            "date_creation": analyse_ia.date_creation.isoformat() if analyse_ia.date_creation else None,
            "date_modification": analyse_ia.date_modification.isoformat() if analyse_ia.date_modification else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut d'analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.get("/service-defaut")
def get_default_service(db: Session = Depends(get_db)):
    """
    Récupérer le service par défaut pour les plaintes.
    """
    try:
        # Récupérer le premier service disponible comme service par défaut
        service = db.query(Service).first()
        if not service:
            raise HTTPException(status_code=404, detail="Aucun service disponible")
        
        return {
            "id": str(service.id),
            "nom": service.nom,
            "description": service.description
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du service par défaut: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")
