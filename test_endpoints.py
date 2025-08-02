#!/usr/bin/env python3
"""
Script de test pour vérifier les endpoints de filtrage des plaintes
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Tester les différents endpoints de filtrage"""
    
    endpoints = [
        "/api/v1/dashboard/plaintes/recu",
        "/api/v1/dashboard/plaintes/en-cours", 
        "/api/v1/dashboard/plaintes/traite",
        "/api/v1/dashboard/plaintes/cloture",
        "/api/v1/dashboard/statistiques"
    ]
    
    print("🔍 Test des endpoints de filtrage des plaintes")
    print("=" * 50)
    
    for endpoint in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n📡 Test de {endpoint}")
            print(f"URL: {url}")
            
            response = requests.get(url, params={"page": 1, "limit": 5})
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Succès (Status: {response.status_code})")
                
                if "plaintes" in data:
                    print(f"   📊 Plaintes trouvées: {len(data['plaintes'])}")
                    print(f"   📈 Total: {data.get('total', 'N/A')}")
                elif "nouvelles_plaintes" in data:
                    print(f"   📊 Nouvelles plaintes: {data.get('nouvelles_plaintes', 0)}")
                    print(f"   📊 En cours: {data.get('en_cours_traitement', 0)}")
                    print(f"   📊 Traitées: {data.get('traitees_ce_mois', 0)}")
                    print(f"   📊 Clôturées: {data.get('plaintes_cloturees', 0)}")
            else:
                print(f"❌ Erreur (Status: {response.status_code})")
                print(f"   Message: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test terminé!")

if __name__ == "__main__":
    test_endpoints() 