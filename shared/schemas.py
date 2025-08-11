#!/usr/bin/env python3
"""
SCHÉMAS PYDANTIC PARTAGÉS - HealthCare AI Architecture ODYSSEE
Schémas de validation inspirés d'ODYSSEE pour l'API et les Workers
Version: 1.0.0 - Architecture ODYSSEE
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

from .models import (
    UserRole, StatutPlainte, PrioritePlainte, 
    TypeAnalyse, StatutAnalyse, TypeService, TypeFichier
)

# ==================== SCHÉMAS BASE (INSPIRÉS D'ODYSSEE) ====================

class TimestampMixin(BaseModel):
    """Mixin pour les timestamps comme dans ODYSSEE"""
    created: datetime
    updated: Optional[datetime] = None

class MetadataMixin(BaseModel):
    """Mixin pour les métadonnées JSON comme dans ODYSSEE"""
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ==================== SCHÉMAS UTILISATEUR ====================

class UserBase(BaseModel):
    """Schéma de base utilisateur (inspiré d'ODYSSEE)"""
    email: EmailStr
    nom_complet: Optional[str] = None
    type_utilisateur: UserRole = UserRole.PATIENT
    est_actif: bool = True
    configuration: Dict[str, Any] = Field(default_factory=dict)

class UserCreate(UserBase):
    """Création d'utilisateur avec mot de passe"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """Mise à jour utilisateur"""
    nom_complet: Optional[str] = None
    type_utilisateur: Optional[UserRole] = None
    est_actif: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None

class UserResponse(UserBase, TimestampMixin):
    """Réponse utilisateur (pas de mot de passe)"""
    id: int
    email_verifie: bool
    
    model_config = ConfigDict(from_attributes=True)

# Organisation supprimée - Architecture simplifiée sans organisations

# ==================== SCHÉMAS SERVICE ====================

class ServiceBase(BaseModel):
    """Service hospitalier avec KPIs - simplifié SANS organisation"""
    nom: str = Field(..., min_length=2, max_length=255)
    code_service: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    categorie: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)

class ServiceCreate(ServiceBase):
    """Création de service"""
    pass

class ServiceUpdate(BaseModel):
    """Mise à jour service"""
    nom: Optional[str] = None
    code_service: Optional[str] = None
    description: Optional[str] = None
    categorie: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

class ServiceKPIs(BaseModel):
    """KPIs du service"""
    nombre_plaintes_total: int = 0
    nombre_plaintes_resolues: int = 0
    temps_moyen_resolution: float = 0.0
    taux_satisfaction: float = 0.0

class ServiceResponse(ServiceBase, TimestampMixin):
    """Réponse service avec KPIs"""
    id: int
    est_actif: bool
    # KPIs inclus
    nombre_plaintes_total: int
    nombre_plaintes_resolues: int
    temps_moyen_resolution: float
    taux_satisfaction: float
    
    model_config = ConfigDict(from_attributes=True)

# ==================== SCHÉMAS PLAINTE (ÉQUIVALENT DASHBOARDS ODYSSEE) ====================

class PlainteBase(BaseModel):
    """Plainte de base (équivalent dashboard ODYSSEE)"""
    titre: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    date_incident: Optional[datetime] = None
    
class PlainteCreate(PlainteBase):
    """Création de plainte (comme création de dashboard ODYSSEE)"""
    service_id: int  # Service obligatoire maintenant
    # Champs additionnels pour formulaire manuel
    nom_plaignant: Optional[str] = None
    prenom_plaignant: Optional[str] = None
    email_plaignant: Optional[str] = None
    telephone_plaignant: Optional[str] = None
    mode_reception: Optional[str] = None
    assigned_user_id: Optional[int] = None
    trigger_analyses: Optional[bool] = True
    # Les analyses seront déclenchées automatiquement après création

class PlainteUpdate(BaseModel):
    """Mise à jour plainte"""
    titre: Optional[str] = None
    description: Optional[str] = None
    statut: Optional[StatutPlainte] = None
    service_id: Optional[int] = None
    date_incident: Optional[datetime] = None

class PlainteResponse(PlainteBase, TimestampMixin):
    """Réponse plainte complète (comme dashboard ODYSSEE avec widgets)"""
    id: int
    numero_plainte: str
    service_id: int  # Service obligatoire maintenant
    cree_par_id: int  # Correspond au champ du modèle SQLAlchemy
    
    # Statut et classification
    statut: StatutPlainte
    priorite: PrioritePlainte
    categorie_principale: Optional[str] = None
    mots_cles: List[str] = Field(default_factory=list)
    
    # Scores IA (résultats des analyses)
    score_sentiment: Optional[float] = None
    score_urgence_ia: Optional[float] = None
    
    # Métadonnées d'analyse IA
    analyse_ia: Dict[str, Any] = Field(default_factory=dict)
    
    # Dates
    date_limite_reponse: Optional[datetime] = None
    
    # Relations (optionnelles dans la réponse)
    service: Optional[ServiceResponse] = None
    createur: Optional[UserResponse] = None
    analyses: List['AnalyseResponse'] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)

# ==================== SCHÉMAS ANALYSE (ÉQUIVALENT WIDGETS ODYSSEE) ====================

class AnalyseBase(BaseModel):
    """Analyse de base (équivalent widget ODYSSEE)"""
    type_analyse: TypeAnalyse
    parametres_entree: Dict[str, Any] = Field(default_factory=dict)

class AnalyseCreate(AnalyseBase):
    """Création d'analyse (comme exécution de widget ODYSSEE)"""
    plainte_id: int

class AnalyseUpdate(BaseModel):
    """Mise à jour analyse (principalement pour les résultats)"""
    statut: Optional[StatutAnalyse] = None
    resultats: Optional[Dict[str, Any]] = None
    erreur_message: Optional[str] = None

class AnalyseResponse(AnalyseBase, TimestampMixin):
    """Réponse analyse (comme résultat de widget ODYSSEE)"""
    id: int
    plainte_id: int
    statut: StatutAnalyse
    resultats: Dict[str, Any]
    
    # Métadonnées d'exécution
    task_id: Optional[str] = None
    duree_execution: Optional[float] = None
    erreur_message: Optional[str] = None
    analyste_id: Optional[int] = None
    
    # Dates d'exécution
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# ==================== SCHÉMAS DE TÂCHES (POUR CELERY) ====================

class TaskStatus(BaseModel):
    """Statut de tâche Celery (inspiré d'ODYSSEE)"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: Optional[int] = None  # Pourcentage 0-100

class AnalyseTaskRequest(BaseModel):
    """Requête de tâche d'analyse (comme les paramètres de widgets ODYSSEE)"""
    plainte_id: int
    types_analyse: List[str] = Field(default_factory=list)  # Chaînes au lieu d'enums
    parametres: Dict[str, Any] = Field(default_factory=dict)
    priorite_task: str = "normal"  # high, normal, low

class AnalyseTaskResult(BaseModel):
    """Résultat de tâche d'analyse (comme les résultats de widgets ODYSSEE)"""
    plainte_id: int
    analyses_completees: List[AnalyseResponse]
    analyses_echouees: List[Dict[str, Any]] = Field(default_factory=list)
    duree_totale: float
    timestamp: datetime

# ==================== SCHÉMAS STATISTIQUES ET DASHBOARD ====================

class StatistiquesResponse(BaseModel):
    """Statistiques générales (comme les métriques ODYSSEE)"""
    total_plaintes: int
    plaintes_nouvelles: int
    plaintes_en_analyse: int
    plaintes_resolues: int
    
    # Métriques de performance
    temps_moyen_analyse: float  # En minutes
    taux_resolution: float      # Pourcentage
    score_satisfaction_moyen: Optional[float] = None
    
    # Répartitions
    repartition_par_service: Dict[str, int]
    repartition_par_priorite: Dict[str, int]
    
    # Tendances (derniers 30 jours)
    evolution_quotidienne: List[Dict[str, Any]]
    
    timestamp: datetime

class DashboardData(BaseModel):
    """Données complètes du dashboard (inspiré d'ODYSSEE)"""
    statistiques: StatistiquesResponse
    plaintes_recentes: List[PlainteResponse]
    analyses_en_cours: List[AnalyseResponse]
    alertes: List[Dict[str, Any]] = Field(default_factory=list)

# ==================== SCHÉMAS WEBSOCKET ====================

class WebSocketMessage(BaseModel):
    """Message WebSocket pour notifications temps réel"""
    type: str  # 'analyse_complete', 'plainte_update', 'system_alert'
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None

class NotificationAnalyseComplete(BaseModel):
    """Notification d'analyse terminée (comme notification de widget ODYSSEE)"""
    plainte_id: int
    analyse_id: int
    type_analyse: TypeAnalyse
    statut: StatutAnalyse
    resultats_resume: Dict[str, Any]

# ==================== SCHÉMAS DE RÉPONSE GÉNÉRIQUES ====================

class SuccessResponse(BaseModel):
    """Réponse de succès générique"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """Réponse d'erreur générique"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

from typing import Generic, TypeVar, List

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Réponse paginée générique"""
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int

# ==================== MISE À JOUR DES RÉFÉRENCES FORWARD ====================

# Mise à jour des références forward pour éviter les erreurs circulaires
PlainteResponse.model_rebuild()