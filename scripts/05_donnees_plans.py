"""
05_donnees_plans.py
Prépare les données des plans types (volet 3).

1. Fond de plan vectoriel (tous les bâtiments BD TOPO de la commune).
2. Terrasses de démonstration sur la place Saint-Léger, tirées des façades réelles.
   Les établissements, arrêtés et dates sont FICTIFS : ils servent à montrer la chaîne
   « saisie de l'emprise -> plan annexé à l'arrêté ».
3. Dispositif d'une manifestation fictive (fête de la musique, centre historique) :
   périmètre, voies fermées, barrages, accès secours, scènes et services.

Lancement : python-qgis-ltr.bat 05_donnees_plans.py
"""
import datetime as dt
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from osgeo import gdal, ogr
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, nearest_points

from schema import SRID

gdal.UseExceptions()
RACINE = Path(__file__).resolve().parents[1]
BRUT = RACINE / "donnees" / "brut"
TRAITE = RACINE / "donnees" / "traite"
BASE = TRAITE / "patrimoine_chambery.gpkg"
PLANS = TRAITE / "plans.gpkg"
AUJOURDHUI = dt.date.today()
MENTION = "Données fictives de démonstration"

troncons = gpd.read_file(BASE, layer="troncon_voirie")
commune = gpd.read_file(BASE, layer="quartier").dissolve()

# --------------------------------------------------------------------------
# 1. Fond de plan : tous les bâtiments de la commune
# --------------------------------------------------------------------------
print("Fond de plan")
bati = gpd.read_file(BRUT / "bdtopo_batiment.geojson").set_crs(4326, allow_override=True).to_crs(SRID)
bati.geometry = bati.geometry.force_2d()
bati = bati[bati.intersects(commune.geometry.iloc[0].buffer(300))][["cleabs", "usage_1", "geometry"]]
if PLANS.exists():
    PLANS.unlink()
bati.to_file(PLANS, layer="fond_batiment", driver="GPKG")

# --------------------------------------------------------------------------
# 2. Terrasses de la place Saint-Léger
# --------------------------------------------------------------------------
print("Terrasses")
VOIE = "73065_3440"  # Place Saint-Léger
axe = troncons[troncons["id_voie"] == VOIE].union_all()
espace_public = axe.buffer(9).difference(bati[bati.distance(axe) < 20].union_all())

candidats = []
for geom in bati[bati.distance(axe) < 9].geometry:
    for poly in getattr(geom, "geoms", [geom]):
        c = list(poly.exterior.coords)
        for a, b in zip(c[:-1], c[1:]):
            seg = LineString([a, b])
            if seg.length < 5 or seg.centroid.distance(axe) > 8:
                continue
            # Tronçon de façade centré, 8 m maximum, poussé de 2,5 m vers l'axe
            longueur = min(seg.length - 1, 8)
            milieu = seg.interpolate(0.5, normalized=True)
            u = (np.array(b) - np.array(a)) / seg.length
            n = np.array([-u[1], u[0]])
            vers_axe = np.array(nearest_points(milieu, axe)[1].coords[0]) - np.array(milieu.coords[0])
            if n @ vers_axe < 0:
                n = -n
            p0 = np.array(milieu.coords[0]) - u * longueur / 2 + n * 0.3
            p1 = p0 + u * longueur
            rect = Polygon([p0, p1, p1 + n * 2.5, p0 + n * 2.5])
            rect = rect.intersection(espace_public)
            if rect.geom_type == "Polygon" and rect.area >= 8:
                candidats.append(rect)

# Sélection sans chevauchement, les plus grandes d'abord, 1,5 m d'écart minimum
retenues = []
for r in sorted(candidats, key=lambda g: -g.area):
    if all(r.distance(o) > 1.5 for o in retenues):
        retenues.append(r)

ban = pd.read_csv(BRUT / "ban_adresses_73.csv.gz", sep=";", dtype=str,
                  usecols=["code_insee", "numero", "rep", "nom_voie", "x", "y"])
ban = ban[(ban["code_insee"] == "73065") & (ban["nom_voie"] == "Place Saint-Léger")]
ban = gpd.GeoDataFrame(ban, geometry=gpd.points_from_xy(ban["x"].astype(float), ban["y"].astype(float)),
                       crs=2154).to_crs(SRID)

ter = gpd.GeoDataFrame(geometry=retenues, crs=SRID)
ter["_ordre"] = ter.centroid.y
ter = ter.sort_values("_ordre", ascending=False).reset_index(drop=True)
n = len(ter)
ter["id_occupation"] = [f"OCC-2026-{i + 1:03d}" for i in range(n)]
ter["type_occupation"] = ["TER_FER" if i % 5 == 3 else "TER_OUV" for i in range(n)]
ter["etablissement"] = [f"Établissement fictif n° {i + 1}" for i in range(n)]
ter["adresse"] = [
    (lambda b: f"{b['numero']}{b['rep'] if isinstance(b['rep'], str) else ''} Place Saint-Léger")(
        ban.iloc[ban.distance(g).argmin()]) for g in ter.geometry]
ter["id_voie"] = VOIE
ter["surface_m2"] = ter.area.round(1)
ter["statut"] = ["INS" if i % 6 == 5 else "AUT" for i in range(n)]
ter["num_arrete"] = [f"2026-OCC-{i + 1:03d}" if s == "AUT" else None
                     for i, s in enumerate(ter["statut"])]
ter["date_debut"] = dt.date(2026, 4, 1)
ter["date_fin"] = dt.date(2026, 10, 31)
ter["source"] = MENTION
ter["date_maj"] = AUJOURDHUI
ter = ter.drop(columns="_ordre")
print(f"  {n} terrasses, surface totale {ter['surface_m2'].sum():.0f} m²")

# Écriture dans la couche occupation_domaine_public des deux bases (schéma et domaines conservés)
for base in [TRAITE / "patrimoine_chambery.gpkg", TRAITE / "patrimoine_chambery.gdb"]:
    ds = gdal.OpenEx(str(base), gdal.OF_UPDATE | gdal.OF_VECTOR)
    lyr = ds.GetLayerByName("occupation_domaine_public")
    for f in list(lyr):
        lyr.DeleteFeature(f.GetFID())
    defn = lyr.GetLayerDefn()
    for _, row in ter.iterrows():
        f = ogr.Feature(defn)
        for champ in ter.columns.drop("geometry"):
            v = row[champ]
            if v is None:
                continue
            if isinstance(v, dt.date):
                f.SetField(champ, v.year, v.month, v.day, 0, 0, 0, 0)
            else:
                f.SetField(champ, v)
        f.SetGeometry(ogr.ForceToMultiPolygon(ogr.CreateGeometryFromWkb(row.geometry.wkb)))
        lyr.CreateFeature(f)
    ds = None

# Cotes : un segment par côté de terrasse, étiqueté avec sa longueur
cotes = []
for _, t in ter.iterrows():
    c = list(t.geometry.exterior.coords)
    for a, b in zip(c[:-1], c[1:]):
        seg = LineString([a, b])
        if seg.length >= 0.8:
            cotes.append({"id_occupation": t["id_occupation"], "longueur": round(seg.length, 2),
                          "geometry": seg})
gpd.GeoDataFrame(cotes, crs=SRID).to_file(PLANS, layer="cote_terrasse", driver="GPKG")

# --------------------------------------------------------------------------
# 3. Manifestation fictive : fête de la musique dans le centre historique
# --------------------------------------------------------------------------
print("Manifestation")
voies_fete = ["73065_3440", "73065_2640", "73065_2650"]  # Saint-Léger, place et rue de la Métropole
axe_fete = troncons[troncons["id_voie"].isin(voies_fete)].union_all()
zone = axe_fete.buffer(14)
# Le périmètre affiché suit l'espace public : la zone moins les bâtiments
perimetre = zone.difference(bati[bati.intersects(zone)].union_all()).buffer(0.5).buffer(-0.5)
parties = [g for g in getattr(perimetre, "geoms", [perimetre]) if g.area > 30]
gpd.GeoDataFrame({"nom": ["Périmètre piéton de la manifestation"] * len(parties),
                  "source": MENTION}, geometry=parties, crs=SRID).to_file(
    PLANS, layer="fete_perimetre", driver="GPKG")

roulables = troncons[troncons["nature"].isin(["Route à 1 chaussée", "Route à 2 chaussées",
                                              "Rond-point", "Route empierrée"])]
fermees = roulables[roulables.intersects(zone)].copy()
fermees.geometry = fermees.intersection(zone)
fermees = fermees[fermees.length > 2]
fermees["motif"] = "Circulation interdite de 16 h à 2 h"
fermees[["cleabs", "nom", "motif", "geometry"]].to_file(PLANS, layer="fete_voie_fermee",
                                                        driver="GPKG")

# Barrages : entrées des voies roulables dans la zone, points à moins de 10 m fusionnés
entrees = roulables[roulables.intersects(zone.boundary)].intersection(zone.boundary)
entrees = entrees.explode(index_parts=False)
entrees = entrees[entrees.geom_type == "Point"]
groupes = entrees.buffer(10).union_all()
bar = gpd.GeoDataFrame(geometry=[g.centroid for g in getattr(groupes, "geoms", [groupes])],
                       crs=SRID)
bar["type"] = "Barrage véhicules (bloc béton)"
# l'accès le plus au nord sert d'entrée secours
bar.loc[bar.geometry.y.idxmax(), "type"] = "Accès secours (barrière amovible)"
bar["source"] = MENTION
bar.to_file(PLANS, layer="fete_barrage", driver="GPKG")

# Équipements de la fête, placés le long de l'axe
ligne = linemerge(axe_fete) if axe_fete.geom_type == "MultiLineString" else axe_fete
ligne = max(getattr(ligne, "geoms", [ligne]), key=lambda g: g.length)
equip = [
    (0.10, "Scène", "Scène principale"),
    (0.55, "Scène", "Scène acoustique"),
    (0.30, "Secours", "Poste de secours"),
    (0.75, "Sanitaires", "Toilettes et point d'eau"),
    (0.20, "Buvette", "Buvette associative"),
    (0.65, "Buvette", "Buvette associative"),
    (0.45, "Information", "Point information et objets trouvés"),
    (0.90, "Sanitaires", "Toilettes"),
]
pts = []
for pos, typ, lib in equip:
    p = ligne.interpolate(pos, normalized=True)
    # décalage latéral de 4 m pour laisser la voie engins libre
    q = ligne.interpolate(min(pos + 0.01, 1), normalized=True)
    u = np.array(q.coords[0]) - np.array(p.coords[0])
    u = u / (np.linalg.norm(u) or 1)
    pts.append({"type": typ, "libelle": lib,
                "geometry": Point(np.array(p.coords[0]) + np.array([-u[1], u[0]]) * 4)})
gpd.GeoDataFrame(pts, crs=SRID).assign(source=MENTION).to_file(PLANS, layer="fete_equipement",
                                                                 driver="GPKG")
gpd.GeoDataFrame({"libelle": ["Voie engins de 4 m maintenue libre"], "source": [MENTION]},
                 geometry=[ligne], crs=SRID).to_file(PLANS, layer="fete_voie_engins", driver="GPKG")
print(f"  {len(fermees)} tronçons fermés, {len(bar)} barrages, {len(pts)} équipements")
print("Données des plans écrites dans", PLANS)
