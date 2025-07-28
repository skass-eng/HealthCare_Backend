"""
API Pages - HealthCare AI
API dédiée par page avec endpoints spécifiques pour chaque fonctionnalité
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from api_unified import get_db
from models_unified import Plainte, Service, Organisation, FichierPlainte, StatutPlainteEnum, PrioriteEnum

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HealthCare AI - API Pages",
    description="API dédiée par page avec endpoints spécifiques",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== TYPES PAR PAGE ====================

from pydantic import BaseModel

# Types communs
class PageResponse(BaseModel):
    """Réponse de base pour toutes les pages"""
    page: str
    timestamp: str
    success: bool
    message: str

# ==================== PAGE DASHBOARD (KPIs) ====================

class DashboardKPIs(BaseModel):
    """KPIs pour la page Dashboard"""
    # Statistiques principales
    total_plaintes: int
    nouvelles_plaintes: int
    plaintes_en_cours: int
    plaintes_traitees: int
    plaintes_en_retard: int
    satisfaction_moyenne: float
    
    # Métriques de performance
    taux_resolution: float
    duree_moyenne_traitement: float
    plaintes_urgentes: int
    
    # Répartitions
    repartition_par_statut: Dict[str, int]
    repartition_par_priorite: Dict[str, int]
    repartition_par_service: Dict[str, int]
    
    # Alertes
    alertes: Dict[str, bool]
    
    # APIs utilisées
    apis_utilisees: List[str]

class DashboardResponse(PageResponse):
    """Réponse pour la page Dashboard"""
    data: DashboardKPIs

# ==================== PAGE NOUVELLES PLAINTES ====================

class NouvellePlainte(BaseModel):
    """Plainte pour la page Nouvelles Plaintes"""
    id: int
    numero_plainte: str
    titre: str
    description: str
    service: str
    priorite: str
    date_creation: str
    date_limite_reponse: Optional[str]
    assignee: Optional[str]

class NouvellesPlaintesResponse(PageResponse):
    """Réponse pour la page Nouvelles Plaintes"""
    data: Dict[str, Any]

# ==================== PAGE EN COURS ====================

class PlainteEnCours(BaseModel):
    """Plainte pour la page En Cours"""
    id: int
    numero_plainte: str
    titre: str
    description: str
    service: str
    priorite: str
    statut: str
    date_creation: str
    date_modification: str
    date_limite_reponse: Optional[str]
    assignee: Optional[str]
    progression: float

class EnCoursResponse(PageResponse):
    """Réponse pour la page En Cours"""
    data: Dict[str, Any]

# ==================== PAGE TRAITÉES ====================

class PlainteTraitee(BaseModel):
    """Plainte pour la page Traitées"""
    id: int
    numero_plainte: str
    titre: str
    description: str
    service: str
    priorite: str
    statut: str
    date_creation: str
    date_resolution: str
    duree_traitement: float
    satisfaction: Optional[float]
    resolution_commentaire: Optional[str]

class TraiteesResponse(PageResponse):
    """Réponse pour la page Traitées"""
    data: Dict[str, Any]

# ==================== PAGE AMÉLIORATIONS ====================

class Amelioration(BaseModel):
    """Amélioration pour la page Améliorations"""
    id: int
    titre: str
    description: str
    categorie: str
    priorite: str
    statut: str
    impact_estime: str
    effort_estime: str
    date_proposition: str
    propose_par: str

class AmeliorationsResponse(PageResponse):
    """Réponse pour la page Améliorations"""
    data: Dict[str, Any]

# ==================== PAGE ANALYTICS ====================

class AnalyticsData(BaseModel):
    """Données pour la page Analytics"""
    evolution_temps: Dict[str, List[int]]
    repartition_geographique: Dict[str, int]
    tendances_priorites: Dict[str, List[float]]
    performance_services: Dict[str, Dict[str, Any]]

class AnalyticsResponse(PageResponse):
    """Réponse pour la page Analytics"""
    data: Dict[str, Any]

# ==================== PAGE ANALYTICS V2 ====================

class AnalyticsV2Data(BaseModel):
    """Données pour la page Analytics V2"""
    predictions_ia: Dict[str, Any]
    insights_avances: List[Dict[str, Any]]
    recommandations: List[str]
    metriques_avancees: Dict[str, Any]

class AnalyticsV2Response(PageResponse):
    """Réponse pour la page Analytics V2"""
    data: Dict[str, Any]

# ==================== PAGE PARAMÈTRES ====================

class Parametre(BaseModel):
    """Paramètre pour la page Paramètres"""
    id: int
    nom: str
    valeur: str
    categorie: str
    description: str
    modifiable: bool

class ParametresResponse(PageResponse):
    """Réponse pour la page Paramètres"""
    data: Dict[str, Any]

# ==================== ENDPOINTS PAR PAGE ====================

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API Pages"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "api": "pages"
    }

# ==================== PAGE DASHBOARD ====================

@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Dashboard (KPIs)"""
    try:
        query = db.query(Plainte)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Statistiques de base
        total_plaintes = query.count()
        nouvelles = query.filter(Plainte.statut == StatutPlainteEnum.NOUVELLE).count()
        en_cours = query.filter(Plainte.statut.in_([
            StatutPlainteEnum.EN_COURS,
            StatutPlainteEnum.EN_COURS_TRAITEMENT,
            StatutPlainteEnum.EN_ATTENTE_INFORMATION
        ])).count()
        traitees = query.filter(Plainte.statut.in_([
            StatutPlainteEnum.TRAITEE,
            StatutPlainteEnum.RESOLUE
        ])).count()
        
        # Plaintes en retard
        aujourd_hui = datetime.now().date()
        il_y_a_30_jours = aujourd_hui - timedelta(days=30)
        
        plaintes_retard_date_limite = query.filter(
            Plainte.date_limite_reponse.isnot(None),
            Plainte.date_limite_reponse < aujourd_hui,
            Plainte.statut.in_([
                StatutPlainteEnum.NOUVELLE,
                StatutPlainteEnum.EN_COURS,
                StatutPlainteEnum.EN_COURS_TRAITEMENT,
                StatutPlainteEnum.EN_ATTENTE_INFORMATION
            ])
        ).count()
        
        plaintes_retard_anciennes = query.filter(
            Plainte.date_creation < il_y_a_30_jours,
            Plainte.statut.in_([
                StatutPlainteEnum.NOUVELLE,
                StatutPlainteEnum.EN_COURS,
                StatutPlainteEnum.EN_COURS_TRAITEMENT,
                StatutPlainteEnum.EN_ATTENTE_INFORMATION
            ])
        ).count()
        
        plaintes_en_retard = plaintes_retard_date_limite + plaintes_retard_anciennes
        
        # Plaintes urgentes
        plaintes_urgentes = query.filter(Plainte.priorite == PrioriteEnum.URGENT).count()
        
        # Répartitions
        repartition_statut = {}
        for statut in StatutPlainteEnum:
            count = query.filter(Plainte.statut == statut).count()
            if count > 0:
                repartition_statut[statut.value] = count
        
        repartition_priorite = {}
        for priorite in PrioriteEnum:
            count = query.filter(Plainte.priorite == priorite).count()
            if count > 0:
                repartition_priorite[priorite.value] = count
        
        repartition_service = {}
        services_data = db.query(Service.nom, func.count(Plainte.id)).join(Plainte).group_by(Service.nom).all()
        for service, count in services_data:
            repartition_service[service] = count
        
        # Calculs avancés
        taux_resolution = round((traitees / total_plaintes * 100) if total_plaintes > 0 else 0, 1)
        satisfaction_moyenne = 4.2  # Mock pour l'instant
        duree_moyenne_traitement = 3.5  # Mock pour l'instant
        
        # Alertes
        alertes = {
            "plaintes_urgentes": plaintes_urgentes > 5,
            "plaintes_en_retard": plaintes_en_retard > 10,
            "taux_resolution_faible": taux_resolution < 70,
            "satisfaction_faible": satisfaction_moyenne < 3.5
        }
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /dashboard",
            "GET /plaintes/statistiques",
            "GET /services/repartition",
            "GET /alertes/actives"
        ]
        
        kpis = DashboardKPIs(
            total_plaintes=total_plaintes,
            nouvelles_plaintes=nouvelles,
            plaintes_en_cours=en_cours,
            plaintes_traitees=traitees,
            plaintes_en_retard=plaintes_en_retard,
            satisfaction_moyenne=satisfaction_moyenne,
            taux_resolution=taux_resolution,
            duree_moyenne_traitement=duree_moyenne_traitement,
            plaintes_urgentes=plaintes_urgentes,
            repartition_par_statut=repartition_statut,
            repartition_par_priorite=repartition_priorite,
            repartition_par_service=repartition_service,
            alertes=alertes,
            apis_utilisees=apis_utilisees
        )
        
        logger.info(f"📊 Dashboard KPIs calculés pour l'organisation {organisation_id}")
        
        return DashboardResponse(
            page="dashboard",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="KPIs récupérés avec succès",
            data=kpis
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_dashboard_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE NOUVELLES PLAINTES ====================

@app.get("/nouvelles-plaintes", response_model=NouvellesPlaintesResponse)
async def get_nouvelles_plaintes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    priorite: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Nouvelles Plaintes"""
    try:
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.NOUVELLE)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        if priorite:
            try:
                priorite_enum = PrioriteEnum(priorite)
                query = query.filter(Plainte.priorite == priorite_enum)
            except ValueError:
                pass
        
        if service_id:
            query = query.filter(Plainte.service_id == service_id)
        
        total = query.count()
        offset = (page - 1) * limit
        
        plaintes = query.offset(offset).limit(limit).all()
        
        # Adapter les plaintes
        nouvelles_plaintes = []
        for plainte in plaintes:
            service_nom = db.query(Service.nom).filter(Service.id == plainte.service_id).scalar() or "Service inconnu"
            assignee_nom = None
            if plainte.assignee_a_id:
                assignee = db.query(Utilisateur.nom_complet).filter(Utilisateur.id == plainte.assignee_a_id).scalar()
                assignee_nom = assignee if assignee else None
            
            nouvelles_plaintes.append(NouvellePlainte(
                id=plainte.id,
                numero_plainte=plainte.numero_plainte,
                titre=plainte.titre,
                description=plainte.description,
                service=service_nom,
                priorite=plainte.priorite,
                date_creation=plainte.date_creation.isoformat(),
                date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                assignee=assignee_nom
            ))
        
        # Filtres disponibles
        filtres_disponibles = {
            "priorites": [p.value for p in PrioriteEnum],
            "services": [s.nom for s in db.query(Service.nom).all()]
        }
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /nouvelles-plaintes",
            "GET /plaintes/filtres",
            "POST /plaintes/assigner",
            "PUT /plaintes/statut"
        ]
        
        return NouvellesPlaintesResponse(
            page="nouvelles-plaintes",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Nouvelles plaintes récupérées avec succès",
            data={
                "plaintes": nouvelles_plaintes,
                "total": total,
                "page": page,
                "limit": limit,
                "filtres_disponibles": filtres_disponibles,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_nouvelles_plaintes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE EN COURS ====================

@app.get("/en-cours", response_model=EnCoursResponse)
async def get_en_cours_data(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page En Cours"""
    try:
        statuts_en_cours = [
            StatutPlainteEnum.EN_COURS,
            StatutPlainteEnum.EN_COURS_TRAITEMENT,
            StatutPlainteEnum.EN_ATTENTE_INFORMATION
        ]
        
        query = db.query(Plainte).filter(Plainte.statut.in_(statuts_en_cours))
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        if statut:
            try:
                statut_enum = StatutPlainteEnum(statut)
                query = query.filter(Plainte.statut == statut_enum)
            except ValueError:
                pass
        
        total = query.count()
        offset = (page - 1) * limit
        
        plaintes = query.offset(offset).limit(limit).all()
        
        # Adapter les plaintes
        plaintes_en_cours = []
        for plainte in plaintes:
            service_nom = db.query(Service.nom).filter(Service.id == plainte.service_id).scalar() or "Service inconnu"
            assignee_nom = None
            if plainte.assignee_a_id:
                assignee = db.query(Utilisateur.nom_complet).filter(Utilisateur.id == plainte.assignee_a_id).scalar()
                assignee_nom = assignee if assignee else None
            
            # Calculer la progression (mock pour l'instant)
            progression = 50.0  # Mock
            
            plaintes_en_cours.append(PlainteEnCours(
                id=plainte.id,
                numero_plainte=plainte.numero_plainte,
                titre=plainte.titre,
                description=plainte.description,
                service=service_nom,
                priorite=plainte.priorite,
                statut=plainte.statut,
                date_creation=plainte.date_creation.isoformat(),
                date_modification=plainte.date_modification.isoformat(),
                date_limite_reponse=plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                assignee=assignee_nom,
                progression=progression
            ))
        
        # Statistiques workflow
        statistiques_workflow = {}
        for statut in statuts_en_cours:
            count = query.filter(Plainte.statut == statut).count()
            statistiques_workflow[statut.value] = count
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /en-cours",
            "GET /plaintes/workflow",
            "PUT /plaintes/progression",
            "POST /plaintes/commentaires"
        ]
        
        return EnCoursResponse(
            page="en-cours",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Plaintes en cours récupérées avec succès",
            data={
                "plaintes": plaintes_en_cours,
                "total": total,
                "page": page,
                "limit": limit,
                "statistiques_workflow": statistiques_workflow,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_en_cours_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE TRAITÉES ====================

@app.get("/traitees", response_model=TraiteesResponse)
async def get_traitees_data(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Traitées"""
    try:
        statuts_traites = [StatutPlainteEnum.TRAITEE, StatutPlainteEnum.RESOLUE]
        query = db.query(Plainte).filter(Plainte.statut.in_(statuts_traites))
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        if date_debut:
            try:
                date_debut_obj = datetime.fromisoformat(date_debut.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_resolution >= date_debut_obj)
            except ValueError:
                pass
        
        if date_fin:
            try:
                date_fin_obj = datetime.fromisoformat(date_fin.replace('Z', '+00:00'))
                query = query.filter(Plainte.date_resolution <= date_fin_obj)
            except ValueError:
                pass
        
        total = query.count()
        offset = (page - 1) * limit
        
        plaintes = query.offset(offset).limit(limit).all()
        
        # Adapter les plaintes
        plaintes_traitees = []
        for plainte in plaintes:
            service_nom = db.query(Service.nom).filter(Service.id == plainte.service_id).scalar() or "Service inconnu"
            
            # Calculer la durée de traitement
            duree_traitement = 0.0
            if plainte.date_resolution and plainte.date_creation:
                duree_traitement = (plainte.date_resolution - plainte.date_creation).days
            
            plaintes_traitees.append(PlainteTraitee(
                id=plainte.id,
                numero_plainte=plainte.numero_plainte,
                titre=plainte.titre,
                description=plainte.description,
                service=service_nom,
                priorite=plainte.priorite,
                statut=plainte.statut,
                date_creation=plainte.date_creation.isoformat(),
                date_resolution=plainte.date_resolution.isoformat() if plainte.date_resolution else "",
                duree_traitement=duree_traitement,
                satisfaction=4.5,  # Mock
                resolution_commentaire="Résolu avec succès"  # Mock
            ))
        
        # Statistiques de résolution
        statistiques_resolution = {
            "total_resolues": total,
            "duree_moyenne": 3.2,  # Mock
            "satisfaction_moyenne": 4.3,  # Mock
            "taux_resolution": 85.5  # Mock
        }
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /traitees",
            "GET /plaintes/statistiques-resolution",
            "POST /plaintes/satisfaction",
            "GET /plaintes/export"
        ]
        
        return TraiteesResponse(
            page="traitees",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Plaintes traitées récupérées avec succès",
            data={
                "plaintes": plaintes_traitees,
                "total": total,
                "page": page,
                "limit": limit,
                "statistiques_resolution": statistiques_resolution,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_traitees_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE AMÉLIORATIONS ====================

@app.get("/ameliorations", response_model=AmeliorationsResponse)
async def get_ameliorations_data(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    categorie: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Améliorations"""
    try:
        # Mock data pour les améliorations
        ameliorations_mock = [
            Amelioration(
                id=1,
                titre="Amélioration de l'interface utilisateur",
                description="Moderniser l'interface pour une meilleure expérience utilisateur",
                categorie="Interface",
                priorite="Élevée",
                statut="En cours",
                impact_estime="Élevé",
                effort_estime="Moyen",
                date_proposition="2024-01-15",
                propose_par="Équipe UX"
            ),
            Amelioration(
                id=2,
                titre="Intégration IA avancée",
                description="Améliorer les suggestions IA pour le traitement des plaintes",
                categorie="IA",
                priorite="Très élevée",
                statut="Planifiée",
                impact_estime="Très élevé",
                effort_estime="Élevé",
                date_proposition="2024-01-20",
                propose_par="Équipe IA"
            )
        ]
        
        # Filtrer par catégorie si spécifiée
        if categorie:
            ameliorations_mock = [a for a in ameliorations_mock if a.categorie.lower() == categorie.lower()]
        
        total = len(ameliorations_mock)
        offset = (page - 1) * limit
        ameliorations_page = ameliorations_mock[offset:offset + limit]
        
        # Catégories disponibles
        categories = ["Interface", "IA", "Performance", "Sécurité", "Fonctionnalités"]
        
        # Statistiques d'impact
        statistiques_impact = {
            "total_ameliorations": total,
            "par_categorie": {"Interface": 5, "IA": 3, "Performance": 2},
            "par_priorite": {"Très élevée": 2, "Élevée": 3, "Moyenne": 4}
        }
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /ameliorations",
            "POST /ameliorations",
            "PUT /ameliorations/{id}",
            "GET /ameliorations/statistiques"
        ]
        
        return AmeliorationsResponse(
            page="ameliorations",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Améliorations récupérées avec succès",
            data={
                "ameliorations": ameliorations_page,
                "total": total,
                "categories": categories,
                "statistiques_impact": statistiques_impact,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_ameliorations_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE ANALYTICS ====================

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics_data(
    periode: str = Query("30j", description="Période d'analyse: 7j, 30j, 90j, 1an"),
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Analytics"""
    try:
        # Calculer la période
        aujourd_hui = datetime.now()
        if periode == "7j":
            debut_periode = aujourd_hui - timedelta(days=7)
        elif periode == "30j":
            debut_periode = aujourd_hui - timedelta(days=30)
        elif periode == "90j":
            debut_periode = aujourd_hui - timedelta(days=90)
        elif periode == "1an":
            debut_periode = aujourd_hui - timedelta(days=365)
        else:
            debut_periode = aujourd_hui - timedelta(days=30)
        
        query = db.query(Plainte).filter(Plainte.date_creation >= debut_periode)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Évolution dans le temps (par jour)
        evolution_temps = {"dates": [], "plaintes": []}
        for i in range((aujourd_hui - debut_periode).days + 1):
            date = debut_periode + timedelta(days=i)
            count = query.filter(
                Plainte.date_creation >= date,
                Plainte.date_creation < date + timedelta(days=1)
            ).count()
            evolution_temps["dates"].append(date.strftime("%Y-%m-%d"))
            evolution_temps["plaintes"].append(count)
        
        # Répartition géographique (mock)
        repartition_geographique = {
            "Paris": 150,
            "Lyon": 89,
            "Marseille": 67,
            "Toulouse": 45,
            "Nantes": 34
        }
        
        # Tendances des priorités
        tendances_priorites = {
            "URGENT": [12, 15, 18, 14, 16, 19, 22],
            "ELEVEE": [45, 42, 48, 51, 47, 44, 49],
            "MOYEN": [78, 82, 75, 79, 81, 77, 80],
            "BAS": [23, 25, 21, 24, 26, 22, 25]
        }
        
        # Performance des services
        performance_services = {}
        services_data = db.query(Service.nom, func.count(Plainte.id)).join(Plainte).group_by(Service.nom).all()
        for service, count in services_data:
            performance_services[service] = {
                "total_plaintes": count,
                "taux_resolution": 85.5,  # Mock
                "satisfaction_moyenne": 4.2,  # Mock
                "duree_moyenne": 3.1  # Mock
            }
        
        analytics_data = AnalyticsData(
            evolution_temps=evolution_temps,
            repartition_geographique=repartition_geographique,
            tendances_priorites=tendances_priorites,
            performance_services=performance_services
        )
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /analytics",
            "GET /analytics/evolution",
            "GET /analytics/geographie",
            "GET /analytics/performance-services"
        ]
        
        return AnalyticsResponse(
            page="analytics",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Données analytics récupérées avec succès",
            data={
                "analytics": analytics_data,
                "periode_analyse": periode,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_analytics_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE ANALYTICS V2 ====================

@app.get("/analytics-v2", response_model=AnalyticsV2Response)
async def get_analytics_v2_data(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les données pour la page Analytics V2"""
    try:
        # Prédictions IA
        predictions_ia = {
            "plaintes_predites_7j": 45,
            "plaintes_urgentes_predites": 8,
            "taux_resolution_predit": 87.3,
            "services_risque": ["Cardiologie", "Urgences"],
            "tendance_satisfaction": "Amélioration"
        }
        
        # Insights avancés
        insights_avances = [
            {
                "type": "tendance",
                "titre": "Augmentation des plaintes cardiologie",
                "description": "Hausse de 23% ce mois",
                "impact": "Élevé",
                "recommandation": "Renforcer l'équipe cardiologie"
            },
            {
                "type": "anomalie",
                "titre": "Baisse satisfaction urgences",
                "description": "Chute de 15% cette semaine",
                "impact": "Critique",
                "recommandation": "Audit immédiat du service"
            }
        ]
        
        # Recommandations
        recommandations = [
            "Augmenter le personnel aux urgences",
            "Améliorer la formation en cardiologie",
            "Optimiser les processus de triage",
            "Renforcer la communication patient"
        ]
        
        # Métriques avancées
        metriques_avancees = {
            "score_qualite_global": 8.7,
            "efficacite_traitement": 92.3,
            "satisfaction_patient": 4.4,
            "temps_reponse_moyen": 2.1,
            "taux_recurrence": 3.2
        }
        
        analytics_v2_data = AnalyticsV2Data(
            predictions_ia=predictions_ia,
            insights_avances=insights_avances,
            recommandations=recommandations,
            metriques_avancees=metriques_avancees
        )
        
        # Modèles IA utilisés
        modeles_ia_utilises = [
            "Modèle de prédiction de charge",
            "Modèle d'analyse de sentiment",
            "Modèle de détection d'anomalies",
            "Modèle de recommandation"
        ]
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /analytics-v2",
            "GET /analytics-v2/predictions",
            "GET /analytics-v2/insights",
            "GET /analytics-v2/recommandations",
            "POST /analytics-v2/entrainement"
        ]
        
        return AnalyticsV2Response(
            page="analytics-v2",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Données Analytics V2 récupérées avec succès",
            data={
                "analytics_v2": analytics_v2_data,
                "modeles_ia_utilises": modeles_ia_utilises,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_analytics_v2_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== PAGE PARAMÈTRES ====================

@app.get("/parametres", response_model=ParametresResponse)
async def get_parametres_data(db: Session = Depends(get_db)):
    """Récupérer les données pour la page Paramètres"""
    try:
        # Mock data pour les paramètres
        parametres_mock = [
            Parametre(
                id=1,
                nom="notifications_email",
                valeur="true",
                categorie="Notifications",
                description="Activer les notifications par email",
                modifiable=True
            ),
            Parametre(
                id=2,
                nom="delai_reponse_max",
                valeur="7",
                categorie="Workflow",
                description="Délai maximum de réponse en jours",
                modifiable=True
            ),
            Parametre(
                id=3,
                nom="langue_interface",
                valeur="fr",
                categorie="Interface",
                description="Langue de l'interface utilisateur",
                modifiable=True
            ),
            Parametre(
                id=4,
                nom="version_api",
                valeur="1.0.0",
                categorie="Système",
                description="Version de l'API",
                modifiable=False
            )
        ]
        
        # Catégories
        categories = ["Notifications", "Workflow", "Interface", "Sécurité", "Système"]
        
        # APIs utilisées par cette page
        apis_utilisees = [
            "GET /parametres",
            "PUT /parametres/{id}",
            "GET /parametres/categories",
            "POST /parametres/backup"
        ]
        
        return ParametresResponse(
            page="parametres",
            timestamp=datetime.now().isoformat(),
            success=True,
            message="Paramètres récupérés avec succès",
            data={
                "parametres": parametres_mock,
                "categories": categories,
                "apis_utilisees": apis_utilisees
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur dans get_parametres_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== ENDPOINT GLOBAL POUR TOUTES LES APIS ====================

@app.get("/apis-utilisees")
async def get_all_apis_utilisees():
    """Récupérer toutes les APIs utilisées par page"""
    return {
        "dashboard": [
            "GET /dashboard",
            "GET /plaintes/statistiques",
            "GET /services/repartition",
            "GET /alertes/actives"
        ],
        "nouvelles-plaintes": [
            "GET /nouvelles-plaintes",
            "GET /plaintes/filtres",
            "POST /plaintes/assigner",
            "PUT /plaintes/statut"
        ],
        "en-cours": [
            "GET /en-cours",
            "GET /plaintes/workflow",
            "PUT /plaintes/progression",
            "POST /plaintes/commentaires"
        ],
        "traitees": [
            "GET /traitees",
            "GET /plaintes/statistiques-resolution",
            "POST /plaintes/satisfaction",
            "GET /plaintes/export"
        ],
        "ameliorations": [
            "GET /ameliorations",
            "POST /ameliorations",
            "PUT /ameliorations/{id}",
            "GET /ameliorations/statistiques"
        ],
        "analytics": [
            "GET /analytics",
            "GET /analytics/evolution",
            "GET /analytics/geographie",
            "GET /analytics/performance-services"
        ],
        "analytics-v2": [
            "GET /analytics-v2",
            "GET /analytics-v2/predictions",
            "GET /analytics-v2/insights",
            "GET /analytics-v2/recommandations",
            "POST /analytics-v2/entrainement"
        ],
        "parametres": [
            "GET /parametres",
            "PUT /parametres/{id}",
            "GET /parametres/categories",
            "POST /parametres/backup"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 