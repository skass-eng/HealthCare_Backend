#!/usr/bin/env python3
"""
GESTIONNAIRE DE TÂCHES - HealthCare AI Architecture ODYSSEE
Interface entre l'API et les Workers Celery (inspiré d'ODYSSEE)
Version: 1.0.0 - Architecture ODYSSEE
"""

from celery import Celery
from celery.result import AsyncResult
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging

from ..core.config import settings
from shared.schemas import TaskStatus, AnalyseTaskRequest

logger = logging.getLogger(__name__)

# Configuration Celery (comme ODYSSEE worker system)
celery_app = Celery(
    "healthcare_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'healthcare_worker_server.tasks.analyse_plainte',
        'healthcare_worker_server.tasks.sentiment',
        'healthcare_worker_server.tasks.classification',
        'healthcare_worker_server.tasks.generate_pdf'
    ]
)

# Configuration des routes de tâches (comme ODYSSEE)
celery_app.conf.update(
    task_routes=settings.CELERY_TASK_ROUTES,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max par tâche
    task_soft_time_limit=25 * 60,  # Soft limit à 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

async def trigger_analyse_plainte(
    plainte_id: UUID,
    types_analyse: List[str],
    user_id: UUID,
    parametres: Dict[str, Any] = None
) -> str:
    """
    Déclencher une analyse de plainte (comme déclencher un widget ODYSSEE)
    """
    try:
        task_data = {
            "plainte_id": str(plainte_id),
            "types_analyse": types_analyse,
            "user_id": str(user_id),
            "parametres": parametres or {}
        }
        
        # Déclencher la tâche Celery principale
        result = celery_app.send_task(
            'healthcare_worker_server.tasks.analyse_plainte.process_plainte_analysis',
            args=[task_data],
            queue='analyses'
        )
        
        logger.info(f"✅ Tâche d'analyse déclenchée: {result.id} pour plainte {plainte_id}")
        return result.id
        
    except Exception as e:
        logger.error(f"❌ Erreur déclenchement analyse: {e}")
        raise

async def get_task_status(task_id: str) -> TaskStatus:
    """
    Récupérer le statut d'une tâche Celery (comme ODYSSEE task monitoring)
    """
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        status_mapping = {
            'PENDING': 'En attente',
            'STARTED': 'En cours',
            'SUCCESS': 'Terminé',
            'FAILURE': 'Échec',
            'RETRY': 'Nouvelle tentative',
            'REVOKED': 'Annulé'
        }
        
        task_status = TaskStatus(
            task_id=task_id,
            status=status_mapping.get(result.state, result.state),
            result=result.result if result.state == 'SUCCESS' else None,
            error_message=str(result.result) if result.state == 'FAILURE' else None,
            progress=None  # À implémenter si nécessaire
        )
        
        return task_status
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération statut tâche: {e}")
        return TaskStatus(
            task_id=task_id,
            status="Erreur",
            error_message=str(e)
        )

async def cancel_task(task_id: str) -> bool:
    """
    Annuler une tâche Celery
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"✅ Tâche annulée: {task_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur annulation tâche: {e}")
        return False

async def retry_task(task_id: str) -> str:
    """
    Relancer une tâche échouée
    """
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state != 'FAILURE':
            raise ValueError(f"La tâche {task_id} n'est pas en échec")
        
        # Récupérer les arguments originaux et relancer
        task_info = result.info
        if task_info and 'args' in task_info:
            new_result = celery_app.send_task(
                result.task_name,
                args=task_info['args'],
                kwargs=task_info.get('kwargs', {}),
                queue='analyses'
            )
            
            logger.info(f"✅ Tâche relancée: {new_result.id} (originale: {task_id})")
            return new_result.id
        
        raise ValueError("Impossible de récupérer les arguments de la tâche")
        
    except Exception as e:
        logger.error(f"❌ Erreur relance tâche: {e}")
        raise

async def get_active_tasks() -> List[Dict[str, Any]]:
    """
    Récupérer la liste des tâches actives (comme ODYSSEE task monitoring)
    """
    try:
        inspect = celery_app.control.inspect()
        
        active_tasks = []
        
        # Récupérer les tâches actives
        active = inspect.active()
        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    active_tasks.append({
                        "task_id": task["id"],
                        "name": task["name"],
                        "worker": worker,
                        "args": task.get("args", []),
                        "kwargs": task.get("kwargs", {}),
                        "time_start": task.get("time_start")
                    })
        
        return active_tasks
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération tâches actives: {e}")
        return []

async def get_worker_stats() -> Dict[str, Any]:
    """
    Récupérer les statistiques des workers (comme ODYSSEE monitoring)
    """
    try:
        inspect = celery_app.control.inspect()
        
        stats = {
            "workers_active": 0,
            "tasks_active": 0,
            "queues": {}
        }
        
        # Statistiques des workers
        active = inspect.active()
        if active:
            stats["workers_active"] = len(active)
            for worker, tasks in active.items():
                stats["tasks_active"] += len(tasks)
        
        # Statistiques des queues
        reserved = inspect.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    queue_name = task.get("delivery_info", {}).get("routing_key", "default")
                    if queue_name not in stats["queues"]:
                        stats["queues"][queue_name] = 0
                    stats["queues"][queue_name] += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération stats workers: {e}")
        return {"error": str(e)}

# Tâches de maintenance

async def cleanup_old_tasks(days: int = 7) -> int:
    """
    Nettoyer les anciennes tâches terminées (comme ODYSSEE cleanup)
    """
    try:
        # Cette fonction dépendrait de la configuration du backend Celery
        # Pour Redis, on pourrait implémenter un nettoyage personnalisé
        logger.info(f"🧹 Nettoyage des tâches de plus de {days} jours")
        
        # Implémentation spécifique selon le backend
        # return nombre_taches_supprimees
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage tâches: {e}")
        return 0

async def ping_workers() -> Dict[str, bool]:
    """
    Vérifier la disponibilité des workers
    """
    try:
        inspect = celery_app.control.inspect()
        ping_result = inspect.ping()
        
        if ping_result:
            return {worker: True for worker in ping_result.keys()}
        else:
            return {}
            
    except Exception as e:
        logger.error(f"❌ Erreur ping workers: {e}")
        return {}

# Fonctions spécialisées pour les analyses

async def trigger_sentiment_analysis(plainte_id: UUID, user_id: UUID) -> str:
    """Déclencher une analyse de sentiment spécifique"""
    return await trigger_analyse_plainte(
        plainte_id=plainte_id,
        types_analyse=["sentiment"],
        user_id=user_id
    )

async def trigger_classification_analysis(plainte_id: UUID, user_id: UUID) -> str:
    """Déclencher une classification automatique"""
    return await trigger_analyse_plainte(
        plainte_id=plainte_id,
        types_analyse=["classification"],
        user_id=user_id
    )

async def trigger_priority_analysis(plainte_id: UUID, user_id: UUID) -> str:
    """Déclencher une analyse de priorité"""
    return await trigger_analyse_plainte(
        plainte_id=plainte_id,
        types_analyse=["priorite"],
        user_id=user_id
    )

async def trigger_full_analysis(plainte_id: UUID, user_id: UUID) -> str:
    """Déclencher une analyse complète (tous types)"""
    return await trigger_analyse_plainte(
        plainte_id=plainte_id,
        types_analyse=["sentiment", "classification", "priorite", "service_suggestion"],
        user_id=user_id
    )

# ==================== FONCTIONS DE GÉNÉRATION PDF ====================

async def trigger_pdf_generation(plainte_id: UUID) -> str:
    """Déclencher la génération du PDF d'archivage"""
    try:
        result = celery_app.send_task(
            'healthcare_worker_server.tasks.generate_pdf.generate_plainte_pdf',
            args=[plainte_id],
            queue='pdf_generation'
        )
        
        logger.info(f"✅ Tâche de génération PDF déclenchée: {result.id} pour plainte {plainte_id}")
        return result.id
        
    except Exception as e:
        logger.error(f"❌ Erreur déclenchement génération PDF: {e}")
        raise

async def trigger_response_pdf_generation(plainte_id: UUID, response_text: str) -> str:
    """Déclencher la génération du PDF de réponse"""
    try:
        result = celery_app.send_task(
            'healthcare_worker_server.tasks.generate_pdf.generate_response_pdf',
            args=[plainte_id, response_text],
            queue='pdf_generation'
        )
        
        logger.info(f"✅ Tâche de génération PDF de réponse déclenchée: {result.id} pour plainte {plainte_id}")
        return result.id
        
    except Exception as e:
        logger.error(f"❌ Erreur déclenchement génération PDF de réponse: {e}")
        raise