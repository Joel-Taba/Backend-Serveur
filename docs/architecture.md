# Architecture

## Principe : une app = un domaine métier

Le dossier `apps/` contient six apps Django, chacune responsable d'un seul
domaine, avec la même forme interne (`models.py`, `serializers.py`,
`views.py`, `urls.py`, `admin.py`, `migrations/`) :

- **`common`** — rien de métier : un modèle abstrait `TimeStampedModel`
  (`created_at`/`updated_at`), les permissions transversales (`IsManager`,
  `IsManagerOrReadOnly`) et la pagination par défaut. Toute app peut en
  dépendre ; aucune app métier ne dépend d'une autre app métier, sauf
  `analytics` qui lit `library` pour construire le tableau de bord (lien
  assumé : le tableau de bord n'a pas de sens sans les données de la
  bibliothèque).
- **`accounts`** — utilisateurs, authentification JWT, historique des
  connexions et des inscriptions.
- **`library`** — dossiers (`Category`), documents (`Document`), upload,
  miniatures, streaming avec support des requêtes `Range`.
- **`analytics`** — visites et endpoint de tableau de bord.
- **`contact`** — messages envoyés depuis la FAQ du frontend.
- **`tools`** — vitrine « Nos Outils ».

`config/` ne contient **aucune logique métier** : uniquement les réglages et
le montage des URLs de chaque app sous son préfixe (`/api/accounts/`,
`/api/library/`, …). Si demain une septième app apparaît (notifications,
paiement, …), elle s'ajoute au même endroit sans toucher aux autres.

## Modélisation

### Utilisateurs (`apps.accounts.User`)

Le frontend n'a jamais eu de champ « nom d'utilisateur » séparé — seulement
un nom complet, un email et un mot de passe (`SignupForm.tsx`). Plutôt que
d'hériter de `AbstractUser` (qui impose un `username` unique dont on
n'aurait rien fait), `User` hérite directement de `AbstractBaseUser` +
`PermissionsMixin`, avec `email` comme `USERNAME_FIELD`. Un champ `role`
(`user` / `manager`) distingue les visiteurs des gestionnaires — c'est ce
qui protège tout l'espace `/admin` du frontend une fois branché.

### Dossiers imbriqués (`apps.library.Category`)

Le frontend représente chaque dossier par un tableau de segments
(`id: string[]`, ex. `["primaire", "sous-dossier"]`), reconstruit à la volée
en scannant le système de fichiers (`lib/catalog.ts`). Côté base de données,
`Category` est un arbre classique : une simple clé étrangère
`parent` (auto-référence), sans bibliothèque tierce (pas de MPTT/django-tree
— l'app n'a pas besoin de requêtes d'arbre complexes, seulement de remonter
ou parcourir quelques niveaux). `Category.get_path_segments()` reconstruit
l'équivalent du tableau `id: string[]` du frontend en remontant les
`parent` jusqu'à la racine — c'est la méthode à connaître pour tout ce qui
touche à la correspondance avec le frontend.

L'unicité d'un nom de dossier « à un emplacement donné » (y compris à la
racine, où `parent` est `NULL`) n'est **pas garantie de façon fiable par la
seule contrainte SQL** `UniqueConstraint(parent, slug)` — la plupart des
moteurs SQL traitent deux `NULL` comme différents, donc deux dossiers
racine pourraient théoriquement porter le même nom sans que la contrainte
s'en aperçoive. C'est pourquoi `CategorySerializer.validate()` fait cette
vérification explicitement en Python, quel que soit le moteur de base de
données utilisé.

### Documents (`apps.library.Document`)

`doc_type` et `size` sont calculés automatiquement à l'enregistrement
(`Document.save()`), jamais saisis par le client — on ne fait pas confiance
à ce qu'envoie le front pour ces champs, exactement comme
`lib/catalog.ts` déduit le type depuis l'extension plutôt que d'un champ
libre.

### Visites (`apps.analytics.Visit`)

Avant ce backend, le frontend traçait les visites dans un fichier JSON local
(`.cache/analytics.json`, incrémenté à chaque chargement de la page
d'accueil) — une solution honnête en l'absence de compte utilisateur
fonctionnel, documentée comme un *proxy* pour « connexions ». `Visit` est
l'équivalent base de données de ce même compteur : `POST
/api/analytics/track-visit/` remplacera l'écriture dans le fichier JSON une
fois le frontend branché. Le tableau de bord agrège ces visites par jour
avec `TruncDate`, sur le même principe que
`lib/analytics.ts::getRecentVisits()`.

### Historique des connexions (`apps.accounts.LoginEvent`)

Chaque tentative de connexion — réussie **ou échouée** — crée une ligne. Le
champ `user` est nullable exprès : une tentative avec un email qui ne
correspond à aucun compte ne peut pas être rattachée à un utilisateur, mais
reste tracée (`email_attempted`) pour la sécurité (repérer un brute-force).
C'est ce que consulte la section « Connexions » de l'espace gestionnaire du
frontend.

## Correspondance des formes de données

Pour que brancher le frontend plus tard soit une substitution de source de
données plutôt qu'une réécriture de composants, plusieurs endpoints
reprennent délibérément la forme exacte utilisée côté frontend :

- `GET /api/library/tree/` renvoie `{"tree": [...]}` avec un champ `kind`
  (`"folder"` | `"document"`) sur chaque nœud — c'est exactement le type
  `CatalogNode` de `lib/catalog.ts`.
- `GET /api/analytics/dashboard/` renvoie `document_count`, `folder_count`,
  `today_visits`, `total_visits`, `visits` (liste `{date, count}`),
  `category_breakdown` et `format_breakdown` — les mêmes clés que
  `DashboardData` dans `components/admin/DashboardOverview.tsx`.

## Brancher le frontend (plan, pas encore fait)

1. Définir `NEXT_PUBLIC_API_BASE_URL` côté frontend et `CORS_ALLOWED_ORIGINS`
   côté backend.
2. Remplacer les appels à `lib/catalog.ts` (accès direct au système de
   fichiers) par des appels à `/api/library/tree/`, `/api/library/documents/`,
   etc. — les composants (`Catalogue.tsx`, `DocumentRow.tsx`…) n'ont pas à
   changer de forme de données, seulement leur source.
3. Remplacer `lib/analytics.ts::recordVisit()` par un appel à
   `POST /api/analytics/track-visit/`.
4. Brancher les pages `/connexion` et `/inscription` (actuellement des
   formulaires sans effet) sur `POST /api/accounts/login/` et
   `POST /api/accounts/register/`, en stockant les jetons JWT retournés.
5. Protéger `/admin` côté frontend en vérifiant `role === "manager"` sur
   l'utilisateur connecté (`GET /api/accounts/me/`), et faire pointer
   `LibraryManager.tsx`/`DashboardOverview.tsx` vers les endpoints
   correspondants au lieu des routes internes Next.js actuelles.
