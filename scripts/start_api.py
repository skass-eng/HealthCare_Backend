#!/usr/bin/env python3
"""
SCRIPT DE DÉMARRAGE API SERVER - HealthCare AI Architecture ODYSSEE
Démarrage du serveur API inspiré d'ODYSSEE
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import logging
import uvicorn
import signal
import asyncio
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from healthcare_api_server.app.core.config import settings

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/api_server.log', mode='a')
        ] if os.path.exists('logs') else [logging.StreamHandler(sys.stdout)]
    )

def check_dependencies():
    """Vérifier les dépendances critiques"""
    logger = logging.getLogger(__name__)
    
    # Vérifier PostgreSQL
    try:
        import psycopg2
        logger.info("[OK] PostgreSQL driver disponible")
    except ImportError:
        logger.error("[ERREUR] psycopg2-binary requis pour PostgreSQL")
        return False
    
    # Vérifier Redis
    try:
        import redis
        logger.info("[OK] Redis client disponible")
    except ImportError:
        logger.error("[ERREUR] redis requis pour Celery et WebSockets")
        return False
    
    # Vérifier FastAPI
    try:
        import fastapi
        logger.info("[OK] FastAPI disponible")
    except ImportError:
        logger.error("[ERREUR] fastapi requis")
        return False
    
    return True

def signal_handler(signum, frame):
    """Gestionnaire de signaux pour un arrêt propre"""
    logger = logging.getLogger(__name__)
    logger.info(f"[SIGNAL] Signal {signum} reçu, arrêt propre du serveur...")
    sys.exit(0)

def setup_signal_handlers():
    """Configuration des gestionnaires de signaux"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Sur Windows, gérer aussi SIGBREAK
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

def main():
    """Fonction principale de démarrage"""
    print("""
    =================================================
    HealthCare AI - Architecture ODYSSEE
                API Server
                                                
    Inspire de l'architecture ODYSSEE            
    FastAPI + SQLAlchemy + WebSockets            
    =================================================
    """)
    
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Configuration des gestionnaires de signaux
    setup_signal_handlers()
    
    # Vérifier les dépendances
    if not check_dependencies():
        logger.error("[ERREUR] Dépendances manquantes, arrêt du démarrage")
        sys.exit(1)
    
    # Afficher la configuration
    logger.info(f"[DEMARRAGE] API Server HealthCare AI")
    logger.info(f"[CONFIG] Host: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"[CONFIG] Database: {str(settings.DATABASE_URL).split('@')[1] if '@' in str(settings.DATABASE_URL) else 'PostgreSQL'}")
    logger.info(f"[CONFIG] Redis: {settings.REDIS_URL}")
    logger.info(f"[CONFIG] Environment: {settings.ENVIRONMENT}")
    logger.info(f"[CONFIG] Debug: {settings.DEBUG}")
    
    # Configuration Uvicorn avec gestion améliorée des signaux
    config = {
        "app": "healthcare_api_server.app.main:app",
        "host": settings.API_HOST,
        "port": settings.API_PORT,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
        "loop": "asyncio",  # Utiliser asyncio explicitement
        "workers": 1 if settings.DEBUG else 1,  # Réduire à 1 worker pour éviter les conflits
        "timeout_graceful_shutdown": 30,  # Donner 30 secondes pour l'arrêt propre
    }
    
    try:
        logger.info("[SUCCES] Serveur API démarré avec succès")
        
        # Utiliser uvicorn.run avec gestion d'erreurs améliorée
        uvicorn.run(**config)
        
    except KeyboardInterrupt:
        logger.info("[ARRET] Arrêt du serveur API demandé (Ctrl+C)")
        
    except SystemExit:
        logger.info("[ARRET] Arrêt du serveur API (SystemExit)")
        
    except Exception as e:
        logger.error(f"[ERREUR] Erreur fatale: {e}")
        sys.exit(1)
        
    finally:
        logger.info("[ARRET] Serveur API arrêté proprement")

if __name__ == "__main__":
    main()