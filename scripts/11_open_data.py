"""
11_open_data.py
Prépare le jeu de données ouvert « Patrimoine bâti et voies de la Ville de Chambéry » :

  - GeoJSON (WGS84, RFC 7946) et CSV (avec longitude / latitude) pour chaque couche publiée ;
  - libellés des codes de domaine ajoutés en clair (colonnes *_libelle) ;
  - champs de gestion interne retirés (état, service affectataire) ;
  - descripteur datapackage.json (Frictionless Data) généré depuis schema.py ;
  - LISEZMOI.md (licence, sources, limites).

Sortie : sorties/open_data/
Lancement : python-qgis-ltr.bat 11_open_data.py
"""
import datetime as dt
import json
from pathlib import Path

import geopandas as gpd

from schema import COUCHES, DOMAINES

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
OD = RACINE / "sorties" / "open_data"
OD.mkdir(parents=True, exist_ok=True)
AUJOURDHUI = dt.date.today().isoformat()

# Couches publiées et champs internes non diffusés
PUBLICATION = {
    "batiment_communal": ("batiments_communaux", ["etat", "affectataire", "source", "date_maj"]),
    "parcelle_communale": ("parcelles_communales", ["source", "date_maj"]),
    "voie": ("referentiel_voies", ["source", "date_maj"]),
}
TYPES_FRICTIONLESS = {"str": "string", "int": "integer", "real": "number", "date": "date"}

ressources = []
for couche, (nom, retires) in PUBLICATION.items():
    gdf = gpd.read_file(BASE, layer=couche).drop(columns=retires, errors="ignore")
    champs = [c for c in COUCHES[couche]["champs"] if c[0] not in retires]
    for champ, _, type_, *_ in champs:  # entiers avec valeurs vides : éviter « 3.0 » dans le CSV
        if type_ == "int":
            gdf[champ] = gdf[champ].astype("Int64")

    # Libellés en clair des codes de domaine
    for champ, _, _, _, domaine, _ in champs:
        if domaine:
            gdf[f"{champ}_libelle"] = gdf[champ].map(DOMAINES[domaine][1])

    wgs = gdf.to_crs(4326)
    wgs.to_file(OD / f"{nom}.geojson", driver="GeoJSON", COORDINATE_PRECISION=7, RFC7946="YES")
    pts = gdf.representative_point().to_crs(4326)
    tab = gdf.drop(columns="geometry").assign(longitude=pts.x.round(7), latitude=pts.y.round(7))
    tab.to_csv(OD / f"{nom}.csv", index=False, encoding="utf-8")

    # Schéma Table Schema (Frictionless)
    schema_champs = []
    for champ, alias, type_, _, domaine, desc in champs:
        f = {"name": champ, "title": alias, "type": TYPES_FRICTIONLESS[type_], "description": desc}
        if domaine:
            f["constraints"] = {"enum": list(DOMAINES[domaine][1])}
        schema_champs.append(f)
        if domaine:
            schema_champs.append({"name": f"{champ}_libelle", "title": f"{alias} (libellé)",
                                  "type": "string"})
    schema_champs += [{"name": "longitude", "type": "number", "description": "WGS84, point intérieur"},
                      {"name": "latitude", "type": "number", "description": "WGS84, point intérieur"}]
    ressources.append({
        "name": nom.replace("_", "-"),
        "title": COUCHES[couche]["alias"],
        "description": COUCHES[couche]["description"],
        "path": f"{nom}.csv",
        "format": "csv",
        "mediatype": "text/csv",
        "encoding": "utf-8",
        "schema": {"fields": schema_champs, "primaryKey": champs[0][0]},
    })
    ressources.append({
        "name": f"{nom.replace('_', '-')}-geo",
        "title": f"{COUCHES[couche]['alias']} (géométries)",
        "path": f"{nom}.geojson",
        "format": "geojson",
        "mediatype": "application/geo+json",
    })
    print(f"{nom} : {len(gdf)} objets")

paquet = {
    "name": "patrimoine-bati-voies-chambery",
    "title": "Patrimoine bâti communal et référentiel des voies de Chambéry",
    "description": "Bâtiments et parcelles dont la commune est propriétaire, et voies nommées "
                   "de la commune. Jeu de démonstration construit à partir de données ouvertes.",
    "version": "1.0.0",
    "created": AUJOURDHUI,
    "licenses": [{"name": "etalab-2.0", "title": "Licence Ouverte / Open Licence version 2.0",
                  "path": "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"}],
    "sources": [
        {"title": "BD TOPO® - IGN", "path": "https://geoservices.ign.fr/bdtopo"},
        {"title": "Plan cadastral informatisé - Etalab", "path": "https://cadastre.data.gouv.fr"},
        {"title": "Base Adresse Nationale", "path": "https://adresse.data.gouv.fr"},
        {"title": "Fichiers des locaux et parcelles des personnes morales - DGFiP",
         "path": "https://www.data.gouv.fr/fr/datasets/605d268f4661cf23272817c3/"},
    ],
    "keywords": ["patrimoine", "bâtiments publics", "voirie", "Chambéry", "SIG"],
    "spatial": {"crs": "EPSG:4326", "commune_insee": "73065"},
    "resources": ressources,
}
(OD / "datapackage.json").write_text(json.dumps(paquet, ensure_ascii=False, indent=2), encoding="utf-8")

(OD / "LISEZMOI.md").write_text(f"""# Patrimoine bâti communal et référentiel des voies de Chambéry

Jeu de données publié le {AUJOURDHUI} sous Licence Ouverte Etalab 2.0.

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
""", encoding="utf-8")
print("Jeu open data écrit dans", OD)
