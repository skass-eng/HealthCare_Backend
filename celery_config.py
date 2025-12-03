"""
Configuration Celery pour l'architecture modulaire
"""

# Configuration Redis
broker_url = 'redis://localhost:6379/1'
result_backend = 'redis://localhost:6379/2'

# Configuration de connexion au broker
broker_connection_retry_on_startup = True

# Configuration des tâches
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Paris'
enable_utc = True

# Configuration du worker
worker_prefetch_multiplier = 1
task_acks_late = True
task_track_started = True

# Import des tâches
imports = [
    'healthcare_worker_server.app.tasks.celery_tasks',
]

# Configuration des résultats
result_expires = 3600
task_result_expires = 3600

# Configuration des logs
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
