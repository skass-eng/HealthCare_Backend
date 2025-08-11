#!/usr/bin/env python3
"""
SCRIPT DE VÉRIFICATION USERS - HealthCare AI Architecture ODYSSEE
Vérifier les utilisateurs existants dans la base de données
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from healthcare_api_server.app.db.database import get_db
from shared.models import User

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def check_users(db):
    """Vérifier les utilisateurs existants"""
    logger = logging.getLogger(__name__)
    
    users = db.query(User).all()
    
    print(f"\n📋 UTILISATEURS EXISTANTS ({len(users)})")
    print("=" * 50)
    
    for user in users:
        print(f"📧 Email: {user.email}")
        print(f"   Nom: {user.nom_complet}")
        print(f"   Rôle: {user.type_utilisateur}")
        print(f"   Actif: {user.est_actif}")
        print(f"   Hash: {user.mot_de_passe_hash[:20]}..." if user.mot_de_passe_hash else "   Hash: None")
        print()

def main():
    """Fonction principale"""
    print("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Vérification Users     ║
    ║           Architecture ODYSSEE                ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Début de la vérification des utilisateurs")
        
        # Récupérer une session de base de données
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            check_users(db)
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 