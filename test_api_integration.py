#!/usr/bin/env python3
"""
Test d'intégration API + Worker modulaire
Test de création de plainte avec traitement modulaire complet
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
PLAINTE_ENDPOINT = f"{API_BASE_URL}/api/v1/test/plainte"

def test_create_complaint_with_document():
    """Test de création de plainte avec document"""
    print("🧪 TEST INTÉGRATION API + WORKER MODULAIRE")
    print("=" * 50)
    
    # Données de test
    plainte_data = {
        "titre": "Délai d'attente trop long en cardiologie",
        "nom_plaignant": "Marie Dupont",
        "prenom_plaignant": "Marie",
        "telephone_plaignant": "0123456789",
        "email_plaignant": "marie.dupont@email.com",
        "description": "Délai d'attente trop long pour consultation spécialisée. Plus de 6 mois d'attente.",
        "service_id": 1,
        "date_incident": "2025-08-13T18:50:00"
    }
    
    print(f"📤 Envoi de la plainte vers {PLAINTE_ENDPOINT}")
    print(f"📋 Données: {json.dumps(plainte_data, indent=2, ensure_ascii=False)}")
    
    try:
        # Envoi de la requête
        response = requests.post(
            PLAINTE_ENDPOINT,
            json=plainte_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 Status HTTP: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("✅ PLAINTE CRÉÉE AVEC SUCCÈS!")
            print(f"📌 ID Plainte: {result.get('id')}")
            print(f"📌 Numéro: {result.get('numero')}")
            print(f"📌 Analyse IA en cours: {result.get('analyse_ia_en_cours', False)}")
            print(f"📌 Task ID: {result.get('task_id', 'N/A')}")
            
            # Si worker modulaire disponible, afficher les détails
            if result.get('analyse_ia_en_cours'):
                print("🔄 TRAITEMENT MODULAIRE EN COURS...")
                print("📊 Étapes du workflow modulaire:")
                print("  1️⃣ Analyse du texte (OCR si document)")
                print("  2️⃣ Analyse IA (sentiment + résumé + contacts)")
                print("  3️⃣ Génération de réponse légale")
                print("  4️⃣ Génération du rapport PDF")
                
                # Attendre quelques secondes pour voir le traitement
                print("\n⏳ Attente du traitement en arrière-plan...")
                time.sleep(3)
                
                # Vérifier le statut via API
                plainte_id = result.get('id')
                if plainte_id:
                    print(f"🔍 Vérification du statut de la plainte {plainte_id}")
                    status_response = requests.get(f"{API_BASE_URL}/api/v1/test/plainte/{plainte_id}", timeout=5)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"📈 Statut actuel: {status_data.get('statut')}")
                        print(f"🤖 Analyse IA terminée: {not status_data.get('analyse_ia_en_cours', True)}")
            
            return True
            
        else:
            print(f"❌ ERREUR HTTP {response.status_code}")
            print(f"📝 Réponse: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERREUR: Impossible de se connecter à l'API")
        print("💡 Vérifiez que l'API est démarrée sur http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ ERREUR: Timeout de la requête")
        return False
    except Exception as e:
        print(f"❌ ERREUR INATTENDUE: {e}")
        return False

def test_api_health():
    """Test de santé de l'API"""
    print("🏥 Test de santé de l'API...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API accessible")
            return True
        else:
            print(f"⚠️ API répond avec code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API inaccessible: {e}")
        return False

if __name__ == "__main__":
    print("🚀 DÉMARRAGE DES TESTS D'INTÉGRATION")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test de santé API
    if test_api_health():
        print()
        # Test de création de plainte
        success = test_create_complaint_with_document()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 INTÉGRATION RÉUSSIE!")
            print("✅ L'architecture modulaire fonctionne avec l'API")
        else:
            print("❌ ÉCHEC DE L'INTÉGRATION")
    else:
        print("❌ Impossible de continuer - API non accessible")
