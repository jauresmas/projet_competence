"""
mise_en_page.py
Outils communs aux mises en page QGIS (plans du volet 3, fiches du volet 4) :
charte graphique, étiquettes, cartes, échelles, légendes, en-tête, exports.
"""
import math
from pathlib import Path

from qgis.core import (Qgis, QgsApplication, QgsFillSymbol, QgsLayoutExporter, QgsLayoutItemLabel,
                       QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
                       QgsLayoutItemScaleBar, QgsLayoutItemShape, QgsLayoutMeasurement,
                       QgsLayoutPoint, QgsLayoutSize, QgsLegendStyle, QgsProject, QgsTextFormat,
                       QgsUnitTypes, QgsVectorLayer)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont

MM = QgsUnitTypes.LayoutMillimeters
POLICE = "Segoe UI"

# Palette : encre, accent de la Ville, gris de fond
ENCRE = "35,38,43"
ACCENT = "0,94,138"
GRIS_TEXTE = "95,99,104"
FOND_BATI = {"color": "226,222,214", "outline_color": "178,172,162", "outline_width": "0.1"}

# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------
def couche(gpkg, nom, titre):
    lyr = QgsVectorLayer(f"{gpkg}|layername={nom}", titre, "ogr")
    assert lyr.isValid(), nom
    QgsProject.instance().addMapLayer(lyr, False)
    return lyr


def remplissage(**p):
    return QgsFillSymbol.createSimple({k: str(v) for k, v in p.items()})


def texte(taille, gras=False, couleur=ENCRE, italique=False):
    f = QgsTextFormat()
    police = QFont(POLICE)
    police.setBold(gras)
    police.setItalic(italique)
    f.setFont(police)
    f.setSize(taille)
    f.setSizeUnit(QgsUnitTypes.RenderPoints)
    f.setColor(QColor(*map(int, couleur.split(","))))
    return f


def placer(item, x, y, w=None, h=None):
    item.attemptMove(QgsLayoutPoint(x, y, MM))
    if w is not None:
        item.attemptResize(QgsLayoutSize(w, h, MM))


def etiquette(layout, txt, x, y, w, h, taille=9, gras=False, couleur=ENCRE,
              align=Qt.AlignLeft, valign=Qt.AlignTop, italique=False):
    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(txt)
    lbl.setTextFormat(texte(taille, gras, couleur, italique))
    lbl.setHAlign(align)
    lbl.setVAlign(valign)
    lbl.setMarginX(0)
    lbl.setMarginY(0)
    layout.addLayoutItem(lbl)
    placer(lbl, x, y, w, h)
    return lbl


def rectangle(layout, x, y, w, h, couleur, contour="no"):
    s = QgsLayoutItemShape(layout)
    s.setShapeType(QgsLayoutItemShape.Rectangle)
    props = {"color": couleur, "outline_style": "no" if contour == "no" else "solid"}
    if contour != "no":
        props.update({"outline_color": contour, "outline_width": "0.25"})
    s.setSymbol(remplissage(**props))
    layout.addLayoutItem(s)
    placer(s, x, y, w, h)
    return s


def carte(layout, couches, x, y, w, h, cadre=True):
    m = QgsLayoutItemMap(layout)
    m.setLayers(couches)
    m.setKeepLayerSet(True)
    m.setFrameEnabled(cadre)
    m.setFrameStrokeColor(QColor(120, 120, 120))
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.25, MM))
    m.setBackgroundColor(QColor(250, 249, 246))
    layout.addLayoutItem(m)
    placer(m, x, y, w, h)
    return m


def echelle(layout, carte_, x, y, par_segment, segments=2, unite="m"):
    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Single Box")
    sb.setLinkedMap(carte_)
    sb.setUnits(QgsUnitTypes.DistanceMeters if unite == "m" else QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel(unite)
    sb.setUnitsPerSegment(par_segment)
    sb.setNumberOfSegments(segments)
    sb.setNumberOfSegmentsLeft(0)
    sb.setHeight(1.6)
    sb.setTextFormat(texte(7, couleur=GRIS_TEXTE))
    layout.addLayoutItem(sb)
    sb.attemptMove(QgsLayoutPoint(x, y, MM))
    return sb


def nord(layout, x, y, taille=11):
    p = QgsLayoutItemPicture(layout)
    p.setPicturePath(str(Path(QgsApplication.pkgDataPath()) / "svg" / "arrows" / "NorthArrow_02.svg"))
    layout.addLayoutItem(p)
    placer(p, x, y, taille, taille)
    return p


def legende(layout, carte_, couches, x, y, titre="Légende", w=None):
    lg = QgsLayoutItemLegend(layout)
    lg.setAutoUpdateModel(False)
    lg.setLinkedMap(carte_)
    racine = lg.model().rootGroup()
    racine.clear()
    for lyr in couches:
        racine.addLayer(lyr)
    lg.setTitle(titre)
    lg.setStyleFont(QgsLegendStyle.Title, _police(9, True))
    lg.setStyleFont(QgsLegendStyle.Subgroup, _police(8, True))
    lg.setStyleFont(QgsLegendStyle.SymbolLabel, _police(7.5))
    lg.setSymbolWidth(6)
    lg.setSymbolHeight(3.5)
    lg.setBackgroundEnabled(False)
    if w:
        lg.setResizeToContents(False)
    layout.addLayoutItem(lg)
    lg.attemptMove(QgsLayoutPoint(x, y, MM))
    return lg


def _police(taille, gras=False):
    f = QFont(POLICE)
    f.setPointSizeF(taille)
    f.setBold(gras)
    return f


def entete(layout, largeur, titre, sous_titre, droite=""):
    rectangle(layout, 0, 0, largeur, 7, ACCENT)
    etiquette(layout, "DÉMONSTRATEUR DE COMPÉTENCES, NON OFFICIEL  ·  SIG Patrimoine Chambéry", 10, 1.6,
              largeur - 20, 5, 8, True, "255,255,255")
    if droite:
        etiquette(layout, droite, 10, 1.6, largeur - 20, 5, 8, True, "255,255,255", Qt.AlignRight)
    etiquette(layout, titre, 10, 11, largeur - 20, 10, 17, True)
    etiquette(layout, sous_titre, 10, 21, largeur - 20, 6, 10, False, GRIS_TEXTE)


def pied(layout, largeur, hauteur, sources):
    etiquette(layout, sources, 10, hauteur - 9, largeur - 20, 7, 6.5, False, GRIS_TEXTE)


def exporter_png(layout, cible, dpi=110):
    reglages = QgsLayoutExporter.ImageExportSettings()
    reglages.dpi = dpi
    QgsLayoutExporter(layout).exportToImage(str(cible), reglages)


def reglages_pdf():
    """Réglages PDF communs : texte réel (sélectionnable, indexable), géométries non simplifiées."""
    reglages = QgsLayoutExporter.PdfExportSettings()
    reglages.textRenderFormat = Qgis.TextRenderFormat.AlwaysText
    reglages.rasterizeWholeImage = False
    reglages.simplifyGeometries = False
    return reglages


def exporter_pdf(layout, cible):
    reglages = reglages_pdf()
    res = QgsLayoutExporter(layout).exportToPdf(str(cible), reglages)
    assert res == QgsLayoutExporter.Success, res


def arrondir_echelle(e, pas):
    return math.ceil(e / pas) * pas

