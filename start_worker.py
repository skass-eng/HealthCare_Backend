#!/usr/bin/env python3
"""
DÉMARRAGE WORKER CELERY - HealthCare AI
Script dédié au lancement du worker Celery pour le traitement des plaintes
Usage: python start_worker.py [--concurrency N] [--loglevel LEVEL]

Ce worker gère:
- L'analyse IA des plaintes (sentiment, priorité, service suggéré)
- La génération des PDFs de rapport
- Le traitement asynchrone des tâches
"""

import os
import sys
import argparse
import signal
import time
from datetime import datetime

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Variable globale pour gérer l'arrêt propre
shutdown_requested = False


def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre"""
    global shutdown_requested
    print("\n⏹️  Signal d'arrêt reçu, fermeture en cours...")
    shutdown_requested = True


def check_redis_connection():
    """Vérifier la connexion Redis"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=1)
        client.ping()
        print("✅ Redis connecté (localhost:6379)")
        return True
    except Exception as e:
        print(f"⚠️  Redis non disponible: {e}")
        print("   Le worker utilisera SQLite comme fallback")
        return False


def check_database_connection():
    """Vérifier la connexion à la base de données"""
    try:
        from healthcare_api_server.app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connecté")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL non disponible: {e}")
        return False


def run_worker_celery(concurrency: int, loglevel: str):
    """Démarrer le worker Celery standard"""
    print("🔧 Mode: Celery Worker")
    
    from celery_worker_v2 import app as celery_app
    
    # Configuration des arguments Celery
    argv = [
        'worker',
        f'--loglevel={loglevel}',
        f'--concurrency={concurrency}',
        '--pool=solo',  # Utiliser solo pour Windows
        '-Q', 'celery,analyses,sentiment,classification',  # Queues à écouter
    ]
    
    print(f"   Concurrency: {concurrency}")
    print(f"   Log Level: {loglevel}")
    print(f"   Queues: celery, analyses, sentiment, classification")
    print()
    print("🚀 Démarrage du worker Celery...")
    print("-" * 60)
    
    celery_app.worker_main(argv)


def run_worker_standalone(check_interval: int = 5):
    """
    Mode standalone: traitement des plaintes sans Celery
    Utile quand Redis n'est pas disponible
    """
    print("🔧 Mode: Standalone (sans Celery)")
    print(f"   Intervalle de vérification: {check_interval} secondes")
    print()
    print("🚀 Démarrage du worker standalone...")
    print("-" * 60)
    
    from healthcare_api_server.app.db.database import SessionLocal
    from shared.models import Plainte, AnalyseIA
    from celery_worker_v2 import generate_plainte_pdf
    import json
    
    def analyze_plainte(plainte, db):
        """Analyser une plainte et mettre à jour l'analyse IA"""
        try:
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte.id).first()
            if not analyse_ia:
                return
            
            # Analyse de sentiment basée sur le texte
            texte = f"{plainte.titre or ''} {plainte.description or ''}"
            if plainte.circonstances:
                texte += f" {plainte.circonstances}"
            if plainte.consequences:
                texte += f" {plainte.consequences}"
            
            mots_negatifs = ['problème', 'mauvais', 'inacceptable', 'colère', 'furieux', 
                           'déçu', 'grave', 'urgent', 'scandaleux', 'horrible']
            mots_positifs = ['merci', 'satisfait', 'bien', 'excellent', 'parfait', 'content']
            mots_urgents = ['urgence', 'urgent', 'grave', 'immédiat', 'critique', 'danger']
            
            score_neg = sum(1 for m in mots_negatifs if m in texte.lower())
            score_pos = sum(1 for m in mots_positifs if m in texte.lower())
            score_urgent = sum(1 for m in mots_urgents if m in texte.lower())
            
            # Déterminer le sentiment
            if score_neg > score_pos:
                sentiment = "négatif"
                confiance = min(0.95, 0.6 + (score_neg * 0.1))
            elif score_pos > score_neg:
                sentiment = "positif"
                confiance = min(0.95, 0.6 + (score_pos * 0.1))
            else:
                sentiment = "neutre"
                confiance = 0.6
            
            # Déterminer la priorité
            if score_urgent > 0 or (sentiment == "négatif" and score_neg >= 3):
                priorite_ia = "URGENT"
                urgence = True
            elif sentiment == "négatif" and score_neg >= 2:
                priorite_ia = "ELEVE"
                urgence = False
            elif sentiment == "positif":
                priorite_ia = "BAS"
                urgence = False
            else:
                priorite_ia = "MOYEN"
                urgence = False
            
            # Déterminer le service suggéré
            if any(w in texte.lower() for w in ['urgence', 'urgent', 'grave']):
                service_suggere = "Service d'Urgence"
            elif any(w in texte.lower() for w in ['consultation', 'médecin', 'docteur']):
                service_suggere = "Service de Consultation"
            elif any(w in texte.lower() for w in ['chirurgie', 'opération']):
                service_suggere = "Service de Chirurgie"
            elif any(w in texte.lower() for w in ['administration', 'secrétariat']):
                service_suggere = "Service Administratif"
            else:
                service_suggere = "Service Qualité"
            
            # Mettre à jour l'analyse
            analyse_ia.sentiment = sentiment
            analyse_ia.confiance_sentiment = confiance
            analyse_ia.service_suggere = service_suggere
            analyse_ia.priorite_ia = priorite_ia
            analyse_ia.score_priorite = confiance
            analyse_ia.urgence_detectee = urgence
            analyse_ia.resume_ia = f"Plainte analysée. Sentiment {sentiment} détecté. Recommandation: {service_suggere}."
            analyse_ia.mots_cles_detectes = json.dumps(["plainte", "service", "patient"])
            analyse_ia.statut_analyse = "complete"
            analyse_ia.date_analyse = datetime.now()
            analyse_ia.date_mise_a_jour = datetime.now()
            analyse_ia.modele_utilise = "HealthCare_AI_Standalone"
            analyse_ia.version_modele = "1.0.0"
            
            db.commit()
            print(f"   ✅ Plainte #{plainte.id}: {sentiment}/{priorite_ia}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur analyse plainte #{plainte.id}: {e}")
            db.rollback()
            return False
    
    def process_pending_analyses():
        """Traiter toutes les analyses en attente"""
        db = SessionLocal()
        try:
            # Récupérer les analyses en cours
            pending = db.query(AnalyseIA).filter(
                AnalyseIA.statut_analyse == "en_cours"
            ).all()
            
            if pending:
                print(f"📋 {len(pending)} analyse(s) en attente")
                
                for analyse in pending:
                    plainte = db.query(Plainte).filter(Plainte.id == analyse.plainte_id).first()
                    if plainte:
                        analyze_plainte(plainte, db)
                        
                        # Générer le PDF si nécessaire
                        try:
                            pdf_path = f"data/pdf_reports/plainte_{plainte.id}_rapport_complet.pdf"
                            if not os.path.exists(pdf_path):
                                generate_plainte_pdf(plainte.id)
                        except Exception as e:
                            print(f"   ⚠️ Erreur PDF plainte #{plainte.id}: {e}")
                
            return len(pending)
            
        except Exception as e:
            print(f"❌ Erreur traitement: {e}")
            return 0
        finally:
            db.close()
    
    # Boucle principale
    global shutdown_requested
    iteration = 0
    
    while not shutdown_requested:
        iteration += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        try:
            count = process_pending_analyses()
            if count == 0 and iteration % 12 == 0:  # Log toutes les minutes environ
                print(f"[{timestamp}] 💤 Aucune tâche en attente...")
        except Exception as e:
            print(f"[{timestamp}] ❌ Erreur: {e}")
        
        # Attendre avant la prochaine vérification
        for _ in range(check_interval):
            if shutdown_requested:
                break
            time.sleep(1)
    
    print("✅ Worker standalone arrêté proprement")


def main():
    parser = argparse.ArgumentParser(description='Démarrer le worker HealthCare AI')
    parser.add_argument('--mode', choices=['celery', 'standalone', 'auto'], 
                       default='auto', help='Mode de fonctionnement (défaut: auto)')
    parser.add_argument('--concurrency', type=int, default=1, 
                       help='Nombre de workers (Celery uniquement, défaut: 1)')
    parser.add_argument('--loglevel', type=str, default='info',
                       choices=['debug', 'info', 'warning', 'error'],
                       help='Niveau de log (défaut: info)')
    parser.add_argument('--interval', type=int, default=5,
                       help='Intervalle de vérification en secondes (standalone, défaut: 5)')
    args = parser.parse_args()

    # Configurer les signaux pour arrêt propre
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("🏥 HealthCare AI - Worker")
    print("=" * 60)
    print(f"📅 Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Vérifier les connexions
    print("🔍 Vérification des dépendances...")
    redis_ok = check_redis_connection()
    db_ok = check_database_connection()
    print()
    
    if not db_ok:
        print("❌ Impossible de démarrer sans connexion à la base de données")
        sys.exit(1)
    
    # Déterminer le mode
    mode = args.mode
    if mode == 'auto':
        mode = 'celery' if redis_ok else 'standalone'
        print(f"🔄 Mode automatique: {mode}")
    
    print("=" * 60)
    
    try:
        if mode == 'celery':
            if not redis_ok:
                print("⚠️  Redis requis pour le mode Celery, passage en mode standalone")
                run_worker_standalone(args.interval)
            else:
                run_worker_celery(args.concurrency, args.loglevel)
        else:
            run_worker_standalone(args.interval)
            
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du worker")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
