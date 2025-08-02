#!/usr/bin/env python3
"""
API UNIFIÉE ROUTER - HealthCare AI
Version router pour inclusion dans l'application principale
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import csv
from io import StringIO

from database_unified import SessionLocal
from models_unified import Plainte, Service, Organisation, Utilisateur
from schemas_unified import (
    OrganisationResponse, ServiceResponse, UtilisateurResponse,
    PlainteResponse, PlaintesListResponse, StatistiquesResponse,
    UtilisateurCreate, UtilisateurUpdate
)

# Configuration du logging
import logging
logger = logging.getLogger(__name__)

# Créer le router
app = APIRouter(
    prefix="",
    tags=["API Unifiée"],
    responses={404: {"description": "Not found"}},
)

# ==================== DEPENDENCY ====================

def get_db() -> Session:
    """Dépendance pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ROUTES DE SANTÉ ====================

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    return {
        "status": "healthy",
        "timestamp": "2025-07-27T15:00:00.000000",
        "version": "1.0.0",
        "api": "unified"
    }

@app.get("/")
async def root():
    """Point d'entrée de l'API unifiée"""
    return {
        "message": "HealthCare AI - API Unifiée",
        "version": "1.0.0",
        "endpoints": {
            "organisations": "/organisations",
            "services": "/services",
            "utilisateurs": "/utilisateurs",
            "plaintes": "/plaintes",
            "statistiques": "/statistiques"
        }
    }

# ==================== ROUTES ORGANISATIONS ====================

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

# ==================== ROUTES SERVICES ====================

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
    
    services = query.offset(skip).limit(limit).all()
    return services

# ==================== ROUTES UTILISATEURS ====================

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
    db_utilisateur = Utilisateur(**utilisateur.dict())
    db.add(db_utilisateur)
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

@app.put("/utilisateurs/{user_id}", response_model=UtilisateurResponse)
async def update_utilisateur(
    user_id: int,
    utilisateur_update: UtilisateurUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour un utilisateur"""
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not db_utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    for field, value in utilisateur_update.dict(exclude_unset=True).items():
        setattr(db_utilisateur, field, value)
    
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

@app.delete("/utilisateurs/{user_id}")
async def delete_utilisateur(user_id: int, db: Session = Depends(get_db)):
    """Supprimer un utilisateur"""
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not db_utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    db.delete(db_utilisateur)
    db.commit()
    return {"message": "Utilisateur supprimé avec succès"}

# ==================== ROUTES PLAINTES ====================

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
        query = query.filter(Plainte.statut == statut)
    if priorite:
        query = query.filter(Plainte.priorite == priorite)
    
    total = query.count()
    plaintes = query.offset(skip).limit(limit).all()
    
    return PlaintesListResponse(
        plaintes=plaintes,
        total=total,
        skip=skip,
        limit=limit
    )

@app.get("/plaintes/en-cours")
async def get_plaintes_en_cours(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes en cours"""
    skip = (page - 1) * limite
    query = db.query(Plainte).filter(Plainte.statut == "EN_COURS")
    
    total = query.count()
    plaintes = query.offset(skip).limit(limite).all()
    
    return {
        "plaintes": plaintes,
        "total": total,
        "page": page,
        "limite": limite
    }

@app.get("/plaintes/traitees")
async def get_plaintes_traitees(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes traitées"""
    skip = (page - 1) * limite
    query = db.query(Plainte).filter(Plainte.statut == "TRAITE")
    
    total = query.count()
    plaintes = query.offset(skip).limit(limite).all()
    
    return {
        "plaintes": plaintes,
        "total": total,
        "page": page,
        "limite": limite
    }

@app.get("/plaintes/en-attente")
async def get_plaintes_en_attente(
    page: int = Query(1, ge=1),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les plaintes en attente"""
    skip = (page - 1) * limite
    query = db.query(Plainte).filter(Plainte.statut == "RECU")
    
    total = query.count()
    plaintes = query.offset(skip).limit(limite).all()
    
    return {
        "plaintes": plaintes,
        "total": total,
        "page": page,
        "limite": limite
    }

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

# ==================== ROUTES STATISTIQUES ====================

@app.get("/statistiques")
async def get_statistiques(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les statistiques générales"""
    # Statistiques de base
    total_plaintes = db.query(Plainte).count()
    plaintes_en_cours = db.query(Plainte).filter(Plainte.statut == "EN_COURS").count()
    plaintes_traitees = db.query(Plainte).filter(Plainte.statut == "TRAITE").count()
    plaintes_en_attente = db.query(Plainte).filter(Plainte.statut == "RECU").count()
    
    # Statistiques par priorité
    urgentes = db.query(Plainte).filter(Plainte.priorite == "URGENT").count()
    elevees = db.query(Plainte).filter(Plainte.priorite == "ELEVE").count()
    moyennes = db.query(Plainte).filter(Plainte.priorite == "MOYEN").count()
    basses = db.query(Plainte).filter(Plainte.priorite == "BAS").count()
    
    return {
        "total_plaintes": total_plaintes,
        "plaintes_en_cours": plaintes_en_cours,
        "plaintes_traitees": plaintes_traitees,
        "plaintes_en_attente": plaintes_en_attente,
        "par_priorite": {
            "urgentes": urgentes,
            "elevees": elevees,
            "moyennes": moyennes,
            "basses": basses
        }
    }

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

# ==================== ROUTES SUGGESTIONS IA ====================

@app.get("/suggestions-ia")
async def get_suggestions_ia(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les suggestions IA générales"""
    # Suggestions basées sur les plaintes récentes
    plaintes_recentes = db.query(Plainte).order_by(Plainte.date_creation.desc()).limit(10).all()
    
    suggestions = []
    for plainte in plaintes_recentes:
        if plainte.priorite == "URGENT":
            suggestions.append({
                "type": "urgence",
                "message": f"Plainte urgente #{plainte.numero_plainte} nécessite une attention immédiate",
                "priorite": "haute"
            })
    
    return {
        "total_suggestions": len(suggestions),
        "suggestions": suggestions
    }

@app.get("/suggestions/par-service")
async def get_suggestions_par_service(
    organisation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Récupérer les suggestions par service"""
    # Analyser les plaintes par service
    services_avec_plaintes = db.query(Plainte.service_id).distinct().all()
    
    suggestions_par_service = []
    for service_id in services_avec_plaintes:
        if service_id[0]:  # Vérifier que service_id n'est pas None
            plaintes_service = db.query(Plainte).filter(Plainte.service_id == service_id[0]).count()
            plaintes_urgentes = db.query(Plainte).filter(
                Plainte.service_id == service_id[0],
                Plainte.priorite == "URGENT"
            ).count()
            
            if plaintes_urgentes > 0:
                suggestions_par_service.append({
                    "service_id": service_id[0],
                    "total_plaintes": plaintes_service,
                    "plaintes_urgentes": plaintes_urgentes,
                    "suggestion": f"Service avec {plaintes_urgentes} plaintes urgentes"
                })
    
    return {
        "services_analyses": len(suggestions_par_service),
        "suggestions": suggestions_par_service
    }

# ==================== ROUTES AUDIT ====================

@app.get("/audit")
async def get_audit_log(
    organisation_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Récupérer le log d'audit"""
    # Pour l'instant, retourner un log d'audit simulé
    # TODO: Implémenter le vrai système d'audit
    audit_entries = [
        {
            "id": 1,
            "timestamp": "2025-07-27T15:00:00.000000",
            "action": "EXPORT_PLAINTES",
            "utilisateur": "admin",
            "details": "Export CSV de 150 plaintes"
        },
        {
            "id": 2,
            "timestamp": "2025-07-27T14:30:00.000000",
            "action": "CREATE_PLAINTE",
            "utilisateur": "agent1",
            "details": "Création plainte #PL-2024-0156"
        }
    ]
    
    return {
        "total": len(audit_entries),
        "audit_entries": audit_entries[skip:skip + limit]
    }

# ==================== ROUTES DE TEST ====================

@app.post("/test-data")
async def create_test_data(db: Session = Depends(get_db)):
    """Créer des données de test"""
    # Cette route peut être utilisée pour créer des données de test
    # TODO: Implémenter la création de données de test
    return {
        "message": "Données de test créées avec succès",
        "timestamp": datetime.now().isoformat()
    } 