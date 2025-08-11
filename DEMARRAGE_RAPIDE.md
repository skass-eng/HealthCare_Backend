# 🚀 Démarrage Rapide - HealthCare AI Architecture ODYSSEE

## ✅ Configuration Récupérée

J'ai récupéré vos paramètres de connexion PostgreSQL existants :

```
HOST: localhost
PORT: 5430
DATABASE: hospital_complaints
USER: postgres
PASSWORD: 242261
```

## 📋 Prérequis

### 1. Services Externes
Assurez-vous que ces services sont démarrés :

```bash
# PostgreSQL (votre base existante)
# ✅ Déjà configuré sur localhost:5430

# Redis (pour Celery et WebSockets)
# Installer Redis si pas encore fait :
# Windows: https://github.com/microsoftarchive/redis/releases
# Ou Docker: docker run -d -p 6379:6379 redis:alpine

# Ollama (pour analyses LLM - optionnel)
# Si vous voulez utiliser Ollama avec mistral:instruct
# https://ollama.ai/download
```

### 2. Vérifier que votre PostgreSQL fonctionne
```bash
# Test rapide de connexion
psql -h localhost -p 5430 -U postgres -d hospital_complaints
# Entrer le mot de passe: 242261
```

## 🔧 Installation et Configuration

### Étape 1: Installer les dépendances
```bash
cd HealthCare_Backend_Odyssee

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement (Windows)
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements_odyssee.txt
```

### Étape 2: Configuration déjà prête
```bash
# Le fichier .env est déjà configuré avec vos paramètres !
# Vérifiez le contenu :
cat .env

# Si vous voulez utiliser OpenAI ou Anthropic, ajoutez vos clés :
# OPENAI_API_KEY="sk-your-key"
# LLM_PROVIDER="openai"
```

### Étape 3: Installer Redis (si pas déjà fait)
```bash
# Option 1: Docker (plus simple)
docker run -d --name redis -p 6379:6379 redis:alpine

# Option 2: Installation native Windows
# Télécharger depuis: https://github.com/microsoftarchive/redis/releases
# Ou utiliser Chocolatey: choco install redis-64
```

## 🚀 Démarrage des Services

### Option 1: Démarrage Automatique (RECOMMANDÉ)
```bash
# 1. Initialiser la base de données avec vos paramètres
python scripts/init_db.py

# 2. Démarrer tous les services
python scripts/start_all.py
```

### Option 2: Démarrage Manuel (pour développement)
```bash
# Terminal 1: API Server
python scripts/start_api.py

# Terminal 2: Worker Principal (analyses LLM)
python scripts/start_worker.py analyses

# Terminal 3: Worker Sentiment
python scripts/start_worker.py sentiment

# Terminal 4: Worker Classification  
python scripts/start_worker.py classification
```

### Option 3: Docker Compose (si Docker disponible)
```bash
cd config/
docker-compose up -d
```

## 🌐 Vérification du Démarrage

Une fois démarré, vous devriez voir :

```
╔═══════════════════════════════════════════════╗
║    🏥 HealthCare AI - Architecture ODYSSEE    ║
║            Démarrage Complet                  ║
║                                               ║
║  🔧 API Server + Worker Server + Services     ║
║  🔄 Inspiré de l'architecture ODYSSEE         ║
╚═══════════════════════════════════════════════╝

🟢 Tous les services sont démarrés!
🌐 Accès:
  - API Documentation: http://localhost:8000/docs
  - API Health: http://localhost:8000/health
```

### Accès aux Services
- **📚 Documentation API** : http://localhost:8000/docs
- **❤️ Health Check** : http://localhost:8000/health
- **🌸 Celery Monitor** : http://localhost:5555 (si Flower démarré)

## 🧪 Test Rapide

### 1. Vérifier l'API
```bash
# Test de santé
curl http://localhost:8000/health

# Réponse attendue:
# {
#   "status": "healthy",
#   "service": "healthcare_api_server",
#   "version": "1.0.0"
# }
```

### 2. Créer un utilisateur de test
L'initialisation a créé des comptes par défaut :

```
📧 admin@healthcare.demo (mot de passe: admin123)
📧 qualite@healthcare.demo (mot de passe: qualite123)  
📧 medecin@healthcare.demo (mot de passe: medecin123)
📧 patient@healthcare.demo (mot de passe: patient123)
```

### 3. Tester la création d'une plainte
```bash
# Obtenir un token d'authentification
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@healthcare.demo",
    "password": "patient123"
  }'

# Utiliser le token pour créer une plainte
curl -X POST "http://localhost:8000/api/v1/plaintes/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "titre": "Test Architecture ODYSSEE",
    "description": "Première plainte avec la nouvelle architecture inspirée d ODYSSEE",
    "organisation_id": "organisation-uuid-from-init"
  }'
```

## 🔧 Dépannage

### Problème 1: Connexion PostgreSQL
```bash
# Vérifier que PostgreSQL est démarré
netstat -an | findstr :5430

# Si pas de réponse, démarrer PostgreSQL
# Services Windows -> PostgreSQL
```

### Problème 2: Redis non disponible
```bash
# Démarrer Redis avec Docker
docker run -d -p 6379:6379 redis:alpine

# Ou installer Redis nativement pour Windows
```

### Problème 3: Erreur de dépendances
```bash
# Réinstaller les dépendances
pip install --upgrade -r requirements_odyssee.txt

# Ou créer un nouvel environnement virtuel
```

### Problème 4: LLM non disponible
```bash
# Vérifier Ollama (si utilisé)
curl http://localhost:11434/api/tags

# Ou désactiver les analyses LLM temporairement
# Dans .env: ANALYSES_AUTO_ENABLED=false
```

## 📊 Surveillance

### Logs
```bash
# Logs API Server
tail -f logs/api_server.log

# Logs Workers
tail -f logs/worker_server.log

# Logs complets
tail -f logs/healthcare_all.log
```

### Statut Celery
```bash
# Depuis le répertoire racine
celery -A healthcare_worker_server.app.core.celery_app inspect active
celery -A healthcare_worker_server.app.core.celery_app inspect stats
```

## 🎯 Prochaines Étapes

1. **Créer des plaintes de test** via l'API
2. **Observer les analyses automatiques** dans les logs
3. **Tester les WebSockets** pour notifications temps réel
4. **Intégrer avec votre frontend** existant
5. **Configurer les clés API LLM** pour analyses avancées

Votre backend HealthCare AI avec architecture ODYSSEE est maintenant prêt ! 🎉