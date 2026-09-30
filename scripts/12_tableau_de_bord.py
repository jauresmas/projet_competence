"""
12_tableau_de_bord.py
Génère un tableau de bord HTML autonome sur le patrimoine bâti : indicateurs,
carte interactive (Leaflet, fond Plan IGN), répartition par type et par quartier,
liste de travail des données à compléter, lien vers la fiche PDF de chaque bâtiment.

Sortie : sorties/tableau_de_bord.html (à ouvrir dans un navigateur, à côté du dossier fiches/)
Lancement : python-qgis-ltr.bat 12_tableau_de_bord.py
"""
import datetime as dt
import json
from pathlib import Path

import geopandas as gpd

from schema import DOMAINES

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
SORTIES = RACINE / "sorties"
FICHES = SORTIES / "fiches"

COULEURS = {"ADM": "#1f4e79", "ENS": "#e08a00", "SPO": "#2e8b57", "CUL": "#8e44ad",
            "REL": "#7f6000", "SAN": "#c0392b", "TEC": "#5d6d7e", "COM": "#d35400",
            "LOG": "#a9a9a9", "ANX": "#c8ccd0", "AQU": "#e6b800"}

bat = gpd.read_file(BASE, layer="batiment_communal")
par = gpd.read_file(BASE, layer="parcelle_communale")
loc = gpd.read_file(BASE, layer="local_communal")
qua = gpd.read_file(BASE, layer="quartier")
tr = gpd.read_file(BASE, layer="troncon_voirie")
noms_quartiers = dict(zip(qua["code"], qua["nom"].str.replace("Chambéry ", "")))

routes = tr[tr["nature"].isin(["Route à 1 chaussée", "Route à 2 chaussées", "Rond-point", "Route empierrée"])]
indicateurs = {
    "batiments": len(bat),
    "emprise_m2": round(bat["emprise_m2"].sum()),
    "locaux": len(loc),
    "parcelles": len(par),
    "surface_ha": round(par["contenance_m2"].sum() / 10000, 1),
    # découpé aux limites des quartiers, comme le plan de voirie du volet 3
    "voirie_km": round(routes.loc[routes["domanialite"] == "COM"].intersection(qua.union_all())
                       .length.sum() / 1000, 1),
}

# Bâtiments en WGS84, géométrie simplifiée (20 cm) pour alléger la page
geo = bat.copy()
geo.geometry = geo.geometry.simplify(0.2)
geo = geo.to_crs(4326)
geo["fiche"] = geo["id_bien"].map(lambda i: f"fiches/{i}.pdf" if (FICHES / f"{i}.pdf").exists() else "")
geo["quartier_nom"] = geo["quartier"].map(noms_quartiers)
geo["type_libelle"] = geo["type_bien"].map(DOMAINES["dom_type_bien"][1])
champs = ["id_bien", "nom", "type_bien", "type_libelle", "quartier", "quartier_nom", "adresse",
          "emprise_m2", "nb_etages", "hauteur_m", "nb_locaux", "fiche", "geometry"]
donnees = json.loads(geo[champs].to_json(na="null", drop_id=True))
for f in donnees["features"]:  # 6 décimales : précision décimétrique, fichier plus léger
    g = f["geometry"]
    arrondir = lambda anneau: [[round(x, 6), round(y, 6)] for x, y in anneau]  # noqa: E731
    if g["type"] == "Polygon":
        g["coordinates"] = [arrondir(a) for a in g["coordinates"]]
    else:
        g["coordinates"] = [[arrondir(a) for a in p] for p in g["coordinates"]]
quartiers_geo = json.loads(qua[["code", "nom", "geometry"]].to_crs(4326).to_json(drop_id=True))

travail = []
for code, g in bat.groupby("quartier"):
    travail.append({"quartier": noms_quartiers.get(code, code), "total": len(g),
                    "sans_nom": int(g["nom"].isna().sum()),
                    "a_qualifier": int((g["type_bien"] == "AQU").sum()),
                    "sans_niveaux": int(g["nb_etages"].isna().sum()),
                    "etat_nr": int((g["etat"] == "NR").sum())})
travail.sort(key=lambda r: -r["total"])

html = (Path(__file__).with_name("tableau_de_bord_modele.html").read_text(encoding="utf-8")
        .replace("__BATIMENTS__", json.dumps(donnees, ensure_ascii=False, separators=(",", ":")))
        .replace("__QUARTIERS__", json.dumps(quartiers_geo, ensure_ascii=False, separators=(",", ":")))
        .replace("__INDICATEURS__", json.dumps(indicateurs))
        .replace("__TRAVAIL__", json.dumps(travail, ensure_ascii=False))
        .replace("__TYPES__", json.dumps(DOMAINES["dom_type_bien"][1], ensure_ascii=False))
        .replace("__COULEURS__", json.dumps(COULEURS))
        .replace("__DATE__", dt.date.today().strftime("%d/%m/%Y")))
cible = SORTIES / "tableau_de_bord.html"
cible.write_text(html, encoding="utf-8")
print(f"Tableau de bord : {cible} ({cible.stat().st_size / 1024:.0f} Ko)")
print(indicateurs)
