#!/usr/bin/env python3
"""
SCRIPT DE CORRECTION AUTH - HealthCare AI Architecture ODYSSEE
Correction du problème d'enum pour l'authentification
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from healthcare_api_server.app.db.database import get_db
from shared.models import User, Organisation
from healthcare_api_server.app.core.auth import get_password_hash

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_test_users(db):
    """Créer des utilisateurs de test avec des valeurs d'enum compatibles"""
    logger = logging.getLogger(__name__)
    
    # Vérifier si des utilisateurs existent déjà
    existing_users = db.query(User).count()
    if existing_users > 0:
        logger.info(f"✅ {existing_users} utilisateurs existent déjà")
        return
    
    # Récupérer l'organisation par défaut
    organisation = db.query(Organisation).first()
    if not organisation:
        logger.error("❌ Aucune organisation trouvée. Exécutez d'abord init_db.py")
        return
    
    # Créer des utilisateurs de test avec des valeurs simples
    test_users = [
        {
            "email": "admin@test.com",
            "nom": "Admin",
            "prenom": "Test",
            "nom_complet": "Administrateur Test",
            "type_utilisateur": "ADMIN",  # Valeur simple
            "password": "admin123"
        },
        {
            "email": "user@test.com",
            "nom": "User",
            "prenom": "Test",
            "nom_complet": "Utilisateur Test",
            "type_utilisateur": "UTILISATEUR",  # Valeur simple
            "password": "user123"
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(
            User.email == user_data["email"]
        ).first()
        
        if existing_user:
            logger.info(f"✅ Utilisateur existant: {existing_user.email}")
            created_users.append(existing_user)
            continue
        
        # Créer le nouvel utilisateur
        user = User(
            email=user_data["email"],
            nom=user_data["nom"],
            prenom=user_data["prenom"],
            nom_complet=user_data["nom_complet"],
            type_utilisateur=user_data["type_utilisateur"],  # Utiliser la valeur string
            mot_de_passe_hash=get_password_hash(user_data["password"]),
            organisation_id=organisation.id,
            est_actif=True,
            email_verifie=True,
            configuration={
                "notifications_email": True,
                "langue_preferee": "fr",
                "theme": "light",
                "demo_account": True
            }
        )
        
        db.add(user)
        created_users.append(user)
        logger.info(f"✅ Utilisateur créé: {user.email} (mot de passe: {user_data['password']})")
    
    db.commit()
    return created_users

def main():
    """Fonction principale"""
    print("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Correction Auth        ║
    ║           Architecture ODYSSEE                ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Début de la correction de l'authentification")
        
        # Récupérer une session de base de données
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Créer les utilisateurs de test
            logger.info("👥 Création des utilisateurs de test...")
            users = create_test_users(db)
            
            if users:
                logger.info("✅ Correction terminée avec succès!")
                
                print("\n" + "="*50)
                print("🔑 UTILISATEURS DE TEST CRÉÉS")
                print("="*50)
                for user in users:
                    print(f"📧 {user.email}")
                    print(f"   Mot de passe: {user.nom_complet.split()[0].lower()}123")
                    print(f"   Rôle: {user.type_utilisateur}")
                    print()
                
                print("🌐 TEST DE L'AUTHENTIFICATION:")
                print("-" * 30)
                print("curl -X POST 'http://localhost:8000/auth/login' \\")
                print("  -H 'Content-Type: application/x-www-form-urlencoded' \\")
                print("  -d 'username=admin@test.com&password=admin123'")
                print("\n✅ Authentification prête à être testée!")
            else:
                logger.info("ℹ️ Aucun utilisateur créé (déjà existants)")
                
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de la correction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 