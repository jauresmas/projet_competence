"""
10_fiches_batiments.py
Génère une fiche PDF par bâtiment communal (atlas QGIS) : identification,
caractéristiques, situation, liste des locaux (relation bâtiment -> locaux)
et points à renseigner.

Par défaut, seuls les bâtiments nommés sont édités (usage courant : fiches des
équipements). TOUS = True produit les 603 fiches.

Sorties : sorties/fiches/<id_bien>.pdf, sorties/fiche_batiment_apercu.png
Lancement : python-qgis-ltr.bat 10_fiches_batiments.py
"""
import datetime as dt
from pathlib import Path

from qgis.core import (QgsApplication, QgsFillSymbol, QgsLayoutExporter, QgsLayoutFrame,
                       QgsLayoutItemAttributeTable, QgsLayoutItemMap, QgsLayoutItemPage,
                       QgsLayoutTableColumn, QgsLineSymbol, QgsPalLayerSettings, QgsPrintLayout,
                       QgsProject, QgsRelation, QgsRuleBasedRenderer, QgsSingleSymbolRenderer,
                       QgsTextBufferSettings, QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor

from mise_en_page import (ACCENT, FOND_BATI, GRIS_TEXTE, carte, couche, echelle, entete,
                          etiquette, exporter_png, nord, pied, placer, rectangle, reglages_pdf,
                          remplissage, texte)
from schema import DOMAINES

TOUS = False

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"
PLANS = RACINE / "donnees" / "traite" / "plans.gpkg"
FICHES = RACINE / "sorties" / "fiches"
FICHES.mkdir(parents=True, exist_ok=True)
AUJOURDHUI = dt.date.today().strftime("%d/%m/%Y")

app = QgsApplication([], False)
app.initQgis()
projet = QgsProject.instance()
projet.setCrs(projet.crs().fromEpsgId(3945))


def libelle(champ, domaine):
    """Expression QGIS qui affiche le libellé d'un code de domaine."""
    cas = " ".join(f"WHEN \"{champ}\" = '{k}' THEN '{v.replace(chr(39), chr(39) * 2)}'"
                   for k, v in DOMAINES[domaine][1].items())
    return f"CASE {cas} ELSE '' END"


def nombre(champ, suffixe=""):
    return (f"[% CASE WHEN \"{champ}\" IS NULL THEN 'non renseigné' "
            f"ELSE replace(to_string(round(\"{champ}\")), ',', ' ') || '{suffixe}' END %]")


# Couches
quartiers = couche(BASE, "quartier", "Quartiers")
fond = couche(PLANS, "fond_batiment", "Bâti")
parcelles = couche(BASE, "parcelle_communale", "Parcelles communales")
voirie = couche(BASE, "troncon_voirie", "Voirie")
bat = couche(BASE, "batiment_communal", "Bâtiments communaux")
locaux = couche(BASE, "local_communal", "Locaux communaux")

fond.setRenderer(QgsSingleSymbolRenderer(remplissage(**FOND_BATI)))
parcelles.setRenderer(QgsSingleSymbolRenderer(remplissage(
    color="232,240,224", outline_color="160,185,140", outline_width="0.2")))
voirie.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
    {"color": "255,255,255", "width": "0.8"})))
tampon = QgsTextBufferSettings()
tampon.setEnabled(True)
tampon.setSize(0.8)
tampon.setColor(QColor(255, 255, 255))
reg = QgsPalLayerSettings()
reg.fieldName = "nom"
reg.placement = QgsPalLayerSettings.Line
fmt = texte(7, False, GRIS_TEXTE, italique=True)
fmt.setBuffer(tampon)
reg.setFormat(fmt)
voirie.setLabeling(QgsVectorLayerSimpleLabeling(reg))
voirie.setLabelsEnabled(True)

courant = "\"id_bien\" = attribute(@atlas_feature, 'id_bien')"
racine = QgsRuleBasedRenderer.Rule(None)
racine.appendChild(QgsRuleBasedRenderer.Rule(
    remplissage(color="0,94,138", outline_color="0,50,80", outline_width="0.4"), 0, 0, courant))
racine.appendChild(QgsRuleBasedRenderer.Rule(
    remplissage(color="140,170,190", outline_color="90,120,140", outline_width="0.15"), 0, 0, "ELSE"))
bat.setRenderer(QgsRuleBasedRenderer(racine))
quartiers.setRenderer(QgsSingleSymbolRenderer(remplissage(
    color="240,238,233", outline_color="150,150,150", outline_width="0.2")))

rel = QgsRelation()
rel.setId("rel_batiment_locaux")
rel.setName("Locaux du bâtiment")
rel.setReferencedLayer(bat.id())
rel.setReferencingLayer(locaux.id())
rel.addFieldPair("id_bien", "id_bien")
assert rel.isValid(), rel.validationError()
projet.relationManager().addRelation(rel)

# --------------------------------------------------------------------------
# Mise en page A4
# --------------------------------------------------------------------------
L = QgsPrintLayout(projet)
L.initializeDefaults()
L.setName("Fiche bâtiment")
L.renderContext().setPredefinedScales([500, 750, 1000, 1500, 2000, 3000])  # échelles de l'atlas
L.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Portrait)
W, H = 210, 297

entete(L, W, "[% coalesce(\"nom\", 'Bâtiment à nommer') %]",
       "[% \"id_bien\" %]  ·  [% \"adresse\" %]",
       "Fiche patrimoine bâti")

m = carte(L, [bat, voirie, fond, parcelles], 10, 31, 190, 112)
L.atlas().setCoverageLayer(bat)
L.atlas().setEnabled(True)
L.atlas().setSortFeatures(True)
L.atlas().setSortExpression("\"id_bien\"")
L.atlas().setFilenameExpression("\"id_bien\"")
if not TOUS:  # filtre d'atlas plutôt que filtre de couche : les autres bâtiments restent affichés
    L.atlas().setFilterFeatures(True)
    L.atlas().setFilterExpression("\"nom\" IS NOT NULL")
m.setAtlasDriven(True)
m.setAtlasScalingMode(QgsLayoutItemMap.Predefined)
m.setAtlasMargin(0.6)
m.zoomToExtent(bat.extent())  # emprise initiale valide avant le pilotage par l'atlas
nord(L, 186, 34)
echelle(L, m, 12, 136, 10, 3)

# Blocs d'information
BLOCS = [
    ("Identification", 10, [
        ("Identifiant GMAO", "[% \"id_bien\" %]"),
        ("Type de bien", "[% " + libelle("type_bien", "dom_type_bien") + " %]"),
        ("Quartier", "[% attribute(get_feature('Quartiers', 'code', \"quartier\"), 'nom') %]"),
        ("Parcelle", "[% \"idu_parcelle\" %]"),
        ("Identifiant RNB", "[% coalesce(\"id_rnb\", 'non renseigné') %]"),
        ("Réf. BD TOPO", "[% \"cleabs\" %]"),
    ]),
    ("Caractéristiques", 108, [
        ("Emprise au sol", nombre("emprise_m2", " m²")),
        ("Niveaux", nombre("nb_etages")),
        ("Hauteur", nombre("hauteur_m", " m")),
        ("Surface de plancher estimée", nombre("sdp_estimee_m2", " m²")),
        ("Usage (IGN)", "[% coalesce(\"usage_bdtopo\", 'non renseigné') %]"),
        ("Locaux fiscaux", "[% \"nb_locaux\" %]"),
    ]),
]
for titre, x, lignes in BLOCS:
    rectangle(L, x, 146, 92, 62, "246,244,240")
    etiquette(L, titre, x + 4, 149, 84, 6, 10, True, ACCENT)
    for i, (k, v) in enumerate(lignes):
        etiquette(L, k, x + 4, 158 + i * 8, 40, 6, 7.5, False, GRIS_TEXTE)
        etiquette(L, v, x + 42, 158 + i * 8, 48, 6, 8, True)

# Locaux (table enfant de la relation)
etiquette(L, "Locaux recensés (DGFiP 2025)", 10, 213, 120, 6, 10, True, ACCENT)
table = QgsLayoutItemAttributeTable.create(L)
L.addMultiFrame(table)
table.setVectorLayer(locaux)
table.setSource(QgsLayoutItemAttributeTable.RelationChildren)
table.setRelationId(rel.id())
colonnes = []
for champ, titre, largeur in [("id_local", "Local", 24), ("batiment", "Bâtiment", 20),
                              ("entree", "Entrée", 18), ("niveau", "Niveau", 18), ("porte", "Porte", 18)]:
    c = QgsLayoutTableColumn(titre)
    c.setAttribute(champ)
    c.setWidth(largeur)
    colonnes.append(c)
table.setColumns(colonnes)
table.setMaximumNumberOfFeatures(8)
table.setHeaderTextFormat(texte(7.5, True, GRIS_TEXTE))
table.setContentTextFormat(texte(7.5))
table.setGridStrokeWidth(0.15)
table.setGridColor(QColor(200, 200, 200))
table.setCellMargin(1)
table.setEmptyTableBehavior(QgsLayoutItemAttributeTable.ShowMessage)
table.setEmptyTableMessage("Aucun local fiscal rattaché à ce bâtiment")
cadre = QgsLayoutFrame(L, table)
placer(cadre, 10, 220, 120, 50)
table.addFrame(cadre)
etiquette(L, "[% CASE WHEN \"nb_locaux\" > 8 THEN '8 premiers locaux sur ' || \"nb_locaux\" "
             "ELSE '' END %]", 10, 271, 120, 5, 7, italique=True, couleur=GRIS_TEXTE)

# Situation dans la commune
etiquette(L, "Situation", 136, 213, 64, 6, 10, True, ACCENT)
ms = carte(L, [quartiers], 136, 220, 64, 50)
ms.zoomToExtent(quartiers.extent())
ms.overview().setLinkedMap(m)
ms.overview().setFrameSymbol(QgsFillSymbol.createSimple(
    {"color": "0,94,138,200", "outline_color": "0,94,138", "outline_width": "0.8"}))

# Points à renseigner (liste de travail pour la GMAO et les visites)
etiquette(L, "À renseigner : [% array_to_string(array_filter(array("
             "CASE WHEN \"etat\" = 'NR' THEN 'état général' END, "
             "CASE WHEN \"affectataire\" = 'NR' THEN 'service affectataire' END, "
             "CASE WHEN \"type_bien\" = 'AQU' THEN 'type de bien' END, "
             "CASE WHEN \"nb_etages\" IS NULL THEN 'nombre de niveaux' END), @element IS NOT NULL), ', ') %]",
          10, 277, 190, 6, 8, True, "200,45,35")
pied(L, W, H, "Sources : BD TOPO® IGN, cadastre Etalab, BAN, DGFiP (locaux des personnes morales 2025). "
              f"Fiche générée automatiquement le {AUJOURDHUI} depuis la base patrimoine.")

# --------------------------------------------------------------------------
# Export : un PDF par bâtiment + aperçu du plus grand équipement nommé
# --------------------------------------------------------------------------
reglages = reglages_pdf()
res, err = QgsLayoutExporter.exportToPdfs(L.atlas(), str(FICHES / "fiche.pdf"), reglages)
assert res == QgsLayoutExporter.Success, err
atlas = L.atlas()
atlas.beginRender()
for i in range(atlas.count()):
    atlas.seekTo(i)
    if atlas.layout().reportContext().feature()["id_bien"] == "BAT-CE-0116":  # Théâtre Charles Dullin
        break
exporter_png(L, RACINE / "sorties" / "fiche_batiment_apercu.png", 120)
atlas.endRender()
print(f"{atlas.count()} fiches exportées dans {FICHES}")
app.exitQgis()
