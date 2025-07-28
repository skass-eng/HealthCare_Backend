#!/usr/bin/env python3
"""
BASE DE DONNÉES UNIFIÉE - HealthCare AI
Configuration de base de données simple et propre
Version: 1.0.0 - Architecture Clean
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator
from config import Settings

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# URL de base de données depuis la configuration
DATABASE_URL = Settings.DATABASE_URL

# Configuration de l'engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Mettre à True pour voir les requêtes SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== FONCTIONS UTILITAIRES ====================

def test_connection() -> bool:
    """Tester la connexion à la base de données"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Connexion à la base de données réussie")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        return False

def create_database_if_not_exists():
    """Créer la base de données si elle n'existe pas"""
    try:
        # Extraire les informations de l'URL
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        
        # Connexion au serveur PostgreSQL (sans base spécifique)
        server_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
        server_engine = create_engine(server_url)
        
        db_name = parsed.path[1:]  # Enlever le '/' initial
        
        with server_engine.connect() as connection:
            # Vérifier si la base existe
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            
            if not result.fetchone():
                # Créer la base de données
                connection.execute(text("COMMIT"))  # Sortir de la transaction
                connection.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"✅ Base de données '{db_name}' créée")
            else:
                logger.info(f"✅ Base de données '{db_name}' existe déjà")
                
        server_engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la base de données: {e}")

def initialize_database():
    """Initialiser la base de données avec les tables"""
    try:
        create_database_if_not_exists()
        
        # Importer les modèles pour créer les tables
        from models_unified import Base
        
        # Créer toutes les tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables créées/mises à jour")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        return False

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager pour les sessions de base de données"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur dans la session de base de données: {e}")
        raise
    finally:
        session.close()

def get_db() -> Generator[Session, None, None]:
    """Générateur de sessions pour FastAPI Depends"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ==================== FONCTIONS DE MAINTENANCE ====================

def reset_database():
    """ATTENTION: Supprimer toutes les tables et les recréer"""
    try:
        from models_unified import Base
        
        logger.warning("⚠️ SUPPRESSION DE TOUTES LES TABLES")
        Base.metadata.drop_all(bind=engine)
        logger.info("🗑️ Tables supprimées")
        
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables recréées")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors du reset: {e}")
        return False

def get_table_info():
    """Obtenir des informations sur les tables"""
    try:
        with engine.connect() as connection:
            # Lister les tables
            tables = connection.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """)
            ).fetchall()
            
            logger.info("📊 Tables existantes:")
            for table in tables:
                # Compter les enregistrements
                try:
                    count = connection.execute(
                        text(f"SELECT COUNT(*) FROM {table[0]}")
                    ).scalar()
                    logger.info(f"  - {table[0]}: {count} enregistrements")
                except:
                    logger.info(f"  - {table[0]}: (erreur comptage)")
            
            return tables
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des infos: {e}")
        return []

def create_sample_data():
    """Créer des données d'exemple de base"""
    try:
        from models_unified import Organisation, Service, Utilisateur
        
        with get_db_session() as session:
            # Vérifier si des données existent déjà
            if session.query(Organisation).count() > 0:
                logger.info("✅ Données d'exemple déjà présentes")
                return True
            
            # Créer une organisation
            org = Organisation(
                nom="Centre Hospitalier Universitaire - Principal",
                nom_court="CHU Principal",
                code_etablissement="CHU_001",
                email="contact@chu-principal.fr",
                telephone="01.42.17.56.78",
                configuration={
                    "delai_reponse_defaut": 7,
                    "analyse_ia_active": True
                }
            )
            session.add(org)
            session.flush()  # Pour obtenir l'ID
            
            # Créer des services
            services_data = [
                {
                    "nom": "Service de Cardiologie",
                    "code_service": "CARDIO",
                    "type_service": "CARDIOLOGIE",
                    "description": "Service spécialisé en cardiologie"
                },
                {
                    "nom": "Service des Urgences", 
                    "code_service": "URGENCES",
                    "type_service": "URGENCES",
                    "description": "Service d'accueil des urgences"
                },
                {
                    "nom": "Service de Pédiatrie",
                    "code_service": "PEDIAT",
                    "type_service": "PEDIATRIE", 
                    "description": "Service spécialisé en pédiatrie"
                }
            ]
            
            services = []
            for service_data in services_data:
                service = Service(
                    organisation_id=org.id,
                    **service_data
                )
                session.add(service)
                services.append(service)
            
            session.flush()  # Pour obtenir les IDs des services
            
            # Créer des utilisateurs
            users_data = [
                {
                    "nom": "Martin",
                    "prenom": "Jean",
                    "nom_complet": "Dr. Jean Martin",
                    "email": "j.martin@chu-principal.fr",
                    "telephone": "01.23.45.67.94",
                    "type_utilisateur": "MEDECIN",
                    "fonction": "Chef de service",
                    "specialite": "Cardiologie",
                    "service_id": services[0].id,
                    "permissions": ["TOUS_DROITS"]
                },
                {
                    "nom": "Dubois",
                    "prenom": "Sophie", 
                    "nom_complet": "Dr. Sophie Dubois",
                    "email": "s.dubois@chu-principal.fr",
                    "telephone": "01.23.45.67.95",
                    "type_utilisateur": "MEDECIN",
                    "fonction": "Médecin urgentiste",
                    "specialite": "Médecine d'urgence",
                    "service_id": services[1].id,
                    "permissions": ["CONSULTER_PLAINTES", "TRAITER_PLAINTES"]
                },
                {
                    "nom": "Admin",
                    "prenom": "Système",
                    "nom_complet": "Administrateur Système",
                    "email": "admin@chu-principal.fr",
                    "telephone": "01.23.45.67.00",
                    "type_utilisateur": "SUPER_ADMIN",
                    "fonction": "Administrateur système",
                    "permissions": ["TOUS_DROITS"]
                }
            ]
            
            for user_data in users_data:
                user = Utilisateur(
                    organisation_id=org.id,
                    **user_data
                )
                session.add(user)
            
            session.commit()
            logger.info("✅ Données d'exemple créées")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des données d'exemple: {e}")
        return False

# ==================== INITIALISATION ====================

if __name__ == "__main__":
    logger.info("🚀 Initialisation de la base de données unifiée")
    
    if initialize_database():
        if create_sample_data():
            logger.info("🎉 Base de données prête à l'emploi!")
            get_table_info()
        else:
            logger.error("❌ Échec de la création des données d'exemple")
    else:
        logger.error("❌ Échec de l'initialisation") 