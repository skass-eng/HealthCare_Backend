#!/usr/bin/env python3
"""
Test et correction du problème de filtrage par type_service
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database_unified import SessionLocal
from models_unified import Plainte, Service, TypeServiceEnum
from api_dashboard_unified import apply_plainte_filters, TypePlainteFilter

def test_filter_problem():
    """Tester le problème de filtrage"""
    db = SessionLocal()
    
    try:
        print("🔍 Test du problème de filtrage par type_service")
        
        # Test 1: Requête de base
        print("\n1. Requête de base:")
        base_query = db.query(Plainte)
        print(f"   Nombre de plaintes total: {base_query.count()}")
        
        # Test 2: Filtre par type_service (problématique)
        print("\n2. Test du filtre problématique:")
        try:
            filters = TypePlainteFilter(type_service="CARDIOLOGIE")
            filtered_query = apply_plainte_filters(base_query, filters)
            count = filtered_query.count()
            print(f"   ✅ Filtre CARDIOLOGIE: {count} plaintes")
        except Exception as e:
            print(f"   ❌ Erreur avec filtre CARDIOLOGIE: {e}")
        
        # Test 3: Vérifier les services disponibles
        print("\n3. Services disponibles:")
        services = db.query(Service).all()
        for service in services:
            print(f"   - {service.nom} (type: {service.type_service})")
        
        # Test 4: Vérifier les plaintes avec services
        print("\n4. Plaintes avec services:")
        plaintes_with_services = db.query(Plainte).join(Service).all()
        print(f"   Nombre de plaintes avec services: {len(plaintes_with_services)}")
        
        for plainte in plaintes_with_services[:3]:  # Afficher les 3 premières
            service_name = plainte.service.nom if plainte.service else "Aucun service"
            print(f"   - Plainte {plainte.id}: {service_name}")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
    finally:
        db.close()

def fix_filter_function():
    """Corriger la fonction de filtrage"""
    print("\n🔧 Correction de la fonction apply_plainte_filters")
    
    # Lire le fichier original
    with open('api_dashboard_unified.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer la fonction problématique
    old_function = '''def apply_plainte_filters(query, filters: TypePlainteFilter):
    """Appliquer les filtres sur la requête des plaintes"""
    if filters.type_service:
        query = query.join(Service).filter(Service.type_service == filters.type_service)
    
    if filters.categorie_principale:
        query = query.filter(Plainte.categorie_principale == filters.categorie_principale)
    
    if filters.sous_categorie:
        query = query.filter(Plainte.sous_categorie == filters.sous_categorie)
    
    if filters.priorite:
        query = query.filter(Plainte.priorite == filters.priorite)
    
    if filters.statut:
        query = query.filter(Plainte.statut == filters.statut)
    
    return query'''
    
    new_function = '''def apply_plainte_filters(query, filters: TypePlainteFilter):
    """Appliquer les filtres sur la requête des plaintes"""
    if filters.type_service:
        # Convertir la chaîne en enum TypeServiceEnum
        try:
            type_service_enum = TypeServiceEnum(filters.type_service)
            query = query.join(Service).filter(Service.type_service == type_service_enum)
        except ValueError:
            # Si la valeur n'est pas un enum valide, ignorer le filtre
            print(f"⚠️ Type de service invalide: {filters.type_service}")
            pass
    
    if filters.categorie_principale:
        query = query.filter(Plainte.categorie_principale == filters.categorie_principale)
    
    if filters.sous_categorie:
        query = query.filter(Plainte.sous_categorie == filters.sous_categorie)
    
    if filters.priorite:
        query = query.filter(Plainte.priorite == filters.priorite)
    
    if filters.statut:
        query = query.filter(Plainte.statut == filters.statut)
    
    return query'''
    
    # Remplacer dans le contenu
    if old_function in content:
        new_content = content.replace(old_function, new_function)
        
        # Sauvegarder le fichier corrigé
        with open('api_dashboard_unified.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Fonction corrigée avec succès!")
        return True
    else:
        print("❌ Impossible de trouver la fonction à corriger")
        return False

def test_fixed_filter():
    """Tester la fonction corrigée"""
    print("\n🧪 Test de la fonction corrigée")
    
    db = SessionLocal()
    
    try:
        # Recharger le module corrigé
        import importlib
        import api_dashboard_unified
        importlib.reload(api_dashboard_unified)
        
        # Test avec le filtre corrigé
        base_query = db.query(Plainte)
        filters = api_dashboard_unified.TypePlainteFilter(type_service="CARDIOLOGIE")
        filtered_query = api_dashboard_unified.apply_plainte_filters(base_query, filters)
        count = filtered_query.count()
        
        print(f"✅ Filtre corrigé CARDIOLOGIE: {count} plaintes")
        
    except Exception as e:
        print(f"❌ Erreur avec le filtre corrigé: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Test et correction du problème de filtrage")
    
    # Test du problème
    test_filter_problem()
    
    # Corriger le problème
    if fix_filter_function():
        # Tester la correction
        test_fixed_filter()
    
    print("\n✅ Test terminé!") 