# 🚀 Guide de Démarrage Rapide - HealthCare AI Architecture ODYSSEE

## 📋 Prérequis

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (pour Celery)

## 🔧 Installation

### 1. Backend (Python/FastAPI)

```bash
cd HealthCare_Backend_Odyssee

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements_odyssee.txt

# Configurer la base de données
# Créer une base PostgreSQL nommée 'healthcare_ai'
```

### 2. Frontend (React/TypeScript)

```bash
cd Explorer_frontend

# Installer les dépendances
npm install

# Installer les dépendances manquantes
npm install lucide-react date-fns
```

## 🚀 Démarrage

### 1. Base de données

```bash
# Démarrer PostgreSQL
# Démarrer Redis
```

### 2. Backend

```bash
cd HealthCare_Backend_Odyssee

# Activer l'environnement virtuel
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Créer les données de test
python scripts/create_test_data.py

# Démarrer l'API
python healthcare_api_server/app/main.py
```

### 3. Workers Celery

```bash
# Dans un nouveau terminal
cd HealthCare_Backend_Odyssee
source venv/bin/activate

# Démarrer les workers
celery -A healthcare_worker_server.app.core.celery_app worker --loglevel=info
```

### 4. Frontend

```bash
cd Explorer_frontend
npm run dev
```

## 🧪 Test de la Création de Plaintes

### 1. Test via Script

```bash
cd HealthCare_Backend_Odyssee
python scripts/test_creation_plainte.py
```

### 2. Test via Frontend

1. Ouvrir http://localhost:5173
2. Se connecter avec les identifiants de test
3. Aller sur `/plaintes/creer`
4. Remplir le formulaire et créer une plainte

### 3. Test via API

```bash
# Créer une plainte
curl -X POST http://localhost:8000/api/v1/plaintes \
  -H "Content-Type: application/json" \
  -d '{
    "titre": "Plainte de test",
    "description": "Description de la plainte",
    "organisation_id": 1,
    "service_id": 1
  }'
```

## 📊 Vérification

### 1. Vérifier les plaintes créées

```bash
curl http://localhost:8000/api/v1/plaintes
```

### 2. Vérifier les analyses IA

```bash
curl http://localhost:8000/api/v1/plaintes/1/analyses
```

### 3. Vérifier les PDFs générés

Les PDFs sont stockés dans :
- `data/pdfs/` : PDFs d'archivage
- `data/reponses/` : PDFs de réponses

## 🔍 Monitoring

### Logs

```bash
# Logs API
tail -f logs/api_server.log

# Logs Workers
tail -f logs/worker_server.log

# Logs Frontend
# Dans la console du navigateur
```

### Statut des services

```bash
# Vérifier l'API
curl http://localhost:8000/health

# Vérifier les workers
celery -A healthcare_worker_server.app.core.celery_app inspect active
```

## 🐛 Dépannage

### Erreur de connexion à l'API
- Vérifier que l'API est démarrée sur le port 8000
- Vérifier les logs dans `logs/api_server.log`

### Erreur de base de données
- Vérifier que PostgreSQL est démarré
- Vérifier la connexion dans `healthcare_api_server/app/core/config.py`

### Erreur de workers
- Vérifier que Redis est démarré
- Vérifier que les workers Celery sont actifs

### Erreur de frontend
- Vérifier que Node.js est installé
- Vérifier que toutes les dépendances sont installées
- Vérifier la console du navigateur pour les erreurs

## 📈 Fonctionnalités Testées

✅ **Création de plaintes** - Formulaire complet avec validation
✅ **Sauvegarde en base** - PostgreSQL avec relations
✅ **Analyses IA** - Sentiment, classification, priorité
✅ **Génération PDF** - Archivage automatique
✅ **Interface moderne** - React avec TypeScript
✅ **API REST** - Endpoints complets
✅ **Workers asynchrones** - Celery pour les tâches lourdes

## 🎯 Prochaines Étapes

1. **Notifications temps réel** - WebSockets
2. **Réponses automatiques** - IA pour rédiger des réponses
3. **Dashboard avancé** - Statistiques et métriques
4. **Gestion des utilisateurs** - Rôles et permissions
5. **Export de données** - Rapports et exports

## 📝 Notes

- Les analyses IA sont asynchrones (peuvent prendre quelques secondes)
- Les PDFs sont générés automatiquement après les analyses
- Toutes les erreurs sont loggées pour le debugging
- Le système est conçu pour être robuste et récupérer des erreurs

## 🔗 URLs

- **Frontend** : http://localhost:5173
- **API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **Health Check** : http://localhost:8000/health

## 📞 Support

En cas de problème :
1. Vérifier les logs dans le dossier `logs/`
2. Vérifier la console du navigateur
3. Vérifier les processus en cours d'exécution
4. Redémarrer les services si nécessaire 