#!/usr/bin/env python3
"""
CONFIGURATION - HealthCare AI Architecture ODYSSEE
Configuration centralisée inspirée d'ODYSSEE avec variables d'environnement
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import logging
from typing import List, Optional
from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings
from functools import lru_cache

logger = logging.getLogger(__name__)

# Valeur placeholder publique par défaut (NE PAS utiliser en production)
_SECRET_KEY_PLACEHOLDER = "your-secret-key-change-in-production"

class Settings(BaseSettings):
    """Configuration de l'application (inspirée d'ODYSSEE)"""
    
    # Configuration de base
    APP_NAME: str = "HealthCare AI - Architecture ODYSSEE"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Configuration du serveur API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Configuration CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://172.20.10.3:3000",  # Accès mobile/réseau local
        "http://127.0.0.1:3000",
        "http://192.168.1.151:3000",  # Accès réseau local WiFi
        "http://192.168.1.151:3001",
        "http://MI-W15XDCK3:3000",  # Accès via nom du PC
        "http://MI-W15XDCK3:3001",
        "http://mi-w15xdck3:3000",  # Nom en minuscules (au cas où)
        "http://mi-w15xdck3:3001",
        "https://healthcare.pulse-360.fr",  # Production - Frontend
        "https://api-healthcare.pulse-360.fr",  # Production - API
        "https://pulse-360.fr",  # Domaine principal
        "https://www.pulse-360.fr",  # WWW
    ]
    
    # Autoriser tous les domaines ngrok (pour le développement/démo)
    CORS_ALLOW_ALL_ORIGINS: bool = True  # Active pour supporter ngrok
    
    # Configuration base de données PostgreSQL (obligatoire comme ODYSSEE)
    DATABASE_URL: PostgresDsn = "postgresql://postgres:242261@localhost:5430/hospital_complaints"
    
    # Configuration Redis (pour Celery et WebSockets)
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    
    # Configuration Celery (inspirée des workers ODYSSEE)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ROUTES: dict = {
        'healthcare_worker_server.tasks.analyse_plainte.*': {'queue': 'analyses'},
        'healthcare_worker_server.tasks.sentiment.*': {'queue': 'sentiment'},
        'healthcare_worker_server.tasks.classification.*': {'queue': 'classification'},
    }
    
    # Configuration sécurité (comme ODYSSEE)
    # Lue depuis l'env SECRET_KEY si définie, sinon placeholder (comportement inchangé).
    SECRET_KEY: str = os.getenv("SECRET_KEY", _SECRET_KEY_PLACEHOLDER)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Configuration LLM (pour les analyses asynchrones)
    LLM_PROVIDER: str = "openai"  # openai, anthropic, ollama
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.1
    
    # Configuration stockage fichiers (comme ODYSSEE)
    STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".doc", ".docx", ".txt", ".jpg", ".png"]
    
    # Configuration WebSockets
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_MAX_CONNECTIONS: int = 1000
    
    # Configuration métier
    DELAI_REPONSE_STANDARD_JOURS: int = 30
    PRIORITES_AUTO_ENABLED: bool = True
    ANALYSES_AUTO_ENABLED: bool = True
    
    # Configuration monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    # Configuration email (pour notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permet les champs supplémentaires

@lru_cache()
def get_settings() -> Settings:
    """Retourne la configuration singleton (pattern ODYSSEE)"""
    return Settings()

# Instance globale
settings = get_settings()

# Avertissement clair au boot si la SECRET_KEY reste le placeholder public.
# (On NE fait PAS crasher l'app pour ne pas casser la démo.)
if settings.SECRET_KEY == _SECRET_KEY_PLACEHOLDER:
    logger.warning(
        "SECRET_KEY utilise la valeur placeholder publique par defaut. "
        "Definissez la variable d'environnement SECRET_KEY avant tout deploiement reel."
    )

# Configuration pour différents environnements
def get_database_url() -> str:
    """URL de base de données selon l'environnement"""
    if settings.ENVIRONMENT == "test":
        return settings.DATABASE_URL.replace("/healthcare_odyssee", "/healthcare_test")
    return str(settings.DATABASE_URL)

def get_redis_url() -> str:
    """URL Redis selon l'environnement"""
    return str(settings.REDIS_URL)

def is_development() -> bool:
    """Vérifie si on est en développement"""
    return settings.ENVIRONMENT == "development" or settings.DEBUG

def is_production() -> bool:
    """Vérifie si on est en production"""
    return settings.ENVIRONMENT == "production"