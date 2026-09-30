"""
13_modele_recolement.py
Construit le modèle graphique QGIS « Intégration d'un plan de récolement » (équivalent
d'un modèle ModelBuilder d'ArcGIS Pro), l'enregistre en .model3 et l'exécute sur le
DXF du géomètre pour vérifier le résultat.

Étapes du modèle :
  1. Définir le SCR du prestataire (le DXF n'en porte pas)
  2. Reprojeter en RGF93 CC45
  3. Séparer les objets des calques connus de la charte et les objets à qualifier
  4. Traduire les calques du prestataire en calques de la Ville (table de correspondance)
  5. Supprimer les géométries en double

À ouvrir dans QGIS : Traitement > Boîte à outils > Modèles > Ouvrir un modèle existant.
Sortie : modeles/integration_recolement.model3, docs/modele_recolement.md
Lancement : python-qgis-ltr.bat 13_modele_recolement.py
"""
import sys
from pathlib import Path

from osgeo import gdal

from qgis.core import (QgsApplication, QgsProcessing, QgsProcessingModelAlgorithm,
                       QgsProcessingModelChildAlgorithm, QgsProcessingModelChildParameterSource,
                       QgsProcessingModelComment, QgsProcessingModelOutput,
                       QgsProcessingModelParameter, QgsProcessingParameterCrs,
                       QgsProcessingParameterFeatureSource, QgsVectorLayer)
from qgis.PyQt.QtCore import QPointF

from charte_topo import CORRESPONDANCE_CALQUES

RACINE = Path(__file__).resolve().parents[1]
DXF = RACINE / "donnees" / "topo" / "recolement_croix_d_or_geometre.dxf"
MODELES = RACINE / "modeles"
MODELES.mkdir(exist_ok=True)
CIBLE = MODELES / "integration_recolement.model3"

gdal.SetConfigOption("DXF_INLINE_BLOCKS", "FALSE")  # un bloc = un point, comme dans AutoCAD
app = QgsApplication([], True)  # mode graphique : nécessaire pour dessiner le schéma du modèle
app.initQgis()
sys.path.append(str(Path(QgsApplication.prefixPath()) / "python" / "plugins"))
from processing.core.Processing import Processing  # noqa: E402

Processing.initialize()
import processing  # noqa: E402

# Expressions tirées de la charte (une seule source de vérité : charte_topo.py)
connus = {k: v for k, v in CORRESPONDANCE_CALQUES.items() if v}
liste_connus = ", ".join(f"'{k}'" for k in connus)
table = ", ".join(f"'{k}', '{v}'" for k, v in connus.items())

m = QgsProcessingModelAlgorithm("Intégration d'un plan de récolement", "SIG Patrimoine")
m.setHelpContent({
    "ALG_DESC": "Met en cohérence une couche DAO livrée par un prestataire avec la charte de la Ville : "
                "SCR, reprojection en CC45, calques conformes ou à qualifier, traduction des calques, "
                "suppression des doublons.",
    "ALG_CREATOR": "Jaurès DAA-HINGBANON",
})


def source_modele(nom):
    return [QgsProcessingModelChildParameterSource.fromModelParameter(nom)]


def source_etape(etape, sortie="OUTPUT"):
    return [QgsProcessingModelChildParameterSource.fromChildOutput(etape, sortie)]


def valeur(v):
    return [QgsProcessingModelChildParameterSource.fromStaticValue(v)]


def etape(identifiant, algo, description, x, y, parametres, sorties=None):
    c = QgsProcessingModelChildAlgorithm(algo)
    c.setChildId(identifiant)
    c.setDescription(description)
    c.setPosition(QPointF(x, y))
    for nom, src in parametres.items():
        c.addParameterSources(nom, src)
    if sorties:
        modeles = {}
        for nom_sortie, (libelle, pos) in sorties.items():
            o = QgsProcessingModelOutput(libelle)
            o.setChildOutputName(nom_sortie)
            o.setDescription(libelle)
            o.setChildId(identifiant)
            o.setPosition(pos)
            modeles[libelle] = o
        c.setModelOutputs(modeles)
    m.addChildAlgorithm(c)


# Entrées
p = QgsProcessingModelParameter("recolement")
p.setPosition(QPointF(160, 60))
m.addModelParameter(QgsProcessingParameterFeatureSource(
    "recolement", "Plan de récolement (DAO)", [QgsProcessing.TypeVectorAnyGeometry]), p)
p = QgsProcessingModelParameter("scr_prestataire")
p.setPosition(QPointF(480, 60))
m.addModelParameter(QgsProcessingParameterCrs(
    "scr_prestataire", "SCR du plan livré", defaultValue="EPSG:2154"), p)

# Chaîne
etape("scr", "native:assignprojection", "1. SCR du prestataire", 300, 170,
      {"INPUT": source_modele("recolement"), "CRS": source_modele("scr_prestataire")})
etape("reprojection", "native:reprojectlayer", "2. Reprojeter en CC45", 300, 270,
      {"INPUT": source_etape("scr"), "TARGET_CRS": valeur("EPSG:3945")})
etape("tri", "native:extractbyexpression", "3. Trier les calques", 300, 370,
      {"INPUT": source_etape("reprojection"), "EXPRESSION": valeur(f"\"Layer\" IN ({liste_connus})")},
      {"FAIL_OUTPUT": ("Objets à qualifier", QPointF(640, 420))})
etape("traduction", "native:fieldcalculator", "4. Traduire les calques", 300, 470,
      {"INPUT": source_etape("tri"), "FIELD_NAME": valeur("calque_ville"), "FIELD_TYPE": valeur(2),
       "FIELD_LENGTH": valeur(40), "FIELD_PRECISION": valeur(0),
       "FORMULA": valeur(f"map_get(map({table}), \"Layer\")")})
etape("doublons", "native:deleteduplicategeometries", "5. Supprimer les doublons", 300, 570,
      {"INPUT": source_etape("traduction")},
      {"OUTPUT": ("Objets conformes, en CC45", QPointF(300, 680))})

commentaire = QgsProcessingModelComment()
commentaire.setDescription("Autres contrôles : script 09")
commentaire.setPosition(QPointF(640, 250))
m.childAlgorithm("reprojection").setComment(commentaire)

ok, erreurs = m.validate()
assert ok, erreurs
assert m.toFile(str(CIBLE)), "écriture du modèle impossible"
print("Modèle enregistré :", CIBLE)

# Schéma du modèle en image (tel qu'il apparaît dans le modeleur graphique)
from qgis.core import QgsProcessingContext  # noqa: E402
from qgis.gui import QgsModelGraphicsScene  # noqa: E402
from qgis.PyQt.QtCore import QRectF  # noqa: E402
from qgis.PyQt.QtGui import QColor, QImage, QPainter  # noqa: E402

scene = QgsModelGraphicsScene()
scene.setModel(m)
scene.createItems(m, QgsProcessingContext())
cadre = scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
image = QImage(int(cadre.width() * 2), int(cadre.height() * 2), QImage.Format_ARGB32)
image.fill(QColor(255, 255, 255))
peintre = QPainter(image)
peintre.setRenderHint(QPainter.Antialiasing)
scene.render(peintre, QRectF(0, 0, image.width(), image.height()), cadre)
peintre.end()
image.save(str(RACINE / "sorties" / "modele_recolement.png"))

# Exécution sur le DXF du géomètre : lignes (bordures, emprise) puis points (blocs)
sorties = {d.description(): d.name() for d in m.destinationParameterDefinitions()}
SORTIE_OK, SORTIE_KO = sorties["Objets conformes, en CC45"], sorties["Objets à qualifier"]
bilan = []
for geom in ["LineString", "Point"]:
    entree = QgsVectorLayer(f"{DXF}|layername=entities|geometrytype={geom}", geom, "ogr")
    res = processing.run(m, {
        "recolement": entree, "scr_prestataire": "EPSG:2154",
        SORTIE_OK: "TEMPORARY_OUTPUT", SORTIE_KO: "TEMPORARY_OUTPUT",
    })
    conformes, qualifier = res[SORTIE_OK], res[SORTIE_KO]
    calques = sorted({f["calque_ville"] for f in conformes.getFeatures()})
    a_qualifier = sorted({f["Layer"] for f in qualifier.getFeatures()})
    x = next(conformes.getFeatures()).geometry().centroid().asPoint().x() if conformes.featureCount() else 0
    bilan.append((geom, entree.featureCount(), conformes.featureCount(), qualifier.featureCount(),
                  calques, a_qualifier, x))
    print(f"{geom} : {entree.featureCount()} objets -> {conformes.featureCount()} conformes "
          f"{calques}, {qualifier.featureCount()} à qualifier {a_qualifier}, X = {x:.0f} (CC45)")

lignes = [
    "# Modèle graphique : intégration d'un plan de récolement",
    "",
    "Modèle QGIS (`modeles/integration_recolement.model3`), équivalent d'un modèle ModelBuilder "
    "d'ArcGIS Pro. À ouvrir dans QGIS : *Traitement > Boîte à outils > Modèles > Ouvrir un modèle existant*.",
    "",
    "| Étape | Outil QGIS | Équivalent ArcGIS Pro |",
    "|---|---|---|",
    "| 1. Définir le SCR du prestataire | Définir la projection | Define Projection |",
    "| 2. Reprojeter en CC45 | Reprojeter une couche | Project |",
    "| 3. Calques de la charte / à qualifier | Extraire par expression | Select (Split by Attributes) |",
    "| 4. Traduire les calques | Calculatrice de champ | Calculate Field |",
    "| 5. Supprimer les doublons | Supprimer les géométries dupliquées | Delete Identical |",
    "",
    "## Exécution sur le DXF du géomètre (fictif)",
    "",
    "| Géométries | Objets reçus | Conformes | À qualifier | Calques Ville obtenus | Calques à qualifier |",
    "|---|---:|---:|---:|---|---|",
]
for geom, n, c, q, calques, aq, _ in bilan:
    lignes.append(f"| {geom} | {n} | {c} | {q} | {', '.join(calques)} | {', '.join(aq)} |")
lignes += ["", "![Schéma du modèle](../sorties/modele_recolement.png)", "", "Les coordonnées de sortie sont en CC45 (X de l'ordre de 1 928 000 m), le plan était livré "
               "en Lambert 93 (X de l'ordre de 940 000 m)."]
(RACINE / "docs" / "modele_recolement.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
app.exitQgis()
