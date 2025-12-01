#!/usr/bin/env python3
"""
TEST API SERVICES - Tests CRUD complets
Teste la création, mise à jour, récupération et suppression des services
"""

import requests
import json
from datetime import datetime

# Configuration de base
BASE_URL = "http://localhost:8000/api/v1"
SERVICES_URL = f"{BASE_URL}/services"

# Données de test pour création
SERVICE_DATA = {
    "nom": "Service Test Automatisé",
    "code_service": f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "description": "Service créé pour test automatisé des APIs Administration",
    "categorie": "Test",
    "configuration": {
        "test_mode": True,
        "created_by": "test_script"
    }
}

# Données de mise à jour
SERVICE_UPDATE_DATA = {
    "nom": "Service Test Modifié",
    "description": "Description modifiée par le test automatisé",
    "categorie": "Test Modifié"
}


def print_separator(title: str):
    """Affiche un séparateur avec titre"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(success: bool, message: str, details: dict = None):
    """Affiche le résultat d'un test"""
    status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
    print(f"\n{status}: {message}")
    if details:
        print(f"   Détails: {json.dumps(details, indent=2, ensure_ascii=False)}")


def test_create_service():
    """
    ÉTAPE 1: Créer un nouveau service
    Code HTTP attendu: 201 (Created) ou 200 (OK selon implémentation)
    """
    print_separator("ÉTAPE 1: CRÉATION D'UN NOUVEAU SERVICE")
    
    print(f"\n📤 Envoi POST vers {SERVICES_URL}")
    print(f"   Données: {json.dumps(SERVICE_DATA, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            SERVICES_URL,
            json=SERVICE_DATA,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📥 Réponse HTTP: {response.status_code}")
        
        # Vérification du code HTTP (201 ou 200 acceptable)
        if response.status_code in [200, 201]:
            data = response.json()
            service_id = data.get("id")
            
            print_result(True, f"Service créé avec ID: {service_id}", {
                "id": service_id,
                "nom": data.get("nom"),
                "code_service": data.get("code_service"),
                "est_actif": data.get("est_actif")
            })
            
            # Vérifier les champs retournés
            assert data.get("nom") == SERVICE_DATA["nom"], "Le nom ne correspond pas"
            assert data.get("code_service") == SERVICE_DATA["code_service"], "Le code service ne correspond pas"
            assert data.get("est_actif") == True, "Le service devrait être actif"
            
            print("\n   ✓ Tous les champs sont corrects")
            return service_id, data
        else:
            print_result(False, f"Code HTTP inattendu: {response.status_code}")
            print(f"   Corps: {response.text}")
            return None, None
            
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return None, None


def test_update_service(service_id: int):
    """
    ÉTAPE 2: Mettre à jour le service
    Code HTTP attendu: 200 (OK)
    """
    print_separator("ÉTAPE 2: MISE À JOUR DU SERVICE")
    
    update_url = f"{SERVICES_URL}/{service_id}"
    print(f"\n📤 Envoi PUT vers {update_url}")
    print(f"   Données: {json.dumps(SERVICE_UPDATE_DATA, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.put(
            update_url,
            json=SERVICE_UPDATE_DATA,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📥 Réponse HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print_result(True, "Service mis à jour avec succès", {
                "id": data.get("id"),
                "nom": data.get("nom"),
                "description": data.get("description"),
                "categorie": data.get("categorie")
            })
            
            # Vérifier que les modifications ont été appliquées
            assert data.get("nom") == SERVICE_UPDATE_DATA["nom"], "Le nom n'a pas été mis à jour"
            assert data.get("description") == SERVICE_UPDATE_DATA["description"], "La description n'a pas été mise à jour"
            assert data.get("categorie") == SERVICE_UPDATE_DATA["categorie"], "La catégorie n'a pas été mise à jour"
            
            print("\n   ✓ Toutes les modifications sont correctes")
            return True, data
        else:
            print_result(False, f"Code HTTP inattendu: {response.status_code}")
            print(f"   Corps: {response.text}")
            return False, None
            
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False, None


def test_get_service(service_id: int, expected_data: dict):
    """
    ÉTAPE 3: Vérifier les modifications en récupérant le service
    Code HTTP attendu: 200 (OK)
    """
    print_separator("ÉTAPE 3: RÉCUPÉRATION DU SERVICE MODIFIÉ")
    
    get_url = f"{SERVICES_URL}/{service_id}"
    print(f"\n📤 Envoi GET vers {get_url}")
    
    try:
        response = requests.get(get_url)
        
        print(f"\n📥 Réponse HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print_result(True, "Service récupéré avec succès", {
                "id": data.get("id"),
                "nom": data.get("nom"),
                "description": data.get("description"),
                "categorie": data.get("categorie"),
                "est_actif": data.get("est_actif")
            })
            
            # Vérifier la cohérence avec les données attendues
            assert data.get("nom") == expected_data.get("nom"), "Incohérence sur le nom"
            assert data.get("description") == expected_data.get("description"), "Incohérence sur la description"
            assert data.get("categorie") == expected_data.get("categorie"), "Incohérence sur la catégorie"
            
            print("\n   ✓ Les données sont cohérentes avec la mise à jour")
            return True, data
        else:
            print_result(False, f"Code HTTP inattendu: {response.status_code}")
            print(f"   Corps: {response.text}")
            return False, None
            
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False, None


def test_delete_service(service_id: int):
    """
    ÉTAPE 4: Supprimer le service
    Code HTTP attendu: 200 (OK avec message) ou 204 (No Content)
    """
    print_separator("ÉTAPE 4: SUPPRESSION DU SERVICE")
    
    delete_url = f"{SERVICES_URL}/{service_id}"
    print(f"\n📤 Envoi DELETE vers {delete_url}")
    
    try:
        response = requests.delete(delete_url)
        
        print(f"\n📥 Réponse HTTP: {response.status_code}")
        
        # 200 avec message ou 204 sans contenu sont acceptables
        if response.status_code in [200, 204]:
            if response.status_code == 200:
                data = response.json()
                print_result(True, "Service supprimé avec succès", data)
            else:
                print_result(True, "Service supprimé avec succès (204 No Content)")
            
            return True
        else:
            print_result(False, f"Code HTTP inattendu: {response.status_code}")
            print(f"   Corps: {response.text}")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False


def test_verify_deletion(service_id: int):
    """
    ÉTAPE 5: Vérifier que le service n'apparaît plus dans la liste
    """
    print_separator("ÉTAPE 5: VÉRIFICATION DE LA SUPPRESSION")
    
    print(f"\n📤 Envoi GET vers {SERVICES_URL} pour lister les services actifs")
    
    try:
        # Vérifier que le service n'est plus accessible directement
        get_url = f"{SERVICES_URL}/{service_id}"
        response_get = requests.get(get_url)
        
        print(f"\n📥 GET /{service_id} - Réponse HTTP: {response_get.status_code}")
        
        if response_get.status_code == 404:
            print_result(True, "Le service n'est plus accessible (404 Not Found)")
        elif response_get.status_code == 200:
            data = response_get.json()
            if data.get("est_actif") == False:
                print_result(True, "Le service est marqué comme inactif (soft delete)")
            else:
                print_result(False, "Le service est toujours actif!")
                return False
        
        # Vérifier que le service n'apparaît plus dans la liste des services actifs
        response_list = requests.get(f"{SERVICES_URL}?actif_seulement=true")
        
        print(f"\n📥 Liste services actifs - Réponse HTTP: {response_list.status_code}")
        
        if response_list.status_code == 200:
            services = response_list.json()
            service_ids = [s.get("id") for s in services]
            
            if service_id not in service_ids:
                print_result(True, f"Le service ID {service_id} n'apparaît plus dans la liste des services actifs")
                print(f"   Nombre de services actifs: {len(services)}")
                return True
            else:
                print_result(False, f"Le service ID {service_id} apparaît encore dans la liste!")
                return False
        else:
            print_result(False, f"Impossible de récupérer la liste des services")
            return False
            
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False


def run_all_tests():
    """Exécute tous les tests CRUD"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "TEST API SERVICES - CRUD COMPLET" + " " * 14 + "║")
    print("║" + " " * 10 + "Administration des Services" + " " * 19 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = {
        "creation": False,
        "mise_a_jour": False,
        "recuperation": False,
        "suppression": False,
        "verification": False
    }
    
    # ÉTAPE 1: Création
    service_id, created_data = test_create_service()
    results["creation"] = service_id is not None
    
    if not service_id:
        print("\n❌ Impossible de continuer sans service créé.")
        print_summary(results)
        return
    
    # ÉTAPE 2: Mise à jour
    update_success, updated_data = test_update_service(service_id)
    results["mise_a_jour"] = update_success
    
    if not update_success:
        print("\n⚠️ La mise à jour a échoué, on continue avec les tests...")
        updated_data = SERVICE_UPDATE_DATA
    
    # ÉTAPE 3: Récupération et vérification
    get_success, retrieved_data = test_get_service(service_id, updated_data)
    results["recuperation"] = get_success
    
    # ÉTAPE 4: Suppression
    delete_success = test_delete_service(service_id)
    results["suppression"] = delete_success
    
    # ÉTAPE 5: Vérification de la suppression
    if delete_success:
        verify_success = test_verify_deletion(service_id)
        results["verification"] = verify_success
    
    # Résumé final
    print_summary(results)


def print_summary(results: dict):
    """Affiche le résumé des tests"""
    print_separator("RÉSUMÉ DES TESTS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print("\n   Résultats:")
    for test_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n   Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n   🎉 TOUS LES TESTS SONT PASSÉS!")
    else:
        print(f"\n   ⚠️ {total - passed} test(s) échoué(s)")
    
    # Résumé des codes HTTP attendus vs reçus
    print("\n   Codes HTTP attendus:")
    print("   • Création (POST)     : 201 Created (ou 200 OK)")
    print("   • Mise à jour (PUT)   : 200 OK")
    print("   • Récupération (GET)  : 200 OK")
    print("   • Suppression (DELETE): 204 No Content (ou 200 OK)")


if __name__ == "__main__":
    run_all_tests()
