# Backend — API Flores Gong Nota

API REST en Django + Django REST Framework pour la plateforme Flores Gong
Nota (bibliothèque numérique + écosystème d'outils). Ce dossier est
**autonome** : il ne dépend d'aucun fichier du frontend Next.js situé à la
racine du dépôt, et le frontend n'appelle pas encore cette API. C'est un
point de départ, prêt à être branché quand vous le déciderez (voir
[docs/architecture.md](docs/architecture.md) pour le plan de connexion).

## Sommaire

- [Ce que couvre ce backend](#ce-que-couvre-ce-backend)
- [Architecture modulaire](#architecture-modulaire)
- [Démarrage rapide](#démarrage-rapide)
- [Variables d'environnement](#variables-denvironnement)
- [Commandes utiles](#commandes-utiles)
- [Documentation complémentaire](#documentation-complémentaire)
- [Limites connues](#limites-connues--honnêteté-avant-tout)

## Ce que couvre ce backend

Chaque fonctionnalité déjà construite côté frontend a son pendant ici :

| Côté frontend | Côté API |
|---|---|
| Bibliothèque (dossiers/sous-dossiers, documents, recherche) | `apps/library` |
| Lecteur (streaming avec Range, miniatures) | `apps/library` (vues download/thumbnail) |
| Connexion / Inscription (pages UI) | `apps/accounts` |
| Espace gestionnaire → Bibliothèque (ajout dossier/document) | `apps/library` (écriture réservée aux gestionnaires) |
| Espace gestionnaire → Inscriptions | `apps/accounts` (`/registrations/`) |
| Espace gestionnaire → Connexions | `apps/accounts` (`/login-events/`) |
| Espace gestionnaire → Dashboard (chiffres, graphes) | `apps/analytics` |
| FAQ → espace de contact | `apps/contact` |
| Catalogue → onglet "Nos Outils" | `apps/tools` |

## Architecture modulaire

```
Backend/
├── manage.py
├── config/                 # réglages & routage du projet (pas de logique métier)
│   ├── settings/
│   │   ├── base.py         # commun à tous les environnements
│   │   ├── dev.py          # développement local
│   │   └── prod.py         # production (durci)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                   # toute la logique métier, une app Django = un domaine
│   ├── common/              # base partagée : modèle horodaté, permissions, pagination
│   ├── accounts/            # utilisateurs, JWT, historique connexions/inscriptions
│   ├── library/              # dossiers, documents, upload, miniatures, streaming
│   ├── analytics/            # suivi des visites, tableau de bord
│   ├── contact/               # messages envoyés depuis la FAQ
│   └── tools/                  # vitrine "Nos Outils"
├── docs/                    # documentation détaillée (architecture, sécurité, API)
├── media/                   # fichiers téléversés (ignoré par git)
└── logs/                    # journaux (sécurité, etc. — ignoré par git)
```

Chaque app suit la même forme : `models.py`, `serializers.py`, `views.py`,
`urls.py`, `admin.py`, `migrations/`. Rien n'est partagé entre apps sauf via
`apps/common` — pour ajouter un domaine (ex: notifications), on ajoute une
app, pas une couche transversale.

Voir [docs/architecture.md](docs/architecture.md) pour le détail des choix
(pourquoi un utilisateur sans `username`, comment les dossiers imbriqués
sont modélisés, etc).

## Démarrage rapide

Prérequis : Python 3.11+.

```bash
cd Backend

# 1. Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

# 2. Dépendances
pip install -r requirements.txt
# (pour les outils de test/lint en plus : pip install -r requirements-dev.txt)

# 3. Configuration
cp .env.example .env
# ouvrez .env et ajustez au moins DJANGO_SECRET_KEY

# 4. Base de données (SQLite par défaut, aucune installation requise)
python manage.py makemigrations
python manage.py migrate

# 5. Un premier compte gestionnaire (nécessaire pour accéder aux endpoints
#    réservés : /registrations/, /login-events/, /dashboard/, écriture sur
#    la bibliothèque, etc.)
python manage.py create_manager --email=vous@exemple.com --full-name="Votre nom"

# 6. Lancement
python manage.py runserver 0.0.0.0:8001
```

L'API est alors disponible sur `http://localhost:8001/api/` (port 8001
choisi pour ne pas entrer en conflit avec le frontend, qui tourne sur le
port 8000). Vérifiez que tout répond avec :

```bash
curl http://localhost:8001/api/health/
# {"status": "ok"}
```

L'interface d'administration Django (utile pour explorer les données sans
écrire de requêtes) est sur `http://localhost:8001/admin/` — connectez-vous
avec le compte créé à l'étape 5.

## Variables d'environnement

Toutes documentées avec leur valeur par défaut dans
[`.env.example`](.env.example). Aucun secret n'est codé en dur dans le
projet : `config/settings/base.py` lit tout via `django-environ`.

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Clé de signature Django (sessions, tokens CSRF…) — à régénérer, jamais celle du dépôt |
| `DJANGO_DEBUG` | `True` en dev uniquement — jamais en production |
| `DJANGO_ALLOWED_HOSTS` | Domaines autorisés à servir l'app |
| `DATABASE_URL` | SQLite par défaut ; `postgres://…` pour la production |
| `CORS_ALLOWED_ORIGINS` | Origines autorisées à appeler l'API (le frontend, une fois branché) |
| `EMAIL_*` | Envoi d'email (réinitialisation de mot de passe, notifications de contact) |
| `GOOGLE_OAUTH_CLIENT_ID` | Active `/api/accounts/google/` si renseigné |
| `MAX_UPLOAD_SIZE_MB` | Taille maximale d'un document envoyé depuis l'espace gestionnaire |

## Commandes utiles

```bash
# Lancer les tests (une fois requirements-dev.txt installé)
pytest

# Vérifier la configuration Django sans lancer de serveur
python manage.py check

# Ouvrir un shell Django (accès direct aux modèles)
python manage.py shell

# Créer/promouvoir un gestionnaire
python manage.py create_manager --email=... 

# Générer les migrations après modification d'un modèle
python manage.py makemigrations
python manage.py migrate
```

## Documentation complémentaire

- [docs/architecture.md](docs/architecture.md) — pourquoi ces choix, comment
  brancher le frontend plus tard.
- [docs/security.md](docs/security.md) — mesures de sécurité en place et
  checklist avant mise en production.
- `docs/api/` — un fichier par app, endpoints détaillés avec exemples de
  requêtes/réponses :
  [accounts](docs/api/accounts.md) ·
  [library](docs/api/library.md) ·
  [analytics](docs/api/analytics.md) ·
  [contact](docs/api/contact.md) ·
  [tools](docs/api/tools.md)

## Limites connues — honnêteté avant tout

- **Ce code n'a pas été exécuté** dans l'environnement où il a été écrit
  (pas d'accès internet pour installer les dépendances). Il a été relu avec
  soin et chaque fichier `.py` a été vérifié syntaxiquement, mais un
  `python manage.py check` réel, une vraie migration et des tests bout en
  bout restent à faire de votre côté avant toute mise en production —
  suivez le [Démarrage rapide](#démarrage-rapide) ci-dessus et signalez ce
  qui coince.
- **Le frontend n'est pas branché.** Les endpoints sont conçus pour
  correspondre le plus possible aux formes de données déjà utilisées côté
  frontend (mêmes noms de champs quand c'est raisonnable), pour que le
  branchement futur soit une substitution plutôt qu'une réécriture — voir
  [docs/architecture.md](docs/architecture.md).
- **La connexion Google** nécessite de vraies identifiants Google Cloud
  (`GOOGLE_OAUTH_CLIENT_ID`) pour fonctionner ; sans eux, l'endpoint répond
  clairement 501 plutôt que d'échouer silencieusement.
- **Le streaming par plages (Range)** relit le segment demandé en mémoire
  avant de le renvoyer — adapté à l'usage d'un mini-serveur personnel, mais
  à revoir (streaming direct via `wsgi.file_wrapper`) avant un usage à
  grande échelle.
