# API — Statistiques (`/api/analytics/`)

Alimente la page Dashboard de l'espace gestionnaire du frontend
(`components/admin/DashboardOverview.tsx`).

## POST `/api/analytics/track-visit/`

Enregistre une visite. Accès : public — à appeler par le frontend à chaque
chargement de la page d'accueil, en remplacement de l'écriture directe dans
`.cache/analytics.json` (voir `docs/architecture.md`).

**Requête** (le corps est optionnel)
```json
{ "path": "/" }
```

**Réponse** `201 Created`, corps vide.

## GET `/api/analytics/dashboard/`

Accès : gestionnaire uniquement. Reprend exactement les clés de
`DashboardData` côté frontend, pour que brancher ce endpoint soit une
substitution directe de la source de données du composant.

```json
{
  "document_count": 15,
  "folder_count": 3,
  "today_visits": 4,
  "total_visits": 128,
  "visits": [
    { "date": "2026-07-22", "count": 3 },
    { "date": "2026-07-23", "count": 0 },
    "… 14 jours au total, aujourd'hui inclus, jours sans visite à 0 …"
  ],
  "category_breakdown": [
    { "label": "Primaire", "value": 6 },
    { "label": "Secondaire", "value": 5 },
    { "label": "Superieur", "value": 4 }
  ],
  "format_breakdown": [
    { "label": "pdf", "value": 14 },
    { "label": "json", "value": 1 }
  ]
}
```

`category_breakdown` compte les documents d'une catégorie racine **et de
tous ses sous-dossiers** (récursif), comme `countDocumentsInNode()` côté
frontend — pas seulement les documents directement à la racine du dossier.
