"""
03_controles_dictionnaire.py
1. Contrôles qualité de la base patrimoine (unicité, complétude, topologie simple,
   intégrité référentielle, conformité aux domaines).
2. Génération du dictionnaire de données à partir de schema.py.

Sorties : docs/controle_qualite.md, docs/dictionnaire_donnees.md
Lancement : python-qgis-ltr.bat 03_controles_dictionnaire.py
"""
import datetime as dt
from pathlib import Path

import geopandas as gpd
import pandas as pd

from schema import COUCHES, DOMAINES, SRID

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
DOCS = RACINE / "docs"
DOCS.mkdir(exist_ok=True)

couches = {nom: gpd.read_file(BASE, layer=nom) for nom in COUCHES}
resultats = []  # (couche, contrôle, nb anomalies, détail)


def controle(couche, libelle, masque, colonne_id):
    anomalies = couches[couche][masque]
    exemples = ", ".join(anomalies[colonne_id].astype(str).head(5))
    resultats.append((couche, libelle, len(anomalies), exemples))


bat = couches["batiment_communal"]
loc = couches["local_communal"]
par = couches["parcelle_communale"]
tr = couches["troncon_voirie"]
voie = couches["voie"]

# Unicité des identifiants
controle("batiment_communal", "Identifiant id_bien en double", bat["id_bien"].duplicated(keep=False), "id_bien")
controle("local_communal", "Identifiant id_local en double", loc["id_local"].duplicated(keep=False), "id_local")
controle("parcelle_communale", "Parcelle idu en double", par["idu"].duplicated(keep=False), "idu")
controle("voie", "Identifiant de voie en double", voie["id_voie"].duplicated(keep=False), "id_voie")

# Complétude
controle("batiment_communal", "Bâtiment sans adresse", bat["adresse"].isna(), "id_bien")
controle("batiment_communal", "Bâtiment hors quartier", bat["quartier"] == "NC", "id_bien")
controle("batiment_communal", "Type de bien à qualifier", bat["type_bien"] == "AQU", "id_bien")
controle("batiment_communal", "Bâtiment sans nom", bat["nom"].isna(), "id_bien")

# Géométrie
controle("batiment_communal", "Géométrie invalide", ~bat.is_valid, "id_bien")
controle("parcelle_communale", "Géométrie invalide", ~par.is_valid, "idu")

# Intégrité référentielle
controle("local_communal", "Local sans bâtiment de rattachement", loc["id_bien"].isna(), "id_local")
controle("local_communal", "Local lié à un id_bien inexistant",
         loc["id_bien"].notna() & ~loc["id_bien"].isin(bat["id_bien"]), "id_local")
controle("batiment_communal", "Parcelle d'accueil absente de parcelle_communale",
         ~bat["idu_parcelle"].isin(par["idu"]), "id_bien")
controle("troncon_voirie", "Tronçon routier sans voie nommée",
         tr["id_voie"].isna() & tr["nature"].str.startswith("Route"), "cleabs")
controle("troncon_voirie", "Tronçon lié à une voie absente du référentiel",
         tr["id_voie"].notna() & ~tr["id_voie"].isin(voie["id_voie"]), "cleabs")

# Conformité aux domaines
for nom, spec in COUCHES.items():
    for champ, _, _, _, domaine, _ in spec["champs"]:
        if domaine:
            s = couches[nom][champ]
            codes = DOMAINES[domaine][1]
            colonne_id = spec["champs"][0][0]
            controle(nom, f"Valeur hors domaine ({champ})", s.notna() & ~s.isin(codes), colonne_id)

# Chevauchement entre bâtiments (tolérance 1 m²)
j = gpd.overlay(bat[["id_bien", "geometry"]], bat[["id_bien", "geometry"]], how="intersection",
                keep_geom_type=True)
j = j[(j["id_bien_1"] < j["id_bien_2"]) & (j.area > 1)]
resultats.append(("batiment_communal", "Chevauchement entre bâtiments (> 1 m²)", len(j),
                  ", ".join((j["id_bien_1"] + "/" + j["id_bien_2"]).head(5))))

# --------------------------------------------------------------------------
# Rapport de contrôle
# --------------------------------------------------------------------------
df = pd.DataFrame(resultats, columns=["couche", "controle", "anomalies", "exemples"])
lignes = [
    "# Contrôle qualité de la base patrimoine",
    "",
    f"Base contrôlée : `{BASE.name}`, le {dt.date.today():%d/%m/%Y}.",
    "",
    "| Couche | Objets |",
    "|---|---:|",
]
lignes += [f"| {n} | {len(g)} |" for n, g in couches.items()]
lignes += ["", "| Couche | Contrôle | Anomalies | Exemples |", "|---|---|---:|---|"]
for r in df.itertuples():
    etat = "OK" if r.anomalies == 0 else str(r.anomalies)
    lignes.append(f"| {r.couche} | {r.controle} | {etat} | {r.exemples} |")
lignes += [
    "",
    "Les anomalies de complétude (nom, type à qualifier) ne sont pas des erreurs :",
    "elles forment la liste de travail à traiter avec les services et lors des visites.",
]
(DOCS / "controle_qualite.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------
# Dictionnaire de données
# --------------------------------------------------------------------------
TYPES = {"str": "Texte", "int": "Entier", "real": "Réel", "date": "Date"}
d = [
    "# Dictionnaire de données du SIG Patrimoine de Chambéry",
    "",
    f"Système de coordonnées : RGF93 / CC45 (EPSG:{SRID}), celui des données de la Ville.",
    "Formats livrés : géodatabase fichier (ArcGIS Pro) et GeoPackage (QGIS), générés par le même script.",
    "",
    "## Classes d'entités",
    "",
]
for nom, spec in COUCHES.items():
    d += [f"### {spec['alias']} (`{nom}`)", "",
          f"{spec['description']} Géométrie : {spec['geom'] or 'aucune (table)'}. "
          f"Objets : {len(couches[nom])}.", "",
          "| Champ | Alias | Type | Domaine | Description |", "|---|---|---|---|---|"]
    for champ, alias, type_, largeur, domaine, desc in spec["champs"]:
        t = TYPES[type_] + (f" ({largeur})" if largeur else "")
        d.append(f"| `{champ}` | {alias} | {t} | {domaine or ''} | {desc} |")
    d.append("")
d += ["## Domaines de valeurs", ""]
for nom, (desc, valeurs) in DOMAINES.items():
    d += [f"### `{nom}` : {desc}", "", "| Code | Libellé |", "|---|---|"]
    d += [f"| {k} | {v} |" for k, v in valeurs.items()]
    d.append("")
d += [
    "## Relations",
    "",
    "- `rel_batiment_locaux` : un bâtiment communal (`id_bien`) contient 0 à n locaux "
    "(`local_communal.id_bien`). Classe de relations dans la géodatabase, relation de projet dans QGIS.",
    "- `troncon_voirie.id_voie` renvoie à `voie.id_voie` (identifiant BAN de la voie).",
    "",
]
(DOCS / "dictionnaire_donnees.md").write_text("\n".join(d), encoding="utf-8")

print(df.to_string(index=False))
