#!/usr/bin/env python3
"""
API PAGES ROUTER - HealthCare AI
Version router pour inclusion dans l'application principale
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from database_unified import SessionLocal
from models_unified import Plainte, Service, Organisation

# Configuration du logging
import logging
logger = logging.getLogger(__name__)

# Créer le router
app = APIRouter(
    prefix="",
    tags=["API Pages"],
    responses={404: {"description": "Not found"}},
)

# ==================== DEPENDENCY ====================

def get_db() -> Session:
    """Dépendance pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ROUTES PAGES ====================

@app.get("/dashboard")
async def get_pages_dashboard(organisation_id: Optional[int] = Query(None)):
    """Page dashboard principale"""
    return {
        "page": "dashboard",
        "title": "Dashboard Principal",
        "description": "Vue d'ensemble des plaintes et statistiques",
        "organisation_id": organisation_id,
        "widgets": [
            "statistiques_plaintes",
            "plaintes_recentes",
            "tendances",
            "alertes"
        ]
    }

@app.get("/nouvelles-plaintes")
async def get_pages_nouvelles_plaintes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    priorite: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None)
):
    """Page des nouvelles plaintes"""
    return {
        "page": "nouvelles-plaintes",
        "title": "Nouvelles Plaintes",
        "description": "Gestion des plaintes nouvellement créées",
        "filters": {
            "organisation_id": organisation_id,
            "priorite": priorite,
            "service_id": service_id
        },
        "pagination": {
            "page": page,
            "limit": limit
        }
    }

@app.get("/en-cours")
async def get_pages_en_cours(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None)
):
    """Page des plaintes en cours"""
    return {
        "page": "en-cours",
        "title": "Plaintes en Cours",
        "description": "Suivi des plaintes en cours de traitement",
        "filters": {
            "organisation_id": organisation_id,
            "statut": statut
        },
        "pagination": {
            "page": page,
            "limit": limit
        }
    }

@app.get("/traitees")
async def get_pages_traitees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None)
):
    """Page des plaintes traitées"""
    return {
        "page": "traitees",
        "title": "Plaintes Traitées",
        "description": "Historique des plaintes résolues",
        "filters": {
            "organisation_id": organisation_id,
            "date_debut": date_debut,
            "date_fin": date_fin
        },
        "pagination": {
            "page": page,
            "limit": limit
        }
    }

@app.get("/ameliorations")
async def get_pages_ameliorations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    categorie: Optional[str] = Query(None)
):
    """Page des améliorations"""
    return {
        "page": "ameliorations",
        "title": "Améliorations",
        "description": "Suggestions d'amélioration du système",
        "filters": {
            "categorie": categorie
        },
        "pagination": {
            "page": page,
            "limit": limit
        }
    }

@app.get("/analytics")
async def get_pages_analytics(
    periode: str = Query("30j", description="Période d'analyse: 7j, 30j, 90j, 1an"),
    organisation_id: Optional[int] = Query(None)
):
    """Page analytics"""
    return {
        "page": "analytics",
        "title": "Analytics",
        "description": "Analyses avancées et métriques",
        "periode": periode,
        "organisation_id": organisation_id,
        "charts": [
            "tendances_plaintes",
            "repartition_services",
            "satisfaction_clients",
            "performance_ia"
        ]
    }

@app.get("/analytics-v2")
async def get_pages_analytics_v2(organisation_id: Optional[int] = Query(None)):
    """Page analytics v2"""
    return {
        "page": "analytics-v2",
        "title": "Analytics V2",
        "description": "Version avancée des analytics",
        "organisation_id": organisation_id,
        "features": [
            "predictions_ia",
            "analyse_sentiment",
            "detection_anomalies",
            "optimisation_automatique"
        ]
    }

@app.get("/parametres")
async def get_pages_parametres():
    """Page des paramètres"""
    return {
        "page": "parametres",
        "title": "Paramètres",
        "description": "Configuration du système",
        "sections": [
            "organisations",
            "services",
            "utilisateurs",
            "notifications",
            "securite"
        ]
    }

@app.get("/apis-utilisees")
async def get_pages_apis_utilisees():
    """Page des APIs utilisées"""
    return {
        "page": "apis-utilisees",
        "title": "APIs Utilisées",
        "description": "Statistiques d'utilisation des APIs",
        "apis": [
            "api_unified",
            "api_pages",
            "api_dashboard_unified"
        ]
    }

@app.get("/health")
async def get_pages_health():
    """Page de santé des APIs"""
    return {
        "page": "health",
        "title": "Santé des APIs",
        "description": "État de santé de tous les services",
        "services": [
            "api_unified",
            "api_pages", 
            "api_dashboard_unified",
            "database",
            "ai_services"
        ]
    } 