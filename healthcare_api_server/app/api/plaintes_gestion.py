#!/usr/bin/env python3
"""
API GESTION PLAINTES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour la gestion, consultation, modification et analyse des plaintes
Toutes les opérations SAUF la création des plaintes
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func, case
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta
from pathlib import Path
import os

from ..db.database import get_db
from shared.models import Plainte, User, UserRole, Service, Analyse, StatutPlainte, DocumentPlainte, AnalyseIA, NotePlainte
from shared.schemas import (
    PlainteCreate, PlainteUpdate, PlainteResponse,
    AnalyseTaskRequest, TaskStatus, PaginatedResponse, AnalyseResponse, DocumentPlainteResponse
)
# Authentification et contrôle de rôle : get_current_user et require_role
# sont définis dans core/auth.py — on les importe, on ne les réécrit pas.
from ..core.auth import get_current_user, require_role
from ..core.storage import assert_within, file_sha256
from ..services.task_manager import trigger_analyse_plainte
from ..services.audit import log_audit, get_historique
from ..services.notifications import send_email_safe
from ..core.config import settings

logger = logging.getLogger(__name__)

# Répertoire d'archive autorisé pour le téléchargement de documents (anti
# path-traversal, finding C6). Tous les documents sont stockés sous
# `data/documents` relativement au répertoire de travail du backend.
REPERTOIRE_ARCHIVE_AUTORISE = Path("data/documents").resolve()

router = APIRouter(prefix="/plaintes", tags=["Plaintes - Gestion"])

@router.get("/", response_model=PaginatedResponse[dict])
def get_plaintes(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments par page"),
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    service_id: Optional[int] = Query(None, description="Filtrer par service"),
    assigned_user_id: Optional[int] = Query(None, description="Filtrer par utilisateur assigné"),
    en_retard: Optional[bool] = Query(None, description="Filtrer les plaintes en retard (délai dépassé, non clôturées)"),
    search: Optional[str] = Query(None, description="Recherche dans titre et description"),
    date_debut: Optional[datetime] = Query(None, description="Date de début (format: YYYY-MM-DD)"),
    date_fin: Optional[datetime] = Query(None, description="Date de fin (format: YYYY-MM-DD)"),
    sort_by: str = Query("date_creation", description="Champ de tri"),
    sort_order: str = Query("desc", description="Ordre de tri (asc/desc)"),
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des plaintes avec pagination et filtres
    """
    try:
        # Construction de la requête de base
        # On exclut systématiquement les plaintes soft-deletées (date_suppression non nul, finding C5).
        query = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses)
        ).filter(Plainte.date_suppression.is_(None))

        # Application des filtres
        if statut:
            try:
                statut_enum = StatutPlainte(statut)
                query = query.filter(Plainte.statut == statut_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Statut invalide: {statut}")

        if service_id:
            query = query.filter(Plainte.service_id == service_id)

        if assigned_user_id:
            # La colonne réelle du modèle est `assignee_a_id` (pas `assigned_user_id`)
            query = query.filter(Plainte.assignee_a_id == assigned_user_id)

        if en_retard is not None:
            today = datetime.now().date()
            overdue = and_(
                Plainte.date_limite_reponse.isnot(None),
                Plainte.date_limite_reponse < today,
                Plainte.statut.notin_([StatutPlainte.TRAITE, StatutPlainte.CLOTURE]),
            )
            query = query.filter(overdue if en_retard else ~overdue)

        if search:
            search_filter = or_(
                Plainte.titre.ilike(f"%{search}%"),
                Plainte.description.ilike(f"%{search}%"),
                Plainte.nom_plaignant.ilike(f"%{search}%"),
                Plainte.prenom_plaignant.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Si aucune date n'est fournie, retourner uniquement les 3 derniers mois par défaut
        if date_debut is None and date_fin is None:
            date_debut = datetime.now() - timedelta(days=90)  # 3 mois par défaut
            logger.info(f"📅 Aucune date fournie - Application du filtre par défaut: 3 derniers mois depuis {date_debut.date()}")
        
        if date_debut:
            query = query.filter(Plainte.date_creation >= date_debut)

        if date_fin:
            # Ajouter 1 jour pour inclure toute la journée de fin
            date_fin_inclusive = date_fin + timedelta(days=1)
            query = query.filter(Plainte.date_creation < date_fin_inclusive)

        # Tri
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(Plainte, sort_by, Plainte.date_creation)))
        else:
            query = query.order_by(getattr(Plainte, sort_by, Plainte.date_creation))

        # Pagination
        total = query.count()
        offset = (page - 1) * limit
        plaintes = query.offset(offset).limit(limit).all()

        # Conversion en réponse
        plaintes_response = []
        for plainte in plaintes:
            plainte_dict = {
                "id": plainte.id,
                "numero_plainte": plainte.numero_plainte,
                "titre": plainte.titre,
                "description": plainte.description,
                "service_id": plainte.service_id,
                "service_nom": plainte.service.nom if plainte.service else None,
                "nom_plaignant": plainte.nom_plaignant,
                "prenom_plaignant": plainte.prenom_plaignant,
                "email_plaignant": plainte.email_plaignant,
                "telephone_plaignant": plainte.telephone_plaignant,
                "mode_reception": plainte.mode_reception,
                "statut": plainte.statut.value if plainte.statut else None,
                "priorite": plainte.priorite.value if plainte.priorite else None,
                "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                "date_modification": plainte.date_modification.isoformat() if plainte.date_modification else None,
                "date_incident": plainte.date_incident.isoformat() if plainte.date_incident else None,
                "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                "date_resolution": plainte.date_resolution.isoformat() if plainte.date_resolution else None,
                "est_en_retard": plainte.est_en_retard,
                "jours_restants": plainte.jours_restants,
                "assigned_user": {
                    "id": plainte.assigned_user.id,
                    "nom": plainte.assigned_user.nom,
                    "prenom": plainte.assigned_user.prenom
                } if plainte.assigned_user else None
            }
            plaintes_response.append(plainte_dict)

        return PaginatedResponse(
            items=plaintes_response,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_plaintes(
    format: str = Query("csv", description="Format d'export: csv, excel, json"),
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    service_id: Optional[int] = Query(None, description="Filtrer par service"),
    date_debut: Optional[datetime] = Query(None, description="Date de début"),
    date_fin: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db)
):
    """
    Exporter les plaintes selon les filtres spécifiés
    """
    try:
        # Construction de la requête avec filtres
        # Les plaintes soft-deletées sont exclues de l'export (finding C5).
        query = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user)
        ).filter(Plainte.date_suppression.is_(None))

        if statut:
            try:
                statut_enum = StatutPlainte(statut)
                query = query.filter(Plainte.statut == statut_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Statut invalide: {statut}")

        if service_id:
            query = query.filter(Plainte.service_id == service_id)

        if date_debut:
            query = query.filter(Plainte.date_creation >= date_debut)

        if date_fin:
            date_fin_inclusive = date_fin + timedelta(days=1)
            query = query.filter(Plainte.date_creation < date_fin_inclusive)

        plaintes = query.all()

        if format.lower() == "csv":
            # Export CSV
            import csv
            from io import StringIO
            from fastapi.responses import Response
            
            output = StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow([
                "ID", "Titre", "Nom Plaignant", "Prénom Plaignant", 
                "Email", "Téléphone", "Mode Réception", "Statut", 
                "Date Création", "Service", "Utilisateur Assigné"
            ])
            
            # Données
            for plainte in plaintes:
                writer.writerow([
                    plainte.id,
                    plainte.titre,
                    plainte.nom_plaignant,
                    plainte.prenom_plaignant,
                    plainte.email_plaignant,
                    plainte.telephone_plaignant,
                    plainte.mode_reception,
                    plainte.statut.value if plainte.statut else "",
                    plainte.date_creation.strftime("%Y-%m-%d %H:%M:%S") if plainte.date_creation else "",
                    plainte.service.nom if plainte.service else "",
                    f"{plainte.assigned_user.prenom} {plainte.assigned_user.nom}" if plainte.assigned_user else ""
                ])
            
            # Récupérer le contenu CSV
            csv_content = output.getvalue()
            output.close()
            
            # Ajouter le BOM UTF-8 pour Excel
            bom = '\ufeff'
            content_with_bom = bom + csv_content
            
            # Encoder en UTF-8
            content_bytes = content_with_bom.encode('utf-8')
            
            # Retourner une Response avec le bon Content-Type
            return Response(
                content=content_bytes,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=plaintes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )
        elif format.lower() == "excel":
            # TODO: Implémenter l'export Excel
            raise HTTPException(status_code=501, detail="Export Excel non encore implémenté")
        else:
            # Export JSON par défaut
            plaintes_data = []
            for plainte in plaintes:
                plaintes_data.append({
                    "id": plainte.id,
                    "titre": plainte.titre,
                    "contenu": plainte.description,  # champ réel = description
                    "nom_plaignant": plainte.nom_plaignant,
                    "prenom_plaignant": plainte.prenom_plaignant,
                    "email_plaignant": plainte.email_plaignant,
                    "telephone_plaignant": plainte.telephone_plaignant,
                    "mode_reception": plainte.mode_reception,
                    "statut": plainte.statut.value if plainte.statut else None,
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_mise_a_jour": plainte.date_modification.isoformat() if plainte.date_modification else None,  # champ réel = date_modification
                    "service": plainte.service.nom if plainte.service else None,
                    "assigned_user": f"{plainte.assigned_user.prenom} {plainte.assigned_user.nom}" if plainte.assigned_user else None
                })
            
            return {"data": plaintes_data, "total": len(plaintes_data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}")
def get_plainte(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer une plainte spécifique par son ID avec tous les documents et l'analyse IA
    """
    try:
        plainte = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses),
            selectinload(Plainte.documents),
            selectinload(Plainte.analyse_ia)
        ).filter(Plainte.id == plainte_id).first()

        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Préparer les documents pour la réponse
        documents_data = []
        for doc in (plainte.documents or []):
            documents_data.append({
                "id": doc.id,
                "plainte_id": doc.plainte_id,
                "nom_fichier": doc.nom_fichier,
                "nom_stockage": doc.nom_stockage,
                "chemin_fichier": doc.chemin_fichier,
                "type_fichier": doc.type_fichier.value if doc.type_fichier else "AUTRE",
                "taille_fichier": doc.taille_fichier,
                "mime_type": doc.mime_type,
                "est_piece_jointe_originale": doc.est_piece_jointe_originale,
                "date_upload": doc.date_upload.isoformat() if doc.date_upload else None
            })

        # Préparer l'analyse IA si disponible
        analyse_ia_data = None
        if plainte.analyse_ia:
            ai = plainte.analyse_ia
            analyse_ia_data = {
                "id": ai.id,
                "sentiment": ai.sentiment,
                "score_sentiment": ai.score_sentiment,
                "service_suggere": ai.service_suggere,
                "priorite_ia": ai.priorite_ia,
                "resume_ia": ai.resume_ia,
                "reponse_suggeree": ai.reponse_suggeree,
                "mots_cles_detectes": ai.mots_cles_detectes,
                "statut_analyse": ai.statut_analyse,
                "date_analyse": ai.date_analyse.isoformat() if ai.date_analyse else None
            }

        # Chercher le PDF rapport généré - plusieurs chemins possibles
        pdf_rapport = None
        
        # Chemin 1: Relatif au fichier actuel (healthcare_api_server/app/api/)
        pdf_dir_1 = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Chemin 2: Relatif au répertoire de travail courant (HealthCare_Backend/)
        pdf_dir_2 = Path("data/pdf_reports")
        
        # Chemin 3: Chemin absolu basé sur le projet
        pdf_dir_3 = Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Essayer tous les chemins possibles
        for pdf_dir in [pdf_dir_1, pdf_dir_2, pdf_dir_3]:
            if pdf_dir.exists():
                logger.info(f"📂 Recherche PDF dans: {pdf_dir}")
                for pdf_file in pdf_dir.glob(f"plainte_{plainte_id}_*.pdf"):
                    pdf_rapport = {
                        "nom_fichier": pdf_file.name,
                        "chemin": str(pdf_file.resolve()),
                        "type": "PDF_RAPPORT",
                        "taille": pdf_file.stat().st_size,
                        "date_creation": datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat()
                    }
                    logger.info(f"✅ PDF trouvé: {pdf_file.name}")
                    break
            if pdf_rapport:
                break

        return {
            "id": plainte.id,
            "numero_plainte": plainte.numero_plainte,
            "titre": plainte.titre,
            "description": plainte.description,
            "contenu": getattr(plainte, 'contenu', plainte.description),
            "nom_plaignant": plainte.nom_plaignant,
            "prenom_plaignant": plainte.prenom_plaignant,
            "email_plaignant": plainte.email_plaignant,
            "telephone_plaignant": plainte.telephone_plaignant,
            "mode_reception": plainte.mode_reception,
            "statut": plainte.statut.value if plainte.statut else "RECU",
            "priorite": plainte.priorite.value if plainte.priorite else "MOYEN",
            "categorie_principale": plainte.categorie_principale,
            "date_incident": plainte.date_incident.isoformat() if plainte.date_incident else None,
            "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
            "date_modification": plainte.date_modification.isoformat() if plainte.date_modification else None,
            "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
            "date_resolution": plainte.date_resolution.isoformat() if plainte.date_resolution else None,
            "est_en_retard": plainte.est_en_retard,
            "jours_restants": plainte.jours_restants,
            "reponse_redigee": plainte.reponse_redigee,
            "reponse_envoyee": bool(plainte.reponse_envoyee),
            "date_reponse_envoyee": plainte.date_reponse_envoyee.isoformat() if plainte.date_reponse_envoyee else None,
            "accuse_reception_envoye": bool(plainte.accuse_reception_envoye),
            "date_accuse_reception": plainte.date_accuse_reception.isoformat() if plainte.date_accuse_reception else None,
            "service_id": plainte.service_id,
            "service": {
                "id": plainte.service.id,
                "nom": plainte.service.nom,
                "code_service": plainte.service.code_service
            } if plainte.service else None,
            "assigned_user": {
                "id": plainte.assigned_user.id,
                "nom": plainte.assigned_user.nom,
                "prenom": plainte.assigned_user.prenom,
                "email": plainte.assigned_user.email
            } if plainte.assigned_user else None,
            "documents": documents_data,
            "pdf_rapport": pdf_rapport,
            "analyse_ia": analyse_ia_data,
            "analyses": [
                {
                    "id": a.id,
                    "type_analyse": a.type_analyse.value if a.type_analyse else None,
                    "statut": a.statut.value if a.statut else None,
                    "resultats": a.resultats
                } for a in (plainte.analyses or [])
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/documents")
def get_plainte_documents(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer tous les documents d'une plainte spécifique
    """
    try:
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Récupérer les documents de la base de données
        documents = db.query(DocumentPlainte).filter(
            DocumentPlainte.plainte_id == plainte_id
        ).all()

        documents_data = []
        for doc in documents:
            # Vérifier si le fichier existe physiquement
            fichier_existe = os.path.exists(doc.chemin_fichier) if doc.chemin_fichier else False
            
            documents_data.append({
                "id": doc.id,
                "plainte_id": doc.plainte_id,
                "nom_fichier": doc.nom_fichier,
                "nom_stockage": doc.nom_stockage,
                "chemin_fichier": doc.chemin_fichier,
                "type_fichier": doc.type_fichier.value if doc.type_fichier else "AUTRE",
                "taille_fichier": doc.taille_fichier,
                "mime_type": doc.mime_type,
                "est_piece_jointe_originale": doc.est_piece_jointe_originale,
                "date_upload": doc.date_upload.isoformat() if doc.date_upload else None,
                "fichier_existe": fichier_existe
            })

        # Chercher aussi le PDF rapport généré - plusieurs chemins possibles
        pdf_rapport = None
        
        # Chemin 1: Relatif au fichier actuel
        pdf_dir_1 = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Chemin 2: Relatif au répertoire de travail courant
        pdf_dir_2 = Path("data/pdf_reports")
        
        # Chemin 3: Chemin absolu résolu
        pdf_dir_3 = Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Essayer tous les chemins possibles
        for pdf_dir in [pdf_dir_1, pdf_dir_2, pdf_dir_3]:
            if pdf_dir.exists():
                for pdf_file in pdf_dir.glob(f"plainte_{plainte_id}_*.pdf"):
                    pdf_rapport = {
                        "nom_fichier": pdf_file.name,
                        "chemin": str(pdf_file.resolve()),
                        "type": "PDF_RAPPORT",
                        "taille": pdf_file.stat().st_size,
                        "date_creation": datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat()
                    }
                    break
            if pdf_rapport:
                break

        return {
            "plainte_id": plainte_id,
            "documents": documents_data,
            "pdf_rapport": pdf_rapport,
            "total_documents": len(documents_data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des documents de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/documents/{document_id}/download")
def download_document(
    plainte_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Télécharger un document spécifique d'une plainte
    """
    try:
        document = db.query(DocumentPlainte).filter(
            DocumentPlainte.id == document_id,
            DocumentPlainte.plainte_id == plainte_id
        ).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        # m4 : on s'assure que le chemin est renseigné avant tout accès disque.
        if not document.chemin_fichier or not os.path.exists(document.chemin_fichier):
            raise HTTPException(status_code=404, detail="Fichier non trouvé sur le serveur")

        # C6 : on vérifie que le fichier demandé reste bien dans le répertoire
        # d'archive autorisé (anti path-traversal) avant de le servir.
        assert_within(REPERTOIRE_ARCHIVE_AUTORISE, document.chemin_fichier)

        # M11 : si une empreinte a été enregistrée à l'upload, on recalcule le
        # SHA-256 du fichier sur disque et on rejette tout fichier dont
        # l'intégrité a été compromise (corruption/altération).
        if document.hash_fichier:
            hash_actuel = file_sha256(document.chemin_fichier)
            if hash_actuel != document.hash_fichier:
                logger.error(
                    "❌ Intégrité fichier compromise pour le document %s "
                    "(plainte %s): hash attendu=%s, hash calculé=%s",
                    document_id, plainte_id, document.hash_fichier, hash_actuel,
                )
                raise HTTPException(status_code=500, detail="integrite fichier compromise")

        return FileResponse(
            path=document.chemin_fichier,
            filename=document.nom_fichier,
            media_type=document.mime_type or "application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du téléchargement du document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/pdf-rapport/download")
def download_pdf_rapport(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Télécharger le PDF rapport généré pour une plainte
    """
    try:
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Chercher le PDF rapport - plusieurs chemins possibles
        pdf_file = None
        
        # Chemin 1: Relatif au fichier actuel
        pdf_dir_1 = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Chemin 2: Relatif au répertoire de travail courant
        pdf_dir_2 = Path("data/pdf_reports")
        
        # Chemin 3: Chemin absolu résolu
        pdf_dir_3 = Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdf_reports"
        
        for pdf_dir in [pdf_dir_1, pdf_dir_2, pdf_dir_3]:
            if pdf_dir.exists():
                for f in pdf_dir.glob(f"plainte_{plainte_id}_*.pdf"):
                    pdf_file = f
                    break
            if pdf_file:
                break

        if not pdf_file or not pdf_file.exists():
            raise HTTPException(status_code=404, detail="Rapport PDF non trouvé")

        return FileResponse(
            path=str(pdf_file.resolve()),
            filename=pdf_file.name,
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du téléchargement du rapport PDF de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{plainte_id}")
async def update_plainte(
    plainte_id: int,
    plainte_data: PlainteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.RESPONSABLE_QUALITE, UserRole.ADMIN])
    ),
):
    """
    Mettre à jour une plainte existante
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Capturer l'état AVANT pour la traçabilité (audit_logs)
        ancien_statut = plainte.statut.value if plainte.statut else None
        ancien_assignee = plainte.assignee_a_id
        ancienne_priorite = plainte.priorite.value if plainte.priorite else None

        # Mise à jour des champs modifiés
        update_data = plainte_data.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(plainte, field):
                setattr(plainte, field, value)

        plainte.date_modification = datetime.now()
        # NB: date_resolution est posée/retirée automatiquement par l'event listener
        # `_plainte_set_resolution` selon le nouveau statut (cf. shared/models.py).

        db.commit()
        db.refresh(plainte)

        # Traçabilité : une entrée d'audit par changement significatif
        nouveau_statut = plainte.statut.value if plainte.statut else None
        if nouveau_statut != ancien_statut:
            log_audit(db, "changement_statut", "plainte", plainte_id, user_id=current_user.id,
                      donnees_avant={"statut": ancien_statut}, donnees_apres={"statut": nouveau_statut})
        if plainte.assignee_a_id != ancien_assignee:
            log_audit(db, "reaffectation", "plainte", plainte_id, user_id=current_user.id,
                      donnees_avant={"assignee_a_id": ancien_assignee},
                      donnees_apres={"assignee_a_id": plainte.assignee_a_id})
        nouvelle_priorite = plainte.priorite.value if plainte.priorite else None
        if nouvelle_priorite != ancienne_priorite:
            log_audit(db, "changement_priorite", "plainte", plainte_id, user_id=current_user.id,
                      donnees_avant={"priorite": ancienne_priorite}, donnees_apres={"priorite": nouvelle_priorite})
        db.commit()

        # Charger les relations pour la réponse
        plainte_updated = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses)
        ).filter(Plainte.id == plainte_id).first()

        # M25 : si la plainte a disparu entre le commit et la re-requête, on
        # échoue proprement avant d'accéder à ses relations (évite un 500 opaque).
        if not plainte_updated:
            raise HTTPException(status_code=500, detail="Plainte introuvable après mise à jour")

        logger.info(f"✅ Plainte mise à jour: ID={plainte_id}")

        # Retourner un dictionnaire simple pour éviter les problèmes de schéma
        return {
            "id": plainte_updated.id,
            "numero_plainte": plainte_updated.numero_plainte,
            "titre": plainte_updated.titre,
            "description": plainte_updated.description,
            "nom_plaignant": plainte_updated.nom_plaignant,
            "prenom_plaignant": plainte_updated.prenom_plaignant,
            "email_plaignant": plainte_updated.email_plaignant,
            "telephone_plaignant": plainte_updated.telephone_plaignant,
            "mode_reception": plainte_updated.mode_reception,
            "statut": plainte_updated.statut.value if plainte_updated.statut else "RECU",
            "priorite": plainte_updated.priorite.value if plainte_updated.priorite else "MOYEN",
            "date_creation": plainte_updated.date_creation.isoformat() if plainte_updated.date_creation else None,
            "date_modification": plainte_updated.date_modification.isoformat() if plainte_updated.date_modification else None,
            "date_limite_reponse": plainte_updated.date_limite_reponse.isoformat() if plainte_updated.date_limite_reponse else None,
            "date_resolution": plainte_updated.date_resolution.isoformat() if plainte_updated.date_resolution else None,
            "est_en_retard": plainte_updated.est_en_retard,
            "jours_restants": plainte_updated.jours_restants,
            "service": {
                "id": plainte_updated.service.id,
                "nom": plainte_updated.service.nom
            } if plainte_updated.service else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la mise à jour de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/historique")
async def get_plainte_historique(plainte_id: int, db: Session = Depends(get_db)):
    """Historique de traçabilité d'une plainte (audit_logs), du plus récent au plus ancien."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    return {"plainte_id": plainte_id, "historique": get_historique(db, "plainte", plainte_id)}


@router.put("/{plainte_id}/reponse")
async def save_reponse(
    plainte_id: int,
    contenu: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.RESPONSABLE_QUALITE, UserRole.ADMIN])
    ),
):
    """Sauvegarder (brouillon) la réponse officielle rédigée par le responsable qualité."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    plainte.reponse_redigee = contenu
    plainte.date_modification = datetime.now()
    db.commit()
    log_audit(db, "reponse_redigee", "plainte", plainte_id, user_id=current_user.id,
              details={"longueur": len(contenu or "")})
    db.commit()
    return {"plainte_id": plainte_id, "reponse_redigee": plainte.reponse_redigee, "message": "Réponse enregistrée"}


@router.post("/{plainte_id}/reponse/envoyer")
async def envoyer_reponse(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.RESPONSABLE_QUALITE, UserRole.ADMIN])
    ),
):
    """Marquer la réponse officielle comme envoyée (email si SMTP configuré, sinon enregistrée)."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    if not (plainte.reponse_redigee or "").strip():
        raise HTTPException(status_code=400, detail="Aucune réponse rédigée à envoyer")
    envoye = send_email_safe(
        settings, plainte.email_plaignant or "",
        f"Réponse à votre réclamation {plainte.numero_plainte}", plainte.reponse_redigee,
    )
    plainte.reponse_envoyee = True
    plainte.date_reponse_envoyee = datetime.now()
    db.commit()
    log_audit(db, "reponse_envoyee", "plainte", plainte_id, user_id=current_user.id,
              details={"email": plainte.email_plaignant, "email_reel_envoye": envoye})
    db.commit()
    return {"plainte_id": plainte_id, "reponse_envoyee": True,
            "date_reponse_envoyee": plainte.date_reponse_envoyee.isoformat(),
            "email_reel_envoye": envoye}


@router.post("/{plainte_id}/accuse-reception")
async def envoyer_accuse_reception(plainte_id: int, db: Session = Depends(get_db)):
    """Émettre l'accusé de réception au plaignant (email si SMTP configuré, sinon enregistré)."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    delai = plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else "le délai légal"
    corps = (
        f"Madame, Monsieur,\n\nNous accusons réception de votre réclamation "
        f"n°{plainte.numero_plainte}. Elle est en cours d'instruction et vous recevrez "
        f"une réponse au plus tard le {delai}.\n\nLe Responsable Qualité"
    )
    envoye = send_email_safe(settings, plainte.email_plaignant or "",
                             f"Accusé de réception — réclamation {plainte.numero_plainte}", corps)
    plainte.accuse_reception_envoye = True
    plainte.date_accuse_reception = datetime.now()
    db.commit()
    log_audit(db, "accuse_reception", "plainte", plainte_id,
              details={"email": plainte.email_plaignant, "email_reel_envoye": envoye})
    db.commit()
    return {"plainte_id": plainte_id, "accuse_reception_envoye": True,
            "date_accuse_reception": plainte.date_accuse_reception.isoformat(),
            "email_reel_envoye": envoye}


@router.get("/{plainte_id}/notes")
async def list_notes(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lister les notes d'instruction d'une plainte (plus récentes d'abord)."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    # M17 : on précharge l'auteur de chaque note pour éviter le N+1.
    notes = (
        db.query(NotePlainte)
        .options(selectinload(NotePlainte.auteur))
        .filter(NotePlainte.plainte_id == plainte_id)
        .order_by(NotePlainte.date_creation.desc())
        .all()
    )
    return {
        "plainte_id": plainte_id,
        "notes": [
            {
                "id": n.id,
                "contenu": n.contenu,
                "auteur_id": n.auteur_id,
                "auteur": f"{n.auteur.prenom} {n.auteur.nom}" if n.auteur else None,
                "date_creation": n.date_creation.isoformat() if n.date_creation else None,
            }
            for n in notes
        ],
    }


@router.post("/{plainte_id}/notes")
async def add_note(
    plainte_id: int,
    contenu: str = Body(..., embed=True),
    auteur_id: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ajouter une note d'instruction interne à une plainte."""
    plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    if not (contenu or "").strip():
        raise HTTPException(status_code=400, detail="Le contenu de la note est requis")
    # M2 : on ignore tout auteur_id fourni par le client et on force l'auteur
    # à l'utilisateur authentifié (anti-falsification de la traçabilité).
    note = NotePlainte(plainte_id=plainte_id, contenu=contenu, auteur_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    log_audit(db, "note_ajoutee", "plainte", plainte_id, user_id=current_user.id, details={"note_id": note.id})
    db.commit()
    return {
        "id": note.id,
        "plainte_id": plainte_id,
        "contenu": note.contenu,
        "auteur_id": note.auteur_id,
        "date_creation": note.date_creation.isoformat() if note.date_creation else None,
    }


@router.delete("/{plainte_id}")
async def delete_plainte(
    plainte_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Supprimer une plainte (réservé aux administrateurs — le front attache le token Bearer).

    C5 : suppression logique (soft-delete) — on horodate `date_suppression`
    au lieu d'un `db.delete()` destructif. La plainte et ses documents disque
    sont conservés (traçabilité/archive), mais exclus des listes/exports.
    """
    try:
        plainte = (
            db.query(Plainte)
            .filter(Plainte.id == plainte_id, Plainte.date_suppression.is_(None))
            .first()
        )

        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Audit AVANT la suppression logique (on trace l'auteur de l'action).
        log_audit(db, "suppression_plainte", "plainte", plainte_id, user_id=current_user.id,
                  details={"numero_plainte": plainte.numero_plainte})

        # Soft-delete : on n'efface ni la ligne en base ni les fichiers disque.
        plainte.date_suppression = datetime.utcnow()
        db.commit()

        logger.info(f"✅ Plainte supprimée (soft-delete): ID={plainte_id}")
        return {"message": "Plainte supprimée avec succès"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ANALYSES ====================

@router.post("/{plainte_id}/analyses", response_model=dict)
async def trigger_analyses(
    plainte_id: int,
    analyses_request: AnalyseTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Déclencher des analyses pour une plainte spécifique
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Déclencher les analyses en arrière-plan
        task_ids = await trigger_analyse_plainte(
            plainte_id=plainte_id,
            types_analyse=analyses_request.types_analyse,
            db=db
        )

        logger.info(f"✅ Analyses déclenchées pour la plainte {plainte_id}: {analyses_request.types_analyse}")

        return {
            "message": "Analyses déclenchées avec succès",
            "task_ids": task_ids,
            "types_analyse": analyses_request.types_analyse
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du déclenchement des analyses pour la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/analyses", response_model=List[AnalyseResponse])
def get_analyses_plainte(
    plainte_id: int,
    type_analyse: Optional[str] = Query(None, description="Filtrer par type d'analyse"),
    db: Session = Depends(get_db)
):
    """
    Récupérer les analyses d'une plainte
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        query = db.query(Analyse).filter(Analyse.plainte_id == plainte_id)
        
        if type_analyse:
            query = query.filter(Analyse.type_analyse == type_analyse)

        analyses = query.order_by(desc(Analyse.date_creation)).all()

        # Le modèle Analyse expose: id, plainte_id, type_analyse, statut, resultats (JSONB),
        # parametres_entree, task_id, duree_execution, erreur_message, analyste_id,
        # date_creation/date_modification (exposées via les propriétés created/updated).
        # Pas de colonnes 'resultat' ni 'score_confiance' -> on construit la réponse
        # avec les vrais attributs pour éviter toute erreur de validation (500).
        return [
            AnalyseResponse(
                id=analyse.id,
                plainte_id=analyse.plainte_id,
                type_analyse=analyse.type_analyse,
                parametres_entree=analyse.parametres_entree or {},
                statut=analyse.statut,
                resultats=analyse.resultats or {},
                task_id=analyse.task_id,
                duree_execution=analyse.duree_execution,
                erreur_message=analyse.erreur_message,
                analyste_id=analyse.analyste_id,
                created=analyse.date_creation,
                updated=analyse.date_modification,
            ) for analyse in analyses
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des analyses de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STATISTIQUES ====================

@router.get("/statistiques/performance", response_model=dict)
async def statistiques_performance(db: Session = Depends(get_db)):
    """KPI de performance CALCULÉS depuis la base (remplace les valeurs codées en dur).

    Tout vient de données réelles ; les champs valent None/0 quand la donnée manque
    plutôt qu'une valeur factice.
    """
    total = db.query(Plainte).count()
    clos = [StatutPlainte.TRAITE, StatutPlainte.CLOTURE]
    resolues = db.query(Plainte).filter(Plainte.statut.in_(clos)).count()
    taux_resolution = round(resolues / total * 100, 1) if total else 0.0

    # Temps moyen de traitement (jours) sur les plaintes effectivement résolues
    avg_secs = db.query(
        func.avg(func.extract("epoch", Plainte.date_resolution - Plainte.date_creation))
    ).filter(Plainte.date_resolution.isnot(None)).scalar()
    temps_traitement_moyen_jours = round(float(avg_secs) / 86400.0, 1) if avg_secs else None

    # Plaintes en retard (délai dépassé, non clôturées)
    today = datetime.now().date()
    nb_en_retard = db.query(Plainte).filter(
        Plainte.date_limite_reponse.isnot(None),
        Plainte.date_limite_reponse < today,
        Plainte.statut.notin_(clos),
    ).count()
    taux_en_retard = round(nb_en_retard / total * 100, 1) if total else 0.0

    # Satisfaction robuste : moyenne du sentiment depuis analyses_ia (toujours alimenté
    # quand l'IA a tourné), converti [-1,1] -> [0,100].
    avg_sent = db.query(func.avg(AnalyseIA.score_sentiment)).filter(
        AnalyseIA.score_sentiment.isnot(None)
    ).scalar()
    satisfaction_pct = round(((float(avg_sent) + 1) / 2) * 100, 1) if avg_sent is not None else None

    # Taux de récurrence : part des plaintes dans une catégorie qui revient (>1 fois)
    cat_rows = db.query(Plainte.categorie_principale, func.count()).filter(
        Plainte.categorie_principale.isnot(None)
    ).group_by(Plainte.categorie_principale).all()
    total_cat = sum(c for _, c in cat_rows)
    recurrents = sum(c for _, c in cat_rows if c > 1)
    taux_recurrence = round(recurrents / total_cat * 100, 1) if total_cat else 0.0

    # Réponses officielles & accusés envoyés (suivi qualité)
    nb_reponses_envoyees = db.query(Plainte).filter(Plainte.reponse_envoyee.is_(True)).count()
    nb_accuses = db.query(Plainte).filter(Plainte.accuse_reception_envoye.is_(True)).count()

    return {
        "total": total,
        "resolues": resolues,
        "taux_resolution": taux_resolution,
        "temps_traitement_moyen_jours": temps_traitement_moyen_jours,
        "nb_en_retard": nb_en_retard,
        "taux_en_retard": taux_en_retard,
        "satisfaction_pct": satisfaction_pct,
        "taux_recurrence": taux_recurrence,
        "nb_reponses_envoyees": nb_reponses_envoyees,
        "nb_accuses_reception": nb_accuses,
    }


@router.get("/statistiques/global", response_model=dict)
def get_statistiques_globales(
    date_debut: Optional[datetime] = Query(None, description="Date de début (format: YYYY-MM-DD)"),
    date_fin: Optional[datetime] = Query(None, description="Date de fin (format: YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques globales des plaintes.
    Si date_debut et date_fin sont fournis, les statistiques sont filtrées par cette période.
    Sinon, retourne les statistiques des 3 derniers mois par défaut.
    """
    try:
        # Si aucune date n'est fournie, utiliser les 3 derniers mois par défaut
        if date_debut is None and date_fin is None:
            date_debut = datetime.now() - timedelta(days=90)
            logger.info(f"📅 Statistiques: Aucune date fournie - Filtre par défaut: 3 derniers mois depuis {date_debut.date()}")
        
        # Log des filtres appliqués
        logger.info(f"📅 Statistiques: Filtrage date_debut={date_debut}, date_fin={date_fin}")
        
        # Construction des filtres de dates
        date_filters = []
        if date_debut:
            date_filters.append(Plainte.date_creation >= date_debut)
        if date_fin:
            date_fin_inclusive = date_fin + timedelta(days=1)
            date_filters.append(Plainte.date_creation < date_fin_inclusive)
        
        # Compter par statut avec les filtres de dates
        stats_query = db.query(
            Plainte.statut,
            func.count(Plainte.id).label('count')
        )
        if date_filters:
            stats_query = stats_query.filter(and_(*date_filters))
        stats_statut = stats_query.group_by(Plainte.statut).all()

        # Convertir en dictionnaire pour accès facile
        stats_dict = {stat.statut.value: stat.count for stat in stats_statut}
        
        logger.info(f"📊 Statistiques calculées: {stats_dict}")

        # Total des plaintes (filtré par dates)
        total_query = db.query(func.count(Plainte.id))
        if date_filters:
            total_query = total_query.filter(and_(*date_filters))
        total = total_query.scalar() or 0

        # Plaintes du mois en cours
        debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        plaintes_mois = db.query(func.count(Plainte.id)).filter(
            Plainte.date_creation >= debut_mois
        ).scalar()

        # Plaintes de la semaine courante
        debut_semaine = datetime.now() - timedelta(days=7)
        plaintes_semaine = db.query(func.count(Plainte.id)).filter(
            Plainte.date_creation >= debut_semaine
        ).scalar()

        # Retourner la structure attendue par le frontend
        return {
            "total": total or 0,
            "nouvelles": stats_dict.get("RECU", 0),
            "en_cours": stats_dict.get("EN_COURS", 0),
            "traitees": stats_dict.get("TRAITE", 0),
            "cloturees": stats_dict.get("CLOTURE", 0),
            "mois_courant": plaintes_mois or 0,
            "semaine_courante": plaintes_semaine or 0
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques globales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/evolution", response_model=dict)
def get_evolution_plaintes(
    periode: str = Query("30j", description="Période: 7j, 30j, 90j"),
    db: Session = Depends(get_db)
):
    """
    Récupérer l'évolution des plaintes sur une période donnée
    """
    try:
        # Calculer la date de début selon la période
        if periode == "7j":
            date_debut = datetime.now() - timedelta(days=7)
        elif periode == "30j":
            date_debut = datetime.now() - timedelta(days=30)
        elif periode == "90j":
            date_debut = datetime.now() - timedelta(days=90)
        else:
            date_debut = datetime.now() - timedelta(days=30)
        
        # Statistiques par jour
        stats_par_jour = db.query(
            func.date(Plainte.date_creation).label('date'),
            func.count(Plainte.id).label('count')
        ).filter(
            Plainte.date_creation >= date_debut
        ).group_by(
            func.date(Plainte.date_creation)
        ).order_by(
            func.date(Plainte.date_creation)
        ).all()
        
        # Statistiques par statut sur la période
        stats_par_statut = db.query(
            Plainte.statut,
            func.count(Plainte.id).label('count')
        ).filter(
            Plainte.date_creation >= date_debut
        ).group_by(Plainte.statut).all()
        
        # Convertir en format attendu
        evolution_data = {
            "periode": periode,
            "evolution_journaliere": [
                {
                    "date": str(stat.date),
                    "count": stat.count
                } for stat in stats_par_jour
            ],
            "stats_par_statut": {
                statut.value: count for statut, count in stats_par_statut
            }
        }
        
        return evolution_data
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de l'évolution des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/departements", response_model=List[dict])
def get_statistiques_departements(
    date_debut: Optional[datetime] = Query(None, description="Date de début (format: YYYY-MM-DD)"),
    date_fin: Optional[datetime] = Query(None, description="Date de fin (format: YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques par département/service
    Inclut tous les services, même ceux sans plaintes
    Si date_debut et date_fin sont fournis, les statistiques sont filtrées par cette période.
    """
    try:
        # Si aucune date n'est fournie, utiliser les 3 derniers mois par défaut
        if date_debut is None and date_fin is None:
            date_debut = datetime.now() - timedelta(days=90)
            logger.info(f"📅 Stats départements: Filtre par défaut 3 derniers mois depuis {date_debut.date()}")
        
        # Construction des conditions de jointure avec filtres de dates
        join_conditions = [Service.id == Plainte.service_id]
        if date_debut:
            join_conditions.append(Plainte.date_creation >= date_debut)
        if date_fin:
            date_fin_inclusive = date_fin + timedelta(days=1)
            join_conditions.append(Plainte.date_creation < date_fin_inclusive)
        
        logger.info(f"📅 Stats départements: date_debut={date_debut}, date_fin={date_fin}")
        
        # Récupérer les statistiques par service avec LEFT JOIN pour inclure tous les services
        stats_services = db.query(
            Service.id,
            Service.nom,
            Service.categorie,
            func.count(Plainte.id).label('total'),
            func.sum(case((Plainte.statut == StatutPlainte.RECU, 1), else_=0)).label('nouvelles'),
            func.sum(case((Plainte.statut == StatutPlainte.EN_COURS, 1), else_=0)).label('en_cours'),
            func.sum(case((Plainte.statut == StatutPlainte.TRAITE, 1), else_=0)).label('traitees'),
            func.sum(case((Plainte.statut == StatutPlainte.CLOTURE, 1), else_=0)).label('cloturees'),
            func.avg(Plainte.score_sentiment).label('satisfaction_moyenne')
        ).outerjoin(
            Plainte, and_(*join_conditions)
        ).filter(
            Service.est_actif == True
        ).group_by(
            Service.id, Service.nom, Service.categorie
        ).all()

        # Formater les données pour le frontend
        return [
            {
                "id": stat.id,
                "nom": stat.nom,
                "type_service": stat.categorie or "AUTRE",
                "total": stat.total or 0,
                "nouvelles": stat.nouvelles or 0,
                "en_cours": stat.en_cours or 0,
                "traitees": stat.traitees or 0,
                "cloturees": stat.cloturees or 0,
                "satisfaction_moyenne": float(stat.satisfaction_moyenne or 0.0)
            }
            for stat in stats_services
        ]
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques par département: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/priorites", response_model=List[dict])
def get_statistiques_priorites(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques par priorité
    """
    try:
        # Récupérer les statistiques par priorité
        stats_priorites = db.query(
            Plainte.priorite,
            func.count(Plainte.id).label('count')
        ).group_by(Plainte.priorite).all()

        # Formater les données pour le frontend
        return [
            {
                "priorite": stat.priorite.value if stat.priorite else "MOYEN",
                "count": stat.count or 0
            }
            for stat in stats_priorites
        ]
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques par priorité: {e}")
        raise HTTPException(status_code=500, detail=str(e))
