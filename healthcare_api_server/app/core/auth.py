#!/usr/bin/env python3
"""
AUTHENTIFICATION - HealthCare AI Architecture ODYSSEE
Système d'authentification inspiré d'ODYSSEE avec FastAPI-Users
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging

from ..db.database import get_db
from shared.models import User, UserRole
from ..core.config import settings

logger = logging.getLogger(__name__)

# Configuration du hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration JWT
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe.

    Retourne False (au lieu de lever) si le hash est NULL/malformé,
    afin que le login renvoie un 401 propre plutôt qu'un 500.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Echec verification mot de passe (hash invalide/manquant): {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hacher un mot de passe"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Créer un token JWT d'accès (comme ODYSSEE)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """
    Créer un token JWT de rafraîchissement
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    Récupérer un utilisateur à partir d'un token JWT
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Convertir l'ID en entier (pas UUID)
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
        
    except (JWTError, ValueError) as e:
        logger.error(f"❌ Erreur validation token: {e}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dépendance pour récupérer l'utilisateur authentifié actuel (comme ODYSSEE)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les informations d'identification",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        user = await get_user_from_token(token, db)
        
        if user is None:
            raise credentials_exception
            
        if not user.est_actif:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Utilisateur inactif"
            )
        
        return user
        
    except JWTError:
        raise credentials_exception

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Vérifier que l'utilisateur est actif et vérifié
    """
    if not current_user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur inactif"
        )
    
    return current_user

# Système de permissions inspiré d'ODYSSEE

def require_role(required_roles: list[UserRole]):
    """
    Décorateur pour vérifier les rôles utilisateur
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.type_utilisateur not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes"
            )
        return current_user
    
    return role_checker

# Dépendances de rôles spécifiques

async def get_admin_user(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> User:
    """Utilisateur avec rôle admin"""
    return current_user

async def get_medical_user(
    current_user: User = Depends(require_role([
        UserRole.ADMIN, 
        UserRole.RESPONSABLE_QUALITE, 
        UserRole.MEDECIN,
        UserRole.INFIRMIER
    ]))
) -> User:
    """Utilisateur avec rôle médical"""
    return current_user

async def get_quality_user(
    current_user: User = Depends(require_role([
        UserRole.ADMIN, 
        UserRole.RESPONSABLE_QUALITE
    ]))
) -> User:
    """Utilisateur avec rôle qualité"""
    return current_user

# Fonctions utilitaires d'authentification

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authentifier un utilisateur avec email/mot de passe
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.mot_de_passe_hash):
        return None
    return user

def is_user_authorized(user: User, resource_type: str, resource_id: UUID, action: str) -> bool:
    """
    Vérifier les autorisations utilisateur sur une ressource (comme ODYSSEE)
    """
    # Logique d'autorisation basée sur les rôles et ressources
    
    # Les admins ont tous les droits
    if user.type_utilisateur == UserRole.ADMIN:
        return True
    
    # Les responsables qualité ont accès aux plaintes et analyses
    if user.type_utilisateur == UserRole.RESPONSABLE_QUALITE:
        if resource_type in ["plainte", "analyse"]:
            return True
    
    # Les médecins peuvent voir leurs plaintes et leurs services
    if user.type_utilisateur in [UserRole.MEDECIN, UserRole.INFIRMIER]:
        if resource_type == "plainte" and action in ["read", "create"]:
            return True
    
    # Les patients peuvent voir leurs propres plaintes
    if user.type_utilisateur == UserRole.PATIENT:
        if resource_type == "plainte" and action in ["read", "create"]:
            # Vérifier que c'est sa propre plainte
            return True
    
    return False

class AuthenticationError(Exception):
    """Erreur d'authentification personnalisée"""
    pass

class AuthorizationError(Exception):
    """Erreur d'autorisation personnalisée"""
    pass