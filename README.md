# HealthCare AI - Architecture ODYSSEE

## 🏥 Vue d'ensemble

Application de gestion des plaintes hospitalières basée sur l'architecture ODYSSEE, reproduisant fidèlement les principes de séparation API/Worker et de persistance automatique.

### Modules Principaux

- **🔧 healthcare_api_server** : API serveur FastAPI avec WebSockets (équivalent Explorer_backend d'ODYSSEE)
- **⚙️ healthcare_worker_server** : Workers Celery pour analyses LLM asynchrones (équivalent worker_server d'ODYSSEE)  
- **🖥️ healthcare_frontend** : Interface React/TypeScript (équivalent Explorer_frontend, développée séparément)

### Équivalences avec ODYSSEE

| ODYSSEE | HealthCare AI | Fonction |
|---------|---------------|----------|
| `Dashboard` | `Plainte` | Entité principale contenant des analyses |
| `Widget` | `Analyse` | Tâche d'analyse exécutée par les workers |
| `api_server` | `healthcare_api_server` | API REST + WebSockets |
| `worker_server` | `healthcare_worker_server` | Workers Celery pour calculs |
| `SQLite/PostgreSQL` | `PostgreSQL` | Base de données partagée |
| `Celery` | `Celery + Redis` | Tâches asynchrones |

## Architecture Générale

### 1. **Stack Technologique**

#### API Server (healthcare_api_server)
- **Framework** : FastAPI avec SQLAlchemy ORM
- **Base de données** : PostgreSQL obligatoire
- **Authentification** : FastAPI-Users avec JWT
- **Communication** : REST API + WebSockets pour notifications temps réel
- **Migrations** : Alembic

#### Worker Server (healthcare_worker_server)
- **Framework** : Celery avec Redis comme broker
- **Analyses** : LLM pour classification automatique des plaintes
- **Tâches** : Analyse de sentiment, détection de priorité, suggestion d'actions
- **Résultats** : Persistance automatique dans PostgreSQL

#### Communication
- **Broker** : Redis pour les tâches Celery
- **WebSockets** : Notifications temps réel des analyses terminées
- **Base de données** : PostgreSQL partagée entre API et Workers

### 2. **Structure des Composants**

```
HealthCare_Backend_Odyssee/
├── healthcare_api_server/          # API serveur FastAPI
│   └── app/
│       ├── api/                   # Endpoints REST
│       │   ├── plaintes.py        # CRUD plaintes
│       │   ├── analyses.py        # Consultation analyses
│       │   ├── auth.py            # Authentification
│       │   └── websockets.py      # Communication temps réel
│       ├── models/                # Modèles SQLAlchemy
│       │   ├── __init__.py
│       │   ├── user.py            # Utilisateurs
│       │   ├── plainte.py         # Plaintes
│       │   ├── analyse.py         # Analyses LLM
│       │   └── service.py         # Services hospitaliers
│       ├── schemas/               # Schemas Pydantic
│       │   ├── __init__.py
│       │   ├── plainte.py
│       │   ├── analyse.py
│       │   └── user.py
│       ├── db/                    # Configuration DB
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── migrations/
│       ├── core/                  # Configuration centrale
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── security.py
│       └── storage/               # Gestion fichiers
│           ├── __init__.py
│           └── file_manager.py
├── healthcare_worker_server/       # Workers Celery
│   ├── app/
│   │   ├── tasks/                 # Tâches Celery
│   │   │   ├── __init__.py
│   │   │   ├── analyse_plainte.py # Analyse principale
│   │   │   ├── sentiment.py       # Analyse sentiment
│   │   │   └── classification.py  # Classification automatique
│   │   ├── services/              # Services LLM
│   │   │   ├── __init__.py
│   │   │   ├── llm_provider.py
│   │   │   ├── openai_service.py
│   │   │   └── anthropic_service.py
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       └── config.py
├── shared/                        # Code partagé
│   ├── __init__.py
│   ├── models.py                  # Modèles communs
│   ├── schemas.py                 # Schémas communs
│   └── utils.py                   # Utilitaires
├── scripts/                       # Scripts de démarrage
│   ├── start_api.py
│   ├── start_worker.py
│   ├── start_all.py
│   └── init_db.py
├── config/                        # Configuration
│   ├── .env.example
│   ├── docker-compose.yml
│   └── redis.conf
└── docs/                          # Documentation
    ├── api.md
    ├── deployment.md
    └── architecture.md
```

## Mécanisme de Sauvegarde des Données

### 1. **Types de Stockage**

#### **Base de données PostgreSQL**
```sql
-- Tables principales adaptées
- user : Utilisateurs et authentification (comme ODYSSEE)
- plainte : Plaintes hospitalières (équivalent des dashboards ODYSSEE)
- analyse : Résultats des analyses LLM (équivalent des widgets ODYSSEE)
- service : Services hospitaliers
- organisation : Hôpitaux et cliniques
- audit_log : Traçabilité des actions
```

#### **Système de fichiers**
```bash
# Structure de stockage adaptée
.healthcare-storage/
├── plaintes/                    # Fichiers attachés aux plaintes
│   └── {plainte_id}/
│       └── {file_id}.pdf
└── analyses/                    # Résultats d'analyses complexes
    └── {analyse_id}/
        └── results.json
```

### 2. **Entités Principales Sauvegardées**

#### **Plaintes**
Équivalent des projets ODYSSEE :
- **Contenu** : Description, circonstances, demandes
- **Métadonnées** : Service, priorité, statut, dates
- **Classification** : Catégorie, mots-clés, tags IA

#### **Analyses LLM**
Équivalent des widgets ODYSSEE :
- **Sentiment** : Score positif/négatif, émotions détectées
- **Priorité** : Classification automatique d'urgence
- **Service** : Suggestion de service approprié
- **Actions** : Recommandations d'actions correctives

### 3. **Mécanismes de Persistance**

#### **ORM et modèles (SQLAlchemy)**
```python
# Modèle adapté d'ODYSSEE pour les plaintes
class Plainte(Base):
    __tablename__ = "plaintes"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    titre = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    service_id = Column(UUID, ForeignKey("services.id"))
    statut = Column(Enum(StatutPlainte), default=StatutPlainte.NOUVELLE)
    
    # Relations avec analyses
    analyses = relationship("Analyse", back_populates="plainte")
```

#### **Gestion des analyses asynchrones**
```python
# Task Celery inspirée d'ODYSSEE
@celery_app.task(bind=True)
def analyser_plainte(self, plainte_id: str):
    # Analyse LLM de la plainte
    # Sauvegarde automatique du résultat
    # Notification WebSocket de fin d'analyse
```

### 4. **Moments de Sauvegarde**

#### **Automatique (comme ODYSSEE)**
- **Soumission plainte** : Sauvegarde immédiate + déclenchement analyse
- **Fin d'analyse** : Persistance automatique résultats LLM
- **Notifications temps réel** : WebSocket vers frontend
- **Backup automatique** : Sauvegarde incrémentale

#### **Événements spécifiques**
- **Nouvelle plainte** : `create_plainte` → `trigger_analyse_task`
- **Modification plainte** : `update_plainte` → `re_analyse_if_needed`
- **Fin analyse LLM** : `save_analyse_results` → `notify_websocket`

## API et Endpoints

### **Endpoints principaux**
- `/api/v1/auth/` : Authentification JWT (comme ODYSSEE)
- `/api/v1/plaintes/` : CRUD plaintes
- `/api/v1/analyses/` : Consultation analyses LLM
- `/api/v1/services/` : Gestion services hospitaliers
- `/api/v1/task/` : Statut des tâches d'analyse
- `/ws/notifications/` : WebSockets notifications temps réel

### **WebSockets**
- `/ws/analyses/{plainte_id}` : Notifications fin d'analyse
- `/ws/plaintes/updates` : Mises à jour temps réel des plaintes

## Résolution des Problèmes Courants

### **Erreur Enum UserRole**

Si vous rencontrez l'erreur :
```
'CHEF_SERVICE' is not among the defined enum values. Enum name: userrole
```

**Solution rapide :**
```bash
# Exécuter le script de démarrage rapide
python scripts/setup_database.py
```

**Solution manuelle :**
```bash
# 1. Migrer l'enum UserRole
python scripts/update_userrole_enum.py

# 2. Initialiser la base de données
python scripts/init_db.py
```

### **Valeurs d'enum ajoutées**
- `SUPER_ADMIN`
- `CHEF_SERVICE` 
- `TECHNICIEN`
- `UTILISATEUR`

## Configuration et Déploiement

### **Variables d'environnement**
```bash
# Configuration inspirée d'ODYSSEE
DATABASE_URL=postgresql://user:password@localhost/healthcare
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
API_CORS_ORIGINS=http://localhost:3000
LLM_PROVIDER=openai  # ou anthropic
OPENAI_API_KEY=your-openai-key
```

### **Démarrage en développement**
```bash
# Terminal 1: API serveur (équivalent ODYSSEE api_server)
python scripts/start_api.py

# Terminal 2: Worker Celery (équivalent ODYSSEE worker_server)
python scripts/start_worker.py

# Terminal 3: Redis (broker pour tâches)
redis-server

# Terminal 4: Frontend React (séparé)
cd ../healthcare_frontend && npm run dev
```

## Sécurité et Permissions

### **Authentification**
- JWT tokens avec expiration (comme ODYSSEE)
- Rôles : `patient`, `medecin`, `admin`, `qualite`
- Isolation des données par organisation

### **Permissions**
- Contrôle d'accès par service et plainte
- Audit trail complet des actions
- Chiffrement des données sensibles

## Points Clés de l'Architecture Adaptée

1. **Séparation claire** : API Server, Worker Server, Frontend séparés
2. **Persistance PostgreSQL** : Base unique partagée entre API et Workers
3. **Analyses asynchrones** : Celery pour analyses LLM sans bloquer l'API
4. **Temps réel** : WebSockets pour notifications d'analyses terminées
5. **Validation stricte** : Pydantic pour toutes les données (comme ODYSSEE)
6. **Backup automatique** : Sauvegarde continue des plaintes et analyses
7. **Performance optimisée** : Cache Redis + analyses en arrière-plan

Cette architecture garantit la **persistance robuste** des plaintes avec **analyse automatique**, **notifications temps réel** et **performance optimisée** pour le traitement des plaintes hospitalières complexes.