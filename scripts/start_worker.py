#!/usr/bin/env python3
"""
SCRIPT DE DÉMARRAGE WORKER SERVER - HealthCare AI Architecture ODYSSEE
Démarrage des workers Celery inspiré d'ODYSSEE
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/worker_server.log', mode='a')
        ] if os.path.exists('logs') else [logging.StreamHandler(sys.stdout)]
    )

def check_dependencies():
    """Vérifier les dépendances critiques"""
    logger = logging.getLogger(__name__)
    
    # Vérifier Celery
    try:
        import celery
        logger.info("[OK] Celery disponible")
    except ImportError:
        logger.error("[ERREUR] celery requis pour les workers")
        return False
    
    # Vérifier Redis
    try:
        import redis
        client = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"))
        client.ping()
        logger.info("[OK] Redis accessible")
    except Exception as e:
        logger.error(f"[ERREUR] Redis inaccessible: {e}")
        return False
    
    # Vérifier les services LLM
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    if llm_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        logger.warning("[WARN] OPENAI_API_KEY non configurée")
    elif llm_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("[WARN] ANTHROPIC_API_KEY non configurée")
    
    return True

def start_worker(worker_type="standard", queues=None, concurrency=2):
    """Démarrer un worker Celery spécifique"""
    logger = logging.getLogger(__name__)
    
    if queues is None:
        queues = ["analyses", "sentiment", "classification"]
    
    # Commande Celery
    cmd = [
        "celery", "-A", "healthcare_worker_server.app.core.celery_app",
        "worker",
        "--loglevel=info",
        f"--queues={','.join(queues)}",
        f"--concurrency={concurrency}",
        f"--hostname={worker_type}@%h",
        "--pool=prefork",  # ou threads pour I/O intensif
        "--without-gossip",
        "--without-mingle",
        "--without-heartbeat"
    ]
    
    logger.info(f"[DEMARRAGE] Worker {worker_type} avec queues: {queues}")
    logger.info(f"[COMMANDE] {' '.join(cmd)}")
    
    try:
        # Changer le répertoire de travail
        os.chdir(root_dir)
        
        # Démarrer le worker
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERREUR] Erreur démarrage worker: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("[ARRET] Arrêt du worker demandé")
        return True

def main():
    """Fonction principale"""
    print("""
    =================================================
    HealthCare AI - Architecture ODYSSEE
              Worker Server
                                                
    Workers Celery pour analyses LLM             
    Inspire de l'architecture ODYSSEE            
    =================================================
    """)
    
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Vérifier les dépendances
    if not check_dependencies():
        logger.error("[ERREUR] Dépendances manquantes, arrêt du démarrage")
        sys.exit(1)
    
    # Afficher la configuration
    logger.info("[DEMARRAGE] Workers HealthCare AI")
    logger.info(f"[CONFIG] Broker: {os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')}")
    logger.info(f"[CONFIG] Backend: {os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')}")
    logger.info(f"[CONFIG] LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    logger.info(f"[CONFIG] Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Déterminer le type de worker à démarrer
    worker_type = sys.argv[1] if len(sys.argv) > 1 else "standard"
    
    if worker_type == "all":
        logger.info("[DEMARRAGE] Démarrage de tous les types de workers...")
        # Ici on pourrait démarrer plusieurs workers en parallèle
        # Pour la simplicité, on démarre un worker standard
        worker_type = "standard"
    
    # Configuration selon le type de worker
    if worker_type == "analyses":
        queues = ["analyses"]
        concurrency = 2
    elif worker_type == "sentiment":
        queues = ["sentiment"]
        concurrency = 4  # Plus rapide
    elif worker_type == "classification":
        queues = ["classification"]
        concurrency = 3
    else:  # standard
        queues = ["analyses", "sentiment", "classification"]
        concurrency = 2
    
    # Démarrer le worker
    try:
        logger.info(f"[SUCCES] Worker {worker_type} démarré avec succès")
        success = start_worker(worker_type, queues, concurrency)
        
        if not success:
            logger.error("[ERREUR] Échec du démarrage du worker")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("[ARRET] Arrêt des workers demandé")
        
    except Exception as e:
        logger.error(f"[ERREUR] Erreur fatale: {e}")
        sys.exit(1)
        
    finally:
        logger.info("[ARRET] Workers arrêtés")

if __name__ == "__main__":
    main()