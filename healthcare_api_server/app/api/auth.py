#!/usr/bin/env python3
"""
AUTHENTIFICATION API - HealthCare AI Architecture ODYSSEE
Endpoints d'authentification inspirés d'ODYSSEE
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from ..core.auth import authenticate_user, create_access_token, get_current_user
from ..core.config import settings
from ..db.database import get_db
from shared.models import User

router = APIRouter()

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint de connexion (comme ODYSSEE auth)
    """
    # Authentifier l'utilisateur (username = email dans notre cas)
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte utilisateur inactif"
        )
    
    # Créer le token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nom_complet": user.nom_complet,
            "type_utilisateur": user.type_utilisateur.value if user.type_utilisateur else None
        }
    }

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtenir les informations de l'utilisateur connecté
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "nom_complet": current_user.nom_complet,
        "type_utilisateur": current_user.type_utilisateur.value if current_user.type_utilisateur else None,
        "est_actif": current_user.est_actif,
        "email_verifie": current_user.email_verifie
    }

@router.post("/logout")
async def logout():
    """
    Endpoint de déconnexion (pour compatibilité)
    """
    return {"message": "Déconnexion réussie"} 