#!/usr/bin/env python3
"""
DÉMARRAGE WORKER SERVER - HealthCare AI Architecture ODYSSEE
Script pour démarrer le worker server Celery pour les analyses LLM
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_redis():
    """Vérifier si Redis est disponible"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("✅ Redis est disponible")
        return True
    except Exception as e:
        logger.error(f"❌ Redis non disponible: {e}")
        return False

def start_worker():
    """Démarrer le worker Celery"""
    try:
        # Vérifier Redis
        if not check_redis():
            logger.error("❌ Impossible de démarrer le worker: Redis non disponible")
            logger.info("💡 Démarrez Redis avec: redis-server")
            return False
        
        # Chemin vers le worker
        worker_path = Path(__file__).parent / "healthcare_worker_server"
        
        # Configuration Celery
        os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/1')
        os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
        
        # Ajouter le répertoire au PYTHONPATH
        current_dir = Path(__file__).parent
        python_path = os.environ.get('PYTHONPATH', '')
        if python_path:
            python_path = f"{current_dir};{python_path}"
        else:
            python_path = str(current_dir)
        os.environ['PYTHONPATH'] = python_path
        
        logger.info("🚀 Démarrage du worker server Celery...")
        logger.info(f"📁 Répertoire worker: {worker_path}")
        logger.info("🔗 Broker: redis://localhost:6379/1")
        logger.info("📊 Backend: redis://localhost:6379/2")
        logger.info(f"🐍 PYTHONPATH: {python_path}")
        
        # Commande pour démarrer le worker
        cmd = [
            sys.executable, "-m", "celery",
            "--app=healthcare_worker_server.app.core.celery_app:celery_app",
            "worker",
            "--loglevel=INFO",
            "--concurrency=2",
            "--queues=analyses,sentiment,classification",
            "--hostname=healthcare-worker@%h"
        ]
        
        logger.info(f"🔧 Commande: {' '.join(cmd)}")
        
        # Démarrer le worker (rester dans le répertoire parent)
        process = subprocess.Popen(
            cmd,
            cwd=Path(__file__).parent,  # Rester dans le répertoire parent
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("✅ Worker Celery démarré avec succès!")
        logger.info(f"🆔 PID: {process.pid}")
        
        # Attendre un peu pour voir les logs initiaux
        time.sleep(3)
        
        # Vérifier si le processus est toujours en cours
        if process.poll() is None:
            logger.info("🟢 Worker en cours d'exécution")
            return True
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ Worker arrêté prématurément")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage du worker: {e}")
        return False

def start_worker_with_monitoring():
    """Démarrer le worker avec monitoring"""
    try:
        logger.info("""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Worker Server          ║
    ║           Architecture ODYSSEE                ║
    ╚═══════════════════════════════════════════════╝
        """)
        
        if start_worker():
            logger.info("""
    💡 WORKER SERVER DÉMARRÉ
    =========================
    
    🔧 Fonctionnalités disponibles:
       - Analyse de sentiment des plaintes
       - Classification automatique
       - Détermination de priorité
       - Suggestions de services
       - Recommandations d'actions
    
    📊 Queues actives:
       - analyses: Analyses principales
       - sentiment: Analyses de sentiment
       - classification: Classification automatique
    
    🔌 Monitoring:
       - Logs en temps réel
       - Statut des tâches
       - Notifications WebSocket
    
    🛑 Pour arrêter: Ctrl+C
            """)
            
            # Garder le processus en vie
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt du worker server...")
                
        else:
            logger.error("❌ Échec du démarrage du worker")
            return False
            
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")

if __name__ == "__main__":
    start_worker_with_monitoring() 