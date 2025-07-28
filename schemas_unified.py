#!/usr/bin/env python3
"""
SCHÉMAS UNIFIÉS - HealthCare AI
Schémas Pydantic unifiés pour l'API
Version: 1.0.0 - Architecture Clean
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum

# ==================== ENUMS ====================

class TypeServiceEnum(str, Enum):
    CARDIOLOGIE = "CARDIOLOGIE"
    URGENCES = "URGENCES"
    PEDIATRIE = "PEDIATRIE"
    CHIRURGIE = "CHIRURGIE"
    NEUROLOGIE = "NEUROLOGIE"
    GYNECOLOGIE = "GYNECOLOGIE"
    DERMATOLOGIE = "DERMATOLOGIE"
    ORTHOPÉDIE = "ORTHOPÉDIE"
    PSYCHIATRIE = "PSYCHIATRIE"
    RADIOLOGIE = "RADIOLOGIE"
    LABORATOIRE = "LABORATOIRE"
    PHARMACIE = "PHARMACIE"
    ADMINISTRATION = "ADMINISTRATION"
    DIRECTION = "DIRECTION"
    QUALITE = "QUALITE"

class TypeUtilisateurEnum(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    RESPONSABLE_QUALITE = "RESPONSABLE_QUALITE"
    CHEF_SERVICE = "CHEF_SERVICE"
    MEDECIN = "MEDECIN"
    INFIRMIER = "INFIRMIER"
    TECHNICIEN = "TECHNICIEN"
    SECRETAIRE = "SECRETAIRE"
    UTILISATEUR = "UTILISATEUR"

class StatutPlainteEnum(str, Enum):
    RECU = "RECU"
    EN_COURS = "EN_COURS"
    TRAITE = "TRAITE"
    CLOTURE = "CLOTURE"

class PrioriteEnum(str, Enum):
    URGENT = "URGENT"
    ELEVE = "ELEVE"
    MOYEN = "MOYEN"
    BAS = "BAS"

class TypeFichierEnum(str, Enum):
    PDF = "PDF"
    DOC = "DOC"
    DOCX = "DOCX"
    TXT = "TXT"
    IMAGE = "IMAGE"
    AUTRE = "AUTRE"

# ==================== ORGANISATIONS ====================

class OrganisationBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)
    nom_court: str = Field(..., min_length=1, max_length=100)
    code_etablissement: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telephone: Optional[str] = Field(None, max_length=20)
    adresse: Optional[str] = None
    site_web: Optional[str] = None
    siret: Optional[str] = Field(None, min_length=14, max_length=14)
    finess: Optional[str] = Field(None, max_length=20)
    configuration: Dict[str, Any] = Field(default_factory=dict)

class OrganisationCreate(OrganisationBase):
    pass

class OrganisationUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=255)
    nom_court: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telephone: Optional[str] = Field(None, max_length=20)
    adresse: Optional[str] = None
    site_web: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    est_actif: Optional[bool] = None

class OrganisationResponse(OrganisationBase):
    id: int
    uuid: str = Field(alias="uuid_str")
    date_creation: datetime
    date_modification: Optional[datetime]
    est_actif: bool
    
    class Config:
        from_attributes = True
        # Exclure les relations pour éviter les erreurs de sérialisation
        exclude = {"services", "utilisateurs", "plaintes"}
        populate_by_name = True

# ==================== SERVICES ====================

class ServiceBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)
    code_service: str = Field(..., min_length=1, max_length=20)
    type_service: TypeServiceEnum
    description: Optional[str] = None
    batiment: Optional[str] = Field(None, max_length=100)
    etage: Optional[str] = Field(None, max_length=50)
    secteur: Optional[str] = Field(None, max_length=100)
    configuration: Dict[str, Any] = Field(default_factory=dict)

class ServiceCreate(ServiceBase):
    organisation_id: int
    chef_service_id: Optional[int] = None
    responsable_qualite_id: Optional[int] = None

class ServiceUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=255)
    code_service: Optional[str] = Field(None, min_length=1, max_length=20)
    type_service: Optional[TypeServiceEnum] = None
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    est_actif: Optional[bool] = None

class ServiceResponse(ServiceBase):
    id: int
    uuid: str = Field(alias="uuid_str")
    organisation_id: int
    chef_service_id: Optional[int]
    responsable_qualite_id: Optional[int]
    date_creation: datetime
    date_modification: Optional[datetime]
    est_actif: bool
    
    class Config:
        from_attributes = True
        # Exclure les relations pour éviter les erreurs de sérialisation
        exclude = {"organisation", "utilisateurs", "plaintes", "chef_service", "responsable_qualite"}
        populate_by_name = True

# ==================== UTILISATEURS ====================

class UtilisateurBase(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telephone: Optional[str] = Field(None, max_length=20)
    telephone_mobile: Optional[str] = Field(None, max_length=20)
    type_utilisateur: TypeUtilisateurEnum
    fonction: Optional[str] = Field(None, max_length=100)
    specialite: Optional[str] = Field(None, max_length=100)
    numero_rpps: Optional[str] = Field(None, max_length=20)
    permissions: List[str] = Field(default_factory=lambda: ["CONSULTER_PLAINTES"])
    configuration: Dict[str, Any] = Field(default_factory=lambda: {
        "notifications_email": True,
        "notifications_sms": False,
        "langue_preferee": "fr",
        "theme": "light"
    })
    statut: str = Field(default="ACTIF", max_length=20)

class UtilisateurCreate(UtilisateurBase):
    organisation_id: int
    service_id: Optional[int] = None
    mot_de_passe: Optional[str] = Field(None, min_length=8)

class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    telephone: Optional[str] = Field(None, max_length=20)
    telephone_mobile: Optional[str] = Field(None, max_length=20)
    type_utilisateur: Optional[TypeUtilisateurEnum] = None
    fonction: Optional[str] = Field(None, max_length=100)
    specialite: Optional[str] = Field(None, max_length=100)
    service_id: Optional[int] = None
    permissions: Optional[List[str]] = None
    configuration: Optional[Dict[str, Any]] = None
    statut: Optional[str] = None
    est_actif: Optional[bool] = None

class UtilisateurResponse(UtilisateurBase):
    id: int
    uuid: str = Field(alias="uuid_str")
    organisation_id: int
    service_id: Optional[int]
    nom_complet: str
    est_actif: bool
    email_verifie: bool
    derniere_connexion: Optional[datetime]
    date_creation: datetime
    
    class Config:
        from_attributes = True
        # Exclure les relations pour éviter les erreurs de sérialisation
        exclude = {"organisation", "service", "plaintes_assignees", "plaintes_creees", "fichiers_uploades"}
        populate_by_name = True

# ==================== PLAINTES ====================

class PlainteBase(BaseModel):
    titre: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    circonstances: Optional[str] = None
    consequences: Optional[str] = None
    demande_plaignant: Optional[str] = None
    priorite: PrioriteEnum = PrioriteEnum.MOYEN
    categorie_principale: Optional[str] = Field(None, max_length=100)
    sous_categorie: Optional[str] = Field(None, max_length=100)
    mots_cles: List[str] = Field(default_factory=list)
    date_incident: Optional[date] = None
    date_limite_reponse: Optional[date] = None

class PlainteCreate(PlainteBase):
    organisation_id: int
    service_id: Optional[int] = None
    assignee_a_id: Optional[int] = None
    cree_par_id: Optional[int] = None

class PlainteUpdate(BaseModel):
    titre: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    circonstances: Optional[str] = None
    consequences: Optional[str] = None
    demande_plaignant: Optional[str] = None
    statut: Optional[StatutPlainteEnum] = None
    priorite: Optional[PrioriteEnum] = None
    categorie_principale: Optional[str] = None
    sous_categorie: Optional[str] = None
    mots_cles: Optional[List[str]] = None
    assignee_a_id: Optional[int] = None
    date_resolution: Optional[datetime] = None

class PlainteResponse(PlainteBase):
    id: int
    uuid: str = Field(alias="uuid_str")
    numero_plainte: str
    numero_interne: Optional[str]
    organisation_id: int
    service_id: Optional[int]
    statut: StatutPlainteEnum
    assignee_a_id: Optional[int]
    cree_par_id: Optional[int]
    score_sentiment: Optional[float]
    score_urgence_ia: Optional[float]
    analyse_ia: Dict[str, Any]
    date_creation: datetime
    date_modification: Optional[datetime]
    date_resolution: Optional[datetime]
    
    class Config:
        from_attributes = True
        # Exclure les relations pour éviter les erreurs de sérialisation
        exclude = {"organisation", "service", "assignee_a", "cree_par", "fichiers"}
        populate_by_name = True

class PlaintesListResponse(BaseModel):
    plaintes: List[PlainteResponse]
    total: int
    skip: int
    limit: int

# ==================== FICHIERS ====================

class FichierPlainteResponse(BaseModel):
    id: int
    uuid: str
    plainte_id: int
    nom_original: str
    nom_stockage: str
    type_fichier: TypeFichierEnum
    mime_type: str
    taille_octets: int
    est_traite: bool
    date_upload: datetime
    uploade_par_id: int
    
    class Config:
        from_attributes = True

# ==================== STATISTIQUES ====================

class StatistiquesResponse(BaseModel):
    total_plaintes: int
    nouvelles: int
    en_cours: int
    traitees: int
    urgentes: int
    elevees: int
    moyennes: int
    basses: int

class AnalyticsResponse(BaseModel):
    periode: str
    total_plaintes: int
    plaintes_par_service: Dict[str, int]
    plaintes_par_priorite: Dict[str, int]
    plaintes_par_statut: Dict[str, int]
    temps_moyen_traitement: Optional[float]
    satisfaction_moyenne: Optional[float]

# ==================== RÉPONSES GÉNÉRIQUES ====================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# ==================== FILTRES ====================

class PlaintesFilters(BaseModel):
    organisation_id: Optional[int] = None
    service_id: Optional[int] = None
    statut: Optional[StatutPlainteEnum] = None
    priorite: Optional[PrioriteEnum] = None
    assignee_a_id: Optional[int] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    mots_cles: Optional[List[str]] = None
    recherche_texte: Optional[str] = None

# ==================== VALIDATION ====================

class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    mot_de_passe: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    utilisateur: Optional[UtilisateurResponse] = None
    message: str

# ==================== UPLOAD ====================

class UploadResponse(BaseModel):
    success: bool
    plainte_id: int
    numero_plainte: str
    fichier_id: int
    message: str 