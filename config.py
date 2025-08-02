import os
from typing import List

class Settings:
    """Configuration de l'application"""
    
    # Configuration de base
    APP_NAME: str = "HealthCare AI - Gestion des Plaintes"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Configuration du serveur
    HOST: str = "0.0.0.0"
    PORT: int = 6000
    
    # Configuration CORS
    ALLOWED_ORIGINS: List[str] = ["*"]  # À restreindre en production
    
    # Configuration des dossiers
    UPLOAD_DIR: str = "./uploads"
    PROCESSED_DIR: str = "./processed"
    LOGS_DIR: str = "./logs"
    DATA_PLAINTES_DIR: str = "./data/plaintes"  # Nouveau dossier pour les plaintes
    
    # Configuration des fichiers
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf"]
    
    # Configuration RGPD
    DELAI_REPONSE_RGPD: int = 30  # jours
    
    # Services disponibles
    SERVICES_DISPONIBLES: List[str] = [
        "Cardiologie",
        "Urgences", 
        "Pédiatrie",
        "Chirurgie",
        "Radiologie",
        "Oncologie",
        "Neurologie",
        "Orthopédie"
    ]
    
    # Priorités disponibles
    PRIORITES_DISPONIBLES: List[str] = [
        "Urgent",
        "Élevé", 
        "Moyen",
        "Bas"
    ]
    
    # Status disponibles
    STATUS_DISPONIBLES: List[str] = [
        "en_attente",
        "en_cours",
        "traite",
        "clos",
        "archive"
    ]
    
    # Configuration LLM - Ollama par défaut car stable et gratuit
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # openai, anthropic, ollama
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")  # Utilise le modèle par défaut si vide
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")  # Clé API générique
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # URL personnalisée
    
    # Clés API spécifiques
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Configuration analyse - LLM ACTIVÉ avec Ollama par défaut (gratuit et local)
    USE_LLM_ANALYSIS: bool = os.getenv("USE_LLM_ANALYSIS", "True").lower() in ["true", "1", "yes"]
    FALLBACK_TO_BASIC_AI: bool = os.getenv("FALLBACK_TO_BASIC_AI", "True").lower() in ["true", "1", "yes"]
    
    # Configuration base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:242261@localhost:5430/hospital_complaints")
    
    # Répertoires de traitement
    DATA_TRAITES_DIR: str = "./data/traites"
    DATA_ECHECS_DIR: str = "./data/echecs"

    def get_llm_config(self) -> dict:
        """Obtenir la configuration LLM selon le provider sélectionné"""
        # FORCER OLLAMA CAR IL FONCTIONNE
        return {
            "provider": "ollama",
            "model": "mistral:instruct",  # Modèle confirmé disponible
            "api_key": None,
            "base_url": "http://localhost:11434"
        }
        
        # Code original (temporairement désactivé)
        # provider = self.LLM_PROVIDER.lower()
        # 
        # if provider == "openai":
        #     api_key = self.LLM_API_KEY or self.OPENAI_API_KEY
        #     return {
        #         "provider": "openai",
        #         "model": self.LLM_MODEL or None,
        #         "api_key": api_key,
        #         "base_url": self.LLM_BASE_URL or None
        #     }
        # elif provider == "anthropic":
        #     api_key = self.LLM_API_KEY or self.ANTHROPIC_API_KEY
        #     return {
        #         "provider": "anthropic", 
        #         "model": self.LLM_MODEL or None,
        #         "api_key": api_key,
        #         "base_url": None
        #     }
        # elif provider == "ollama":
        #     return {
        #         "provider": "ollama",
        #         "model": self.LLM_MODEL or None,
        #         "api_key": None,
        #         "base_url": self.LLM_BASE_URL or self.OLLAMA_BASE_URL
        #     }
        # else:
        #     raise ValueError(f"Provider LLM non supporté: {provider}")
    
    def create_directories(self):
        """Créer les répertoires nécessaires s'ils n'existent pas"""
        directories = [
            self.UPLOAD_DIR,
            self.PROCESSED_DIR,
            self.LOGS_DIR,
            self.DATA_PLAINTES_DIR,
            self.DATA_TRAITES_DIR,
            self.DATA_ECHECS_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Instance globale des paramètres
settings = Settings()

# Créer les répertoires au démarrage
settings.create_directories() 