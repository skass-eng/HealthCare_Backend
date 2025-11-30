"""
Script de démarrage pour le worker Celery modulaire
"""
import os
import sys
import subprocess
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_modular_worker():
    """Démarre le worker modulaire"""
    logger.info("🚀 Démarrage du worker Celery modulaire...")
    
    try:
        # Vérifier que Redis est accessible
        logger.info("📡 Vérification de la connexion Redis...")
        
        # Démarrer le worker
        logger.info("🔄 Lancement du worker...")
        python_path = sys.executable
        worker_script = "celery_worker_v3_modular.py"
        
        cmd = [python_path, worker_script]
        logger.info(f"Commande: {' '.join(cmd)}")
        
        # Exécuter le worker
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur lors du démarrage du worker: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt du worker demandé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    start_modular_worker()
