#!/usr/bin/env python3
"""
API GESTION PLAINTES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour la gestion, consultation, modification et analyse des plaintes
Toutes les opérations SAUF la création des plaintes
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func, case
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timedelta

from ..db.database import get_db
from shared.models import Plainte, User, Service, Analyse, StatutPlainte
from shared.schemas import (
    PlainteCreate, PlainteUpdate, PlainteResponse,
    AnalyseTaskRequest, TaskStatus, PaginatedResponse, AnalyseResponse
)
# from ..core.auth import get_current_user  # Désactivé pour le développement
from ..services.task_manager import trigger_analyse_plainte

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaintes", tags=["Plaintes - Gestion"])

@router.get("/", response_model=PaginatedResponse[dict])
def get_plaintes(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments par page"),
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    service_id: Optional[int] = Query(None, description="Filtrer par service"),
    assigned_user_id: Optional[int] = Query(None, description="Filtrer par utilisateur assigné"),
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
        query = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses)
        )

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
            query = query.filter(Plainte.assigned_user_id == assigned_user_id)

        if search:
            search_filter = or_(
                Plainte.titre.ilike(f"%{search}%"),
                Plainte.description.ilike(f"%{search}%"),
                Plainte.nom_plaignant.ilike(f"%{search}%"),
                Plainte.prenom_plaignant.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

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

@router.get("/{plainte_id}", response_model=PlainteResponse)
def get_plainte(plainte_id: int, db: Session = Depends(get_db)):
    """
    Récupérer une plainte spécifique par son ID
    """
    try:
        plainte = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses)
        ).filter(Plainte.id == plainte_id).first()

        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        return PlainteResponse(
            id=plainte.id,
            titre=plainte.titre,
            contenu=plainte.contenu,
            nom_plaignant=plainte.nom_plaignant,
            prenom_plaignant=plainte.prenom_plaignant,
            email_plaignant=plainte.email_plaignant,
            telephone_plaignant=plainte.telephone_plaignant,
            mode_reception=plainte.mode_reception,
            statut=plainte.statut,
            date_creation=plainte.date_creation,
            date_mise_a_jour=plainte.date_mise_a_jour,
            service=plainte.service,
            assigned_user=plainte.assigned_user,
            analyses=plainte.analyses or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{plainte_id}", response_model=PlainteResponse)
async def update_plainte(
    plainte_id: int,
    plainte_data: PlainteUpdate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour une plainte existante
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        # Mise à jour des champs modifiés
        update_data = plainte_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(plainte, field):
                setattr(plainte, field, value)

        plainte.date_mise_a_jour = datetime.now()
        
        db.commit()
        db.refresh(plainte)

        # Charger les relations pour la réponse
        plainte_updated = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user),
            selectinload(Plainte.analyses)
        ).filter(Plainte.id == plainte_id).first()

        logger.info(f"✅ Plainte mise à jour: ID={plainte_id}")

        return PlainteResponse(
            id=plainte_updated.id,
            titre=plainte_updated.titre,
            contenu=plainte_updated.contenu,
            nom_plaignant=plainte_updated.nom_plaignant,
            prenom_plaignant=plainte_updated.prenom_plaignant,
            email_plaignant=plainte_updated.email_plaignant,
            telephone_plaignant=plainte_updated.telephone_plaignant,
            mode_reception=plainte_updated.mode_reception,
            statut=plainte_updated.statut,
            date_creation=plainte_updated.date_creation,
            date_mise_a_jour=plainte_updated.date_mise_a_jour,
            service=plainte_updated.service,
            assigned_user=plainte_updated.assigned_user,
            analyses=plainte_updated.analyses or []
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la mise à jour de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{plainte_id}")
async def delete_plainte(plainte_id: int, db: Session = Depends(get_db)):
    """
    Supprimer une plainte
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")

        db.delete(plainte)
        db.commit()

        logger.info(f"✅ Plainte supprimée: ID={plainte_id}")
        return {"message": "Plainte supprimée avec succès"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression de la plainte {plainte_id}: {e}")
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
        query = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.assigned_user)
        )

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
            # TODO: Implémenter l'export CSV
            raise HTTPException(status_code=501, detail="Export CSV non encore implémenté")
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
                    "contenu": plainte.contenu,
                    "nom_plaignant": plainte.nom_plaignant,
                    "prenom_plaignant": plainte.prenom_plaignant,
                    "email_plaignant": plainte.email_plaignant,
                    "telephone_plaignant": plainte.telephone_plaignant,
                    "mode_reception": plainte.mode_reception,
                    "statut": plainte.statut.value if plainte.statut else None,
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_mise_a_jour": plainte.date_mise_a_jour.isoformat() if plainte.date_mise_a_jour else None,
                    "service": plainte.service.nom if plainte.service else None,
                    "assigned_user": f"{plainte.assigned_user.prenom} {plainte.assigned_user.nom}" if plainte.assigned_user else None
                })
            
            return {"data": plaintes_data, "total": len(plaintes_data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export des plaintes: {e}")
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

        return [
            AnalyseResponse(
                id=analyse.id,
                type_analyse=analyse.type_analyse,
                resultat=analyse.resultat,
                score_confiance=analyse.score_confiance,
                date_creation=analyse.date_creation,
                statut=analyse.statut,
                plainte_id=analyse.plainte_id
            ) for analyse in analyses
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des analyses de la plainte {plainte_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STATISTIQUES ====================

@router.get("/statistiques/global", response_model=dict)
def get_statistiques_globales(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques globales des plaintes
    """
    try:
        # Compter par statut
        stats_statut = db.query(
            Plainte.statut,
            func.count(Plainte.id).label('count')
        ).group_by(Plainte.statut).all()

        # Convertir en dictionnaire pour accès facile
        stats_dict = {stat.statut.value: stat.count for stat in stats_statut}

        # Total des plaintes
        total = db.query(func.count(Plainte.id)).scalar()

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
def get_statistiques_departements(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques par département/service
    """
    try:
        # Récupérer les statistiques par service
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
        ).join(
            Plainte, Service.id == Plainte.service_id
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
