-- =============================================================================
-- Script d'initialisation PostgreSQL pour HealthCare AI
-- À exécuter en tant qu'administrateur PostgreSQL
-- =============================================================================

-- 1. Créer l'utilisateur healthcare_user avec mot de passe sécurisé
CREATE USER healthcare_user WITH ENCRYPTED PASSWORD 'HealthCare2025!';

-- 2. Créer la base de données
CREATE DATABASE hospital_complaints 
    WITH OWNER = healthcare_user
    ENCODING = 'UTF8'
    LC_COLLATE = 'fr_FR.UTF-8'
    LC_CTYPE = 'fr_FR.UTF-8'
    TEMPLATE = template0;

-- 3. Accorder les privilèges sur la base de données
GRANT ALL PRIVILEGES ON DATABASE hospital_complaints TO healthcare_user;

-- 4. Se connecter à la base hospital_complaints
\c hospital_complaints

-- 5. Accorder les privilèges sur le schéma public
GRANT ALL ON SCHEMA public TO healthcare_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO healthcare_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO healthcare_user;

-- 6. Privilèges par défaut pour les futures tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO healthcare_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO healthcare_user;

-- 7. Créer les extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- Pour générer des UUIDs
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Pour la recherche full-text

-- 8. Afficher les informations de connexion
\echo '============================================'
\echo 'Initialisation PostgreSQL terminée !'
\echo '============================================'
\echo 'Base de données: hospital_complaints'
\echo 'Utilisateur: healthcare_user'
\echo 'Mot de passe: HealthCare2025!'
\echo 'Host: localhost'
\echo 'Port: 5430'
\echo '============================================' 