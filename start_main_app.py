#!/usr/bin/env python3
"""
DÉMARRAGE APPLICATION PRINCIPALE - HealthCare AI
Script de démarrage pour l'application principale unifiée
Version: 1.0.0 - Architecture Organisée
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Vérifier les dépendances requises"""
    try:
        import fastapi
        import sqlalchemy
        import psycopg2
        logger.info("✅ Toutes les dépendances sont installées")
        return True
    except ImportError as e:
        logger.error(f"❌ Dépendance manquante: {e}")
        return False

def check_postgresql():
    """Vérifier que PostgreSQL est accessible"""
    try:
        from database_unified import test_connection
        if test_connection():
            logger.info("✅ PostgreSQL accessible")
            return True
        else:
            logger.error("❌ PostgreSQL inaccessible")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur PostgreSQL: {e}")
        return False

def initialize_database():
    """Initialiser la base de données"""
    try:
        from database_unified import initialize_database, create_sample_data
        
        logger.info("🔧 Initialisation de la base de données...")
        if initialize_database():
            logger.info("✅ Base de données initialisée")
            
            if create_sample_data():
                logger.info("✅ Données d'exemple créées")
            else:
                logger.warning("⚠️ Échec création données d'exemple")
            
            return True
        else:
            logger.error("❌ Échec initialisation base")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        return False

def start_main_app():
    """Démarrer l'application principale"""
    logger.info("🚀 Démarrage de HealthCare AI - Application Principale")
    
    # Vérifier les dépendances
    if not check_dependencies():
        logger.error("❌ Dépendances manquantes")
        return False
    
    # Vérifier PostgreSQL
    if not check_postgresql():
        logger.error("❌ PostgreSQL requis pour l'application")
        logger.info("💡 Veuillez démarrer PostgreSQL et réessayer")
        return False
    
    # Initialiser la base
    if not initialize_database():
        logger.error("❌ Impossible d'initialiser la base de données")
        return False
    
    # Démarrer le serveur
    logger.info("🌟 Lancement de l'application principale...")
    logger.info("📱 Page d'accueil: http://localhost:5000")
    logger.info("📚 Documentation: http://localhost:5000/docs")
    logger.info("🔍 Navigation: http://localhost:5000/navigation")
    
    try:
        uvicorn.run(
            "main_app:app",
            host="0.0.0.0",
            port=5000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt de l'application sur demande utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur serveur: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║        🏥 HealthCare AI - Application         ║
    ║              Principale                       ║
    ║                                               ║
    ║  ✅ API Unifiée                              ║
    ║  ✅ Organisation par Sections                ║
    ║  ✅ Navigation Intuitive                     ║
    ║  ✅ Documentation Complète                   ║
    ║  ✅ Interface Web Moderne                    ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    success = start_main_app()
    if not success:
        print("\n❌ Échec du démarrage")
        sys.exit(1)
    else:
        print("\n✅ Application démarrée avec succès") 