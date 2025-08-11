#!/usr/bin/env python3
"""
SCRIPT DE TEST CRÉATION PLAINTE - HealthCare AI Architecture ODYSSEE
Test de la création de plaintes via l'API REST
Version: 1.0.0 - Architecture ODYSSEE
"""

import requests
import json
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de l'API
API_BASE_URL = "http://localhost:8000"
API_ENDPOINTS = {
    "organisations": f"{API_BASE_URL}/api/v1/organisations",
    "services": f"{API_BASE_URL}/api/v1/services",
    "plaintes": f"{API_BASE_URL}/api/v1/plaintes",
    "analyses": f"{API_BASE_URL}/api/v1/plaintes/{{plainte_id}}/analyses"
}

def test_api_connection():
    """Tester la connexion à l'API"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            logger.info("✅ Connexion à l'API réussie")
            return True
        else:
            logger.error(f"❌ Erreur de connexion à l'API: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Impossible de se connecter à l'API: {e}")
        return False

def get_organisations():
    """Récupérer la liste des organisations"""
    try:
        response = requests.get(API_ENDPOINTS["organisations"])
        if response.status_code == 200:
            organisations = response.json()
            logger.info(f"✅ {len(organisations)} organisations récupérées")
            return organisations
        else:
            logger.error(f"❌ Erreur lors de la récupération des organisations: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des organisations: {e}")
        return []

def get_services(organisation_id=None):
    """Récupérer la liste des services"""
    try:
        url = API_ENDPOINTS["services"]
        if organisation_id:
            url += f"?organisation_id={organisation_id}"
        
        response = requests.get(url)
        if response.status_code == 200:
            services = response.json()
            logger.info(f"✅ {len(services)} services récupérés")
            return services
        else:
            logger.error(f"❌ Erreur lors de la récupération des services: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des services: {e}")
        return []

def create_test_plainte(organisation_id, service_id=None):
    """Créer une plainte de test"""
    try:
        plainte_data = {
            "titre": f"Plainte de test - {datetime.now().strftime('%H:%M:%S')}",
            "description": """Cette plainte de test concerne un problème de communication entre le service et le patient. 
            Le patient a signalé un manque d'information sur son traitement et souhaite une meilleure communication 
            de la part du personnel soignant. Cette situation a causé de l'anxiété et de la frustration.""",
            "organisation_id": organisation_id,
            "date_incident": "2024-01-15T10:30:00Z"
        }
        
        if service_id:
            plainte_data["service_id"] = service_id
        
        response = requests.post(
            API_ENDPOINTS["plaintes"],
            json=plainte_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            plainte = response.json()
            logger.info(f"✅ Plainte créée avec succès: {plainte.get('numero_plainte', 'N/A')}")
            return plainte
        else:
            logger.error(f"❌ Erreur lors de la création de la plainte: {response.status_code}")
            logger.error(f"Réponse: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la plainte: {e}")
        return None

def trigger_analyses(plainte_id):
    """Déclencher des analyses pour une plainte"""
    try:
        analyses_data = {
            "plainte_id": plainte_id,
            "types_analyse": ["sentiment", "classification", "priorite"],
            "parametres": {
                "auto_analyse": True,
                "priorite_task": "normal"
            }
        }
        
        response = requests.post(
            API_ENDPOINTS["analyses"].format(plainte_id=plainte_id),
            json=analyses_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Analyses déclenchées: {result.get('message', 'N/A')}")
            return result
        else:
            logger.error(f"❌ Erreur lors du déclenchement des analyses: {response.status_code}")
            logger.error(f"Réponse: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Erreur lors du déclenchement des analyses: {e}")
        return None

def main():
    """Fonction principale de test"""
    logger.info("🚀 Début du test de création de plaintes")
    
    # 1. Tester la connexion à l'API
    if not test_api_connection():
        logger.error("❌ Impossible de se connecter à l'API. Arrêt du test.")
        return
    
    # 2. Récupérer les organisations
    organisations = get_organisations()
    if not organisations:
        logger.error("❌ Aucune organisation trouvée. Arrêt du test.")
        return
    
    # 3. Récupérer les services de la première organisation
    first_org = organisations[0]
    services = get_services(first_org["id"])
    
    # 4. Créer une plainte de test
    service_id = services[0]["id"] if services else None
    plainte = create_test_plainte(first_org["id"], service_id)
    
    if not plainte:
        logger.error("❌ Échec de la création de la plainte. Arrêt du test.")
        return
    
    # 5. Déclencher des analyses (optionnel)
    logger.info("🔄 Déclenchement des analyses IA...")
    analyses_result = trigger_analyses(plainte["id"])
    
    if analyses_result:
        logger.info("✅ Analyses déclenchées avec succès")
    else:
        logger.warning("⚠️ Échec du déclenchement des analyses")
    
    # 6. Afficher le résumé
    logger.info("🎉 Test terminé avec succès !")
    logger.info(f"📊 Résumé:")
    logger.info(f"   - Organisation: {first_org['nom']}")
    logger.info(f"   - Service: {services[0]['nom'] if services else 'Aucun'}")
    logger.info(f"   - Plainte créée: {plainte['numero_plainte']}")
    logger.info(f"   - ID Plainte: {plainte['id']}")
    logger.info(f"   - Statut: {plainte['statut']}")
    logger.info(f"   - Priorité: {plainte['priorite']}")

if __name__ == "__main__":
    main() 