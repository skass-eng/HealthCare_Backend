#!/usr/bin/env python3
"""
PAGE PRINCIPALE - HealthCare AI
Point d'entrée unifié avec organisation des APIs par sections
Version: 1.0.0 - Architecture Organisée
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports des APIs existantes
from api_unified_router import app as api_unified_router
from api_pages_router import app as api_pages_router
from api_dashboard_unified import app as api_dashboard_unified_router

# Imports de base de données
from database_unified import SessionLocal, engine
from models_unified import Base

# ==================== STARTUP / SHUTDOWN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application principale"""
    logger.info("🚀 Démarrage de HealthCare AI - Application Principale")
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Base de données initialisée")
    
    yield
    
    logger.info("🛑 Arrêt de HealthCare AI")

# ==================== APPLICATION PRINCIPALE ====================

app = FastAPI(
    title="HealthCare AI - Application Principale",
    description="Application unifiée pour la gestion des plaintes médicales avec organisation par sections",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DEPENDENCY ====================

def get_db() -> Session:
    """Dépendance pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== PAGE D'ACCUEIL ====================

@app.get("/", response_class=HTMLResponse)
async def page_accueil():
    """Page d'accueil avec navigation vers toutes les sections"""
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HealthCare AI - Application Principale</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 40px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 3em;
                margin: 0;
                background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
                margin: 10px 0;
            }
            .sections-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-top: 40px;
            }
            .section-card {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 15px;
                padding: 25px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .section-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            }
            .section-title {
                font-size: 1.5em;
                font-weight: bold;
                margin-bottom: 15px;
                color: #4ecdc4;
            }
            .section-description {
                margin-bottom: 20px;
                opacity: 0.9;
                line-height: 1.6;
            }
            .api-links {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .api-link {
                display: inline-block;
                padding: 10px 15px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                transition: background 0.3s ease;
                font-size: 0.9em;
            }
            .api-link:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: scale(1.02);
            }
            .status-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-online {
                background: #4ecdc4;
            }
            .status-offline {
                background: #ff6b6b;
            }
            .footer {
                text-align: center;
                margin-top: 40px;
                opacity: 0.7;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 HealthCare AI</h1>
                <p>Application Principale - Gestion des Plaintes Médicales</p>
                <p>API Unifiée avec Organisation par Sections</p>
            </div>
            
            <div class="sections-grid">
                <!-- Section 1: Gestion des Plaintes -->
                <div class="section-card">
                    <div class="section-title">📋 Gestion des Plaintes</div>
                    <div class="section-description">
                        APIs pour la création, consultation et gestion des plaintes médicales
                    </div>
                    <div class="api-links">
                        <a href="/api/v1/plaintes" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Liste des Plaintes
                        </a>
                        <a href="/api/v1/plaintes/en-cours" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Plaintes en Cours
                        </a>
                        <a href="/api/v1/plaintes/traitees" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Plaintes Traitées
                        </a>
                        <a href="/api/v1/plaintes/en-attente" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Plaintes en Attente
                        </a>
                    </div>
                </div>

                <!-- Section 2: Statistiques et Analytics -->
                <div class="section-card">
                    <div class="section-title">📊 Statistiques et Analytics</div>
                    <div class="section-description">
                        KPIs, métriques et analyses de performance du système
                    </div>
                    <div class="api-links">
                        <a href="/api/v1/statistiques" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Statistiques Générales
                        </a>
                        <a href="/api/v1/statistiques/tendances" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Tendances
                        </a>
                        <a href="/api/v1/suggestions-ia" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Suggestions IA
                        </a>
                        <a href="/api/v1/suggestions/par-service" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Suggestions par Service
                        </a>
                    </div>
                </div>

                <!-- Section 3: Gestion des Services -->
                <div class="section-card">
                    <div class="section-title">🏥 Gestion des Services</div>
                    <div class="section-description">
                        Configuration et gestion des services médicaux
                    </div>
                    <div class="api-links">
                        <a href="/api/v1/services" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Liste des Services
                        </a>
                        <a href="/api/v1/organisations" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Organisations
                        </a>
                        <a href="/api/v1/utilisateurs" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Utilisateurs
                        </a>
                    </div>
                </div>

                <!-- Section 4: Dashboard et Pages -->
                <div class="section-card">
                    <div class="section-title">📱 Dashboard et Pages</div>
                    <div class="section-description">
                        Interfaces utilisateur et dashboards spécialisés avec filtres
                    </div>
                    <div class="api-links">
                        <a href="/api/v1/dashboard/statistiques" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Dashboard Unifié
                        </a>
                        <a href="/api/v1/dashboard/filtres-disponibles" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Filtres Disponibles
                        </a>
                        <a href="/api/v1/dashboard/plaintes/urgentes" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Plaintes Urgentes
                        </a>
                        <a href="/api/v2/pages/analytics" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Analytics Avancées
                        </a>
                    </div>
                </div>

                <!-- Section 5: Audit et Sécurité -->
                <div class="section-card">
                    <div class="section-title">🔒 Audit et Sécurité</div>
                    <div class="section-description">
                        Traçabilité et sécurité des opérations
                    </div>
                    <div class="api-links">
                        <a href="/api/v1/audit" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Logs d'Audit
                        </a>
                        <a href="/api/v1/health" class="api-link">
                            <span class="status-indicator status-online"></span>
                            État du Système
                        </a>
                    </div>
                </div>

                <!-- Section 6: Documentation -->
                <div class="section-card">
                    <div class="section-title">📚 Documentation</div>
                    <div class="section-description">
                        Documentation interactive des APIs
                    </div>
                    <div class="api-links">
                        <a href="/docs" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Documentation Swagger
                        </a>
                        <a href="/redoc" class="api-link">
                            <span class="status-indicator status-online"></span>
                            Documentation ReDoc
                        </a>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>HealthCare AI - Application Principale v1.0.0</p>
                <p>Démarré le """ + datetime.now().strftime("%d/%m/%Y à %H:%M:%S") + """</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ==================== ROUTES DE SANTÉ ====================

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'application principale"""
    return {
        "status": "healthy",
        "application": "HealthCare AI - Application Principale",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api_unified": "online",
            "api_pages": "online", 
            "api_dashboard": "online",
            "api_dashboard_simple": "online"
        }
    }

@app.get("/status")
async def status_complet():
    """Statut complet de tous les services"""
    return {
        "application": "HealthCare AI - Application Principale",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api_unified": {
                "status": "online",
                "port": 6000,
                "endpoints": "/api/v1/*"
            },
            "api_pages": {
                "status": "online", 
                "port": 8002,
                "endpoints": "/api/v2/pages/*"
            },
            "api_dashboard_unified": {
                "status": "online",
                "port": 6000,
                "endpoints": "/api/v1/dashboard/*"
            }
        },
        "database": "postgresql",
        "features": [
            "Gestion des Plaintes",
            "Statistiques et Analytics", 
            "Gestion des Services",
            "Dashboard et Pages",
            "Audit et Sécurité"
        ]
    }

# ==================== INCLUSION DES APIS ====================

# Inclure toutes les routes de l'API unifiée avec préfixe
app.include_router(api_unified_router, prefix="/api/v1", tags=["API Unifiée"])

# Inclure les routes de l'API pages avec préfixe
app.include_router(api_pages_router, prefix="/api/v2/pages", tags=["API Pages"])

# Inclure les routes du dashboard unifié avec préfixe
app.include_router(api_dashboard_unified_router, prefix="/api/v1/dashboard", tags=["Dashboard Unifié"])

# ==================== ROUTES DE NAVIGATION ====================

@app.get("/navigation")
async def navigation_guide():
    """Guide de navigation vers toutes les sections"""
    return {
        "application": "HealthCare AI - Application Principale",
        "sections": {
            "gestion_plaintes": {
                "titre": "📋 Gestion des Plaintes",
                "description": "APIs pour la création, consultation et gestion des plaintes médicales",
                "endpoints": {
                    "liste_plaintes": "/api/v1/plaintes",
                    "plaintes_en_cours": "/api/v1/plaintes/en-cours",
                    "plaintes_traitees": "/api/v1/plaintes/traitees",
                    "plaintes_en_attente": "/api/v1/plaintes/en-attente"
                }
            },
            "statistiques_analytics": {
                "titre": "📊 Statistiques et Analytics",
                "description": "KPIs, métriques et analyses de performance du système",
                "endpoints": {
                    "statistiques_generales": "/api/v1/statistiques",
                    "tendances": "/api/v1/statistiques/tendances",
                    "suggestions_ia": "/api/v1/suggestions-ia",
                    "suggestions_par_service": "/api/v1/suggestions/par-service"
                }
            },
            "gestion_services": {
                "titre": "🏥 Gestion des Services",
                "description": "Configuration et gestion des services médicaux",
                "endpoints": {
                    "services": "/api/v1/services",
                    "organisations": "/api/v1/organisations",
                    "utilisateurs": "/api/v1/utilisateurs"
                }
            },
            "dashboard_pages": {
                "titre": "📱 Dashboard et Pages",
                "description": "Interfaces utilisateur et dashboards spécialisés avec filtres",
                "endpoints": {
                    "dashboard_unifie": "/api/v1/dashboard/statistiques",
                    "filtres_disponibles": "/api/v1/dashboard/filtres-disponibles",
                    "plaintes_urgentes": "/api/v1/dashboard/plaintes/urgentes",
                    "plaintes_en_cours": "/api/v1/dashboard/plaintes/en-cours",
                    "plaintes_traitees": "/api/v1/dashboard/plaintes/traitees",
                    "plaintes_en_attente": "/api/v1/dashboard/plaintes/en-attente",
                    "analytics": "/api/v2/pages/analytics"
                }
            },
            "audit_securite": {
                "titre": "🔒 Audit et Sécurité",
                "description": "Traçabilité et sécurité des opérations",
                "endpoints": {
                    "audit": "/api/v1/audit",
                    "health": "/api/v1/health"
                }
            },
            "documentation": {
                "titre": "📚 Documentation",
                "description": "Documentation interactive des APIs",
                "endpoints": {
                    "swagger": "/docs",
                    "redoc": "/redoc"
                }
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔═══════════════════════════════════════════════╗
    ║        🏥 HealthCare AI - Application         ║
    ║              Principale                       ║
    ║                                               ║
    ║  ✅ API Unifiée                              ║
    ║  ✅ Organisation par Sections                ║
    ║  ✅ Navigation Intuitive                     ║
    ║  ✅ Documentation Complète                   ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main_app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    ) 