#!/usr/bin/env python3
"""
CONFIGURATION - HealthCare AI Architecture ODYSSEE
Configuration centralisée inspirée d'ODYSSEE avec variables d'environnement
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
from typing import List, Optional
from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings
from functools import lru_cache

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
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
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
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
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