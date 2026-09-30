"""
12_tableau_de_bord.py
Génère la page de présentation et le tableau de bord HTML autonome du SIG Patrimoine :

  - présentation des quatre volets, avec accès direct à la carte ;
  - indicateurs ;
  - carte interactive (Leaflet, fond Plan IGN) : bâtiments filtrables, et couches activables
    (parcelles communales, voirie par domanialité, terrasses, fête, chantier de récolement) ;
  - répartition par type et par quartier, liste de travail des données à compléter ;
  - documents du projet (plans, rapport de récolement, open data, dictionnaire, dépôt).

Sortie : sorties/tableau_de_bord.html (à côté du dossier fiches/ et des plans PDF)
Lancement : python-qgis-ltr.bat 12_tableau_de_bord.py
"""
import datetime as dt
import json
from pathlib import Path

import ezdxf
import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from schema import DOMAINES

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
PLANS = RACINE / "donnees" / "traite" / "plans.gpkg"
TOPO_MAJ = RACINE / "donnees" / "topo" / "base_topo_secteur_croix_d_or_maj.dxf"
SORTIES = RACINE / "sorties"
FICHES = SORTIES / "fiches"
DEPOT = "https://github.com/jauresmas/projet_competence"

COULEURS = {"ADM": "#1f4e79", "ENS": "#e08a00", "SPO": "#2e8b57", "CUL": "#8e44ad",
            "REL": "#7f6000", "SAN": "#c0392b", "TEC": "#5d6d7e", "COM": "#d35400",
            "LOG": "#a9a9a9", "ANX": "#c8ccd0", "AQU": "#e6b800"}
COULEURS_DOM = {"COM": "#c82d23", "DEP": "#e68c14", "NAT": "#6c3483", "AUT": "#5a5a5a",
                "PRI": "#969696", "NR": "#2882c8"}


def geojson(gdf, champs, tolerance=0.2, decimales=6):
    """GeoDataFrame (CC45) -> GeoJSON WGS84 allégé : simplification et coordonnées arrondies."""
    g = gdf[champs + ["geometry"]].copy()
    if tolerance:
        g.geometry = g.geometry.simplify(tolerance)
    g = g.to_crs(4326)
    d = json.loads(g.to_json(na="null", drop_id=True))

    def arrondir(c):
        return [round(c[0], decimales), round(c[1], decimales)] if isinstance(c[0], float) \
            else [arrondir(x) for x in c]
    for f in d["features"]:
        f["geometry"]["coordinates"] = arrondir(f["geometry"]["coordinates"])
    return d


bat = gpd.read_file(BASE, layer="batiment_communal")
par = gpd.read_file(BASE, layer="parcelle_communale")
loc = gpd.read_file(BASE, layer="local_communal")
qua = gpd.read_file(BASE, layer="quartier")
tr = gpd.read_file(BASE, layer="troncon_voirie")
ter = gpd.read_file(BASE, layer="occupation_domaine_public")
fete = gpd.read_file(PLANS, layer="fete_perimetre")
noms_quartiers = dict(zip(qua["code"], qua["nom"].str.replace("Chambéry ", "")))

routes = tr[tr["nature"].isin(["Route à 1 chaussée", "Route à 2 chaussées", "Rond-point",
                               "Route empierrée", "Bretelle", "Type autoroutier"])].copy()
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

# Bâtiments
bat["fiche"] = bat["id_bien"].map(lambda i: f"fiches/{i}.pdf" if (FICHES / f"{i}.pdf").exists() else "")
bat["quartier_nom"] = bat["quartier"].map(noms_quartiers)
bat["type_libelle"] = bat["type_bien"].map(DOMAINES["dom_type_bien"][1])
batiments = geojson(bat, ["id_bien", "nom", "type_bien", "type_libelle", "quartier", "quartier_nom",
                          "adresse", "emprise_m2", "nb_etages", "hauteur_m", "nb_locaux", "fiche"])

# Couches complémentaires
par["surface"] = par["contenance_m2"]
parcelles = geojson(par, ["idu", "adresse", "surface", "batie"], tolerance=1, decimales=5)
# Tronçons fusionnés par voie et domanialité : quelques centaines d'objets au lieu de plusieurs milliers
fusion = routes.assign(nom=routes["nom"].fillna("Voie sans nom")).dissolve(
    by=["nom", "domanialite"], as_index=False).assign(geometry=lambda g: g.line_merge())
fusion["dom_libelle"] = fusion["domanialite"].map(DOMAINES["dom_domanialite"][1])
fusion["longueur_m"] = fusion.length.round()
voirie = geojson(fusion, ["nom", "domanialite", "dom_libelle", "longueur_m"], tolerance=1, decimales=5)
ter["type_libelle"] = ter["type_occupation"].map(DOMAINES["dom_type_occupation"][1])
ter["statut_libelle"] = ter["statut"].map(DOMAINES["dom_statut_autorisation"][1])
terrasses = geojson(ter, ["id_occupation", "etablissement", "adresse", "type_libelle", "surface_m2",
                          "statut_libelle", "num_arrete"], tolerance=0)
fete_geo = geojson(fete, ["nom"], tolerance=0.2)

# Chantier de récolement : emprise et objets intégrés, lus dans la base topo mise à jour (CC45)
doc = ezdxf.readfile(TOPO_MAJ)
msp = doc.modelspace()
emprises = [Polygon([p[:2] for p in e.get_points()]) for e in msp.query('LWPOLYLINE[layer=="REC_EMPRISE"]')]
emprise = emprises[0]
LIBELLES = {"ECL_CANDELABRE": "Candélabre", "VEG_ARBRE": "Arbre", "ASS_AVALOIR": "Avaloir"}
objets = []
for e in msp.query("INSERT"):
    p = Point(e.dxf.insert.vec2)
    if e.dxf.layer in LIBELLES and emprise.contains(p):
        attrs = {a.dxf.tag: a.dxf.text for a in e.attribs}
        detail = attrs.get("NUMERO") or attrs.get("ESSENCE") or ""
        objets.append({"objet": LIBELLES[e.dxf.layer], "detail": detail, "geometry": p})
for e in msp.query('LWPOLYLINE[layer=="VOI_BORDURE"]'):
    ligne = LineString([p[:2] for p in e.get_points()])
    if emprise.buffer(0.5).contains(ligne):
        objets.append({"objet": "Bordure", "detail": f"{ligne.length:.1f} m", "geometry": ligne})
chantier = gpd.GeoDataFrame(objets, crs=3945)
chantier_geo = geojson(chantier, ["objet", "detail"], tolerance=0)
emprise_geo = geojson(gpd.GeoDataFrame({"nom": ["Emprise du chantier (récolement fictif)"]},
                                       geometry=[emprise], crs=3945), ["nom"], tolerance=0)
quartiers_geo = geojson(qua, ["code", "nom"], tolerance=1, decimales=5)

travail = []
for code, g in bat.groupby("quartier"):
    travail.append({"quartier": noms_quartiers.get(code, code), "total": len(g),
                    "sans_nom": int(g["nom"].isna().sum()),
                    "a_qualifier": int((g["type_bien"] == "AQU").sum()),
                    "sans_niveaux": int(g["nb_etages"].isna().sum()),
                    "etat_nr": int((g["etat"] == "NR").sum())})
travail.sort(key=lambda r: -r["total"])


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


remplacements = {
    "__BATIMENTS__": js(batiments), "__QUARTIERS__": js(quartiers_geo), "__PARCELLES__": js(parcelles),
    "__VOIRIE__": js(voirie), "__TERRASSES__": js(terrasses), "__FETE__": js(fete_geo),
    "__CHANTIER__": js(chantier_geo), "__EMPRISE__": js(emprise_geo),
    "__INDICATEURS__": js(indicateurs), "__TRAVAIL__": js(travail),
    "__TYPES__": js(DOMAINES["dom_type_bien"][1]), "__COULEURS__": js(COULEURS),
    "__COULEURS_DOM__": js(COULEURS_DOM), "__DOMANIALITES__": js(DOMAINES["dom_domanialite"][1]),
    "__NB_TERRASSES__": str(len(ter)), "__NB_FICHES__": str(len(list(FICHES.glob("*.pdf")))),
    "__DEPOT__": DEPOT, "__DATE__": dt.date.today().strftime("%d/%m/%Y"),
}
html = Path(__file__).with_name("tableau_de_bord_modele.html").read_text(encoding="utf-8")
for cle, valeur in remplacements.items():
    html = html.replace(cle, valeur)
cible = SORTIES / "tableau_de_bord.html"
cible.write_text(html, encoding="utf-8")
print(f"Tableau de bord : {cible} ({cible.stat().st_size / 1024:.0f} Ko)")
print(indicateurs, f"{len(objets)} objets de chantier")
