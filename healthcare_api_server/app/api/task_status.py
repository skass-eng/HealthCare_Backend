#!/usr/bin/env python3
"""
API STATUT DES TÂCHES - HealthCare AI Architecture ODYSSEE
Endpoints pour vérifier le statut des tâches Celery et notifications
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional
import logging
from datetime import datetime

from ..db.database import get_db
from shared.models import AnalyseIA, Plainte
from celery_worker_v2 import get_task_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Tâches"])

@router.get("/status/{task_id}")
async def get_task_status_endpoint(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Récupérer le statut d'une tâche Celery
    """
    try:
        task_status = get_task_status(task_id)
        return task_status
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut de la tâche {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du statut")

@router.get("/plainte/{plainte_id}/status")
async def get_plainte_analysis_status(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer le statut de l'analyse d'une plainte
    """
    try:
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Récupérer l'analyse IA
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        if not analyse_ia:
            return {
                "plainte_id": plainte_id,
                "status": "not_started",
                "message": "Aucune analyse en cours"
            }
        
        status_info = {
            "plainte_id": plainte_id,
            "status": analyse_ia.statut_analyse,
            "date_analyse": analyse_ia.date_analyse.isoformat() if analyse_ia.date_analyse else None,
            "date_mise_a_jour": analyse_ia.date_mise_a_jour.isoformat() if analyse_ia.date_mise_a_jour else None,
        }
        
        # Ajouter les résultats si l'analyse est terminée
        if analyse_ia.statut_analyse == "complete":
            status_info.update({
                "sentiment": analyse_ia.sentiment,
                "service_suggere": analyse_ia.service_suggere,
                "priorite_ia": analyse_ia.priorite_ia,
                "resume_ia": analyse_ia.resume_ia,
                "reponse_suggeree": analyse_ia.reponse_suggeree,
                "notification": {
                    "type": "success",
                    "title": "Analyse terminée",
                    "message": f"L'analyse de la plainte #{plainte.numero_plainte} est terminée. Le rapport PDF et l'analyse IA sont disponibles.",
                    "timestamp": datetime.now().isoformat()
                }
            })
        elif analyse_ia.statut_analyse == "erreur":
            status_info.update({
                "notification": {
                    "type": "error",
                    "title": "Erreur d'analyse",
                    "message": f"Une erreur s'est produite lors de l'analyse de la plainte #{plainte.numero_plainte}.",
                    "timestamp": datetime.now().isoformat()
                }
            })
        elif analyse_ia.statut_analyse == "en_cours":
            status_info.update({
                "notification": {
                    "type": "info",
                    "title": "Analyse en cours",
                    "message": f"L'analyse de la plainte #{plainte.numero_plainte} est en cours de traitement...",
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut d'analyse: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/plainte/{plainte_id}/pdf-status")
async def check_pdf_status(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Vérifier si le PDF d'une plainte a été généré
    """
    try:
        import os
        from pathlib import Path
        
        # Vérifier que la plainte existe
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise HTTPException(status_code=404, detail="Plainte non trouvée")
        
        # Vérifier l'existence du PDF
        pdf_dir = Path("data/pdf_reports")
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = pdf_dir / pdf_filename
        
        if pdf_path.exists():
            return {
                "plainte_id": plainte_id,
                "pdf_generated": True,
                "pdf_path": str(pdf_path),
                "pdf_size": pdf_path.stat().st_size,
                "generated_at": datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat()
            }
        else:
            return {
                "plainte_id": plainte_id,
                "pdf_generated": False,
                "message": "PDF non encore généré"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification du PDF")

@router.post("/plainte/{plainte_id}/notify-complete")
async def mark_analysis_notified(
    plainte_id: int,
    db: Session = Depends(get_db)
):
    """
    Marquer qu'une notification a été vue par l'utilisateur
    """
    try:
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        if not analyse_ia:
            raise HTTPException(status_code=404, detail="Analyse non trouvée")
        
        # Ici on pourrait ajouter un champ pour marquer la notification comme vue
        # Pour l'instant, on retourne simplement un success
        
        return {
            "plainte_id": plainte_id,
            "notified": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la notification: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la notification")
