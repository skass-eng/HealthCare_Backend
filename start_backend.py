#!/usr/bin/env python3
"""
Script de démarrage pour HealthCare AI - Architecture ODYSSEE
Basé sur vos paramètres PostgreSQL existants
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
WORKER_LOG_LEVEL = "info"

def print_banner():
    """Afficher la bannière de démarrage"""
    print("=" * 60)
    print("🏥 HealthCare AI - Architecture ODYSSEE")
    print("=" * 60)
    print("📊 Configuration:")
    print(f"   - API Server: http://{API_HOST}:{API_PORT}")
    print(f"   - PostgreSQL: localhost:5430/hospital_complaints")
    print(f"   - Redis: localhost:6379")
    print(f"   - Documentation: http://localhost:{API_PORT}/docs")
    print("=" * 60)

def check_dependencies():
    """Vérifier les dépendances"""
    print("🔍 Vérification des dépendances...")
    
    # Vérifier Python
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Vérifier les modules
    required_modules = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'psycopg2', 
        'celery', 'redis', 'pydantic'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - Module manquant")
            return False
    
    return True

def start_api_server():
    """Démarrer le serveur API FastAPI"""
    print("\n🚀 Démarrage du serveur API...")
    
    # Changer vers le répertoire backend
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Configuration pour votre base PostgreSQL
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': 'postgresql://postgres:242261@localhost:5430/hospital_complaints',
        'REDIS_URL': 'redis://localhost:6379/0',
        'API_HOST': API_HOST,
        'API_PORT': str(API_PORT),
        'SECRET_KEY': 'your-secret-key-change-this-in-production',
        'LLM_PROVIDER': 'ollama',
        'LLM_MODEL': 'qwen2.5:7b',
        'LLM_BASE_URL': 'http://localhost:11434',
        'PYTHONPATH': str(backend_dir)
    })
    
    try:
        # Démarrer uvicorn
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'healthcare_api_server.app.main:app',
            '--host', API_HOST,
            '--port', str(API_PORT),
            '--reload'
        ]
        
        print(f"📡 API Server: http://localhost:{API_PORT}")
        print(f"📚 Documentation: http://localhost:{API_PORT}/docs")
        
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du serveur API")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de l'API: {e}")

def start_celery_worker():
    """Démarrer le worker Celery"""
    print("\n🔧 Démarrage du worker Celery...")
    
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': 'postgresql://postgres:242261@localhost:5430/hospital_complaints',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0'
    })
    
    try:
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'healthcare_worker_server.app.core.celery_app',
            'worker',
            '--loglevel=' + WORKER_LOG_LEVEL
        ]
        
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du worker Celery")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage du worker: {e}")

def start_flower():
    """Démarrer Flower (monitoring Celery)"""
    print("\n🌸 Démarrage de Flower (monitoring)...")
    
    env = os.environ.copy()
    env.update({
        'CELERY_BROKER_URL': 'redis://localhost:6379/0'
    })
    
    try:
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'healthcare_worker_server.app.core.celery_app',
            'flower',
            '--port=5555'
        ]
        
        print("🌸 Flower Monitor: http://localhost:5555")
        
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt de Flower")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de Flower: {e}")

def main():
    """Fonction principale"""
    print_banner()
    
    # Vérifier les dépendances
    if not check_dependencies():
        print("\n❌ Dépendances manquantes. Installez-les avec:")
        print("   pip install -r requirements_odyssee.txt")
        return
    
    print("\n🎯 Choisissez le mode de démarrage:")
    print("1. API Server uniquement")
    print("2. Worker Celery uniquement")
    print("3. API + Worker (recommandé)")
    print("4. API + Worker + Flower (monitoring)")
    print("5. Test de connexion")
    
    try:
        choice = input("\nVotre choix (1-5): ").strip()
        
        if choice == "1":
            start_api_server()
        elif choice == "2":
            start_celery_worker()
        elif choice == "3":
            print("\n🚀 Démarrage API + Worker...")
            print("💡 Ouvrez deux terminaux pour voir les logs séparément")
            start_api_server()
        elif choice == "4":
            print("\n🚀 Démarrage complet (API + Worker + Flower)...")
            print("💡 Ouvrez trois terminaux pour voir les logs séparément")
            start_api_server()
        elif choice == "5":
            print("\n🔍 Test de connexion...")
            subprocess.run([sys.executable, "test_connection.py"])
        else:
            print("❌ Choix invalide")
            
    except KeyboardInterrupt:
        print("\n👋 Arrêt du programme")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main() 
    