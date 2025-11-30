#!/usr/bin/env python3
"""
AUTHENTIFICATION API - HealthCare AI Architecture ODYSSEE
Endpoints d'authentification inspirés d'ODYSSEE
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from ..core.auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from ..core.config import settings
from ..db.database import get_db
from shared.models import User, UserRole, Organisation

router = APIRouter()

# ==================== SCHÉMAS POUR L'INSCRIPTION ====================

class RegisterRequest(BaseModel):
    """Schéma pour l'inscription d'un nouvel utilisateur"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")
    name: str = Field(..., min_length=2, description="Nom complet")

class RegisterResponse(BaseModel):
    """Réponse après inscription réussie"""
    success: bool
    message: str
    user: dict
    access_token: str
    token_type: str = "bearer"

# ==================== ENDPOINTS ====================

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint d'inscription d'un nouvel utilisateur
    """
    # Vérifier si l'email existe déjà
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cet email existe déjà"
        )
    
    # Récupérer ou créer l'organisation par défaut
    default_org = db.query(Organisation).first()
    if not default_org:
        # Créer une organisation par défaut si elle n'existe pas
        default_org = Organisation(
            nom="Organisation par défaut",
            code_etablissement="ORG001"
        )
        db.add(default_org)
        db.commit()
        db.refresh(default_org)
    
    # Séparer le nom en prénom et nom de famille
    name_parts = request.name.strip().split(' ', 1)
    prenom = name_parts[0]
    nom = name_parts[1] if len(name_parts) > 1 else name_parts[0]
    
    # Créer le nouvel utilisateur
    new_user = User(
        email=request.email,
        mot_de_passe_hash=get_password_hash(request.password),
        nom=nom,
        prenom=prenom,
        nom_complet=request.name,
        type_utilisateur=UserRole.UTILISATEUR,
        organisation_id=default_org.id,
        est_actif=True,
        email_verifie=False,
        date_creation=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Créer le token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=access_token_expires
    )
    
    return RegisterResponse(
        success=True,
        message="Inscription réussie",
        user={
            "id": new_user.id,
            "email": new_user.email,
            "nom_complet": new_user.nom_complet,
            "type_utilisateur": new_user.type_utilisateur.value if new_user.type_utilisateur else None
        },
        access_token=access_token
    )

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