# API — Outils de l'écosystème (`/api/tools/`)

Correspond à l'onglet « Nos Outils » de la section Contenus du frontend
(actuellement une liste statique dans `lib/tools.ts`) — rendu dynamique et
administrable ici.

Lecture publique, écriture réservée aux gestionnaires
(`IsManagerOrReadOnly`), standard REST (`ModelViewSet`).

## GET `/api/tools/`

```json
[
  {
    "id": 1,
    "name": "Apprentissage de l'alphabet",
    "description": "Application web ludique pour apprendre à reconnaître, prononcer et tracer les lettres de l'alphabet.",
    "status": "en-developpement",
    "url": "",
    "created_at": "2026-08-04T09:00:00Z"
  }
]
```

`status` ∈ `disponible` | `en-developpement`. `url` est vide tant que
l'outil n'est pas encore disponible — c'est ce que `ToolCard.tsx` utilise
côté frontend pour savoir si la carte doit être cliquable ou affichée comme
« bientôt disponible ».

## POST / PATCH / DELETE `/api/tools/{id}/`

Accès : gestionnaire uniquement. Permet d'ajouter un nouvel outil à la
vitrine, de le faire passer à `disponible` avec son URL une fois prêt, ou de
le retirer.
