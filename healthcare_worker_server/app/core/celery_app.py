#!/usr/bin/env python3
"""
CELERY APP - HealthCare AI Architecture ODYSSEE
Configuration Celery pour les Workers d'analyses LLM (inspiré d'ODYSSEE)
Version: 1.0.0 - Architecture ODYSSEE
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import logging
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Celery (inspirée d'ODYSSEE worker_server)
def create_celery_app():
    """
    Créer l'application Celery (comme ODYSSEE)
    """
    
    # Configuration depuis les variables d'environnement
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Création de l'app Celery
    celery_app = Celery(
        "healthcare_worker_server",
        broker=broker_url,
        backend=result_backend,
        include=[
            'healthcare_worker_server.app.tasks.analyse_plainte',
            'healthcare_worker_server.app.tasks.sentiment',
            'healthcare_worker_server.app.tasks.classification'
        ]
    )
    
    # Configuration (inspirée d'ODYSSEE)
    celery_app.conf.update(
        # Sérialisation
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        
        # Timezone
        timezone='UTC',
        enable_utc=True,
        
        # Task tracking
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        
        # Timeouts (importantes pour les analyses LLM)
        task_time_limit=30 * 60,      # 30 minutes max
        task_soft_time_limit=25 * 60, # 25 minutes soft limit
        
        # Worker configuration
        worker_max_tasks_per_child=100,
        worker_disable_rate_limits=False,
        
        # Retry configuration
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,
        
        # Routes des tâches (comme ODYSSEE)
        task_routes={
            'healthcare_worker_server.app.tasks.analyse_plainte.*': {
                'queue': 'analyses'
            },
            'healthcare_worker_server.app.tasks.sentiment.*': {
                'queue': 'sentiment'
            },
            'healthcare_worker_server.app.tasks.classification.*': {
                'queue': 'classification'
            },
        },
        
        # Résultats
        result_expires=3600,  # 1 heure
        result_persistent=True,
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Sécurité
        worker_hijack_root_logger=False,
        worker_log_color=False,
    )
    
    return celery_app

# Instance globale Celery
celery_app = create_celery_app()

# Signaux Celery (comme ODYSSEE monitoring)

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """
    Signal déclenché quand un worker est prêt
    """
    logger.info("🟢 Worker Celery prêt - HealthCare AI Architecture ODYSSEE")
    logger.info(f"Worker ID: {sender}")
    
    # Ici on pourrait ajouter des initialisations spécifiques
    # comme la vérification des modèles LLM, etc.

@worker_shutdown.connect  
def worker_shutdown_handler(sender=None, **kwargs):
    """
    Signal déclenché à l'arrêt d'un worker
    """
    logger.info("🔴 Arrêt du Worker Celery - HealthCare AI")
    logger.info(f"Worker ID: {sender}")

# Configuration des queues
CELERY_QUEUES = {
    'analyses': {
        'description': 'Queue principale pour toutes les analyses de plaintes',
        'routing_key': 'analyses',
        'priority': 10
    },
    'sentiment': {
        'description': 'Queue spécialisée pour les analyses de sentiment',
        'routing_key': 'sentiment', 
        'priority': 8
    },
    'classification': {
        'description': 'Queue pour la classification automatique',
        'routing_key': 'classification',
        'priority': 6
    },
    'priority_analysis': {
        'description': 'Queue pour les analyses de priorité urgente',
        'routing_key': 'priority_analysis',
        'priority': 15
    }
}

# Décorateur pour les tâches avec retry automatique
def healthcare_task(name=None, **kwargs):
    """
    Décorateur personnalisé pour les tâches HealthCare (inspiré d'ODYSSEE)
    """
    def decorator(func):
        # Configuration par défaut pour les tâches HealthCare
        task_kwargs = {
            'bind': True,
            'autoretry_for': (Exception,),
            'retry_kwargs': {'max_retries': 3, 'countdown': 60},
            'retry_backoff': True,
            'retry_jitter': True,
            **kwargs
        }
        
        if name:
            task_kwargs['name'] = name
            
        return celery_app.task(**task_kwargs)(func)
    
    return decorator

# Configuration spécifique pour l'environnement
def configure_for_environment(environment: str = "development"):
    """
    Configurer Celery selon l'environnement (comme ODYSSEE)
    """
    if environment == "development":
        celery_app.conf.update(
            task_always_eager=False,  # False pour tester les tâches async
            task_eager_propagates=True,
            worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
            worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
        )
    elif environment == "production":
        celery_app.conf.update(
            worker_log_format='%(message)s',
            worker_task_log_format='[%(task_name)s(%(task_id)s)] %(message)s',
            worker_redirect_stdouts_level='INFO',
        )
    elif environment == "test":
        celery_app.conf.update(
            task_always_eager=True,  # Exécution synchrone pour les tests
            task_eager_propagates=True,
        )

# Fonction d'inspection des workers (comme ODYSSEE monitoring)
def get_worker_status():
    """
    Récupérer le statut des workers actifs
    """
    try:
        inspect = celery_app.control.inspect()
        
        stats = {
            'active_workers': 0,
            'active_tasks': 0,
            'available_workers': [],
            'queues': {}
        }
        
        # Workers actifs
        active = inspect.active()
        if active:
            stats['active_workers'] = len(active)
            stats['available_workers'] = list(active.keys())
            
            # Compter les tâches actives
            for worker, tasks in active.items():
                stats['active_tasks'] += len(tasks)
        
        # Statistiques des queues
        reserved = inspect.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    stats['queues'][queue] = stats['queues'].get(queue, 0) + 1
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération statut workers: {e}")
        return {'error': str(e)}

# Auto-découverte des tâches
if __name__ == "__main__":
    celery_app.start()