#!/usr/bin/env python3
"""
Test de l'endpoint API du dashboard unifié
"""

import requests
import json

def test_api_endpoint():
    """Tester l'endpoint API"""
    base_url = "http://localhost:8000"
    
    print("🧪 Test de l'endpoint API du dashboard unifié")
    
    # Test 1: Health check
    print("\n1. Test health check:")
    try:
        response = requests.get(f"{base_url}/api/v1/dashboard/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Health check OK: {response.json()}")
        else:
            print(f"   ❌ Health check échoué: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur health check: {e}")
    
    # Test 2: Filtres disponibles
    print("\n2. Test filtres disponibles:")
    try:
        response = requests.get(f"{base_url}/api/v1/dashboard/filtres-disponibles")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Filtres disponibles: {len(data.get('filtres', {}).get('types_services', []))} types de services")
        else:
            print(f"   ❌ Erreur filtres: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur filtres: {e}")
    
    # Test 3: Statistiques sans filtre
    print("\n3. Test statistiques sans filtre:")
    try:
        response = requests.get(f"{base_url}/api/v1/dashboard/statistiques")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Statistiques OK: {data.get('nouvelles_plaintes', 0)} nouvelles plaintes")
        else:
            print(f"   ❌ Erreur statistiques: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur statistiques: {e}")
    
    # Test 4: Statistiques avec filtre CARDIOLOGIE
    print("\n4. Test statistiques avec filtre CARDIOLOGIE:")
    try:
        params = {"type_service": "CARDIOLOGIE"}
        response = requests.get(f"{base_url}/api/v1/dashboard/statistiques", params=params)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Statistiques CARDIOLOGIE OK: {data.get('nouvelles_plaintes', 0)} nouvelles plaintes")
        else:
            print(f"   ❌ Erreur statistiques CARDIOLOGIE: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur statistiques CARDIOLOGIE: {e}")

if __name__ == "__main__":
    test_api_endpoint()
    print("\n✅ Test terminé!") 