# Dashboard Unifié - HealthCare AI

## 🎯 Vue d'ensemble

Le Dashboard Unifié combine les fonctionnalités des deux dashboards précédents et ajoute un système de filtres avancé pour les types de plaintes. Il permet une navigation intuitive et une analyse ciblée des données.

## 🔧 Fonctionnalités Principales

### 📊 Statistiques Unifiées
- **KPIs principaux** : Nouvelles plaintes, en attente, en retard, en cours, traitées
- **Métriques avancées** : Satisfaction, progression, répartitions
- **Alertes intelligentes** : Détection automatique des situations critiques

### 🎛️ Système de Filtres
- **Type de service** : URGENCES, CARDIOLOGIE, PEDIATRIE, etc.
- **Catégorie principale** : Classification des plaintes
- **Sous-catégorie** : Détail de la classification
- **Priorité** : URGENT, ELEVE, MOYEN, BAS
- **Statut** : NOUVELLE, EN_COURS, TRAITEE, etc.

### 📋 Gestion des Plaintes
- **Plaintes en cours** : Suivi des traitements actifs
- **Plaintes traitées** : Historique avec filtres de dates
- **Plaintes en attente** : Actions requises
- **Plaintes urgentes** : Priorité maximale

## 🚀 Endpoints Disponibles

### Statistiques et Filtres
```bash
# Statistiques avec filtres
GET /api/v1/dashboard/statistiques
GET /api/v1/dashboard/statistiques?type_service=URGENCES
GET /api/v1/dashboard/statistiques?categorie_principale=QUALITE
GET /api/v1/dashboard/statistiques?priorite=URGENT

# Filtres disponibles
GET /api/v1/dashboard/filtres-disponibles
GET /api/v1/dashboard/filtres-disponibles?organisation_id=1
```

### Plaintes avec Filtres
```bash
# Plaintes en cours
GET /api/v1/dashboard/plaintes/en-cours
GET /api/v1/dashboard/plaintes/en-cours?type_service=CARDIOLOGIE
GET /api/v1/dashboard/plaintes/en-cours?priorite=ELEVE

# Plaintes traitées
GET /api/v1/dashboard/plaintes/traitees
GET /api/v1/dashboard/plaintes/traitees?date_debut=2024-01-01
GET /api/v1/dashboard/plaintes/traitees?date_fin=2024-12-31

# Plaintes en attente
GET /api/v1/dashboard/plaintes/en-attente
GET /api/v1/dashboard/plaintes/en-attente?categorie_principale=ADMINISTRATION

# Plaintes urgentes
GET /api/v1/dashboard/plaintes/urgentes
GET /api/v1/dashboard/plaintes/urgentes?type_service=URGENCES
```

## 🎛️ Utilisation des Filtres

### Filtres Simples
```bash
# Filtrer par type de service
GET /api/v1/dashboard/statistiques?type_service=URGENCES

# Filtrer par priorité
GET /api/v1/dashboard/plaintes/en-cours?priorite=URGENT

# Filtrer par organisation
GET /api/v1/dashboard/statistiques?organisation_id=1
```

### Filtres Combinés
```bash
# Combiner plusieurs filtres
GET /api/v1/dashboard/plaintes/en-cours?type_service=CARDIOLOGIE&priorite=ELEVE&categorie_principale=QUALITE

# Filtres avec pagination
GET /api/v1/dashboard/plaintes/traitees?page=1&limit=20&date_debut=2024-01-01&type_service=ADMINISTRATION
```

### Filtres de Dates
```bash
# Plaintes traitées sur une période
GET /api/v1/dashboard/plaintes/traitees?date_debut=2024-01-01&date_fin=2024-12-31

# Format des dates : YYYY-MM-DD
```

## 📊 Types de Services Disponibles

- **URGENCES** : Service d'urgence
- **CARDIOLOGIE** : Service de cardiologie
- **PEDIATRIE** : Service de pédiatrie
- **CHIRURGIE** : Service de chirurgie
- **NEUROLOGIE** : Service de neurologie
- **GYNECOLOGIE** : Service de gynécologie
- **DERMATOLOGIE** : Service de dermatologie
- **ORTHOPÉDIE** : Service d'orthopédie
- **PSYCHIATRIE** : Service de psychiatrie
- **RADIOLOGIE** : Service de radiologie
- **LABORATOIRE** : Service de laboratoire
- **PHARMACIE** : Service de pharmacie
- **ADMINISTRATION** : Service administratif
- **DIRECTION** : Direction
- **QUALITE** : Service qualité

## 🎯 Priorités Disponibles

- **URGENT** : Priorité maximale
- **ELEVE** : Priorité élevée
- **MOYEN** : Priorité moyenne
- **BAS** : Priorité basse

## 📈 Statuts Disponibles

- **NOUVELLE** : Plainte nouvellement créée
- **EN_COURS** : En cours de traitement
- **EN_ATTENTE_INFORMATION** : En attente d'informations
- **EN_COURS_TRAITEMENT** : En cours de traitement
- **TRAITEE** : Plainte traitée
- **RESOLUE** : Plainte résolue
- **FERMEE** : Plainte fermée
- **ARCHIVEE** : Plainte archivée

## 🔍 Exemples d'Utilisation

### Dashboard pour les Urgences
```bash
# Statistiques des urgences
GET /api/v1/dashboard/statistiques?type_service=URGENCES

# Plaintes urgentes en cours
GET /api/v1/dashboard/plaintes/en-cours?type_service=URGENCES&priorite=URGENT
```

### Suivi Qualité
```bash
# Statistiques qualité
GET /api/v1/dashboard/statistiques?categorie_principale=QUALITE

# Plaintes qualité traitées ce mois
GET /api/v1/dashboard/plaintes/traitees?categorie_principale=QUALITE&date_debut=2024-01-01
```

### Monitoring Administratif
```bash
# Statistiques administratives
GET /api/v1/dashboard/statistiques?type_service=ADMINISTRATION

# Plaintes administratives en attente
GET /api/v1/dashboard/plaintes/en-attente?type_service=ADMINISTRATION
```

## 📱 Interface Utilisateur

### Navigation Intuitive
- **Page d'accueil** : http://localhost:6000
- **Dashboard unifié** : http://localhost:6000/api/v1/dashboard/statistiques
- **Filtres disponibles** : http://localhost:6000/api/v1/dashboard/filtres-disponibles

### Fonctionnalités
- **Filtres dynamiques** : Sélection en temps réel
- **Pagination** : Navigation dans les résultats
- **Export** : Possibilité d'export des données filtrées
- **Alertes** : Notifications automatiques

## 🔧 Configuration

### Variables d'Environnement
```bash
# Configuration des filtres par défaut
DEFAULT_ORGANISATION_ID=1
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100

# Configuration des alertes
ALERTE_PLAINTES_URGENTES=5
ALERTE_PLAINTES_EN_RETARD=10
```

### Personnalisation
```python
# Exemple de personnalisation des filtres
filtres_personnalises = {
    "type_service": "URGENCES",
    "priorite": "URGENT",
    "categorie_principale": "QUALITE"
}
```

## 📊 Métriques et KPIs

### KPIs Principaux
- **Nouvelles plaintes** : Nombre de plaintes créées
- **Plaintes en attente** : Actions requises
- **Plaintes en retard** : Délais dépassés
- **En cours traitement** : Actuellement traitées
- **Traitées ce mois** : Résolues ce mois
- **Satisfaction moyenne** : Score de satisfaction

### Métriques Avancées
- **Taux de résolution** : Pourcentage de plaintes résolues
- **Délai moyen** : Temps moyen de traitement
- **Répartition par service** : Distribution par service
- **Répartition par priorité** : Distribution par priorité
- **Tendances** : Évolution dans le temps

## 🚀 Démarrage

### Démarrage de l'Application
```bash
# Script Windows
start_all_apis.bat

# Ou directement
cd backend
python start_main_app.py
```

### Accès au Dashboard
- **URL principale** : http://localhost:6000
- **Documentation** : http://localhost:6000/docs
- **Navigation** : http://localhost:6000/navigation

## 🔄 Migration depuis l'Ancien Système

### Changements Principaux
1. **API unifiée** : Un seul endpoint pour tous les dashboards
2. **Filtres avancés** : Système de filtres complet
3. **Performance améliorée** : Optimisation des requêtes
4. **Interface moderne** : Navigation intuitive

### Compatibilité
- ✅ Tous les anciens endpoints restent accessibles
- ✅ Migration transparente
- ✅ Données préservées

---

**HealthCare AI - Dashboard Unifié v1.0.0**
*Interface moderne avec filtres avancés pour la gestion des plaintes médicales* 