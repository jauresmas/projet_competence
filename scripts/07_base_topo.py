"""
07_base_topo.py
Reconstitue un extrait de la base topographique de la Ville (DXF, CC45) sur le
secteur de la rue Croix d'Or, selon la charte de charte_topo.py.

Faute de levé topographique ouvert, l'extrait est dérivé des données IGN et du
cadastre : bâti BD TOPO, limites parcellaires, axes de voirie, bordures reconstituées
(axe décalé de la demi-largeur de chaussée), mobilier existant simulé sur la rue.

Sortie : donnees/topo/base_topo_secteur_croix_d_or.dxf
Lancement : python-qgis-ltr.bat 07_base_topo.py
"""
import math
from pathlib import Path

import ezdxf
import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from shapely.ops import linemerge

from charte_topo import SRID_VILLE, creer_calques_et_blocs

RACINE = Path(__file__).resolve().parents[1]
BRUT = RACINE / "donnees" / "brut"
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
TOPO = RACINE / "donnees" / "topo"
TOPO.mkdir(exist_ok=True)
CIBLE = TOPO / "base_topo_secteur_croix_d_or.dxf"

VOIE_CHANTIER = "73065_1000"  # Rue Croix d'Or

troncons = gpd.read_file(BASE, layer="troncon_voirie")
axe_chantier = troncons[troncons["id_voie"] == VOIE_CHANTIER].union_all()
secteur = box(*axe_chantier.buffer(220).bounds)

bati = gpd.read_file(BRUT / "bdtopo_batiment.geojson").set_crs(4326, allow_override=True)
bati = bati.to_crs(SRID_VILLE)
bati.geometry = bati.geometry.force_2d()
bati = bati[bati.intersects(secteur)]
bati_union = bati.union_all()

parcelles = gpd.read_file("/vsigzip/" + str(BRUT / "cadastre_parcelles_73065.json.gz")).to_crs(SRID_VILLE)
parcelles = parcelles[parcelles.intersects(secteur)]

routes = troncons[troncons.intersects(secteur) & troncons["nature"].isin(
    ["Route à 1 chaussée", "Route à 2 chaussées", "Rond-point", "Route empierrée"])]

doc = ezdxf.new("R2018", setup=True)
doc.header["$INSUNITS"] = 6  # mètres
doc.header["$PROJECTNAME"] = "Base topographique Ville de Chambery - RGF93 CC45"
creer_calques_et_blocs(doc)
msp = doc.modelspace()


def polyligne(geom, calque, ferme=False):
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty:
            continue
        if g.geom_type == "Polygon":
            msp.add_lwpolyline(list(g.exterior.coords)[:-1], close=True, dxfattribs={"layer": calque})
            for trou in g.interiors:
                msp.add_lwpolyline(list(trou.coords)[:-1], close=True, dxfattribs={"layer": calque})
        elif g.geom_type == "LineString" and g.length > 0.2:
            msp.add_lwpolyline(list(g.coords), close=ferme, dxfattribs={"layer": calque})


def angle_lisible(ligne):
    a, b = ligne.interpolate(0.45, True), ligne.interpolate(0.55, True)
    ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
    return ang + 180 if ang > 90 else ang - 180 if ang < -90 else ang


# Bâti et cadastre
for g in bati.geometry:
    polyligne(g.intersection(secteur), "BAT_BATI")
for g in parcelles.geometry:
    polyligne(g.boundary.intersection(secteur), "CAD_LIMITE")

# Axes, bordures reconstituées, noms de voies
for _, t in routes.iterrows():
    axe = t.geometry.intersection(secteur)
    for ligne in getattr(axe, "geoms", [axe]):
        if ligne.geom_type != "LineString" or ligne.length < 1:
            continue
        polyligne(ligne, "VOI_AXE")
        demi = (t["largeur_m"] if pd.notna(t["largeur_m"]) else 4.0) / 2
        for cote in (demi, -demi):
            bord = ligne.offset_curve(cote)
            polyligne(bord.difference(bati_union.buffer(0.3)), "VOI_BORDURE")
        if t["nom"] and ligne.length > 40:
            m = ligne.interpolate(0.5, True)
            msp.add_text(t["nom"], height=1.6, rotation=angle_lisible(ligne),
                         dxfattribs={"layer": "TXT_VOIE"}).set_placement(
                (m.x, m.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

# Numéros d'adresse (BAN)
ban = pd.read_csv(BRUT / "ban_adresses_73.csv.gz", sep=";", dtype=str,
                  usecols=["code_insee", "numero", "rep", "x", "y"])
ban = ban[ban["code_insee"] == "73065"]
ban = gpd.GeoDataFrame(ban, geometry=gpd.points_from_xy(ban["x"].astype(float), ban["y"].astype(float)),
                       crs=2154).to_crs(SRID_VILLE)
for _, a in ban[ban.within(secteur)].iterrows():
    msp.add_text(a["numero"] + (a["rep"] if isinstance(a["rep"], str) else ""), height=0.8,
                 dxfattribs={"layer": "TXT_ADRESSE"}).set_placement((a.geometry.x, a.geometry.y))

# Mobilier existant simulé sur la rue Croix d'Or (sera remplacé par le récolement)
fusion = linemerge(axe_chantier) if axe_chantier.geom_type == "MultiLineString" else axe_chantier
ligne = max(getattr(fusion, "geoms", [fusion]), key=lambda g: g.length)
for i, d in enumerate(range(10, int(ligne.length), 30)):
    p = ligne.offset_curve(2.3).interpolate(d)
    msp.add_blockref("CANDELABRE", (p.x, p.y), dxfattribs={"layer": "ECL_CANDELABRE"}).add_auto_attribs(
        {"NUMERO": f"CD-A{i + 1:02d}", "HAUTEUR": "4"})
for d in range(20, int(ligne.length), 45):
    p = ligne.offset_curve(-1.9).interpolate(d)
    msp.add_blockref("AVALOIR", (p.x, p.y), dxfattribs={"layer": "ASS_AVALOIR"})

doc.set_modelspace_vport(height=ligne.length * 1.6, center=(ligne.centroid.x, ligne.centroid.y))
doc.saveas(CIBLE)
compte = pd.Series([e.dxf.layer for e in msp]).value_counts()
print(f"Base topo écrite : {CIBLE.name}")
print(compte.to_string())
