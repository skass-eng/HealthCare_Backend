#!/usr/bin/env python3
"""
Test de résolution de l'import circulaire
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Tester les imports"""
    print("🧪 Test de résolution de l'import circulaire")
    
    try:
        print("1. Test import api_unified...")
        import api_unified
        print("   ✅ Import api_unified réussi")
        
        print("2. Test import api_dashboard_unified...")
        import api_dashboard_unified
        print("   ✅ Import api_dashboard_unified réussi")
        
        print("3. Test création de l'app...")
        from api_unified import app
        print("   ✅ App créée avec succès")
        
        print("4. Test des routes...")
        routes = [route.path for route in app.routes]
        dashboard_routes = [r for r in routes if '/api/v1/dashboard' in str(r)]
        print(f"   ✅ Routes dashboard trouvées: {len(dashboard_routes)}")
        
        for route in dashboard_routes[:3]:  # Afficher les 3 premières
            print(f"      - {route}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✅ Import circulaire résolu!")
    else:
        print("\n❌ Problème d'import persistant") 