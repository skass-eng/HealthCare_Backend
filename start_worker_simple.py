#!/usr/bin/env python3
"""
Script de démarrage simple pour le worker Celery
"""
import os
import sys

# Ajouter le répertoire courant au path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importer et démarrer le worker
from celery_worker_v2 import app

if __name__ == "__main__":
    print("🚀 CELERY WORKER - HealthCare AI")
    print("Démarrage du worker...")
    
    # Arguments pour le worker
    worker_args = [
        'worker',
        '--loglevel=info',
        '--pool=solo',
        '--concurrency=1'
    ]
    
    app.worker_main(argv=worker_args)
