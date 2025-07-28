#!/usr/bin/env python3
"""
API DASHBOARD UNIFIÉE - HealthCare AI
Combine les deux dashboards avec filtres par type de plaintes
Version: 1.0.0 - Dashboard Unifié
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

# get_db sera importé dynamiquement pour éviter l'import circulaire
from models_unified import (
    Plainte, Service, Organisation, FichierPlainte, 
    StatutPlainteEnum, PrioriteEnum, TypeServiceEnum
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import APIRouter

app = APIRouter(
    prefix="",
    tags=["Dashboard Unifié"],
    responses={404: {"description": "Not found"}},
)

# Note: CORS est géré par l'application principale

# ==================== DEPENDENCY ====================

def get_db() -> Session:
    """Dépendance pour obtenir une session de base de données"""
    from database_unified import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== TYPES UNIFIÉS ====================

from pydantic import BaseModel

class DashboardStatistiques(BaseModel):
    """Statistiques unifiées pour le dashboard"""
    # Statistiques principales pour les cartes
    nouvelles_plaintes: int
    plaintes_en_attente: int
    plaintes_en_retard: int
    en_cours_traitement: int
    traitees_ce_mois: int
    satisfaction_moyenne: float
    
    # Progressions et métriques
    progression: Dict[str, str]
    
    # Statistiques détaillées
    statistiques_detaillees: Dict[str, Any]
    
    # Répartitions
    repartitions: Dict[str, List[Dict[str, Any]]]
    
    # Alertes
    alertes: Dict[str, bool]
    
    # Timestamp
    derniere_mise_a_jour: str

class DashboardPlainte(BaseModel):
    """Plainte unifiée pour le dashboard"""
    id: int
    plainte_id: str
    titre: str
    contenu: str
    service: str
    priorite: str
    statut: str
    date_creation: str
    date_limite_reponse: Optional[str] = None
    nom_plaignant: Optional[str] = None
    email_plaignant: Optional[str] = None
    telephone_plaignant: Optional[str] = None
    categorie_principale: Optional[str] = None
    sous_categorie: Optional[str] = None

class DashboardPlaintesResponse(BaseModel):
    """Réponse unifiée pour les plaintes du dashboard"""
    plaintes: List[DashboardPlainte]
    total: int
    page: int
    limit: int
    filtres_appliques: Dict[str, Any]

class TypePlainteFilter(BaseModel):
    """Filtres pour les types de plaintes"""
    type_service: Optional[str] = None
    categorie_principale: Optional[str] = None
    sous_categorie: Optional[str] = None
    priorite: Optional[str] = None
    statut: Optional[str] = None

# ==================== FONCTIONS UTILITAIRES ====================

def apply_plainte_filters(query, filters: TypePlainteFilter):
    """Appliquer les filtres sur la requête des plaintes"""
    if filters.type_service:
        # Convertir la chaîne en enum TypeServiceEnum
        try:
            type_service_enum = TypeServiceEnum(filters.type_service)
            query = query.join(Service).filter(Service.type_service == type_service_enum)
        except ValueError:
            # Si la valeur n'est pas un enum valide, ignorer le filtre
            logger.warning(f"Type de service invalide: {filters.type_service}")
            pass
    
    if filters.categorie_principale:
        query = query.filter(Plainte.categorie_principale == filters.categorie_principale)
    
    if filters.sous_categorie:
        query = query.filter(Plainte.sous_categorie == filters.sous_categorie)
    
    if filters.priorite:
        query = query.filter(Plainte.priorite == filters.priorite)
    
    if filters.statut:
        query = query.filter(Plainte.statut == filters.statut)
    
    return query

def get_available_filters(db: Session, organisation_id: Optional[int] = None):
    """Récupérer les filtres disponibles avec statistiques"""
    query = db.query(Plainte)
    
    if organisation_id:
        query = query.filter(Plainte.organisation_id == organisation_id)
    
    # Types de services avec statistiques
    services_query = db.query(
        Service.type_service,
        func.count(Plainte.id).label('count')
    ).join(Plainte, Service.id == Plainte.service_id, isouter=True)
    
    if organisation_id:
        services_query = services_query.filter(Service.organisation_id == organisation_id)
    
    services_query = services_query.group_by(Service.type_service).order_by(Service.type_service)
    services_stats = services_query.all()
    
    types_services = [s[0].value if hasattr(s[0], 'value') else str(s[0]) for s in services_stats]
    
    # Catégories principales avec statistiques
    categories_query = query.with_entities(
        Plainte.categorie_principale,
        func.count(Plainte.id).label('count')
    ).filter(Plainte.categorie_principale.isnot(None)).group_by(Plainte.categorie_principale).order_by(Plainte.categorie_principale)
    categories_stats = categories_query.all()
    categories = [c[0] for c in categories_stats if c[0]]
    
    # Sous-catégories avec statistiques
    sous_categories_query = query.with_entities(
        Plainte.sous_categorie,
        func.count(Plainte.id).label('count')
    ).filter(Plainte.sous_categorie.isnot(None)).group_by(Plainte.sous_categorie).order_by(Plainte.sous_categorie)
    sous_categories_stats = sous_categories_query.all()
    sous_categories = [sc[0] for sc in sous_categories_stats if sc[0]]
    
    # Priorités avec statistiques
    priorites_query = query.with_entities(
        Plainte.priorite,
        func.count(Plainte.id).label('count')
    ).group_by(Plainte.priorite).order_by(Plainte.priorite)
    priorites_stats = priorites_query.all()
    priorites = [p[0].value if hasattr(p[0], 'value') else str(p[0]) for p in priorites_stats]
    
    # Statuts avec statistiques
    statuts_query = query.with_entities(
        Plainte.statut,
        func.count(Plainte.id).label('count')
    ).group_by(Plainte.statut).order_by(Plainte.statut)
    statuts_stats = statuts_query.all()
    statuts = [s[0].value if hasattr(s[0], 'value') else str(s[0]) for s in statuts_stats]
    
    return {
        "types_services": types_services,
        "categories_principales": categories,
        "sous_categories": sous_categories,
        "priorites": priorites,
        "statuts": statuts,
        "statistiques": {
            "services": {(s[0].value if hasattr(s[0], 'value') else str(s[0])): s[1] for s in services_stats},
            "categories": {c[0]: c[1] for c in categories_stats if c[0]},
            "sous_categories": {sc[0]: sc[1] for sc in sous_categories_stats if sc[0]},
            "priorites": {(p[0].value if hasattr(p[0], 'value') else str(p[0])): p[1] for p in priorites_stats},
            "statuts": {(s[0].value if hasattr(s[0], 'value') else str(s[0])): s[1] for s in statuts_stats}
        }
    }

# ==================== ENDPOINTS UNIFIÉS ====================

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API Dashboard Unifiée"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "api": "dashboard-unified"
    }

@app.get("/filtres-disponibles")
async def get_filtres_disponibles(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les filtres disponibles pour les plaintes"""
    try:
        filtres = get_available_filters(db, organisation_id)
        return {
            "success": True,
            "filtres": filtres,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des filtres: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des filtres")

@app.get("/services-details")
async def get_services_details(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les détails des services avec statistiques"""
    try:
        # Requête pour récupérer les services avec leurs statistiques
        services_query = db.query(
            Service.id,
            Service.nom,
            Service.code_service,
            Service.type_service,
            Service.description,
            func.count(Plainte.id).label('total_plaintes'),
            func.sum(case((Plainte.statut == StatutPlainteEnum.RECU, 1), else_=0)).label('nouvelles'),
            func.sum(case((Plainte.statut == StatutPlainteEnum.EN_COURS, 1), else_=0)).label('en_cours'),
            func.sum(case((Plainte.statut == StatutPlainteEnum.TRAITE, 1), else_=0)).label('traitees'),
            func.avg(Plainte.score_sentiment).label('satisfaction_moyenne')
        ).join(Plainte, Service.id == Plainte.service_id, isouter=True)
        
        if organisation_id:
            services_query = services_query.filter(Service.organisation_id == organisation_id)
        
        services_query = services_query.group_by(
            Service.id, Service.nom, Service.code_service, 
            Service.type_service, Service.description
        ).order_by(Service.type_service, Service.nom)
        
        services_data = services_query.all()
        
        services = []
        for service in services_data:
            services.append({
                "id": service.id,
                "nom": service.nom,
                "code_service": service.code_service,
                "type_service": service.type_service,
                "description": service.description,
                "statistiques": {
                    "total_plaintes": service.total_plaintes or 0,
                    "nouvelles": service.nouvelles or 0,
                    "en_cours": service.en_cours or 0,
                    "traitees": service.traitees or 0,
                    "satisfaction_moyenne": float(service.satisfaction_moyenne) if service.satisfaction_moyenne else 0.0
                }
            })
        
        return {
            "success": True,
            "services": services,
            "total_services": len(services),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails des services: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des détails des services")

@app.get("/statistiques", response_model=DashboardStatistiques)
async def get_dashboard_statistiques(
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    categorie_principale: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    statut: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les statistiques détaillées pour le dashboard avec filtres"""
    try:
        # Construire la requête de base
        query = db.query(Plainte)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Appliquer les filtres
        filters = TypePlainteFilter(
            type_service=type_service,
            categorie_principale=categorie_principale,
            sous_categorie=sous_categorie,
            priorite=priorite,
            statut=statut
        )
        query = apply_plainte_filters(query, filters)
        
        # Statistiques de base
        total_plaintes = query.count()
        recu = query.filter(Plainte.statut == StatutPlainteEnum.RECU).count()
        en_cours = query.filter(Plainte.statut == StatutPlainteEnum.EN_COURS).count()
        traite = query.filter(Plainte.statut == StatutPlainteEnum.TRAITE).count()
        cloture = query.filter(Plainte.statut == StatutPlainteEnum.CLOTURE).count()
        traitees_mois = query.filter(
            and_(
                Plainte.statut == StatutPlainteEnum.TRAITE,
                Plainte.date_modification >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            )
        ).count()
        
        # Plaintes en retard
        aujourd_hui = datetime.now().date()
        en_retard = query.filter(
            and_(
                Plainte.date_limite_reponse < aujourd_hui,
                Plainte.statut.in_([StatutPlainteEnum.RECU, StatutPlainteEnum.EN_COURS])
            )
        ).count()
        
        # Satisfaction moyenne (simulée)
        satisfaction_moyenne = 4.2  # À remplacer par un calcul réel
        
        # Progressions (simulées)
        progression = {
            "nouvelles_plaintes": "+12%",
            "plaintes_en_attente": "-5%",
            "plaintes_en_retard": "-8%",
            "en_cours_traitement": "+3%",
            "traitees_ce_mois": "+15%",
            "satisfaction_moyenne": "+2%"
        }
        
        # Statistiques détaillées
        statistiques_detaillees = {
            "plaintes": {
                "total": total_plaintes,
                "en_attente": recu,
                "en_cours": en_cours,
                "traitees_mois": traitees_mois,
                "nouvelles_7_jours": query.filter(
                    Plainte.date_creation >= datetime.now() - timedelta(days=7)
                ).count()
            },
            "fichiers": {
                "total": db.query(FichierPlainte).count(),
                "en_attente_traitement": db.query(FichierPlainte).filter(FichierPlainte.est_traite == False).count(),
                "traites": db.query(FichierPlainte).filter(FichierPlainte.est_traite == True).count(),
                "traites_aujourd_hui": db.query(FichierPlainte).filter(
                    and_(
                        FichierPlainte.est_traite == True,
                        FichierPlainte.date_traitement >= datetime.now().date()
                    )
                ).count(),
                "taux_traitement_pct": 85.5
            },
            "ia_performance": {
                "total_suggestions": 1250,
                "suggestions_approuvees": 980,
                "suggestions_utilisees": 850,
                "taux_approbation_pct": 78.4,
                "efficacite_ia": "Excellente"
            }
        }
        
        # Répartitions
        repartitions = {
            "par_services": [
                {"service": "URGENCES", "count": query.join(Service).filter(Service.type_service == TypeServiceEnum.URGENCES).count()},
                {"service": "CARDIOLOGIE", "count": query.join(Service).filter(Service.type_service == TypeServiceEnum.CARDIOLOGIE).count()},
                {"service": "PEDIATRIE", "count": query.join(Service).filter(Service.type_service == TypeServiceEnum.PEDIATRIE).count()},
                {"service": "CHIRURGIE", "count": query.join(Service).filter(Service.type_service == TypeServiceEnum.CHIRURGIE).count()},
                {"service": "ADMINISTRATION", "count": query.join(Service).filter(Service.type_service == TypeServiceEnum.ADMINISTRATION).count()}
            ],
            "par_priorites": [
                {"priorite": "URGENT", "count": query.filter(Plainte.priorite == PrioriteEnum.URGENT).count()},
                {"priorite": "ELEVE", "count": query.filter(Plainte.priorite == PrioriteEnum.ELEVE).count()},
                {"priorite": "MOYEN", "count": query.filter(Plainte.priorite == PrioriteEnum.MOYEN).count()},
                {"priorite": "BAS", "count": query.filter(Plainte.priorite == PrioriteEnum.BAS).count()}
            ],
            "par_types_fichiers": [
                {"type": "PDF", "count": db.query(FichierPlainte).filter(FichierPlainte.type_fichier == "PDF").count()},
                {"type": "DOC", "count": db.query(FichierPlainte).filter(FichierPlainte.type_fichier == "DOC").count()},
                {"type": "IMAGE", "count": db.query(FichierPlainte).filter(FichierPlainte.type_fichier == "IMAGE").count()}
            ]
        }
        
        # Alertes
        alertes = {
            "fichiers_en_attente_critique": en_retard > 10,
            "plaintes_urgentes": query.filter(Plainte.priorite == PrioriteEnum.URGENT).count() > 5,
            "performance_ia_faible": satisfaction_moyenne < 3.5,
            "satisfaction_faible": satisfaction_moyenne < 4.0
        }
        
        return DashboardStatistiques(
            nouvelles_plaintes=recu,
            plaintes_en_attente=recu,
            plaintes_en_retard=en_retard,
            en_cours_traitement=en_cours,
            traitees_ce_mois=traitees_mois,
            satisfaction_moyenne=satisfaction_moyenne,
            progression=progression,
            statistiques_detaillees=statistiques_detaillees,
            repartitions=repartitions,
            alertes=alertes,
            derniere_mise_a_jour=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@app.get("/plaintes/recu", response_model=DashboardPlaintesResponse)
async def get_dashboard_plaintes_recu(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    categorie_principale: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes reçues (nouveau statut)"""
    try:
        skip = (page - 1) * limit
        
        # Construire la requête de base
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.RECU)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Appliquer les filtres
        filters = TypePlainteFilter(
            type_service=type_service,
            categorie_principale=categorie_principale,
            sous_categorie=sous_categorie,
            priorite=priorite
        )
        query = apply_plainte_filters(query, filters)
        
        # Compter le total
        total = query.count()
        
        # Récupérer les plaintes avec pagination
        plaintes = query.offset(skip).limit(limit).all()
        
        # Convertir en format de réponse
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append(DashboardPlainte(
                    id=plainte.id,
                    plainte_id=plainte.numero_plainte,
                    titre=plainte.titre,
                    contenu=plainte.description,
                    service=plainte.service.nom if plainte.service else "Service inconnu",
                    priorite=plainte.priorite.value if plainte.priorite else "MOYEN",
                    statut=plainte.statut.value if plainte.statut else "RECU",
                    date_creation=plainte.date_creation.isoformat() if plainte.date_creation else None,
                    date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    categorie_principale=plainte.categorie_principale,
                    sous_categorie=plainte.sous_categorie
                ))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return DashboardPlaintesResponse(
            plaintes=plaintes_data,
            total=total,
            page=page,
            limit=limit,
            filtres_appliques={
                "type_service": type_service,
                "categorie_principale": categorie_principale,
                "sous_categorie": sous_categorie,
                "priorite": priorite,
                "statut": "RECU"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_dashboard_plaintes_recu: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/plaintes/en-cours", response_model=DashboardPlaintesResponse)
async def get_dashboard_plaintes_en_cours(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    categorie_principale: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes en cours"""
    try:
        skip = (page - 1) * limit
        
        # Construire la requête de base
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.EN_COURS)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Appliquer les filtres
        filters = TypePlainteFilter(
            type_service=type_service,
            categorie_principale=categorie_principale,
            sous_categorie=sous_categorie,
            priorite=priorite
        )
        query = apply_plainte_filters(query, filters)
        
        # Compter le total
        total = query.count()
        
        # Récupérer les plaintes avec pagination
        plaintes = query.offset(skip).limit(limit).all()
        
        # Convertir en format de réponse
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append(DashboardPlainte(
                    id=plainte.id,
                    plainte_id=plainte.numero_plainte,
                    titre=plainte.titre,
                    contenu=plainte.description,
                    service=plainte.service.nom if plainte.service else "Service inconnu",
                    priorite=plainte.priorite.value if plainte.priorite else "MOYEN",
                    statut=plainte.statut.value if plainte.statut else "EN_COURS",
                    date_creation=plainte.date_creation.isoformat() if plainte.date_creation else None,
                    date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    categorie_principale=plainte.categorie_principale,
                    sous_categorie=plainte.sous_categorie
                ))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return DashboardPlaintesResponse(
            plaintes=plaintes_data,
            total=total,
            page=page,
            limit=limit,
            filtres_appliques={
                "type_service": type_service,
                "categorie_principale": categorie_principale,
                "sous_categorie": sous_categorie,
                "priorite": priorite,
                "statut": "EN_COURS"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_dashboard_plaintes_en_cours: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/plaintes/traite", response_model=DashboardPlaintesResponse)
async def get_dashboard_plaintes_traite(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    categorie_principale: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes traitées (nouveau statut)"""
    try:
        skip = (page - 1) * limit
        
        # Construire la requête de base
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.TRAITE)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Appliquer les filtres
        filters = TypePlainteFilter(
            type_service=type_service,
            categorie_principale=categorie_principale,
            sous_categorie=sous_categorie,
            priorite=priorite
        )
        query = apply_plainte_filters(query, filters)
        
        # Filtres de date optionnels
        if date_debut:
            try:
                date_debut_dt = datetime.fromisoformat(date_debut.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_modification >= date_debut_dt)
            except ValueError:
                logger.warning(f"Format de date invalide pour date_debut: {date_debut}")
        
        if date_fin:
            try:
                date_fin_dt = datetime.fromisoformat(date_fin.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_modification <= date_fin_dt)
            except ValueError:
                logger.warning(f"Format de date invalide pour date_fin: {date_fin}")
        
        # Compter le total
        total = query.count()
        
        # Récupérer les plaintes avec pagination
        plaintes = query.offset(skip).limit(limit).all()
        
        # Convertir en format de réponse
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append(DashboardPlainte(
                    id=plainte.id,
                    plainte_id=plainte.numero_plainte,
                    titre=plainte.titre,
                    contenu=plainte.description,
                    service=plainte.service.nom if plainte.service else "Service inconnu",
                    priorite=plainte.priorite.value if plainte.priorite else "MOYEN",
                    statut=plainte.statut.value if plainte.statut else "TRAITE",
                    date_creation=plainte.date_creation.isoformat() if plainte.date_creation else None,
                    date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    categorie_principale=plainte.categorie_principale,
                    sous_categorie=plainte.sous_categorie
                ))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return DashboardPlaintesResponse(
            plaintes=plaintes_data,
            total=total,
            page=page,
            limit=limit,
            filtres_appliques={
                "type_service": type_service,
                "categorie_principale": categorie_principale,
                "sous_categorie": sous_categorie,
                "priorite": priorite,
                "statut": "TRAITE",
                "date_debut": date_debut,
                "date_fin": date_fin
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_dashboard_plaintes_traite: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/plaintes/cloture", response_model=DashboardPlaintesResponse)
async def get_dashboard_plaintes_cloture(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    categorie_principale: Optional[str] = Query(None),
    sous_categorie: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes clôturées (nouveau statut)"""
    try:
        skip = (page - 1) * limit
        
        # Construire la requête de base
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.CLOTURE)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Appliquer les filtres
        filters = TypePlainteFilter(
            type_service=type_service,
            categorie_principale=categorie_principale,
            sous_categorie=sous_categorie,
            priorite=priorite
        )
        query = apply_plainte_filters(query, filters)
        
        # Filtres de date optionnels
        if date_debut:
            try:
                date_debut_dt = datetime.fromisoformat(date_debut.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_modification >= date_debut_dt)
            except ValueError:
                logger.warning(f"Format de date invalide pour date_debut: {date_debut}")
        
        if date_fin:
            try:
                date_fin_dt = datetime.fromisoformat(date_fin.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_modification <= date_fin_dt)
            except ValueError:
                logger.warning(f"Format de date invalide pour date_fin: {date_fin}")
        
        # Compter le total
        total = query.count()
        
        # Récupérer les plaintes avec pagination
        plaintes = query.offset(skip).limit(limit).all()
        
        # Convertir en format de réponse
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append(DashboardPlainte(
                    id=plainte.id,
                    plainte_id=plainte.numero_plainte,
                    titre=plainte.titre,
                    contenu=plainte.description,
                    service=plainte.service.nom if plainte.service else "Service inconnu",
                    priorite=plainte.priorite.value if plainte.priorite else "MOYEN",
                    statut=plainte.statut.value if plainte.statut else "CLOTURE",
                    date_creation=plainte.date_creation.isoformat() if plainte.date_creation else None,
                    date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    categorie_principale=plainte.categorie_principale,
                    sous_categorie=plainte.sous_categorie
                ))
            except Exception as e:
                logger.error(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return DashboardPlaintesResponse(
            plaintes=plaintes_data,
            total=total,
            page=page,
            limit=limit,
            filtres_appliques={
                "type_service": type_service,
                "categorie_principale": categorie_principale,
                "sous_categorie": sous_categorie,
                "priorite": priorite,
                "statut": "CLOTURE",
                "date_debut": date_debut,
                "date_fin": date_fin
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_dashboard_plaintes_cloture: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/plaintes/urgentes")
async def get_plaintes_urgentes(
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes urgentes avec filtres"""
    try:
        query = db.query(Plainte).filter(
            and_(
                Plainte.priorite == PrioriteEnum.URGENT,
                Plainte.statut.in_([StatutPlainteEnum.NOUVELLE, StatutPlainteEnum.EN_COURS, StatutPlainteEnum.EN_ATTENTE_INFORMATION])
            )
        )
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        if type_service:
            query = query.join(Service).filter(Service.type_service == type_service)
        
        plaintes = query.limit(20).all()
        
        return {
            "success": True,
            "plaintes": [
                {
                    "id": p.id,
                    "numero": p.numero_plainte,
                    "titre": p.titre,
                    "service": p.service.nom if p.service else "Non assigné",
                    "statut": p.statut.value,
                    "date_creation": p.date_creation.isoformat(),
                    "date_limite": p.date_limite_reponse.isoformat() if p.date_limite_reponse else None
                }
                for p in plaintes
            ],
            "total": len(plaintes)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des plaintes urgentes: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des plaintes urgentes")

@app.post("/test-data")
async def create_dashboard_test_data(db: Session = Depends(get_db)):
    """Créer des données de test pour le dashboard"""
    try:
        # Vérifier si des données existent déjà
        if db.query(Plainte).count() > 0:
            return {
                "success": False,
                "message": "Des données existent déjà dans la base"
            }
        
        # Créer des données de test
        from create_sample_data import create_sample_data
        create_sample_data(db)
        
        return {
            "success": True,
            "message": "Données de test créées avec succès",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la création des données de test: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création des données de test")

# Note: L'application est démarrée via main_app.py 