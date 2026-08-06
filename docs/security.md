# Sécurité

## Ce qui est déjà en place

### Authentification & mots de passe

- Mots de passe jamais stockés en clair : hachage PBKDF2 fourni par Django
  (`AbstractBaseUser.set_password`).
- `AUTH_PASSWORD_VALIDATORS` refuse les mots de passe trop courts (< 8
  caractères), trop proches des infos du compte, trop communs, ou
  entièrement numériques.
- Authentification par JWT (`djangorestframework-simplejwt`) : jeton d'accès
  court (15 min), jeton de rafraîchissement à rotation automatique et mis en
  liste noire après usage (`ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`)
  — un jeton de rafraîchissement volé ne peut pas être rejoué indéfiniment.
- `POST /api/accounts/logout/` met explicitement le jeton en liste noire :
  une déconnexion révoque réellement l'accès, plutôt que de simplement
  « oublier » le jeton côté client.
- Réinitialisation de mot de passe : réponse **identique** que l'email
  existe ou non (`PasswordResetRequestView`), pour empêcher l'énumération
  de comptes existants ; jeton à usage unique et signé
  (`PasswordResetTokenGenerator` de Django).

### Autorisation

- Principe de moindre privilège : `DEFAULT_PERMISSION_CLASSES` est
  `IsAuthenticated` par défaut — un endpoint est **protégé sauf déclaration
  contraire explicite**, jamais l'inverse.
- Deux permissions dédiées (`apps/common/permissions.py`) : `IsManager`
  (accès réservé aux gestionnaires) et `IsManagerOrReadOnly` (lecture
  publique, écriture réservée) — utilisées explicitement sur chaque vue
  selon ce que fait réellement l'équivalent frontend (la bibliothèque se
  parcourt sans compte, mais seul un gestionnaire y ajoute du contenu).
- Historique des connexions et des inscriptions strictement réservé aux
  gestionnaires (`IsManager`).

### Contre le brute-force

- Limites de fréquence (throttling) dédiées sur les endpoints sensibles :
  connexion (10/minute), inscription (5/minute), réinitialisation de mot de
  passe (5/minute) — en plus des limites générales anonyme/authentifié.
- Chaque tentative de connexion, réussie ou non, est journalisée
  (`LoginEvent`) avec IP et user-agent — permet de repérer un
  acharnement sur un compte a posteriori, même si le throttling n'a pas
  suffi à le bloquer en temps réel.
- Journal dédié (`logs/security.log`, `apps.accounts` logger) qui trace les
  inscriptions, connexions réussies/échouées et réinitialisations de mot de
  passe, séparément des logs applicatifs génériques.

### Téléversement de fichiers

- Extension vérifiée contre une liste blanche
  (`ALLOWED_DOCUMENT_EXTENSIONS`, synchronisée avec `lib/catalog.ts` côté
  frontend) — un `.exe` renommé en `.pdf` échoue quand même car la
  vérification porte sur l'extension déclarée, pas sur le nom voulu par
  l'utilisateur (voir limite ci-dessous).
- Taille maximale configurable (`MAX_UPLOAD_SIZE_MB`, 300 Mo par défaut).
- Le fichier n'est jamais servi depuis son chemin disque réel : toujours via
  `DocumentDownloadView`, qui ne révèle aucune information sur
  l'arborescence du serveur.

### Réseau & en-têtes

- CORS en liste blanche explicite (`CORS_ALLOWED_ORIGINS`) — jamais de
  wildcard `*`, en particulier une fois le frontend branché.
- `django-cors-headers` place le middleware CORS très tôt, comme recommandé
  par sa documentation.
- Réponses de fichiers avec `X-Content-Type-Options: nosniff` — un
  navigateur ne doit pas deviner un type de contenu différent de celui
  annoncé (mitige les attaques de confusion de type MIME).

### Configuration & secrets

- Aucun secret dans le code : tout passe par des variables d'environnement
  (`django-environ`), avec `.env` explicitement dans `.gitignore`.
- `config/settings/prod.py` **échoue au démarrage** si `DJANGO_SECRET_KEY`
  ou `DJANGO_ALLOWED_HOSTS` ne sont pas fournis (pas de valeur par défaut
  dangereuse en production), contrairement à `dev.py` qui reste permissif
  pour ne pas gêner le développement local.
- `config/settings/prod.py` active HTTPS forcé, cookies de session/CSRF
  marqués `Secure`/`HttpOnly`, HSTS (30 jours, sous-domaines inclus),
  `X-Frame-Options: DENY`.

## Ce qui reste à faire avant une mise en production réelle

Cette checklist est volontairement explicite plutôt qu'implicite — mieux
vaut une limite connue qu'une fausse impression de sécurité :

- [ ] **Exécuter réellement le projet** (voir la section « Limites connues »
      du README) : ce code n'a pas tourné dans l'environnement où il a été
      écrit, faute d'accès internet pour installer les dépendances.
- [ ] Générer une vraie `DJANGO_SECRET_KEY` aléatoire (`python -c "import
      secrets; print(secrets.token_urlsafe(50))"`), différente entre
      environnements.
- [ ] Vérifier le contenu réel des fichiers téléversés, pas seulement leur
      extension — un scan antivirus (ex: ClamAV) ou une vérification de
      signature de fichier (« magic bytes ») avant acceptation, si la
      plateforme s'ouvre à des utilisateurs non approuvés.
- [ ] Configurer un vrai serveur d'email (SMTP) — le backend `console` par
      défaut n'envoie rien, il affiche juste l'email dans le terminal.
- [ ] Mettre en place une rotation/expiration des logs de sécurité au-delà
      du `RotatingFileHandler` déjà configuré (5 fichiers de 5 Mo), selon la
      politique de rétention voulue.
- [ ] Placer l'API derrière un reverse proxy (nginx, Caddy…) qui termine le
      TLS, comme anticipé par `SECURE_PROXY_SSL_HEADER` dans `prod.py`.
- [ ] Revoir le streaming par plages (`Range`) pour éviter de charger un
      segment entier en mémoire — voir « Limites connues » du README.
- [ ] Ajouter une vraie suite de tests automatisés (le projet est structuré
      pour `pytest-django`, mais aucun test n'a encore été écrit).
- [ ] Configurer `GOOGLE_OAUTH_CLIENT_ID` avec de vrais identifiants Google
      Cloud si la connexion Google doit réellement fonctionner.
