#!/usr/bin/env python3
"""
API SERVICES - HealthCare AI Architecture ODYSSEE
Endpoints REST pour les services hospitaliers
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..db.database import get_db
from shared.models import Service
from shared.schemas import ServiceResponse, ServiceCreate, ServiceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["Services"])

@router.get("/", response_model=List[ServiceResponse])
async def list_services(
    actif_seulement: bool = Query(True, description="Afficher seulement les services actifs"),
    db: Session = Depends(get_db)
):
    """
    Lister les services hospitaliers avec filtres optionnels
    """
    try:
        query = db.query(Service)
        
        if actif_seulement:
            query = query.filter(Service.est_actif == True)
        
        services = query.all()
        
        # Convertir les objets SQLAlchemy en schémas Pydantic
        services_response = []
        for service in services:
            services_response.append(ServiceResponse.model_validate(service))
        
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
    Créer un nouveau service
    """
    try:
        # Créer le nouveau service
        new_service = Service(**service_data.model_dump())
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        
        return ServiceResponse.model_validate(new_service)
        
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
    Récupérer un service par ID
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Convertir l'objet SQLAlchemy en schéma Pydantic
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
        
        # Mettre à jour les champs du service
        update_data = service_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        db.commit()
        db.refresh(service)
        
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
        
        # Soft delete - marquer comme inactif
        service.est_actif = False
        db.commit()
        
        return {"message": "Service supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression du service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Nouveaux endpoints pour le pattern /clinics/{clinic_id}/services
# Ces routes doivent être définies AVANT la route générique /{service_id}
@router.get("/clinics/{clinic_id}/services", response_model=List[ServiceResponse])
async def list_clinic_services(
    clinic_id: int,
    organisation_id: Optional[int] = Query(None, description="Filtrer par organisation"),
    db: Session = Depends(get_db)
):
    """
    Lister les services d'une clinique spécifique
    """
    try:
        query = db.query(Service).filter(Service.est_actif == True)
        
        # Filtrer par organisation (clinic_id)
        query = query.filter(Service.organisation_id == clinic_id)
        
        # Si organisation_id est spécifié en plus, l'utiliser aussi
        if organisation_id and organisation_id != clinic_id:
            query = query.filter(Service.organisation_id == organisation_id)
        
        services = query.all()
        
        # Convertir les objets SQLAlchemy en schémas Pydantic
        services_response = []
        for service in services:
            services_response.append(ServiceResponse.model_validate(service))
        
        return services_response
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des services de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clinics/{clinic_id}/services/{service_id}", response_model=ServiceResponse)
async def get_clinic_service(
    clinic_id: int,
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer un service spécifique d'une clinique
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.organisation_id == clinic_id,
            Service.est_actif == True
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Convertir l'objet SQLAlchemy en schéma Pydantic
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération du service {service_id} de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clinics/{clinic_id}/services", response_model=ServiceResponse)
async def create_clinic_service(
    clinic_id: int,
    service_data: ServiceCreate,
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau service pour une clinique
    """
    try:
        # Ajouter l'organisation_id au service
        service_dict = service_data.model_dump()
        service_dict["organisation_id"] = clinic_id
        
        # Créer le nouveau service
        new_service = Service(**service_dict)
        db.add(new_service)
        db.commit()
        db.refresh(new_service)
        
        return ServiceResponse.model_validate(new_service)
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la création du service pour la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clinics/{clinic_id}/services/{service_id}", response_model=ServiceResponse)
async def update_clinic_service(
    clinic_id: int,
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un service d'une clinique
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.organisation_id == clinic_id
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Mettre à jour les champs du service
        update_data = service_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(service, key):
                setattr(service, key, value)
        
        db.commit()
        db.refresh(service)
        
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la mise à jour du service {service_id} de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clinics/{clinic_id}/services/{service_id}")
async def delete_clinic_service(
    clinic_id: int,
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprimer un service d'une clinique (soft delete)
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.organisation_id == clinic_id
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Soft delete - marquer comme inactif
        service.est_actif = False
        db.commit()
        
        return {"message": "Service supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression du service {service_id} de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clinics/{clinic_id}/services/{service_id}/status", response_model=ServiceResponse)
async def toggle_clinic_service_status(
    clinic_id: int,
    service_id: int,
    status_data: dict,
    db: Session = Depends(get_db)
):
    """
    Activer/désactiver un service d'une clinique
    """
    try:
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.organisation_id == clinic_id
        ).first()
        
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        
        # Mettre à jour le statut
        service.est_actif = status_data.get("est_actif", True)
        db.commit()
        db.refresh(service)
        
        return ServiceResponse.model_validate(service)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors du changement de statut du service {service_id} de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clinics/{clinic_id}/services/stats")
async def get_clinic_service_stats(
    clinic_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques des services d'une clinique
    """
    try:
        # Compter les services
        total_services = db.query(Service).filter(Service.organisation_id == clinic_id).count()
        services_actifs = db.query(Service).filter(
            Service.organisation_id == clinic_id,
            Service.est_actif == True
        ).count()
        services_inactifs = total_services - services_actifs
        
        # Services récents (limité à 5)
        services_recents = db.query(Service).filter(
            Service.organisation_id == clinic_id,
            Service.est_actif == True
        ).order_by(Service.date_creation.desc()).limit(5).all()
        
        # Convertir les services récents
        services_recents_response = []
        for service in services_recents:
            services_recents_response.append(ServiceResponse.model_validate(service))
        
        return {
            "total_services": total_services,
            "services_actifs": services_actifs,
            "services_inactifs": services_inactifs,
            "repartition_par_categorie": {},  # À implémenter si nécessaire
            "services_recents": services_recents_response
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des stats des services de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clinics/{clinic_id}/services/search")
async def search_clinic_services(
    clinic_id: int,
    q: str = Query(..., description="Terme de recherche"),
    limit: int = Query(10, description="Nombre maximum de résultats"),
    db: Session = Depends(get_db)
):
    """
    Rechercher des services dans une clinique
    """
    try:
        services = db.query(Service).filter(
            Service.organisation_id == clinic_id,
            Service.est_actif == True,
            (Service.nom.ilike(f"%{q}%") | Service.code_service.ilike(f"%{q}%"))
        ).limit(limit).all()
        
        # Convertir les objets SQLAlchemy en schémas Pydantic
        services_response = []
        for service in services:
            services_response.append(ServiceResponse.model_validate(service))
        
        return services_response
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la recherche des services de la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clinics/{clinic_id}/services/validate-code")
async def validate_clinic_service_code(
    clinic_id: int,
    code_service: str = Query(..., description="Code de service à valider"),
    exclude_id: Optional[int] = Query(None, description="ID à exclure de la validation"),
    db: Session = Depends(get_db)
):
    """
    Valider l'unicité d'un code de service dans une clinique
    """
    try:
        query = db.query(Service).filter(
            Service.organisation_id == clinic_id,
            Service.code_service == code_service
        )
        
        if exclude_id:
            query = query.filter(Service.id != exclude_id)
        
        existing_service = query.first()
        
        return {
            "is_valid": existing_service is None,
            "message": "Code de service déjà utilisé" if existing_service else "Code de service disponible"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation du code de service pour la clinique {clinic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 