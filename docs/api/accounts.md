# API — Comptes (`/api/accounts/`)

Correspond aux pages `/connexion` et `/inscription` du frontend, et aux
sections « Inscriptions » / « Connexions » de l'espace gestionnaire
(`/admin`).

## POST `/api/accounts/register/`

Inscription. Accès : public. Limite : 5 requêtes/minute par IP.

**Requête**
```json
{
  "full_name": "Amina Diallo",
  "email": "amina@example.com",
  "password": "un-mot-de-passe-suffisamment-long"
}
```

**Réponse `201 Created`**
```json
{
  "user": { "id": 3, "email": "amina@example.com", "full_name": "Amina Diallo", "role": "user", "is_active": true, "date_joined": "2026-08-04T10:00:00Z" },
  "access": "<jwt>",
  "refresh": "<jwt>"
}
```

`400 Bad Request` si l'email est déjà utilisé ou si le mot de passe ne
respecte pas les règles (voir `docs/security.md`).

## POST `/api/accounts/login/`

Connexion. Accès : public. Limite : 10 requêtes/minute par IP. Chaque
tentative est journalisée dans `LoginEvent`, qu'elle réussisse ou non.

**Requête**
```json
{ "email": "amina@example.com", "password": "...", "remember_me": true }
```

`remember_me: true` porte la durée de vie du jeton de rafraîchissement à 30
jours (au lieu d'1 jour par défaut — voir `REMEMBER_ME_REFRESH_LIFETIME`).

**Réponse `200 OK`** — même forme que `/register/`.

**Réponse `401 Unauthorized`**
```json
{ "detail": "Email ou mot de passe incorrect." }
```

## POST `/api/accounts/token/refresh/`

Standard `djangorestframework-simplejwt`. Requête `{"refresh": "<jwt>"}`,
réponse `{"access": "<jwt>"}` (nouveau jeton de rafraîchissement inclus si
`ROTATE_REFRESH_TOKENS` — c'est le cas ici).

## POST `/api/accounts/logout/`

Accès : authentifié. Révoque le jeton fourni (`{"refresh": "<jwt>"}`) : il
ne pourra plus servir à obtenir de nouveaux jetons d'accès. Réponse `205
Reset Content`.

## POST `/api/accounts/google/`

Bouton « Continuer avec Google ». Accès : public.

**Requête** `{"id_token": "<jeton renvoyé par Google Identity Services>"}`

**Réponse `200 OK`** — même forme que `/login/`, avec en plus `"created":
true|false` selon qu'un nouveau compte a été créé.

**Réponse `501 Not Implemented`** si `GOOGLE_OAUTH_CLIENT_ID` n'est pas
configuré sur le serveur, ou si `google-auth` n'est pas installé — voir
`docs/security.md` et le README pour la configuration requise.

## GET/PATCH `/api/accounts/me/`

Profil de l'utilisateur connecté. Accès : authentifié (en-tête `Authorization:
Bearer <access>`).

```json
{ "id": 3, "email": "amina@example.com", "full_name": "Amina Diallo", "role": "user", "is_active": true, "date_joined": "..." }
```

`role` et `is_active` sont en lecture seule — un utilisateur ne peut pas
s'auto-promouvoir gestionnaire via cet endpoint.

## POST `/api/accounts/password-reset/`

Correspond au lien « Mot de passe oublié ? » de la page `/connexion`.
Accès : public. Limite : 5/minute.

**Requête** `{"email": "amina@example.com"}`

**Réponse `200 OK`** — toujours le même message, que l'email corresponde à
un compte ou non (voir `docs/security.md` — anti-énumération) :
```json
{ "detail": "Si un compte existe pour cette adresse, un email a été envoyé." }
```

## POST `/api/accounts/password-reset/confirm/`

**Requête**
```json
{ "uid": "<depuis le lien reçu par email>", "token": "<idem>", "new_password": "..." }
```

**Réponse `200 OK`** `{"detail": "Mot de passe mis à jour."}`, ou `400` si
le lien est invalide/expiré.

## GET `/api/accounts/registrations/`

Historique des inscriptions — section « Inscriptions » de l'espace
gestionnaire. Accès : gestionnaire uniquement. Paginé, trié du plus récent
au plus ancien. Chaque élément a la même forme que `/me/`.

## GET `/api/accounts/login-events/`

Historique des connexions — section « Connexions » de l'espace
gestionnaire. Accès : gestionnaire uniquement.

```json
{
  "id": 42,
  "user": 3,
  "user_email": "amina@example.com",
  "email_attempted": "amina@example.com",
  "success": true,
  "ip_address": "192.168.1.12",
  "user_agent": "Mozilla/5.0 …",
  "created_at": "2026-08-04T10:05:00Z"
}
```

`user` est `null` et `success` est `false` pour une tentative avec un email
qui ne correspond à aucun compte — c'est volontaire, voir
`docs/architecture.md`.
