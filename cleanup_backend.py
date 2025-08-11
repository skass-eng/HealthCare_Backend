#!/usr/bin/env python3
"""
PLAN DE NETTOYAGE DU BACKEND - Architecture ODYSSEE
Ce script liste et supprime les fichiers de développement/test qui polluent le projet
"""

import os
import shutil
from pathlib import Path

# Répertoire racine du backend
BACKEND_ROOT = Path(".")

# Fichiers ESSENTIELS à conserver
ESSENTIAL_FILES = {
    # Configuration et documentation principale
    "README.md",
    "requirements_odyssee.txt", 
    "package.json",
    ".env",
    "start_backend.py",
    "start_worker.py",
    
    # Documentation importante
    "ARCHITECTURE_SUMMARY.md",
    "DEMARRAGE_RAPIDE.md",
    "GUIDE_DEMARRAGE.md",
    
    # Worker Celery final (v2 seulement)
    "celery_worker_v2.py",
    
    # Répertoires essentiels
    "healthcare_api_server/",
    "healthcare_worker_server/", 
    "shared/",
    "config/",
    "data/",
    "logs/",
    "scripts/",
    "venv/",
    "uploads/"
}

# Fichiers DE TEST/DEV à supprimer
FILES_TO_DELETE = [
    # Anciens workers
    "celery_worker.py",
    
    # Fichiers de test
    "test_*.py",
    "create_test_services.py",
    
    # Fichiers de monitoring dev
    "monitor_redis.py",
    "monitor_redis.bat",
    "run_test.bat",
    
    # Fichiers temporaires dev
    "check_stats.py",
    "test_new_api.py",
    
    # Documentation temporaire
    "GUIDE_MONITORING_REDIS.md",
    "GUIDE_TEST_CREATION_PLAINTES.md",
    
    # Node modules (pas nécessaire pour le backend Python)
    "node_modules/",
    "package-lock.json",
    
    # Cache Python
    "__pycache__/",
    "**/__pycache__/"
]

def analyze_files():
    """Analyser les fichiers du projet"""
    print("🔍 ANALYSE DU PROJET BACKEND")
    print("=" * 50)
    
    all_files = []
    test_files = []
    essential_files = []
    
    for item in BACKEND_ROOT.iterdir():
        if item.is_file():
            all_files.append(item.name)
            
            if any(pattern in item.name for pattern in ["test_", "monitor_", "check_"]):
                test_files.append(item.name)
            elif item.name in ESSENTIAL_FILES:
                essential_files.append(item.name)
    
    print(f"📁 Total des fichiers: {len(all_files)}")
    print(f"✅ Fichiers essentiels: {len(essential_files)}")
    print(f"🧪 Fichiers de test/dev: {len(test_files)}")
    
    print(f"\n🧪 FICHIERS DE TEST/DEV DÉTECTÉS:")
    for f in test_files:
        print(f"   - {f}")
    
    return test_files

def clean_project(dry_run=True):
    """Nettoyer le projet"""
    
    print(f"\n🧹 NETTOYAGE DU PROJET ({'DRY RUN' if dry_run else 'RÉEL'})")
    print("=" * 50)
    
    deleted_count = 0
    
    for pattern in FILES_TO_DELETE:
        if pattern.endswith("/"):
            # Répertoire
            dir_path = BACKEND_ROOT / pattern.rstrip("/")
            if dir_path.exists():
                print(f"📁 {'[DRY RUN] ' if dry_run else ''}Suppression répertoire: {dir_path}")
                if not dry_run:
                    shutil.rmtree(dir_path)
                deleted_count += 1
        elif "*" in pattern:
            # Pattern avec wildcards
            for file_path in BACKEND_ROOT.glob(pattern):
                if file_path.exists():
                    print(f"🗑️ {'[DRY RUN] ' if dry_run else ''}Suppression: {file_path}")
                    if not dry_run:
                        if file_path.is_dir():
                            shutil.rmtree(file_path)
                        else:
                            file_path.unlink()
                    deleted_count += 1
        else:
            # Fichier spécifique
            file_path = BACKEND_ROOT / pattern
            if file_path.exists():
                print(f"🗑️ {'[DRY RUN] ' if dry_run else ''}Suppression: {file_path}")
                if not dry_run:
                    file_path.unlink()
                deleted_count += 1
    
    print(f"\n📊 Résultat: {deleted_count} éléments {'seraient supprimés' if dry_run else 'supprimés'}")
    
    return deleted_count

def create_clean_structure():
    """Créer la structure propre du projet"""
    print(f"\n✨ STRUCTURE FINALE DU PROJET")
    print("=" * 50)
    
    structure = """
healthcare_backend_odyssee/
├── 📄 README.md                          # Documentation principale
├── 📄 requirements_odyssee.txt           # Dépendances Python
├── 📄 .env                              # Variables d'environnement
├── 📄 start_backend.py                  # Script de démarrage API
├── 📄 start_worker.py                   # Script de démarrage Worker
├── 📄 celery_worker_v2.py               # Worker Celery (PDF + IA)
├── 📁 healthcare_api_server/            # Serveur API FastAPI
│   ├── 📁 app/
│   │   ├── 📁 api/                      # Endpoints REST
│   │   ├── 📁 core/                     # Configuration
│   │   ├── 📁 db/                       # Base de données
│   │   └── 📁 services/                 # Services métier
├── 📁 healthcare_worker_server/         # Serveur Worker
├── 📁 shared/                           # Modèles partagés
│   ├── 📄 models.py                     # Modèles SQLAlchemy
│   └── 📄 schemas.py                    # Schémas Pydantic
├── 📁 config/                           # Configuration
├── 📁 data/                             # Données et PDFs générés
├── 📁 scripts/                          # Scripts utilitaires
└── 📁 logs/                             # Fichiers de logs
    """
    
    print(structure)

if __name__ == "__main__":
    print("🏥 NETTOYAGE BACKEND - HealthCare AI Architecture ODYSSEE")
    print("=" * 60)
    
    # 1. Analyser les fichiers
    test_files = analyze_files()
    
    # 2. Simulation du nettoyage
    clean_project(dry_run=True)
    
    # 3. Afficher la structure finale
    create_clean_structure()
    
    print(f"\n❓ VOULEZ-VOUS PROCÉDER AU NETTOYAGE ?")
    print(f"   - {len(test_files)} fichiers de test/dev seront supprimés")
    print(f"   - La structure sera simplifiée")
    print(f"   - Les fonctionnalités principales seront conservées")
    print(f"\n🚀 Pour lancer le nettoyage: python cleanup_backend.py --execute")
