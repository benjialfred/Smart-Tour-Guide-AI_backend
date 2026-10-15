# Smart Tour Guide AI — Backend Django & Agent MCP Geoapify

Backend d'orchestration pour l'application **Smart Tour Guide AI**, propulsé par Django REST Framework, l'agent IA Grok / Groq et le protocole MCP (Model Context Protocol) connecté aux APIs Geoapify.

---

## 🚀 Fonctionnalités Clés

- **Agent IA Tour Guide** : Orchestration conversationnelle avec Groq / Grok (`qwen/qwen3.8-27b` ou `openai/gpt-oss-120b`).
- **Client & Manifeste MCP Geoapify** : Exécution des outils géographiques via le standard Model Context Protocol :
  - `geoapify_geocode` : Géocodage précis d'adresses, villes et monuments.
  - `geoapify_places_search` : Recherche de points d'intérêt (monuments, musées, gastronomie, parcs) avec filtres par catégorie et rayon.
  - `geoapify_routing` : Calcul d'itinéraires piétons ou cyclables avec géométrie LineString et temps de marche réel.
  - `geoapify_place_details` : Récupération des informations détaillées (horaires, contact, site web).
- **Normalisation GeoJSON RFC 7946** : Transformation automatique des données spatiales pour affichage immédiat dans Leaflet.
- **Mémoire & Persistance des Visites** : Historique des sessions de voyage, messages, itinéraires et favoris stockés dans SQLite via les modèles Django.
- **Synthèse Vocale Prête à l'Emploi** : Génération d'un script de narration audio pour chaque étape.

---

## 📁 Structure du Projet

```
Smart-Tour-Guide-AI_backend/
├── .env                     # Variables d'environnement configurées (clés Groq et Geoapify)
├── .env.example             # Modèle de configuration
├── requirements.txt         # Dépendances Python
├── manage.py
├── smart_guide_backend/     # Configuration globale Django & CORS
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── guide_core/              # Application principale
    ├── models.py            # TourSession, ChatMessage, SavedItinerary, SavedPlace
    ├── views.py             # Chat, Sessions, GeoCode, Places, Route, MCP Manifest
    ├── serializers.py       # Sérialiseurs DRF
    ├── urls.py              # Routes API (/api/...)
    ├── services/
    │   ├── geoapify_service.py # Client REST Geoapify & normalisation GeoJSON
    │   ├── geoapify_mcp.py     # Définitions MCP & dispatcher d'outils
    │   └── agent_service.py    # Agent Grok, gestion des tours de dialogue & mémoire
    └── tests/               # Suite complète de tests unitaires et d'intégration
```

---

## 🛠️ Installation & Démarrage

### 1. Activer l'environnement virtuel

```powershell
cd Smart-Tour-Guide-AI_backend
.venv\Scripts\activate
```

*(Si l'environnement n'existe pas encore : `python -m venv .venv` puis `.venv\Scripts\pip install -r requirements.txt`)*

### 2. Appliquer les migrations de base de données

```powershell
.venv\Scripts\python.exe manage.py migrate
```

### 3. Lancer la suite de tests

```powershell
.venv\Scripts\python.exe manage.py test
```

### 4. Démarrer le serveur backend

```powershell
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Le serveur sera accessible sur `http://127.0.0.1:8000`.

---

## 📡 Endpoints de l'API REST

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health/` | État de santé du backend et statut des clés API |
| `POST` | `/api/chat/` | Envoi d'un message au guide IA, exécution MCP et réponse GeoJSON |
| `GET / POST` | `/api/sessions/` | Liste ou création de sessions de visite |
| `GET / DELETE` | `/api/sessions/<uuid>/` | Récupération de l'historique ou suppression d'une session |
| `GET` | `/api/geo/geocode/?text=Rome` | Recherche de coordonnées GPS pour une ville ou adresse |
| `GET` | `/api/geo/places/?text=Paris&categories=tourism.sights` | Recherche directe de points d'intérêt |
| `POST` | `/api/geo/route/` | Calcul d'un itinéraire piéton/voiture entre waypoints |
| `GET / POST` | `/api/itineraries/` | Sauvegarde et consultation d'itinéraires complets |
| `GET / POST` | `/api/places/` | Gestion des lieux favoris enregistrés |
| `GET` | `/api/mcp/manifest/` | Manifeste complet des outils MCP Geoapify |
