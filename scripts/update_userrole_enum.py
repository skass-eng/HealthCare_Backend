#!/usr/bin/env python3
"""
Script pour mettre à jour l'enum UserRole dans PostgreSQL
Ajout des valeurs manquantes: SUPER_ADMIN, CHEF_SERVICE, TECHNICIEN, UTILISATEUR
Version: 1.0.0 - Architecture ODYSSEE
"""

import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine, text
from healthcare_api_server.app.core.config import settings

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def update_userrole_enum():
    """Mettre à jour l'enum UserRole dans PostgreSQL"""
    
    logger = logging.getLogger(__name__)
    
    # Créer la connexion à la base de données
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("🚀 Mise à jour de l'enum UserRole...")
            
            # Désactiver les contraintes de clés étrangères temporairement
            conn.execute(text("SET session_replication_role = replica;"))
            
            # Ajouter les nouvelles valeurs à l'enum
            logger.info("📝 Ajout des nouvelles valeurs à l'enum UserRole...")
            
            # Valeurs à ajouter
            new_values = [
                "SUPER_ADMIN",
                "CHEF_SERVICE", 
                "TECHNICIEN",
                "UTILISATEUR"
            ]
            
            for value in new_values:
                try:
                    conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{value}';"))
                    logger.info(f"✅ Ajouté: {value}")
                except Exception as e:
                    logger.warning(f"⚠️ Valeur {value} déjà présente ou erreur: {e}")
            
            # Réactiver les contraintes
            conn.execute(text("SET session_replication_role = DEFAULT;"))
            
            # Valider les changements
            conn.commit()
            
            logger.info("✅ Enum UserRole mis à jour avec succès!")
            
            # Vérifier les valeurs disponibles
            result = conn.execute(text("SELECT unnest(enum_range(NULL::userrole)) as values;"))
            values = [row[0] for row in result]
            logger.info(f"📊 Valeurs disponibles dans l'enum UserRole: {values}")
            
            return values
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour de l'enum: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

def main():
    """Fonction principale"""
    print("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Architecture ODYSSEE    ║
    ║           Mise à jour Enum UserRole           ║
    ║                                               ║
    ║  Ajout des valeurs manquantes à l'enum       ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Début de la mise à jour de l'enum UserRole")
        
        # Mettre à jour l'enum
        values = update_userrole_enum()
        
        logger.info("✅ Mise à jour terminée avec succès!")
        
        print("\n" + "="*50)
        print("📋 RÉSUMÉ DE LA MISE À JOUR")
        print("="*50)
        print(f"📊 Nombre total de valeurs: {len(values)}")
        print(f"📝 Valeurs disponibles: {', '.join(values)}")
        print("\n✅ L'enum UserRole est maintenant compatible avec toutes les valeurs!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 