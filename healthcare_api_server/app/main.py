#!/usr/bin/env python3
"""
API SERVER PRINCIPAL - HealthCare AI Architecture ODYSSEE
Serveur API inspiré d'ODYSSEE avec FastAPI, WebSockets et intégration Celery
Version: 1.0.0 - Architecture ODYSSEE
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from datetime import datetime
from typing import Optional

from .core.config import settings
from .db.database import init_database, close_database
from .api import plaintes_creation, plaintes_gestion, websockets, auth, healthcare_ai, users, services_kpi

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application (comme ODYSSEE)
    """
    logger.info("🚀 Démarrage du serveur API HealthCare AI - Architecture ODYSSEE")
    
    try:
        # Initialiser la base de données
        await init_database()
        logger.info("✅ Base de données initialisée")
        
        # Ici on pourrait ajouter d'autres initialisations
        # comme la vérification de la connexion Redis, etc.
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage: {e}")
        raise
    finally:
        logger.info("🛑 Arrêt du serveur API HealthCare AI")
        try:
            # Fermer proprement les connexions à la base de données
            await close_database()
            logger.info("✅ Connexions à la base de données fermées")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la fermeture de la base de données: {e}")

# Création de l'application FastAPI (inspirée d'ODYSSEE)
app = FastAPI(
    title=settings.APP_NAME,
    description="API pour la gestion des plaintes hospitalières avec architecture ODYSSEE",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configuration CORS (comme ODYSSEE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

# Routes de santé et monitoring
@app.get("/health")
async def health_check():
    """
    Vérification de l'état du serveur API (comme ODYSSEE)
    """
    return {
        "status": "healthy",
        "service": "healthcare_api_server",
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": settings.ENVIRONMENT
    }



@app.get("/")
async def root():
    """
    Page d'accueil de l'API
    """
    return {
        "message": "HealthCare AI - Architecture ODYSSEE",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Gestion des plaintes hospitalières",
            "Analyses LLM asynchrones",
            "Notifications temps réel",
            "API REST complète",
            "WebSockets pour monitoring"
        ]
    }

# Inclusion des routeurs (comme ODYSSEE structure)
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentification"]
)

# Routeurs séparés pour les plaintes
app.include_router(
    plaintes_creation.router,
    prefix="/api/v1",
    tags=["Plaintes - Création"]
)

app.include_router(
    plaintes_gestion.router,
    prefix="/api/v1",
    tags=["Plaintes - Gestion"]
)

app.include_router(
    healthcare_ai.router,
    prefix="/api/v1",
    tags=["Healthcare AI"]
)

app.include_router(
    services_kpi.router,
    prefix="/api/v1",
    tags=["Services KPI"]
)

app.include_router(
    users.router,
    prefix="/api/v1",
    tags=["Utilisateurs"]
)



app.include_router(
    websockets.router,
    tags=["WebSockets"]
)

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Gestionnaire d'erreurs global (comme ODYSSEE error handling)
    """
    logger.error(f"❌ Erreur non gérée: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "detail": str(exc) if settings.DEBUG else "Une erreur s'est produite",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Gestionnaire d'erreurs HTTP
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    print(f"""
    ╔═══════════════════════════════════════════════╗
    ║    🏥 HealthCare AI - Architecture ODYSSEE    ║
    ║                API Server                     ║
    ║                                               ║
    ║  ✅ FastAPI avec SQLAlchemy ORM              ║
    ║  ✅ WebSockets temps réel                    ║
    ║  ✅ Intégration Celery Workers               ║
    ║  ✅ Authentification JWT                     ║
    ║  ✅ Base PostgreSQL                          ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        loop="asyncio",
        timeout_graceful_shutdown=30
    )