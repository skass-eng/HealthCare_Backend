#!/usr/bin/env python3
"""
Script simplifié pour démarrer uniquement l'API server
"""

import uvicorn
import sys
import os

# Ajouter le chemin du projet au PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    print("🚀 Démarrage de l'API HealthCare...")
    print("📡 API Server: http://localhost:8000")
    print("📚 Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "healthcare_api_server.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[project_root]
    )
