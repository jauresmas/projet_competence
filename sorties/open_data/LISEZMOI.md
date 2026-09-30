# Patrimoine bâti communal et référentiel des voies de Chambéry

Jeu de données publié le 2026-09-30 sous Licence Ouverte Etalab 2.0.

| Fichier | Contenu |
|---|---|
| `batiments_communaux.csv` / `.geojson` | Bâtiments situés sur des parcelles communales |
| `parcelles_communales.csv` / `.geojson` | Parcelles dont la commune est propriétaire |
| `referentiel_voies.csv` / `.geojson` | Voies nommées, identifiant BAN |
| `datapackage.json` | Description et schéma des fichiers (format Frictionless Data) |

Les CSV sont en UTF-8, séparateur virgule, avec la position (WGS84) d'un point intérieur à
chaque objet. Les codes (type de bien...) sont accompagnés de leur libellé (colonnes `_libelle`).

## Limites

- La propriété communale provient du fichier fiscal DGFiP : les biens loués ou mis à disposition
  n'y figurent pas.
- Les champs de gestion interne (état, service affectataire) ne sont pas diffusés.
- Données de démonstration produites dans le cadre d'un portfolio : elles n'engagent pas la Ville.
