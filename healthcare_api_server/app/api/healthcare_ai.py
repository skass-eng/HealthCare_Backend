#!/usr/bin/env python3
"""
API HEALTHCARE AI - Architecture ODYSSEE
Endpoints pour les statistiques et métriques de la page healthcare-ai
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Optional
from datetime import datetime, date, timedelta
import logging

from ..db.database import get_db
from shared.models import Plainte, StatutPlainte
from shared.schemas import SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healthcare-ai", tags=["Healthcare AI"])

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