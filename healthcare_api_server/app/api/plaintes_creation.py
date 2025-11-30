#!/usr/bin/env python3
"""
API CRÉATION PLAINTES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour la création et les informations nécessaires à la création des plaintes
Utilisé par la page http://localhost:3000/plaintes/nouvelles
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, File, UploadFile, Form, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func, case
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, red, grey
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from ..db.database import get_db
from shared.models import Plainte, User, Service, Analyse, StatutPlainte, PrioritePlainte, AnalyseIA
from shared.schemas import (
    PlainteCreate, PlainteUpdate, PlainteResponse,
    AnalyseTaskRequest, TaskStatus, PaginatedResponse, AnalyseResponse
)
# from ..core.auth import get_current_user  # Désactivé pour le développement
from ..services.task_manager import trigger_analyse_plainte
# from ..services.worker_tasks import trigger_analyse_plainte_complete  # Ancien système simulé
from celery_worker_v2 import trigger_plainte_analysis  # Système Celery v2

logger = logging.getLogger(__name__)

# Import du nouveau système modulaire
try:
    from healthcare_worker_server.app.tasks.celery_tasks import process_complaint_complete
    MODULAR_WORKER_AVAILABLE = True
    logger.info("Worker modulaire disponible")
except ImportError:
    MODULAR_WORKER_AVAILABLE = False
    logger.warning("Worker modulaire non disponible - utilisation du worker v2")

logger = logging.getLogger(__name__)

def generate_pdf_synchrone(plainte_id: int, db: Session) -> str:
    """
    Générer un PDF synchrone quand le worker Celery n'est pas disponible
    """
    try:
        # Récupérer la plainte avec toutes ses relations
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise Exception(f"Plainte {plainte_id} non trouvée")
        
        # Récupérer le service associé
        service = db.query(Service).filter(Service.id == plainte.service_id).first()
        
        # Récupérer l'utilisateur assigné (si existe)
        utilisateur_assigne = None
        if plainte.utilisateur_assigne_id:
            utilisateur_assigne = db.query(User).filter(User.id == plainte.utilisateur_assigne_id).first()
        
        # Créer le dossier de sortie
        output_dir = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom du fichier PDF
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = output_dir / pdf_filename
        
        # Configuration du document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceBefore=15,
            spaceAfter=10
        )
        
        # Titre principal
        story.append(Paragraph(f"Rapport de Plainte #{plainte_id}", title_style))
        story.append(Spacer(1, 20))
        
        # Informations générales
        story.append(Paragraph("Informations Générales", header_style))
        
        info_data = [
            ["Titre:", plainte.titre or "Non spécifié"],
            ["Service concerné:", service.nom if service else "Non assigné"],
            ["Statut:", plainte.statut.value if plainte.statut else "Non défini"],
            ["Priorité:", plainte.priorite.value if plainte.priorite else "Non définie"],
            ["Date de création:", plainte.date_creation.strftime("%d/%m/%Y %H:%M") if plainte.date_creation else "Non disponible"],
            ["Utilisateur assigné:", f"{utilisateur_assigne.nom} {utilisateur_assigne.prenom}" if utilisateur_assigne else "Non assigné"]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Description de la plainte
        if plainte.description:
            story.append(Paragraph("Description de la Plainte", header_style))
            story.append(Paragraph(plainte.description, styles['Normal']))
            story.append(Spacer(1, 15))
        
        # Informations du plaignant (si disponibles)
        if plainte.nom_plaignant:
            story.append(Paragraph("Informations du Plaignant", header_style))
            plaignant_data = [
                ["Nom:", f"{plainte.nom_plaignant or ''} {plainte.prenom_plaignant or ''}".strip()],
                ["Email:", plainte.email_plaignant or "Non spécifié"],
                ["Téléphone:", plainte.telephone_plaignant or "Non spécifié"]
            ]
            
            plaignant_table = Table(plaignant_data, colWidths=[2*inch, 4*inch])
            plaignant_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(plaignant_table)
            story.append(Spacer(1, 20))
        
        # Pied de page avec informations de génération
        story.append(Spacer(1, 30))
        story.append(Paragraph("—" * 50, styles['Normal']))
        story.append(Paragraph(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        story.append(Paragraph("Système HealthCare AI - Architecture ODYSSEE", styles['Normal']))
        
        # Construire le PDF
        doc.build(story)
        
        logger.info(f"✅ PDF généré avec succès: {pdf_path}")
        return str(pdf_path)
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération PDF synchrone: {e}")
        raise

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

async def launch_background_analysis(plainte_id: int):
    """
    Fonction pour lancer les tâches d'analyse en arrière-plan
    Utilise le worker modulaire si disponible, sinon fallback sur v2
    """
    try:
        from ..db.database import get_db
        
        # Créer une nouvelle session DB pour les tâches background
        db = next(get_db())
        
        logger.info(f"🚀 Lancement des tâches en arrière-plan pour plainte {plainte_id}")
        
        # Récupérer l'analyse IA
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        # Déclenchement automatique de l'analyse IA via Celery
        task_id = None
        try:
            if MODULAR_WORKER_AVAILABLE:
                # Utiliser le nouveau worker modulaire
                logger.info(f"📦 Utilisation du worker modulaire pour plainte {plainte_id}")
                task_result = process_complaint_complete.delay(plainte_id)
                task_id = task_result.id
                logger.info(f"🚀 Tâche modulaire déclenchée: Task={task_id}")
            else:
                # Fallback sur le worker v2
                logger.info(f"📦 Fallback worker v2 pour plainte {plainte_id}")
                task_result = trigger_plainte_analysis(plainte_id)
                task_id = task_result['task_id']
                logger.info(f"🚀 Tâche Celery v2 déclenchée: Task={task_id}")
            
            # Mettre à jour le statut pour indiquer que le traitement a commencé
            if analyse_ia:
                analyse_ia.statut_analyse = "en_cours"
                db.commit()
            
        except Exception as e:
            logger.warning(f"Worker Celery non disponible pour plainte {plainte_id}: {e}")
            # Solution de contournement : générer PDF directement + analyse simple
            try:
                pdf_path = generate_pdf_synchrone(plainte_id, db)
                logger.info(f"📄 PDF généré en mode synchrone: {pdf_path}")
            except Exception as pdf_error:
                logger.error(f"Erreur génération PDF synchrone: {pdf_error}")
            
            # Simuler une analyse simple si le worker n'est pas disponible
            if analyse_ia:
                analyse_ia.sentiment = "neutre"
                analyse_ia.categorie_principale = "generale"
                analyse_ia.mots_cles = json.dumps(["plainte", "service"])
                analyse_ia.statut_analyse = "complete_simulation"
                db.commit()
                logger.info(f"✅ Analyse IA simulée pour plainte {plainte_id}")
        
        db.close()
        logger.info(f"✅ Tâches en arrière-plan terminées pour plainte {plainte_id}")
        
    except Exception as e:
        logger.error(f"Erreur dans les tâches en arrière-plan pour plainte {plainte_id}: {e}")

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
            query = query.filter(Service.est_actif == True)
        
        services = query.all()
        
        return [
            {
                "id": service.id,
                "nom": service.nom,
                "description": service.description,
                "actif": service.est_actif
            }
            for service in services
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des services: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

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

@router.options("/nouvelle")
async def options_create_complaint():
    """Endpoint OPTIONS pour CORS preflight"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

@router.post("/nouvelle", response_model=PlainteResponse)
async def create_new_complaint(
    background_tasks: BackgroundTasks,
    # Données du plaignant
    nom_plaignant: str = Form(...),
    prenom_plaignant: str = Form(...),
    email_plaignant: str = Form(...),
    telephone_plaignant: str = Form(...),
    
    # Détails de la plainte
    objet: str = Form(...),
    description: str = Form(...),
    date_incident: str = Form(...),
    
    # Assignation
    service_concerne_id: str = Form(...),
    utilisateur_assigne_id: str = Form(None),
    priorite: str = Form("MOYEN"),
    
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
        
        # Validation des IDs
        try:
            service_id = int(service_concerne_id)
            user_id = int(utilisateur_assigne_id) if utilisateur_assigne_id else None
        except ValueError:
            raise HTTPException(status_code=400, detail="IDs de service ou utilisateur invalides")
        
        # Vérifications d'existence
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
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
            titre=objet,
            description=description,
            date_incident=date_incident_parsed,
            service_id=service_id,
            assignee_a_id=user_id,
            priorite=PrioritePlainte(priorite),
            statut=StatutPlainte.EN_COURS,
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
            statut_analyse="en_attente"
        )
        db.add(analyse_ia)
        db.commit()
        
        # 🚀 RÉPONSE RAPIDE : Lancer les tâches en arrière-plan APRÈS avoir répondu
        background_tasks.add_task(launch_background_analysis, new_plainte.id)
        
        # Préparer la réponse rapide (sans attendre les tâches)
        response_data = {
            "id": str(new_plainte.id),
            "numero_plainte": new_plainte.numero_plainte,
            "nom_plaignant": new_plainte.nom_plaignant,
            "prenom_plaignant": new_plainte.prenom_plaignant,
            "email_plaignant": new_plainte.email_plaignant,
            "telephone_plaignant": new_plainte.telephone_plaignant,
            "titre": new_plainte.titre,
            "description": new_plainte.description,
            "date_incident": new_plainte.date_incident.isoformat() if new_plainte.date_incident else None,
            "service_id": str(new_plainte.service_id),
            "assignee_a_id": str(new_plainte.assignee_a_id) if new_plainte.assignee_a_id else None,
            "priorite": new_plainte.priorite.value,
            "statut": new_plainte.statut.value,
            "date_creation": new_plainte.date_creation.isoformat(),
            "date_modification": new_plainte.date_modification.isoformat() if new_plainte.date_modification else None,
            # Informations sur les tâches en arrière-plan
            "task_info": {
                "status": "plainte_created",
                "background_processing": "started",
                "pdf_generation": "en_cours",
                "ai_analysis": "en_cours",
                "status_endpoint": f"/api/tasks/plainte/{new_plainte.id}/status"
            }
        }
        
        # Retourner une JSONResponse avec en-têtes CORS explicites
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
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
                statut_analyse="en_attente"
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
