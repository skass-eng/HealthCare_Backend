#!/usr/bin/env python3
"""
Script pour corriger les problèmes de migration
Version: 2.0.0 - Architecture ODYSSEE simplifiée
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import SessionLocal, engine
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_duplicate_codes():
    """Corriger les codes services en doublon"""
    
    db = SessionLocal()
    
    try:
        logger.info("🔍 Recherche des doublons de code_service...")
        
        # Trouver les doublons
        result = db.execute(text("""
            SELECT code_service, COUNT(*) as count
            FROM services 
            GROUP BY code_service 
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        
        if not duplicates:
            logger.info("✅ Aucun doublon trouvé")
            return True
        
        logger.info(f"⚠️  {len(duplicates)} codes en doublon trouvés")
        
        for code_service, count in duplicates:
            logger.info(f"   - {code_service}: {count} occurrences")
            
            # Récupérer tous les services avec ce code
            services = db.execute(text(f"""
                SELECT id, nom, code_service 
                FROM services 
                WHERE code_service = '{code_service}'
                ORDER BY id
            """)).fetchall()
            
            # Garder le premier, renommer les autres
            for i, (service_id, nom, old_code) in enumerate(services):
                if i == 0:
                    logger.info(f"   Garder: ID {service_id} - {nom}")
                    continue
                
                new_code = f"{old_code}_{i}"
                
                # Vérifier que le nouveau code n'existe pas déjà
                while True:
                    existing = db.execute(text(f"""
                        SELECT COUNT(*) FROM services WHERE code_service = '{new_code}'
                    """)).scalar()
                    
                    if existing == 0:
                        break
                    new_code = f"{old_code}_{i}_{existing}"
                
                # Mettre à jour
                db.execute(text(f"""
                    UPDATE services 
                    SET code_service = '{new_code}'
                    WHERE id = {service_id}
                """))
                
                logger.info(f"   Renommé: ID {service_id} - {nom} -> {new_code}")
        
        db.commit()
        logger.info("✅ Doublons corrigés")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur: {e}")
        return False
    finally:
        db.close()

def add_kpi_columns():
    """Ajouter les colonnes KPI si elles n'existent pas"""
    
    db = SessionLocal()
    inspector = inspect(engine)
    
    try:
        # Vérifier les colonnes existantes
        service_columns = [col['name'] for col in inspector.get_columns('services')]
        
        kpi_columns = [
            ('nombre_plaintes_total', 'INTEGER DEFAULT 0'),
            ('nombre_plaintes_resolues', 'INTEGER DEFAULT 0'), 
            ('temps_moyen_resolution', 'REAL DEFAULT 0.0'),
            ('taux_satisfaction', 'REAL DEFAULT 0.0')
        ]
        
        for col_name, col_def in kpi_columns:
            if col_name not in service_columns:
                logger.info(f"➕ Ajout colonne {col_name}")
                db.execute(text(f"ALTER TABLE services ADD COLUMN {col_name} {col_def}"))
                db.execute(text(f"ALTER TABLE services ALTER COLUMN {col_name} SET NOT NULL"))
        
        db.commit()
        logger.info("✅ Colonnes KPI ajoutées")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur ajout KPI: {e}")
        return False
    finally:
        db.close()

def remove_organisation_references():
    """Supprimer les références à organisation"""
    
    db = SessionLocal()
    inspector = inspect(engine)
    
    try:
        # Vérifier les colonnes des tables
        service_columns = [col['name'] for col in inspector.get_columns('services')]
        plainte_columns = [col['name'] for col in inspector.get_columns('plaintes')] if 'plaintes' in inspector.get_table_names() else []
        
        # Supprimer organisation_id des services si elle existe
        if 'organisation_id' in service_columns:
            logger.info("🗑️  Suppression organisation_id des services")
            db.execute(text("ALTER TABLE services DROP COLUMN organisation_id"))
        
        # Supprimer organisation_id des plaintes et rendre service_id obligatoire
        if 'organisation_id' in plainte_columns:
            logger.info("🗑️  Suppression organisation_id des plaintes")
            
            # D'abord, assurer que toutes les plaintes ont un service_id
            services = db.execute(text("SELECT id FROM services WHERE est_actif = true LIMIT 1")).fetchone()
            if services:
                service_id = services[0]
                db.execute(text(f"""
                    UPDATE plaintes 
                    SET service_id = {service_id}
                    WHERE service_id IS NULL
                """))
            
            # Supprimer la colonne organisation_id
            db.execute(text("ALTER TABLE plaintes DROP COLUMN organisation_id"))
            
            # Rendre service_id obligatoire
            db.execute(text("ALTER TABLE plaintes ALTER COLUMN service_id SET NOT NULL"))
        
        # Supprimer la table organisations si elle existe
        tables = inspector.get_table_names()
        if 'organisations' in tables:
            logger.info("🗑️  Suppression table organisations")
            db.execute(text("DROP TABLE organisations"))
        
        db.commit()
        logger.info("✅ Références organisation supprimées")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur suppression organisation: {e}")
        return False
    finally:
        db.close()

def calculate_initial_kpis():
    """Calculer les KPIs initiaux"""
    
    db = SessionLocal()
    
    try:
        logger.info("📊 Calcul des KPIs initiaux...")
        
        services = db.execute(text("SELECT id, nom FROM services WHERE est_actif = true")).fetchall()
        
        for service_id, nom in services:
            # Vérifier si la table plaintes existe
            inspector = inspect(engine)
            if 'plaintes' not in inspector.get_table_names():
                logger.info("⚠️  Table plaintes n'existe pas, KPIs mis à 0")
                continue
            
            # Calculer les KPIs
            total_plaintes = db.execute(text(f"""
                SELECT COUNT(*) FROM plaintes WHERE service_id = {service_id}
            """)).scalar() or 0
            
            plaintes_resolues = db.execute(text(f"""
                SELECT COUNT(*) FROM plaintes 
                WHERE service_id = {service_id} AND statut IN ('TRAITE', 'CLOTURE')
            """)).scalar() or 0
            
            avg_resolution = db.execute(text(f"""
                SELECT AVG(EXTRACT(EPOCH FROM date_resolution - date_creation) / 86400)
                FROM plaintes 
                WHERE service_id = {service_id} AND date_resolution IS NOT NULL
            """)).scalar()
            
            temps_moyen = round(float(avg_resolution or 0), 2)
            
            avg_sentiment = db.execute(text(f"""
                SELECT AVG(score_sentiment)
                FROM plaintes 
                WHERE service_id = {service_id} AND score_sentiment IS NOT NULL
            """)).scalar()
            
            taux_satisfaction = round(((float(avg_sentiment or 0) + 1) / 2) * 100, 2) if avg_sentiment else 0.0
            
            # Mettre à jour
            db.execute(text(f"""
                UPDATE services SET
                    nombre_plaintes_total = {total_plaintes},
                    nombre_plaintes_resolues = {plaintes_resolues},
                    temps_moyen_resolution = {temps_moyen},
                    taux_satisfaction = {taux_satisfaction}
                WHERE id = {service_id}
            """))
            
            logger.info(f"📈 {nom}: {total_plaintes} plaintes, {plaintes_resolues} résolues")
        
        db.commit()
        logger.info("✅ KPIs calculés")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur calcul KPIs: {e}")
        return False
    finally:
        db.close()

def main():
    """Migration complète"""
    
    logger.info("🚀 Correction et migration de la base de données")
    logger.info("=" * 60)
    
    success = True
    
    # 1. Corriger les doublons
    if not fix_duplicate_codes():
        success = False
    
    # 2. Ajouter les colonnes KPI
    if not add_kpi_columns():
        success = False
    
    # 3. Supprimer les références organisation
    if not remove_organisation_references():
        success = False
    
    # 4. Calculer les KPIs initiaux
    if not calculate_initial_kpis():
        success = False
    
    logger.info("=" * 60)
    
    if success:
        logger.info("🎉 Migration réussie !")
        print("\n✅ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("🔗 Vous pouvez maintenant démarrer le serveur")
        print("📊 Les KPIs sont calculés et prêts")
    else:
        logger.error("❌ Migration échouée")
        print("\n💥 MIGRATION ÉCHOUÉE")
        print("🔧 Vérifiez les erreurs ci-dessus")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)