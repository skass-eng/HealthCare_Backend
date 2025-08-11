#!/usr/bin/env python3
"""
Script de migration pour supprimer la table organisation
et mettre à jour les services avec les nouveaux KPIs
Version: 2.0.0 - Architecture ODYSSEE simplifiée
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from healthcare_api_server.app.db.database import SessionLocal, engine
from shared.models import Base, Service, Plainte
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migrer la base de données vers la nouvelle architecture sans organisation"""
    
    db = SessionLocal()
    inspector = inspect(engine)
    
    try:
        logger.info("🔄 Début de la migration de la base de données...")
        
        # 1. Vérifier si les colonnes KPI existent déjà
        service_columns = [col['name'] for col in inspector.get_columns('services')]
        
        if 'nombre_plaintes_total' not in service_columns:
            logger.info("📊 Ajout des colonnes KPI aux services...")
            
            # Ajouter les nouvelles colonnes KPI
            db.execute(text("""
                ALTER TABLE services 
                ADD COLUMN nombre_plaintes_total INTEGER DEFAULT 0,
                ADD COLUMN nombre_plaintes_resolues INTEGER DEFAULT 0,
                ADD COLUMN temps_moyen_resolution REAL DEFAULT 0.0,
                ADD COLUMN taux_satisfaction REAL DEFAULT 0.0
            """))
            
            # Mettre à jour les contraintes
            db.execute(text("""
                ALTER TABLE services 
                ALTER COLUMN nombre_plaintes_total SET NOT NULL,
                ALTER COLUMN nombre_plaintes_resolues SET NOT NULL,
                ALTER COLUMN temps_moyen_resolution SET NOT NULL,
                ALTER COLUMN taux_satisfaction SET NOT NULL
            """))
            
            logger.info("✅ Colonnes KPI ajoutées avec succès")
        
        # 2. Supprimer la contrainte de clé étrangère organisation_id des services
        if 'organisation_id' in service_columns:
            logger.info("🔗 Suppression de la référence organisation dans services...")
            
            # Créer une nouvelle table services sans organisation_id
            db.execute(text("""
                CREATE TABLE services_new (
                    id INTEGER PRIMARY KEY,
                    nom VARCHAR(255) NOT NULL,
                    code_service VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT,
                    categorie VARCHAR(100),
                    nombre_plaintes_total INTEGER DEFAULT 0 NOT NULL,
                    nombre_plaintes_resolues INTEGER DEFAULT 0 NOT NULL,
                    temps_moyen_resolution REAL DEFAULT 0.0 NOT NULL,
                    taux_satisfaction REAL DEFAULT 0.0 NOT NULL,
                    configuration JSONB DEFAULT '{}',
                    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    est_actif BOOLEAN DEFAULT TRUE NOT NULL
                )
            """))
            
            # Copier les données existantes
            db.execute(text("""
                INSERT INTO services_new (
                    id, nom, code_service, description, categorie,
                    nombre_plaintes_total, nombre_plaintes_resolues,
                    temps_moyen_resolution, taux_satisfaction,
                    configuration, date_creation, date_modification, est_actif
                )
                SELECT 
                    id, nom, code_service, description, categorie,
                    COALESCE(nombre_plaintes_total, 0),
                    COALESCE(nombre_plaintes_resolues, 0),
                    COALESCE(temps_moyen_resolution, 0.0),
                    COALESCE(taux_satisfaction, 0.0),
                    configuration, date_creation, date_modification, est_actif
                FROM services
            """))
            
            # Supprimer l'ancienne table et renommer
            db.execute(text("DROP TABLE services"))
            db.execute(text("ALTER TABLE services_new RENAME TO services"))
            
            # Recréer les index
            db.execute(text("CREATE INDEX idx_service_code ON services(code_service)"))
            db.execute(text("CREATE INDEX idx_service_actif ON services(est_actif)"))
            
            logger.info("✅ Table services migrée sans organisation_id")
        
        # 3. Mettre à jour les plaintes pour rendre service_id obligatoire
        plainte_columns = [col['name'] for col in inspector.get_columns('plaintes')]
        
        if 'organisation_id' in plainte_columns:
            logger.info("🏥 Mise à jour des plaintes...")
            
            # Assigner toutes les plaintes sans service au premier service disponible
            result = db.execute(text("SELECT id FROM services WHERE est_actif = true LIMIT 1"))
            first_service = result.fetchone()
            
            if first_service:
                service_id = first_service[0]
                
                # Mettre à jour les plaintes sans service
                db.execute(text(f"""
                    UPDATE plaintes 
                    SET service_id = {service_id}
                    WHERE service_id IS NULL
                """))
                
                logger.info(f"✅ Plaintes sans service assignées au service ID {service_id}")
            
            # Supprimer la colonne organisation_id des plaintes
            db.execute(text("ALTER TABLE plaintes DROP COLUMN organisation_id"))
            
            # Rendre service_id obligatoire
            db.execute(text("ALTER TABLE plaintes ALTER COLUMN service_id SET NOT NULL"))
            
            # Recréer l'index
            db.execute(text("DROP INDEX IF EXISTS idx_plainte_organisation_date"))
            db.execute(text("CREATE INDEX idx_plainte_service_date ON plaintes(service_id, date_creation)"))
            
            logger.info("✅ Table plaintes migrée")
        
        # 4. Calculer les KPIs initiaux pour tous les services
        logger.info("📊 Calcul des KPIs initiaux...")
        
        services = db.execute(text("SELECT id FROM services WHERE est_actif = true")).fetchall()
        
        for (service_id,) in services:
            # Calculer les KPIs pour ce service
            total_plaintes = db.execute(text(f"""
                SELECT COUNT(*) FROM plaintes WHERE service_id = {service_id}
            """)).scalar()
            
            plaintes_resolues = db.execute(text(f"""
                SELECT COUNT(*) FROM plaintes 
                WHERE service_id = {service_id} AND statut = 'RESOLU'
            """)).scalar()
            
            avg_resolution = db.execute(text(f"""
                SELECT AVG(EXTRACT(EPOCH FROM date_resolution - date_creation) / 86400)
                FROM plaintes 
                WHERE service_id = {service_id} AND date_resolution IS NOT NULL
            """)).scalar()
            
            avg_sentiment = db.execute(text(f"""
                SELECT AVG(score_sentiment)
                FROM plaintes 
                WHERE service_id = {service_id} AND score_sentiment IS NOT NULL
            """)).scalar()
            
            temps_moyen = round(float(avg_resolution or 0), 2)
            taux_satisfaction = round(((float(avg_sentiment or 0) + 1) / 2) * 100, 2) if avg_sentiment else 0.0
            
            # Mettre à jour le service
            db.execute(text(f"""
                UPDATE services SET
                    nombre_plaintes_total = {total_plaintes or 0},
                    nombre_plaintes_resolues = {plaintes_resolues or 0},
                    temps_moyen_resolution = {temps_moyen},
                    taux_satisfaction = {taux_satisfaction}
                WHERE id = {service_id}
            """))
            
            logger.info(f"✅ KPIs calculés pour service ID {service_id}: {total_plaintes} plaintes, {plaintes_resolues} résolues")
        
        # 5. Supprimer la table organisations si elle existe
        if 'organisations' in inspector.get_table_names():
            logger.info("🗑️  Suppression de la table organisations...")
            db.execute(text("DROP TABLE organisations"))
            logger.info("✅ Table organisations supprimée")
        
        # Valider toutes les modifications
        db.commit()
        
        logger.info("🎉 Migration terminée avec succès !")
        logger.info("📋 Résumé des modifications:")
        logger.info("   - Table organisations supprimée")
        logger.info("   - Services migrés avec KPIs")
        logger.info("   - Plaintes mises à jour")
        logger.info("   - KPIs calculés pour tous les services")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise
    finally:
        db.close()

def verify_migration():
    """Vérifier que la migration s'est bien déroulée"""
    
    db = SessionLocal()
    inspector = inspect(engine)
    
    try:
        logger.info("🔍 Vérification de la migration...")
        
        # Vérifier que la table organisations n'existe plus
        tables = inspector.get_table_names()
        if 'organisations' in tables:
            logger.warning("⚠️  La table organisations existe encore")
            return False
        
        # Vérifier les colonnes de la table services
        service_columns = [col['name'] for col in inspector.get_columns('services')]
        required_columns = ['nombre_plaintes_total', 'nombre_plaintes_resolues', 'temps_moyen_resolution', 'taux_satisfaction']
        
        missing_columns = [col for col in required_columns if col not in service_columns]
        if missing_columns:
            logger.warning(f"⚠️  Colonnes manquantes dans services: {missing_columns}")
            return False
        
        if 'organisation_id' in service_columns:
            logger.warning("⚠️  La colonne organisation_id existe encore dans services")
            return False
        
        # Vérifier les colonnes de la table plaintes
        plainte_columns = [col['name'] for col in inspector.get_columns('plaintes')]
        if 'organisation_id' in plainte_columns:
            logger.warning("⚠️  La colonne organisation_id existe encore dans plaintes")
            return False
        
        # Compter les services et plaintes
        services_count = db.execute(text("SELECT COUNT(*) FROM services")).scalar()
        plaintes_count = db.execute(text("SELECT COUNT(*) FROM plaintes")).scalar()
        
        logger.info(f"✅ Migration vérifiée avec succès!")
        logger.info(f"   - {services_count} services dans la base")
        logger.info(f"   - {plaintes_count} plaintes dans la base")
        logger.info(f"   - Table organisations supprimée")
        logger.info(f"   - KPIs disponibles pour tous les services")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de la migration vers l'architecture sans organisation")
    
    try:
        migrate_database()
        
        if verify_migration():
            logger.info("🎯 Migration complète et vérifiée avec succès!")
            print("\n" + "="*60)
            print("✅ MIGRATION RÉUSSIE - Architecture simplifiée activée")
            print("🔗 Les services peuvent maintenant être gérés via /api/v1/services")
            print("📊 Les KPIs sont automatiquement calculés et mis à jour")
            print("="*60)
        else:
            logger.error("❌ Problèmes détectés lors de la vérification")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Échec de la migration: {e}")
        sys.exit(1)