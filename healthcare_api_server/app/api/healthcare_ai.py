#!/usr/bin/env python3
"""
API HEALTHCARE AI - Architecture ODYSSEE
Endpoints pour les statistiques et métriques de la page healthcare-ai
Version: 2.0.0 - Architecture ODYSSEE avec Analyse IA Avancée (Ollama)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import logging
import json
import httpx
import asyncio
import uuid
import redis

from ..db.database import get_db
from shared.models import Plainte, StatutPlainte, Service, AIAnalysisResult
from shared.schemas import SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healthcare-ai", tags=["Healthcare AI"])

# Configuration Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"  # Modèle disponible localement

# Configuration Redis pour les tâches async
REDIS_URL = "redis://localhost:6379/0"

# Stockage en mémoire des tâches d'analyse (pour simplifier, sinon utiliser Redis)
_analysis_tasks: Dict[str, Dict[str, Any]] = {}

def get_redis_client():
    """Obtenir un client Redis"""
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Erreur connexion Redis: {e}")
        return None

def publish_task_event(event_type: str, data: Dict[str, Any]):
    """Publier un événement de tâche via Redis (canal websocket_notifications)"""
    try:
        r = get_redis_client()
        if r:
            message = json.dumps({
                "event": event_type,
                "data": data
            })
            # Utiliser le même canal que le listener Redis du main.py
            r.publish("websocket_notifications", message)
            logger.info(f"📤 Événement publié: {event_type} -> websocket_notifications")
    except Exception as e:
        logger.error(f"Erreur publication Redis: {e}")

@router.get("/complaints/summary")
async def get_complaints_summary(
    from_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    db: Session = Depends(get_db)
):
    """
    Récupère le résumé des plaintes pour la page healthcare-ai
    Retourne les 4 métriques principales selon l'architecture ODYSSEE
    """
    try:
        logger.info("🔍 Récupération des statistiques des plaintes")
        
        # Query de base
        base_query = db.query(Plainte)
        
        # Filtres de date
        if from_date:
            try:
                start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
                base_query = base_query.filter(func.date(Plainte.date_creation) >= start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour from_date (YYYY-MM-DD)")
        
        if to_date:
            try:
                end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
                base_query = base_query.filter(func.date(Plainte.date_creation) <= end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide pour to_date (YYYY-MM-DD)")
        
        # Filtre par statut
        if status:
            try:
                statut_enum = StatutPlainte(status.upper())
                base_query = base_query.filter(Plainte.statut == statut_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
        
        # 1. Nombre total de plaintes
        total = base_query.count()
        
        # 2. Nombre de plaintes en cours
        in_progress = base_query.filter(Plainte.statut == StatutPlainte.EN_COURS).count()
        
        # 3. Nombre de plaintes résolues (traitées + clôturées)
        resolved = base_query.filter(
            Plainte.statut.in_([StatutPlainte.TRAITE, StatutPlainte.CLOTURE])
        ).count()
        
        # 4. Temps moyen de résolution (en secondes)
        avg_resolution_time_seconds = 0.0
        
        # Query pour calculer le temps moyen de résolution
        resolved_complaints = base_query.filter(
            and_(
                Plainte.statut.in_([StatutPlainte.TRAITE, StatutPlainte.CLOTURE]),
                Plainte.date_resolution.isnot(None)
            )
        ).all()
        
        if resolved_complaints:
            total_resolution_time = 0
            count = 0
            
            for plainte in resolved_complaints:
                if plainte.date_resolution and plainte.date_creation:
                    resolution_time = (plainte.date_resolution - plainte.date_creation).total_seconds()
                    total_resolution_time += resolution_time
                    count += 1
            
            if count > 0:
                avg_resolution_time_seconds = total_resolution_time / count
        
        # Métriques supplémentaires pour le contexte
        nouvelles = base_query.filter(Plainte.statut == StatutPlainte.RECU).count()
        
        # Log des résultats
        logger.info(f"📊 Statistiques calculées - Total: {total}, En cours: {in_progress}, Résolues: {resolved}, Temps moyen: {avg_resolution_time_seconds:.2f}s")
        
        response_data = {
            "total": total,
            "in_progress": in_progress,
            "resolved": resolved,
            "avg_resolution_time_seconds": round(avg_resolution_time_seconds, 2),
            # Métriques additionnelles
            "nouvelles": nouvelles,
            "filters_applied": {
                "from_date": from_date,
                "to_date": to_date,
                "status": status
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": response_data,
            "message": "Statistiques récupérées avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du calcul des statistiques: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur interne lors du calcul des statistiques: {str(e)}"
        )

@router.get("/complaints/trends")
async def get_complaints_trends(
    days: int = Query(30, ge=1, le=365, description="Nombre de jours pour les tendances"),
    db: Session = Depends(get_db)
):
    """
    Récupère les tendances des plaintes sur une période donnée
    Pour des graphiques et analytics avancés
    """
    try:
        logger.info(f"📈 Récupération des tendances sur {days} jours")
        
        # Calculer la date de début
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Query de base avec filtre de date
        base_query = db.query(Plainte).filter(
            func.date(Plainte.date_creation) >= start_date,
            func.date(Plainte.date_creation) <= end_date
        )
        
        # Grouper par jour et statut
        daily_stats = db.query(
            func.date(Plainte.date_creation).label('date'),
            Plainte.statut,
            func.count(Plainte.id).label('count')
        ).filter(
            func.date(Plainte.date_creation) >= start_date,
            func.date(Plainte.date_creation) <= end_date
        )
        
        daily_stats = daily_stats.group_by(
            func.date(Plainte.date_creation),
            Plainte.statut
        ).order_by(func.date(Plainte.date_creation)).all()
        
        # Organiser les données par date
        trends = {}
        for stat in daily_stats:
            date_str = stat.date.isoformat()
            if date_str not in trends:
                trends[date_str] = {
                    "date": date_str,
                    "total": 0,
                    "recu": 0,
                    "en_cours": 0,
                    "traite": 0,
                    "cloture": 0
                }
            
            trends[date_str]["total"] += stat.count
            
            if stat.statut == StatutPlainte.RECU:
                trends[date_str]["recu"] = stat.count
            elif stat.statut == StatutPlainte.EN_COURS:
                trends[date_str]["en_cours"] = stat.count
            elif stat.statut == StatutPlainte.TRAITE:
                trends[date_str]["traite"] = stat.count
            elif stat.statut == StatutPlainte.CLOTURE:
                trends[date_str]["cloture"] = stat.count
        
        # Convertir en liste triée
        trends_list = list(trends.values())
        trends_list.sort(key=lambda x: x["date"])
        
        response_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "trends": trends_list,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": response_data,
            "message": f"Tendances récupérées pour {days} jours"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du calcul des tendances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du calcul des tendances: {str(e)}"
        )


# ==================== ANALYSE IA AVANCÉE AVEC OLLAMA ====================

async def call_ollama(prompt: str, system_prompt: str = None) -> str:
    """
    Appelle Ollama pour générer une réponse IA
    """
    try:
        logger.info(f"📡 Appel Ollama - Modèle: {OLLAMA_MODEL}, URL: {OLLAMA_BASE_URL}")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            logger.info(f"📤 Envoi requête à Ollama ({len(prompt)} caractères)...")
            
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 2000
                    }
                }
            )
            
            logger.info(f"📥 Réponse Ollama: status={response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                logger.info(f"✅ Ollama OK - Réponse: {len(content)} caractères")
                return content
            else:
                logger.error(f"❌ Erreur Ollama: {response.status_code} - {response.text[:500]}")
                return None
                
    except httpx.TimeoutException:
        logger.error("⏱️ Timeout lors de l'appel à Ollama (180s)")
        return None
    except httpx.ConnectError as e:
        logger.error(f"🔌 Erreur connexion Ollama: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur Ollama: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


# Ordre de sévérité décroissant pour la gravité (le plus critique en premier)
_GRAVITE_RANK = {"CRITIQUE": 0, "ELEVEE": 1, "MOYENNE": 2, "FAIBLE": 3}
_GRAVITE_ENUM = {"FAIBLE", "MOYENNE", "ELEVEE", "CRITIQUE"}


def normaliser_gravite(valeur: Any) -> str:
    """
    Normalise une valeur de gravité renvoyée par le LLM vers l'enum
    {FAIBLE, MOYENNE, ELEVEE, CRITIQUE}.

    - Si le LLM renvoie plusieurs valeurs séparées par '|' (ex 'ELEVEE|CRITIQUE'),
      on ne garde que la plus haute selon l'ordre CRITIQUE > ELEVEE > MOYENNE > FAIBLE.
    - Mise en majuscules, suppression des espaces.
    - Toute valeur hors enum (ex 'INCONNUE', '') retombe sur 'MOYENNE'.
    """
    if not valeur:
        return "MOYENNE"
    texte = str(valeur).upper()
    candidats = [p.strip() for p in texte.split("|") if p.strip()]
    # Ne conserver que les candidats appartenant à l'enum
    valides = [c for c in candidats if c in _GRAVITE_ENUM]
    if not valides:
        return "MOYENNE"
    # La plus haute (rang le plus petit)
    return min(valides, key=lambda c: _GRAVITE_RANK[c])


def prepare_complaints_data_for_analysis(plaintes: List[Plainte], services: List[Service]) -> Dict[str, Any]:
    """
    Prépare les données des plaintes pour l'analyse IA
    """
    # Statistiques globales
    total = len(plaintes)
    by_status = {}
    by_service = {}
    by_priority = {}
    sentiments = []
    resolution_times = []
    recent_complaints = []
    
    for p in plaintes:
        # Par statut
        status = p.statut.value if p.statut else "INCONNU"
        by_status[status] = by_status.get(status, 0) + 1
        
        # Par service
        service_name = p.service.nom if p.service else "Non assigné"
        by_service[service_name] = by_service.get(service_name, 0) + 1
        
        # Par priorité
        priority = p.priorite.value if p.priorite else "MOYEN"
        by_priority[priority] = by_priority.get(priority, 0) + 1
        
        # Sentiments
        if p.score_sentiment is not None:
            sentiments.append(p.score_sentiment)
        
        # Temps de résolution
        if p.date_resolution and p.date_creation:
            delta = (p.date_resolution - p.date_creation).total_seconds() / 86400
            resolution_times.append(delta)
        
        # 10 plaintes récentes avec détails
        if len(recent_complaints) < 10:
            recent_complaints.append({
                "numero": p.numero_plainte,
                "titre": p.titre[:100] if p.titre else "",
                "description": p.description[:200] if p.description else "",
                "service": service_name,
                "statut": status,
                "priorite": priority,
                "date": p.date_creation.strftime("%Y-%m-%d") if p.date_creation else "",
                "sentiment": p.score_sentiment,
                "mots_cles": p.mots_cles[:5] if p.mots_cles else []
            })
    
    # Calculer les moyennes
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Services avec leurs stats
    services_stats = []
    for s in services:
        services_stats.append({
            "nom": s.nom,
            "code": s.code_service,
            "plaintes_total": s.nombre_plaintes_total,
            "plaintes_resolues": s.nombre_plaintes_resolues,
            "temps_moyen": s.temps_moyen_resolution,
            "satisfaction": s.taux_satisfaction
        })
    
    return {
        "total_plaintes": total,
        "repartition_statut": by_status,
        "repartition_service": by_service,
        "repartition_priorite": by_priority,
        "sentiment_moyen": round(avg_sentiment, 2),
        "temps_resolution_moyen_jours": round(avg_resolution, 2),
        "plaintes_recentes": recent_complaints,
        "services": services_stats
    }


@router.post("/analyze/start")
async def start_ai_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Démarre une analyse IA asynchrone des plaintes.
    Retourne immédiatement un task_id pour suivre la progression.
    """
    try:
        # Générer un ID unique pour cette tâche
        task_id = str(uuid.uuid4())
        
        # Compter les plaintes et services pour estimer le temps
        plaintes_count = db.query(Plainte).count()
        services_count = db.query(Service).filter(Service.est_actif == True).count()
        
        if plaintes_count == 0:
            return {
                "success": True,
                "task_id": None,
                "message": "Aucune plainte à analyser",
                "data": {
                    "total_plaintes_analysees": 0,
                    "nombre_services": 0,
                    "analyses_par_service": [],
                    "causes_globales": [],
                    "services_critiques": [],
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Initialiser la tâche
        _analysis_tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "current_step": "Initialisation...",
            "total_plaintes": plaintes_count,
            "total_services": services_count,
            "services_analysed": 0,
            "started_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }
        
        # Publier l'événement de démarrage
        publish_task_event("ai_analysis_started", {
            "task_id": task_id,
            "total_plaintes": plaintes_count,
            "total_services": services_count,
            "message": f"Démarrage de l'analyse de {plaintes_count} plaintes..."
        })
        
        # Lancer l'analyse en arrière-plan
        background_tasks.add_task(run_ai_analysis_background, task_id)
        
        logger.info(f"🚀 Analyse IA démarrée - Task ID: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Analyse démarrée pour {plaintes_count} plaintes sur {services_count} services",
            "estimated_time_seconds": services_count * 30  # ~30s par service
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur démarrage analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/status/{task_id}")
async def get_analysis_status(task_id: str):
    """
    Récupère le statut d'une analyse en cours
    """
    if task_id not in _analysis_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = _analysis_tasks[task_id]
    
    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"],
        "total_plaintes": task["total_plaintes"],
        "total_services": task["total_services"],
        "services_analysed": task["services_analysed"],
        "started_at": task["started_at"],
        "has_result": task["result"] is not None,
        "error": task["error"]
    }


@router.get("/analyze/result/{task_id}")
async def get_analysis_result(task_id: str):
    """
    Récupère le résultat d'une analyse terminée
    """
    if task_id not in _analysis_tasks:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    task = _analysis_tasks[task_id]
    
    if task["status"] == "pending" or task["status"] == "running":
        return {
            "success": False,
            "message": "L'analyse est encore en cours",
            "status": task["status"],
            "progress": task["progress"]
        }
    
    if task["status"] == "error":
        return {
            "success": False,
            "message": task["error"],
            "status": "error"
        }
    
    return {
        "success": True,
        "data": task["result"],
        "message": "Analyse complétée avec succès"
    }


@router.get("/analyze/latest")
async def get_latest_analysis(db: Session = Depends(get_db)):
    """
    Récupère la dernière analyse IA sauvegardée en base de données.
    Permet d'afficher les résultats même après un rechargement de page.
    """
    try:
        # Récupérer la dernière analyse complétée
        latest = db.query(AIAnalysisResult).filter(
            AIAnalysisResult.status == "completed"
        ).order_by(AIAnalysisResult.completed_at.desc()).first()
        
        if not latest:
            return {
                "success": True,
                "data": None,
                "message": "Aucune analyse disponible. Lancez une première analyse IA."
            }
        
        # Construire le résultat
        result = {
            "total_plaintes_analysees": latest.total_plaintes_analysees,
            "nombre_services": latest.nombre_services,
            "analyses_par_service": latest.analyses_par_service or [],
            "causes_globales": latest.causes_globales or [],
            "services_critiques": latest.services_critiques or [],
            "timestamp": latest.completed_at.isoformat() if latest.completed_at else None,
            "model_used": latest.model_used,
            "duree_secondes": latest.duree_secondes,
            "task_id": latest.task_id
        }
        
        return {
            "success": True,
            "data": result,
            "message": f"Dernière analyse du {latest.completed_at.strftime('%d/%m/%Y à %H:%M') if latest.completed_at else 'N/A'}"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération dernière analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/history")
async def get_analysis_history(
    limit: int = Query(10, ge=1, le=50, description="Nombre d'analyses à retourner"),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des analyses IA
    """
    try:
        analyses = db.query(AIAnalysisResult).filter(
            AIAnalysisResult.status == "completed"
        ).order_by(AIAnalysisResult.completed_at.desc()).limit(limit).all()
        
        history = []
        for a in analyses:
            history.append({
                "task_id": a.task_id,
                "total_plaintes_analysees": a.total_plaintes_analysees,
                "nombre_services": a.nombre_services,
                "services_critiques_count": len(a.services_critiques) if a.services_critiques else 0,
                "model_used": a.model_used,
                "duree_secondes": a.duree_secondes,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None
            })
        
        return {
            "success": True,
            "data": history,
            "count": len(history),
            "message": f"{len(history)} analyses trouvées"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur historique analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_ai_analysis_background(task_id: str):
    """
    Exécute l'analyse IA en arrière-plan avec notifications de progression
    """
    from ..db.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        task = _analysis_tasks[task_id]
        task["status"] = "running"
        task["current_step"] = "Récupération des plaintes..."
        task["progress"] = 5
        
        publish_task_event("ai_analysis_progress", {
            "task_id": task_id,
            "progress": 5,
            "step": "Récupération des plaintes...",
            "message": "Chargement des données..."
        })
        
        # Récupérer les plaintes
        plaintes = db.query(Plainte).order_by(Plainte.date_creation.desc()).all()
        services = db.query(Service).filter(Service.est_actif == True).all()
        services_dict = {s.id: s.nom for s in services}
        
        task["progress"] = 10
        task["current_step"] = "Regroupement par service..."
        
        publish_task_event("ai_analysis_progress", {
            "task_id": task_id,
            "progress": 10,
            "step": "Regroupement par service...",
            "message": f"{len(plaintes)} plaintes chargées"
        })
        
        # Regrouper par service
        descriptions_par_service = {}
        
        for p in plaintes:
            try:
                service_name = services_dict.get(p.service_id, "Non assigné") if p.service_id else "Non assigné"
                
                texte_plainte = ""
                if p.titre:
                    texte_plainte += f"Titre: {p.titre}. "
                if p.description:
                    texte_plainte += f"Description: {p.description}. "
                if p.circonstances:
                    texte_plainte += f"Circonstances: {str(p.circonstances)[:300]}. "
                if p.consequences:
                    texte_plainte += f"Conséquences: {str(p.consequences)[:200]}. "
                if p.demande_plaignant:
                    texte_plainte += f"Demande: {str(p.demande_plaignant)[:200]}"
                
                if texte_plainte.strip():
                    if service_name not in descriptions_par_service:
                        descriptions_par_service[service_name] = []
                    descriptions_par_service[service_name].append({
                        "numero": p.numero_plainte or f"PL_{p.id}",
                        "texte": texte_plainte[:800],
                        "priorite": p.priorite.value if p.priorite else "MOYEN",
                        "statut": p.statut.value if p.statut else "RECU",
                        "score_sentiment": p.score_sentiment  # [-1, 1] ou None
                    })
            except Exception as e:
                logger.warning(f"Erreur plainte {p.id}: {e}")
                continue
        
        total_services = len(descriptions_par_service)
        task["total_services"] = total_services
        task["progress"] = 15
        
        # Analyser chaque service
        analyses_par_service = []
        progress_per_service = 75 / max(total_services, 1)  # 75% du temps pour les analyses
        
        for idx, (service_name, plaintes_service) in enumerate(descriptions_par_service.items()):
            if len(plaintes_service) == 0:
                continue
            
            current_progress = 15 + int(idx * progress_per_service)
            task["progress"] = current_progress
            task["current_step"] = f"Analyse du service: {service_name}"
            task["services_analysed"] = idx + 1
            
            # Publier la progression
            publish_task_event("ai_analysis_progress", {
                "task_id": task_id,
                "progress": current_progress,
                "step": f"Analyse du service: {service_name}",
                "message": f"Service {idx + 1}/{total_services}: {service_name} ({len(plaintes_service)} plaintes)",
                "services_analysed": idx + 1,
                "total_services": total_services
            })
            
            # Préparer le prompt
            descriptions_texte = "\n\n".join([
                f"[Plainte {i+1}] {p['texte']}" 
                for i, p in enumerate(plaintes_service[:20])
            ])
            
            # Prompt V2 (valide par banc d'essai oracle: 97.5% vs 63.8% pour l'ancien).
            system_prompt = """Tu es un expert qualite et gestion des risques dans un etablissement de sante francais. Tu analyses des plaintes de patients pour en extraire les causes RACINES concretes et actionnables.

METHODE:
1. Regroupe les plaintes par CAUSE RACINE commune (pas par symptome vague). Nomme chaque cause de facon PRECISE et SPECIFIQUE (ex: "Erreurs de dosage lors de la delivrance des medicaments" et NON "probleme de pharmacie" ; "Defaut de tri infirmier a l'accueil entrainant un retard de prise en charge" et NON "temps d'attente"). causes_identifiees[0] = LA cause dominante (mecanisme + consequence). Maximum 4 causes, triees par frequence decroissante.
2. "frequence" = NOMBRE EXACT de plaintes (parmi celles fournies) mentionnant cette cause. Ne depasse jamais le nombre total de plaintes. Ne liste une cause QUE si frequence >= 1 avec au moins une citation reelle.
3. BAREME de "gravite" (UNE seule valeur, jamais de "|"):
   - CRITIQUE: pronostic vital engage, erreur medicamenteuse, retard de prise en charge d'une urgence vitale (AVC, douleur thoracique non triee).
   - ELEVEE: atteinte a la securite/dignite sans risque vital immediat (sous-effectif de nuit, infection, suivi post-operatoire absent).
   - MOYENNE: desagrement organisationnel sans risque clinique (delai de rendez-vous non urgent, manque d'information). Un rendez-vous programme n'est JAMAIS une urgence vitale.
   - FAIBLE: gene mineure. POSITIF: remerciement/satisfaction.
4. "sentiment_general" parmi TRES_NEGATIF, NEGATIF, NEUTRE, POSITIF. Il reflete la cause DOMINANTE (la plus frequente/grave), pas une moyenne: une plainte positive isolee n'annule PAS un grief ELEVEE/CRITIQUE recurrent. Si une cause CRITIQUE existe (risque vital, erreur medicamenteuse, AVC/infarctus, deces evite), sentiment_general DOIT etre TRES_NEGATIF.
5. "exemples": UNIQUEMENT des extraits copies-colles MOT POUR MOT des plaintes. Interdiction d'inventer, de paraphraser, d'ecrire "Plainte 1". Si tu ne peux pas citer textuellement, mets [].
6. "recommandations": liste PLATE de chaines de caracteres (jamais d'objets ni de listes imbriquees), actions concretes liees aux causes.
Reponds en FRANCAIS uniquement, et UNIQUEMENT en JSON valide (aucun texte avant/apres, aucun mot anglais)."""

            # L'exemple few-shot est une chaine simple (accolades reelles) -> concatene avec
            # la partie dynamique en f-string, pour eviter tout echappement d'accolades.
            _exemple_format = (
                'EXEMPLE de format attendu (service fictif "Laboratoire", 3 plaintes):\n'
                '{\n'
                '  "service": "Laboratoire",\n'
                '  "nombre_plaintes": 3,\n'
                '  "causes_identifiees": [\n'
                '    {"cause": "Perte ou non-transmission des resultats d\'analyse aux patients", "frequence": 2, "gravite": "ELEVEE", "exemples": ["je n\'ai jamais recu mes resultats"]},\n'
                '    {"cause": "Accueil peu courtois", "frequence": 1, "gravite": "FAIBLE", "exemples": ["la secretaire etait desagreable"]}\n'
                '  ],\n'
                '  "problemes_recurrents": ["Perte de resultats d\'analyse"],\n'
                '  "sentiment_general": "NEGATIF",\n'
                '  "recommandations": ["Mettre en place une tracabilite des resultats", "Sensibiliser le personnel d\'accueil"]\n'
                '}'
            )
            analysis_prompt = (
                _exemple_format
                + f'\n\nAnalyse maintenant les {len(plaintes_service)} plaintes du service "{service_name}":\n\n'
                + descriptions_texte
                + f'\n\nProduis le MEME format JSON (cle "service"="{service_name}", "nombre_plaintes"={len(plaintes_service)}). '
                + "Cause dominante en premier (precise); frequence = comptage reel; gravite = une seule valeur du bareme; "
                + "exemples = citations EXACTES (verbatim) ou []; recommandations = liste plate de chaines; "
                + "sentiment_general coherent avec la gravite. JSON UNIQUEMENT."
            )

            # Appeler Ollama
            ai_response = await call_ollama(analysis_prompt, system_prompt)
            
            if ai_response:
                try:
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = ai_response[json_start:json_end]
                        service_analysis = json.loads(json_str)
                        analyses_par_service.append(service_analysis)
                    else:
                        raise ValueError("JSON non trouvé")
                except (json.JSONDecodeError, ValueError) as e:
                    analyses_par_service.append({
                        "service": service_name,
                        "nombre_plaintes": len(plaintes_service),
                        "causes_identifiees": [{
                            "cause": "Erreur de parsing - réessayez",
                            "frequence": len(plaintes_service),
                            "gravite": "MOYENNE",
                            "exemples": []
                        }],
                        "problemes_recurrents": [],
                        "sentiment_general": "INCONNU",
                        "recommandations": []
                    })
            else:
                analyses_par_service.append({
                    "service": service_name,
                    "nombre_plaintes": len(plaintes_service),
                    "causes_identifiees": [{
                        "cause": "Ollama non disponible",
                        "frequence": len(plaintes_service),
                        "gravite": "INCONNUE",
                        "exemples": []
                    }],
                    "problemes_recurrents": [],
                    "sentiment_general": "INCONNU",
                    "recommandations": ["Vérifier Ollama"]
                })
        
        # Synthèse finale
        task["progress"] = 95
        task["current_step"] = "Génération de la synthèse..."
        
        publish_task_event("ai_analysis_progress", {
            "task_id": task_id,
            "progress": 95,
            "step": "Génération de la synthèse...",
            "message": "Compilation des résultats..."
        })
        
        # NETTOYAGE DE LA GRAVITE: normaliser chaque cause de chaque service
        # (le LLM renvoie parfois 'ELEVEE|CRITIQUE' ou des valeurs hors enum).
        # On normalise in-place dans causes_identifiees (causes par service) ...
        for analyse in analyses_par_service:
            for cause in analyse.get("causes_identifiees", []):
                if isinstance(cause, dict):
                    cause["gravite"] = normaliser_gravite(cause.get("gravite"))

        # ... puis on collecte les causes globales avec la gravité déjà normalisée.
        toutes_causes = []
        for analyse in analyses_par_service:
            for cause in analyse.get("causes_identifiees", []):
                if not isinstance(cause, dict):
                    continue
                toutes_causes.append({
                    "service": analyse["service"],
                    "cause": cause.get("cause", ""),
                    "gravite": normaliser_gravite(cause.get("gravite")),
                    "frequence": cause.get("frequence", 0)
                })

        toutes_causes.sort(key=lambda x: _GRAVITE_RANK.get(x["gravite"], 5))
        
        # SERVICES CRITIQUES DISCRIMINANTS
        # On ne se fie plus au seul sentiment_general renvoyé par le LLM
        # ('NEGATIF + >3 plaintes' marquait 5-6/6 services).
        # On calcule des agrégats RÉELS à partir des score_sentiment ([-1,1])
        # des plaintes déjà regroupées par service dans descriptions_par_service.
        SEUIL_PCT_NEGATIFS = 60.0   # >= 60% de plaintes à sentiment négatif
        SEUIL_SCORE_MOYEN = -0.3    # OU score sentiment moyen <= -0.3
        SEUIL_MIN_PLAINTES = 3      # ET au moins 3 plaintes

        services_critiques_detail = []
        for service_name, plaintes_service in descriptions_par_service.items():
            nb_plaintes = len(plaintes_service)
            if nb_plaintes < SEUIL_MIN_PLAINTES:
                continue

            scores = [
                p["score_sentiment"]
                for p in plaintes_service
                if p.get("score_sentiment") is not None
            ]
            if not scores:
                # Pas de données de sentiment exploitables pour ce service
                continue

            nb_negatifs = sum(1 for s in scores if s < 0)
            pct_negatifs = (nb_negatifs / len(scores)) * 100.0
            score_moyen = sum(scores) / len(scores)

            if pct_negatifs >= SEUIL_PCT_NEGATIFS or score_moyen <= SEUIL_SCORE_MOYEN:
                services_critiques_detail.append({
                    "service": service_name,
                    "nombre_plaintes": nb_plaintes,
                    "pct_negatifs": round(pct_negatifs, 1),
                    "score_sentiment_moyen": round(score_moyen, 2),
                })

        # Trier par sévérité (plus négatif d'abord, puis plus de négatifs) et limiter au top 3
        services_critiques_detail.sort(
            key=lambda x: (x["score_sentiment_moyen"], -x["pct_negatifs"])
        )
        services_critiques_detail = services_critiques_detail[:3]
        services_critiques = [s["service"] for s in services_critiques_detail]

        # Résultat final
        result = {
            "total_plaintes_analysees": len(plaintes),
            "nombre_services": total_services,
            "analyses_par_service": analyses_par_service,
            "causes_globales": toutes_causes[:10],
            "services_critiques": services_critiques,
            "services_critiques_detail": services_critiques_detail,
            "timestamp": datetime.now().isoformat(),
            "model_used": OLLAMA_MODEL
        }
        
        # Calculer la durée de l'analyse
        started_at_dt = datetime.fromisoformat(task["started_at"])
        completed_at_dt = datetime.now()
        duree_secondes = (completed_at_dt - started_at_dt).total_seconds()
        
        # Sauvegarder dans la base de données
        try:
            ai_result = AIAnalysisResult(
                task_id=task_id,
                total_plaintes_analysees=len(plaintes),
                nombre_services=total_services,
                model_used=OLLAMA_MODEL,
                analyses_par_service=analyses_par_service,
                causes_globales=toutes_causes[:10],
                services_critiques=result["services_critiques"],
                status="completed",
                started_at=started_at_dt,
                completed_at=completed_at_dt,
                duree_secondes=duree_secondes
            )
            db.add(ai_result)
            db.commit()
            logger.info(f"💾 Résultat analyse IA sauvegardé en base - Task ID: {task_id}")
        except Exception as db_error:
            logger.error(f"❌ Erreur sauvegarde DB: {db_error}")
            db.rollback()
        
        # Marquer comme terminé
        task["status"] = "completed"
        task["progress"] = 100
        task["current_step"] = "Analyse terminée!"
        task["result"] = result
        
        # Publier la notification de fin
        publish_task_event("ai_analysis_completed", {
            "task_id": task_id,
            "success": True,
            "total_plaintes": len(plaintes),
            "total_services": total_services,
            "services_critiques": len(result["services_critiques"]),
            "message": f"Analyse terminée: {len(plaintes)} plaintes analysées sur {total_services} services"
        })
        
        logger.info(f"✅ Analyse IA terminée - Task ID: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}")
        import traceback
        traceback.print_exc()
        
        task = _analysis_tasks.get(task_id)
        if task:
            task["status"] = "error"
            task["error"] = str(e)
            task["current_step"] = "Erreur!"
        
        publish_task_event("ai_analysis_error", {
            "task_id": task_id,
            "error": str(e),
            "message": f"Erreur lors de l'analyse: {str(e)}"
        })
    
    finally:
        db.close()


# Garder l'ancien endpoint pour compatibilité (redirige vers le nouveau)
@router.post("/analyze")
async def analyze_with_ai(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    [DEPRECATED] Utilisez /analyze/start pour une analyse asynchrone.
    Cet endpoint démarre maintenant une analyse asynchrone.
    """
    return await start_ai_analysis(background_tasks, db)


def generate_fallback_analysis(data: Dict[str, Any]) -> str:
    """
    Génère une analyse basique si Ollama n'est pas disponible
    """
    total = data['total_plaintes']
    by_status = data['repartition_statut']
    by_service = data['repartition_service']
    by_priority = data['repartition_priorite']
    
    # Trouver le service avec le plus de plaintes
    top_service = max(by_service.items(), key=lambda x: x[1]) if by_service else ("Aucun", 0)
    
    # Calculer le taux de résolution
    resolved = by_status.get('TRAITE', 0) + by_status.get('CLOTURE', 0)
    taux_resolution = (resolved / total * 100) if total > 0 else 0
    
    # Plaintes urgentes
    urgentes = by_priority.get('URGENT', 0) + by_priority.get('ELEVE', 0)
    
    analysis = f"""### 1. DIAGNOSTIC GLOBAL
Sur les 90 derniers jours, {total} plaintes ont été enregistrées.
- Taux de résolution: {taux_resolution:.1f}%
- Sentiment moyen: {data['sentiment_moyen']} ({"négatif" if data['sentiment_moyen'] < 0 else "positif"})
- Temps de résolution moyen: {data['temps_resolution_moyen_jours']:.1f} jours

### 2. PATTERNS DÉTECTÉS
- Le service "{top_service[0]}" concentre le plus de plaintes ({top_service[1]} plaintes, soit {top_service[1]/total*100:.1f}%)
- {urgentes} plaintes sont marquées comme urgentes ou priorité élevée ({urgentes/total*100:.1f}%)
- {by_status.get('RECU', 0)} plaintes sont encore en attente de traitement

### 3. CAUSES PRINCIPALES DES PROBLÈMES
- Concentration des plaintes sur certains services
- Temps de traitement potentiellement trop long ({data['temps_resolution_moyen_jours']:.1f} jours en moyenne)
- Score de sentiment négatif indiquant une insatisfaction générale

### 4. SERVICES CRITIQUES
"""
    
    # Ajouter les services critiques
    for service in data.get('services', [])[:3]:
        if service['plaintes_total'] > 0:
            analysis += f"- **{service['nom']}**: {service['plaintes_total']} plaintes, satisfaction {service['satisfaction']:.0f}%\n"
    
    analysis += f"""
### 5. RECOMMANDATIONS PRIORITAIRES
1. **Prioriser le service {top_service[0]}** - Analyser les causes spécifiques des {top_service[1]} plaintes
2. **Réduire le temps de traitement** - Objectif: passer de {data['temps_resolution_moyen_jours']:.1f} à moins de 5 jours
3. **Traiter les {by_status.get('RECU', 0)} plaintes en attente** - Mettre en place un processus de triage rapide
4. **Former les équipes** - Sur la gestion des plaintes et la communication patient
5. **Mettre en place un suivi proactif** - Contacter les patients avant l'escalade

### 6. INDICATEURS À SURVEILLER
- Temps moyen de première réponse
- Taux de résolution à J+7
- Score de satisfaction post-résolution
- Nombre de plaintes par service par semaine
- Taux de récurrence des plaintes
"""
    
    return analysis


def parse_ai_response(response: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse la réponse de l'IA pour extraire les sections structurées
    """
    result = {
        "resume": "",
        "patterns": [],
        "causes": [],
        "recommandations": [],
        "services_critiques": [],
        "indicateurs": []
    }
    
    try:
        # Extraire un résumé (première section ou premiers paragraphes)
        lines = response.split('\n')
        resume_lines = []
        for line in lines[:10]:
            if line.strip() and not line.startswith('#'):
                resume_lines.append(line.strip())
            if len(resume_lines) >= 3:
                break
        result["resume"] = " ".join(resume_lines)
        
        # Extraire les patterns (recherche de mots-clés)
        if "PATTERN" in response.upper() or "SCHÉMA" in response.upper():
            result["patterns"] = extract_list_items(response, ["pattern", "schéma", "tendance", "récurrent"])
        
        # Extraire les causes
        if "CAUSE" in response.upper():
            result["causes"] = extract_list_items(response, ["cause", "origine", "problème", "raison"])
        
        # Extraire les recommandations
        if "RECOMMANDATION" in response.upper() or "ACTION" in response.upper():
            result["recommandations"] = extract_list_items(response, ["recommandation", "action", "amélioration", "proposition"])
        
        # Services critiques basés sur les données
        services_data = data.get('services', [])
        for s in services_data:
            if s.get('satisfaction', 100) < 50 or s.get('plaintes_total', 0) > 10:
                result["services_critiques"].append({
                    "nom": s.get('nom', 'Inconnu'),
                    "raison": f"Satisfaction: {s.get('satisfaction', 0):.0f}%, Plaintes: {s.get('plaintes_total', 0)}"
                })
        
        # Indicateurs
        result["indicateurs"] = [
            "Temps moyen de résolution",
            "Taux de satisfaction",
            "Nombre de plaintes par service",
            "Score de sentiment moyen",
            "Taux de résolution sous 7 jours"
        ]
        
    except Exception as e:
        logger.error(f"Erreur parsing réponse IA: {e}")
    
    return result


def extract_list_items(text: str, keywords: List[str]) -> List[str]:
    """
    Extrait les éléments de liste d'un texte basé sur des mots-clés
    """
    items = []
    lines = text.split('\n')
    
    in_section = False
    for line in lines:
        line_lower = line.lower()
        
        # Vérifier si on entre dans une section pertinente
        if any(kw in line_lower for kw in keywords):
            in_section = True
            continue
        
        # Si on est dans la section, extraire les items de liste
        if in_section:
            stripped = line.strip()
            if stripped.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                # Nettoyer l'item
                item = stripped.lstrip('-*•0123456789.)')
                item = item.strip()
                if item and len(item) > 10:
                    items.append(item[:200])  # Limiter la longueur
            elif stripped.startswith('#'):
                # Nouvelle section, on sort
                in_section = False
        
        if len(items) >= 5:
            break
    
    return items


@router.get("/analyze/status")
async def get_analysis_status():
    """
    Vérifie si Ollama est disponible pour l'analyse
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                return {
                    "success": True,
                    "data": {
                        "ollama_available": True,
                        "models_available": model_names,
                        "recommended_model": OLLAMA_MODEL,
                        "model_ready": any(OLLAMA_MODEL in m for m in model_names)
                    },
                    "message": "Ollama est disponible"
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "ollama_available": False,
                        "models_available": [],
                        "recommended_model": OLLAMA_MODEL,
                        "model_ready": False
                    },
                    "message": "Ollama n'est pas disponible"
                }
                
    except Exception as e:
        return {
            "success": True,
            "data": {
                "ollama_available": False,
                "error": str(e),
                "recommended_model": OLLAMA_MODEL,
                "model_ready": False
            },
            "message": f"Impossible de contacter Ollama: {str(e)}"
        }