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
import mimetypes

from ..db.database import get_db
from shared.models import Plainte, User, Service, Analyse, StatutPlainte, PrioritePlainte, AnalyseIA, DocumentPlainte, TypeFichier
from shared.schemas import (
    PlainteCreate, PlainteUpdate, PlainteResponse,
    AnalyseTaskRequest, TaskStatus, PaginatedResponse, AnalyseResponse
)
# from ..core.auth import get_current_user  # Désactivé pour le développement
from ..services.task_manager import trigger_analyse_plainte
# from ..services.worker_tasks import trigger_analyse_plainte_complete  # Ancien système simulé
from celery_worker_v2 import trigger_plainte_analysis  # Système Celery v2

# Import des services d'extraction PDF et analyse
try:
    from healthcare_worker_server.app.services.document_parser import DocumentParserService
    from healthcare_worker_server.app.services.complaint_analysis import ComplaintAnalysisService
    from healthcare_worker_server.app.services.llm_provider import get_llm_service
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_EXTRACTION_AVAILABLE = False

# Import du service OCR pour les images
try:
    from healthcare_worker_server.app.services.image_ocr import ImageOCRService, get_ocr_service
    IMAGE_OCR_AVAILABLE = True
except ImportError:
    IMAGE_OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_type_fichier(filename: str) -> TypeFichier:
    """Détermine le type de fichier basé sur l'extension"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    mapping = {
        'pdf': TypeFichier.PDF,
        'doc': TypeFichier.DOC,
        'docx': TypeFichier.DOCX,
        'txt': TypeFichier.TXT,
        'jpg': TypeFichier.IMAGE,
        'jpeg': TypeFichier.IMAGE,
        'png': TypeFichier.IMAGE,
        'gif': TypeFichier.IMAGE,
        'bmp': TypeFichier.IMAGE,
    }
    return mapping.get(ext, TypeFichier.AUTRE)


def generate_numero_plainte(db: Session) -> str:
    """
    Génère un numéro de plainte unique et robuste.
    Utilise MAX au lieu de COUNT pour éviter les doublons après suppression.
    Inclut une vérification de sécurité pour les conditions de concurrence.
    
    Format: PL_YYYY_XXXX (ex: PL_2025_0148)
    
    Args:
        db: Session de base de données
    
    Returns:
        Numéro de plainte unique
    """
    current_year = datetime.now().year
    prefix = f"PL_{current_year}_"
    
    # Trouver le dernier numéro utilisé pour cette année
    last_plainte = db.query(Plainte.numero_plainte).filter(
        Plainte.numero_plainte.like(f"{prefix}%")
    ).order_by(Plainte.numero_plainte.desc()).first()
    
    if last_plainte and last_plainte[0]:
        try:
            last_num = int(last_plainte[0].replace(prefix, ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    
    numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
    
    # Vérification de sécurité: s'assurer que le numéro n'existe pas déjà
    max_attempts = 100  # Éviter boucle infinie
    attempts = 0
    while db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first() and attempts < max_attempts:
        next_num += 1
        numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
        attempts += 1
    
    if attempts >= max_attempts:
        # Fallback: utiliser un UUID partiel pour garantir l'unicité
        import uuid
        numero_plainte = f"{prefix}{str(uuid.uuid4())[:8].upper()}"
    
    logger.info(f"📝 Numéro de plainte généré: {numero_plainte}")
    return numero_plainte

# Import du nouveau système modulaire
try:
    from healthcare_worker_server.app.tasks.celery_tasks import process_complaint_complete
    MODULAR_WORKER_AVAILABLE = True
    logger.info("Worker modulaire disponible")
except ImportError:
    MODULAR_WORKER_AVAILABLE = False
    logger.warning("Worker modulaire non disponible - utilisation du worker v2")

# Import du générateur PDF robuste
try:
    from ..services.pdf_generator import PDFGenerator, generate_pdf_for_plainte
    PDF_GENERATOR_AVAILABLE = True
    logger.info("✅ PDFGenerator importé avec succès")
except ImportError as e:
    PDF_GENERATOR_AVAILABLE = False
    logger.warning(f"⚠️ PDFGenerator non disponible: {e}")

logger = logging.getLogger(__name__)

def generate_pdf_synchrone(plainte_id: int, db: Session) -> str:
    """
    Générer un PDF synchrone - utilise le nouveau générateur robuste
    """
    try:
        # Utiliser le nouveau générateur robuste s'il est disponible
        if PDF_GENERATOR_AVAILABLE:
            logger.info(f"📄 Utilisation du PDFGenerator robuste pour plainte {plainte_id}")
            return generate_pdf_for_plainte(plainte_id, db)
        
        # Fallback sur l'ancienne méthode
        logger.info(f"📄 Fallback sur la méthode legacy pour plainte {plainte_id}")
        return _generate_pdf_legacy(plainte_id, db)
        
    except Exception as e:
        logger.error(f"❌ Erreur génération PDF: {e}")
        # Dernier recours: générer un PDF minimal
        return _generate_minimal_pdf(plainte_id, db)


def _generate_minimal_pdf(plainte_id: int, db: Session) -> str:
    """
    Générer un PDF minimal en dernier recours
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        output_dir = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = output_dir / pdf_filename
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"Rapport de Plainte #{plainte_id}", styles['Title']))
        story.append(Spacer(1, 20))
        
        if plainte:
            story.append(Paragraph(f"Numéro: {plainte.numero_plainte or 'N/A'}", styles['Normal']))
            story.append(Paragraph(f"Titre: {plainte.titre or 'N/A'}", styles['Normal']))
            story.append(Paragraph(f"Description: {plainte.description or 'N/A'}", styles['Normal']))
            story.append(Paragraph(f"Statut: {plainte.statut.value if plainte.statut else 'N/A'}", styles['Normal']))
        else:
            story.append(Paragraph("Plainte non trouvée", styles['Normal']))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        
        doc.build(story)
        logger.info(f"✅ PDF minimal généré: {pdf_path}")
        return str(pdf_path)
        
    except Exception as e:
        logger.error(f"❌ Échec total génération PDF: {e}")
        raise


def _generate_pdf_legacy(plainte_id: int, db: Session) -> str:
    """
    Ancienne méthode de génération PDF (fallback)
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
        if plainte.assignee_a_id:
            utilisateur_assigne = db.query(User).filter(User.id == plainte.assignee_a_id).first()
        
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
            User.est_actif == True
        ).all()
        
        result = []
        for user in users:
            # Récupérer le service séparément si l'utilisateur a un service_id
            service_name = None
            if user.service_id:
                service = db.query(Service).filter(Service.id == user.service_id).first()
                service_name = service.nom if service else None
            
            result.append({
                "id": str(user.id),
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "service": service_name,
                "full_name": f"{user.prenom} {user.nom}"
            })
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

async def launch_background_analysis(plainte_id: int):
    """
    Fonction pour lancer les tâches d'analyse en arrière-plan
    Génère TOUJOURS le PDF de manière synchrone + essaie le worker pour l'analyse IA
    """
    try:
        from ..db.database import get_db
        
        # Créer une nouvelle session DB pour les tâches background
        db = next(get_db())
        
        logger.info(f"🚀 Lancement des tâches en arrière-plan pour plainte {plainte_id}")
        
        # Récupérer l'analyse IA
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        # 📄 TOUJOURS générer le PDF de manière synchrone (fiable)
        try:
            pdf_path = generate_pdf_synchrone(plainte_id, db)
            logger.info(f"📄 PDF généré avec succès: {pdf_path}")
        except Exception as pdf_error:
            logger.error(f"❌ Erreur génération PDF: {pdf_error}")
        
        # Vérifier si Redis/Celery est disponible
        celery_available = False
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            redis_client.ping()
            celery_available = True
            logger.info("✅ Redis disponible, utilisation de Celery")
        except Exception as redis_error:
            logger.warning(f"⚠️ Redis non disponible: {redis_error}")
        
        # Déclenchement de l'analyse IA
        if celery_available:
            try:
                if MODULAR_WORKER_AVAILABLE:
                    logger.info(f"📦 Utilisation du worker modulaire pour plainte {plainte_id}")
                    task_result = process_complaint_complete.delay(plainte_id)
                    task_id = task_result.id
                    logger.info(f"🚀 Tâche modulaire déclenchée: Task={task_id}")
                else:
                    logger.info(f"📦 Fallback worker v2 pour plainte {plainte_id}")
                    task_result = trigger_plainte_analysis(plainte_id)
                    task_id = task_result['task_id']
                    logger.info(f"🚀 Tâche Celery v2 déclenchée: Task={task_id}")
                
                if analyse_ia:
                    analyse_ia.statut_analyse = "en_cours"
                    db.commit()
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur Celery pour plainte {plainte_id}: {e}")
                celery_available = False
        
        # Si Celery n'est pas disponible, faire l'analyse IA simulée immédiatement
        if not celery_available and analyse_ia:
            logger.info(f"🔄 Exécution de l'analyse IA simulée pour plainte {plainte_id}")
            
            # Récupérer la plainte pour l'analyse
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            if plainte:
                # Analyse de sentiment basée sur le texte
                texte = f"{plainte.titre or ''} {plainte.description or ''}"
                
                mots_negatifs = ['problème', 'mauvais', 'inacceptable', 'colère', 'furieux', 'déçu', 'grave', 'urgent']
                mots_positifs = ['merci', 'satisfait', 'bien', 'excellent', 'parfait']
                
                score_neg = sum(1 for m in mots_negatifs if m in texte.lower())
                score_pos = sum(1 for m in mots_positifs if m in texte.lower())
                
                if score_neg > score_pos:
                    sentiment = "négatif"
                    priorite_ia = "URGENT" if score_neg >= 2 else "ELEVE"
                elif score_pos > score_neg:
                    sentiment = "positif"
                    priorite_ia = "BAS"
                else:
                    sentiment = "neutre"
                    priorite_ia = "MOYEN"
                
                # Déterminer le service suggéré
                if any(w in texte.lower() for w in ['urgence', 'urgent', 'grave']):
                    service_suggere = "Service d'Urgence"
                elif any(w in texte.lower() for w in ['consultation', 'médecin']):
                    service_suggere = "Service de Consultation"
                else:
                    service_suggere = "Service Qualité"
                
                analyse_ia.sentiment = sentiment
                analyse_ia.service_suggere = service_suggere
                analyse_ia.priorite_ia = priorite_ia
                analyse_ia.confiance_sentiment = 0.75
                analyse_ia.score_priorite = 0.7
                analyse_ia.resume_ia = f"Plainte analysée automatiquement. Sentiment {sentiment} détecté. Recommandation: {service_suggere}."
                analyse_ia.mots_cles_detectes = json.dumps(["plainte", "service", "patient"])
                analyse_ia.statut_analyse = "complete"
                analyse_ia.date_analyse = datetime.now()
                db.commit()
                logger.info(f"✅ Analyse IA simulée terminée pour plainte {plainte_id}: {sentiment}/{priorite_ia}")
        
        db.close()
        logger.info(f"✅ Tâches en arrière-plan terminées pour plainte {plainte_id}")
        
    except Exception as e:
        logger.error(f"❌ Erreur dans les tâches en arrière-plan pour plainte {plainte_id}: {e}")

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
        
        # Génération du numéro de plainte (utilise la fonction robuste)
        numero_plainte = generate_numero_plainte(db)
        
        # Traitement des documents - Sauvegarde sur disque
        documents_info = []  # Liste pour stocker les infos des documents
        if documents:
            upload_dir = "data/documents"
            os.makedirs(upload_dir, exist_ok=True)
            
            for doc in documents:
                if doc.filename:
                    nom_stockage = f"{numero_plainte}_{doc.filename}"
                    file_path = os.path.join(upload_dir, nom_stockage)
                    content = await doc.read()
                    
                    with open(file_path, "wb") as buffer:
                        buffer.write(content)
                    
                    # Collecter les infos pour l'enregistrement en DB
                    documents_info.append({
                        "nom_fichier": doc.filename,
                        "nom_stockage": nom_stockage,
                        "chemin_fichier": file_path,
                        "taille_fichier": len(content),
                        "mime_type": doc.content_type or mimetypes.guess_type(doc.filename)[0],
                        "type_fichier": get_type_fichier(doc.filename)
                    })
                    logger.info(f"📄 Document sauvegardé: {file_path} ({len(content)} octets)")
        
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
        
        # Enregistrement des documents en base de données
        documents_saved = []
        for doc_info in documents_info:
            doc_record = DocumentPlainte(
                plainte_id=new_plainte.id,
                nom_fichier=doc_info["nom_fichier"],
                nom_stockage=doc_info["nom_stockage"],
                chemin_fichier=doc_info["chemin_fichier"],
                type_fichier=doc_info["type_fichier"],
                taille_fichier=doc_info["taille_fichier"],
                mime_type=doc_info["mime_type"],
                est_piece_jointe_originale=True
            )
            db.add(doc_record)
            documents_saved.append({
                "nom": doc_info["nom_fichier"],
                "taille": doc_info["taille_fichier"],
                "type": doc_info["type_fichier"].value
            })
        
        if documents_saved:
            db.commit()
            logger.info(f"📁 {len(documents_saved)} document(s) enregistré(s) en base pour plainte {new_plainte.id}")
        
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
            # Documents attachés
            "documents": documents_saved,
            "documents_count": len(documents_saved),
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


# ==================== CRÉATION DEPUIS UN PDF ====================

def _extract_basic_data_from_text(text: str) -> dict:
    """
    Extraction basique de données depuis le texte du PDF (fallback sans LLM).
    Utilise des expressions régulières pour extraire les informations courantes.
    """
    import re
    
    # Patterns de base
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    phone_pattern = r'(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}'
    date_pattern = r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})'
    
    # Extraction email
    emails = re.findall(email_pattern, text)
    email = emails[0] if emails else None
    
    # Extraction téléphone
    phones = re.findall(phone_pattern, text)
    telephone = phones[0].replace(" ", "").replace(".", "").replace("-", "") if phones else None
    
    # Extraction date
    dates = re.findall(date_pattern, text)
    date_incident = None
    if dates:
        day, month, year = dates[0]
        if len(year) == 2:
            year = "20" + year
        date_incident = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Extraction nom/prénom
    name_patterns = [
        r'(?:Madame|Mme\.?)\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]+)',
        r'(?:Monsieur|Mr?\.?)\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]+)',
        r'(?:Nom|NOM)\s*[:\s]+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)',
        r'(?:Prénom|PRENOM)\s*[:\s]+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)',
    ]
    
    prenom = None
    nom = None
    for pattern in name_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple):
                prenom, nom = matches[0]
            else:
                nom = matches[0]
            break
    
    # Extraction du titre/objet
    titre = None
    objet_match = re.search(r'(?:Objet|OBJET)\s*[:\s]+(.+?)(?:\n|$)', text)
    if objet_match:
        titre = objet_match.group(1).strip()[:100]
    else:
        # Prendre les premiers mots significatifs
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not re.match(r'^[\d\s\-\/\.]+$', line):
                titre = line[:100]
                break
    
    # Extraire une description (premiers paragraphes significatifs)
    description = ""
    paragraphs = text.split('\n\n')
    for p in paragraphs:
        p = p.strip()
        if len(p) > 50:
            description = p[:1000]
            break
    
    if not description:
        description = text[:1000] if text else "Plainte importée depuis PDF"
    
    logger.info(f"📝 Extraction basique: nom={nom}, prenom={prenom}, email={email}, tel={telephone}")
    
    return {
        "plaignant": {
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "telephone": telephone
        },
        "plainte": {
            "titre": titre or "Plainte importée depuis PDF",
            "description": description,
            "date_incident": date_incident,
            "service_concerne": None,
            "mode_reception": "pdf_import"
        },
        "analyse": {
            "priorite_suggeree": "MOYEN",
            "mots_cles": [],
            "gravite_estimee": "non déterminée",
            "resume_court": "Plainte importée depuis un document PDF."
        },
        "confiance_extraction": {
            "score_global": 0.5,
            "champs_incertains": ["nom", "prenom", "date_incident", "service_concerne"]
        }
    }


@router.post("/depuis-donnees-validees")
async def create_complaint_from_validated_data(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="Fichier PDF à rattacher à la plainte"),
    service_id: int = Form(..., description="ID du service"),
    # Données validées par l'utilisateur (obligatoires)
    titre: str = Form(..., description="Titre de la plainte (validé par l'utilisateur)"),
    description: str = Form(..., description="Description de la plainte (validée par l'utilisateur)"),
    nom_plaignant: str = Form(..., description="Nom du plaignant (validé par l'utilisateur)"),
    prenom_plaignant: str = Form(..., description="Prénom du plaignant (validé par l'utilisateur)"),
    # Données optionnelles
    email_plaignant: Optional[str] = Form(None, description="Email du plaignant"),
    telephone_plaignant: Optional[str] = Form(None, description="Téléphone du plaignant"),
    mode_reception: Optional[str] = Form("pdf_import", description="Mode de réception"),
    date_incident: Optional[str] = Form(None, description="Date de l'incident (YYYY-MM-DD)"),
    priorite: Optional[str] = Form("MOYEN", description="Priorité de la plainte"),
    assigned_user_id: Optional[int] = Form(None, description="ID de l'utilisateur assigné"),
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle plainte avec les données VALIDÉES par l'utilisateur.
    
    Cette route est optimisée pour être utilisée APRÈS la prévisualisation.
    Elle ne refait PAS l'analyse IA - elle utilise directement les données validées.
    
    Processus:
    1. Validation des données obligatoires
    2. Upload et stockage du PDF original
    3. Création directe de la plainte en BDD
    4. Rattachement du PDF à la plainte
    5. Lancement de l'analyse IA en arrière-plan (optionnel)
    
    Returns:
        La plainte créée avec le document attaché
    """
    try:
        logger.info(f"📄 Création plainte depuis données validées - PDF: {pdf_file.filename}")
        logger.info(f"📝 Données: titre={titre[:50]}..., nom={nom_plaignant}, prenom={prenom_plaignant}, service={service_id}")
        
        # Vérification du type de fichier
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
        
        # Lecture et vérification de la taille
        content = await pdf_file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Le fichier PDF ne doit pas dépasser 10 MB")
        
        # Vérifier que le service existe
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service ID {service_id} non trouvé")
        
        # Génération du numéro de plainte (utilise la fonction robuste)
        numero_plainte = generate_numero_plainte(db)
        
        # Sauvegarde du PDF original
        upload_dir = Path("data/documents/pdf_originaux")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        nom_stockage = f"{numero_plainte}_{pdf_file.filename}"
        file_path = upload_dir / nom_stockage
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"📁 PDF sauvegardé: {file_path} ({len(content)} octets)")
        
        # Conversion de la priorité
        try:
            priorite_enum = PrioritePlainte(priorite) if priorite else PrioritePlainte.MOYEN
        except ValueError:
            priorite_enum = PrioritePlainte.MOYEN
        
        # Conversion de la date d'incident
        date_incident_parsed = None
        if date_incident:
            try:
                date_incident_parsed = datetime.strptime(date_incident, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Création de la plainte avec les données validées
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=titre[:500],
            description=description,
            nom_plaignant=nom_plaignant,
            prenom_plaignant=prenom_plaignant,
            email_plaignant=email_plaignant,
            telephone_plaignant=telephone_plaignant,
            mode_reception=mode_reception or "pdf_import",
            service_id=service_id,
            priorite=priorite_enum,
            statut=StatutPlainte.RECU,
            date_incident=date_incident_parsed,
            date_creation=datetime.now(),
            date_modification=datetime.now(),
            assignee_a_id=assigned_user_id
        )
        
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte créée: {new_plainte.numero_plainte} (ID: {new_plainte.id})")
        
        # Enregistrement du document PDF
        doc_record = DocumentPlainte(
            plainte_id=new_plainte.id,
            nom_fichier=pdf_file.filename,
            nom_stockage=nom_stockage,
            chemin_fichier=str(file_path),
            type_fichier=TypeFichier.PDF,
            taille_fichier=len(content),
            mime_type="application/pdf",
            description="PDF original de la plainte (document source)",
            est_piece_jointe_originale=True
        )
        db.add(doc_record)
        db.commit()
        
        logger.info(f"📎 Document attaché: {pdf_file.filename}")
        
        # Lancer l'analyse IA en arrière-plan (optionnel)
        background_tasks.add_task(launch_background_analysis, new_plainte.id)
        
        # Réponse
        return JSONResponse(
            content={
                "success": True,
                "message": "Plainte créée avec succès",
                "plainte": {
                    "id": new_plainte.id,
                    "numero_plainte": new_plainte.numero_plainte,
                    "titre": new_plainte.titre,
                    "description": new_plainte.description[:500] + "..." if len(new_plainte.description) > 500 else new_plainte.description,
                    "statut": new_plainte.statut.value,
                    "priorite": new_plainte.priorite.value,
                    "service_id": new_plainte.service_id,
                    "service_nom": service.nom,
                    "date_creation": new_plainte.date_creation.isoformat()
                },
                "plaignant": {
                    "nom": new_plainte.nom_plaignant,
                    "prenom": new_plainte.prenom_plaignant,
                    "email": new_plainte.email_plaignant,
                    "telephone": new_plainte.telephone_plaignant
                },
                "document": {
                    "nom_fichier": pdf_file.filename,
                    "taille": len(content),
                    "chemin_stockage": str(file_path)
                },
                "analyse_ia": {
                    "statut": "en_cours",
                    "message": "Analyse IA en cours en arrière-plan"
                }
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création plainte depuis données validées: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ==================== CRÉATION DEPUIS IMAGE AVEC DONNÉES VALIDÉES ====================

@router.post("/depuis-image/donnees-validees")
async def create_complaint_from_image_validated_data(
    background_tasks: BackgroundTasks,
    image_file: UploadFile = File(..., description="Image à rattacher à la plainte (jpg, png, webp)"),
    service_id: int = Form(..., description="ID du service"),
    # Données validées par l'utilisateur (obligatoires)
    titre: str = Form(..., description="Titre de la plainte (validé par l'utilisateur)"),
    description: str = Form(..., description="Description de la plainte (validée par l'utilisateur)"),
    nom_plaignant: str = Form(..., description="Nom du plaignant (validé par l'utilisateur)"),
    prenom_plaignant: str = Form(..., description="Prénom du plaignant (validé par l'utilisateur)"),
    # Données optionnelles
    email_plaignant: Optional[str] = Form(None, description="Email du plaignant"),
    telephone_plaignant: Optional[str] = Form(None, description="Téléphone du plaignant"),
    mode_reception: Optional[str] = Form("photo_import", description="Mode de réception"),
    date_incident: Optional[str] = Form(None, description="Date de l'incident (YYYY-MM-DD)"),
    priorite: Optional[str] = Form("MOYEN", description="Priorité de la plainte"),
    assigned_user_id: Optional[int] = Form(None, description="ID de l'utilisateur assigné"),
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle plainte avec les données VALIDÉES par l'utilisateur à partir d'une image.
    
    Cette route est optimisée pour être utilisée APRÈS la prévisualisation OCR.
    Elle ne refait PAS l'OCR/analyse IA - elle utilise directement les données validées.
    
    Processus:
    1. Validation des données obligatoires
    2. Upload et stockage de l'image originale
    3. Création directe de la plainte en BDD
    4. Rattachement de l'image à la plainte
    5. Lancement de l'analyse IA en arrière-plan (optionnel)
    
    Formats supportés: JPG, PNG, WEBP, TIFF, BMP, GIF
    
    Returns:
        La plainte créée avec le document attaché
    """
    try:
        logger.info(f"📷 Création plainte depuis données validées - Image: {image_file.filename}")
        logger.info(f"📝 Données: titre={titre[:50]}..., nom={nom_plaignant}, prenom={prenom_plaignant}, service={service_id}")
        
        # Vérification du type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif']
        file_ext = Path(image_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Format d'image non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Lecture et vérification de la taille
        content = await image_file.read()
        if len(content) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="L'image ne doit pas dépasser 15 MB")
        
        # Vérifier que le service existe
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Service ID {service_id} non trouvé")
        
        # Génération du numéro de plainte (utilise la fonction robuste)
        numero_plainte = generate_numero_plainte(db)
        
        # Sauvegarde de l'image originale
        upload_dir = Path("data/documents/images_originales")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        nom_stockage = f"{numero_plainte}_{image_file.filename}"
        file_path = upload_dir / nom_stockage
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"📁 Image sauvegardée: {file_path} ({len(content)} octets)")
        
        # Conversion de la priorité
        try:
            priorite_enum = PrioritePlainte(priorite) if priorite else PrioritePlainte.MOYEN
        except ValueError:
            priorite_enum = PrioritePlainte.MOYEN
        
        # Conversion de la date d'incident
        date_incident_parsed = None
        if date_incident:
            try:
                date_incident_parsed = datetime.strptime(date_incident, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Création de la plainte avec les données validées
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=titre[:500],
            description=description,
            nom_plaignant=nom_plaignant,
            prenom_plaignant=prenom_plaignant,
            email_plaignant=email_plaignant,
            telephone_plaignant=telephone_plaignant,
            mode_reception=mode_reception or "photo_import",
            service_id=service_id,
            priorite=priorite_enum,
            statut=StatutPlainte.RECU,
            date_incident=date_incident_parsed,
            date_creation=datetime.now(),
            date_modification=datetime.now(),
            assignee_a_id=assigned_user_id
        )
        
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte créée: {new_plainte.numero_plainte} (ID: {new_plainte.id})")
        
        # Déterminer le type MIME
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.webp': 'image/webp',
            '.tiff': 'image/tiff', '.bmp': 'image/bmp', '.gif': 'image/gif'
        }
        mime_type = mime_types.get(file_ext, 'image/jpeg')
        
        # Enregistrement du document Image
        doc_record = DocumentPlainte(
            plainte_id=new_plainte.id,
            nom_fichier=image_file.filename,
            nom_stockage=nom_stockage,
            chemin_fichier=str(file_path),
            type_fichier=TypeFichier.IMAGE,
            taille_fichier=len(content),
            mime_type=mime_type,
            description="Image originale de la plainte (document source OCR)",
            est_piece_jointe_originale=True
        )
        db.add(doc_record)
        db.commit()
        
        logger.info(f"📎 Document attaché: {image_file.filename}")
        
        # Lancer l'analyse IA en arrière-plan (optionnel)
        background_tasks.add_task(launch_background_analysis, new_plainte.id)
        
        # Réponse
        return JSONResponse(
            content={
                "success": True,
                "message": "Plainte créée avec succès depuis l'image",
                "plainte": {
                    "id": new_plainte.id,
                    "numero_plainte": new_plainte.numero_plainte,
                    "titre": new_plainte.titre,
                    "description": new_plainte.description[:500] + "..." if len(new_plainte.description) > 500 else new_plainte.description,
                    "statut": new_plainte.statut.value,
                    "priorite": new_plainte.priorite.value,
                    "service_id": new_plainte.service_id,
                    "service_nom": service.nom,
                    "date_creation": new_plainte.date_creation.isoformat()
                },
                "plaignant": {
                    "nom": new_plainte.nom_plaignant,
                    "prenom": new_plainte.prenom_plaignant,
                    "email": new_plainte.email_plaignant,
                    "telephone": new_plainte.telephone_plaignant
                },
                "document": {
                    "nom_fichier": image_file.filename,
                    "taille": len(content),
                    "chemin_stockage": str(file_path),
                    "type": "image"
                },
                "analyse_ia": {
                    "statut": "en_cours",
                    "message": "Analyse IA en cours en arrière-plan"
                }
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création plainte depuis image validée: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/depuis-pdf")
async def create_complaint_from_pdf(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="Fichier PDF de la plainte à analyser"),
    service_id: Optional[int] = Form(None, description="ID du service (optionnel, sera détecté automatiquement)"),
    # Données modifiées par l'utilisateur (prioritaires sur l'extraction IA)
    titre: Optional[str] = Form(None, description="Titre de la plainte (modifié par l'utilisateur)"),
    description: Optional[str] = Form(None, description="Description de la plainte (modifiée par l'utilisateur)"),
    nom_plaignant: Optional[str] = Form(None, description="Nom du plaignant (modifié par l'utilisateur)"),
    prenom_plaignant: Optional[str] = Form(None, description="Prénom du plaignant (modifié par l'utilisateur)"),
    email_plaignant: Optional[str] = Form(None, description="Email du plaignant (modifié par l'utilisateur)"),
    telephone_plaignant: Optional[str] = Form(None, description="Téléphone du plaignant (modifié par l'utilisateur)"),
    db: Session = Depends(get_db)
):
    """
    [DÉPRÉCIÉ - Utiliser /depuis-donnees-validees à la place]
    Créer une nouvelle plainte à partir d'un PDF existant.
    
    Processus:
    1. Upload et stockage du PDF original
    2. Extraction du texte via PyPDF2
    3. Analyse IA pour extraire les informations clés (Ollama/Mistral)
    4. Création automatique de la plainte en BDD avec les données extraites
    
    Returns:
        La plainte créée avec les données extraites et le statut de l'analyse
    """
    try:
        logger.info(f"📄 Début de création de plainte depuis PDF: {pdf_file.filename}")
        
        # Vérification du type de fichier
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail="Seuls les fichiers PDF sont acceptés"
            )
        
        # Vérification de la taille (max 10 MB)
        content = await pdf_file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail="Le fichier PDF ne doit pas dépasser 10 MB"
            )
        
        # Génération du numéro de plainte (utilise la fonction robuste)
        numero_plainte = generate_numero_plainte(db)
        
        # Sauvegarde du PDF original
        upload_dir = Path("data/documents/pdf_originaux")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        nom_stockage = f"{numero_plainte}_{pdf_file.filename}"
        file_path = upload_dir / nom_stockage
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"📁 PDF sauvegardé: {file_path} ({len(content)} octets)")
        
        # Extraction du texte du PDF
        extracted_data = None
        extracted_text = ""
        
        if PDF_EXTRACTION_AVAILABLE:
            try:
                # Utiliser le service de parsing de documents
                document_parser = DocumentParserService()
                extraction_result = document_parser.extract_text_from_document(str(file_path))
                
                if extraction_result["success"]:
                    extracted_text = extraction_result["text"]
                    logger.info(f"📝 Texte extrait: {len(extracted_text)} caractères")
                    
                    # Analyse IA pour extraire les données structurées
                    try:
                        llm_service = get_llm_service()
                        analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                        analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                        
                        if analysis_result.success:
                            extracted_data = json.loads(analysis_result.content)
                            logger.info(f"🤖 Données extraites par IA avec confiance: {analysis_result.confidence}")
                    except Exception as ai_error:
                        logger.warning(f"⚠️ Erreur analyse IA: {ai_error} - Utilisation extraction basique")
                else:
                    logger.warning(f"⚠️ Échec extraction texte: {extraction_result.get('error', 'Erreur inconnue')}")
            except Exception as parse_error:
                logger.error(f"❌ Erreur parsing PDF: {parse_error}")
        else:
            # Fallback: extraction basique avec PyPDF2
            try:
                import PyPDF2
                await pdf_file.seek(0)  # Reset file position
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                logger.info(f"📝 Texte extrait (fallback PyPDF2): {len(extracted_text)} caractères")
            except Exception as pdf_error:
                logger.error(f"❌ Erreur extraction PyPDF2: {pdf_error}")
        
        # Préparation des données pour la plainte
        # Les données modifiées par l'utilisateur sont prioritaires sur l'extraction IA
        plaignant_data = extracted_data.get("plaignant", {}) if extracted_data else {}
        plainte_data = extracted_data.get("plainte", {}) if extracted_data else {}
        analyse_data = extracted_data.get("analyse", {}) if extracted_data else {}
        
        # Utiliser les données utilisateur en priorité
        final_titre = titre or plainte_data.get("titre") or "Plainte importée depuis PDF"
        final_description = description or plainte_data.get("description") or (extracted_text[:2000] if extracted_text else "Contenu du PDF non extractible")
        final_nom = nom_plaignant or plaignant_data.get("nom")
        final_prenom = prenom_plaignant or plaignant_data.get("prenom")
        final_email = email_plaignant or plaignant_data.get("email")
        final_telephone = telephone_plaignant or plaignant_data.get("telephone")
        
        logger.info(f"📝 Données finales - Titre: {final_titre[:50]}..., Nom: {final_nom}, Prénom: {final_prenom}")
        
        # Détermination du service
        if not service_id:
            # Essayer de trouver le service par son nom
            service_name = plainte_data.get("service_concerne")
            if service_name:
                service = db.query(Service).filter(
                    Service.nom.ilike(f"%{service_name}%")
                ).first()
                if service:
                    service_id = service.id
            
            # Fallback: prendre le premier service disponible
            if not service_id:
                default_service = db.query(Service).filter(Service.est_actif == True).first()
                if default_service:
                    service_id = default_service.id
                else:
                    raise HTTPException(status_code=400, detail="Aucun service disponible dans le système")
        
        # Vérifier que le service existe
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Détermination de la priorité
        priorite_str = analyse_data.get("priorite_suggeree", "MOYEN")
        try:
            priorite = PrioritePlainte(priorite_str)
        except ValueError:
            priorite = PrioritePlainte.MOYEN
        
        # Conversion de la date d'incident
        date_incident = None
        date_incident_str = plainte_data.get("date_incident")
        if date_incident_str:
            try:
                date_incident = datetime.strptime(date_incident_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Création de la plainte avec les données finales (utilisateur ou IA)
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=final_titre[:500],  # Limiter la longueur du titre
            description=final_description,
            nom_plaignant=final_nom,
            prenom_plaignant=final_prenom,
            email_plaignant=final_email,
            telephone_plaignant=final_telephone,
            mode_reception=plainte_data.get("mode_reception", "pdf_import"),
            service_id=service_id,
            priorite=priorite,
            statut=StatutPlainte.RECU,
            date_incident=date_incident,
            date_creation=datetime.now(),
            date_modification=datetime.now()
        )
        
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte créée depuis PDF: {new_plainte.numero_plainte} (ID: {new_plainte.id})")
        
        # Enregistrement du document PDF original
        doc_record = DocumentPlainte(
            plainte_id=new_plainte.id,
            nom_fichier=pdf_file.filename,
            nom_stockage=nom_stockage,
            chemin_fichier=str(file_path),
            type_fichier=TypeFichier.PDF,
            taille_fichier=len(content),
            mime_type="application/pdf",
            description="PDF original de la plainte (document source)",
            est_piece_jointe_originale=True
        )
        db.add(doc_record)
        db.commit()
        
        # Création de l'enregistrement d'analyse IA avec les données extraites
        analyse_ia = AnalyseIA(
            plainte_id=new_plainte.id,
            sentiment=analyse_data.get("gravite_estimee"),
            priorite_ia=priorite_str,
            resume_ia=analyse_data.get("resume_court"),
            mots_cles_detectes=analyse_data.get("mots_cles") if isinstance(analyse_data.get("mots_cles"), list) else [],
            statut_analyse="extraction_complete" if extracted_data else "en_attente",
            confiance_sentiment=extracted_data.get("confiance_extraction", {}).get("score_global", 0.5) if extracted_data else 0.0,
            date_analyse=datetime.now()
        )
        db.add(analyse_ia)
        db.commit()
        
        # Lancer l'analyse complète en arrière-plan
        background_tasks.add_task(launch_background_analysis, new_plainte.id)
        
        # Préparer la réponse
        response_data = {
            "success": True,
            "message": "Plainte créée avec succès depuis le PDF",
            "plainte": {
                "id": new_plainte.id,
                "numero_plainte": new_plainte.numero_plainte,
                "titre": new_plainte.titre,
                "description": new_plainte.description[:500] + "..." if len(new_plainte.description) > 500 else new_plainte.description,
                "statut": new_plainte.statut.value,
                "priorite": new_plainte.priorite.value,
                "service_id": new_plainte.service_id,
                "service_nom": service.nom,
                "date_creation": new_plainte.date_creation.isoformat()
            },
            "plaignant": {
                "nom": new_plainte.nom_plaignant,
                "prenom": new_plainte.prenom_plaignant,
                "email": new_plainte.email_plaignant,
                "telephone": new_plainte.telephone_plaignant
            },
            "extraction": {
                "texte_extrait_longueur": len(extracted_text),
                "donnees_extraites": extracted_data is not None,
                "confiance": extracted_data.get("confiance_extraction", {}).get("score_global") if extracted_data else None,
                "champs_incertains": extracted_data.get("confiance_extraction", {}).get("champs_incertains") if extracted_data else []
            },
            "document": {
                "nom_fichier": pdf_file.filename,
                "taille": len(content),
                "chemin_stockage": str(file_path)
            },
            "analyse_ia": {
                "statut": "en_cours",
                "message": "Analyse IA complète en cours en arrière-plan"
            }
        }
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création plainte depuis PDF: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la plainte depuis le PDF: {str(e)}")


# ==================== PRÉVISUALISATION PDF ASYNCHRONE ====================

@router.post("/depuis-pdf/preview-async")
async def preview_pdf_extraction_async(
    pdf_file: UploadFile = File(..., description="Fichier PDF à analyser de manière asynchrone"),
    db: Session = Depends(get_db)
):
    """
    Lance l'extraction des données d'un PDF de manière ASYNCHRONE.
    Retourne immédiatement un task_id. Le résultat sera envoyé via WebSocket.
    
    Workflow:
    1. Upload du PDF et extraction du texte (rapide)
    2. Retour immédiat avec task_id
    3. Analyse IA en arrière-plan (Celery worker)
    4. Notification WebSocket quand terminé (événement 'pdf_extraction_complete')
    
    Returns:
        task_id pour suivre le traitement et recevoir les résultats via WebSocket
    """
    import uuid
    
    try:
        logger.info(f"📄 [Async] Prévisualisation PDF: {pdf_file.filename}")
        
        # Vérification du type de fichier
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
        
        # Lecture du contenu
        content = await pdf_file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Le fichier PDF ne doit pas dépasser 10 MB")
        
        # Générer un task_id unique
        task_id = str(uuid.uuid4())
        
        # Sauvegarde temporaire pour extraction du texte
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"async_{task_id}_{pdf_file.filename}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        # Extraction rapide du texte (synchrone, car rapide)
        extracted_text = ""
        try:
            if PDF_EXTRACTION_AVAILABLE:
                document_parser = DocumentParserService()
                extraction_result = document_parser.extract_text_from_document(str(temp_path))
                if extraction_result["success"]:
                    extracted_text = extraction_result["text"]
            
            if not extracted_text:
                import PyPDF2
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
        except Exception as extract_error:
            logger.error(f"❌ Erreur extraction texte PDF: {extract_error}")
            # Nettoyer si erreur
            try:
                os.remove(temp_path)
            except:
                pass
            raise HTTPException(status_code=400, detail="Impossible d'extraire le texte du PDF")
        
        # Note: On garde le fichier temp pour l'utiliser lors de la création de la plainte
        # Il sera supprimé après la création de la plainte
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Impossible d'extraire le texte du PDF")
        
        logger.info(f"📝 [Async] Texte extrait: {len(extracted_text)} caractères")
        
        # Lancer la tâche Celery pour l'analyse IA (passer aussi le temp_path)
        try:
            from healthcare_worker_server.app.tasks.celery_tasks import extract_pdf_data_async
            celery_task = extract_pdf_data_async.delay(task_id, extracted_text, pdf_file.filename, str(temp_path))
            logger.info(f"🚀 [Async] Tâche Celery lancée: {celery_task.id}")
        except Exception as celery_error:
            logger.warning(f"⚠️ Celery non disponible: {celery_error}. Extraction synchrone de secours.")
            # Fallback synchrone si Celery n'est pas disponible
            try:
                llm_service = get_llm_service()
                analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                
                if analysis_result.success:
                    extracted_data = json.loads(analysis_result.content)
                else:
                    extracted_data = _extract_basic_data_from_text(extracted_text)
                
                # Récupérer la liste des services disponibles
                services = db.query(Service).filter(Service.est_actif == True).all()
                services_list = [{"id": s.id, "nom": s.nom, "code": s.code_service} for s in services]
                
                return JSONResponse(content={
                    "success": True,
                    "async": False,  # Indique que c'est une réponse synchrone (fallback)
                    "task_id": task_id,
                    "filename": pdf_file.filename,
                    "temp_file_path": str(temp_path),  # Chemin du fichier temp
                    "extraction": {
                        "texte_brut": extracted_text[:3000],
                        "texte_longueur": len(extracted_text),
                        "donnees_structurees": extracted_data
                    },
                    "services_disponibles": services_list,
                    "message": "Extraction terminée (mode synchrone)"
                })
            except Exception as sync_error:
                logger.error(f"❌ Erreur extraction synchrone: {sync_error}")
                raise HTTPException(status_code=500, detail=str(sync_error))
        
        # Récupérer la liste des services disponibles
        services = db.query(Service).filter(Service.est_actif == True).all()
        services_list = [{"id": s.id, "nom": s.nom, "code": s.code_service} for s in services]
        
        # Retourner immédiatement avec le task_id et le chemin du fichier temp
        return JSONResponse(content={
            "success": True,
            "async": True,
            "task_id": task_id,
            "celery_task_id": celery_task.id,
            "filename": pdf_file.filename,
            "file_size": len(content),
            "text_length": len(extracted_text),
            "temp_file_path": str(temp_path),  # Chemin du fichier temp pour création plainte
            "services_disponibles": services_list,
            "message": "Analyse IA en cours. Vous serez notifié via WebSocket quand elle sera terminée.",
            "websocket_events": {
                "started": "pdf_extraction_started",
                "complete": "pdf_extraction_complete", 
                "failed": "pdf_extraction_failed"
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation async PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/depuis-pdf/preview")
async def preview_pdf_extraction(
    pdf_file: UploadFile = File(..., description="Fichier PDF à analyser pour prévisualisation"),
    db: Session = Depends(get_db)
):
    """
    Prévisualise l'extraction des données d'un PDF sans créer de plainte.
    Permet à l'utilisateur de vérifier et corriger les données avant la création.
    
    Returns:
        Les données extraites du PDF pour validation par l'utilisateur
    """
    try:
        logger.info(f"👁️ Prévisualisation de l'extraction PDF: {pdf_file.filename}")
        
        # Vérification du type de fichier
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail="Seuls les fichiers PDF sont acceptés"
            )
        
        # Lecture du contenu
        content = await pdf_file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail="Le fichier PDF ne doit pas dépasser 10 MB"
            )
        
        # Sauvegarde temporaire pour analyse
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"preview_{datetime.now().strftime('%Y%m%d%H%M%S')}_{pdf_file.filename}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        extracted_text = ""
        extracted_data = None
        
        try:
            # Étape 1: Extraction du texte
            if PDF_EXTRACTION_AVAILABLE:
                document_parser = DocumentParserService()
                extraction_result = document_parser.extract_text_from_document(str(temp_path))
                
                if extraction_result["success"]:
                    extracted_text = extraction_result["text"]
                    logger.info(f"✅ Texte extrait via DocumentParserService: {len(extracted_text)} caractères")
                else:
                    logger.warning(f"⚠️ Échec DocumentParserService, fallback PyPDF2")
                    # Fallback PyPDF2
                    import PyPDF2
                    with open(temp_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n"
            else:
                # Fallback PyPDF2
                logger.info("📄 Extraction du texte via PyPDF2 (fallback)")
                import PyPDF2
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                logger.info(f"✅ Texte extrait via PyPDF2: {len(extracted_text)} caractères")
            
            # Étape 2: Analyse IA (toujours essayer si on a du texte)
            if extracted_text:
                try:
                    logger.info("🤖 Démarrage de l'analyse IA...")
                    llm_service = get_llm_service()
                    logger.info(f"📡 Service LLM utilisé: {type(llm_service).__name__}")
                    analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                    analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                    
                    if analysis_result.success:
                        extracted_data = json.loads(analysis_result.content)
                        logger.info(f"✅ Données extraites par IA: {list(extracted_data.keys()) if extracted_data else 'None'}")
                    else:
                        logger.warning(f"⚠️ Analyse IA non réussie, utilisation du fallback regex")
                except Exception as ai_error:
                    logger.warning(f"⚠️ Erreur analyse IA preview: {ai_error}")
                    import traceback
                    traceback.print_exc()
            
            # Étape 3: Fallback extraction basique si pas de données IA
            if extracted_data is None and extracted_text:
                logger.info("🔄 Utilisation de l'extraction basique (regex) comme fallback")
                extracted_data = _extract_basic_data_from_text(extracted_text)
                
        finally:
            # Nettoyer le fichier temporaire
            try:
                os.remove(temp_path)
            except:
                pass
        
        # Récupérer la liste des services disponibles
        services = db.query(Service).filter(Service.est_actif == True).all()
        services_list = [{"id": s.id, "nom": s.nom, "code": s.code_service} for s in services]
        
        response_data = {
            "success": True,
            "filename": pdf_file.filename,
            "file_size": len(content),
            "extraction": {
                "texte_brut": extracted_text[:3000] if len(extracted_text) > 3000 else extracted_text,
                "texte_longueur": len(extracted_text),
                "donnees_structurees": extracted_data
            },
            "services_disponibles": services_list,
            "message": "Prévisualisation réussie. Vérifiez les données avant de créer la plainte."
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prévisualisation: {str(e)}")


# ==================== CRÉATION DEPUIS IMAGE (PHOTO) ====================

@router.post("/depuis-image/preview")
async def preview_image_extraction(
    image_file: UploadFile = File(..., description="Image à analyser pour prévisualisation (jpg, png, webp)"),
    db: Session = Depends(get_db)
):
    """
    Prévisualise l'extraction des données d'une image via OCR sans créer de plainte.
    Permet à l'utilisateur de vérifier et corriger les données avant la création.
    
    Formats supportés: JPG, PNG, WEBP, TIFF, BMP, GIF
    
    Returns:
        Les données extraites de l'image pour validation par l'utilisateur
    """
    try:
        logger.info(f"👁️ Prévisualisation de l'extraction image: {image_file.filename}")
        
        # Vérification du type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif']
        file_ext = Path(image_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Format d'image non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Lecture du contenu
        content = await image_file.read()
        if len(content) > 15 * 1024 * 1024:  # 15 MB pour les images
            raise HTTPException(
                status_code=400, 
                detail="L'image ne doit pas dépasser 15 MB"
            )
        
        extracted_text = ""
        extracted_data = None
        ocr_confidence = 0.0
        ocr_metadata = {}
        
        # Étape 1: Extraction du texte via OCR
        if IMAGE_OCR_AVAILABLE:
            try:
                ocr_service = get_ocr_service()
                ocr_result = ocr_service.extract_text_from_image(content, image_file.filename)
                
                if ocr_result["success"]:
                    extracted_text = ocr_result["text"]
                    ocr_confidence = ocr_result.get("confidence", 0.5)
                    ocr_metadata = ocr_result.get("metadata", {})
                    logger.info(f"✅ Texte extrait via OCR: {len(extracted_text)} caractères, confiance: {ocr_confidence:.2f}")
                else:
                    logger.warning(f"⚠️ OCR échoué: {ocr_result.get('error', 'Erreur inconnue')}")
            except Exception as ocr_error:
                logger.error(f"❌ Erreur OCR: {ocr_error}")
        else:
            # Fallback: utiliser pytesseract directement
            logger.info("📄 Extraction du texte via pytesseract (fallback)")
            try:
                from PIL import Image
                import pytesseract
                import io
                
                image = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(image, config=r'--oem 3 --psm 6 -l fra+eng')
                ocr_confidence = 0.5  # Confiance par défaut sans métadonnées
                logger.info(f"✅ Texte extrait via pytesseract fallback: {len(extracted_text)} caractères")
            except Exception as fallback_error:
                logger.error(f"❌ Erreur pytesseract fallback: {fallback_error}")
        
        # Étape 2: Analyse IA (si on a du texte)
        if extracted_text and PDF_EXTRACTION_AVAILABLE:
            try:
                logger.info("🤖 Démarrage de l'analyse IA...")
                llm_service = get_llm_service()
                logger.info(f"📡 Service LLM utilisé: {type(llm_service).__name__}")
                analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                
                if analysis_result.success:
                    extracted_data = json.loads(analysis_result.content)
                    logger.info(f"✅ Données extraites par IA: {list(extracted_data.keys()) if extracted_data else 'None'}")
                else:
                    logger.warning(f"⚠️ Analyse IA non réussie, utilisation du fallback regex")
            except Exception as ai_error:
                logger.warning(f"⚠️ Erreur analyse IA preview: {ai_error}")
                import traceback
                traceback.print_exc()
        
        # Étape 3: Fallback extraction basique si pas de données IA
        if extracted_data is None and extracted_text:
            logger.info("🔄 Utilisation de l'extraction basique (regex) comme fallback")
            extracted_data = _extract_basic_data_from_text(extracted_text)
            # Ajuster le mode de réception pour les images
            if extracted_data and extracted_data.get("plainte"):
                extracted_data["plainte"]["mode_reception"] = "photo_import"
        
        # Ajouter les informations OCR à la confiance d'extraction
        if extracted_data:
            if "confiance_extraction" not in extracted_data:
                extracted_data["confiance_extraction"] = {}
            extracted_data["confiance_extraction"]["score_ocr"] = ocr_confidence
            extracted_data["confiance_extraction"]["qualite_ocr"] = (
                "excellent" if ocr_confidence >= 0.8 else
                "bon" if ocr_confidence >= 0.6 else
                "moyen" if ocr_confidence >= 0.4 else
                "faible"
            )
        
        # Récupérer la liste des services disponibles
        services = db.query(Service).filter(Service.est_actif == True).all()
        services_list = [{"id": s.id, "nom": s.nom, "code": s.code_service} for s in services]
        
        response_data = {
            "success": True,
            "filename": image_file.filename,
            "file_size": len(content),
            "extraction": {
                "texte_brut": extracted_text[:3000] if len(extracted_text) > 3000 else extracted_text,
                "texte_longueur": len(extracted_text),
                "donnees_structurees": extracted_data
            },
            "ocr_info": {
                "confiance": ocr_confidence,
                "qualite": (
                    "excellent" if ocr_confidence >= 0.8 else
                    "bon" if ocr_confidence >= 0.6 else
                    "moyen" if ocr_confidence >= 0.4 else
                    "faible"
                ),
                "metadata": ocr_metadata
            },
            "services_disponibles": services_list,
            "message": "Prévisualisation réussie. Vérifiez les données extraites par OCR avant de créer la plainte."
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation image: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prévisualisation: {str(e)}")


# ==================== PRÉVISUALISATION IMAGE ASYNCHRONE ====================

@router.post("/depuis-image/preview-async")
async def preview_image_extraction_async(
    image_file: UploadFile = File(..., description="Image à analyser de manière asynchrone"),
    db: Session = Depends(get_db)
):
    """
    Lance l'extraction des données d'une image de manière ASYNCHRONE.
    Retourne immédiatement un task_id. Le résultat sera envoyé via WebSocket.
    
    Workflow:
    1. Upload de l'image et sauvegarde temporaire
    2. Retour immédiat avec task_id
    3. OCR + Analyse IA en arrière-plan (Celery worker)
    4. Notification WebSocket quand terminé (événement 'image_extraction_complete')
    
    Returns:
        task_id pour suivre le traitement et recevoir les résultats via WebSocket
    """
    import uuid
    
    try:
        logger.info(f"📷 [Async] Prévisualisation Image: {image_file.filename}")
        
        # Vérification du type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif']
        file_ext = Path(image_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Format d'image non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Lecture du contenu
        content = await image_file.read()
        if len(content) > 15 * 1024 * 1024:  # 15 MB pour les images
            raise HTTPException(
                status_code=400, 
                detail="L'image ne doit pas dépasser 15 MB"
            )
        
        # Générer un task_id unique
        task_id = str(uuid.uuid4())
        
        # Sauvegarde temporaire pour l'analyse OCR par le worker
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"async_{task_id}_{image_file.filename}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"📁 [Async] Image sauvegardée temporairement: {temp_path}")
        
        # Récupérer la liste des services disponibles (pour le frontend)
        services = db.query(Service).filter(Service.est_actif == True).all()
        services_list = [{"id": s.id, "nom": s.nom, "code": s.code_service} for s in services]
        
        # Lancer la tâche Celery pour l'OCR + analyse IA
        try:
            from healthcare_worker_server.app.tasks.celery_tasks import extract_image_data_async
            celery_task = extract_image_data_async.delay(task_id, str(temp_path), image_file.filename)
            logger.info(f"🚀 [Async] Tâche Celery lancée: {celery_task.id}")
            
            return JSONResponse(content={
                "success": True,
                "async": True,
                "task_id": task_id,
                "celery_task_id": celery_task.id,
                "filename": image_file.filename,
                "file_size": len(content),
                "temp_file_path": str(temp_path),  # Chemin du fichier temp pour création plainte
                "services_disponibles": services_list,
                "message": "Analyse OCR et IA en cours. Vous recevrez le résultat via WebSocket (événement 'image_extraction_complete')."
            })
            
        except Exception as celery_error:
            logger.warning(f"⚠️ Celery non disponible: {celery_error}. Extraction synchrone de secours.")
            
            # Fallback synchrone si Celery n'est pas disponible
            try:
                extracted_text = ""
                ocr_confidence = 0.0
                extracted_data = None
                
                # OCR synchrone
                if IMAGE_OCR_AVAILABLE:
                    ocr_service = get_ocr_service()
                    ocr_result = ocr_service.extract_text_from_image(content, image_file.filename)
                    
                    if ocr_result["success"]:
                        extracted_text = ocr_result["text"]
                        ocr_confidence = ocr_result.get("confidence", 0.5)
                else:
                    # Fallback pytesseract
                    from PIL import Image
                    import pytesseract
                    import io
                    
                    image = Image.open(io.BytesIO(content))
                    extracted_text = pytesseract.image_to_string(image, config=r'--oem 3 --psm 6 -l fra+eng')
                    ocr_confidence = 0.5
                
                # Analyse IA synchrone
                if extracted_text and PDF_EXTRACTION_AVAILABLE:
                    llm_service = get_llm_service()
                    analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                    analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                    
                    if analysis_result.success:
                        extracted_data = json.loads(analysis_result.content)
                    else:
                        extracted_data = _extract_basic_data_from_text(extracted_text)
                elif extracted_text:
                    extracted_data = _extract_basic_data_from_text(extracted_text)
                
                # Ajuster le mode de réception
                if extracted_data and extracted_data.get("plainte"):
                    extracted_data["plainte"]["mode_reception"] = "photo_import"
                
                # Nettoyer le fichier temporaire
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                return JSONResponse(content={
                    "success": True,
                    "async": False,  # Indique que c'est une réponse synchrone (fallback)
                    "task_id": task_id,
                    "filename": image_file.filename,
                    "extraction": {
                        "texte_brut": extracted_text[:3000] if len(extracted_text) > 3000 else extracted_text,
                        "texte_longueur": len(extracted_text),
                        "donnees_structurees": extracted_data
                    },
                    "ocr_info": {
                        "confiance": ocr_confidence,
                        "qualite": (
                            "excellent" if ocr_confidence >= 0.8 else
                            "bon" if ocr_confidence >= 0.6 else
                            "moyen" if ocr_confidence >= 0.4 else
                            "faible"
                        )
                    },
                    "services_disponibles": services_list,
                    "message": "Extraction réalisée de manière synchrone (Celery non disponible)."
                })
                
            except Exception as sync_error:
                # Nettoyer le fichier temporaire en cas d'erreur
                try:
                    os.remove(temp_path)
                except:
                    pass
                raise HTTPException(status_code=500, detail=f"Erreur extraction synchrone: {str(sync_error)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur prévisualisation image async: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prévisualisation: {str(e)}")


@router.post("/depuis-image")
async def create_complaint_from_image(
    background_tasks: BackgroundTasks,
    image_file: UploadFile = File(..., description="Image de la plainte à analyser (jpg, png, webp)"),
    service_id: Optional[int] = Form(None, description="ID du service (optionnel, sera détecté automatiquement)"),
    # Données modifiées par l'utilisateur (prioritaires sur l'extraction OCR)
    titre: Optional[str] = Form(None, description="Titre de la plainte (modifié par l'utilisateur)"),
    description: Optional[str] = Form(None, description="Description de la plainte (modifiée par l'utilisateur)"),
    nom_plaignant: Optional[str] = Form(None, description="Nom du plaignant (modifié par l'utilisateur)"),
    prenom_plaignant: Optional[str] = Form(None, description="Prénom du plaignant (modifié par l'utilisateur)"),
    email_plaignant: Optional[str] = Form(None, description="Email du plaignant (modifié par l'utilisateur)"),
    telephone_plaignant: Optional[str] = Form(None, description="Téléphone du plaignant (modifié par l'utilisateur)"),
    mode_reception: Optional[str] = Form("photo_import", description="Mode de réception"),
    date_incident: Optional[str] = Form(None, description="Date de l'incident"),
    priorite: Optional[str] = Form("MOYEN", description="Priorité de la plainte"),
    assigned_user_id: Optional[int] = Form(None, description="ID de l'utilisateur assigné"),
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle plainte à partir d'une image (photo de document).
    
    Processus:
    1. Upload et stockage de l'image originale
    2. Extraction du texte via OCR (Tesseract)
    3. Analyse IA pour extraire les informations clés (Ollama/Mistral)
    4. Création automatique de la plainte en BDD avec les données extraites
    
    Formats supportés: JPG, PNG, WEBP, TIFF, BMP, GIF
    
    Returns:
        La plainte créée avec les données extraites et le statut de l'analyse
    """
    try:
        logger.info(f"📷 Début de création de plainte depuis image: {image_file.filename}")
        
        # Vérification du type de fichier
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif']
        file_ext = Path(image_file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Format d'image non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Vérification de la taille (max 15 MB)
        content = await image_file.read()
        if len(content) > 15 * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail="L'image ne doit pas dépasser 15 MB"
            )
        
        # Génération du numéro de plainte (utilise la fonction robuste)
        numero_plainte = generate_numero_plainte(db)
        
        # Sauvegarde de l'image originale
        upload_dir = Path("data/documents/images_originales")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        nom_stockage = f"{numero_plainte}_{image_file.filename}"
        file_path = upload_dir / nom_stockage
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"📁 Image sauvegardée: {file_path} ({len(content)} octets)")
        
        # Extraction du texte via OCR
        extracted_data = None
        extracted_text = ""
        ocr_confidence = 0.0
        
        if IMAGE_OCR_AVAILABLE:
            try:
                ocr_service = get_ocr_service()
                ocr_result = ocr_service.extract_text_from_image(content, image_file.filename)
                
                if ocr_result["success"]:
                    extracted_text = ocr_result["text"]
                    ocr_confidence = ocr_result.get("confidence", 0.5)
                    logger.info(f"📝 Texte extrait par OCR: {len(extracted_text)} caractères, confiance: {ocr_confidence:.2f}")
                    
                    # Analyse IA pour extraire les données structurées
                    if PDF_EXTRACTION_AVAILABLE:
                        try:
                            llm_service = get_llm_service()
                            analysis_service = ComplaintAnalysisService(llm_provider=llm_service)
                            analysis_result = analysis_service.extract_complaint_data_from_pdf(extracted_text)
                            
                            if analysis_result.success:
                                extracted_data = json.loads(analysis_result.content)
                                logger.info(f"🤖 Données extraites par IA avec confiance: {analysis_result.confidence}")
                        except Exception as ai_error:
                            logger.warning(f"⚠️ Erreur analyse IA: {ai_error} - Utilisation extraction basique")
                else:
                    logger.warning(f"⚠️ Échec OCR: {ocr_result.get('error', 'Erreur inconnue')}")
            except Exception as ocr_error:
                logger.error(f"❌ Erreur OCR: {ocr_error}")
        else:
            # Fallback: extraction basique avec pytesseract
            try:
                from PIL import Image
                import pytesseract
                import io
                
                image = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(image, config=r'--oem 3 --psm 6 -l fra+eng')
                ocr_confidence = 0.5
                logger.info(f"📝 Texte extrait (fallback pytesseract): {len(extracted_text)} caractères")
            except Exception as ocr_error:
                logger.error(f"❌ Erreur extraction pytesseract: {ocr_error}")
        
        # Préparation des données pour la plainte
        # Les données modifiées par l'utilisateur sont prioritaires sur l'extraction OCR
        plaignant_data = extracted_data.get("plaignant", {}) if extracted_data else {}
        plainte_data = extracted_data.get("plainte", {}) if extracted_data else {}
        analyse_data = extracted_data.get("analyse", {}) if extracted_data else {}
        
        # Utiliser les données utilisateur en priorité
        final_titre = titre or plainte_data.get("titre") or "Plainte importée depuis image"
        final_description = description or plainte_data.get("description") or (extracted_text[:2000] if extracted_text else "Contenu de l'image non extractible")
        final_nom = nom_plaignant or plaignant_data.get("nom")
        final_prenom = prenom_plaignant or plaignant_data.get("prenom")
        final_email = email_plaignant or plaignant_data.get("email")
        final_telephone = telephone_plaignant or plaignant_data.get("telephone")
        
        # Priorité: utilisateur > IA > défaut
        final_priorite = priorite or analyse_data.get("priorite_suggeree", "MOYEN")
        
        # Mode de réception par défaut pour les images
        final_mode_reception = mode_reception or plainte_data.get("mode_reception") or "photo_import"
        
        # Date incident
        final_date_incident = None
        if date_incident:
            try:
                final_date_incident = datetime.strptime(date_incident, "%Y-%m-%d")
            except:
                pass
        elif plainte_data.get("date_incident"):
            try:
                final_date_incident = datetime.strptime(plainte_data["date_incident"], "%Y-%m-%d")
            except:
                pass
        
        # Sélection du service
        if service_id:
            service = db.query(Service).filter(Service.id == service_id).first()
        else:
            # Essayer de trouver via l'extraction
            service_nom = plainte_data.get("service_concerne")
            if service_nom:
                service = db.query(Service).filter(
                    Service.nom.ilike(f"%{service_nom}%")
                ).first()
            else:
                service = None
        
        # Service par défaut si non trouvé
        if not service:
            service = db.query(Service).filter(Service.est_actif == True).first()
            if not service:
                raise HTTPException(
                    status_code=400, 
                    detail="Aucun service disponible dans le système"
                )
        
        # Créer la plainte en base
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=final_titre[:200],  # Limiter la longueur
            description=final_description,
            statut=StatutPlainte.NOUVELLE,
            priorite=PrioritePlainte(final_priorite) if final_priorite in [p.value for p in PrioritePlainte] else PrioritePlainte.MOYEN,
            service_id=service.id,
            mode_reception=final_mode_reception,
            date_incident=final_date_incident,
            # Informations du plaignant
            nom_plaignant=final_nom,
            prenom_plaignant=final_prenom,
            email_plaignant=final_email,
            telephone_plaignant=final_telephone,
            # Métadonnées
            source_document=str(file_path),
            texte_original=extracted_text[:10000] if extracted_text else None,  # Limiter la taille
            assignee_a_id=assigned_user_id
        )
        
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte créée: {numero_plainte} (ID: {new_plainte.id})")
        
        # Créer l'entrée DocumentPlainte pour l'image
        try:
            document = DocumentPlainte(
                plainte_id=new_plainte.id,
                nom_fichier=image_file.filename,
                nom_fichier_stockage=nom_stockage,
                chemin_stockage=str(file_path),
                type_fichier=TypeFichier.IMAGE,
                taille_fichier=len(content),
                mime_type=f"image/{file_ext.replace('.', '')}",
                description="Image originale de la plainte (import OCR)"
            )
            db.add(document)
            db.commit()
            logger.info(f"📄 Document image enregistré en BDD")
        except Exception as doc_error:
            logger.warning(f"⚠️ Erreur enregistrement document: {doc_error}")
        
        # Lancer l'analyse complète en arrière-plan
        background_tasks.add_task(launch_background_analysis, new_plainte.id)
        
        # Préparer la réponse
        response_data = {
            "success": True,
            "message": "Plainte créée avec succès depuis l'image",
            "plainte": {
                "id": new_plainte.id,
                "numero_plainte": new_plainte.numero_plainte,
                "titre": new_plainte.titre,
                "description": new_plainte.description[:500] + "..." if len(new_plainte.description) > 500 else new_plainte.description,
                "statut": new_plainte.statut.value,
                "priorite": new_plainte.priorite.value,
                "service_id": new_plainte.service_id,
                "service_nom": service.nom,
                "date_creation": new_plainte.date_creation.isoformat()
            },
            "plaignant": {
                "nom": new_plainte.nom_plaignant,
                "prenom": new_plainte.prenom_plaignant,
                "email": new_plainte.email_plaignant,
                "telephone": new_plainte.telephone_plaignant
            },
            "extraction": {
                "texte_extrait_longueur": len(extracted_text),
                "donnees_extraites": extracted_data is not None,
                "confiance_ocr": ocr_confidence,
                "confiance": extracted_data.get("confiance_extraction", {}).get("score_global") if extracted_data else None,
                "champs_incertains": extracted_data.get("confiance_extraction", {}).get("champs_incertains") if extracted_data else []
            },
            "document": {
                "nom_fichier": image_file.filename,
                "taille": len(content),
                "chemin_stockage": str(file_path)
            },
            "analyse_ia": {
                "statut": "en_cours",
                "message": "Analyse IA complète en cours en arrière-plan"
            }
        }
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création plainte depuis image: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la plainte depuis l'image: {str(e)}")


# ==================== CRÉATION PLAINTE DEPUIS FICHIER TEMPORAIRE ====================

@router.post("/depuis-temp")
async def create_plainte_from_temp_file(
    temp_file_path: str = Form(..., description="Chemin du fichier temporaire sur le serveur"),
    file_type: str = Form(..., description="Type de fichier: 'pdf' ou 'image'"),
    service_id: int = Form(..., description="ID du service concerné"),
    titre: str = Form(..., description="Titre de la plainte"),
    description: str = Form(..., description="Description de la plainte"),
    nom_plaignant: str = Form(..., description="Nom du plaignant"),
    prenom_plaignant: str = Form(..., description="Prénom du plaignant"),
    email_plaignant: Optional[str] = Form(None, description="Email du plaignant"),
    telephone_plaignant: Optional[str] = Form(None, description="Téléphone du plaignant"),
    mode_reception: Optional[str] = Form("document_import", description="Mode de réception"),
    date_incident: Optional[str] = Form(None, description="Date de l'incident"),
    priorite: Optional[str] = Form("MOYEN", description="Priorité"),
    assigned_user_id: Optional[int] = Form(None, description="ID de l'utilisateur assigné"),
    db: Session = Depends(get_db)
):
    """
    Crée une plainte à partir d'un fichier temporaire déjà uploadé et analysé.
    
    Ce endpoint est utilisé quand l'utilisateur a navigué pendant le traitement OCR/IA
    et revient pour créer la plainte. Le fichier est récupéré depuis le dossier temp.
    
    Args:
        temp_file_path: Chemin vers le fichier temporaire (data/temp/async_xxx_filename.ext)
        file_type: 'pdf' ou 'image'
        service_id: ID du service concerné
        ... autres champs du formulaire
    
    Returns:
        Plainte créée avec document attaché
    """
    try:
        logger.info(f"📁 Création plainte depuis fichier temp: {temp_file_path}")
        
        # Vérifier que le fichier temp existe
        temp_path = Path(temp_file_path)
        if not temp_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Le fichier temporaire n'existe plus. Veuillez re-uploader le document."
            )
        
        # Vérifier que le fichier est bien dans le dossier temp (sécurité)
        allowed_temp_dirs = [Path("data/temp"), Path("./data/temp")]
        is_valid_path = any(
            str(temp_path.resolve()).startswith(str(allowed_dir.resolve()))
            for allowed_dir in allowed_temp_dirs
            if allowed_dir.exists()
        )
        
        if not is_valid_path and "data/temp" not in str(temp_path):
            raise HTTPException(
                status_code=403,
                detail="Accès non autorisé à ce fichier"
            )
        
        # Lire le contenu du fichier
        with open(temp_path, "rb") as f:
            content = f.read()
        
        # Récupérer le nom de fichier original (sans le préfixe async_uuid_)
        original_filename = temp_path.name
        if original_filename.startswith("async_"):
            # Format: async_{task_id}_{original_filename}
            parts = original_filename.split("_", 2)
            if len(parts) >= 3:
                original_filename = parts[2]
        
        logger.info(f"📄 Fichier récupéré: {original_filename} ({len(content)} bytes)")
        
        # Vérifier le service
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            service = db.query(Service).first()
            if not service:
                raise HTTPException(status_code=400, detail="Aucun service disponible")
        
        # Génération du numéro de plainte (robuste avec MAX au lieu de COUNT)
        current_year = datetime.now().year
        prefix = f"PL_{current_year}_"
        
        # Trouver le dernier numéro utilisé pour cette année
        last_plainte = db.query(Plainte.numero_plainte).filter(
            Plainte.numero_plainte.like(f"{prefix}%")
        ).order_by(Plainte.numero_plainte.desc()).first()
        
        if last_plainte and last_plainte[0]:
            try:
                last_num = int(last_plainte[0].replace(prefix, ""))
                next_num = last_num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        
        numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
        
        # Vérification de sécurité: s'assurer que le numéro n'existe pas déjà
        while db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first():
            next_num += 1
            numero_plainte = f"{prefix}{str(next_num).zfill(4)}"
        
        # Convertir la priorité
        priorite_enum = PrioritePlainte.MOYEN
        if priorite:
            try:
                priorite_enum = PrioritePlainte(priorite.upper())
            except ValueError:
                priorite_enum = PrioritePlainte.MOYEN
        
        new_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=titre,
            description=description,
            statut=StatutPlainte.RECU,
            priorite=priorite_enum,
            service_id=service.id,
            assignee_a_id=assigned_user_id if assigned_user_id else None,
            date_incident=datetime.strptime(date_incident, "%Y-%m-%d").date() if date_incident else None,
            nom_plaignant=nom_plaignant,
            prenom_plaignant=prenom_plaignant,
            email_plaignant=email_plaignant,
            telephone_plaignant=telephone_plaignant,
            mode_reception=mode_reception or ("pdf_import" if file_type == "pdf" else "photo_import")
        )
        
        db.add(new_plainte)
        db.flush()
        
        # Déterminer le dossier de destination
        if file_type == "image":
            docs_dir = Path("data/documents/images_originales")
        else:
            docs_dir = Path("data/documents/pdf_originaux")
        
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom de fichier final avec numéro de plainte
        safe_filename = original_filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
        final_filename = f"{numero_plainte}_{safe_filename}"
        file_path = docs_dir / final_filename
        
        # Déplacer le fichier temp vers le dossier documents
        import shutil
        shutil.move(str(temp_path), str(file_path))
        logger.info(f"📂 Fichier déplacé: {temp_path} → {file_path}")
        
        # Déterminer le type de fichier
        type_fichier = TypeFichier.AUTRE
        if file_type == "pdf":
            type_fichier = TypeFichier.PDF
        elif file_type == "image":
            type_fichier = TypeFichier.IMAGE
        
        # Créer le document associé
        document = DocumentPlainte(
            plainte_id=new_plainte.id,
            nom_fichier=original_filename,
            nom_stockage=final_filename,
            chemin_fichier=str(file_path),
            type_fichier=type_fichier,
            taille_fichier=len(content),
            est_piece_jointe_originale=True
        )
        
        db.add(document)
        db.commit()
        db.refresh(new_plainte)
        
        logger.info(f"✅ Plainte {numero_plainte} créée depuis fichier temp")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Plainte {numero_plainte} créée avec succès",
            "plainte": {
                "id": new_plainte.id,
                "numero_plainte": numero_plainte,
                "titre": titre,
                "description": description[:200] + "..." if len(description) > 200 else description,
                "statut": new_plainte.statut.value if hasattr(new_plainte.statut, 'value') else str(new_plainte.statut),
                "priorite": new_plainte.priorite.value if hasattr(new_plainte.priorite, 'value') else str(new_plainte.priorite),
                "service_id": service.id,
                "service_nom": service.nom,
                "date_creation": new_plainte.date_creation.isoformat() if new_plainte.date_creation else None
            },
            "plaignant": {
                "nom": nom_plaignant,
                "prenom": prenom_plaignant,
                "email": email_plaignant,
                "telephone": telephone_plaignant
            },
            "document": {
                "nom_fichier": original_filename,
                "taille": len(content),
                "chemin_stockage": str(file_path),
                "type": file_type
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création plainte depuis fichier temp: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
