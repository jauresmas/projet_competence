"""
09_integration_recolement.py
Contrôle un plan de récolement DXF, le met en cohérence avec la charte de la Ville
et l'intègre dans la base topographique.

Étapes :
  1. Inventaire et détection du système de coordonnées, transformation vers CC45.
  2. Contrôles : calques hors charte, calque 0, doublons, objets hors emprise,
     attributs obligatoires, bordures en conflit avec le bâti, raccords avec l'existant.
  3. Intégration : les objets existants dans l'emprise sont archivés (calque gelé),
     les objets conformes sont ajoutés avec les calques, blocs et attributs de la Ville,
     les objets douteux vont sur un calque de contrôle.
  4. Rapport de contrôle (Markdown) et vues avant / après.

Entrées : donnees/topo/base_topo_secteur_croix_d_or.dxf, donnees/topo/recolement_croix_d_or_geometre.dxf
Sorties : donnees/topo/base_topo_secteur_croix_d_or_maj.dxf, docs/controle_recolement.md,
          sorties/recolement_avant_apres.png
Lancement : python-qgis-ltr.bat 09_integration_recolement.py
"""
import datetime as dt
from pathlib import Path

import ezdxf
import matplotlib
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from charte_topo import (BLOCS, CALQUES_REMPLACABLES, CORRESPONDANCE_ATTRIBUTS,
                         CORRESPONDANCE_BLOCS, CORRESPONDANCE_CALQUES, SRID_VILLE,
                         creer_calques_et_blocs)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
TOPO = RACINE / "donnees" / "topo"
BASE_DXF = TOPO / "base_topo_secteur_croix_d_or.dxf"
REC_DXF = TOPO / "recolement_croix_d_or_geometre.dxf"
MAJ_DXF = TOPO / "base_topo_secteur_croix_d_or_maj.dxf"
RAPPORT = RACINE / "docs" / "controle_recolement.md"
IMAGE = RACINE / "sorties" / "recolement_avant_apres.png"

TOLERANCE_DOUBLON = 0.05  # m
TOLERANCE_RACCORD = 0.50  # m

anomalies = []  # (code, gravité, calque, objet, message, action, x, y)


def signaler(code, gravite, calque, objet, message, action, xy=(None, None)):
    anomalies.append((code, gravite, calque, objet, message, action, *xy))


# --------------------------------------------------------------------------
# 1. Lecture, inventaire, système de coordonnées
# --------------------------------------------------------------------------
rec = ezdxf.readfile(REC_DXF)
msp_rec = rec.modelspace()
inventaire = {}
for e in msp_rec:
    inventaire[e.dxf.layer] = inventaire.get(e.dxf.layer, 0) + 1

xs, ys = [], []
for e in msp_rec:
    if e.dxftype() == "LWPOLYLINE":
        pts = [p[:2] for p in e.get_points()]
    elif e.dxftype() == "INSERT":
        pts = [e.dxf.insert.vec2]
    elif e.dxftype() == "LINE":
        pts = [e.dxf.start.vec2, e.dxf.end.vec2]
    else:
        continue
    xs += [p[0] for p in pts]
    ys += [p[1] for p in pts]
xm, ym = sorted(xs)[len(xs) // 2], sorted(ys)[len(ys) // 2]  # médiane : insensible aux erreurs isolées
if 700_000 < xm < 1_300_000 and 6_000_000 < ym < 7_200_000:
    scr_source = 2154
elif 1_600_000 < xm < 2_300_000 and 4_100_000 < ym < 4_400_000:
    scr_source = SRID_VILLE
else:
    raise SystemExit(f"Système de coordonnées non reconnu (médiane {xm:.0f}, {ym:.0f})")
if scr_source != SRID_VILLE:
    signaler("C01", "Bloquant corrigé", "tous", "fichier",
             f"Plan livré en EPSG:{scr_source} (Lambert 93) au lieu de CC45",
             "Transformation EPSG:2154 vers EPSG:3945 (pyproj)")
tr = Transformer.from_crs(scr_source, SRID_VILLE, always_xy=True)


def cc45(x, y):
    return tr.transform(x, y)


# Objets normalisés
objets = []
for e in msp_rec:
    calque, t = e.dxf.layer, e.dxftype()
    if t == "LWPOLYLINE":
        pts = [cc45(*p[:2]) for p in e.get_points()]
        geom = Polygon(pts) if e.closed else LineString(pts)
        objets.append({"calque": calque, "type": "polyligne", "geom": geom, "ferme": e.closed})
    elif t == "LINE":
        geom = LineString([cc45(*e.dxf.start.vec2), cc45(*e.dxf.end.vec2)])
        objets.append({"calque": calque, "type": "polyligne", "geom": geom, "ferme": False})
    elif t == "INSERT":
        x, y = cc45(*e.dxf.insert.vec2)
        attrs = {a.dxf.tag: a.dxf.text for a in e.attribs}
        objets.append({"calque": calque, "type": "bloc", "geom": Point(x, y), "bloc": e.dxf.name,
                       "attributs": attrs, "rotation": e.dxf.rotation, "z": e.dxf.insert.z})
    elif t in ("TEXT", "MTEXT", "DIMENSION"):
        objets.append({"calque": calque, "type": "habillage", "geom": None})

# --------------------------------------------------------------------------
# 2. Contrôles
# --------------------------------------------------------------------------
emprises = [o["geom"] for o in objets if o["calque"] == "EMPRISE_CHANTIER"]
if not emprises:
    raise SystemExit("Récolement sans emprise de chantier : intégration impossible")
emprise = unary_union(emprises)

for o in objets:
    c = o["calque"]
    o["cible"] = CORRESPONDANCE_CALQUES.get(c, "INCONNU")
    xy = (round(o["geom"].centroid.x, 2), round(o["geom"].centroid.y, 2)) if o["geom"] else (None, None)
    if c == "0":
        o["cible"] = "CTL_A_QUALIFIER"
        signaler("C02", "À reprendre", c, o["type"], "Objet sur le calque 0 : nature inconnue",
                 "Placé sur CTL_A_QUALIFIER, demande de précision au géomètre", xy)
    elif o["cible"] == "INCONNU":
        o["cible"] = "CTL_A_QUALIFIER"
        signaler("C03", "À reprendre", c, o["type"], f"Calque « {c} » absent de la charte",
                 "Placé sur CTL_A_QUALIFIER", xy)
    elif o["cible"] is None:
        o["cible"] = None
if any(o["cible"] is None for o in objets):
    exclus = sorted({o["calque"] for o in objets if o["cible"] is None})
    n = sum(1 for o in objets if o["cible"] is None)
    signaler("C04", "Information", ", ".join(exclus), f"{n} objets",
             "Habillage du prestataire (cotations, cartouche)", "Non intégré")

# Doublons de blocs
blocs = [o for o in objets if o["type"] == "bloc"]
for i, a in enumerate(blocs):
    for b in blocs[:i]:
        if not b.get("doublon") and a["bloc"] == b["bloc"] and a["geom"].distance(b["geom"]) < TOLERANCE_DOUBLON:
            a["doublon"] = True
            signaler("C05", "Corrigé", a["calque"], f"{a['bloc']} {a['attributs'].get('NUM', '')}",
                     "Bloc en double (même position à moins de 5 cm)", "Doublon supprimé",
                     (round(a["geom"].x, 2), round(a["geom"].y, 2)))

# Hors emprise
for o in objets:
    if o["geom"] is not None and o["calque"] != "EMPRISE_CHANTIER" and not o.get("doublon") \
            and not emprise.buffer(1).contains(o["geom"]):
        o["cible"] = "CTL_A_QUALIFIER"
        d = o["geom"].distance(emprise)
        signaler("C06", "À reprendre", o["calque"], o.get("bloc", o["type"]),
                 f"Objet à {d:.0f} m de l'emprise du chantier (erreur de saisie probable)",
                 "Placé sur CTL_A_QUALIFIER, non intégré", (round(o["geom"].x, 2), round(o["geom"].y, 2)))

# Attributs obligatoires
for o in blocs:
    bloc_ville = CORRESPONDANCE_BLOCS.get(o["bloc"])
    o["attributs_ville"] = {CORRESPONDANCE_ATTRIBUTS.get(k, k): v for k, v in o["attributs"].items()}
    for att in BLOCS.get(bloc_ville, []):
        if not o["attributs_ville"].get(att):
            o["incomplet"] = True
            signaler("C07", "À compléter", o["calque"], f"{bloc_ville} {o['attributs_ville'].get('NUMERO', '')}",
                     f"Attribut obligatoire {att} vide", "Intégré et signalé sur CTL_A_QUALIFIER",
                     (round(o["geom"].x, 2), round(o["geom"].y, 2)))

# Cohérence avec l'existant : bâti et raccords des bordures
base = ezdxf.readfile(BASE_DXF)
msp = base.modelspace()
bati = unary_union([Polygon([p[:2] for p in e.get_points()]).buffer(0)
                    for e in msp.query('LWPOLYLINE[layer=="BAT_BATI"]') if len(e) >= 3])
bordures_hors = unary_union([LineString([p[:2] for p in e.get_points()])
                             for e in msp.query('LWPOLYLINE[layer=="VOI_BORDURE"]')]).difference(emprise)
for o in objets:
    if o["cible"] == "VOI_BORDURE":
        conflit = o["geom"].intersection(bati.buffer(-0.2))
        if conflit.length > 0.1:
            signaler("C08", "À reprendre", o["calque"], "bordure",
                     f"Bordure traversant le bâti existant sur {conflit.length:.1f} m",
                     "Intégrée, à vérifier sur place", (round(conflit.centroid.x, 2), round(conflit.centroid.y, 2)))
        for extremite in (Point(o["geom"].coords[0]), Point(o["geom"].coords[-1])):
            if extremite.distance(emprise.boundary) < 1.5:  # l'extrémité arrive en limite de chantier
                ecart = extremite.distance(bordures_hors)
                if ecart > TOLERANCE_RACCORD:
                    signaler("C09", "Information", o["calque"], "bordure",
                             f"Raccord avec la bordure existante : écart de {ecart:.2f} m",
                             "À contrôler (la bordure existante est reconstituée)",
                             (round(extremite.x, 2), round(extremite.y, 2)))
if any(o.get("z") for o in blocs):
    signaler("C10", "Information", "blocs", f"{len(blocs)} blocs",
             "Altitudes présentes dans les points d'insertion", "Base planimétrique : objets ramenés à Z = 0")

# --------------------------------------------------------------------------
# 3. Intégration dans la base topographique
# --------------------------------------------------------------------------
creer_calques_et_blocs(base)
archives = 0
for e in list(msp):
    if e.dxf.layer not in CALQUES_REMPLACABLES:
        continue
    if e.dxftype() == "INSERT":
        if emprise.contains(Point(e.dxf.insert.vec2)):
            e.dxf.layer = "ARC_OBJET_REMPLACE"
            archives += 1
    elif e.dxftype() == "LWPOLYLINE":
        g = LineString([p[:2] for p in e.get_points()])
        if not g.intersects(emprise):
            continue
        # la partie hors emprise reste en service, la partie dans l'emprise est archivée
        for partie, calque in [(g.difference(emprise), e.dxf.layer), (g.intersection(emprise), "ARC_OBJET_REMPLACE")]:
            for s in getattr(partie, "geoms", [partie]):
                if s.geom_type == "LineString" and s.length > 0.05:
                    msp.add_lwpolyline(list(s.coords), dxfattribs={"layer": calque})
        msp.delete_entity(e)
        archives += 1
base.layers.get("ARC_OBJET_REMPLACE").freeze()

ajoutes = 0
for o in objets:
    if o["cible"] is None or o.get("doublon") or o["geom"] is None:
        continue
    calque = o["cible"]
    if o["type"] == "polyligne":
        if o["ferme"]:
            msp.add_lwpolyline(list(o["geom"].exterior.coords)[:-1], close=True, dxfattribs={"layer": calque})
        else:
            msp.add_lwpolyline(list(o["geom"].coords), dxfattribs={"layer": calque})
    else:
        bloc_ville = CORRESPONDANCE_BLOCS.get(o["bloc"], o["bloc"])
        ref = msp.add_blockref(bloc_ville, (o["geom"].x, o["geom"].y), dxfattribs={
            "layer": calque, "rotation": o["rotation"]})
        if BLOCS.get(bloc_ville):
            ref.add_auto_attribs({k: o["attributs_ville"].get(k, "") for k in BLOCS[bloc_ville]})
        if o.get("incomplet"):
            msp.add_circle((o["geom"].x, o["geom"].y), 1.2, dxfattribs={"layer": "CTL_A_QUALIFIER"})
    ajoutes += 1

# Repères des anomalies localisées
for code, _, _, _, _, _, x, y in anomalies:
    if x is not None and code in ("C02", "C03", "C06", "C07", "C08"):
        msp.add_text(code, height=0.8, dxfattribs={"layer": "CTL_A_QUALIFIER"}).set_placement((x + 1.5, y + 1.5))

base.header["$LASTSAVEDBY"] = "Demonstrateur de competences SIG Patrimoine"
audit = base.audit()
base.saveas(MAJ_DXF)
print(f"Base mise à jour : {MAJ_DXF.name} ({archives} objets archivés, {ajoutes} objets intégrés, "
      f"{len(audit.errors)} erreur(s) d'audit DXF)")

# --------------------------------------------------------------------------
# 4. Rapport et vues avant / après
# --------------------------------------------------------------------------
x0, y0, x1, y1 = emprise.buffer(6).bounds
fig, axes = plt.subplots(1, 2, figsize=(16, 8.5))
for ax, (doc, titre) in zip(axes, [(ezdxf.readfile(BASE_DXF), "Base topographique avant intégration"),
                                   (ezdxf.readfile(MAJ_DXF), "Après intégration du récolement")]):
    for masque in ["CAD_LIMITE", "TXT_ADRESSE", "TXT_VOIE"]:  # lisibilité de la vue seulement
        doc.layers.get(masque).off()
    Frontend(RenderContext(doc), MatplotlibBackend(ax),
             config=Configuration(background_policy=BackgroundPolicy.WHITE,
                                         lineweight_scaling=2.5)).draw_layout(doc.modelspace())
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_title(titre, fontsize=13, loc="left")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("#999")
fig.suptitle("Rue Croix d'Or : intégration d'un plan de récolement (données fictives)", fontsize=15,
             x=0.01, ha="left")
fig.text(0.01, 0.015, "Jaune : candélabres · vert : arbres · bleu : avaloirs · rouge : à qualifier, "
         "repères d'anomalies · magenta : emprise du chantier.\nLes objets remplacés sont archivés "
         "sur un calque gelé. Cadastre et adresses masqués sur cette vue.", fontsize=9, color="#555")
fig.tight_layout(rect=(0, 0.05, 1, 0.95))
fig.savefig(IMAGE, dpi=150)

gravites = {}
for a in anomalies:
    gravites[a[1]] = gravites.get(a[1], 0) + 1
L = [
    "# Contrôle et intégration d'un plan de récolement",
    "",
    "Chantier : réaménagement de la rue Croix d'Or (**fictif**, document de démonstration).  ",
    f"Fichier reçu : `{REC_DXF.name}`. Contrôle du {dt.date.today():%d/%m/%Y}.",
    "",
    "## Synthèse",
    "",
    f"- Système de coordonnées détecté : EPSG:{scr_source}, transformé en RGF93 CC45 (EPSG:{SRID_VILLE}).",
    f"- Objets reçus : {sum(inventaire.values())} ; intégrés : {ajoutes} ; archivés dans la base : {archives}.",
    "- Anomalies : " + ", ".join(f"{v} « {k} »" for k, v in gravites.items()) + ".",
    f"- Fichier produit : `{MAJ_DXF.name}` (l'original est conservé).",
    "",
    "## Inventaire du fichier reçu",
    "",
    "| Calque du prestataire | Objets | Calque Ville |",
    "|---|---:|---|",
]
for c, n in sorted(inventaire.items()):
    cible = CORRESPONDANCE_CALQUES.get(c, "CTL_A_QUALIFIER")
    L.append(f"| {c} | {n} | {cible or 'non intégré'} |")
L += ["", "## Anomalies", "", "| Code | Gravité | Calque | Objet | Constat | Action | X (CC45) | Y (CC45) |",
      "|---|---|---|---|---|---|---:|---:|"]
for code, grav, calque, obj, msg, action, x, y in anomalies:
    L.append(f"| {code} | {grav} | {calque} | {obj} | {msg} | {action} | {x if x is not None else ''} | "
             f"{y if y is not None else ''} |")
L += [
    "",
    "## Demande de reprise au prestataire",
    "",
    "1. Livrer les plans en RGF93 CC45, système de la Ville (le Lambert 93 a été transformé cette fois).",
    "2. Préciser la nature des objets posés sur le calque 0 et sur les calques hors charte.",
    "3. Corriger la position de l'arbre saisi hors emprise.",
    "4. Compléter les attributs obligatoires manquants (hauteur des candélabres).",
    "5. Utiliser les calques et blocs de la charte (table de correspondance jointe).",
    "",
    "![Avant / après](../sorties/recolement_avant_apres.png)",
]
RAPPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"Rapport : {RAPPORT.name}, {len(anomalies)} anomalies")
for a in anomalies:
    print("  ", a[0], a[1], "|", a[4])
