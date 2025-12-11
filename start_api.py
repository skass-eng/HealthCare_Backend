#!/usr/bin/env python3
"""
DÉMARRAGE API SERVER - HealthCare AI
Script dédié au lancement du serveur API FastAPI
Usage: python start_api.py [--port PORT] [--reload] [--kill]
"""

import os
import sys
import argparse
import socket
import subprocess
import time

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def is_port_in_use(port: int) -> bool:
    """Vérifie si un port est actuellement utilisé."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        return result == 0


def kill_process_on_port(port: int) -> bool:
    """Tue le processus qui utilise le port spécifié (Windows)."""
    try:
        # Trouver le PID du processus utilisant le port
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True
        )
        
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    print(f"🔍 Processus trouvé sur le port {port}: PID {pid}")
                    # Tuer le processus
                    kill_result = subprocess.run(
                        ['taskkill', '/F', '/PID', pid],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    if kill_result.returncode == 0:
                        print(f"✅ Processus {pid} terminé avec succès")
                        time.sleep(1)  # Attendre que le port soit libéré
                        return True
                    else:
                        print(f"⚠️ Impossible de terminer le processus: {kill_result.stderr}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la libération du port: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Démarrer le serveur API HealthCare AI')
    parser.add_argument('--port', type=int, default=8000, help='Port du serveur (défaut: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host du serveur (défaut: 0.0.0.0)')
    parser.add_argument('--reload', action='store_true', help='Activer le rechargement automatique')
    parser.add_argument('--kill', action='store_true', help='Tuer le processus existant sur le port si nécessaire')
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

    # Vérifier si le port est déjà utilisé
    if is_port_in_use(args.port):
        print(f"⚠️ Le port {args.port} est déjà utilisé!")
        if args.kill:
            print("🔧 Tentative de libération du port...")
            if kill_process_on_port(args.port):
                print(f"✅ Port {args.port} libéré!")
            else:
                print(f"❌ Impossible de libérer le port {args.port}")
                print(f"💡 Essayez manuellement: netstat -ano | findstr :{args.port}")
                sys.exit(1)
        else:
            print(f"💡 Utilisez --kill pour libérer automatiquement le port")
            print(f"💡 Ou vérifiez manuellement: netstat -ano | findstr :{args.port}")
            sys.exit(1)

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
    except OSError as e:
        if e.errno == 10048:
            print(f"\n❌ Erreur: Le port {args.port} est occupé!")
            print(f"💡 Relancez avec: python start_api.py --kill")
        else:
            print(f"❌ Erreur OS: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
