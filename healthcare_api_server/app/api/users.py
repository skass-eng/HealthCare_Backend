#!/usr/bin/env python3
"""
API UTILISATEURS - HealthCare AI Architecture ODYSSEE
Gestion des utilisateurs du système
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging
from datetime import datetime

from ..db.database import get_db
from shared.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

# ==================== ENDPOINTS PRINCIPAUX ====================

@router.get("/")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    type_utilisateur: Optional[str] = Query(None),
    est_actif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des utilisateurs avec pagination et filtres
    """
    try:
        # Construire la requête de base
        query = db.query(User).filter(User.date_suppression.is_(None))
        
        # Appliquer les filtres
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.nom.ilike(search_term)) |
                (User.prenom.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.fonction.ilike(search_term))
            )
        
        if type_utilisateur:
            query = query.filter(User.type_utilisateur == type_utilisateur)
        
        if est_actif is not None:
            query = query.filter(User.est_actif == est_actif)
        
        # Compter le total
        total = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()
        
        # Formater la réponse
        items = []
        for user in users:
            items.append({
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "nom_complet": user.nom_complet,
                "email": user.email,
                "telephone": user.telephone,
                "telephone_mobile": user.telephone_mobile,
                "type_utilisateur": user.type_utilisateur.value if user.type_utilisateur else None,
                "fonction": user.fonction,
                "specialite": user.specialite,
                "numero_rpps": user.numero_rpps,
                "est_actif": user.est_actif,
                "email_verifie": user.email_verifie,
                "date_creation": user.date_creation.isoformat() if user.date_creation else None,
                "date_modification": user.date_modification.isoformat() if user.date_modification else None,
                "permissions": user.permissions or {},
                "configuration": user.configuration or {}
            })
        
        return {
            "success": True,
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des utilisateurs: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/types")
async def get_user_types():
    """
    Récupérer les types d'utilisateurs disponibles (endpoint public)
    """
    try:
        types = []
        for role in UserRole:
            types.append({
                "value": role.value,
                "label": role.value.replace("_", " ").title(),
                "description": f"Rôle {role.value.lower()}"
            })
        
        return {
            "success": True,
            "data": types
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des types: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/validate-email")
async def validate_email(
    email: str = Query(..., description="Email à valider"),
    exclude_id: Optional[int] = Query(None, description="ID de l'utilisateur à exclure"),
    db: Session = Depends(get_db)
):
    """
    Valider un email (vérifier s'il est unique)
    """
    try:
        query = db.query(User).filter(
            User.email == email,
            User.date_suppression.is_(None)
        )
        
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        
        existing_user = query.first()
        
        return {
            "success": True,
            "data": {
                "is_valid": existing_user is None,
                "message": "Email déjà utilisé" if existing_user else "Email disponible"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation de l'email: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/stats")
async def get_user_stats(
    db: Session = Depends(get_db)
):
    """
    Récupérer les statistiques des utilisateurs
    """
    try:
        # Statistiques de base
        total_users = db.query(func.count(User.id)).filter(
            User.date_suppression.is_(None)
        ).scalar()
        
        return {
            "success": True,
            "data": {
                "total_users": total_users,
                "message": "Statistiques simplifiées"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer un utilisateur par son ID
    """
    try:
        user = db.query(User).filter(
            User.id == user_id,
            User.date_suppression.is_(None)
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "nom_complet": user.nom_complet,
                "email": user.email,
                "telephone": user.telephone,
                "telephone_mobile": user.telephone_mobile,
                "type_utilisateur": user.type_utilisateur.value if user.type_utilisateur else None,
                "fonction": user.fonction,
                "specialite": user.specialite,
                "numero_rpps": user.numero_rpps,
                "est_actif": user.est_actif,
                "email_verifie": user.email_verifie,
                "date_creation": user.date_creation.isoformat() if user.date_creation else None,
                "date_modification": user.date_modification.isoformat() if user.date_modification else None,
                "permissions": user.permissions or {},
                "configuration": user.configuration or {}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/")
async def create_user(
    user_data: dict,
    db: Session = Depends(get_db)
):
    """
    Créer un nouvel utilisateur
    """
    try:
        # Validation des champs obligatoires
        if not user_data.get("nom"):
            raise HTTPException(status_code=400, detail="Le nom est obligatoire")
        
        if not user_data.get("prenom"):
            raise HTTPException(status_code=400, detail="Le prénom est obligatoire")
        
        if not user_data.get("email"):
            raise HTTPException(status_code=400, detail="L'email est obligatoire")
        
        if not user_data.get("mot_de_passe"):
            raise HTTPException(status_code=400, detail="Le mot de passe est obligatoire")
        
        if not user_data.get("type_utilisateur"):
            raise HTTPException(status_code=400, detail="Le type d'utilisateur est obligatoire")
        
        # Vérifier que l'email est unique
        existing_user = db.query(User).filter(
            User.email == user_data["email"],
            User.date_suppression.is_(None)
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Un utilisateur avec cet email existe déjà")
        
        # Valider le type d'utilisateur
        try:
            user_type = UserRole(user_data["type_utilisateur"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Type d'utilisateur invalide")
        
        # Hasher le mot de passe
        from ..core.auth import get_password_hash
        hashed_password = get_password_hash(user_data["mot_de_passe"])
        
        # Créer l'utilisateur
        # Organisation par défaut si non fournie
        organisation_id = user_data.get("organisation_id", 1)
        
        new_user = User(
            nom=user_data["nom"],
            prenom=user_data["prenom"],
            nom_complet=f"{user_data['prenom']} {user_data['nom']}",
            email=user_data["email"],
            mot_de_passe_hash=hashed_password,
            organisation_id=organisation_id,  # Organisation par défaut
            service_id=user_data.get("service_id"),
            telephone=user_data.get("telephone"),
            telephone_mobile=user_data.get("telephone_mobile"),
            type_utilisateur=user_type,
            fonction=user_data.get("fonction"),
            specialite=user_data.get("specialite"),
            numero_rpps=user_data.get("numero_rpps"),
            permissions=user_data.get("permissions", {}),
            configuration=user_data.get("configuration", {}),
            est_actif=True,
            email_verifie=False,
            date_creation=datetime.now()  # Date de création manuelle
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✅ Utilisateur créé: {new_user.nom_complet} (ID: {new_user.id})")
        
        return {
            "success": True,
            "data": {
                "id": new_user.id,
                "nom": new_user.nom,
                "prenom": new_user.prenom,
                "nom_complet": new_user.nom_complet,
                "email": new_user.email,
                "telephone": new_user.telephone,
                "telephone_mobile": new_user.telephone_mobile,
                "type_utilisateur": new_user.type_utilisateur.value,
                "fonction": new_user.fonction,
                "specialite": new_user.specialite,
                "numero_rpps": new_user.numero_rpps,
                "est_actif": new_user.est_actif,
                "email_verifie": new_user.email_verifie,
                "date_creation": new_user.date_creation.isoformat() if new_user.date_creation else None,
                "date_modification": new_user.date_modification.isoformat() if new_user.date_modification else None,
                "permissions": new_user.permissions or {},
                "configuration": new_user.configuration or {}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la création de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {e}")

@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: dict,
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un utilisateur existant
    """
    try:
        # Récupérer l'utilisateur
        user = db.query(User).filter(
            User.id == user_id,
            User.date_suppression.is_(None)
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Vérifier que l'email est unique si modifié
        if user_data.get("email") and user_data["email"] != user.email:
            existing_user = db.query(User).filter(
                User.email == user_data["email"],
                User.id != user_id,
                User.date_suppression.is_(None)
            ).first()
            
            if existing_user:
                raise HTTPException(status_code=400, detail="Un utilisateur avec cet email existe déjà")
        
        # Mettre à jour les champs
        if "nom" in user_data:
            user.nom = user_data["nom"]
        
        if "prenom" in user_data:
            user.prenom = user_data["prenom"]
            user.nom_complet = f"{user.prenom} {user.nom}"
        
        if "email" in user_data:
            user.email = user_data["email"]
        
        if "telephone" in user_data:
            user.telephone = user_data["telephone"]
        
        if "telephone_mobile" in user_data:
            user.telephone_mobile = user_data["telephone_mobile"]
        
        if "fonction" in user_data:
            user.fonction = user_data["fonction"]
        
        if "specialite" in user_data:
            user.specialite = user_data["specialite"]
        
        if "numero_rpps" in user_data:
            user.numero_rpps = user_data["numero_rpps"]
        
        if "permissions" in user_data:
            user.permissions = user_data["permissions"]
        
        if "configuration" in user_data:
            user.configuration = user_data["configuration"]
        
        # Mettre à jour le mot de passe si fourni
        if user_data.get("mot_de_passe"):
            from ..core.auth import get_password_hash
            user.mot_de_passe_hash = get_password_hash(user_data["mot_de_passe"])
        
        # Mettre à jour le type d'utilisateur si fourni
        if user_data.get("type_utilisateur"):
            try:
                user.type_utilisateur = UserRole(user_data["type_utilisateur"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Type d'utilisateur invalide")
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Utilisateur modifié: {user.nom_complet} (ID: {user.id})")
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "nom_complet": user.nom_complet,
                "email": user.email,
                "telephone": user.telephone,
                "telephone_mobile": user.telephone_mobile,
                "type_utilisateur": user.type_utilisateur.value if user.type_utilisateur else None,
                "fonction": user.fonction,
                "specialite": user.specialite,
                "numero_rpps": user.numero_rpps,
                "est_actif": user.est_actif,
                "email_verifie": user.email_verifie,
                "date_creation": user.date_creation.isoformat() if user.date_creation else None,
                "date_modification": user.date_modification.isoformat() if user.date_modification else None,
                "permissions": user.permissions or {},
                "configuration": user.configuration or {}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la modification de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprimer un utilisateur (soft delete)
    """
    try:
        # Récupérer l'utilisateur
        user = db.query(User).filter(
            User.id == user_id,
            User.date_suppression.is_(None)
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Note: Suppression de la vérification de l'utilisateur actuel car plus de protection
        
        # Soft delete
        user.date_suppression = datetime.now()
        user.est_actif = False
        
        db.commit()
        
        logger.info(f"✅ Utilisateur supprimé: {user.nom_complet} (ID: {user.id})")
        
        return {
            "success": True,
            "message": "Utilisateur supprimé avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la suppression de l'utilisateur: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# Export des routers
__all__ = ["router"] 