#!/usr/bin/env python3
"""
SCRIPT DE DÉMARRAGE COMPLET - HealthCare AI Architecture ODYSSEE
Démarrage de tous les services inspiré d'ODYSSEE
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
from pathlib import Path
from typing import List, Dict

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

class ServiceManager:
    """Gestionnaire de services inspiré d'ODYSSEE"""
    
    def __init__(self):
        self.services: Dict[str, subprocess.Popen] = {}
        self.running = True
        self.logger = logging.getLogger(__name__)
        
        # Gérer les signaux d'arrêt
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Gestionnaire de signaux pour arrêt propre"""
        self.logger.info(f"[SIGNAL] Signal {signum} reçu, arrêt des services...")
        self.running = False
        self.stop_all_services()
        sys.exit(0)
    
    def check_service_dependencies(self) -> bool:
        """Vérifier que les dépendances externes sont disponibles"""
        dependencies = {
            "PostgreSQL": ("psql", "--version"),
            "Redis": ("redis-cli", "ping")
        }
        
        for name, (cmd, arg) in dependencies.items():
            try:
                result = subprocess.run([cmd, arg], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    self.logger.info(f"[OK] {name} disponible")
                else:
                    self.logger.warning(f"[WARN] {name} pourrait ne pas être disponible")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.logger.warning(f"[WARN] {name} non détecté (peut être normal si dans Docker)")
        
        return True
    
    def start_service(self, name: str, command: List[str], cwd: str = None) -> bool:
        """Démarrer un service"""
        try:
            self.logger.info(f"[DEMARRAGE] {name}...")
            
            # Définir le répertoire de travail
            work_dir = cwd or root_dir
            
            # Démarrer le processus
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy()
            )
            
            self.services[name] = process
            
            # Attendre un peu pour vérifier que le service démarre
            time.sleep(2)
            
            if process.poll() is None:
                self.logger.info(f"[OK] {name} démarré (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                self.logger.error(f"[ERREUR] {name} a échoué au démarrage")
                self.logger.error(f"STDOUT: {stdout.decode()}")
                self.logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"[ERREUR] Erreur démarrage {name}: {e}")
            return False
    
    def monitor_service(self, name: str):
        """Surveiller un service et le redémarrer si nécessaire"""
        while self.running:
            if name in self.services:
                process = self.services[name]
                if process.poll() is not None:
                    self.logger.warning(f"[WARN] {name} s'est arrêté (code: {process.returncode})")
                    # On pourrait implémenter un redémarrage automatique ici
            
            time.sleep(10)
    
    def stop_service(self, name: str):
        """Arrêter un service"""
        if name in self.services:
            process = self.services[name]
            self.logger.info(f"[ARRET] Arrêt {name}...")
            
            try:
                # Tentative d'arrêt propre
                process.terminate()
                process.wait(timeout=10)
                self.logger.info(f"[OK] {name} arrêté proprement")
            except subprocess.TimeoutExpired:
                # Forcer l'arrêt si nécessaire
                self.logger.warning(f"[WARN] Arrêt forcé de {name}")
                process.kill()
                process.wait()
            
            del self.services[name]
    
    def stop_all_services(self):
        """Arrêter tous les services"""
        service_names = list(self.services.keys())
        for name in service_names:
            self.stop_service(name)
    
    def get_service_status(self) -> Dict[str, str]:
        """Récupérer le statut de tous les services"""
        status = {}
        for name, process in self.services.items():
            if process.poll() is None:
                status[name] = "running"
            else:
                status[name] = f"stopped (code: {process.returncode})"
        return status

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/healthcare_all.log', mode='a')
        ] if os.path.exists('logs') else [logging.StreamHandler(sys.stdout)]
    )

def main():
    """Fonction principale"""
    print("""
    =================================================
    HealthCare AI - Architecture ODYSSEE
            Démarrage Complet
                                                
    API Server + Worker Server + Services     
    Inspire de l'architecture ODYSSEE         
    =================================================
    """)
    
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Créer le gestionnaire de services
    service_manager = ServiceManager()
    
    # Vérifier les dépendances
    if not service_manager.check_service_dependencies():
        logger.error("[ERREUR] Dépendances manquantes")
        sys.exit(1)
    
    logger.info("[DEMARRAGE] Démarrage de tous les services HealthCare AI...")
    
    # Services à démarrer (ordre important)
    services_config = [
        {
            "name": "API Server",
            "command": [sys.executable, "scripts/start_api.py"],
            "essential": True
        },
        {
            "name": "Worker Analyses",
            "command": [sys.executable, "scripts/start_worker.py", "analyses"],
            "essential": True
        },
        {
            "name": "Worker Sentiment", 
            "command": [sys.executable, "scripts/start_worker.py", "sentiment"],
            "essential": False
        },
        {
            "name": "Worker Classification",
            "command": [sys.executable, "scripts/start_worker.py", "classification"],
            "essential": False
        }
    ]
    
    # Démarrer les services
    failed_services = []
    for service_config in services_config:
        name = service_config["name"]
        command = service_config["command"]
        essential = service_config.get("essential", False)
        
        success = service_manager.start_service(name, command)
        
        if not success:
            failed_services.append(name)
            if essential:
                logger.error(f"[ERREUR] Service essentiel {name} a échoué, arrêt")
                service_manager.stop_all_services()
                sys.exit(1)
    
    if failed_services:
        logger.warning(f"[WARN] Services non démarrés: {', '.join(failed_services)}")
    
    # Démarrer la surveillance des services
    monitor_threads = []
    for service_name in service_manager.services.keys():
        thread = threading.Thread(
            target=service_manager.monitor_service,
            args=(service_name,),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
    
    # Afficher le statut initial
    logger.info("[STATUT] Statut des services:")
    for name, status in service_manager.get_service_status().items():
        logger.info(f"  - {name}: {status}")
    
    logger.info("[SUCCES] Tous les services sont démarrés!")
    logger.info("[ACCES] Accès:")
    logger.info("  - API Documentation: http://localhost:8000/docs")
    logger.info("  - API Health: http://localhost:8000/health")
    logger.info("  - Flower (Celery): http://localhost:5555 (si démarré)")
    
    # Boucle principale
    try:
        while service_manager.running:
            time.sleep(5)
            
            # Vérifier si tous les services essentiels sont toujours actifs
            status = service_manager.get_service_status()
            running_services = [name for name, stat in status.items() if "running" in stat]
            
            if len(running_services) == 0:
                logger.warning("[WARN] Aucun service en cours d'exécution")
                break
    
    except KeyboardInterrupt:
        logger.info("[ARRET] Arrêt demandé par l'utilisateur")
    
    finally:
        logger.info("[ARRET] Arrêt de tous les services...")
        service_manager.stop_all_services()
        logger.info("[OK] Arrêt terminé")

if __name__ == "__main__":
    main()