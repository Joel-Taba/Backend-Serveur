# API — Bibliothèque (`/api/library/`)

Correspond à la section « Contenus » / onglet « Bibliothèque » du frontend,
ainsi qu'à sa gestion depuis l'espace `/admin`.

Lecture (`GET`) publique pour tout ce qui suit — la bibliothèque se
parcourt sans compte, comme côté frontend. Écriture (`POST`/`PATCH`/`PUT`/
`DELETE`) réservée aux gestionnaires (`IsManagerOrReadOnly`).

## GET `/api/library/tree/`

Arborescence complète, dossiers et documents mélangés — miroir direct de
`getCatalogTree()` côté frontend. Chaque nœud porte un champ `kind`.

```json
{
  "tree": [
    {
      "kind": "folder",
      "id": 1,
      "name": "Primaire",
      "path": ["primaire"],
      "children": [
        {
          "kind": "document",
          "id": 5,
          "title": "Algorithme Quantique",
          "doc_type": "pdf",
          "size": 374525,
          "path": ["primaire", "algorithme-quantique"],
          "download_url": "http://localhost:8001/api/library/documents/5/download/",
          "thumbnail_url": "http://localhost:8001/api/library/documents/5/thumbnail/"
        }
      ]
    }
  ]
}
```

## Dossiers — `/api/library/categories/`

Standard REST (`ModelViewSet`) : `GET` (liste), `POST` (création,
gestionnaire), `GET /{id}/`, `PATCH`/`PUT /{id}/`, `DELETE /{id}/`.

- `?parent=<id>` filtre les enfants directs d'un dossier ; `?parent=` (vide)
  cible la racine.
- Créer un dossier : `POST` avec `{"name": "Secondaire", "parent": null}` —
  reprend le formulaire « Créer le dossier » de l'espace gestionnaire
  (`LibraryManager.tsx`).
- `400 Bad Request` si un dossier du même nom existe déjà au même
  emplacement, ou si l'opération créerait un cycle (déplacer un dossier
  dans l'un de ses propres sous-dossiers).

## Documents — `/api/library/documents/`

Standard REST également.

- `?category=<id>` filtre par dossier direct ; `?category=` (vide) cible les
  documents à la racine.
- `?q=recherche` filtre par titre **ou** par nom d'un dossier ancêtre
  (le « genre » de la recherche côté frontend, voir `HeroSearchForm.tsx`) —
  insensible à la casse.
- Créer un document : `POST multipart/form-data` avec `file` (obligatoire),
  `category` (optionnel, id du dossier), `title` (optionnel — déduit du nom
  de fichier sinon, comme côté frontend). Reprend le bouton « Ajouter un
  document » de l'espace gestionnaire.
- `doc_type` et `size` sont calculés automatiquement, jamais acceptés en
  entrée.
- `400 Bad Request` si l'extension n'est pas dans la liste autorisée
  (`.pdf`, `.epub`, `.json`, `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`), si le
  fichier dépasse `MAX_UPLOAD_SIZE_MB`, ou si un document du même nom existe
  déjà dans ce dossier.

**Exemple de réponse** (`GET /api/library/documents/5/`)
```json
{
  "id": 5,
  "title": "Algorithme Quantique",
  "slug": "algorithme-quantique",
  "category": 1,
  "doc_type": "pdf",
  "size": 374525,
  "path": ["primaire", "algorithme-quantique"],
  "download_url": "http://localhost:8001/api/library/documents/5/download/",
  "thumbnail_url": "http://localhost:8001/api/library/documents/5/thumbnail/",
  "uploaded_by_email": "gestionnaire@example.com",
  "created_at": "2026-08-04T09:00:00Z"
}
```

## GET `/api/library/documents/{id}/download/`

Sert le fichier lui-même, en streaming. Accès public. Prend en charge l'en-tête
`Range` (`Range: bytes=0-1023`) et répond `206 Partial Content` — nécessaire
à pdf.js côté frontend pour charger un PDF par plages d'octets, exactement
comme `app/api/file/[...id]/route.ts`. Sans en-tête `Range`, répond `200 OK`
avec le fichier entier.

En-têtes de réponse : `Content-Disposition: inline` (le navigateur affiche
plutôt que proposer un téléchargement nommé), `Accept-Ranges: bytes`,
`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.

## GET `/api/library/documents/{id}/thumbnail/?page=N`

Miniature PNG mise en cache (`media/_thumbnails/`). `page` ne s'applique
qu'aux PDF (page 1 par défaut = miniature de couverture ; les autres pages
servent à la barre latérale du lecteur). Pas de miniature pour les documents
JSON, ni si la génération échoue (dépendances manquantes, EPUB sans
couverture déclarée…) — répond alors `404 Not Found` plutôt que de renvoyer
une image cassée, comme côté frontend.
