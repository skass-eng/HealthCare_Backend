#!/usr/bin/env python3
"""
API UNIFIÉE - HealthCare AI
Combine V1 et V2 en une seule API propre et maintenable
Version: 1.0.0 - Architecture Clean
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from contextlib import asynccontextmanager
import os
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uvicorn
import json
import httpx

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports locaux unifiés
from database_unified import SessionLocal, engine
from models_unified import (
    Base, Organisation, Service, Utilisateur, Plainte, 
    FichierPlainte, AuditLog,
    StatutPlainteEnum, PrioriteEnum, TypeServiceEnum, TypeUtilisateurEnum
)
# Import du dashboard router sera fait après la définition de get_db
from schemas_unified import (
    # Organisations
    OrganisationCreate, OrganisationResponse, OrganisationUpdate,
    # Services  
    ServiceCreate, ServiceResponse, ServiceUpdate,
    # Utilisateurs
    UtilisateurCreate, UtilisateurResponse, UtilisateurUpdate,
    # Plaintes
    PlainteCreate, PlainteResponse, PlainteUpdate, PlaintesListResponse,
    # Statistiques
    StatistiquesResponse, AnalyticsResponse,
    # Réponses génériques
    SuccessResponse, ErrorResponse
)
from config import settings

# Configuration API Pages
PAGES_API_BASE_URL = "http://localhost:8002"

# ==================== STARTUP / SHUTDOWN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    logger.info("🚀 Démarrage de HealthCare AI - API Unifiée")
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Base de données initialisée")
    
    yield
    
    logger.info("🛑 Arrêt de HealthCare AI")

app = FastAPI(
    title="HealthCare AI - API Unifiée",
    description="API moderne unifiée pour la gestion des plaintes médicales",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure le router du dashboard unifié (après la définition de get_db)

# ==================== DEPENDENCY ====================

def get_db() -> Session:
    """Dépendance pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inclure le router du dashboard unifié (après la définition de get_db)
# L'inclusion sera faite à la fin du fichier pour éviter les imports circulaires

# ==================== ROUTES DE SANTÉ ====================

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "api": "unified"
    }

@app.get("/")
async def root():
    """Route racine avec informations sur l'API"""
    return {
        "message": "🏥 HealthCare AI - API Unifiée",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "features": [
            "Gestion des organisations",
            "Gestion des services",
            "Gestion des utilisateurs", 
            "Gestion des plaintes",
            "Analytics et statistiques",
            "Traçabilité complète"
        ]
    }

# ==================== ORGANISATIONS ====================

@app.get("/organisations", response_model=List[OrganisationResponse])
async def get_organisations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    actif_seulement: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Récupérer la liste des organisations"""
    query = db.query(Organisation)
    
    if actif_seulement:
        query = query.filter(Organisation.est_actif == True)
    
    organisations = query.offset(skip).limit(limit).all()
    return organisations

@app.post("/organisations", response_model=OrganisationResponse)
async def create_organisation(
    organisation: OrganisationCreate,
    db: Session = Depends(get_db)
):
    """Créer une nouvelle organisation"""
    # Vérifier unicité du code établissement
    existing = db.query(Organisation).filter(
        Organisation.code_etablissement == organisation.code_etablissement
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Code établissement '{organisation.code_etablissement}' déjà utilisé"
        )
    
    db_org = Organisation(**organisation.dict())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    return db_org

@app.get("/organisations/{org_id}", response_model=OrganisationResponse)
async def get_organisation(org_id: int, db: Session = Depends(get_db)):
    """Récupérer une organisation par ID"""
    organisation = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not organisation:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    return organisation

@app.put("/organisations/{org_id}", response_model=OrganisationResponse)
async def update_organisation(
    org_id: int,
    organisation_update: OrganisationUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour une organisation"""
    organisation = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not organisation:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")
    
    for field, value in organisation_update.dict(exclude_unset=True).items():
        setattr(organisation, field, value)
    
    organisation.date_modification = datetime.now()
    db.commit()
    db.refresh(organisation)
    
    return organisation

# ==================== SERVICES ====================

@app.get("/services", response_model=List[ServiceResponse])
async def get_services(
    organisation_id: Optional[int] = Query(None),
    type_service: Optional[str] = Query(None),
    actif_seulement: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Récupérer la liste des services"""
    query = db.query(Service)
    
    if organisation_id:
        query = query.filter(Service.organisation_id == organisation_id)
    
    if type_service:
        query = query.filter(Service.type_service == type_service)
    
    if actif_seulement:
        query = query.filter(Service.est_actif == True)
    
    services = query.all()
    return services

@app.post("/services", response_model=ServiceResponse)
async def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db)
):
    """Créer un nouveau service"""
    db_service = Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    return db_service

# ==================== UTILISATEURS ====================

@app.get("/utilisateurs", response_model=List[UtilisateurResponse])
async def get_utilisateurs(
    organisation_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    type_utilisateur: Optional[str] = Query(None),
    actif_seulement: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Récupérer la liste des utilisateurs"""
    query = db.query(Utilisateur)
    
    if organisation_id:
        query = query.filter(Utilisateur.organisation_id == organisation_id)
    
    if service_id:
        query = query.filter(Utilisateur.service_id == service_id)
    
    if type_utilisateur:
        query = query.filter(Utilisateur.type_utilisateur == type_utilisateur)
    
    if actif_seulement:
        query = query.filter(Utilisateur.est_actif == True)
    
    utilisateurs = query.all()
    return utilisateurs

@app.post("/utilisateurs", response_model=UtilisateurResponse)
async def create_utilisateur(
    utilisateur: UtilisateurCreate,
    db: Session = Depends(get_db)
):
    """Créer un nouvel utilisateur"""
    # Vérifier unicité de l'email
    existing = db.query(Utilisateur).filter(Utilisateur.email == utilisateur.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Calculer nom_complet automatiquement
    utilisateur_data = utilisateur.dict()
    utilisateur_data['nom_complet'] = f"{utilisateur.prenom} {utilisateur.nom}"
    
    db_user = Utilisateur(**utilisateur_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.put("/utilisateurs/{user_id}", response_model=UtilisateurResponse)
async def update_utilisateur(
    user_id: int,
    utilisateur_update: UtilisateurUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour un utilisateur"""
    utilisateur = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    for field, value in utilisateur_update.dict(exclude_unset=True).items():
        setattr(utilisateur, field, value)
    
    # Recalculer nom_complet si nécessaire
    if 'nom' in utilisateur_update.dict() or 'prenom' in utilisateur_update.dict():
        utilisateur.nom_complet = f"{utilisateur.prenom} {utilisateur.nom}"
    
    db.commit()
    db.refresh(utilisateur)
    
    return utilisateur

# ==================== PLAINTES ====================

@app.get("/plaintes", response_model=PlaintesListResponse)
async def get_plaintes(
    organisation_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Récupérer la liste des plaintes avec filtres"""
    query = db.query(Plainte)
    
    if organisation_id:
        query = query.filter(Plainte.organisation_id == organisation_id)
    
    if service_id:
        query = query.filter(Plainte.service_id == service_id)
    
    if statut:
        try:
            statut_enum = StatutPlainteEnum(statut)
            query = query.filter(Plainte.statut == statut_enum)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Statut invalide: {statut}")
    
    if priorite:
        try:
            priorite_enum = PrioriteEnum(priorite)
            query = query.filter(Plainte.priorite == priorite_enum)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Priorité invalide: {priorite}")
    
    # Compter le total
    total = query.count()
    
    # Appliquer pagination
    plaintes = query.offset(skip).limit(limit).all()
    
    return PlaintesListResponse(
        plaintes=plaintes,
        total=total,
        skip=skip,
        limit=limit
    )

@app.post("/plaintes", response_model=PlainteResponse)
async def create_plainte(
    plainte: PlainteCreate,
    db: Session = Depends(get_db)
):
    """Créer une nouvelle plainte"""
    # Générer numéro de plainte automatique
    year = datetime.now().year
    count = db.query(Plainte).filter(
        Plainte.numero_plainte.like(f"PL-{year}-%")
    ).count()
    
    numero_plainte = f"PL-{year}-{count+1:06d}"
    
    plainte_data = plainte.dict()
    plainte_data['numero_plainte'] = numero_plainte
    
    db_plainte = Plainte(**plainte_data)
    db.add(db_plainte)
    db.commit()
    db.refresh(db_plainte)
    
    return db_plainte

# ==================== ENDPOINTS SPÉCIFIQUES POUR LE DASHBOARD ====================

@app.get("/plaintes/en-cours")
async def get_plaintes_en_cours(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes en cours"""
    try:
        skip = (page - 1) * limite
        
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.EN_COURS)
        
        total = query.count()
        plaintes = query.offset(skip).limit(limite).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append({
                    "id": plainte.id,
                    "plainte_id": plainte.numero_plainte,
                    "titre": plainte.titre,
                    "contenu": plainte.description,
                    "service": plainte.service.nom if plainte.service else "Service inconnu",
                    "priorite": plainte.priorite.value if plainte.priorite else "MOYEN",
                    "statut": plainte.statut.value if plainte.statut else "RECU",
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    "categorie_principale": plainte.categorie_principale,
                    "type_service": plainte.service.nom if plainte.service else None
                })
            except Exception as e:
                print(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return {
            "plaintes": plaintes_data,
            "total": total,
            "page": page,
            "limite": limite
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des plaintes en cours: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/plaintes/traitees")
async def get_plaintes_traitees(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes traitées"""
    try:
        skip = (page - 1) * limite
        
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.TRAITE)
        
        total = query.count()
        plaintes = query.offset(skip).limit(limite).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append({
                    "id": plainte.id,
                    "plainte_id": plainte.numero_plainte,
                    "titre": plainte.titre,
                    "contenu": plainte.description,
                    "service": plainte.service.nom if plainte.service else "Service inconnu",
                    "priorite": plainte.priorite.value if plainte.priorite else "MOYEN",
                    "statut": plainte.statut.value if plainte.statut else "RECU",
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    "categorie_principale": plainte.categorie_principale,
                    "type_service": plainte.service.nom if plainte.service else None
                })
            except Exception as e:
                print(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return {
            "plaintes": plaintes_data,
            "total": total,
            "page": page,
            "limite": limite
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des plaintes traitées: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/plaintes/en-attente")
async def get_plaintes_en_attente(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes en attente (Reçues)"""
    try:
        skip = (page - 1) * limite
        
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.RECU)
        
        total = query.count()
        plaintes = query.offset(skip).limit(limite).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append({
                    "id": plainte.id,
                    "plainte_id": plainte.numero_plainte,
                    "titre": plainte.titre,
                    "contenu": plainte.description,
                    "service": plainte.service.nom if plainte.service else "Service inconnu",
                    "priorite": plainte.priorite.value if plainte.priorite else "MOYEN",
                    "statut": plainte.statut.value if plainte.statut else "RECU",
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    "categorie_principale": plainte.categorie_principale,
                    "type_service": plainte.service.nom if plainte.service else None
                })
            except Exception as e:
                print(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return {
            "plaintes": plaintes_data,
            "total": total,
            "page": page,
            "limite": limite
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des plaintes en attente: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/plaintes/cloturees")
async def get_plaintes_cloturees(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes clôturées"""
    try:
        skip = (page - 1) * limite
        
        query = db.query(Plainte).filter(Plainte.statut == StatutPlainteEnum.CLOTURE)
        
        total = query.count()
        plaintes = query.offset(skip).limit(limite).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        plaintes_data = []
        for plainte in plaintes:
            try:
                plaintes_data.append({
                    "id": plainte.id,
                    "plainte_id": plainte.numero_plainte,
                    "titre": plainte.titre,
                    "contenu": plainte.description,
                    "service": plainte.service.nom if plainte.service else "Service inconnu",
                    "priorite": plainte.priorite.value if plainte.priorite else "MOYEN",
                    "statut": plainte.statut.value if plainte.statut else "RECU",
                    "date_creation": plainte.date_creation.isoformat() if plainte.date_creation else None,
                    "date_limite_reponse": plainte.date_limite_reponse.isoformat() if plainte.date_limite_reponse else None,
                    "categorie_principale": plainte.categorie_principale,
                    "type_service": plainte.service.nom if plainte.service else None
                })
            except Exception as e:
                print(f"Erreur lors de la conversion de la plainte {plainte.id}: {e}")
                continue
        
        return {
            "plaintes": plaintes_data,
            "total": total,
            "page": page,
            "limite": limite
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des plaintes clôturées: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/plaintes/export")
async def export_plaintes(
    format: str = Query("csv", regex="^(csv|json)$"),
    statut: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Exporter les plaintes selon les critères"""
    query = db.query(Plainte)
    
    # Appliquer les filtres
    if statut:
        query = query.filter(Plainte.statut == statut)
    if service:
        query = query.filter(Plainte.service_id == service)
    if date_debut:
        query = query.filter(Plainte.date_creation >= date_debut)
    if date_fin:
        query = query.filter(Plainte.date_creation <= date_fin)
    
    plaintes = query.all()
    
    if format == "json":
        return {
            "plaintes": [
                {
                    "id": p.id,
                    "numero_plainte": p.numero_plainte,
                    "titre": p.titre,
                    "statut": p.statut,
                    "priorite": p.priorite,
                    "date_creation": p.date_creation,
                    "date_limite_reponse": p.date_limite_reponse
                }
                for p in plaintes
            ],
            "total": len(plaintes),
            "export_date": datetime.now().isoformat()
        }
    else:  # CSV
        import csv
        from io import StringIO, BytesIO
        from fastapi.responses import Response
        
        # Créer un buffer en mémoire pour le CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow([
            "ID", "Numéro Plainte", "Titre", "Statut", "Priorité", 
            "Date Création", "Date Limite Réponse"
        ])
        
        # Données
        for p in plaintes:
            writer.writerow([
                p.id, p.numero_plainte, p.titre, p.statut, p.priorite,
                p.date_creation, p.date_limite_reponse
            ])
        
        # Récupérer le contenu CSV
        csv_content = output.getvalue()
        output.close()
        
        # Ajouter le BOM UTF-8 pour Excel
        bom = '\ufeff'  # BOM UTF-8
        content_with_bom = bom + csv_content
        
        # Encoder en UTF-8
        content_bytes = content_with_bom.encode('utf-8')
        
        # Retourner une Response avec le bon Content-Type et encodage pour le téléchargement
        return Response(
            content=content_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=plaintes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

# ==================== ENDPOINTS GÉNÉRIQUES POUR LES PLAINTES ====================

@app.get("/plaintes/{numero_plainte}", response_model=PlainteResponse)
async def get_plainte(numero_plainte: str, db: Session = Depends(get_db)):
    """Récupérer une plainte par numéro de plainte"""
    plainte = db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    return plainte

@app.get("/plaintes/{numero_plainte}/suggestions")
async def get_plainte_suggestions(numero_plainte: str, db: Session = Depends(get_db)):
    """Récupérer les suggestions IA pour une plainte"""
    # Vérifier que la plainte existe
    plainte = db.query(Plainte).filter(Plainte.numero_plainte == numero_plainte).first()
    if not plainte:
        raise HTTPException(status_code=404, detail="Plainte non trouvée")
    
    # Pour l'instant, retourner des suggestions mockées
    # TODO: Intégrer avec le service d'IA réel
    suggestions = {
        "plainte_id": plainte.numero_plainte,
        "total_suggestions": 2,
        "suggestions_par_type": {
            "reponse": [
                {
                    "id": 1,
                    "contenu": "Réponse empathique recommandée avec excuses personnalisées",
                    "confiance": 0.85,
                    "modele": "gpt-4",
                    "date_generation": datetime.now().isoformat(),
                    "est_approuve": False,
                    "est_utilise": False
                }
            ],
            "action": [
                {
                    "id": 2,
                    "contenu": "Investigation approfondie et suivi post-réponse nécessaire",
                    "confiance": 0.78,
                    "modele": "gpt-4",
                    "date_generation": datetime.now().isoformat(),
                    "est_approuve": False,
                    "est_utilise": False
                }
            ]
        },
        "types_disponibles": ["reponse", "action", "classification", "contact"]
    }
    
    return suggestions

@app.get("/statistiques/tendances")
async def get_tendances(
    periode: str = Query("7j", regex="^(7j|30j|90j)$"),
    db: Session = Depends(get_db)
):
    """Récupérer les tendances des plaintes"""
    # Pour l'instant, retourner des données mockées
    # TODO: Implémenter la vraie logique de calcul des tendances
    
    if periode == "7j":
        return {
            "periode": "7j",
            "nouvelles_trend": [
                {"period": "2024-01-01", "count": 12},
                {"period": "2024-01-02", "count": 15},
                {"period": "2024-01-03", "count": 8},
                {"period": "2024-01-04", "count": 18},
                {"period": "2024-01-05", "count": 22},
                {"period": "2024-01-06", "count": 10},
                {"period": "2024-01-07", "count": 6}
            ],
            "traitees_trend": [
                {"period": "2024-01-01", "count": 8},
                {"period": "2024-01-02", "count": 12},
                {"period": "2024-01-03", "count": 10},
                {"period": "2024-01-04", "count": 14},
                {"period": "2024-01-05", "count": 16},
                {"period": "2024-01-06", "count": 8},
                {"period": "2024-01-07", "count": 5}
            ],
            "satisfaction_trend": [
                {"period": "2024-01-01", "avg_satisfaction": 4.2},
                {"period": "2024-01-02", "avg_satisfaction": 4.1},
                {"period": "2024-01-03", "avg_satisfaction": 4.3},
                {"period": "2024-01-04", "avg_satisfaction": 4.0},
                {"period": "2024-01-05", "avg_satisfaction": 4.4},
                {"period": "2024-01-06", "avg_satisfaction": 4.5},
                {"period": "2024-01-07", "avg_satisfaction": 4.6}
            ],
            "service_trends": [
                {"service": "Cardiologie", "count": 15, "evolution": 12},
                {"service": "Urgences", "count": 28, "evolution": -5},
                {"service": "Pédiatrie", "count": 22, "evolution": 8},
                {"service": "Chirurgie", "count": 18, "evolution": 15},
                {"service": "Radiologie", "count": 12, "evolution": -2}
            ],
            "insights": {
                "pic_jour": "Vendredi",
                "evolution_satisfaction": "+5%",
                "service_attention": "Cardiologie"
            }
        }
    else:
        # Données pour 30j ou 90j
        return {
            "periode": periode,
            "nouvelles_trend": [],
            "traitees_trend": [],
            "satisfaction_trend": [],
            "service_trends": [],
            "insights": {
                "pic_jour": "N/A",
                "evolution_satisfaction": "0%",
                "service_attention": "N/A"
            }
        }

# ==================== STATISTIQUES ====================

@app.get("/statistiques")
async def get_statistiques(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les statistiques détaillées pour le dashboard"""
    try:
        query = db.query(Plainte)
        
        if organisation_id:
            query = query.filter(Plainte.organisation_id == organisation_id)
        
        # Statistiques de base
        total_plaintes = query.count()
        nouvelles = query.filter(Plainte.statut == StatutPlainteEnum.RECU).count()
        en_cours = query.filter(Plainte.statut == StatutPlainteEnum.EN_COURS).count()
        traitees = query.filter(Plainte.statut == StatutPlainteEnum.TRAITE).count()
        cloturees = query.filter(Plainte.statut == StatutPlainteEnum.CLOTURE).count()
        
        # Plaintes en retard (dépassant la date limite ou créées il y a plus de 30 jours)
        aujourd_hui = datetime.now().date()
        il_y_a_30_jours = aujourd_hui - timedelta(days=30)
        
        # Plaintes avec date limite dépassée
        plaintes_retard_date_limite = query.filter(
            Plainte.date_limite_reponse.isnot(None),
            Plainte.date_limite_reponse < aujourd_hui,
            Plainte.statut.in_([
                StatutPlainteEnum.RECU,
                StatutPlainteEnum.EN_COURS,
                StatutPlainteEnum.EN_COURS_TRAITEMENT,
                StatutPlainteEnum.EN_ATTENTE_INFORMATION
            ])
        ).count()
        
        # Plaintes créées il y a plus de 30 jours (sans date limite définie)
        plaintes_retard_anciennes = query.filter(
            Plainte.date_creation < il_y_a_30_jours,
            Plainte.statut.in_([
                StatutPlainteEnum.RECU,
                StatutPlainteEnum.EN_COURS,
                StatutPlainteEnum.EN_COURS_TRAITEMENT,
                StatutPlainteEnum.EN_ATTENTE_INFORMATION
            ])
        ).count()
        
        plaintes_en_retard = plaintes_retard_date_limite + plaintes_retard_anciennes
        
        # Plaintes traitées ce mois
        debut_mois = datetime.now().replace(day=1).date()
        traitees_ce_mois = query.filter(
            Plainte.statut.in_([StatutPlainteEnum.TRAITEE, StatutPlainteEnum.RESOLUE]),
            Plainte.date_modification >= debut_mois
        ).count()
        
        # Nouvelles plaintes (7 derniers jours)
        il_y_a_7_jours = datetime.now().date() - timedelta(days=7)
        nouvelles_7_jours = query.filter(
            Plainte.date_creation >= il_y_a_7_jours,
            Plainte.statut == StatutPlainteEnum.NOUVELLE
        ).count()
        
        # Statistiques des fichiers
        fichiers_query = db.query(FichierPlainte)
        if organisation_id:
            fichiers_query = fichiers_query.join(Plainte).filter(Plainte.organisation_id == organisation_id)
        
        total_fichiers = fichiers_query.count()
        fichiers_traites = fichiers_query.filter(FichierPlainte.est_traite == True).count()
        fichiers_en_attente = total_fichiers - fichiers_traites
        
        # Répartitions
        repartition_services = db.query(Service.nom, func.count(Plainte.id)).join(Plainte).group_by(Service.nom).all()
        repartition_priorites = db.query(Plainte.priorite, func.count(Plainte.id)).group_by(Plainte.priorite).all()
        
        # Satisfaction moyenne (mock pour l'instant)
        satisfaction_moyenne = 4.2
        
        # Logs pour déboguer
        logger.info(f"📊 Statistiques calculées:")
        logger.info(f"  - Total plaintes: {total_plaintes}")
        logger.info(f"  - Nouvelles: {nouvelles}")
        logger.info(f"  - En cours: {en_cours}")
        logger.info(f"  - Traitées: {traitees}")
        logger.info(f"  - Cloturées: {cloturees}")
        logger.info(f"  - Plaintes en retard (date limite): {plaintes_retard_date_limite}")
        logger.info(f"  - Plaintes en retard (anciennes): {plaintes_retard_anciennes}")
        logger.info(f"  - Plaintes en retard (total): {plaintes_en_retard}")
        logger.info(f"  - Traitées ce mois: {traitees_ce_mois}")
        logger.info(f"  - Nouvelles 7 jours: {nouvelles_7_jours}")
        
        result = {
            # Statistiques principales pour les cartes
            "nouvelles_plaintes": nouvelles,
            "plaintes_en_attente": nouvelles,
            "plaintes_en_retard": plaintes_en_retard,
            "en_cours_traitement": en_cours,
            "traitees_ce_mois": traitees_ce_mois,
            "satisfaction_moyenne": satisfaction_moyenne,
            
            # Progressions et métriques
            "progression": {
                "nouvelles_plaintes": f"+{nouvelles_7_jours}",
                "plaintes_en_attente": f"+{nouvelles}",
                "plaintes_en_retard": f"+{plaintes_en_retard}",
                "en_cours_traitement": f"+{en_cours}",
                "traitees_ce_mois": f"+{traitees_ce_mois}",
                "satisfaction_moyenne": f"+{satisfaction_moyenne}"
            },
            
            # Statistiques détaillées
            "statistiques_detaillees": {
                "plaintes": {
                    "total": total_plaintes,
                    "en_attente": nouvelles,
                    "en_cours": en_cours,
                    "traitees_mois": traitees_ce_mois,
                    "nouvelles_7_jours": nouvelles_7_jours
                },
                "fichiers": {
                    "total": total_fichiers,
                    "en_attente_traitement": fichiers_en_attente,
                    "traites": fichiers_traites,
                    "traites_aujourd_hui": 0,  # Mock
                    "taux_traitement_pct": round((fichiers_traites / total_fichiers * 100) if total_fichiers > 0 else 0, 1)
                },
                "ia_performance": {
                    "total_suggestions": 150,  # Mock
                    "suggestions_approuvees": 120,  # Mock
                    "suggestions_utilisees": 95,  # Mock
                    "taux_approbation_pct": 80.0,  # Mock
                    "efficacite_ia": "Excellente"  # Mock
                }
            },
            
            # Répartitions
            "repartitions": {
                "par_services": [{"service": service, "count": count} for service, count in repartition_services],
                "par_priorites": [{"priorite": priorite, "count": count} for priorite, count in repartition_priorites],
                "par_types_fichiers": [{"type": "PDF", "count": total_fichiers}]  # Mock
            },
            
            # Alertes
            "alertes": {
                "fichiers_en_attente_critique": fichiers_en_attente > 10,
                "plaintes_urgentes": plaintes_en_retard > 5,
                "performance_ia_faible": False,  # Mock
                "satisfaction_faible": satisfaction_moyenne < 3.5
            },
            
            # Timestamp
            "derniere_mise_a_jour": datetime.now().isoformat()
        }
        
        logger.info(f"📊 Résultat final: {result}")
        return result
    except Exception as e:
        logger.error(f"Erreur dans get_statistiques: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/test-data")
async def create_test_data(db: Session = Depends(get_db)):
    """Créer des données de test pour les statistiques"""
    try:
        # Créer une organisation de test
        org = Organisation(
            nom="Hôpital Test",
            nom_court="HT",
            code_etablissement="TEST001",
            est_actif=True
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        
        # Créer un service de test
        service = Service(
            organisation_id=org.id,
            nom="Service Test",
            code_service="ST001",
            type_service="MEDICAL",
            est_actif=True
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        
        # Créer des plaintes de test avec différentes dates
        aujourd_hui = datetime.now()
        il_y_a_35_jours = aujourd_hui - timedelta(days=35)
        il_y_a_10_jours = aujourd_hui - timedelta(days=10)
        il_y_a_5_jours = aujourd_hui - timedelta(days=5)
        
        plaintes_test = [
            # Plaintes en retard (créées il y a plus de 30 jours)
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte en retard 1",
                description="Plainte créée il y a 35 jours",
                statut=StatutPlainteEnum.RECU,
                priorite=PrioriteEnum.ELEVEE,
                date_creation=il_y_a_35_jours,
                date_limite_reponse=il_y_a_35_jours + timedelta(days=7)
            ),
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte en retard 2",
                description="Plainte créée il y a 35 jours",
                statut=StatutPlainteEnum.EN_COURS,
                priorite=PrioriteEnum.MOYENNE,
                date_creation=il_y_a_35_jours,
                date_limite_reponse=il_y_a_35_jours + timedelta(days=10)
            ),
            # Plaintes récentes
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte récente 1",
                description="Plainte créée il y a 5 jours",
                statut=StatutPlainteEnum.RECU,
                priorite=PrioriteEnum.BASSE,
                date_creation=il_y_a_5_jours
            ),
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte récente 2",
                description="Plainte créée il y a 10 jours",
                statut=StatutPlainteEnum.EN_COURS,
                priorite=PrioriteEnum.ELEVEE,
                date_creation=il_y_a_10_jours
            ),
            # Plaintes traitées ce mois
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte traitée 1",
                description="Plainte traitée ce mois",
                statut=StatutPlainteEnum.TRAITE,
                priorite=PrioriteEnum.MOYENNE,
                date_creation=il_y_a_10_jours,
                date_modification=aujourd_hui
            ),
            Plainte(
                organisation_id=org.id,
                service_id=service.id,
                titre="Plainte traitée 2",
                description="Plainte traitée ce mois",
                statut=StatutPlainteEnum.RESOLUE,
                priorite=PrioriteEnum.BASSE,
                date_creation=il_y_a_5_jours,
                date_modification=aujourd_hui
            )
        ]
        
        for plainte in plaintes_test:
            db.add(plainte)
        
        db.commit()
        
        return {
            "message": "Données de test créées avec succès",
            "organisation_id": org.id,
            "service_id": service.id,
            "plaintes_crees": len(plaintes_test)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la création des données de test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== UPLOAD DE FICHIERS ====================

@app.post("/upload-plainte")
async def upload_plainte(
    file: UploadFile = File(...),
    organisation_id: int = Form(...),
    service_id: Optional[int] = Form(None),
    priorite: str = Form("MOYEN"),
    db: Session = Depends(get_db)
):
    """Upload d'une plainte avec fichier"""
    
    # Validation du fichier
    if file.content_type not in ["application/pdf", "text/plain", "application/msword"]:
        raise HTTPException(status_code=400, detail="Type de fichier non supporté")
    
    # Créer la plainte
    numero_plainte = f"PL-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
    
    db_plainte = Plainte(
        numero_plainte=numero_plainte,
        organisation_id=organisation_id,
        service_id=service_id,
        titre=f"Plainte uploadée - {file.filename}",
        description="Plainte uploadée via fichier",
        priorite=priorite,
        statut="NOUVELLE"
    )
    
    db.add(db_plainte)
    db.commit()
    db.refresh(db_plainte)
    
    # Sauvegarder le fichier
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{numero_plainte}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Créer l'enregistrement du fichier
    db_fichier = FichierPlainte(
        plainte_id=db_plainte.id,
        nom_original=file.filename,
        nom_stockage=f"{numero_plainte}_{file.filename}",
        chemin_relatif=file_path,
        type_fichier="PDF" if file.content_type == "application/pdf" else "AUTRE",
        mime_type=file.content_type,
        taille_octets=len(content),
        checksum_md5=hashlib.md5(content).hexdigest(),
        uploade_par_id=1  # TODO: Récupérer l'utilisateur connecté
    )
    
    db.add(db_fichier)
    db.commit()
    
    return {
        "success": True,
        "plainte_id": db_plainte.id,
        "numero_plainte": numero_plainte,
        "fichier_id": db_fichier.id,
        "message": "Plainte et fichier uploadés avec succès"
    }

# ==================== AUDIT ET AMÉLIORATIONS ====================

@app.get("/audit")
async def get_audit_log(
    organisation_id: Optional[int] = Query(None),
    utilisateur_id: Optional[int] = Query(None),
    objet_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Récupérer les logs d'audit"""
    try:
        query = db.query(AuditLog)
        
        if organisation_id:
            query = query.filter(AuditLog.organisation_id == organisation_id)
        if utilisateur_id:
            query = query.filter(AuditLog.utilisateur_id == utilisateur_id)
        if objet_type:
            query = query.filter(AuditLog.ressource_type == objet_type)
        if action:
            query = query.filter(AuditLog.action == action)
        if date_debut:
            query = query.filter(AuditLog.date_action >= date_debut)
        if date_fin:
            query = query.filter(AuditLog.date_action <= date_fin)
            
        total = query.count()
        logs = query.offset(skip).limit(limit).all()
        
        return {
            "logs": logs,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Erreur dans get_audit_log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/ameliorations")
async def get_ameliorations(db: Session = Depends(get_db)):
    """Récupérer les suggestions d'amélioration du système"""
    try:
        # Mock data pour les améliorations
        ameliorations = [
            {
                "id": 1,
                "titre": "Interface utilisateur",
                "description": "Améliorer l'ergonomie du dashboard",
                "priorite": "MOYEN",
                "statut": "EN_COURS",
                "progression": 75,
                "date_creation": datetime.now().isoformat()
            },
            {
                "id": 2,
                "titre": "Performance IA",
                "description": "Optimiser les algorithmes d'analyse",
                "priorite": "ELEVE",
                "statut": "PLANIFIE",
                "progression": 25,
                "date_creation": datetime.now().isoformat()
            },
            {
                "id": 3,
                "titre": "Sécurité",
                "description": "Renforcer l'authentification",
                "priorite": "URGENT",
                "statut": "TERMINE",
                "progression": 100,
                "date_creation": datetime.now().isoformat()
            }
        ]
        
        return {
            "ameliorations": ameliorations,
            "total": len(ameliorations)
        }
    except Exception as e:
        logger.error(f"Erreur dans get_ameliorations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/suggestions-ia")
async def get_suggestions_ia(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les suggestions IA globales"""
    try:
        # Mock data pour les suggestions IA
        suggestions = [
            {
                "id": 1,
                "type": "classification",
                "contenu": "Automatiser la classification des plaintes par catégorie",
                "score_confiance": 0.85,
                "date_generation": datetime.now().isoformat(),
                "est_approuve": True
            },
            {
                "id": 2,
                "type": "priorite",
                "contenu": "Système de détection automatique des urgences",
                "score_confiance": 0.92,
                "date_generation": datetime.now().isoformat(),
                "est_approuve": False
            }
        ]
        
        return {
            "suggestions": suggestions,
            "total": len(suggestions)
        }
    except Exception as e:
        logger.error(f"Erreur dans get_suggestions_ia: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.get("/suggestions/par-service")
async def get_suggestions_par_service(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les suggestions IA par service"""
    try:
        # Mock data pour les suggestions par service
        services_suggestions = [
            {
                "service": "Cardiologie",
                "total_suggestions": 15,
                "plaintes_analysées": 25,
                "suggestions_par_type": {
                    "classification": [
                        {
                            "id": 1,
                            "contenu": "Classer automatiquement les plaintes cardiologiques par type d'incident",
                            "score_confiance": 0.88,
                            "date_generation": datetime.now().isoformat(),
                            "est_approuve": True,
                            "est_utilise": True
                        }
                    ],
                    "contact": [],
                    "reponse": [],
                    "action": [],
                    "mots_cles": [],
                    "priorite": []
                },
                "types_disponibles": ["classification"]
            },
            {
                "service": "Urgences",
                "total_suggestions": 8,
                "plaintes_analysées": 12,
                "suggestions_par_type": {
                    "classification": [],
                    "contact": [],
                    "reponse": [
                        {
                            "id": 2,
                            "contenu": "Réponse standardisée pour les plaintes d'hygiène",
                            "score_confiance": 0.92,
                            "date_generation": datetime.now().isoformat(),
                            "est_approuve": False,
                            "est_utilise": False
                        }
                    ],
                    "action": [],
                    "mots_cles": [],
                    "priorite": []
                },
                "types_disponibles": ["reponse"]
            }
        ]
        
        return {
            "services": services_suggestions,
            "total_services": len(services_suggestions),
            "total_suggestions": sum(s["total_suggestions"] for s in services_suggestions)
        }
    except Exception as e:
        logger.error(f"Erreur dans get_suggestions_par_service: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# ==================== INTÉGRATION API PAGES ====================

async def call_pages_api(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Fonction utilitaire pour appeler l'API Pages"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{PAGES_API_BASE_URL}{endpoint}"
            if params:
                response = await client.get(url, params=params)
            else:
                response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erreur API Pages {endpoint}: {response.status_code}")
                return {"error": f"Erreur API Pages: {response.status_code}"}
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à l'API Pages {endpoint}: {str(e)}")
        return {"error": f"Erreur de connexion à l'API Pages: {str(e)}"}

@app.get("/pages/dashboard")
async def get_pages_dashboard(organisation_id: Optional[int] = Query(None)):
    """Récupérer les données du dashboard via l'API Pages"""
    params = {}
    if organisation_id:
        params["organisation_id"] = organisation_id
    
    result = await call_pages_api("/dashboard", params)
    return result

@app.get("/pages/nouvelles-plaintes")
async def get_pages_nouvelles_plaintes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    priorite: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None)
):
    """Récupérer les nouvelles plaintes via l'API Pages"""
    params = {
        "page": page,
        "limit": limit
    }
    if organisation_id:
        params["organisation_id"] = organisation_id
    if priorite:
        params["priorite"] = priorite
    if service_id:
        params["service_id"] = service_id
    
    result = await call_pages_api("/nouvelles-plaintes", params)
    return result

@app.get("/pages/en-cours")
async def get_pages_en_cours(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None)
):
    """Récupérer les plaintes en cours via l'API Pages"""
    params = {
        "page": page,
        "limit": limit
    }
    if organisation_id:
        params["organisation_id"] = organisation_id
    if statut:
        params["statut"] = statut
    
    result = await call_pages_api("/en-cours", params)
    return result

@app.get("/pages/traitees")
async def get_pages_traitees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    organisation_id: Optional[int] = Query(None),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None)
):
    """Récupérer les plaintes traitées via l'API Pages"""
    params = {
        "page": page,
        "limit": limit
    }
    if organisation_id:
        params["organisation_id"] = organisation_id
    if date_debut:
        params["date_debut"] = date_debut
    if date_fin:
        params["date_fin"] = date_fin
    
    result = await call_pages_api("/traitees", params)
    return result

@app.get("/pages/ameliorations")
async def get_pages_ameliorations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    categorie: Optional[str] = Query(None)
):
    """Récupérer les améliorations via l'API Pages"""
    params = {
        "page": page,
        "limit": limit
    }
    if categorie:
        params["categorie"] = categorie
    
    result = await call_pages_api("/ameliorations", params)
    return result

@app.get("/pages/analytics")
async def get_pages_analytics(
    periode: str = Query("30j", description="Période d'analyse: 7j, 30j, 90j, 1an"),
    organisation_id: Optional[int] = Query(None)
):
    """Récupérer les analytics via l'API Pages"""
    params = {"periode": periode}
    if organisation_id:
        params["organisation_id"] = organisation_id
    
    result = await call_pages_api("/analytics", params)
    return result

@app.get("/pages/analytics-v2")
async def get_pages_administration(organisation_id: Optional[int] = Query(None)):
    """Récupérer les données d'administration via l'API Pages"""
    params = {}
    if organisation_id:
        params["organisation_id"] = organisation_id
    
    result = await call_pages_api("/analytics-v2", params)
    return result

@app.get("/pages/parametres")
async def get_pages_parametres():
    """Récupérer les paramètres via l'API Pages"""
    result = await call_pages_api("/parametres")
    return result

@app.get("/pages/apis-utilisees")
async def get_pages_apis_utilisees():
    """Récupérer la liste des APIs utilisées par page"""
    result = await call_pages_api("/apis-utilisees")
    return result

@app.get("/pages/health")
async def get_pages_health():
    """Vérifier la santé de l'API Pages"""
    result = await call_pages_api("/health")
    return result

# ==================== INCLUSION DES ROUTERS ====================

# Inclure le router du dashboard unifié (à la fin pour éviter les imports circulaires)
from api_dashboard_unified import app as dashboard_router
app.include_router(dashboard_router, prefix="/api/v1/dashboard")

# ==================== MAIN ====================

if __name__ == "__main__":
    uvicorn.run(
        "api_unified:app",
        host="0.0.0.0",
        port=6000,
        reload=True,
        log_level="info"
    ) 