# Healthcare Backend API

Backend API pour l'application de gestion des plaintes de santé.

## 🚀 Technologies utilisées

- **Python 3.8+**
- **FastAPI** - Framework web moderne et rapide
- **SQLAlchemy** - ORM pour la base de données
- **PostgreSQL** - Base de données principale
- **Pydantic** - Validation des données
- **Uvicorn** - Serveur ASGI

## 📋 Prérequis

- Python 3.8 ou supérieur
- PostgreSQL installé et configuré
- pip (gestionnaire de paquets Python)

## 🛠️ Installation

1. **Cloner le repository**
   ```bash
   git clone <repository-url>
   cd HealthCare_Backend
   ```

2. **Créer un environnement virtuel**
   ```bash
   python -m venv venv
   ```

3. **Activer l'environnement virtuel**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configurer la base de données**
   - Créer une base de données PostgreSQL
   - Modifier le fichier `config.py` avec vos paramètres de connexion

6. **Initialiser la base de données**
   ```bash
   python init_postgres.sql
   ```

## 🚀 Démarrage

1. **Démarrer le serveur de développement**
   ```bash
   python main_app.py
   ```

2. **Ou utiliser uvicorn directement**
   ```bash
   uvicorn main_app:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Accéder à l'API**
   - API: http://localhost:8000
   - Documentation Swagger: http://localhost:8000/docs
   - Documentation ReDoc: http://localhost:8000/redoc

## 📁 Structure du projet

```
HealthCare_Backend/
├── main_app.py              # Point d'entrée principal
├── api_unified.py           # API unifiée
├── api_dashboard_unified.py # API pour le dashboard
├── api_pages.py             # API pour les pages
├── models_unified.py        # Modèles de données
├── schemas_unified.py       # Schémas Pydantic
├── database_unified.py      # Configuration de la base de données
├── config.py                # Configuration
├── requirements.txt         # Dépendances Python
├── services/                # Services métier
├── data/                    # Données
├── logs/                    # Fichiers de logs
└── uploads/                 # Fichiers uploadés
```

## 🔧 Configuration

Modifiez le fichier `config.py` pour configurer :

- **Base de données PostgreSQL**
- **Paramètres de sécurité**
- **Configuration CORS**
- **Variables d'environnement**

## 📊 Endpoints principaux

### Plaintes
- `GET /api/plaintes` - Liste des plaintes
- `POST /api/plaintes` - Créer une plainte
- `GET /api/plaintes/{id}` - Détails d'une plainte
- `PUT /api/plaintes/{id}` - Modifier une plainte
- `DELETE /api/plaintes/{id}` - Supprimer une plainte

### Analytics
- `GET /api/analytics/rapport-complet` - Rapport complet
- `GET /api/stats/tendances` - Tendances statistiques
- `GET /api/suggestions/par-service` - Suggestions par service

### Dashboard
- `GET /api/dashboard/stats` - Statistiques du dashboard
- `GET /api/dashboard/plaintes` - Plaintes pour le dashboard

## 🔒 Sécurité

- CORS configuré pour le frontend
- Validation des données avec Pydantic
- Gestion des erreurs centralisée
- Logs de sécurité

## 📝 Logs

Les logs sont stockés dans le dossier `logs/` :
- `app.log` - Logs de l'application
- `error.log` - Logs d'erreurs
- `access.log` - Logs d'accès

## 🧪 Tests

```bash
# Lancer les tests
python -m pytest

# Tests avec couverture
python -m pytest --cov=.
```

## 📦 Déploiement

### Production
```bash
# Installer gunicorn
pip install gunicorn

# Démarrer en production
gunicorn main_app:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```bash
# Construire l'image
docker build -t healthcare-backend .

# Lancer le conteneur
docker run -p 8000:8000 healthcare-backend
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou problème :
- Créer une issue sur GitHub
- Contacter l'équipe de développement

## 🔄 Mise à jour

```bash
# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade

# Mettre à jour le code
git pull origin main
``` 