#!/usr/bin/env python3
"""
MODÈLES PARTAGÉS - HealthCare AI Architecture ODYSSEE
Inspiré de l'architecture ODYSSEE avec adaptation pour les plaintes hospitalières
Version: 1.0.0 - Architecture ODYSSEE
"""

from sqlalchemy import (
    Boolean, Column, Integer, BigInteger, String, Text, Float, SmallInteger,
    DateTime, Date, ForeignKey, Index, CheckConstraint, func, Enum as SQLEnum,
    JSON, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from datetime import datetime, date, timedelta
from uuid import uuid4
import enum

# Délai standard de réponse à une plainte (en jours) — aligné sur Organisation.configuration.
DELAI_REPONSE_STANDARD_JOURS = 30

Base = declarative_base()

# ==================== ENUMERATIONS ODYSSEE ADAPTÉES ====================

class UserRole(enum.Enum):
    """Rôles utilisateur inspirés d'ODYSSEE"""
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    RESPONSABLE_QUALITE = "RESPONSABLE_QUALITE"
    CHEF_SERVICE = "CHEF_SERVICE"
    MEDECIN = "MEDECIN"
    INFIRMIER = "INFIRMIER"
    TECHNICIEN = "TECHNICIEN"
    SECRETAIRE = "SECRETAIRE"
    PATIENT = "PATIENT"
    UTILISATEUR = "UTILISATEUR"

class StatutPlainte(enum.Enum):
    """Statuts des plaintes (équivalent des statuts widgets ODYSSEE)"""
    RECU = "RECU"
    EN_COURS = "EN_COURS"
    TRAITE = "TRAITE"
    CLOTURE = "CLOTURE"

class PrioritePlainte(enum.Enum):
    """Priorités déterminées par IA (comme les calculs ODYSSEE)"""
    URGENT = "URGENT"
    ELEVE = "ELEVE"
    MOYEN = "MOYEN"
    BAS = "BAS"

class TypeAnalyse(enum.Enum):
    """Types d'analyses LLM (équivalent des types de widgets ODYSSEE)"""
    SENTIMENT = "sentiment"
    CLASSIFICATION = "classification"
    PRIORITE = "priorite"
    SERVICE_SUGGESTION = "service_suggestion"
    ACTION_RECOMMENDATION = "action_recommendation"

class StatutAnalyse(enum.Enum):
    """Statuts des analyses (inspiré du système de tâches ODYSSEE)"""
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    ECHEC = "echec"

class TypeService(enum.Enum):
    """Types de services médicaux (inspiré d'ODYSSEE)"""
    CARDIOLOGIE = "CARDIOLOGIE"
    URGENCES = "URGENCES"
    PEDIATRIE = "PEDIATRIE"
    CHIRURGIE = "CHIRURGIE"
    NEUROLOGIE = "NEUROLOGIE"
    GYNECOLOGIE = "GYNECOLOGIE"
    DERMATOLOGIE = "DERMATOLOGIE"
    ORTHOPEDIE = "ORTHOPEDIE"
    PSYCHIATRIE = "PSYCHIATRIE"
    RADIOLOGIE = "RADIOLOGIE"
    LABORATOIRE = "LABORATOIRE"
    PHARMACIE = "PHARMACIE"
    ADMINISTRATION = "ADMINISTRATION"
    DIRECTION = "DIRECTION"
    QUALITE = "QUALITE"

class TypeFichier(enum.Enum):
    """Types de fichiers supportés"""
    PDF = "PDF"
    DOC = "DOC"
    DOCX = "DOCX"
    TXT = "TXT"
    IMAGE = "IMAGE"
    AUTRE = "AUTRE"

# ==================== MODÈLES INSPIRÉS D'ODYSSEE ====================

class User(Base):
    """Modèle utilisateur inspiré d'ODYSSEE UserSQL"""
    __tablename__ = "utilisateurs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, default=uuid4)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"))
    
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    nom_complet = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    mot_de_passe_hash = Column(String)
    telephone = Column(String)
    telephone_mobile = Column(String)
    
    type_utilisateur = Column(SQLEnum(UserRole), nullable=False)
    fonction = Column(String)
    specialite = Column(String)
    numero_rpps = Column(String)
    
    permissions = Column(JSONB, default=lambda: {})
    configuration = Column(JSONB, default=lambda: {})
    statut = Column(String, nullable=False, default="actif")
    est_actif = Column(Boolean, default=True)
    email_verifie = Column(Boolean, default=False)
    
    derniere_connexion = Column(DateTime)
    tentatives_connexion_echouees = Column(SmallInteger, default=0)
    compte_verrouille_jusqu = Column(DateTime)
    
    date_creation = Column(DateTime, nullable=False, server_default=func.now())
    date_modification = Column(DateTime, onupdate=func.now())
    date_suppression = Column(DateTime)
    
    # Relations
    plaintes_creees = relationship("Plainte", foreign_keys="Plainte.cree_par_id", back_populates="createur")
    analyses_assignees = relationship("Analyse", back_populates="analyste")
    
    # Propriétés pour compatibilité avec les schémas Pydantic
    @property
    def created(self):
        return self.date_creation
    
    @property
    def updated(self):
        return self.date_modification

class Organisation(Base):
    """Organisation hospitalière (équivalent des projects ODYSSEE)"""
    __tablename__ = "organisations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String, nullable=False)
    code_etablissement = Column(String, unique=True, nullable=False)
    
    # Configuration comme les projets ODYSSEE
    configuration = Column(JSONB, default=lambda: {
        "delai_reponse_standard": 30,
        "services_actifs": [],
        "workflow_automatique": True
    })
    
    # Métadonnées
    date_creation = Column(DateTime, server_default=func.now())
    date_modification = Column(DateTime, onupdate=func.now())
    est_actif = Column(Boolean, default=True)
    
    # Relations - Supprimé car Plainte n'a plus d'organisation_id
    
    # Propriétés pour compatibilité avec les schémas Pydantic
    @property
    def created(self):
        return self.date_creation
    
    @property
    def updated(self):
        return self.date_modification

class Service(Base):
    """Service hospitalier - Modèle simplifié SANS organisation avec KPIs"""
    __tablename__ = "services"
    
    # Clés primaires
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Champs obligatoires
    nom = Column(String(255), nullable=False)
    code_service = Column(String(50), nullable=False, unique=True)
    
    # Champs optionnels
    description = Column(Text, nullable=True)
    categorie = Column(String(100), nullable=True)
    
    # KPIs pour le service
    nombre_plaintes_total = Column(Integer, default=0)
    nombre_plaintes_resolues = Column(Integer, default=0)
    temps_moyen_resolution = Column(Float, default=0.0)  # en jours
    taux_satisfaction = Column(Float, default=0.0)       # pourcentage
    
    # Configuration JSON simplifiée
    configuration = Column(JSONB, default=lambda: {
        "email_contact": "",
        "telephone_contact": "",
        "objectif_resolution": 30,  # jours
        "seuil_urgence": 3
    })
    
    # Dates de création et modification
    date_creation = Column(DateTime, nullable=False, server_default=func.now())
    date_modification = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Statut actif/inactif
    est_actif = Column(Boolean, default=True, nullable=False)
    
    # Relations simplifiées
    plaintes = relationship("Plainte", back_populates="service", cascade="all, delete-orphan")
    
    # Index pour performance
    __table_args__ = (
        Index('idx_service_code', 'code_service'),
        Index('idx_service_actif', 'est_actif'),
    )
    
    # Propriétés pour compatibilité avec l'API
    @property
    def created(self):
        return self.date_creation
    
    @property
    def updated(self):
        return self.date_modification

class Plainte(Base):
    """
    Plainte hospitalière - Équivalent des Dashboards ODYSSEE
    Chaque plainte contient des analyses (équivalent des widgets)
    """
    __tablename__ = "plaintes"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, default=uuid4)
    numero_plainte = Column(String, unique=True, nullable=False, index=True)
    numero_interne = Column(String)
    
    # Références simplifiées
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)  # Service obligatoire maintenant
    cree_par_id = Column(Integer, ForeignKey("utilisateurs.id"))
    assignee_a_id = Column(Integer, ForeignKey("utilisateurs.id"))
    
    # Contenu principal
    titre = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    circonstances = Column(Text)
    consequences = Column(Text)
    demande_plaignant = Column(Text)
    
    # Informations du plaignant
    nom_plaignant = Column(String(100))
    prenom_plaignant = Column(String(100))
    email_plaignant = Column(String(255))
    telephone_plaignant = Column(String(20))
    mode_reception = Column(String(50))  # email, papier, oral, autre
    
    # Statut et priorité (déterminée par IA comme les calculs ODYSSEE)
    statut = Column(SQLEnum(StatutPlainte), default=StatutPlainte.RECU)
    priorite = Column(SQLEnum(PrioritePlainte), default=PrioritePlainte.MOYEN)
    
    # Classification automatique (résultat des analyses)
    categorie_principale = Column(String)
    sous_categorie = Column(String)
    mots_cles = Column(JSONB, default=list)
    score_sentiment = Column(Float)  # -1 à 1
    score_urgence_ia = Column(Float)    # 0 à 1
    # Métadonnées d'analyse IA (legacy - sera remplacé par la relation)
    # analyse_ia_legacy = Column(JSONB, default=dict)  # Temporairement commenté
    
    # Dates importantes
    date_incident = Column(Date)
    date_limite_reponse = Column(Date)
    date_resolution = Column(DateTime)
    date_creation = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    date_modification = Column(DateTime, onupdate=func.now())
    date_suppression = Column(DateTime)

    # Réponse officielle au plaignant + accusé de réception (cycle qualité)
    reponse_redigee = Column(Text)                       # réponse officielle éditée par le responsable qualité
    reponse_envoyee = Column(Boolean, default=False)
    date_reponse_envoyee = Column(DateTime)
    accuse_reception_envoye = Column(Boolean, default=False)
    date_accuse_reception = Column(DateTime)

    # Relations simplifiées
    service = relationship("Service", back_populates="plaintes")
    createur = relationship("User", foreign_keys=[cree_par_id], back_populates="plaintes_creees")
    assigned_user = relationship("User", foreign_keys=[assignee_a_id])
    analyses = relationship("Analyse", back_populates="plainte", cascade="all, delete-orphan")
    analyse_ia = relationship("AnalyseIA", back_populates="plainte", uselist=False, cascade="all, delete-orphan")
    documents = relationship("DocumentPlainte", back_populates="plainte", cascade="all, delete-orphan")
    
    # Index pour performance
    __table_args__ = (
        Index('idx_plainte_statut_priorite', 'statut', 'priorite'),
        Index('idx_plainte_service_date', 'service_id', 'date_creation'),
        Index('idx_plainte_numero', 'numero_plainte'),
    )
    
    # Propriétés pour compatibilité avec les schémas Pydantic
    @property
    def created(self):
        return self.date_creation

    @property
    def updated(self):
        return self.date_modification

    @property
    def est_en_retard(self) -> bool:
        """True si le délai de réponse est dépassé et la plainte n'est pas clôturée."""
        if self.date_limite_reponse is None:
            return False
        if self.statut in (StatutPlainte.TRAITE, StatutPlainte.CLOTURE):
            return False
        return self.date_limite_reponse < date.today()

    @property
    def jours_restants(self):
        """Jours avant l'échéance (négatif si en retard), None si pas d'échéance."""
        if self.date_limite_reponse is None:
            return None
        return (self.date_limite_reponse - date.today()).days


# === Automatisations cycle de vie (centralisées pour TOUS les canaux de création/MAJ) ===
@event.listens_for(Plainte, "before_insert")
def _plainte_set_deadline(mapper, connection, target):
    """Calcule automatiquement la date limite de réponse à la création."""
    if target.date_limite_reponse is None:
        base = target.date_creation or datetime.utcnow()
        target.date_limite_reponse = (base + timedelta(days=DELAI_REPONSE_STANDARD_JOURS)).date()


@event.listens_for(Plainte, "before_update")
def _plainte_set_resolution(mapper, connection, target):
    """Pose date_resolution à la clôture (TRAITE/CLOTURE), la retire en cas de réouverture."""
    if target.statut in (StatutPlainte.TRAITE, StatutPlainte.CLOTURE):
        if target.date_resolution is None:
            target.date_resolution = datetime.utcnow()
    elif target.statut in (StatutPlainte.RECU, StatutPlainte.EN_COURS):
        target.date_resolution = None


class Analyse(Base):
    """
    Analyse LLM d'une plainte - Équivalent des Widgets ODYSSEE
    Chaque analyse est une tâche asynchrone comme les widgets de calcul ODYSSEE
    """
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plainte_id = Column(BigInteger, ForeignKey("plaintes.id"), nullable=False)
    
    # Type d'analyse (équivalent du type de widget ODYSSEE)
    type_analyse = Column(SQLEnum(TypeAnalyse), nullable=False)
    statut = Column(SQLEnum(StatutAnalyse), default=StatutAnalyse.EN_ATTENTE)
    
    # Paramètres d'entrée (comme les paramètres de widgets ODYSSEE)
    parametres_entree = Column(JSONB, default=dict)
    
    # Résultats de l'analyse (comme les résultats de widgets ODYSSEE)
    resultats = Column(JSONB, default=dict)
    
    # Métadonnées d'exécution (comme ODYSSEE)
    task_id = Column(String)  # ID de la tâche Celery
    duree_execution = Column(Float)  # En secondes
    erreur_message = Column(Text)
    
    # Assignation (optionnelle)
    analyste_id = Column(Integer, ForeignKey("utilisateurs.id"))
    
    # Dates d'exécution (comme les tâches ODYSSEE)
    date_debut = Column(DateTime)
    date_fin = Column(DateTime)
    date_creation = Column(DateTime, server_default=func.now())
    date_modification = Column(DateTime, onupdate=func.now())
    
    # Relations
    plainte = relationship("Plainte", back_populates="analyses")
    analyste = relationship("User", back_populates="analyses_assignees")
    
    # Index pour performance
    __table_args__ = (
        Index('idx_analyse_plainte_type', 'plainte_id', 'type_analyse'),
        Index('idx_analyse_statut_date', 'statut', 'date_creation'),
        Index('idx_analyse_task_id', 'task_id'),
    )
    
    # Propriétés pour compatibilité avec les schémas Pydantic
    @property
    def created(self):
        return self.date_creation
    
    @property
    def updated(self):
        return self.date_modification

class Resource(Base):
    """
    Système de permissions inspiré d'ODYSSEE
    Contrôle l'accès aux plaintes et analyses
    """
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("utilisateurs.id"))
    ressource_type = Column(String, nullable=False)  # 'plainte', 'analyse', 'service'
    ressource_id = Column(BigInteger, nullable=False)
    
    # Permissions (comme ODYSSEE)
    permissions = Column(JSONB, default=lambda: {
        "read": True,
        "write": False,
        "delete": False,
        "execute": False
    })
    
    date_creation = Column(DateTime, server_default=func.now())
    
    # Relations
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_resource_user_type', 'user_id', 'ressource_type'),
        Index('idx_resource_type_id', 'ressource_type', 'ressource_id'),
    )

class AnalyseIA(Base):
    """
    Table pour stocker les analyses IA des plaintes
    Contient sentiment, classification, priorité, résumé et réponse suggérée
    """
    __tablename__ = "analyses_ia"
    
    id = Column(Integer, primary_key=True, index=True)
    plainte_id = Column(Integer, ForeignKey("plaintes.id", ondelete="CASCADE"), unique=True)
    
    # Analyse de sentiment
    sentiment = Column(String(50))
    score_sentiment = Column(Float)
    confiance_sentiment = Column(Float)
    
    # Classification par service
    service_suggere = Column(String(255))
    score_service = Column(Float)
    confiance_service = Column(Float)
    
    # Priorité IA
    priorite_ia = Column(String(50))
    score_priorite = Column(Float)
    urgence_detectee = Column(Boolean, default=False)
    
    # Résumé et réponse IA
    resume_ia = Column(Text)
    reponse_suggeree = Column(Text)
    mots_cles_detectes = Column(ARRAY(String))  # Array de mots-clés
    
    # Métadonnées d'analyse
    modele_utilise = Column(String(100))
    version_modele = Column(String(50))
    temps_traitement = Column(Float)  # en secondes
    statut_analyse = Column(String(50), default="en_cours")
    
    # Timestamps
    date_analyse = Column(DateTime, default=datetime.utcnow)
    date_mise_a_jour = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    plainte = relationship("Plainte", back_populates="analyse_ia")

class NotePlainte(Base):
    """Note d'instruction interne attachée à une plainte (investigation, échanges)."""
    __tablename__ = "notes_plaintes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plainte_id = Column(BigInteger, ForeignKey("plaintes.id", ondelete="CASCADE"), nullable=False, index=True)
    auteur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    contenu = Column(Text, nullable=False)
    date_creation = Column(DateTime, server_default=func.now())

    auteur = relationship("User")

class AuditLog(Base):
    """
    Journal d'audit inspiré d'ODYSSEE
    Traçabilité de toutes les actions
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("utilisateurs.id"))
    
    # Action et ressource
    action = Column(String, nullable=False)
    ressource_type = Column(String, nullable=False)
    ressource_id = Column(BigInteger)
    
    # Détails de l'action
    details = Column(JSONB, default=dict)
    donnees_avant = Column(JSONB)
    donnees_apres = Column(JSONB)
    
    # Contexte
    adresse_ip = Column(String)
    user_agent = Column(String)
    
    date_creation = Column(DateTime, server_default=func.now())
    
    # Relations
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_audit_user_date', 'user_id', 'date_creation'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_ressource', 'ressource_type', 'ressource_id'),
    )


class DocumentPlainte(Base):
    """
    Documents attachés aux plaintes
    Permet de stocker les fichiers liés à chaque plainte
    """
    __tablename__ = "documents_plaintes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plainte_id = Column(BigInteger, ForeignKey("plaintes.id", ondelete="CASCADE"), nullable=False)
    
    # Informations du fichier
    nom_fichier = Column(String(255), nullable=False)  # Nom original du fichier
    nom_stockage = Column(String(500), nullable=False)  # Nom sur le disque (avec préfixe plainte)
    chemin_fichier = Column(String(1000), nullable=False)  # Chemin complet
    type_fichier = Column(SQLEnum(TypeFichier), default=TypeFichier.AUTRE)
    taille_fichier = Column(BigInteger)  # Taille en octets
    mime_type = Column(String(100))
    
    # Métadonnées
    description = Column(Text)
    est_piece_jointe_originale = Column(Boolean, default=True)  # True si uploadé avec la plainte
    
    # Dates
    date_upload = Column(DateTime, nullable=False, server_default=func.now())
    date_modification = Column(DateTime, onupdate=func.now())
    
    # Relations
    plainte = relationship("Plainte", back_populates="documents")
    
    # Index pour performance
    __table_args__ = (
        Index('idx_document_plainte', 'plainte_id'),
        Index('idx_document_type', 'type_fichier'),
    )


class AIAnalysisResult(Base):
    """
    Stockage des résultats d'analyse IA
    Permet de conserver l'historique des analyses et d'afficher la dernière analyse
    """
    __tablename__ = "ai_analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), unique=True, nullable=False)  # UUID de la tâche
    
    # Informations de l'analyse
    total_plaintes_analysees = Column(Integer, default=0)
    nombre_services = Column(Integer, default=0)
    model_used = Column(String(100))  # Modèle Ollama utilisé
    
    # Résultats JSON
    analyses_par_service = Column(JSONB)  # Liste des analyses par service
    causes_globales = Column(JSONB)  # Top causes identifiées
    services_critiques = Column(JSONB)  # Liste des services critiques
    
    # Statut
    status = Column(String(50), default='completed')  # pending, running, completed, error
    error_message = Column(Text)
    
    # Dates
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime)
    
    # Métadonnées
    duree_secondes = Column(Float)  # Durée de l'analyse en secondes
    
    # Index pour performance
    __table_args__ = (
        Index('idx_ai_analysis_date', 'completed_at'),
        Index('idx_ai_analysis_status', 'status'),
    )