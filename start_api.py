#!/usr/bin/env python3
"""
DÉMARRAGE API SERVER - HealthCare AI
Script dédié au lancement du serveur API FastAPI
Usage: python start_api.py [--port PORT] [--reload]
"""

import os
import sys
import argparse

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description='Démarrer le serveur API HealthCare AI')
    parser.add_argument('--port', type=int, default=8000, help='Port du serveur (défaut: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host du serveur (défaut: 0.0.0.0)')
    parser.add_argument('--reload', action='store_true', help='Activer le rechargement automatique')
    args = parser.parse_args()

    print("=" * 60)
    print("🏥 HealthCare AI - API Server")
    print("=" * 60)
    print(f"📡 Host: {args.host}")
    print(f"🔌 Port: {args.port}")
    print(f"🔄 Reload: {'Activé' if args.reload else 'Désactivé'}")
    print(f"📚 Documentation: http://localhost:{args.port}/docs")
    print("=" * 60)
    print()

    try:
        import uvicorn
        from healthcare_api_server.app.main import app
        
        print("🚀 Démarrage du serveur API...")
        
        # Configuration uvicorn
        config = uvicorn.Config(
            "healthcare_api_server.app.main:app" if args.reload else app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
        
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du serveur API")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
