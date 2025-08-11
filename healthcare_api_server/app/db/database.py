#!/usr/bin/env python3
"""
DATABASE - HealthCare AI Architecture ODYSSEE
Configuration base de données inspirée d'ODYSSEE avec PostgreSQL
Version: 1.0.0 - Architecture ODYSSEE
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import logging
import asyncio

from ..core.config import get_database_url, is_development

logger = logging.getLogger(__name__)

# Métadonnées avec convention de nommage (comme ODYSSEE)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Configuration du moteur de base de données
def create_database_engine():
    """Crée le moteur de base de données avec configuration optimisée"""
    database_url = get_database_url()
    
    # Configuration selon l'environnement
    engine_kwargs = {
        "echo": is_development(),  # Log SQL en développement
        "pool_pre_ping": True,     # Vérification des connexions
        "pool_recycle": 3600,      # Recyclage des connexions après 1h
    }
    
    # Configuration spécifique pour PostgreSQL
    if database_url.startswith("postgresql"):
        engine_kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
        })
    
    engine = create_engine(database_url, **engine_kwargs)
    logger.info(f"✅ Moteur de base de données créé: {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    return engine

# Instance globale du moteur
engine = create_database_engine()

# Configuration de la session (comme ODYSSEE)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Important pour les objets utilisés après commit
)

def get_db():
    """
    Dependency pour obtenir une session de base de données
    Inspiré du pattern ODYSSEE
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erreur de base de données: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """Crée toutes les tables (comme ODYSSEE startup)"""
    try:
        # Import des modèles pour les enregistrer
        import sys
        from pathlib import Path
        root_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(root_dir))
        from shared.models import Base as SharedBase
        
        # Crée toutes les tables
        SharedBase.metadata.create_all(bind=engine)
        logger.info("✅ Tables créées avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables: {e}")
        raise

def drop_tables():
    """Supprime toutes les tables (pour tests)"""
    try:
        import sys
        from pathlib import Path
        root_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(root_dir))
        from shared.models import Base as SharedBase
        
        SharedBase.metadata.drop_all(bind=engine)
        logger.info("✅ Tables supprimées avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression des tables: {e}")
        raise

async def init_database():
    """Initialise la base de données (comme ODYSSEE) - Version asynchrone"""
    logger.info("🚀 Initialisation de la base de données...")
    
    # Exécuter la création des tables dans un thread pool pour éviter le blocage
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, create_tables)
    
    # Ici on pourrait ajouter des données de test ou de configuration
    # comme dans ODYSSEE
    
    logger.info("✅ Base de données initialisée avec succès")

async def close_database():
    """Ferme proprement les connexions à la base de données"""
    logger.info("🛑 Fermeture des connexions à la base de données...")
    
    try:
        # Fermer le pool de connexions
        engine.dispose()
        logger.info("✅ Pool de connexions fermé")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fermeture de la base de données: {e}")

# Pour les tests
def get_test_db():
    """Session de test avec transaction rollback"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Moteur de test en mémoire
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine
    )
    
    # Crée les tables pour les tests
    import sys
    from pathlib import Path
    root_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(root_dir))
    from shared.models import Base as SharedBase
    SharedBase.metadata.create_all(bind=test_engine)
    
    return TestingSessionLocal()