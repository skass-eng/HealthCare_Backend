#!/usr/bin/env python3
"""
Script de démarrage rapide - HealthCare AI Architecture ODYSSEE
Exécute la migration de l'enum et l'initialisation de la base de données
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_migration():
    """Exécuter la migration de l'enum UserRole"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 Exécution de la migration de l'enum UserRole...")
        
        # Importer et exécuter le script de migration
        from scripts.update_userrole_enum import update_userrole_enum
        values = update_userrole_enum()
        
        logger.info("✅ Migration terminée avec succès!")
        return values
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise

def run_initialization():
    """Exécuter l'initialisation de la base de données"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 Exécution de l'initialisation de la base de données...")
        
        # Importer et exécuter le script d'initialisation
        from scripts.init_db import main as init_main
        init_main()
        
        logger.info("✅ Initialisation terminée avec succès!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        raise

def main():
    """Fonction principale de démarrage rapide"""
    print("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Architecture ODYSSEE    ║
    ║           Démarrage Rapide Database           ║
    ║                                               ║
    ║  Migration + Initialisation complète         ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Début du démarrage rapide de la base de données")
        
        # Étape 1: Migration de l'enum
        print("\n" + "="*50)
        print("🔄 ÉTAPE 1: MIGRATION DE L'ENUM USEROLE")
        print("="*50)
        values = run_migration()
        
        # Étape 2: Initialisation de la base de données
        print("\n" + "="*50)
        print("🔄 ÉTAPE 2: INITIALISATION DE LA BASE DE DONNÉES")
        print("="*50)
        run_initialization()
        
        logger.info("✅ Démarrage rapide terminé avec succès!")
        
        print("\n" + "="*50)
        print("🎉 DÉMARRAGE RAPIDE TERMINÉ!")
        print("="*50)
        print("📊 Enum UserRole mis à jour avec les valeurs:")
        print(f"   {', '.join(values)}")
        print("\n🌐 L'application est prête à être utilisée!")
        print("📚 Documentation: http://localhost:8000/docs")
        print("🔍 Health Check: http://localhost:8000/health")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage rapide: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 