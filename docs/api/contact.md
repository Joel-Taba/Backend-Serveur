# API — Contact (`/api/contact/`)

Correspond à l'espace de contact de la FAQ (`components/ContactForm.tsx`) :
plaintes, encouragements, critiques, appréciations.

## POST `/api/contact/messages/`

Accès : public.

**Requête**
```json
{
  "name": "Un visiteur",
  "email": "visiteur@example.com",
  "message_type": "appreciation",
  "message": "Merci pour cette bibliothèque, vraiment pratique !"
}
```

`message_type` ∈ `appreciation` | `suggestion` | `critique` | `plainte` |
`autre` (par défaut). `name` et `email` sont facultatifs — le frontend
actuel (formulaire `mailto:`) ne les collecte pas systématiquement non
plus.

**Réponse `201 Created`** — le message créé. Une notification est envoyée
par email à `CONTACT_NOTIFICATION_EMAIL` (`joeltaba4@gmail.com` par défaut),
en best-effort (`fail_silently=True` : un email qui échoue n'empêche pas
l'enregistrement du message).

## GET `/api/contact/messages/`

Accès : gestionnaire uniquement. Liste paginée, du plus récent au plus
ancien.

## PATCH `/api/contact/messages/{id}/`

Accès : gestionnaire uniquement. Seul `is_read` est modifiable — sert à
marquer un message comme traité depuis un futur écran d'administration.

```json
{ "is_read": true }
```
