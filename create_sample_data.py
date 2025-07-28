#!/usr/bin/env python3
"""
Script pour créer des données de simulation
Génère des organisations, services, utilisateurs et plaintes de test
"""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database_unified import SessionLocal
from models_unified import (
    Base, Organisation, Service, Utilisateur, Plainte, 
    FichierPlainte, AuditLog,
    StatutPlainteEnum, PrioriteEnum, TypeServiceEnum, TypeUtilisateurEnum
)
import uuid

def create_sample_data():
    """Créer des données de simulation complètes"""
    
    db = SessionLocal()
    
    try:
        print("🏥 Création des données de simulation...")
        
        # ==================== ORGANISATIONS ====================
        print("📋 Création des organisations...")
        
        organisations = [
            Organisation(
                nom="Centre Hospitalier Universitaire de Paris",
                nom_court="CHU Paris",
                code_etablissement="CHU-PARIS-001",
                email="contact@chu-paris.fr",
                telephone="01 42 34 56 78",
                adresse="123 Avenue de la Santé, 75001 Paris",
                site_web="https://www.chu-paris.fr",
                finess="750000001",
                configuration={
                    "theme": "blue",
                    "notifications": True,
                    "timezone": "Europe/Paris"
                }
            ),
            Organisation(
                nom="Clinique Saint-Joseph",
                nom_court="Clinique St-Joseph",
                code_etablissement="CLIN-SJ-002",
                email="info@clinique-saint-joseph.fr",
                telephone="01 45 67 89 01",
                adresse="456 Rue de la Paix, 75002 Paris",
                site_web="https://www.clinique-saint-joseph.fr",
                finess="750000002",
                configuration={
                    "theme": "green",
                    "notifications": True,
                    "timezone": "Europe/Paris"
                }
            ),
            Organisation(
                nom="Hôpital Général de Lyon",
                nom_court="Hôpital Lyon",
                code_etablissement="HOP-LYON-003",
                email="contact@hopital-lyon.fr",
                telephone="04 78 12 34 56",
                adresse="789 Boulevard de la Santé, 69001 Lyon",
                site_web="https://www.hopital-lyon.fr",
                finess="690000001",
                configuration={
                    "theme": "red",
                    "notifications": True,
                    "timezone": "Europe/Paris"
                }
            )
        ]
        
        for org in organisations:
            db.add(org)
        db.commit()
        
        print(f"✅ {len(organisations)} organisations créées")
        
        # ==================== SERVICES ====================
        print("🏥 Création des services...")
        
        services = []
        for org in organisations:
            org_services = [
                Service(
                    organisation_id=org.id,
                    nom="Service d'Urgences",
                    code_service="URG",
                    type_service=TypeServiceEnum.URGENCES,
                    description="Service d'urgences médicales et chirurgicales",
                    batiment="Bâtiment A",
                    etage="Rez-de-chaussée",
                    secteur="Urgences"
                ),
                Service(
                    organisation_id=org.id,
                    nom="Service de Cardiologie",
                    code_service="CARD",
                    type_service=TypeServiceEnum.CARDIOLOGIE,
                    description="Service de cardiologie et maladies cardiovasculaires",
                    batiment="Bâtiment B",
                    etage="2ème étage",
                    secteur="Médecine"
                ),
                Service(
                    organisation_id=org.id,
                    nom="Service de Pédiatrie",
                    code_service="PED",
                    type_service=TypeServiceEnum.PEDIATRIE,
                    description="Service de pédiatrie générale et spécialisée",
                    batiment="Bâtiment C",
                    etage="1er étage",
                    secteur="Pédiatrie"
                ),
                Service(
                    organisation_id=org.id,
                    nom="Service de Chirurgie",
                    code_service="CHIR",
                    type_service=TypeServiceEnum.CHIRURGIE,
                    description="Service de chirurgie générale et spécialisée",
                    batiment="Bâtiment D",
                    etage="3ème étage",
                    secteur="Chirurgie"
                ),
                Service(
                    organisation_id=org.id,
                    nom="Service de Radiologie",
                    code_service="RAD",
                    type_service=TypeServiceEnum.RADIOLOGIE,
                    description="Service de radiologie et imagerie médicale",
                    batiment="Bâtiment E",
                    etage="Rez-de-chaussée",
                    secteur="Imagerie"
                )
            ]
            services.extend(org_services)
        
        for service in services:
            db.add(service)
        db.commit()
        
        print(f"✅ {len(services)} services créés")
        
        # ==================== UTILISATEURS ====================
        print("👥 Création des utilisateurs...")
        
        utilisateurs = []
        for org in organisations:
            org_users = [
                Utilisateur(
                    organisation_id=org.id,
                    service_id=services[0].id if org.id == services[0].organisation_id else None,
                    nom="Dupont",
                    prenom="Jean",
                    nom_complet="Jean Dupont",
                    email=f"jean.dupont@{org.nom_court.lower().replace(' ', '-')}.fr",
                    mot_de_passe_hash="hashed_password_123",
                    telephone="01 23 45 67 89",
                    telephone_mobile="06 12 34 56 78",
                    type_utilisateur=TypeUtilisateurEnum.SUPER_ADMIN,
                    fonction="Directeur Général",
                    specialite=None,
                    numero_rpps=None,
                    permissions=["ALL"],
                    configuration={
                        "notifications_email": True,
                        "notifications_sms": False,
                        "langue_preferee": "fr",
                        "theme": "light"
                    }
                ),
                Utilisateur(
                    organisation_id=org.id,
                    service_id=services[1].id if org.id == services[1].organisation_id else None,
                    nom="Martin",
                    prenom="Marie",
                    nom_complet="Marie Martin",
                    email=f"marie.martin@{org.nom_court.lower().replace(' ', '-')}.fr",
                    mot_de_passe_hash="hashed_password_456",
                    telephone="01 98 76 54 32",
                    telephone_mobile="06 98 76 54 32",
                    type_utilisateur=TypeUtilisateurEnum.CHEF_SERVICE,
                    fonction="Chef de Service Cardiologie",
                    specialite="Cardiologie",
                    numero_rpps="12345678901",
                    permissions=["GESTION_PLAINTES", "CONSULTER_PLAINTES", "ASSIGNER_PLAINTES"],
                    configuration={
                        "notifications_email": True,
                        "notifications_sms": True,
                        "langue_preferee": "fr",
                        "theme": "dark"
                    }
                ),
                Utilisateur(
                    organisation_id=org.id,
                    service_id=services[2].id if org.id == services[2].organisation_id else None,
                    nom="Bernard",
                    prenom="Sophie",
                    nom_complet="Sophie Bernard",
                    email=f"sophie.bernard@{org.nom_court.lower().replace(' ', '-')}.fr",
                    mot_de_passe_hash="hashed_password_789",
                    telephone="01 11 22 33 44",
                    telephone_mobile="06 11 22 33 44",
                    type_utilisateur=TypeUtilisateurEnum.MEDECIN,
                    fonction="Médecin Pédiatre",
                    specialite="Pédiatrie",
                    numero_rpps="98765432109",
                    permissions=["CONSULTER_PLAINTES", "TRAITER_PLAINTES"],
                    configuration={
                        "notifications_email": True,
                        "notifications_sms": False,
                        "langue_preferee": "fr",
                        "theme": "light"
                    }
                ),
                Utilisateur(
                    organisation_id=org.id,
                    service_id=services[3].id if org.id == services[3].organisation_id else None,
                    nom="Petit",
                    prenom="Pierre",
                    nom_complet="Pierre Petit",
                    email=f"pierre.petit@{org.nom_court.lower().replace(' ', '-')}.fr",
                    mot_de_passe_hash="hashed_password_101",
                    telephone="01 55 66 77 88",
                    telephone_mobile="06 55 66 77 88",
                    type_utilisateur=TypeUtilisateurEnum.RESPONSABLE_QUALITE,
                    fonction="Responsable Qualité",
                    specialite=None,
                    numero_rpps=None,
                    permissions=["GESTION_PLAINTES", "CONSULTER_PLAINTES", "ANALYSE_QUALITE"],
                    configuration={
                        "notifications_email": True,
                        "notifications_sms": True,
                        "langue_preferee": "fr",
                        "theme": "blue"
                    }
                )
            ]
            utilisateurs.extend(org_users)
        
        for user in utilisateurs:
            db.add(user)
        db.commit()
        
        print(f"✅ {len(utilisateurs)} utilisateurs créés")
        
        # ==================== PLAINTES ====================
        print("📝 Création des plaintes...")
        
        titres_plaintes = [
            "Temps d'attente trop long aux urgences",
            "Mauvaise communication du personnel médical",
            "Erreur de diagnostic",
            "Conditions d'hygiène insuffisantes",
            "Médicament administré en retard",
            "Perte de dossier médical",
            "Attitude inappropriée du personnel",
            "Erreur de prescription",
            "Manque d'information sur le traitement",
            "Problème de confidentialité",
            "Retard dans la prise en charge",
            "Équipement médical défaillant",
            "Erreur dans les résultats d'analyse",
            "Manque de personnel",
            "Problème de coordination entre services"
        ]
        
        descriptions_plaintes = [
            "J'ai attendu plus de 4 heures aux urgences sans être pris en charge correctement.",
            "Le personnel médical n'a pas pris le temps de m'expliquer mon diagnostic.",
            "Le médecin a fait une erreur de diagnostic qui a retardé mon traitement.",
            "Les conditions d'hygiène dans ma chambre étaient insuffisantes.",
            "Mon médicament a été administré avec 2 heures de retard.",
            "Mon dossier médical a été perdu, causant des retards dans ma prise en charge.",
            "Un membre du personnel a eu une attitude inappropriée envers moi.",
            "Le médecin a fait une erreur dans la prescription de mes médicaments.",
            "Je n'ai pas reçu suffisamment d'informations sur mon traitement.",
            "Mes informations personnelles ont été divulguées sans mon consentement.",
            "Il y a eu un retard important dans ma prise en charge initiale.",
            "L'équipement médical utilisé était défaillant.",
            "Les résultats de mes analyses contenaient des erreurs.",
            "Il y avait un manque de personnel pour nous prendre en charge.",
            "Il y a eu un problème de coordination entre les différents services."
        ]
        
        plaintes = []
        statuts = list(StatutPlainteEnum)
        priorites = list(PrioriteEnum)
        
        for i in range(50):  # Créer 50 plaintes
            org = random.choice(organisations)
            service = random.choice([s for s in services if s.organisation_id == org.id])
            utilisateur = random.choice([u for u in utilisateurs if u.organisation_id == org.id])
            
            # Date d'incident aléatoire dans les 30 derniers jours
            date_incident = datetime.now() - timedelta(days=random.randint(1, 30))
            
            # Date de création après l'incident
            date_creation = date_incident + timedelta(days=random.randint(0, 7))
            
            # Date de modification
            date_modification = date_creation + timedelta(days=random.randint(0, 14))
            
            # Date de résolution (seulement pour les plaintes traitées)
            date_resolution = None
            statut = random.choice(statuts)
            if statut in [StatutPlainteEnum.TRAITEE, StatutPlainteEnum.RESOLUE]:
                date_resolution = date_modification + timedelta(days=random.randint(1, 10))
            
            plainte = Plainte(
                numero_plainte=f"PL-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}",
                numero_interne=f"INT-{i+1:04d}",
                organisation_id=org.id,
                service_id=service.id,
                statut=statut,
                priorite=random.choice(priorites),
                titre=random.choice(titres_plaintes),
                description=random.choice(descriptions_plaintes),
                circonstances=f"Incident survenu le {date_incident.strftime('%d/%m/%Y')}",
                consequences="Retard dans la prise en charge",
                demande_plaignant="Amélioration de la qualité des soins",
                categorie_principale=random.choice(["Soins", "Communication", "Organisation", "Équipement", "Personnel"]),
                sous_categorie=random.choice(["Urgences", "Consultation", "Hospitalisation", "Ambulatoire"]),
                mots_cles=random.sample(["attente", "communication", "diagnostic", "hygiène", "médicament", "personnel"], 3),
                date_incident=date_incident.date(),
                date_limite_reponse=date_incident + timedelta(days=30),
                assignee_a_id=utilisateur.id,
                cree_par_id=utilisateur.id,
                score_sentiment=random.uniform(-1.0, 1.0),
                score_urgence_ia=random.uniform(0.0, 1.0),
                analyse_ia={
                    "sentiment": "négatif" if random.random() > 0.5 else "positif",
                    "urgence": random.choice(["faible", "moyenne", "élevée", "critique"]),
                    "categorie_suggeree": random.choice(["soins", "communication", "organisation"]),
                    "mots_cles_detectes": ["attente", "personnel", "soins"]
                },
                date_creation=date_creation,
                date_modification=date_modification,
                date_resolution=date_resolution
            )
            plaintes.append(plainte)
        
        for plainte in plaintes:
            db.add(plainte)
        db.commit()
        
        print(f"✅ {len(plaintes)} plaintes créées")
        
        # ==================== FICHIERS PLAINTES ====================
        print("📎 Création des fichiers de plaintes...")
        
        fichiers = []
        for i, plainte in enumerate(plaintes[:20]):  # Ajouter des fichiers pour 20 plaintes
            fichier = FichierPlainte(
                plainte_id=plainte.id,
                nom_original=f"plainte_{plainte.numero_plainte}.pdf",
                nom_stockage=f"PL-{plainte.numero_plainte}_{i}.pdf",
                chemin_relatif=f"uploads/PL-{plainte.numero_plainte}_{i}.pdf",
                type_fichier="PDF",
                mime_type="application/pdf",
                taille_octets=random.randint(50000, 500000),
                checksum_md5="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                checksum_sha256="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                texte_extrait=f"Contenu extrait de la plainte {plainte.numero_plainte}",
                metadonnees_extraction={
                    "pages": random.randint(1, 5),
                    "langue": "fr",
                    "confiance": random.uniform(0.8, 1.0)
                },
                est_traite=True,
                date_traitement=datetime.now() - timedelta(days=random.randint(1, 10)),
                est_chiffre=False,
                niveau_confidentialite="PUBLIC",
                uploade_par_id=plainte.cree_par_id
            )
            fichiers.append(fichier)
        
        for fichier in fichiers:
            db.add(fichier)
        db.commit()
        
        print(f"✅ {len(fichiers)} fichiers créés")
        
        # ==================== AUDIT LOGS ====================
        print("📊 Création des logs d'audit...")
        
        logs = []
        actions = ["CREATE", "UPDATE", "ASSIGN", "STATUS_CHANGE", "VIEW"]
        ressources = ["PLAINTE", "UTILISATEUR", "SERVICE", "ORGANISATION"]
        
        for i in range(100):  # Créer 100 logs d'audit
            utilisateur = random.choice(utilisateurs)
            log = AuditLog(
                utilisateur_id=utilisateur.id,
                session_id=f"session_{uuid.uuid4().hex[:8]}",
                action=random.choice(actions),
                ressource_type=random.choice(ressources),
                ressource_id=str(random.randint(1, 100)),
                description=f"Action {random.choice(actions)} sur {random.choice(ressources)}",
                donnees_avant={"status": "old"},
                donnees_apres={"status": "new"},
                adresse_ip=f"192.168.1.{random.randint(1, 255)}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                date_action=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            logs.append(log)
        
        for log in logs:
            db.add(log)
        db.commit()
        
        print(f"✅ {len(logs)} logs d'audit créés")
        
        print("\n🎉 Données de simulation créées avec succès !")
        print(f"📊 Résumé :")
        print(f"   - {len(organisations)} organisations")
        print(f"   - {len(services)} services")
        print(f"   - {len(utilisateurs)} utilisateurs")
        print(f"   - {len(plaintes)} plaintes")
        print(f"   - {len(fichiers)} fichiers")
        print(f"   - {len(logs)} logs d'audit")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des données : {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data() 