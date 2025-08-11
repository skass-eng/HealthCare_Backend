#!/usr/bin/env python3
"""
API SERVICES KPI - HealthCare AI Architecture ODYSSEE
Endpoints REST CRUD pour les services hospitaliers avec KPIs
Version: 2.0.0 - Architecture ODYSSEE simplifiée SANS organisation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from ..db.database import get_db
from shared.models import Service, Plainte, StatutPlainte
from shared.schemas import ServiceResponse, ServiceCreate, ServiceUpdate, ServiceKPIs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["Services KPI"])

# ==================== CRUD SERVICES ====================

@router.get("/", response_model=List[ServiceResponse])
async def list_services(
    actif_seulement: bool = Query(True, description="Afficher seulement les services actifs"),
    db: Session = Depends(get_db)
):
    """
    Lister tous les services avec leurs KPIs calculés
    """
    try:
        query = db.query(Service)
        
        if actif_seulement:
            query = query.filter(Service.est_actif == True)
        
        services = query.all()
        
        # Calculer les KPIs pour chaque service
        for service in services:
            await _calculate_service_kpis(service, db)
        
        db.commit()
        
        # Convertir en réponse
        services_response = [ServiceResponse.model_validate(service) for service in services]
        
        logger.info(f"✅ {len(services_response)} services récupérés avec KPIs")
        return services_response
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ServiceResponse)
async def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau service hospitalier
    """
    try:
        # Vérifier l'unicité du code service
        existing_service = db.query(Service).filter(
            Service.code_service == service_data.code_service
        ).first()
        
        if existing_service:
            raise HTTPException(
                status_code=400, 
                detail=f"Un service avec le code '{service_data.code_service}' existe déjà"
            )
        
        # Créer le nouveau service
        new_service = Service(**service_data.model_dump())
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        
        logger.info(f"✅ Service créé: {new_service.nom} (ID: {new_service.id})")
        return ServiceResponse.model_validate(new_service)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la création du service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer un service par ID avec ses KPIs calculés
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Calculer les KPIs
        await _calculate_service_kpis(service, db)
        db.commit()
        
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération du service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un service
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Vérifier l'unicité du code service si modifié
        if service_data.code_service and service_data.code_service != service.code_service:
            existing_service = db.query(Service).filter(
                Service.code_service == service_data.code_service,
                Service.id != service_id
            ).first()
            
            if existing_service:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Un service avec le code '{service_data.code_service}' existe déjà"
                )
        
        # Mettre à jour les champs
        update_data = service_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        # Recalculer les KPIs
        await _calculate_service_kpis(service, db)
        
        db.commit()
        db.refresh(service)
        
        logger.info(f"✅ Service mis à jour: {service.nom} (ID: {service.id})")
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la mise à jour du service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprimer un service (soft delete)
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Vérifier s'il y a des plaintes associées
        plaintes_count = db.query(func.count(Plainte.id)).filter(
            Plainte.service_id == service_id
        ).scalar()
        
        if plaintes_count > 0:
            # Soft delete - garder les données pour l'historique
            service.est_actif = False
            message = f"Service désactivé (contient {plaintes_count} plaintes)"
        else:
            # Hard delete si aucune plainte
            db.delete(service)
            message = "Service supprimé définitivement"
        
        db.commit()
        
        logger.info(f"✅ {message}: {service.nom} (ID: {service_id})")
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression du service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ENDPOINTS KPI ====================

@router.get("/{service_id}/kpis", response_model=ServiceKPIs)
async def get_service_kpis(
    service_id: int,
    recalculer: bool = Query(False, description="Forcer le recalcul des KPIs"),
    db: Session = Depends(get_db)
):
    """
    Récupérer uniquement les KPIs d'un service
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        if recalculer:
            await _calculate_service_kpis(service, db)
            db.commit()
        
        return ServiceKPIs(
            nombre_plaintes_total=service.nombre_plaintes_total,
            nombre_plaintes_resolues=service.nombre_plaintes_resolues,
            temps_moyen_resolution=service.temps_moyen_resolution,
            taux_satisfaction=service.taux_satisfaction
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recalculate-all-kpis")
async def recalculate_all_kpis(
    db: Session = Depends(get_db)
):
    """
    Recalculer tous les KPIs de tous les services actifs
    """
    try:
        services = db.query(Service).filter(Service.est_actif == True).all()
        
        for service in services:
            await _calculate_service_kpis(service, db)
        
        db.commit()
        
        logger.info(f"✅ KPIs recalculés pour {len(services)} services")
        return {
            "message": f"KPIs recalculés pour {len(services)} services",
            "services_updated": len(services)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors du recalcul des KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== FONCTIONS UTILITAIRES ====================

async def _calculate_service_kpis(service: Service, db: Session):
    """
    Calculer les KPIs d'un service donné
    """
    try:
        # 1. Nombre total de plaintes
        total_plaintes = db.query(func.count(Plainte.id)).filter(
            Plainte.service_id == service.id
        ).scalar() or 0
        
        # 2. Nombre de plaintes résolues (statut TRAITE ou CLOTURE)
        plaintes_resolues = db.query(func.count(Plainte.id)).filter(
            and_(
                Plainte.service_id == service.id,
                Plainte.statut.in_([StatutPlainte.TRAITE, StatutPlainte.CLOTURE])
            )
        ).scalar() or 0
        
        # 3. Temps moyen de résolution (en jours)
        avg_resolution = db.query(
            func.avg(
                func.extract('epoch', Plainte.date_resolution - Plainte.date_creation) / 86400
            )
        ).filter(
            and_(
                Plainte.service_id == service.id,
                Plainte.date_resolution.isnot(None)
            )
        ).scalar()
        
        temps_moyen = round(float(avg_resolution or 0), 2)
        
        # 4. Taux de satisfaction (basé sur le score sentiment moyen)
        avg_sentiment = db.query(
            func.avg(Plainte.score_sentiment)
        ).filter(
            and_(
                Plainte.service_id == service.id,
                Plainte.score_sentiment.isnot(None)
            )
        ).scalar()
        
        # Convertir sentiment (-1 à 1) en pourcentage de satisfaction (0 à 100)
        if avg_sentiment is not None:
            taux_satisfaction = round(((float(avg_sentiment) + 1) / 2) * 100, 2)
        else:
            taux_satisfaction = 0.0
        
        # Mettre à jour le service
        service.nombre_plaintes_total = total_plaintes
        service.nombre_plaintes_resolues = plaintes_resolues
        service.temps_moyen_resolution = temps_moyen
        service.taux_satisfaction = taux_satisfaction
        
        logger.debug(f"KPIs calculés pour {service.nom}: {total_plaintes} plaintes, {plaintes_resolues} résolues")
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul KPIs pour service {service.id}: {e}")
        raise