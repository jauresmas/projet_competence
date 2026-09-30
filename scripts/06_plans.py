"""
06_plans.py
Produit les trois plans types du volet 3 avec les mises en page QGIS :

  1. Plan de terrasse annexé à l'arrêté (A4 portrait, atlas : une page par terrasse)
  2. Plan de dispositif d'une manifestation (A3 paysage)
  3. Plan de la voirie communale pour le conseil municipal (A3 portrait)

Sorties : sorties/*.pdf et sorties/*.png (aperçus pour le portfolio)
Lancement : python-qgis-ltr.bat 06_plans.py
"""
import datetime as dt
from pathlib import Path

import geopandas as gpd
from qgis.core import (QgsApplication, QgsCategorizedSymbolRenderer, QgsLayoutExporter,
                       QgsLayoutFrame, QgsLayoutItemManualTable, QgsLayoutItemMap,
                       QgsLayoutItemPage, QgsLayoutTableColumn, QgsLineSymbol, QgsMarkerSymbol,
                       QgsPalLayerSettings, QgsPrintLayout, QgsProject, QgsProperty,
                       QgsRendererCategory, QgsRuleBasedRenderer,
                       QgsSingleSymbolRenderer, QgsTableCell, QgsTextBufferSettings,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from mise_en_page import (ACCENT, FOND_BATI, GRIS_TEXTE, arrondir_echelle, carte, couche,
                          echelle, entete, etiquette, exporter_pdf, exporter_png, legende, nord,
                          pied, placer, rectangle, reglages_pdf, remplissage,
                          rendre_chemins_relatifs, texte)

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
PLANS = RACINE / "donnees" / "traite" / "plans.gpkg"
SORTIES = RACINE / "sorties"
SORTIES.mkdir(exist_ok=True)
AUJOURDHUI = dt.date.today().strftime("%d/%m/%Y")

app = QgsApplication([], False)
app.initQgis()
projet = QgsProject.instance()
projet.setCrs(projet.crs().fromEpsgId(3945))
projet.setFileName(str(RACINE / "plans_volet3.qgz"))  # chemins relatifs au projet

# Couches communes
fond = couche(PLANS, "fond_batiment", "Bâti")
fond.setRenderer(QgsSingleSymbolRenderer(remplissage(**FOND_BATI)))

SOURCES = ("Sources : BD TOPO® IGN, cadastre Etalab, Base Adresse Nationale, DGFiP. "
           "Projection RGF93 CC45. Plan établi le " + AUJOURDHUI + ".")

# ==========================================================================
# 1. PLAN DE TERRASSE (atlas A4 portrait)
# ==========================================================================
print("Plan de terrasse")
ter = couche(BASE, "occupation_domaine_public", "Terrasses")
cotes = couche(PLANS, "cote_terrasse", "Cotes")
courant = "\"id_occupation\" = attribute(@atlas_feature, 'id_occupation')"

racine = QgsRuleBasedRenderer.Rule(None)
racine.appendChild(QgsRuleBasedRenderer.Rule(
    remplissage(color="200,45,35,90", outline_color="200,45,35", outline_width="0.6"),
    0, 0, courant, "Emprise autorisée"))
autre = remplissage(color="150,150,150", style="b_diagonal", outline_color="130,130,130",
                    outline_width="0.2", outline_style="dash")
racine.appendChild(QgsRuleBasedRenderer.Rule(autre, 0, 0, "ELSE", "Autre terrasse"))
ter.setRenderer(QgsRuleBasedRenderer(racine))

cotes.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
    {"color": "0,0,0,0", "width": "0"})))
reg = QgsPalLayerSettings()
reg.fieldName = "replace(to_string(round(\"longueur\", 2)), '.', ',') || ' m'"
reg.isExpression = True
reg.placement = QgsPalLayerSettings.Line
fmt = texte(8, True, "200,45,35")
tampon = QgsTextBufferSettings()
tampon.setEnabled(True)
tampon.setSize(0.8)
tampon.setColor(QColor(255, 255, 255))
fmt.setBuffer(tampon)
reg.setFormat(fmt)
reg.dataDefinedProperties().setProperty(QgsPalLayerSettings.Show, QgsProperty.fromExpression(courant))
cotes.setLabeling(QgsVectorLayerSimpleLabeling(reg))
cotes.setLabelsEnabled(True)

L = QgsPrintLayout(projet)
L.initializeDefaults()
L.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Portrait)
W, H = 210, 297

entete(L, W, "Occupation du domaine public : terrasse",
       "[% \"etablissement\" %], [% \"adresse\" %]",
       "Annexe à l'arrêté n° [% coalesce(\"num_arrete\", 'en instruction') %]")

m = carte(L, [cotes, ter, fond], 10, 31, 190, 150)
L.atlas().setCoverageLayer(ter)
L.atlas().setEnabled(True)
L.atlas().setPageNameExpression("\"id_occupation\"")
m.setAtlasDriven(True)
m.setAtlasScalingMode(QgsLayoutItemMap.Fixed)
m.zoomToExtent(ter.extent())
m.setScale(200)
nord(L, 186, 34)
echelle(L, m, 12, 174, 2, 3)

# Encadré des caractéristiques
rectangle(L, 10, 186, 112, 74, "246,244,240")
etiquette(L, "Caractéristiques de l'autorisation", 14, 189, 104, 6, 10, True, ACCENT)
lignes = [
    ("Référence", "[% \"id_occupation\" %]"),
    ("Type", "[% CASE WHEN \"type_occupation\" = 'TER_FER' THEN 'Terrasse fermée' "
             "ELSE 'Terrasse ouverte' END %]"),
    ("Surface autorisée", "[% replace(to_string(round(\"surface_m2\", 1)), '.', ',') %] m²"),
    ("Période", "du [% format_date(\"date_debut\", 'dd/MM/yyyy') %] "
                "au [% format_date(\"date_fin\", 'dd/MM/yyyy') %]"),
    ("Statut", "[% CASE WHEN \"statut\" = 'AUT' THEN 'Autorisée' "
               "WHEN \"statut\" = 'INS' THEN 'En instruction' ELSE \"statut\" END %]"),
    ("Voie", "Place Saint-Léger (secteur piétonnier)"),
]
for i, (k, v) in enumerate(lignes):
    etiquette(L, k, 14, 198 + i * 8, 36, 6, 8, False, GRIS_TEXTE)
    etiquette(L, v, 50, 198 + i * 8, 70, 6, 8.5, True)

# Carte de situation
etiquette(L, "Situation", 127, 186, 73, 5, 8, True, GRIS_TEXTE)
tr = couche(BASE, "troncon_voirie", "Voirie")
tr.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({"color": "255,255,255", "width": "0.6"})))
ms = carte(L, [tr, fond], 127, 192, 73, 68)
ms.setAtlasDriven(True)
ms.setAtlasScalingMode(QgsLayoutItemMap.Fixed)
ms.zoomToExtent(ter.extent())
ms.setScale(2500)
ms.overview().setLinkedMap(m)
ms.overview().setFrameSymbol(remplissage(color="200,45,35,60", outline_color="200,45,35",
                                         outline_width="0.5"))

# Légende manuelle (sémiologie volontairement simple)
y0 = 265
rectangle(L, 10, y0, 8, 4, "200,45,35,90", "200,45,35")
etiquette(L, "Emprise autorisée", 20, y0 + 0.3, 40, 5, 7.5)
rectangle(L, 62, y0, 8, 4, "226,222,214", "178,172,162")
etiquette(L, "Bâti", 72, y0 + 0.3, 20, 5, 7.5)
rectangle(L, 90, y0, 8, 4, "200,200,200", "130,130,130")
etiquette(L, "Autre terrasse", 100, y0 + 0.3, 30, 5, 7.5)
etiquette(L, "3,50 m", 130, y0 + 0.1, 14, 5, 7.5, True, "200,45,35")
etiquette(L, "Cote en mètres", 145, y0 + 0.3, 40, 5, 7.5)
etiquette(L, "Le titulaire doit laisser libre un passage piéton de 1,40 m minimum. "
             "Tout mobilier hors de l'emprise est interdit.", 10, 272, 190, 8, 7.5,
          italique=True, couleur=GRIS_TEXTE)
pied(L, W, H, SOURCES + " Terrasses, établissements et arrêtés FICTIFS (document de démonstration).")

atlas = L.atlas()
res, err = QgsLayoutExporter.exportToPdf(atlas, str(SORTIES / "plan_terrasses_arretes.pdf"),
                                         reglages_pdf())
assert res == QgsLayoutExporter.Success, err
atlas.beginRender()
atlas.first()
exporter_png(L, SORTIES / "plan_terrasse_apercu.png", 120)
atlas.endRender()
print(f"  {ter.featureCount()} pages")

# ==========================================================================
# 2. PLAN DE MANIFESTATION (A3 paysage)
# ==========================================================================
print("Plan de manifestation")
per = couche(PLANS, "fete_perimetre", "Périmètre piéton")
per.setRenderer(QgsSingleSymbolRenderer(remplissage(color="255,214,102,110", outline_color="214,150,0",
                                                    outline_width="0.5")))
fer = couche(PLANS, "fete_voie_fermee", "Voie fermée à la circulation")
fer.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
    {"color": "200,45,35", "width": "1.1", "line_style": "dash", "capstyle": "flat"})))
eng = couche(PLANS, "fete_voie_engins", "Voie engins de 4 m maintenue libre")
eng.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
    {"color": "0,94,138", "width": "0.5", "line_style": "dot"})))
bar = couche(PLANS, "fete_barrage", "Contrôle des accès")
bar.setRenderer(QgsCategorizedSymbolRenderer("type", [
    QgsRendererCategory("Barrage véhicules (bloc béton)", QgsMarkerSymbol.createSimple(
        {"name": "square", "color": "35,38,43", "outline_color": "255,255,255", "size": "3.6"}),
        "Barrage véhicules (bloc béton)"),
    QgsRendererCategory("Accès secours (barrière amovible)", QgsMarkerSymbol.createSimple(
        {"name": "triangle", "color": "46,139,87", "outline_color": "255,255,255", "size": "5"}),
        "Accès secours (barrière amovible)"),
]))
equ = couche(PLANS, "fete_equipement", "Équipements")
FORMES = {
    "Scène": ("star", "108,52,131", 6.5),
    "Secours": ("cross_fill", "200,45,35", 5),
    "Sanitaires": ("square", "0,94,138", 3.8),
    "Buvette": ("circle", "160,100,40", 3.8),
    "Information": ("diamond", "0,140,140", 4.2),
}
equ.setRenderer(QgsCategorizedSymbolRenderer("type", [
    QgsRendererCategory(k, QgsMarkerSymbol.createSimple(
        {"name": f, "color": c, "outline_color": "255,255,255", "outline_width": "0.3", "size": str(s)}),
        {"Secours": "Poste de secours"}.get(k, k)) for k, (f, c, s) in FORMES.items()]))
reg = QgsPalLayerSettings()
reg.fieldName = "libelle"
reg.placement = QgsPalLayerSettings.AroundPoint
reg.dist = 1.5
fmt = texte(7.5, True)
fmt.setBuffer(tampon)
reg.setFormat(fmt)
equ.setLabeling(QgsVectorLayerSimpleLabeling(reg))
equ.setLabelsEnabled(True)

L2 = QgsPrintLayout(projet)
L2.initializeDefaults()
L2.pageCollection().page(0).setPageSize("A3", QgsLayoutItemPage.Landscape)
W, H = 420, 297
entete(L2, W, "Fête de la musique : dispositif de sécurité du centre historique",
       "Place Saint-Léger, place et rue de la Métropole  ·  21 juin, de 16 h à 2 h",
       "Plan annexé à l'arrêté de circulation et de stationnement")
m2 = carte(L2, [equ, bar, eng, fer, per, tr, fond], 10, 31, 300, 256)
emprise = per.extent()
emprise.combineExtentWith(bar.extent())
emprise.grow(25)
m2.zoomToExtent(emprise)
m2.setScale(arrondir_echelle(m2.scale(), 250))
nord(L2, 296, 34, 12)
echelle(L2, m2, 14, 279, 25, 4)

X = 318
etiquette(L2, "Légende", X, 32, 92, 6, 11, True, ACCENT)
legende(L2, m2, [per, fer, eng, bar, equ], X, 39, titre="")
rectangle(L2, X, 150, 92, 66, "246,244,240")
etiquette(L2, "Consignes", X + 4, 154, 84, 6, 10, True, ACCENT)
consignes = (
    "•  Barrages posés à 15 h 30, retirés à 2 h 30 par les services techniques.\n\n"
    "•  Voie engins de 4 m maintenue libre sur tout le parcours : aucun stand, "
    "aucune terrasse ni aucun mobilier sur cet axe.\n\n"
    "•  L'accès secours se fait par la barrière amovible nord, gardée en permanence.\n\n"
    "•  Terrasses autorisées maintenues dans leur emprise ; extensions interdites.\n\n"
    "•  Stationnement interdit sur les voies fermées à partir de 12 h.")
etiquette(L2, consignes, X + 4, 162, 84, 52, 8.5)
pied(L2, W, H, SOURCES + " Manifestation et dispositif FICTIFS (document de démonstration).")
exporter_pdf(L2, SORTIES / "plan_manifestation.pdf")
exporter_png(L2, SORTIES / "plan_manifestation_apercu.png", 90)

# ==========================================================================
# 3. PLAN DE VOIRIE POUR LE CONSEIL MUNICIPAL (A3 portrait)
# ==========================================================================
print("Plan de voirie")
quart = couche(BASE, "quartier", "Quartiers")
quart.setRenderer(QgsSingleSymbolRenderer(remplissage(style="no", outline_color="35,38,43",
                                                      outline_width="0.6")))
reg = QgsPalLayerSettings()
reg.fieldName = "replace(\"nom\", 'Chambéry ', '')"
reg.isExpression = True
reg.placement = QgsPalLayerSettings.OverPoint
fmt = texte(11, True, "35,38,43")
fmt.setBuffer(tampon)
fmt.buffer().setSize(1.2)
reg.setFormat(fmt)
quart.setLabeling(QgsVectorLayerSimpleLabeling(reg))
quart.setLabelsEnabled(True)
ROUTES = ("\"nature\" IN ('Route à 1 chaussée', 'Route à 2 chaussées', 'Rond-point', "
          "'Route empierrée', 'Bretelle', 'Type autoroutier')")
voirie = couche(BASE, "troncon_voirie", "Domanialité de la voirie")
voirie.setSubsetString(ROUTES)
DOM = [
    ("COM", "Voirie communale", "200,45,35", 0.7),
    ("DEP", "Route départementale", "230,140,20", 0.9),
    ("NAT", "Route nationale", "108,52,131", 1.1),
    ("AUT", "Autoroute concédée", "90,90,90", 1.2),
    ("PRI", "Voie privée", "150,150,150", 0.35),
    ("NR", "Domanialité à déterminer", "40,130,200", 0.5),
]
voirie.setRenderer(QgsCategorizedSymbolRenderer("domanialite", [
    QgsRendererCategory(c, QgsLineSymbol.createSimple({"color": col, "width": str(w)}), lib)
    for c, lib, col, w in DOM]))
chemins = couche(BASE, "troncon_voirie", "Chemins, sentiers, escaliers")
chemins.setSubsetString("NOT (" + ROUTES + ")")
chemins.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
    {"color": "170,170,170", "width": "0.2", "line_style": "dash"})))

fond_clair = couche(PLANS, "fond_batiment", "Bâti")
fond_clair.setRenderer(QgsSingleSymbolRenderer(remplissage(color="236,233,227", outline_style="no")))

# Linéaire par quartier (découpage des tronçons par quartier)
g_tr = gpd.read_file(BASE, layer="troncon_voirie")
g_tr = g_tr[g_tr["nature"].isin(["Route à 1 chaussée", "Route à 2 chaussées", "Rond-point",
                                 "Route empierrée", "Bretelle", "Type autoroutier"])]
g_q = gpd.read_file(BASE, layer="quartier")
decoupe = gpd.overlay(g_tr[["domanialite", "geometry"]], g_q[["nom", "geometry"]],
                      how="intersection", keep_geom_type=True)
decoupe["km"] = decoupe.length / 1000
tab = decoupe.pivot_table(index="nom", columns="domanialite", values="km", aggfunc="sum",
                          fill_value=0)
tab["total"] = tab.sum(axis=1)
tab = tab.sort_values("COM", ascending=False)


def km(v):
    return f"{v:.1f}".replace(".", ",")


L3 = QgsPrintLayout(projet)
L3.initializeDefaults()
L3.pageCollection().page(0).setPageSize("A3", QgsLayoutItemPage.Portrait)
W, H = 297, 420
total_com = tab["COM"].sum()
entete(L3, W, "Voirie de la commune : linéaire par domanialité",
       f"Document préparatoire au conseil municipal  ·  {km(total_com)} km de voirie communale présumée",
       "Mise à jour du tableau de classement")
m3 = carte(L3, [quart, voirie, chemins, fond_clair], 10, 31, 277, 262)
ext = quart.extent()
ext.grow(150)
m3.zoomToExtent(ext)
m3.setScale(arrondir_echelle(m3.scale(), 2500))
nord(L3, 272, 34, 12)
echelle(L3, m3, 14, 285, 0.5, 2, "km")

legende(L3, m3, [voirie, chemins], 10, 300, titre="Légende")
etiquette(L3, "Linéaire de voirie par quartier (km)", 100, 299, 187, 6, 10, True, ACCENT)
table = QgsLayoutItemManualTable.create(L3)
L3.addMultiFrame(table)
cols = ["Quartier", "Communale", "Départ.", "Nationale", "Autres", "Total"]
entetes = []
for i, c in enumerate(cols):
    col = QgsLayoutTableColumn(c)
    col.setHAlignment(Qt.AlignLeft if i == 0 else Qt.AlignRight)
    entetes.append(col)
table.setHeaders(entetes)
table.setIncludeTableHeader(True)
lignes = []
for nom, r in tab.iterrows():
    autres = r.get("AUT", 0) + r.get("PRI", 0) + r.get("NR", 0)
    lignes.append([nom.replace("Chambéry ", ""), km(r.get("COM", 0)), km(r.get("DEP", 0)),
                   km(r.get("NAT", 0)), km(autres), km(r["total"])])
tot = tab.sum()
lignes.append(["Commune", km(tot.get("COM", 0)), km(tot.get("DEP", 0)), km(tot.get("NAT", 0)),
               km(tot.get("AUT", 0) + tot.get("PRI", 0) + tot.get("NR", 0)), km(tot["total"])])
contenu = []
for i, ligne in enumerate(lignes):
    rangee = []
    for j, v in enumerate(ligne):
        c = QgsTableCell(v)
        c.setTextFormat(texte(8.5, gras=(i == len(lignes) - 1 or j == 1)))
        c.setHorizontalAlignment(Qt.AlignLeft if j == 0 else Qt.AlignRight)
        if i == len(lignes) - 1:
            c.setBackgroundColor(QColor(246, 244, 240))
        rangee.append(c)
    contenu.append(rangee)
table.setTableContents(contenu)
table.setHeaderTextFormat(texte(8, True, GRIS_TEXTE))
table.setCellMargin(1.4)
table.setGridStrokeWidth(0.15)
table.setGridColor(QColor(200, 200, 200))
table.setColumnWidths([36, 26, 24, 24, 22, 22])
cadre = QgsLayoutFrame(L3, table)
placer(cadre, 100, 307, 187, 70)
table.addFrame(cadre)

etiquette(L3, "La domanialité est présumée à partir de la BD TOPO (classement administratif "
              "des routes). Elle doit être confirmée par le tableau de classement de la voirie "
              "communale avant délibération. Le linéaire de voirie communale entre dans le calcul "
              "de la dotation globale de fonctionnement.", 100, 382, 187, 20, 8, italique=True,
          couleur=GRIS_TEXTE)
pied(L3, W, H, SOURCES)
exporter_pdf(L3, SORTIES / "plan_voirie_conseil_municipal.pdf")
exporter_png(L3, SORTIES / "plan_voirie_apercu.png", 80)
print(tab.round(2).to_string())

# Projet QGIS contenant les trois mises en page, pour retouche manuelle
for lay, nom in [(L, "1. Plan de terrasse (atlas)"), (L2, "2. Plan de manifestation"),
                 (L3, "3. Plan de voirie")]:
    lay.setName(nom)
    projet.layoutManager().addLayout(lay)
arbre = projet.layerTreeRoot()
for titre, lyrs in [("Terrasses", [cotes, ter]),
                    ("Manifestation", [equ, bar, eng, fer, per]),
                    ("Voirie", [quart, voirie, chemins]),
                    ("Fond", [tr, fond, fond_clair])]:
    g = arbre.addGroup(titre)
    for lyr in lyrs:
        g.addLayer(lyr)
projet.write(str(RACINE / "plans_volet3.qgz"))
rendre_chemins_relatifs(RACINE / "plans_volet3.qgz", RACINE)

app.exitQgis()
print("Plans exportés dans", SORTIES)
