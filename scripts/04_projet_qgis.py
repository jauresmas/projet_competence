"""
04_projet_qgis.py
Crée le projet QGIS de gestion du SIG Patrimoine : couches du GeoPackage, styles,
relations (bâtiment / locaux, bâtiment / visites) et formulaires de saisie
(listes, contraintes, valeurs calculées : voir formulaires.py).

Produit aussi un paquet QField autonome (qfield/) pour les visites de terrain.

Lancement : python-qgis-ltr.bat 04_projet_qgis.py
"""
import shutil
from pathlib import Path
from urllib.parse import quote

from qgis.core import (QgsApplication, QgsCategorizedSymbolRenderer, QgsDataProvider,
                       QgsFillSymbol, QgsLineSymbol, QgsProject, QgsRasterLayer, QgsRelation,
                       QgsRendererCategory, QgsVectorLayer)

from formulaires import configurer
from schema import COUCHES, DOMAINES, RELATIONS

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "donnees" / "traite" / "patrimoine_chambery.gpkg"

COULEURS_TYPE = {
    "ADM": "31,78,121", "ENS": "224,138,0", "SPO": "46,139,87", "CUL": "142,68,173",
    "REL": "127,96,0", "SAN": "192,57,43", "TEC": "93,109,126", "COM": "211,84,0",
    "LOG": "169,169,169", "ANX": "213,216,220", "AQU": "241,196,15",
}

app = QgsApplication([], False)
app.initQgis()
projet = QgsProject.instance()
projet.setCrs(projet.crs().fromEpsgId(3945))
projet.setTitle("SIG Patrimoine Chambéry (démonstrateur)")

ORDRE = ["occupation_domaine_public", "batiment_communal", "local_communal", "visite_batiment",
         "parcelle_communale", "equipement_public", "troncon_voirie", "voie", "quartier"]
couches = {}
for nom in ORDRE:
    lyr = QgsVectorLayer(f"{BASE}|layername={nom}", COUCHES[nom]["alias"], "ogr")
    assert lyr.isValid(), nom
    for champ, alias, *_ in COUCHES[nom]["champs"]:
        idx = lyr.fields().indexOf(champ)
        if idx >= 0:
            lyr.setFieldAlias(idx, alias)
    couches[nom] = lyr

# Styles
cats = [QgsRendererCategory(code, QgsFillSymbol.createSimple(
            {"color": rgb, "outline_color": "60,60,60", "outline_width": "0.1"}),
            DOMAINES["dom_type_bien"][1][code]) for code, rgb in COULEURS_TYPE.items()]
couches["batiment_communal"].setRenderer(QgsCategorizedSymbolRenderer("type_bien", cats))
couches["parcelle_communale"].renderer().setSymbol(QgsFillSymbol.createSimple(
    {"color": "232,240,224", "outline_color": "181,201,163", "outline_width": "0.1"}))
couches["quartier"].renderer().setSymbol(QgsFillSymbol.createSimple(
    {"style": "no", "outline_color": "80,80,80", "outline_width": "0.5"}))
couches["equipement_public"].renderer().setSymbol(QgsFillSymbol.createSimple(
    {"style": "no", "outline_color": "142,68,173", "outline_width": "0.3",
     "outline_style": "dash"}))
couches["equipement_public"].setOpacity(0.7)
couches["troncon_voirie"].renderer().setSymbol(QgsLineSymbol.createSimple(
    {"color": "200,200,200", "width": "0.3"}))
couches["voie"].renderer().setSymbol(QgsLineSymbol.createSimple(
    {"color": "120,120,120", "width": "0.2"}))
couches["voie"].setScaleBasedVisibility(True)
couches["voie"].setMinimumScale(10000)
couches["occupation_domaine_public"].renderer().setSymbol(QgsFillSymbol.createSimple(
    {"color": "230,90,60,120", "outline_color": "200,40,20", "outline_width": "0.3"}))

# addMapLayer place chaque couche en haut de l'arbre : on ajoute de bas en haut
for nom in reversed(ORDRE):
    projet.addMapLayer(couches[nom])

# Fonds de plan IGN (Géoplateforme), en bas de l'arbre
groupe = projet.layerTreeRoot().addGroup("Fonds de plan")
for nom, couche, fmt, visible in [
        ("Plan IGN", "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", "image/png", True),
        ("Photographies aériennes IGN", "ORTHOIMAGERY.ORTHOPHOTOS", "image/jpeg", False)]:
    tuile = ("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
             f"&LAYER={couche}&STYLE=normal&TILEMATRIXSET=PM&FORMAT={fmt}"
             "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}")
    fond = QgsRasterLayer("type=xyz&zmin=0&zmax=19&url=" + quote(tuile, safe=":/{}"), nom, "wms")
    if visible:
        fond.renderer().setOpacity(0.5)
    projet.addMapLayer(fond, False)
    groupe.addLayer(fond).setItemVisibilityChecked(visible)
groupe.setExpanded(False)

# Relations 1-n déclarées dans schema.py
for nom, parent, enfant, cle, _, _ in RELATIONS:
    rel = QgsRelation()
    rel.setId(nom)
    rel.setName(COUCHES[enfant]["alias"])
    rel.setReferencedLayer(couches[parent].id())
    rel.setReferencingLayer(couches[enfant].id())
    rel.addFieldPair(cle, cle)
    assert rel.isValid(), rel.validationError()
    projet.relationManager().addRelation(rel)

configurer(couches, projet.relationManager().relations())

cible = RACINE / "patrimoine_chambery.qgz"
projet.setFileName(str(cible))  # chemins relatifs au projet
projet.write()
print("Projet écrit :", cible)

# Paquet QField : copie de la base et du projet, sans les couches inutiles sur le terrain
TERRAIN = RACINE / "qfield"
TERRAIN.mkdir(exist_ok=True)
(TERRAIN / "DCIM").mkdir(exist_ok=True)  # photos des visites, chemins relatifs au projet
base_terrain = TERRAIN / BASE.name
shutil.copy2(BASE, base_terrain)
for nom in ["equipement_public", "troncon_voirie"]:
    projet.removeMapLayer(couches.pop(nom).id())
for nom, lyr in couches.items():
    lyr.setDataSource(f"{base_terrain}|layername={nom}", lyr.name(), "ogr",
                      QgsDataProvider.ProviderOptions())
projet.setFileName(str(TERRAIN / "patrimoine_terrain.qgz"))
projet.setTitle("Visites du patrimoine bâti (QField)")
projet.write()
print("Paquet QField écrit :", TERRAIN)
app.exitQgis()
