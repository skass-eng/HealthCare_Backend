#!/usr/bin/env python3
"""
SCRIPT DE DÉMARRAGE COMPLET - HealthCare AI avec Celery Worker
Lance automatiquement l'API serveur et le worker Celery
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import subprocess
import signal
import time
import psutil
from pathlib import Path

def check_redis():
    """Vérifier si Redis est disponible"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        client.ping()
        print("✅ Redis est disponible")
        return True
    except (ImportError, redis.ConnectionError, redis.ResponseError) as e:
        print(f"⚠️  Redis non disponible: {e}")
        print("ℹ️  Le worker utilisera SQLite comme fallback")
        return False

def kill_existing_processes():
    """Tuer les processus existants sur les ports utilisés"""
    ports_to_check = [8000, 5555]  # API server, Flower
    
    for port in ports_to_check:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"🔪 Terminaison du processus {proc.info['pid']} sur le port {port}")
                        proc.terminate()
                        proc.wait(timeout=3)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

def start_celery_worker():
    """Démarrer le worker Celery"""
    print("🔧 Démarrage du worker Celery...")
    
    # Configuration des variables d'environnement pour Celery
    env = os.environ.copy()
    if check_redis():
        env['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
        env['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/1'
    else:
        env['CELERY_BROKER_URL'] = 'sqla+sqlite:///celery.db'
        env['CELERY_RESULT_BACKEND'] = 'db+sqlite:///results.db'
    
    # Lancer le worker
    worker_process = subprocess.Popen([
        sys.executable, '-m', 'celery',
        '-A', 'celery_worker_v2',
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--pool=solo' if os.name == 'nt' else '--pool=prefork'  # solo pour Windows
    ], env=env)
    
    return worker_process

def start_api_server():
    """Démarrer le serveur API"""
    print("🚀 Démarrage du serveur API...")
    
    api_process = subprocess.Popen([
        sys.executable, '-m', 'uvicorn',
        'healthcare_api_server.app.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ])
    
    return api_process

def start_flower_monitoring():
    """Démarrer Flower pour monitorer Celery (optionnel)"""
    try:
        print("🌸 Démarrage de Flower (monitoring Celery)...")
        
        env = os.environ.copy()
        if check_redis():
            env['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
        else:
            env['CELERY_BROKER_URL'] = 'sqla+sqlite:///celery.db'
        
        flower_process = subprocess.Popen([
            sys.executable, '-m', 'celery',
            '-A', 'celery_worker_v2',
            'flower',
            '--port=5555'
        ], env=env)
        
        return flower_process
    except Exception as e:
        print(f"⚠️  Impossible de démarrer Flower: {e}")
        return None

def main():
    """Fonction principale"""
    print("🏥 HEALTHCARE AI - DÉMARRAGE COMPLET")
    print("=" * 50)
    
    # Tuer les processus existants
    kill_existing_processes()
    
    # Vérifier Redis
    redis_available = check_redis()
    
    # Démarrer les services
    processes = []
    
    try:
        # 1. Worker Celery
        worker_process = start_celery_worker()
        processes.append(('Worker Celery', worker_process))
        time.sleep(3)  # Attendre que le worker démarre
        
        # 2. Serveur API
        api_process = start_api_server()
        processes.append(('API Server', api_process))
        time.sleep(2)  # Attendre que l'API démarre
        
        # 3. Flower (optionnel)
        flower_process = start_flower_monitoring()
        if flower_process:
            processes.append(('Flower', flower_process))
        
        print("\n" + "=" * 50)
        print("✅ TOUS LES SERVICES SONT DÉMARRÉS")
        print("=" * 50)
        print("🌐 API Server: http://localhost:8000")
        print("📊 API Docs: http://localhost:8000/docs")
        if flower_process:
            print("🌸 Flower: http://localhost:5555")
        if redis_available:
            print("🔗 Redis: Connecté")
        else:
            print("💾 Broker: SQLite (fallback)")
        print("=" * 50)
        print("Appuyez sur Ctrl+C pour arrêter tous les services")
        
        # Attendre l'interruption
        try:
            while True:
                # Vérifier que tous les processus sont toujours vivants
                for name, process in processes:
                    if process.poll() is not None:
                        print(f"❌ {name} s'est arrêté de manière inattendue")
                        return
                time.sleep(1)
        except KeyboardInterrupt:
            print("\\n🛑 Arrêt demandé...")
    
    except Exception as e:
        print(f"❌ Erreur lors du démarrage: {e}")
    
    finally:
        # Arrêter tous les processus
        print("🔄 Arrêt des services...")
        for name, process in processes:
            try:
                print(f"  - Arrêt de {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  - Force l'arrêt de {name}...")
                process.kill()
            except Exception as e:
                print(f"  - Erreur lors de l'arrêt de {name}: {e}")
        
        print("✅ Tous les services sont arrêtés")

if __name__ == "__main__":
    main()
