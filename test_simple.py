#!/usr/bin/env python3
"""
Test simple de la correction du filtre
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_unified import SessionLocal
from models_unified import Plainte, Service, TypeServiceEnum
from api_dashboard_unified import apply_plainte_filters, TypePlainteFilter

def test_correction():
    """Tester la correction du filtre"""
    db = SessionLocal()
    
    try:
        print("🧪 Test de la correction du filtre")
        
        # Test 1: Requête de base
        base_query = db.query(Plainte)
        print(f"   Nombre de plaintes total: {base_query.count()}")
        
        # Test 2: Filtre par type_service (corrigé)
        filters = TypePlainteFilter(type_service="CARDIOLOGIE")
        filtered_query = apply_plainte_filters(base_query, filters)
        count = filtered_query.count()
        print(f"   ✅ Filtre CARDIOLOGIE: {count} plaintes")
        
        # Test 3: Vérifier les services disponibles
        services = db.query(Service).all()
        print(f"   Services disponibles: {len(services)}")
        for service in services:
            print(f"     - {service.nom} (type: {service.type_service})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_correction()
    if success:
        print("\n✅ Test réussi! Le filtre fonctionne maintenant.")
    else:
        print("\n❌ Test échoué. Il y a encore un problème.") 