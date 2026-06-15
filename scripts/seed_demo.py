#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED DEMO - HealthCare AI (variante odyssee)
=============================================

Script de seed DETERMINISTE et REJOUABLE destine a preparer une demo jury.

Ce qu'il fait :
  1. VIDAGE TOTAL PROPRE de la base (DROP SCHEMA public CASCADE ; CREATE SCHEMA public)
     puis recreation UNIQUEMENT des tables/enums du modele via Base.metadata.create_all.
  2. Re-remplissage controle (organisation, services, utilisateurs, plaintes,
     analyses IA, documents pointant vers de vrais PDF, resultat d'analyse globale).
  3. VACUUM ANALYZE final + recapitulatif (comptes + identifiants jury).

IMPORTANT :
  - Utilise TOUJOURS l'ENGINE de l'application (jamais une URL en dur).
  - Utilise get_password_hash() du backend (NE PAS reinstancier un CryptContext,
    sinon le login renverrait une 500).
  - random.seed(42) pour une demo 100% reproductible.
  - AUCUNE date future : la date du jour de reference est 2026-06-14, on s'appuie
    sur datetime.now() borne a cette journee.

ATTENTION : ce script DETRUIT toutes les donnees existantes. Il N'EST PAS lance
automatiquement ; il faut l'executer explicitement.
"""

import os
import sys
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration des imports : on ajoute la racine du backend (HealthCare_Backend)
# au sys.path, exactement comme le fait scripts/init_db.py.
# --------------------------------------------------------------------------- #
BACKEND_ROOT = Path(__file__).resolve().parent.parent           # .../HealthCare_Backend
REPO_ROOT = BACKEND_ROOT.parent                                 # .../odyssee
sys.path.append(str(BACKEND_ROOT))

# Engine et session de l'application (jamais d'URL en dur)
from healthcare_api_server.app.db.database import engine, SessionLocal  # noqa: E402
# Hash de mot de passe officiel du backend (NE PAS reinstancier un CryptContext)
from healthcare_api_server.app.core.auth import get_password_hash       # noqa: E402
# Modeles + enums partages
from shared.models import (  # noqa: E402
    Base,
    Organisation,
    Service,
    User,
    Plainte,
    AnalyseIA,
    DocumentPlainte,
    AIAnalysisResult,
    UserRole,
    StatutPlainte,
    PrioritePlainte,
    TypeFichier,
)
from sqlalchemy import text  # noqa: E402

# --------------------------------------------------------------------------- #
# Constantes de demo
# --------------------------------------------------------------------------- #
random.seed(42)  # Reproductibilite totale

# Date du jour de reference de la demo (cf. contrat commun)
TODAY = datetime(2026, 6, 14, 12, 0, 0)

# Mot de passe en clair du compte jury (memorable, affiche a la fin)
JURY_EMAIL = "admin@chu.fr"
JURY_PASSWORD = "demo1234"

# Repertoire des PDF reels existants
PDF_DIR = REPO_ROOT / "data" / "documents" / "pdf_originaux"
PDF_FILES = [
    "PL_2025_0119_plainte_contre_la_clinique_V10032022.pdf",
    "PL_2025_0131_plainte_contre_la_clinique_V10032022.pdf",
    "PL_2025_0133_plainte_contre_la_clinique_V10032022.pdf",
]


# --------------------------------------------------------------------------- #
# Etape 1 : vidage total propre + recreation des tables du modele
# --------------------------------------------------------------------------- #
def reset_schema():
    """
    DROP SCHEMA public CASCADE puis CREATE SCHEMA public.

    Cela supprime :
      - les tables divergentes du modele,
      - les eventuelles tables hors-modele,
      - les enums orphelins (buggys) qui empechent un create_all propre.

    Puis Base.metadata.create_all recree UNIQUEMENT les tables + enums du modele.
    """
    print(">>> ETAPE 1/10 : vidage total propre du schema 'public'...")
    # DROP/CREATE SCHEMA doit etre en autocommit (DDL global)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
    print("    Schema public recree (vide).")

    # Recreation des tables + enums du modele partage uniquement
    Base.metadata.create_all(bind=engine)
    nb_tables = len(Base.metadata.tables)
    print(f"    Tables du modele recreees : {nb_tables} tables.")


# --------------------------------------------------------------------------- #
# Etape 2 : organisation
# --------------------------------------------------------------------------- #
def seed_organisation(db):
    print(">>> ETAPE 2/10 : creation de l'organisation (id=1)...")
    orga = Organisation(
        id=1,  # Forcer id=1
        nom="Centre Hospitalier Universitaire",
        code_etablissement="CHU001",
        est_actif=True,
        configuration={
            "delai_reponse_standard": 30,
            "services_actifs": [
                "ADMINISTRATION", "URGENCES", "CARDIOLOGIE",
                "PEDIATRIE", "CHIRURGIE", "RADIOLOGIE",
            ],
            "workflow_automatique": True,
        },
    )
    db.add(orga)
    db.flush()
    print(f"    Organisation : {orga.nom} (id={orga.id})")
    return orga


# --------------------------------------------------------------------------- #
# Etape 3 : services
# --------------------------------------------------------------------------- #
def _service_config(email, tel):
    """Configuration JSONB standard d'un service (objectif/seuil exiges)."""
    return {
        "email_contact": email,
        "telephone_contact": tel,
        "objectif_resolution": 30,  # jours
        "seuil_urgence": 3,
    }


def seed_services(db):
    """
    6 services actifs. On FORCE id=1 = 'Administration / Qualite' (code 'ADM')
    car c'est le fallback attendu cote front.

    NB : on ne pre-remplit PAS les KPI denormalises
    (nombre_plaintes_total / _resolues / temps_moyen_resolution / taux_satisfaction)
    : ils restent a 0 et sont recalcules a chaque GET /services.
    """
    print(">>> ETAPE 3/10 : creation des 6 services...")
    services_data = [
        # (id_force, nom, code, categorie, email, tel)
        (1, "Administration / Qualite", "ADM", "ADMINISTRATION",
         "qualite@chu.fr", "0102030401"),
        (None, "Urgences", "URG", "URGENCES",
         "urgences@chu.fr", "0102030402"),
        (None, "Cardiologie", "CARDIO", "CARDIOLOGIE",
         "cardiologie@chu.fr", "0102030403"),
        (None, "Pediatrie", "PED", "PEDIATRIE",
         "pediatrie@chu.fr", "0102030404"),
        (None, "Chirurgie", "CHIR", "CHIRURGIE",
         "chirurgie@chu.fr", "0102030405"),
        (None, "Radiologie", "RADIO", "RADIOLOGIE",
         "radiologie@chu.fr", "0102030406"),
    ]

    # NB : sur un schema fraichement recree, la sequence services.id demarre a 1.
    # On NE FORCE PAS id=1 (cela n'avance pas la sequence -> collision au 2e insert).
    # On insere simplement Administration EN PREMIER : elle obtient id=1 naturellement.
    services = {}  # nom -> objet Service
    for _id_force, nom, code, categorie, email, tel in services_data:
        svc = Service(
            nom=nom,
            code_service=code,
            categorie=categorie,
            description=f"Service {nom} du CHU",
            est_actif=True,
            configuration=_service_config(email, tel),
        )
        db.add(svc)
        db.flush()
        services[nom] = svc
        print(f"    Service : {nom} (id={svc.id}, code={code})")

    # Garantie : le service de fallback front (Administration) doit avoir id=1.
    admin_svc = services["Administration / Qualite"]
    if admin_svc.id != 1:
        raise RuntimeError(
            f"Le service Administration/Qualite a id={admin_svc.id} (attendu 1). "
            "Le fallback front service_concerne_id='1' serait casse."
        )

    return services


# --------------------------------------------------------------------------- #
# Etape 4 : utilisateurs
# --------------------------------------------------------------------------- #
def seed_users(db, services):
    """
    5 utilisateurs, tous actifs, rattaches a l'organisation 1.
    Mots de passe hashes via get_password_hash (backend) -> login OK.
    """
    print(">>> ETAPE 4/10 : creation des 5 utilisateurs...")

    # (nom, prenom, email, role, service_nom, fonction, mdp_clair)
    users_data = [
        ("Admin", "Demo", JURY_EMAIL, UserRole.ADMIN,
         "Administration / Qualite", "Administrateur", JURY_PASSWORD),
        ("Bernard", "Sophie", "sophie.bernard@chu.fr", UserRole.MEDECIN,
         "Cardiologie", "Medecin", "demo1234"),
        ("Martin", "Marie", "marie.martin@chu.fr", UserRole.RESPONSABLE_QUALITE,
         "Administration / Qualite", "Responsable Qualite", "demo1234"),
        ("Dupont", "Jean", "jean.dupont@chu.fr", UserRole.CHEF_SERVICE,
         "Urgences", "Chef de service", "demo1234"),
        ("Petit", "Claire", "claire.petit@chu.fr", UserRole.UTILISATEUR,
         "Chirurgie", "Agent d'accueil", "demo1234"),
    ]

    users = []
    for nom, prenom, email, role, svc_nom, fonction, mdp in users_data:
        # nom_complet est coherent avec le format 'Prenom Nom'
        nom_complet = f"{prenom} {nom}" if prenom != "Demo" else "Demo Admin"
        svc = services.get(svc_nom)
        u = User(
            organisation_id=1,
            service_id=svc.id if svc else None,
            nom=nom,
            prenom=prenom,
            nom_complet=nom_complet,
            email=email,
            mot_de_passe_hash=get_password_hash(mdp),  # hash backend officiel
            type_utilisateur=role,
            fonction=fonction,
            statut="actif",
            est_actif=True,
            email_verifie=True,
            date_suppression=None,
            permissions={},
            configuration={},
        )
        db.add(u)
        db.flush()
        users.append(u)
        print(f"    User : {nom_complet} <{email}> ({role.value})")

    return users


# --------------------------------------------------------------------------- #
# Etape 5 : plaintes
# --------------------------------------------------------------------------- #

# Repartition exacte des statuts (total = 45)
STATUTS_PLAN = (
    [StatutPlainte.RECU] * 14
    + [StatutPlainte.EN_COURS] * 16
    + [StatutPlainte.TRAITE] * 11
    + [StatutPlainte.CLOTURE] * 4
)

# Repartition exacte des priorites (total = 45)
PRIORITES_PLAN = (
    [PrioritePlainte.URGENT] * 7
    + [PrioritePlainte.ELEVE] * 11
    + [PrioritePlainte.MOYEN] * 18
    + [PrioritePlainte.BAS] * 9
)

# Repartition des services (total = 45)
# Urgences 13, Chirurgie 9, Cardiologie 7, Pediatrie 6, Radiologie 6, Administration 4
SERVICES_PLAN = (
    ["Urgences"] * 13
    + ["Chirurgie"] * 9
    + ["Cardiologie"] * 7
    + ["Pediatrie"] * 6
    + ["Radiologie"] * 6
    + ["Administration / Qualite"] * 4
)

# Services critiques : biaiser vers le negatif
SERVICES_CRITIQUES = {"Urgences", "Chirurgie"}

# Plaignants fictifs (format 'Nom Prenom' demande pour nom_plaignant)
PLAIGNANTS = [
    ("Durand", "Pierre"), ("Lefevre", "Anne"), ("Moreau", "Luc"),
    ("Garnier", "Julie"), ("Rousseau", "Marc"), ("Blanc", "Emma"),
    ("Faure", "Paul"), ("Girard", "Lea"), ("Bonnet", "Hugo"),
    ("Dupuis", "Chloe"), ("Lambert", "Nathan"), ("Fontaine", "Sarah"),
    ("Robin", "Thomas"), ("Vincent", "Camille"), ("Muller", "Antoine"),
    ("Lemaire", "Manon"), ("Roux", "Maxime"), ("Mercier", "Ines"),
    ("Boyer", "Theo"), ("Brun", "Eva"), ("Gauthier", "Adam"),
    ("Perrin", "Lina"), ("Morel", "Noah"), ("Henry", "Jade"),
    ("Garcia", "Louis"),
]

MODES_RECEPTION = ["email", "courrier", "telephone", "accueil"]

# --------------------------------------------------------------------------- #
# Contenu PREMIUM de la plainte 'parfaite' (filet de securite demo).
# Description tres realiste ; la reponse_suggeree exemplaire est generee
# separement via _lettre_type(..., parfaite=True).
# --------------------------------------------------------------------------- #
PLAINTE_PARFAITE_CONTENU = {
    "titre": (
        "Prise en charge tardive aux urgences ayant aggrave l'etat d'un patient"
    ),
    "description": (
        "Le samedi 17 mai 2026, je me suis presente au service des urgences a "
        "21h05 pour de violentes douleurs thoraciques irradiant dans le bras "
        "gauche, accompagnees de sueurs et d'essoufflement. Apres un bref "
        "passage a l'accueil, on m'a demande de patienter en salle d'attente "
        "sans realiser de tri infirmier immediat. J'y suis reste plus de cinq "
        "heures, malgre mes appels repetes au guichet et l'aggravation visible "
        "de mon malaise. Ce n'est qu'a 02h20, apres l'insistance d'un autre "
        "patient, qu'une infirmiere a enfin pris ma tension et constate une "
        "situation preoccupante. L'electrocardiogramme realise dans la foulee "
        "a revele une souffrance cardiaque qui aurait du etre detectee des mon "
        "arrivee."
    ),
    "circonstances": (
        "Affluence importante un samedi soir, absence de tri infirmier a "
        "l'accueil (IOA), aucune reevaluation des patients en attente, "
        "communication inexistante sur les delais. Le registre de tri n'a pas "
        "ete renseigne a mon arrivee."
    ),
    "consequences": (
        "Retard de diagnostic d'un syndrome coronarien, hospitalisation en "
        "unite de soins intensifs cardiologiques, et selon le cardiologue une "
        "prise en charge plus precoce aurait limite les sequelles. "
        "Consequences psychologiques durables (anxiete, troubles du sommeil)."
    ),
    "demande_plaignant": (
        "Je demande : (1) la communication de mon dossier complet de passage "
        "aux urgences, (2) la saisine de la Commission des Usagers, (3) un "
        "entretien avec un mediateur medical, et (4) la mise en place de "
        "mesures correctives garantissant un tri infirmier systematique a "
        "l'arrivee."
    ),
}

# --------------------------------------------------------------------------- #
# Templates de contenu RICHE par service.
# Pour chaque service : listes de fragments selon le sentiment (negatif/neutre/positif).
# Chaque template fournit titre / description / circonstances / consequences /
# demande_plaignant pour nourrir l'analyse IA globale.
# --------------------------------------------------------------------------- #
TEMPLATES = {
    "Urgences": {
        "negatif": [
            {
                "titre": "Temps d'attente excessif aux urgences",
                "description": (
                    "Je me suis presente aux urgences avec de fortes douleurs "
                    "thoraciques et j'ai attendu plus de six heures avant d'etre "
                    "pris en charge. Le personnel etait deborde et personne ne "
                    "venait nous donner d'information sur l'avancement."
                ),
                "circonstances": (
                    "Arrivee un samedi soir vers 21h, salle d'attente saturee, "
                    "aucun tri visible, plusieurs patients sont repartis sans soins."
                ),
                "consequences": (
                    "Aggravation de mon etat de stress et douleur non soulagee "
                    "pendant toute l'attente."
                ),
                "demande_plaignant": (
                    "Je demande une revision de l'organisation du tri et des "
                    "excuses formelles de l'etablissement."
                ),
            },
            {
                "titre": "Manque de communication du personnel aux urgences",
                "description": (
                    "Lors de ma venue aux urgences, aucun soignant ne m'a explique "
                    "le diagnostic ni le traitement administre. Je suis ressorti "
                    "sans comprendre ce qui m'etait arrive ni les suites a donner."
                ),
                "circonstances": (
                    "Prise en charge nocturne, changement d'equipe pendant mon "
                    "passage, dossier visiblement perdu entre deux services."
                ),
                "consequences": (
                    "Angoisse importante et necessite de reconsulter un medecin "
                    "de ville le lendemain."
                ),
                "demande_plaignant": (
                    "Je souhaite obtenir un compte rendu detaille de ma prise en "
                    "charge et des garanties sur la transmission des informations."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Demande d'information sur le parcours aux urgences",
                "description": (
                    "Je souhaite comprendre le fonctionnement du service des "
                    "urgences et les criteres de priorisation des patients afin "
                    "de mieux anticiper une prochaine visite."
                ),
                "circonstances": (
                    "Passage en journee, prise en charge globalement correcte "
                    "mais procedures peu lisibles pour le public."
                ),
                "consequences": (
                    "Aucune consequence medicale, simple besoin de clarification."
                ),
                "demande_plaignant": (
                    "Je demande une documentation expliquant le parcours patient "
                    "aux urgences."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Remerciements pour la rapidite de prise en charge",
                "description": (
                    "Malgre l'affluence, l'equipe des urgences a su me prendre en "
                    "charge rapidement et avec beaucoup de professionnalisme. Je "
                    "tenais a saluer leur engagement."
                ),
                "circonstances": (
                    "Arrivee en fin de journee, tri efficace, information reguliere "
                    "sur l'attente."
                ),
                "consequences": (
                    "Prise en charge satisfaisante, retablissement rapide."
                ),
                "demande_plaignant": (
                    "Je souhaite simplement transmettre mes remerciements a l'equipe."
                ),
            },
        ],
    },
    "Chirurgie": {
        "negatif": [
            {
                "titre": "Report repete d'une intervention chirurgicale",
                "description": (
                    "Mon intervention a ete reportee a trois reprises sans "
                    "explication claire. A chaque fois j'avais effectue le jeune "
                    "et les preparatifs, en vain."
                ),
                "circonstances": (
                    "Programmation initiale au bloc puis annulations successives "
                    "pour cause de surcharge et de manque d'anesthesiste."
                ),
                "consequences": (
                    "Douleur prolongee, arrets de travail repetes et perte de "
                    "confiance envers le service."
                ),
                "demande_plaignant": (
                    "Je demande une date d'intervention ferme et une prise en "
                    "charge prioritaire."
                ),
            },
            {
                "titre": "Suivi post-operatoire insuffisant en chirurgie",
                "description": (
                    "Apres mon operation, je n'ai recu aucune consigne ecrite et "
                    "le suivi de la cicatrice a ete bacle. Une infection est "
                    "survenue faute de surveillance adequate."
                ),
                "circonstances": (
                    "Sortie rapide apres l'intervention, pas de rendez-vous de "
                    "controle planifie, douleurs ignorees lors de l'appel."
                ),
                "consequences": (
                    "Infection necessitant un nouveau traitement antibiotique et "
                    "une reconsultation en urgence."
                ),
                "demande_plaignant": (
                    "Je demande la mise en place d'un protocole de suivi "
                    "post-operatoire systematique."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Question sur les modalites de preparation a une chirurgie",
                "description": (
                    "Je dois etre opere prochainement et je souhaite obtenir des "
                    "precisions sur la preparation, le jeune et les documents a "
                    "fournir le jour de l'intervention."
                ),
                "circonstances": (
                    "Intervention programmee, consignes recues oralement mais "
                    "incompletes."
                ),
                "consequences": (
                    "Aucune consequence, besoin d'information avant l'operation."
                ),
                "demande_plaignant": (
                    "Je demande une fiche recapitulative de preparation a "
                    "l'intervention."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Satisfaction apres une intervention reussie",
                "description": (
                    "L'equipe chirurgicale a ete remarquable, de l'accueil au bloc "
                    "jusqu'au suivi. Tout a ete clairement explique et l'operation "
                    "s'est parfaitement deroulee."
                ),
                "circonstances": (
                    "Intervention programmee, accompagnement attentif avant et "
                    "apres l'operation."
                ),
                "consequences": (
                    "Retablissement conforme aux attentes, aucune complication."
                ),
                "demande_plaignant": (
                    "Je tiens a feliciter l'ensemble de l'equipe chirurgicale."
                ),
            },
        ],
    },
    "Cardiologie": {
        "negatif": [
            {
                "titre": "Delai trop long pour un rendez-vous de cardiologie",
                "description": (
                    "Adresse par mon medecin traitant pour des palpitations, j'ai "
                    "du attendre plusieurs mois pour obtenir une consultation, ce "
                    "qui m'a beaucoup inquiete."
                ),
                "circonstances": (
                    "Demande de rendez-vous deposee mais sans priorisation malgre "
                    "le caractere preoccupant des symptomes."
                ),
                "consequences": (
                    "Anxiete prolongee et sentiment d'abandon par le service."
                ),
                "demande_plaignant": (
                    "Je demande un meilleur tri des demandes urgentes en "
                    "cardiologie."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Demande d'explication sur des resultats cardiologiques",
                "description": (
                    "J'ai recu les resultats de mon echographie cardiaque mais "
                    "certains termes restent obscurs pour moi. Je souhaite des "
                    "explications complementaires."
                ),
                "circonstances": (
                    "Examen realise dans de bonnes conditions, compte rendu remis "
                    "sans commentaire detaille."
                ),
                "consequences": (
                    "Aucune consequence, besoin de comprehension."
                ),
                "demande_plaignant": (
                    "Je demande un entretien avec le cardiologue pour expliquer "
                    "mes resultats."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Remerciements pour un suivi cardiologique attentif",
                "description": (
                    "Le suivi de mon insuffisance cardiaque est exemplaire. Le "
                    "cardiologue prend le temps d'expliquer et de rassurer a "
                    "chaque consultation."
                ),
                "circonstances": (
                    "Suivi regulier sur plusieurs mois, disponibilite de l'equipe."
                ),
                "consequences": (
                    "Etat de sante stabilise, grande confiance dans le service."
                ),
                "demande_plaignant": (
                    "Je souhaite remercier chaleureusement l'equipe de cardiologie."
                ),
            },
        ],
    },
    "Pediatrie": {
        "negatif": [
            {
                "titre": "Accueil inadapte d'un enfant en pediatrie",
                "description": (
                    "Mon enfant, tres anxieux, a ete recu avec brusquerie et sans "
                    "aucune attention a son jeune age. Personne n'a cherche a le "
                    "rassurer pendant les soins."
                ),
                "circonstances": (
                    "Consultation en journee, salle bruyante, manque de personnel "
                    "forme a l'accueil des enfants."
                ),
                "consequences": (
                    "Traumatisme et peur de l'hopital chez mon enfant."
                ),
                "demande_plaignant": (
                    "Je demande une sensibilisation du personnel a l'accueil des "
                    "jeunes patients."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Demande d'information sur les visites en pediatrie",
                "description": (
                    "Je souhaite connaitre les horaires de visite et les regles "
                    "d'accompagnement pour rester aupres de mon enfant hospitalise."
                ),
                "circonstances": (
                    "Hospitalisation programmee, informations dispersees entre "
                    "plusieurs interlocuteurs."
                ),
                "consequences": (
                    "Aucune consequence, simple besoin d'organisation."
                ),
                "demande_plaignant": (
                    "Je demande une fiche claire sur les modalites de visite en "
                    "pediatrie."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Remerciements pour la bienveillance en pediatrie",
                "description": (
                    "L'equipe de pediatrie a su mettre mon enfant en confiance "
                    "avec une douceur remarquable. Les soins ont ete vecus sans "
                    "stress, ce qui est exceptionnel."
                ),
                "circonstances": (
                    "Hospitalisation de courte duree, personnel attentif et "
                    "pedagogique."
                ),
                "consequences": (
                    "Experience positive, enfant rassure et bien soigne."
                ),
                "demande_plaignant": (
                    "Je felicite toute l'equipe de pediatrie pour son humanite."
                ),
            },
        ],
    },
    "Radiologie": {
        "negatif": [
            {
                "titre": "Erreur de programmation d'un examen de radiologie",
                "description": (
                    "Je me suis deplace pour un scanner qui n'etait finalement pas "
                    "programme dans le systeme. On m'a renvoye chez moi sans "
                    "solution ni nouvelle date."
                ),
                "circonstances": (
                    "Convocation recue par courrier mais absente du planning du "
                    "service le jour J."
                ),
                "consequences": (
                    "Perte d'une demi-journee et retard dans mon diagnostic."
                ),
                "demande_plaignant": (
                    "Je demande une reprogrammation rapide et une verification du "
                    "circuit de convocation."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Demande de copie d'images radiologiques",
                "description": (
                    "Je souhaite obtenir une copie numerique de mes images "
                    "d'IRM afin de les transmettre a un specialiste exterieur."
                ),
                "circonstances": (
                    "Examen realise correctement, demande administrative en cours."
                ),
                "consequences": (
                    "Aucune consequence, demarche administrative."
                ),
                "demande_plaignant": (
                    "Je demande la remise de mes images sur support numerique."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Satisfaction sur la prise en charge en radiologie",
                "description": (
                    "L'examen d'imagerie s'est deroule rapidement, dans le respect "
                    "de l'horaire annonce, avec des manipulateurs courtois et "
                    "rassurants."
                ),
                "circonstances": (
                    "Rendez-vous respecte, explications claires avant l'examen."
                ),
                "consequences": (
                    "Aucune attente, experience tres satisfaisante."
                ),
                "demande_plaignant": (
                    "Je remercie l'equipe de radiologie pour son efficacite."
                ),
            },
        ],
    },
    "Administration / Qualite": {
        "negatif": [
            {
                "titre": "Erreur de facturation difficile a corriger",
                "description": (
                    "J'ai recu une facture erronee et malgre plusieurs appels et "
                    "courriers, aucune correction n'a ete apportee. Le service "
                    "administratif se renvoie la responsabilite."
                ),
                "circonstances": (
                    "Facturation d'un acte non realise, dossier balade entre "
                    "plusieurs interlocuteurs sans suivi."
                ),
                "consequences": (
                    "Stress financier et relances de recouvrement injustifiees."
                ),
                "demande_plaignant": (
                    "Je demande l'annulation de la facture erronee et un "
                    "interlocuteur unique."
                ),
            },
        ],
        "neutre": [
            {
                "titre": "Demande d'acces a un dossier medical",
                "description": (
                    "Je souhaite obtenir une copie de mon dossier medical complet "
                    "et connaitre la procedure ainsi que les delais applicables."
                ),
                "circonstances": (
                    "Demande administrative classique, formulaire transmis."
                ),
                "consequences": (
                    "Aucune consequence, demarche en cours."
                ),
                "demande_plaignant": (
                    "Je demande communication de mon dossier medical dans les "
                    "delais legaux."
                ),
            },
        ],
        "positif": [
            {
                "titre": "Remerciements au service administratif",
                "description": (
                    "Le service administratif a traite ma demande avec efficacite "
                    "et courtoisie. Mon dossier a ete regle en quelques jours."
                ),
                "circonstances": (
                    "Demande deposee en ligne, suivi reactif et clair."
                ),
                "consequences": (
                    "Demarche resolue rapidement, grande satisfaction."
                ),
                "demande_plaignant": (
                    "Je remercie le service pour sa reactivite."
                ),
            },
        ],
    },
}


def _sentiment_label(score):
    """Retourne le libelle de sentiment aligne sur le signe du score (-1..1)."""
    if score < -0.1:
        return "negatif"
    if score > 0.1:
        return "positif"
    return "neutre"


def _tirer_score_sentiment(service_nom, rng):
    """
    Tire un score_sentiment dans [-1, 1] selon la repartition cible
    (~40% negatif, ~25% neutre, ~35% positif), biaise vers le negatif pour
    les services critiques (Urgences / Chirurgie).
    Retourne (score, label).
    """
    if service_nom in SERVICES_CRITIQUES:
        # Biais negatif marque pour les services critiques
        poids = [("negatif", 0.60), ("neutre", 0.20), ("positif", 0.20)]
    else:
        poids = [("negatif", 0.40), ("neutre", 0.25), ("positif", 0.35)]

    r = rng.random()
    cumul = 0.0
    label = "neutre"
    for lbl, p in poids:
        cumul += p
        if r <= cumul:
            label = lbl
            break

    if label == "negatif":
        score = round(rng.uniform(-0.8, -0.3), 3)
    elif label == "positif":
        score = round(rng.uniform(0.3, 0.8), 3)
    else:
        score = round(rng.uniform(-0.2, 0.2), 3)
        # Re-aligner le label sur le signe reel pour rester coherent
        label = _sentiment_label(score)
    return score, label


def seed_plaintes(db, services, users):
    """
    Cree ~45 plaintes avec distributions exactes de statut/priorite/service,
    dates etalees sur 90 jours, scores de sentiment non nuls, contenu riche.
    Retourne la liste des plaintes creees + l'id de la plainte 'parfaite'.
    """
    print(">>> ETAPE 5/10 : creation des ~45 plaintes...")
    rng = random.Random(42)  # generateur dedie pour stabilite

    total = len(SERVICES_PLAN)  # 45

    # On melange chaque plan independamment avec un seed stable, puis on
    # affecte par index. On veille a concentrer URGENT/ELEVE sur Urgences/Chirurgie.
    services_plan = list(SERVICES_PLAN)
    rng.shuffle(services_plan)

    statuts_plan = list(STATUTS_PLAN)
    rng.shuffle(statuts_plan)

    # Pour la priorite, on trie les indices : on place les priorites hautes
    # en priorite sur les plaintes des services critiques.
    indices = list(range(total))
    # Score de "criticite" : 0 = critique (Urgences/Chirurgie), 1 = autre
    indices.sort(key=lambda i: (0 if services_plan[i] in SERVICES_CRITIQUES else 1,
                                rng.random()))
    priorites_ordonnees = sorted(
        PRIORITES_PLAN,
        key=lambda p: {PrioritePlainte.URGENT: 0, PrioritePlainte.ELEVE: 1,
                       PrioritePlainte.MOYEN: 2, PrioritePlainte.BAS: 3}[p],
    )
    priorite_par_index = {}
    for rang, idx in enumerate(indices):
        priorite_par_index[idx] = priorites_ordonnees[rang]

    # --- Plainte 'parfaite' : on garantit qu'elle tombe sur l'index 0 avec un
    # profil coherent (Urgences / EN_COURS / URGENT) SANS casser les comptes :
    # on echange simplement les valeurs deja planifiees entre l'index 0 et un
    # index portant le profil voulu.
    def _swap_vers_index0(plan, valeur_cible):
        """Place 'valeur_cible' a l'index 0 du plan via un swap (comptes intacts)."""
        if plan[0] == valeur_cible:
            return
        for j in range(1, len(plan)):
            if plan[j] == valeur_cible:
                plan[0], plan[j] = plan[j], plan[0]
                return

    _swap_vers_index0(services_plan, "Urgences")
    _swap_vers_index0(statuts_plan, StatutPlainte.EN_COURS)
    # La priorite est indexee dans un dict : on s'assure que l'index 0 = URGENT
    # en echangeant avec un index qui possede URGENT (comptes intacts).
    if priorite_par_index[0] != PrioritePlainte.URGENT:
        for j in range(1, total):
            if priorite_par_index[j] == PrioritePlainte.URGENT:
                priorite_par_index[0], priorite_par_index[j] = (
                    priorite_par_index[j], priorite_par_index[0])
                break

    createurs = users  # tous les users peuvent creer
    assignables = [u for u in users if u.type_utilisateur in (
        UserRole.MEDECIN, UserRole.RESPONSABLE_QUALITE,
        UserRole.CHEF_SERVICE, UserRole.UTILISATEUR)]

    plaintes = []
    plainte_parfaite_idx = 0  # la 1re plainte sera la plainte 'parfaite'

    for i in range(total):
        service_nom = services_plan[i]
        svc = services[service_nom]
        statut = statuts_plan[i]
        priorite = priorite_par_index[i]

        # Date de creation etalee sur 90 jours (today-90 .. today), jamais future
        jours_avant = rng.randint(0, 90)
        heure = rng.randint(8, 18)
        minute = rng.randint(0, 59)
        date_creation = (TODAY - timedelta(days=jours_avant)).replace(
            hour=heure, minute=minute, second=0, microsecond=0)
        if date_creation > TODAY:
            date_creation = TODAY

        # Score de sentiment + label aligne
        score, label = _tirer_score_sentiment(service_nom, rng)

        est_parfaite = (i == plainte_parfaite_idx)
        if est_parfaite:
            # Plainte 'parfaite' : on force un sentiment negatif marque et un
            # contenu premium tres realiste (cf. PLAINTE_PARFAITE_CONTENU).
            score = -0.92
            label = "negatif"
            tpl = PLAINTE_PARFAITE_CONTENU
        else:
            # Contenu riche selon service + sentiment
            bucket = TEMPLATES[service_nom][label]
            tpl = rng.choice(bucket)

        # Plaignant + plaignant info
        nom_p, prenom_p = rng.choice(PLAIGNANTS)
        nom_plaignant = f"{nom_p} {prenom_p}"  # format 'Nom Prenom'
        email_plaignant = (
            f"{prenom_p.lower()}.{nom_p.lower()}@exemple.fr")
        mode_reception = rng.choice(MODES_RECEPTION)

        createur = rng.choice(createurs)
        assignee = rng.choice(assignables) if rng.random() < 0.7 else None

        numero = f"PL_2026_{i + 1:04d}"

        plainte = Plainte(
            uuid=uuid.uuid4(),
            numero_plainte=numero,
            service_id=svc.id,
            cree_par_id=createur.id,
            assignee_a_id=assignee.id if assignee else None,
            titre=tpl["titre"][:500],
            description=tpl["description"],
            circonstances=tpl["circonstances"],
            consequences=tpl["consequences"],
            demande_plaignant=tpl["demande_plaignant"],
            nom_plaignant=nom_plaignant[:100],
            prenom_plaignant=prenom_p[:100],
            email_plaignant=email_plaignant[:255],
            telephone_plaignant=f"06{rng.randint(10000000, 99999999)}",
            mode_reception=mode_reception,
            statut=statut,
            priorite=priorite,
            categorie_principale=service_nom,
            mots_cles=[],
            score_sentiment=score,
            score_urgence_ia=round(rng.uniform(0.2, 0.95), 3),
            date_creation=date_creation,
        )

        # date_resolution pour TRAITE / CLOTURE (15 au total), <= today
        if statut in (StatutPlainte.TRAITE, StatutPlainte.CLOTURE):
            delai = rng.randint(2, 15)
            resolution = date_creation + timedelta(days=delai)
            if resolution > TODAY:
                resolution = TODAY
            plainte.date_resolution = resolution

        db.add(plainte)
        plaintes.append(plainte)

    db.flush()

    # On retient l'id de la 1re plainte comme reference pour la plainte 'parfaite'
    plainte_parfaite = plaintes[plainte_parfaite_idx]

    print(f"    {len(plaintes)} plaintes creees "
          f"(statuts RECU14/EN_COURS16/TRAITE11/CLOTURE4, "
          f"priorites URGENT7/ELEVE11/MOYEN18/BAS9).")
    return plaintes, plainte_parfaite


# --------------------------------------------------------------------------- #
# Etape 6 : analyses IA (1-1 avec les plaintes)
# --------------------------------------------------------------------------- #

# Variantes de lettre-type juridique (au moins 4), variees selon sentiment.
def _lettre_type(label, service_nom, plainte, parfaite=False):
    """Genere une reponse_suggeree (lettre type juridique) NON VIDE."""
    entete = (
        "Madame, Monsieur,\n\n"
        f"Nous accusons reception de votre reclamation relative au service "
        f"{service_nom} et vous remercions de l'attention portee a la qualite "
        "de nos prises en charge.\n\n"
    )

    if parfaite:
        # Reponse exemplaire et detaillee (plainte 'parfaite')
        corps = (
            "Apres une analyse approfondie de votre dossier par notre "
            "commission des usagers, nous reconnaissons que le delai de prise "
            "en charge constate n'est pas conforme a nos engagements de qualite "
            "et de securite des soins. Conformement aux articles L.1112-3 et "
            "R.1112-91 et suivants du Code de la sante publique, votre "
            "reclamation a ete inscrite au registre de la Commission des "
            "Usagers (CDU) et fera l'objet d'un examen en seance.\n\n"
            "Nous avons d'ores et deja engage les mesures correctives "
            "suivantes : (1) revision du protocole de tri et de priorisation, "
            "(2) renforcement de l'effectif soignant aux heures de forte "
            "affluence, (3) mise en place d'une information systematique des "
            "patients sur les delais d'attente. Un mediateur medical se tient "
            "a votre disposition pour un entretien, conformement a votre droit "
            "a la mediation.\n\n"
            "Nous vous presentons nos excuses les plus sinceres pour la gene "
            "occasionnee et restons pleinement mobilises pour retablir votre "
            "confiance.\n\n"
        )
    elif label == "negatif":
        corps = (
            "Nous prenons tres au serieux les difficultes que vous decrivez. "
            "Conformement aux dispositions du Code de la sante publique "
            "relatives aux droits des usagers (art. L.1112-3), votre "
            "reclamation est transmise a la Commission des Usagers qui "
            "examinera les faits et veillera a la mise en oeuvre des mesures "
            "correctives appropriees. Un mediateur peut etre saisi a votre "
            "demande.\n\n"
            "Nous vous prions d'accepter nos excuses pour les desagrements "
            "subis et nous engageons a vous tenir informe des suites donnees.\n\n"
        )
    elif label == "neutre":
        corps = (
            "Votre demande d'information a ete transmise au service concerne. "
            "Conformement a la reglementation en vigueur, nous nous engageons "
            "a vous apporter une reponse complete dans les meilleurs delais et "
            "a vous communiquer l'ensemble des elements utiles a votre "
            "comprehension.\n\n"
        )
    else:  # positif
        corps = (
            "Nous avons transmis vos remerciements aux equipes du service "
            f"{service_nom}, qui y ont ete tres sensibles. Votre retour positif "
            "constitue un encouragement precieux pour l'ensemble de nos "
            "professionnels et contribue a la demarche d'amelioration continue "
            "de la qualite de nos soins.\n\n"
        )

    pied = (
        "Nous restons a votre disposition pour tout complement d'information.\n\n"
        "Veuillez agreer, Madame, Monsieur, l'expression de nos salutations "
        "distinguees.\n\n"
        "La Direction de la Qualite et des Relations avec les Usagers\n"
        "Centre Hospitalier Universitaire"
    )
    return entete + corps + pied


def _mots_cles(service_nom, label):
    """Retourne une VRAIE liste Python de mots-cles (colonne ARRAY(String))."""
    base = {
        "Urgences": ["urgences", "attente", "prise en charge"],
        "Chirurgie": ["chirurgie", "intervention", "bloc operatoire"],
        "Cardiologie": ["cardiologie", "consultation", "suivi"],
        "Pediatrie": ["pediatrie", "enfant", "accueil"],
        "Radiologie": ["radiologie", "imagerie", "examen"],
        "Administration / Qualite": ["administration", "dossier", "facturation"],
    }[service_nom]
    suffixe = {
        "negatif": ["insatisfaction", "delai"],
        "neutre": ["information", "demande"],
        "positif": ["satisfaction", "remerciements"],
    }[label]
    return base + suffixe


def _resume_ia(label, service_nom, plainte):
    """Resume IA court et coherent."""
    tonalite = {
        "negatif": "exprime une insatisfaction",
        "neutre": "formule une demande d'information",
        "positif": "exprime sa satisfaction",
    }[label]
    return (
        f"Le plaignant {tonalite} concernant le service {service_nom}. "
        f"Objet principal : {plainte.titre}. "
        f"Priorite estimee : {plainte.priorite.value}."
    )


def seed_analyses_ia(db, plaintes, services, plainte_parfaite):
    """1 ligne analyses_ia par plainte (relation 1-1)."""
    print(">>> ETAPE 6/10 : creation des analyses IA (1 par plainte)...")
    rng = random.Random(42)

    for plainte in plaintes:
        score = plainte.score_sentiment
        label = _sentiment_label(score)
        service_nom = plainte.categorie_principale
        est_parfaite = (plainte.id == plainte_parfaite.id)

        analyse = AnalyseIA(
            plainte_id=int(plainte.id),  # cast explicite (relation 1-1)
            sentiment=label,             # negatif / neutre / positif
            score_sentiment=score,       # identique a la plainte
            confiance_sentiment=round(rng.uniform(0.80, 0.95), 3),
            service_suggere=service_nom,
            score_service=round(rng.uniform(0.7, 0.98), 3),
            confiance_service=round(rng.uniform(0.80, 0.95), 3),
            priorite_ia=plainte.priorite.value,  # graphie EXACTE URGENT/ELEVE/...
            score_priorite=round(rng.uniform(0.3, 0.95), 3),
            urgence_detectee=(plainte.priorite in (
                PrioritePlainte.URGENT, PrioritePlainte.ELEVE)),
            resume_ia=_resume_ia(label, service_nom, plainte),
            reponse_suggeree=_lettre_type(label, service_nom, plainte,
                                          parfaite=est_parfaite),
            mots_cles_detectes=_mots_cles(service_nom, label),  # vraie liste
            modele_utilise="qwen2.5:3b",
            version_modele="2.5",
            temps_traitement=round(rng.uniform(1.5, 8.0), 2),
            statut_analyse="complete",
            date_analyse=plainte.date_creation + timedelta(minutes=5),
            date_mise_a_jour=plainte.date_creation + timedelta(minutes=5),
        )
        db.add(analyse)

    db.flush()
    print(f"    {len(plaintes)} analyses IA creees "
          f"(plainte 'parfaite' : {plainte_parfaite.numero_plainte}).")


# --------------------------------------------------------------------------- #
# Etape 7 : documents (PDF reels)
# --------------------------------------------------------------------------- #
def seed_documents(db, plaintes):
    """
    8 a 12 documents pointant vers des PDF reels existants.
    chemin_fichier = chemin ABSOLU resolu (utilise par FileResponse au download).
    """
    print(">>> ETAPE 7/10 : creation des documents (PDF reels)...")
    rng = random.Random(42)

    # On attache des documents aux 5 premieres plaintes, 2 par plainte (=10),
    # en cyclant sur les 3 PDF reels disponibles.
    cibles = plaintes[:5]
    nb_docs = 0
    for plainte in cibles:
        for _ in range(2):
            pdf_name = PDF_FILES[nb_docs % len(PDF_FILES)]
            chemin_abs = str((PDF_DIR / pdf_name).resolve())
            nom_fichier = pdf_name
            nom_stockage = f"{plainte.numero_plainte}_{pdf_name}"
            doc = DocumentPlainte(
                plainte_id=int(plainte.id),
                nom_fichier=nom_fichier,
                nom_stockage=nom_stockage,
                chemin_fichier=chemin_abs,
                type_fichier=TypeFichier.PDF,
                taille_fichier=721556,
                mime_type="application/pdf",
                description="Piece jointe originale de la plainte (PDF).",
                est_piece_jointe_originale=True,
            )
            db.add(doc)
            nb_docs += 1

    db.flush()
    print(f"    {nb_docs} documents crees (PDF reels dans {PDF_DIR}).")
    return nb_docs


# --------------------------------------------------------------------------- #
# Etape 8 : resultat d'analyse globale (ai_analysis_results)
# --------------------------------------------------------------------------- #
def seed_ai_analysis_result(db, plaintes, services):
    """1 ligne ai_analysis_results coherente avec les donnees reelles."""
    print(">>> ETAPE 8/10 : creation du resultat d'analyse globale...")

    total = len(plaintes)

    # Comptage par service + comptage des negatifs par service
    par_service = {}
    negatifs_par_service = {}
    for p in plaintes:
        svc = p.categorie_principale
        par_service[svc] = par_service.get(svc, 0) + 1
        if _sentiment_label(p.score_sentiment) == "negatif":
            negatifs_par_service[svc] = negatifs_par_service.get(svc, 0) + 1

    # ------------------------------------------------------------------ #
    # Catalogue de causes / problemes / recommandations par service.
    # Permet de produire un schema EXACTEMENT conforme a ce que le
    # renderer Ameliorations.tsx (onglet "Analyse IA Avancee") attend :
    #   - analyses_par_service[].causes_identifiees[] = {cause, frequence,
    #     gravite, exemples[]}
    #   - analyses_par_service[].sentiment_general (TRES_NEGATIF / NEGATIF /
    #     NEUTRE / POSITIF)
    #   - analyses_par_service[].problemes_recurrents[] (string[])
    #   - analyses_par_service[].recommandations[] (string[])
    #   - causes_globales[] = {service, cause, gravite, frequence}
    #   - services_critiques = string[] (noms de services)
    # ------------------------------------------------------------------ #
    catalogue_causes = {
        "Urgences": {
            "causes": [
                ("Delais d'attente excessifs aux urgences", "CRITIQUE", [
                    "J'ai attendu plus de 5 heures avant d'etre pris en charge.",
                    "Aucune information sur le temps d'attente restant.",
                ]),
                ("Manque de communication sur la prise en charge", "ELEVEE", [
                    "Personne ne m'a explique ce qui se passait.",
                ]),
                ("Conditions d'accueil et de confort insuffisantes", "MOYENNE", [
                    "Salle d'attente bondee, aucune intimite.",
                ]),
            ],
            "problemes": ["Delais d'attente", "Communication", "Surcharge du service"],
            "recommandations": [
                "Renforcer l'equipe de triage aux heures de pointe.",
                "Afficher en temps reel les temps d'attente estimes.",
                "Mettre en place un referent communication patient.",
            ],
        },
        "Chirurgie": {
            "causes": [
                ("Report ou annulation d'interventions programmees", "CRITIQUE", [
                    "Mon operation a ete annulee deux fois sans explication.",
                ]),
                ("Suivi post-operatoire insuffisant", "ELEVEE", [
                    "Aucun suivi apres ma sortie, douleurs ignorees.",
                ]),
                ("Defaut d'information sur les risques", "MOYENNE", [
                    "On ne m'a pas explique les suites de l'intervention.",
                ]),
            ],
            "problemes": ["Annulations", "Suivi post-operatoire", "Information patient"],
            "recommandations": [
                "Securiser la planification du bloc operatoire.",
                "Formaliser un protocole de suivi post-operatoire.",
                "Remettre une fiche d'information avant chaque intervention.",
            ],
        },
        "Cardiologie": {
            "causes": [
                ("Delais de rendez-vous trop longs", "ELEVEE", [
                    "Plusieurs semaines d'attente pour une consultation.",
                ]),
                ("Resultats d'examens communiques tardivement", "MOYENNE", [
                    "J'ai attendu 10 jours pour avoir mes resultats.",
                ]),
            ],
            "problemes": ["Delais de rendez-vous", "Transmission des resultats"],
            "recommandations": [
                "Ouvrir des creneaux de consultation supplementaires.",
                "Automatiser l'envoi securise des resultats d'examens.",
            ],
        },
        "Pediatrie": {
            "causes": [
                ("Accueil des familles a ameliorer", "MOYENNE", [
                    "Manque de disponibilite du personnel pour rassurer les parents.",
                ]),
                ("Coordination des soins perfectible", "MOYENNE", [
                    "Plusieurs interlocuteurs, informations contradictoires.",
                ]),
            ],
            "problemes": ["Accueil des familles", "Coordination"],
            "recommandations": [
                "Designer un soignant referent par enfant hospitalise.",
                "Renforcer l'information aux familles.",
            ],
        },
        "Radiologie": {
            "causes": [
                ("Delais d'attente pour les examens d'imagerie", "MOYENNE", [
                    "Rendez-vous obtenu plusieurs semaines apres la prescription.",
                ]),
                ("Compte rendu d'examen tardif", "MOYENNE", [
                    "Le compte rendu n'etait pas pret a la date prevue.",
                ]),
            ],
            "problemes": ["Delais d'examen", "Comptes rendus"],
            "recommandations": [
                "Optimiser le planning des appareils d'imagerie.",
                "Reduire le delai de redaction des comptes rendus.",
            ],
        },
        "Administration / Qualite": {
            "causes": [
                ("Erreurs et lenteurs de facturation", "MOYENNE", [
                    "Facture erronee, plusieurs relances necessaires.",
                ]),
                ("Difficultes d'acces aux documents administratifs", "BASSE", [
                    "Demande de dossier medical restee sans reponse.",
                ]),
            ],
            "problemes": ["Facturation", "Acces aux documents"],
            "recommandations": [
                "Fiabiliser le processus de facturation.",
                "Mettre en place un guichet unique pour les demandes administratives.",
            ],
        },
    }

    def _sentiment_general(svc, nb, nb_neg):
        """Libelle de sentiment global du service, format attendu par le front."""
        if nb <= 0:
            return "NEUTRE"
        ratio = nb_neg / nb
        if svc in SERVICES_CRITIQUES or ratio >= 0.55:
            return "TRES_NEGATIF"
        if ratio >= 0.35:
            return "NEGATIF"
        if ratio <= 0.15:
            return "POSITIF"
        return "NEUTRE"

    # analyses_par_service : forme RICHE attendue par le renderer (cartes).
    analyses_par_service = []
    for svc, nb in sorted(par_service.items(),
                          key=lambda kv: kv[1], reverse=True):
        nb_neg = negatifs_par_service.get(svc, 0)
        infos = catalogue_causes.get(svc, {
            "causes": [
                ("Insatisfaction generale signalee", "MOYENNE", [
                    "Plaintes diverses concernant la prise en charge.",
                ]),
            ],
            "problemes": ["Prise en charge"],
            "recommandations": ["Analyser les retours patients du service."],
        })
        causes_identifiees = [
            {
                "cause": libelle,
                "frequence": freq,
                "gravite": gravite,
                "exemples": exemples,
            }
            # frequence decroissante et plafonnee au nombre de negatifs
            for idx, (libelle, gravite, exemples) in enumerate(infos["causes"])
            for freq in (max(1, nb_neg - idx * 2),)
        ]
        analyses_par_service.append({
            "service": svc,
            "nombre_plaintes": nb,
            "plaintes_negatives": nb_neg,
            "sentiment_general": _sentiment_general(svc, nb, nb_neg),
            "causes_identifiees": causes_identifiees,
            "problemes_recurrents": list(infos["problemes"]),
            "recommandations": list(infos["recommandations"]),
        })

    # causes_globales : Top causes "tous services", en OBJETS
    # {service, cause, gravite, frequence} (forme exacte du tableau front).
    causes_globales = []
    for analyse in analyses_par_service:
        for cause in analyse["causes_identifiees"]:
            causes_globales.append({
                "service": analyse["service"],
                "cause": cause["cause"],
                "gravite": cause["gravite"],
                "frequence": cause["frequence"],
            })
    # Tri par gravite puis frequence decroissante, limite au Top 10.
    ordre_gravite = {"CRITIQUE": 0, "ELEVEE": 1, "MOYENNE": 2, "BASSE": 3}
    causes_globales.sort(
        key=lambda c: (ordre_gravite.get(c["gravite"], 9), -int(c["frequence"]))
    )
    causes_globales = causes_globales[:10]

    # services_critiques : LISTE DE NOMS (string[]) attendue par le front.
    # Inclut explicitement Urgences / Chirurgie + tout service au sentiment
    # global tres negatif.
    noms_critiques = []
    for svc in ("Urgences", "Chirurgie"):
        if svc in par_service and svc not in noms_critiques:
            noms_critiques.append(svc)
    for analyse in analyses_par_service:
        if (analyse["sentiment_general"] == "TRES_NEGATIF"
                and analyse["service"] not in noms_critiques):
            noms_critiques.append(analyse["service"])
    services_critiques = noms_critiques

    started = TODAY - timedelta(minutes=12)
    completed = TODAY - timedelta(minutes=10)

    result = AIAnalysisResult(
        task_id=f"seed-demo-{uuid.uuid4()}",  # task_id UNIQUE
        total_plaintes_analysees=total,        # = COUNT reel
        nombre_services=len(services),          # 6
        model_used="qwen2.5:3b",
        analyses_par_service=analyses_par_service,
        causes_globales=causes_globales,
        services_critiques=services_critiques,
        status="completed",
        started_at=started,
        completed_at=completed,
        duree_secondes=round((completed - started).total_seconds(), 1),
    )
    db.add(result)
    db.flush()
    print(f"    Resultat d'analyse globale cree "
          f"(total={total}, services={len(services)}, "
          f"critiques={services_critiques}).")


# --------------------------------------------------------------------------- #
# Etape 9 : VACUUM ANALYZE (autocommit obligatoire)
# --------------------------------------------------------------------------- #
def vacuum_analyze():
    """VACUUM ANALYZE : impossible dans une transaction -> AUTOCOMMIT."""
    print(">>> ETAPE 9/10 : VACUUM ANALYZE...")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM ANALYZE;"))
    print("    VACUUM ANALYZE termine.")


# --------------------------------------------------------------------------- #
# Etape 10 : recapitulatif final
# --------------------------------------------------------------------------- #
def afficher_recap(db, nb_docs, plainte_parfaite):
    print(">>> ETAPE 10/10 : recapitulatif final")
    print("=" * 60)
    print("COMPTES PAR TABLE :")
    print(f"  organisations        : {db.query(Organisation).count()}")
    print(f"  services             : {db.query(Service).count()}")
    print(f"  utilisateurs         : {db.query(User).count()}")
    print(f"  plaintes             : {db.query(Plainte).count()}")
    print(f"  analyses_ia          : {db.query(AnalyseIA).count()}")
    print(f"  documents_plaintes   : {db.query(DocumentPlainte).count()}")
    print(f"  ai_analysis_results  : {db.query(AIAnalysisResult).count()}")
    print("=" * 60)
    print("IDENTIFIANTS JURY (a retenir) :")
    print(f"  Email        : {JURY_EMAIL}")
    print(f"  Mot de passe : {JURY_PASSWORD}")
    print("=" * 60)
    print("PLAINTE 'PARFAITE' (filet de securite demo) :")
    print(f"  id      : {plainte_parfaite.id}")
    print(f"  numero  : {plainte_parfaite.numero_plainte}")
    print(f"  titre   : {plainte_parfaite.titre}")
    print("=" * 60)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main():
    # Avertissement clair + URL cible (sans afficher le mot de passe DB en clair
    # plus que necessaire : on masque la portion credentials).
    try:
        from healthcare_api_server.app.core.config import get_database_url
        db_url = get_database_url()
        affichage_url = (
            db_url.split("@")[-1] if "@" in db_url else db_url)
    except Exception:
        affichage_url = "(URL inconnue)"

    print("=" * 60)
    print("  SEED DEMO HEALTHCARE - ATTENTION : OPERATION DESTRUCTIVE")
    print("=" * 60)
    print(f"  Base de donnees cible : {affichage_url}")
    print("  Ce script va SUPPRIMER toutes les donnees existantes puis")
    print("  recreer un jeu de donnees de demonstration deterministe.")
    print("=" * 60)

    # Etape 1 : reset (hors session ORM)
    reset_schema()

    # Etapes 2 a 8 : remplissage dans une session ORM transactionnelle
    db = SessionLocal()
    try:
        orga = seed_organisation(db)              # noqa: F841
        services = seed_services(db)
        users = seed_users(db, services)
        plaintes, plainte_parfaite = seed_plaintes(db, services, users)
        seed_analyses_ia(db, plaintes, services, plainte_parfaite)
        nb_docs = seed_documents(db, plaintes)
        seed_ai_analysis_result(db, plaintes, services)

        db.commit()
        print(">>> Donnees commitees avec succes.")
    except Exception as exc:
        db.rollback()
        print(f"!!! ERREUR pendant le seed, rollback effectue : {exc}")
        raise
    finally:
        # On garde une reference simple pour le recap (rechargement leger)
        db.close()

    # Etape 9 : VACUUM (hors transaction)
    vacuum_analyze()

    # Etape 10 : recap (nouvelle session de lecture)
    db = SessionLocal()
    try:
        # plainte_parfaite peut etre detachee : on la recharge par id
        pp = db.query(Plainte).filter(
            Plainte.id == plainte_parfaite.id).first()
        afficher_recap(db, nb_docs, pp if pp else plainte_parfaite)
    finally:
        db.close()

    print(">>> SEED DEMO TERMINE.")


if __name__ == "__main__":
    main()
