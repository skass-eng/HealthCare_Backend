# HealthCare AI - Application Principale

## 🏥 Vue d'ensemble

L'Application Principale de HealthCare AI est un point d'entrée unifié qui organise toutes les APIs en sections logiques avec des titres pour chaque ensemble de KPI. Elle offre une interface web moderne et intuitive pour naviguer entre les différentes fonctionnalités.

## 🚀 Démarrage Rapide

### Option 1: Script Windows
```bash
# Double-cliquer sur le fichier
start_all_apis.bat
```

### Option 2: Commande Python
```bash
cd backend
python start_main_app.py
```

### Option 3: Uvicorn Direct
```bash
cd backend
uvicorn main_app:app --host 0.0.0.0 --port 6000 --reload
```

## 📱 Accès à l'Application

- **Page d'accueil**: http://localhost:6000
- **Documentation Swagger**: http://localhost:6000/docs
- **Documentation ReDoc**: http://localhost:6000/redoc
- **Guide de navigation**: http://localhost:6000/navigation
- **État du système**: http://localhost:6000/status

## 📋 Organisation par Sections

### 1. 📋 Gestion des Plaintes
**Description**: APIs pour la création, consultation et gestion des plaintes médicales

**Endpoints**:
- `GET /api/v1/plaintes` - Liste des plaintes
- `GET /api/v1/plaintes/en-cours` - Plaintes en cours
- `GET /api/v1/plaintes/traitees` - Plaintes traitées
- `GET /api/v1/plaintes/en-attente` - Plaintes en attente
- `POST /api/v1/plaintes` - Créer une plainte
- `PUT /api/v1/plaintes/{id}` - Modifier une plainte

### 2. 📊 Statistiques et Analytics
**Description**: KPIs, métriques et analyses de performance du système

**Endpoints**:
- `GET /api/v1/statistiques` - Statistiques générales
- `GET /api/v1/statistiques/tendances` - Tendances
- `GET /api/v1/suggestions-ia` - Suggestions IA
- `GET /api/v1/suggestions/par-service` - Suggestions par service

### 3. 🏥 Gestion des Services
**Description**: Configuration et gestion des services médicaux

**Endpoints**:
- `GET /api/v1/services` - Liste des services
- `POST /api/v1/services` - Créer un service
- `PUT /api/v1/services/{id}` - Modifier un service
- `GET /api/v1/organisations` - Liste des organisations
- `GET /api/v1/utilisateurs` - Liste des utilisateurs

### 4. 📱 Dashboard et Pages
**Description**: Interfaces utilisateur et dashboards spécialisés

**Endpoints**:
- `GET /api/v2/pages/dashboard` - Dashboard principal
- `GET /api/v2/pages/analytics` - Analytics avancées
- `GET /api/v2/pages/analytics-v2` - Administration
- `GET /api/v2/pages/ameliorations` - Améliorations

### 5. 🔒 Audit et Sécurité
**Description**: Traçabilité et sécurité des opérations

**Endpoints**:
- `GET /api/v1/audit` - Logs d'audit
- `GET /api/v1/health` - État du système

### 6. 📚 Documentation
**Description**: Documentation interactive des APIs

**Endpoints**:
- `GET /docs` - Documentation Swagger
- `GET /redoc` - Documentation ReDoc

## 🏗️ Architecture

```
main_app.py (Port 6000)
├── /api/v1/* (API Unifiée)
│   ├── /plaintes/*
│   ├── /statistiques/*
│   ├── /services/*
│   ├── /organisations/*
│   ├── /utilisateurs/*
│   └── /audit/*
├── /api/v2/pages/* (API Pages)
│   ├── /dashboard
│   ├── /analytics
│   ├── /analytics-v2
│   └── /ameliorations
├── /api/v1/dashboard/* (API Dashboard)
├── /api/v1/simple/* (API Dashboard Simple)
└── / (Page d'accueil HTML)
```

## 🎨 Interface Utilisateur

### Page d'Accueil
- Interface web moderne avec design responsive
- Navigation intuitive par sections
- Indicateurs de statut en temps réel
- Design avec dégradés et effets visuels

### Fonctionnalités
- **Navigation par cartes**: Chaque section est présentée dans une carte cliquable
- **Statut en ligne**: Indicateurs visuels pour l'état des services
- **Responsive Design**: Compatible mobile et desktop
- **Thème moderne**: Interface utilisateur moderne avec animations

## 🔧 Configuration

### Variables d'Environnement
```bash
# Base de données PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/healthcare_ai

# Configuration API
API_HOST=0.0.0.0
API_PORT=6000
DEBUG=True
```

### Dépendances
```bash
pip install -r requirements.txt
```

## 📊 Monitoring

### Endpoints de Monitoring
- `GET /health` - Vérification de santé
- `GET /status` - Statut complet du système
- `GET /navigation` - Guide de navigation

### Logs
Les logs sont configurés pour afficher :
- Démarrage/arrêt de l'application
- État des services
- Erreurs et avertissements
- Performance des requêtes

## 🚀 Déploiement

### Développement
```bash
python start_main_app.py
```

### Production
```bash
uvicorn main_app:app --host 0.0.0.0 --port 6000 --workers 4
```

### Docker (optionnel)
```bash
docker build -t healthcare-ai-main .
docker run -p 6000:6000 healthcare-ai-main
```

## 🔄 Migration depuis l'Ancienne Architecture

### Changements Principaux
1. **Point d'entrée unifié**: Une seule application au lieu de plusieurs
2. **Organisation par sections**: APIs regroupées logiquement
3. **Interface web**: Page d'accueil avec navigation
4. **Documentation intégrée**: Accès direct à la documentation

### Compatibilité
- Tous les endpoints existants restent accessibles
- Aucune modification des APIs requise
- Migration transparente pour les clients

## 📈 Avantages

### Pour les Développeurs
- **Architecture claire**: Organisation logique des APIs
- **Documentation intégrée**: Accès facile à la documentation
- **Développement simplifié**: Un seul point d'entrée

### Pour les Utilisateurs
- **Navigation intuitive**: Interface web moderne
- **Accès centralisé**: Toutes les fonctionnalités au même endroit
- **Statut en temps réel**: Monitoring des services

### Pour les Administrateurs
- **Monitoring unifié**: Un seul point de contrôle
- **Déploiement simplifié**: Une seule application à gérer
- **Logs centralisés**: Traçabilité complète

## 🐛 Dépannage

### Problèmes Courants

1. **Port déjà utilisé**
   ```bash
   # Vérifier les processus
   netstat -ano | findstr :6000
   # Arrêter le processus
   taskkill /PID <PID> /F
   ```

2. **Base de données inaccessible**
   ```bash
   # Vérifier PostgreSQL
   pg_isready -h localhost -p 5432
   ```

3. **Dépendances manquantes**
   ```bash
   pip install -r requirements.txt
   ```

### Logs de Débogage
```bash
# Activer les logs détaillés
export LOG_LEVEL=DEBUG
python start_main_app.py
```

## 📞 Support

Pour toute question ou problème :
1. Consulter la documentation : http://localhost:6000/docs
2. Vérifier l'état du système : http://localhost:6000/status
3. Consulter les logs de l'application

---

**HealthCare AI - Application Principale v1.0.0**
*Architecture organisée et interface moderne pour la gestion des plaintes médicales* 