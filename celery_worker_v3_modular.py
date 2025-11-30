"""
Worker Celery modulaire - Version 3
Utilise l'architecture modulaire avec services séparés
"""
import logging
import os
import sys
from datetime import datetime

# Configuration du logging sans emojis pour Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/worker_modular.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire des tâches au path
current_dir = os.path.dirname(os.path.abspath(__file__))
tasks_dir = os.path.join(current_dir, 'healthcare_worker_server', 'app', 'tasks')
sys.path.append(current_dir)
sys.path.append(tasks_dir)

try:
    # Import des tâches modulaires
    from healthcare_worker_server.app.tasks.celery_tasks import app
    
    logger.info("Import des taches modulaires reussi")
    
    # Configuration supplémentaire
    app.conf.update(
        task_track_started=True,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Europe/Paris',
        enable_utc=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )
    
    logger.info("Configuration Celery mise a jour")
    
except ImportError as e:
    logger.error(f"Erreur d'import des taches: {str(e)}")
    sys.exit(1)

def main():
    """Point d'entrée principal du worker"""
    logger.info("Demarrage du worker Celery modulaire v3")
    logger.info("Taches disponibles:")
    
    # Lister les tâches disponibles
    for task_name in app.tasks.keys():
        if not task_name.startswith('celery.'):
            logger.info(f"  • {task_name}")
    
    logger.info("Worker en attente de taches...")
    logger.info("Broker: Redis (db=1)")
    logger.info("Backend: Redis (db=2)")
    
    try:
        # Démarrer le worker
        app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--pool=prefork'
        ])
    except KeyboardInterrupt:
        logger.info("Arret du worker demande par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale du worker: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
