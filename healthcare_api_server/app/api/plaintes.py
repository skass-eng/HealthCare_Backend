#!/usr/bin/env python3
"""
API PLAINTES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour les plaintes (équivalent des dashboards ODYSSEE)
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

router = APIRouter(prefix="/plaintes", tags=["Plaintes"])

@router.get("/total", response_model=int)
def get_total_complaints_for_year(
    year: int = Query(datetime.now().year),
    db: Session = Depends(get_db)
):
    """
    Récupérer le nombre total de plaintes pour l'année spécifiée.
    """
    try:
        total_complaints = db.query(func.count(Plainte.id)).filter(
            func.extract('year', Plainte.date_creation) == year
        ).scalar()
        return total_complaints
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des plaintes: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/", response_model=PlainteResponse)
async def create_plainte(
    plainte_data: PlainteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle plainte et déclencher des analyses IA.
    """
    try:
        service = db.query(Service).filter(
            Service.id == plainte_data.service_id,
            Service.est_actif == True
        ).first()

        if not service:
            raise HTTPException(
                status_code=404,
                detail="Service non trouvé ou inactif"
            )

        now = datetime.now()
        numero_plainte = f"PLT-{service.code_service}-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

        nouvelle_plainte = Plainte(
            numero_plainte=numero_plainte,
            titre=plainte_data.titre,
            description=plainte_data.description,
            service_id=plainte_data.service_id,
            cree_par_id=1,
            date_incident=plainte_data.date_incident,
            date_creation=now,
            analyse_ia={
                "source": "api",
                "analyses_demandees": ["sentiment", "classification", "priorite"],
                "workflow_auto": True
            }
        )

        db.add(nouvelle_plainte)
        db.commit()
        db.refresh(nouvelle_plainte)

        logger.info(f"✅ Plainte créée: {nouvelle_plainte.numero_plainte}")

        background_tasks.add_task(
            trigger_analyse_plainte, nouvelle_plainte.id
        )

        return nouvelle_plainte
    except Exception as e:
        logger.error(f"Erreur lors de la création de la plainte: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/", response_model=PaginatedResponse)
async def list_plaintes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    statut: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lister les plaintes avec filtres et pagination (comme lister les dashboards ODYSSEE)
    """
    try:
        query = db.query(Plainte)
        
        # Filtres
        if statut:
            query = query.filter(Plainte.statut == statut)
        
        if priorite:
            query = query.filter(Plainte.priorite == priorite)
            
        if service_id:
            query = query.filter(Plainte.service_id == service_id)
            
        if search:
            query = query.filter(
                or_(
                    Plainte.titre.ilike(f"%{search}%"),
                    Plainte.description.ilike(f"%{search}%"),
                    Plainte.numero_plainte.ilike(f"%{search}%")
                )
            )
        
        # Pagination
        total = query.count()
        offset = (page - 1) * limit
        plaintes = query.order_by(desc(Plainte.date_creation)).offset(offset).limit(limit).all()
        
        # Formatage simple des données pour éviter les problèmes de validation
        plaintes_response = []
        for plainte in plaintes:
            plainte_dict = {
                "id": plainte.id,
                "numero_plainte": plainte.numero_plainte,
                "titre": plainte.titre,
                "description": plainte.description,
                "service_id": plainte.service_id,
                "cree_par_id": plainte.cree_par_id or 0,
                "nom_plaignant": plainte.nom_plaignant,
                "prenom_plaignant": plainte.prenom_plaignant,
                "email_plaignant": plainte.email_plaignant,
                "telephone_plaignant": plainte.telephone_plaignant,
                "mode_reception": plainte.mode_reception,
                "statut": plainte.statut.value if plainte.statut else None,
                "priorite": plainte.priorite.value if plainte.priorite else None,
                "categorie_principale": plainte.categorie_principale,
                "mots_cles": plainte.mots_cles or [],
                "score_sentiment": plainte.score_sentiment,
                "score_urgence_ia": plainte.score_urgence_ia,
                "date_incident": plainte.date_incident.isoformat() if plainte.date_incident else None,
                "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                "date_modification": plainte.date_modification.isoformat() if plainte.date_modification else None,
                "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None
            }
            plaintes_response.append(plainte_dict)
        
        return {
            "items": plaintes_response,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_plaintes(
    format: str = Query("csv", description="Format d'export: csv ou json"),
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    service: Optional[str] = Query(None, description="Filtrer par service"),
    date_debut: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_fin: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Exporter les plaintes au format CSV ou JSON
    """
    try:
        from fastapi.responses import StreamingResponse
        import csv
        import io
        from datetime import datetime
        
        # Construire la requête avec filtres
        query = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.createur)
        )
        
        # Appliquer les filtres
        if statut:
            query = query.filter(Plainte.statut == statut)
        
        if service:
            query = query.join(Service).filter(Service.nom.ilike(f"%{service}%"))
        
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d").date()
                query = query.filter(Plainte.date_creation >= date_debut_obj)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour date_debut")
        
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d").date()
                query = query.filter(Plainte.date_creation <= date_fin_obj)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour date_fin")
        
        # Récupérer toutes les plaintes
        plaintes = query.order_by(desc(Plainte.date_creation)).all()
        
        if format.lower() == "csv":
            # Générer le CSV avec support complet du français
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
            
            # En-têtes en français avec accents
            headers = [
                "Numéro Plainte", "Titre", "Description", "Statut", "Priorité",
                "Service", "Date Création", "Date Incident", "Catégorie",
                "Score Sentiment", "Score Urgence IA", "Créé par"
            ]
            writer.writerow(headers)
            
            # Données avec gestion des caractères spéciaux
            for plainte in plaintes:
                # Nettoyer et encoder correctement les textes français
                def clean_text(text):
                    if text is None:
                        return ""
                    # Convertir en string et nettoyer
                    text_str = str(text)
                    # Remplacer les caractères problématiques pour CSV
                    text_str = text_str.replace('\n', ' ').replace('\r', ' ')
                    text_str = text_str.replace('\t', ' ')
                    text_str = text_str.replace('"', '""')  # Échapper les guillemets doubles
                    # Supprimer les espaces multiples
                    text_str = ' '.join(text_str.split())
                    # Limiter la longueur pour éviter les problèmes
                    if len(text_str) > 1000:
                        text_str = text_str[:997] + "..."
                    # S'assurer que le texte est bien encodé en UTF-8
                    try:
                        text_str.encode('utf-8')
                    except UnicodeEncodeError:
                        # Si problème d'encodage, nettoyer les caractères problématiques
                        text_str = text_str.encode('utf-8', errors='ignore').decode('utf-8')
                    return text_str
                
                row = [
                    clean_text(plainte.numero_plainte),
                    clean_text(plainte.titre),
                    clean_text(plainte.description),
                    clean_text(plainte.statut.value if plainte.statut else ""),
                    clean_text(plainte.priorite.value if plainte.priorite else ""),
                    clean_text(plainte.service.nom if plainte.service else ""),
                    plainte.date_creation.strftime("%Y-%m-%d %H:%M:%S") if plainte.date_creation else "",
                    plainte.date_incident.strftime("%Y-%m-%d") if plainte.date_incident else "",
                    clean_text(plainte.categorie_principale or ""),
                    str(plainte.score_sentiment) if plainte.score_sentiment else "",
                    str(plainte.score_urgence_ia) if plainte.score_urgence_ia else "",
                    clean_text(plainte.createur.nom_complet if plainte.createur else "")
                ]
                writer.writerow(row)
            
            output.seek(0)
            content = output.getvalue()
            
            # Encoder en UTF-8 avec BOM pour Excel et compatibilité française
            content_bytes = content.encode('utf-8-sig')
            
            return StreamingResponse(
                io.BytesIO(content_bytes),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=plaintes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )
        
        elif format.lower() == "json":
            # Convertir en JSON
            plaintes_data = []
            for plainte in plaintes:
                plainte_dict = {
                    "id": plainte.id,
                    "numero_plainte": plainte.numero_plainte,
                    "titre": plainte.titre,
                    "description": plainte.description,
                    "statut": plainte.statut.value if plainte.statut else None,
                    "priorite": plainte.priorite.value if plainte.priorite else None,
                    "service": plainte.service.nom if plainte.service else None,
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_incident": plainte.date_incident.isoformat() if plainte.date_incident else None,
                    "categorie_principale": plainte.categorie_principale,
                    "score_sentiment": plainte.score_sentiment,
                    "score_urgence_ia": plainte.score_urgence_ia,
                    "createur": plainte.createur.nom_complet if plainte.createur else None
                }
                plaintes_data.append(plainte_dict)
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=plaintes_data,
                headers={
                    "Content-Disposition": f"attachment; filename=plaintes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="Format non supporté. Utilisez 'csv' ou 'json'")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}", response_model=PlainteResponse)
async def get_plainte(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer une plainte par ID (comme récupérer un dashboard ODYSSEE)
    """
    try:
        plainte = db.query(Plainte).options(
            selectinload(Plainte.service),
            selectinload(Plainte.createur),
            selectinload(Plainte.analyses)
        ).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Convertir l'objet SQLAlchemy en schéma Pydantic
        return PlainteResponse.model_validate(plainte)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de la plainte: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{plainte_id}", response_model=PlainteResponse)
async def update_plainte(
    plainte_id: int,
    plainte_update: PlainteUpdate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour une plainte (comme modifier un dashboard ODYSSEE)
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Mise à jour des champs modifiés
        update_data = plainte_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plainte, field, value)
        
        db.commit()
        db.refresh(plainte)
        
        logger.info(f"✅ Plainte mise à jour: {plainte.numero_plainte}")
        
        # Recharger avec relations
        plainte_updated = db.query(Plainte).options(
            selectinload(Plainte.organisation),
            selectinload(Plainte.service),
            selectinload(Plainte.createur),
            selectinload(Plainte.analyses)
        ).filter(Plainte.id == plainte_id).first()
        
        # Convertir l'objet SQLAlchemy en schéma Pydantic
        return PlainteResponse.model_validate(plainte_updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour de la plainte: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{plainte_id}/analyses", response_model=dict)
async def trigger_analyses(
    plainte_id: int,
    analyses_request: AnalyseTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Déclencher des analyses spécifiques (comme exécuter des widgets ODYSSEE)
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Déclencher les analyses demandées
        task_ids = []
        for type_analyse in analyses_request.types_analyse:
            task_id = await trigger_analyse_plainte(
                plainte_id=plainte_id,
                types_analyse=[type_analyse],
                user_id=1,  # Utilisateur par défaut pour le développement
                parametres=analyses_request.parametres
            )
            task_ids.append(task_id)
        
        return {
            "message": f"Analyses déclenchées pour la plainte {plainte.numero_plainte}",
            "task_ids": task_ids,
            "types_analyse": analyses_request.types_analyse
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du déclenchement des analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{plainte_id}/analyses", response_model=List[AnalyseResponse])
async def get_analyses_plainte(
    plainte_id: int,
    type_analyse: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Récupérer les analyses d'une plainte (comme récupérer les widgets d'un dashboard ODYSSEE)
    """
    try:
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        query = db.query(Analyse).filter(Analyse.plainte_id == plainte_id)
        
        if type_analyse:
            query = query.filter(Analyse.type_analyse == type_analyse)
        
        analyses = query.order_by(desc(Analyse.date_creation)).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        analyses_response = []
        for analyse in analyses:
            analyses_response.append(AnalyseResponse.model_validate(analyse))
        
        return analyses_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{plainte_id}")
async def delete_plainte(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprimer une plainte (soft delete comme ODYSSEE)
    """
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Soft delete : mettre à jour les métadonnées
        import datetime
        plainte.metadata = {
            **plainte.metadata,
            "deleted_at": datetime.datetime.now().isoformat(),
            "deleted_by": "1"  # Utilisateur par défaut pour le développement
        }
        
        db.commit()
        
        logger.info(f"✅ Plainte supprimée: {plainte.numero_plainte}")
        
        return {"message": f"Plainte {plainte.numero_plainte} supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression de la plainte: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/global", response_model=dict)
async def get_statistiques_globales(
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques globales pour la page Vue d'ensemble
    """
    try:
        # Statistiques par statut
        stats_par_statut = db.query(
            Plainte.statut,
            func.count(Plainte.id).label('count')
        ).group_by(Plainte.statut).all()
        
        # Total des plaintes
        total_plaintes = db.query(func.count(Plainte.id)).scalar()
        
        # Plaintes du mois en cours
        debut_mois = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        plaintes_mois = db.query(func.count(Plainte.id)).filter(
            Plainte.date_creation >= debut_mois
        ).scalar()
        
        # Plaintes de la semaine
        debut_semaine = datetime.now() - timedelta(days=datetime.now().weekday())
        debut_semaine = debut_semaine.replace(hour=0, minute=0, second=0, microsecond=0)
        plaintes_semaine = db.query(func.count(Plainte.id)).filter(
            Plainte.date_creation >= debut_semaine
        ).scalar()
        
        # Convertir les statistiques en format attendu par le frontend
        stats_dict = {
            "total": total_plaintes,
            "nouvelles": 0,
            "en_cours": 0,
            "traitees": 0,
            "cloturees": 0,
            "mois_courant": plaintes_mois,
            "semaine_courante": plaintes_semaine
        }
        
        for statut, count in stats_par_statut:
            if statut == StatutPlainte.RECU or statut == StatutPlainte.RECU.value:
                stats_dict["nouvelles"] = count
            elif statut == StatutPlainte.EN_COURS or statut == StatutPlainte.EN_COURS.value:
                stats_dict["en_cours"] = count
            elif statut == StatutPlainte.TRAITE or statut == StatutPlainte.TRAITE.value:
                stats_dict["traitees"] = count
            elif statut == StatutPlainte.CLOTURE or statut == StatutPlainte.CLOTURE.value:
                stats_dict["cloturees"] = count
        
        return stats_dict
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques globales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/departements", response_model=List[dict])
async def get_statistiques_departements(
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques par département/service pour la page Vue d'ensemble
    """
    try:
        # Récupérer les statistiques par service avec les vraies données
        # Utiliser une requête plus précise pour correspondre aux données réelles
        services_stats = db.query(
            Service.id,
            Service.nom,
            Service.categorie,
            func.count(Plainte.id).label('total_plaintes'),
            func.sum(case((Plainte.statut == StatutPlainte.RECU.value, 1), else_=0)).label('nouvelles'),
            func.sum(case((Plainte.statut == StatutPlainte.EN_COURS.value, 1), else_=0)).label('en_cours'),
            func.sum(case((Plainte.statut == StatutPlainte.TRAITE.value, 1), else_=0)).label('traitees'),
            func.sum(case((Plainte.statut == StatutPlainte.CLOTURE.value, 1), else_=0)).label('cloturees')
        ).outerjoin(Plainte, Service.id == Plainte.service_id).group_by(
            Service.id, Service.nom, Service.categorie
        ).filter(
            Service.est_actif == True  # Seulement les services actifs
        ).all()
        
        # Convertir en format attendu par le frontend
        departements_stats = []
        for service in services_stats:
            # Calculer la satisfaction moyenne (placeholder pour l'instant)
            satisfaction_moyenne = 0.0  # À implémenter avec les vraies données de satisfaction
            
            # S'assurer que les valeurs sont des entiers
            total = int(service.total_plaintes or 0)
            nouvelles = int(service.nouvelles or 0)
            en_cours = int(service.en_cours or 0)
            traitees = int(service.traitees or 0)
            cloturees = int(service.cloturees or 0)
            
            departement_data = {
                "id": service.id,
                "nom": service.nom,
                "type_service": service.categorie or "",
                "total": total,
                "nouvelles": nouvelles,
                "en_cours": en_cours,
                "traitees": traitees,
                "cloturees": cloturees,
                "satisfaction_moyenne": satisfaction_moyenne
            }
            departements_stats.append(departement_data)
        
        # Trier par nom de service pour une meilleure présentation
        departements_stats.sort(key=lambda x: x["nom"])
        
        return departements_stats
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques par département: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/priorites", response_model=List[dict])
async def get_statistiques_priorites(
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques par priorité pour le graphique pie chart
    """
    try:
        # Récupérer les statistiques par priorité
        stats_par_priorite = db.query(
            Plainte.priorite,
            func.count(Plainte.id).label('count')
        ).group_by(Plainte.priorite).all()
        
        # Convertir en format attendu par le frontend
        priorites_stats = []
        for stat in stats_par_priorite:
            priorite_data = {
                "priorite": stat.priorite,
                "count": stat.count
            }
            priorites_stats.append(priorite_data)
        
        return priorites_stats
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques par priorité: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistiques/evolution", response_model=dict)
async def get_evolution_plaintes(
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
                statut: count for statut, count in stats_par_statut
            }
        }
        
        return evolution_data
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de l'évolution des plaintes: {e}")
        raise HTTPException(status_code=500, detail=str(e))