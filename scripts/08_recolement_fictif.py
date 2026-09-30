"""
08_recolement_fictif.py
Simule le plan de récolement livré par un géomètre après le réaménagement
(FICTIF) de la rue Croix d'Or : nouvelles bordures, candélabres, arbres, avaloirs.

Le fichier reproduit volontairement les écarts rencontrés en pratique :
  - livré en Lambert 93 (EPSG:2154) et non dans le système de la Ville (CC45) ;
  - calques et blocs nommés selon la nomenclature du prestataire ;
  - objets posés sur le calque 0 et sur un calque inconnu ;
  - un candélabre en double, un candélabre sans hauteur ;
  - un arbre saisi avec une coordonnée erronée (hors emprise du chantier) ;
  - habillage (cotations, cartouche) mélangé aux objets.

Sortie : donnees/topo/recolement_croix_d_or_geometre.dxf
Lancement : python-qgis-ltr.bat 08_recolement_fictif.py
"""
from pathlib import Path

import ezdxf
import geopandas as gpd
from pyproj import Transformer
from shapely.ops import linemerge

from charte_topo import SRID_VILLE

RACINE = Path(__file__).resolve().parents[1]
BRUT = RACINE / "donnees" / "brut"
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
CIBLE = RACINE / "donnees" / "topo" / "recolement_croix_d_or_geometre.dxf"

vers_l93 = Transformer.from_crs(SRID_VILLE, 2154, always_xy=True)


def l93(x, y):
    return vers_l93.transform(x, y)


troncons = gpd.read_file(BASE, layer="troncon_voirie")
axe = troncons[troncons["id_voie"] == "73065_1000"].union_all()
fusion = linemerge(axe) if axe.geom_type == "MultiLineString" else axe
ligne = max(getattr(fusion, "geoms", [fusion]), key=lambda g: g.length)

bati = gpd.read_file(BRUT / "bdtopo_batiment.geojson").set_crs(4326, allow_override=True)
bati = bati.to_crs(SRID_VILLE)
bati.geometry = bati.geometry.force_2d()
bati = bati[bati.intersects(ligne.buffer(40))].union_all()
libre = ligne.buffer(12).difference(bati.buffer(0.8))  # espace où poser le mobilier

doc = ezdxf.new("R2013")
doc.header["$INSUNITS"] = 6
for nom, couleur in [("BORDURE", 7), ("CANDELABRE", 30), ("ARBRES", 82), ("AVALOIRS", 150),
                     ("EMPRISE_CHANTIER", 6), ("COTATION", 4), ("CARTOUCHE", 7),
                     ("MOBILIER_DIVERS", 40)]:
    doc.layers.add(nom, color=couleur)
b = doc.blocks.new("LAMP")
b.add_circle((0, 0), 0.3)
b.add_attdef("NUM", (0.4, 0), dxfattribs={"height": 0.25})
b.add_attdef("HT", (0.4, -0.35), dxfattribs={"height": 0.2})
b = doc.blocks.new("TREE")
b.add_circle((0, 0), 1.2)
b.add_attdef("ESS", (1.3, 0), dxfattribs={"height": 0.25})
b.add_attdef("CIRC", (1.3, -0.35), dxfattribs={"height": 0.2})
b = doc.blocks.new("AVAL")
b.add_lwpolyline([(-0.3, -0.2), (0.3, -0.2), (0.3, 0.2), (-0.3, 0.2)], close=True)
msp = doc.modelspace()
Z = 270.0  # altitude NGF des points levés

# Emprise du chantier
emprise = ligne.buffer(9, cap_style="flat")
msp.add_lwpolyline([l93(*c) for c in list(emprise.exterior.coords)[:-1]], close=True,
                   dxfattribs={"layer": "EMPRISE_CHANTIER"})

# Nouvelles bordures : chaussée recalibrée à 5,20 m
segments = []
for cote in (2.6, -2.6):
    bord = ligne.offset_curve(cote).difference(bati.buffer(0.3))
    segments += [g for g in getattr(bord, "geoms", [bord]) if g.length > 1]
for i, s in enumerate(segments):
    calque = "0" if i in (1, 4) else "BORDURE"  # anomalie : deux bordures sur le calque 0
    msp.add_lwpolyline([l93(*c) for c in s.coords], dxfattribs={"layer": calque})


def poser(bloc, calque, d, decalage, attributs):
    p = ligne.offset_curve(decalage).interpolate(d)
    if not libre.contains(p):
        return None
    x, y = l93(p.x, p.y)
    ref = msp.add_blockref(bloc, (x, y, Z), dxfattribs={"layer": calque})
    ref.add_auto_attribs(attributs)
    return ref


# Candélabres tous les 20 m côté gauche
n = 0
for d in range(8, int(ligne.length), 20):
    n += 1
    ht = "" if n == 3 else "6"  # anomalie : hauteur manquante
    ref = poser("LAMP", "CANDELABRE", d, 3.0, {"NUM": f"CD-N{n:02d}", "HT": ht})
    if n == 1 and ref is not None:  # anomalie : doublon exact
        msp.add_blockref("LAMP", ref.dxf.insert, dxfattribs={"layer": "CANDELABRE"}).add_auto_attribs(
            {"NUM": "CD-N01", "HT": "6"})

# Arbres tous les 16 m côté droit
essences = ["Tilia cordata", "Acer campestre", "Carpinus betulus"]
arbres = [poser("TREE", "ARBRES", d, -3.8, {"ESS": essences[i % 3], "CIRC": "20"})
          for i, d in enumerate(range(12, int(ligne.length), 16))]
arbres = [a for a in arbres if a is not None]
if arbres:  # anomalie : coordonnée X saisie avec 1 km d'erreur
    x, y, z = arbres[-1].dxf.insert
    arbres[-1].dxf.insert = (x + 1000, y, z)

# Avaloirs tous les 25 m au fil d'eau
for d in range(15, int(ligne.length), 25):
    poser("AVAL", "AVALOIRS", d, -2.3, {})

# Objet sur un calque hors nomenclature : un banc
p = ligne.offset_curve(3.2).interpolate(ligne.length * 0.55)
msp.add_line(l93(p.x - 0.9, p.y), l93(p.x + 0.9, p.y), dxfattribs={"layer": "MOBILIER_DIVERS"})

# Habillage du prestataire
for s in segments[:3]:
    m = s.interpolate(0.5, True)
    msp.add_text(f"L={s.length:.2f}", height=0.4, dxfattribs={"layer": "COTATION"}).set_placement(l93(m.x, m.y))
x0, y0 = l93(*emprise.bounds[:2])
msp.add_text("RECOLEMENT - REAMENAGEMENT RUE CROIX D'OR - CABINET GEOMETRE (FICTIF) - RGF93 LAMBERT 93",
             height=1.0, dxfattribs={"layer": "CARTOUCHE"}).set_placement((x0, y0 - 8))

doc.saveas(CIBLE)
print(f"Récolement écrit : {CIBLE.name}")
print({l.dxf.name: sum(1 for e in msp if e.dxf.layer == l.dxf.name) for l in doc.layers})
