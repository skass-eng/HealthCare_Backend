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
import json
from datetime import datetime
from typing import Optional
import socketio

from .core.config import settings
from .db.database import init_database, close_database
from .api import plaintes_creation, plaintes_gestion, websockets, auth, healthcare_ai, users, services_kpi, task_status, test_endpoint

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variables globales pour le listener Redis
_redis_listener_task = None
_redis_listener_started = False

# Listener Redis pour les notifications Celery -> Socket.IO
async def redis_pubsub_listener(sio_server):
    """
    Écoute les notifications Redis du worker Celery
    et les retransmet aux clients Socket.IO
    """
    import redis.asyncio as aioredis
    
    while True:
        try:
            redis_client = aioredis.Redis(host='localhost', port=6379, db=0)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe('websocket_notifications')
            
            logger.info("📡 Redis PubSub listener démarré - Écoute du canal 'websocket_notifications'")
            
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        event_type = data.get('event')
                        event_data = data.get('data', {})
                        
                        logger.info(f"📨 Message Redis reçu: {event_type}")
                        
                        # Émettre à tous les clients Socket.IO
                        await sio_server.emit(event_type, event_data)
                        
                        # Émettre aussi à la room spécifique de la tâche si task_id présent
                        task_id = event_data.get('task_id')
                        if task_id:
                            await sio_server.emit(event_type, event_data, room=f'task_{task_id}')
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Erreur parsing message Redis: {e}")
                    except Exception as e:
                        logger.error(f"❌ Erreur émission Socket.IO: {e}")
                        
                await asyncio.sleep(0.1)  # Petite pause pour ne pas surcharger
                        
        except asyncio.CancelledError:
            logger.info("📡 Redis PubSub listener arrêté")
            break
        except Exception as e:
            logger.error(f"❌ Erreur Redis PubSub: {e}")
            await asyncio.sleep(5)  # Réessayer après un délai

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application (comme ODYSSEE)
    """
    global _redis_listener_task, _redis_listener_started
    
    logger.info("🚀 Démarrage du serveur API HealthCare AI - Architecture ODYSSEE")
    
    try:
        # Initialiser la base de données
        await init_database()
        logger.info("✅ Base de données initialisée")
        
        # Démarrer le listener Redis (sera démarré après la création de sio)
        # Note: Le listener sera démarré après la création du serveur Socket.IO
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage: {e}")
        raise
    finally:
        logger.info("🛑 Arrêt du serveur API HealthCare AI")
        
        # Arrêter le listener Redis
        if _redis_listener_task:
            _redis_listener_task.cancel()
            try:
                await _redis_listener_task
            except asyncio.CancelledError:
                pass
        
        try:
            # Fermer proprement les connexions à la base de données
            await close_database()
            logger.info("✅ Connexions à la base de données fermées")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la fermeture de la base de données: {e}")

# Création du serveur Socket.IO (compatible avec socket.io-client du frontend)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10 * 1024 * 1024,  # 10MB pour les gros fichiers
)

# Création de l'application FastAPI (inspirée d'ODYSSEE)
fastapi_app = FastAPI(
    title=settings.APP_NAME,
    description="API pour la gestion des plaintes hospitalières avec architecture ODYSSEE",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Monter FastAPI sur Socket.IO ASGI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ, auth=None):
    """Connexion d'un client Socket.IO"""
    global _redis_listener_task, _redis_listener_started
    
    logger.info(f"✅ Client Socket.IO connecté: {sid}")
    # Stocker le token si fourni
    if auth and 'token' in auth:
        await sio.save_session(sid, {'token': auth['token']})
    await sio.emit('connected', {'message': 'Connexion établie', 'sid': sid}, to=sid)
    
    # Démarrer le listener Redis au premier connect (si pas déjà démarré)
    if not _redis_listener_started:
        _redis_listener_started = True
        _redis_listener_task = asyncio.create_task(redis_pubsub_listener(sio))
        logger.info("🚀 Redis PubSub listener lancé")

@sio.event
async def disconnect(sid):
    """Déconnexion d'un client Socket.IO"""
    logger.info(f"📡 Client Socket.IO déconnecté: {sid}")

@sio.event
async def subscribe_task(sid, data):
    """S'abonner aux mises à jour d'une tâche"""
    task_id = data.get('task_id')
    if task_id:
        await sio.enter_room(sid, f'task_{task_id}')
        logger.info(f"📝 Client {sid} abonné à la tâche {task_id}")
        await sio.emit('subscribed', {'task_id': task_id}, to=sid)

@sio.event
async def unsubscribe_task(sid, data):
    """Se désabonner d'une tâche"""
    task_id = data.get('task_id')
    if task_id:
        await sio.leave_room(sid, f'task_{task_id}')
        logger.info(f"📝 Client {sid} désabonné de la tâche {task_id}")

@sio.event
async def subscribe_extraction(sid, data):
    """S'abonner aux mises à jour d'une tâche d'extraction PDF/Image"""
    task_id = data.get('task_id')
    if task_id:
        await sio.enter_room(sid, f'task_{task_id}')
        logger.info(f"📄 Client {sid} abonné à l'extraction {task_id}")
        await sio.emit('extraction_subscribed', {'task_id': task_id}, to=sid)

@sio.event
async def unsubscribe_extraction(sid, data):
    """Se désabonner d'une tâche d'extraction"""
    task_id = data.get('task_id')
    if task_id:
        await sio.leave_room(sid, f'task_{task_id}')
        logger.info(f"📄 Client {sid} désabonné de l'extraction {task_id}")

# Exporter le serveur Socket.IO pour utilisation dans d'autres modules
def get_socketio_server():
    return sio

# Configuration CORS (comme ODYSSEE) - Doit être AVANT les autres middlewares
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporairement autoriser toutes les origines
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware de logging des requêtes
@fastapi_app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    
    # Gérer les requêtes OPTIONS pour CORS preflight
    if request.method == "OPTIONS":
        response = JSONResponse(content={}, status_code=200)
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    try:
        response = await call_next(request)
    except Exception as e:
        # En cas d'erreur, retourner une réponse JSON avec headers CORS
        logger.error(f"❌ Erreur non gérée: {e}")
        response = JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    process_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

# Routes de santé et monitoring
@fastapi_app.get("/health")
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



@fastapi_app.get("/")
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
fastapi_app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentification"]
)

# Routeurs séparés pour les plaintes
fastapi_app.include_router(
    plaintes_creation.router,
    prefix="/api/v1",
    tags=["Plaintes - Création"]
)

fastapi_app.include_router(
    plaintes_gestion.router,
    prefix="/api/v1",
    tags=["Plaintes - Gestion"]
)

fastapi_app.include_router(
    healthcare_ai.router,
    prefix="/api/v1",
    tags=["Healthcare AI"]
)

fastapi_app.include_router(
    services_kpi.router,
    prefix="/api/v1",
    tags=["Services KPI"]
)

fastapi_app.include_router(
    users.router,
    prefix="/api/v1",
    tags=["Utilisateurs"]
)

# Routeur pour le statut des tâches
fastapi_app.include_router(
    task_status.router,
    tags=["Statut des Tâches"]
)

fastapi_app.include_router(
    websockets.router,
    tags=["WebSockets"]
)

# Routeur de test pour l'intégration modulaire
fastapi_app.include_router(
    test_endpoint.router,
    prefix="/api/v1",
    tags=["Test - API Modulaire"]
)

# Gestionnaire d'erreurs global
@fastapi_app.exception_handler(Exception)
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

@fastapi_app.exception_handler(HTTPException)
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
    ║  ✅ Socket.IO temps réel                     ║
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