#!/usr/bin/env python3
"""
MODÈLES UNIFIÉS - HealthCare AI
Combine V1 et V2 en une seule définition de modèles propre
Version: 1.0.0 - Architecture Clean
"""

from sqlalchemy import (
    Boolean, Column, Integer, BigInteger, String, Text, Float, SmallInteger,
    DateTime, Date, ForeignKey, Index, CheckConstraint, func, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TSVECTOR
from datetime import datetime
import uuid
import enum

Base = declarative_base()

# ==================== ENUMERATIONS ====================

class TypeServiceEnum(enum.Enum):
    """Types de services médicaux"""
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

class TypeUtilisateurEnum(enum.Enum):
    """Types d'utilisateurs"""
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    RESPONSABLE_QUALITE = "RESPONSABLE_QUALITE"
    CHEF_SERVICE = "CHEF_SERVICE"
    MEDECIN = "MEDECIN"
    INFIRMIER = "INFIRMIER"
    TECHNICIEN = "TECHNICIEN"
    SECRETAIRE = "SECRETAIRE"
    UTILISATEUR = "UTILISATEUR"

class StatutPlainteEnum(enum.Enum):
    """Statuts des plaintes"""
    RECU = "RECU"
    EN_COURS = "EN_COURS"
    TRAITE = "TRAITE"
    CLOTURE = "CLOTURE"

class PrioriteEnum(enum.Enum):
    """Niveaux de priorité"""
    URGENT = "URGENT"
    ELEVE = "ELEVE"
    MOYEN = "MOYEN"
    BAS = "BAS"

class TypeFichierEnum(enum.Enum):
    """Types de fichiers"""
    PDF = "PDF"
    DOC = "DOC"
    DOCX = "DOCX"
    TXT = "TXT"
    IMAGE = "IMAGE"
    AUTRE = "AUTRE"

# ==================== TABLES PRINCIPALES ====================

class Organisation(Base):
    """Table des organisations (hôpitaux, cliniques)"""
    __tablename__ = "organisations"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Informations de base
    nom = Column(String(255), nullable=False)
    nom_court = Column(String(100), nullable=False)
    code_etablissement = Column(String(50), unique=True, nullable=False, index=True)
    
    # Contact
    email = Column(String(255), nullable=True)
    telephone = Column(String(20), nullable=True)
    adresse = Column(Text, nullable=True)
    site_web = Column(String(255), nullable=True)
    
    # Identification officielle
    siret = Column(String(14), nullable=True, unique=True)
    finess = Column(String(20), nullable=True, unique=True)
    
    # Configuration
    configuration = Column(JSONB, default={}, nullable=False)
    
    # Métadonnées
    date_creation = Column(DateTime, default=func.now(), nullable=False)
    date_modification = Column(DateTime, default=func.now(), onupdate=func.now())
    est_actif = Column(Boolean, default=True, nullable=False)
    
    # Relations
    services = relationship("Service", back_populates="organisation")
    utilisateurs = relationship("Utilisateur", back_populates="organisation")
    plaintes = relationship("Plainte", back_populates="organisation")
    
    # Index
    __table_args__ = (
        Index('idx_organisation_code', 'code_etablissement'),
        Index('idx_organisation_actif', 'est_actif'),
    )
    
    @property
    def uuid_str(self):
        """Retourne l'UUID sous forme de string"""
        return str(self.uuid) if self.uuid else None

class Service(Base):
    """Table des services médicaux et administratifs"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    
    # Informations de base
    nom = Column(String(255), nullable=False)
    code_service = Column(String(20), nullable=False)
    type_service = Column(SQLEnum(TypeServiceEnum), nullable=False)
    description = Column(Text, nullable=True)
    
    # Localisation
    batiment = Column(String(100), nullable=True)
    etage = Column(String(50), nullable=True)
    secteur = Column(String(100), nullable=True)
    
    # Responsables
    chef_service_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    responsable_qualite_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    
    # Configuration
    configuration = Column(JSONB, default={}, nullable=False)
    
    # Métadonnées
    date_creation = Column(DateTime, default=func.now(), nullable=False)
    date_modification = Column(DateTime, default=func.now(), onupdate=func.now())
    est_actif = Column(Boolean, default=True, nullable=False)
    
    # Relations
    organisation = relationship("Organisation", back_populates="services")
    utilisateurs = relationship("Utilisateur", back_populates="service", foreign_keys="[Utilisateur.service_id]")
    plaintes = relationship("Plainte", back_populates="service")
    
    # Relations pour les responsables (séparées)
    chef_service = relationship("Utilisateur", foreign_keys=[chef_service_id], post_update=True)
    responsable_qualite = relationship("Utilisateur", foreign_keys=[responsable_qualite_id], post_update=True)
    
    # Index
    __table_args__ = (
        Index('idx_service_organisation', 'organisation_id', 'est_actif'),
        Index('idx_service_type', 'type_service', 'est_actif'),
    )
    
    @property
    def uuid_str(self):
        """Retourne l'UUID sous forme de string"""
        return str(self.uuid) if self.uuid else None

class Utilisateur(Base):
    """Table des utilisateurs du système"""
    __tablename__ = "utilisateurs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    # Informations personnelles
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    nom_complet = Column(String(255), nullable=False)
    
    # Authentification
    email = Column(String(255), unique=True, nullable=False, index=True)
    mot_de_passe_hash = Column(String(255), nullable=True)
    
    # Contact
    telephone = Column(String(20), nullable=True)
    telephone_mobile = Column(String(20), nullable=True)
    
    # Profil professionnel
    type_utilisateur = Column(SQLEnum(TypeUtilisateurEnum), nullable=False)
    fonction = Column(String(100), nullable=True)
    specialite = Column(String(100), nullable=True)
    numero_rpps = Column(String(20), nullable=True)
    
    # Permissions et configuration
    permissions = Column(JSONB, default=lambda: ["CONSULTER_PLAINTES"], nullable=False)
    configuration = Column(JSONB, default=lambda: {
        "notifications_email": True,
        "notifications_sms": False,
        "langue_preferee": "fr",
        "theme": "light"
    }, nullable=False)
    
    # Statut
    statut = Column(String(20), default="ACTIF", nullable=False)
    est_actif = Column(Boolean, default=True, nullable=False)
    email_verifie = Column(Boolean, default=False, nullable=False)
    
    # Sécurité
    derniere_connexion = Column(DateTime, nullable=True)
    tentatives_connexion_echouees = Column(SmallInteger, default=0, nullable=False)
    compte_verrouille_jusqu = Column(DateTime, nullable=True)
    
    # Métadonnées
    date_creation = Column(DateTime, default=func.now(), nullable=False)
    date_modification = Column(DateTime, default=func.now(), onupdate=func.now())
    date_suppression = Column(DateTime, nullable=True)
    
    # Relations
    organisation = relationship("Organisation", back_populates="utilisateurs")
    service = relationship("Service", back_populates="utilisateurs", foreign_keys=[service_id])
    plaintes_assignees = relationship("Plainte", foreign_keys="[Plainte.assignee_a_id]")
    plaintes_creees = relationship("Plainte", foreign_keys="[Plainte.cree_par_id]")
    fichiers_uploades = relationship("FichierPlainte", back_populates="uploade_par")
    
    # Index
    __table_args__ = (
        Index('idx_utilisateur_email_actif', 'email', 'est_actif'),
        Index('idx_utilisateur_type_actif', 'type_utilisateur', 'est_actif'),
        Index('idx_utilisateur_organisation', 'organisation_id', 'est_actif'),
    )
    
    @property
    def uuid_str(self):
        """Retourne l'UUID sous forme de string"""
        return str(self.uuid) if self.uuid else None

class Plainte(Base):
    """Table principale des plaintes"""
    __tablename__ = "plaintes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Identifiants métier
    numero_plainte = Column(String(50), unique=True, nullable=False, index=True)
    numero_interne = Column(String(50), nullable=True)
    
    # Entités liées
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    # Workflow
    statut = Column(SQLEnum(StatutPlainteEnum), default=StatutPlainteEnum.RECU, nullable=False)
    priorite = Column(SQLEnum(PrioriteEnum), default=PrioriteEnum.MOYEN, nullable=False)
    
    # Contenu
    titre = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    circonstances = Column(Text, nullable=True)
    consequences = Column(Text, nullable=True)
    demande_plaignant = Column(Text, nullable=True)
    
    # Classification
    categorie_principale = Column(String(100), nullable=True)
    sous_categorie = Column(String(100), nullable=True)
    mots_cles = Column(JSONB, default=[], nullable=False)
    
    # Dates importantes
    date_incident = Column(Date, nullable=True)
    date_limite_reponse = Column(Date, nullable=True)
    date_resolution = Column(DateTime, nullable=True)
    
    # Assignation
    assignee_a_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    cree_par_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    
    # IA et analytics
    score_sentiment = Column(Float, nullable=True)
    score_urgence_ia = Column(Float, nullable=True)
    analyse_ia = Column(JSONB, default={}, nullable=False)
    
    # Métadonnées
    date_creation = Column(DateTime, default=func.now(), nullable=False)
    date_modification = Column(DateTime, default=func.now(), onupdate=func.now())
    date_suppression = Column(DateTime, nullable=True)
    
    # Relations
    organisation = relationship("Organisation", back_populates="plaintes")
    service = relationship("Service", back_populates="plaintes")
    assignee_a = relationship("Utilisateur", foreign_keys=[assignee_a_id])
    cree_par = relationship("Utilisateur", foreign_keys=[cree_par_id])
    fichiers = relationship("FichierPlainte", back_populates="plainte", cascade="all, delete-orphan")
    
    # Index
    __table_args__ = (
        Index('idx_plainte_numero', 'numero_plainte'),
        Index('idx_plainte_statut_priorite', 'statut', 'priorite'),
        Index('idx_plainte_organisation_date', 'organisation_id', 'date_creation'),
        Index('idx_plainte_assignation', 'assignee_a_id', 'statut'),
    )
    
    @property
    def uuid_str(self):
        """Retourne l'UUID sous forme de string"""
        return str(self.uuid) if self.uuid else None

class FichierPlainte(Base):
    """Fichiers attachés aux plaintes"""
    __tablename__ = "fichiers_plaintes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    plainte_id = Column(BigInteger, ForeignKey("plaintes.id", ondelete="CASCADE"), nullable=False)
    
    # Informations fichier
    nom_original = Column(String(500), nullable=False)
    nom_stockage = Column(String(500), nullable=False, unique=True)
    chemin_relatif = Column(String(1000), nullable=False)
    type_fichier = Column(SQLEnum(TypeFichierEnum), nullable=False)
    mime_type = Column(String(255), nullable=False)
    
    # Métadonnées techniques
    taille_octets = Column(BigInteger, nullable=False)
    checksum_md5 = Column(String(32), nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    
    # Traitement et extraction
    texte_extrait = Column(Text, nullable=True)
    texte_extrait_tsvector = Column(TSVECTOR, nullable=True)
    metadonnees_extraction = Column(JSONB, default={}, nullable=False)
    est_traite = Column(Boolean, default=False, nullable=False)
    date_traitement = Column(DateTime, nullable=True)
    erreur_traitement = Column(Text, nullable=True)
    
    # Sécurité
    est_chiffre = Column(Boolean, default=False, nullable=False)
    niveau_confidentialite = Column(String(50), default="PUBLIC", nullable=False)
    
    # Métadonnées
    date_upload = Column(DateTime, default=func.now(), nullable=False)
    uploade_par_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    date_suppression = Column(DateTime, nullable=True)
    
    # Relations
    plainte = relationship("Plainte", back_populates="fichiers")
    uploade_par = relationship("Utilisateur", back_populates="fichiers_uploades")
    
    # Index et contraintes
    __table_args__ = (
        Index('idx_fichier_plainte_id', 'plainte_id'),
        Index('idx_fichier_type_date', 'type_fichier', 'date_upload'),
        Index('idx_fichier_checksum', 'checksum_md5'),
        CheckConstraint('taille_octets > 0', name='ck_taille_positive'),
    )

class AuditLog(Base):
    """Table d'audit pour traçabilité"""
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Identifiants
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Action
    action = Column(String(50), nullable=False)
    ressource_type = Column(String(100), nullable=False)
    ressource_id = Column(String(100), nullable=True)
    
    # Détails
    description = Column(Text, nullable=False)
    donnees_avant = Column(JSONB, nullable=True)
    donnees_apres = Column(JSONB, nullable=True)
    
    # Contexte
    adresse_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Métadonnées
    date_action = Column(DateTime, default=func.now(), nullable=False)
    
    # Relations
    utilisateur = relationship("Utilisateur")
    
    # Index
    __table_args__ = (
        Index('idx_audit_utilisateur_date', 'utilisateur_id', 'date_action'),
        Index('idx_audit_action_ressource', 'action', 'ressource_type'),
        Index('idx_audit_date', 'date_action'),
    ) 