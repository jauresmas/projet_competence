"""
15_captures.py
Produit les captures d'écran du portfolio :

  1. Tableau de bord (Microsoft Edge sans interface) : haut de page, page entière,
     vues « chantier » et « terrasses » ouvertes par lien direct (?vue=...).
  2. Formulaires QGIS réels : fiche d'un bâtiment (onglets, locaux, visites) et saisie
     d'une visite avec un contrôle qui se déclenche. Deux visites FICTIVES sont ajoutées
     dans une copie temporaire de la base : la base du projet n'est pas modifiée.

Sorties : sorties/captures/*.png
Lancement : python-qgis-ltr.bat 15_captures.py (Windows, Edge installé)
"""
import faulthandler
import os
import sys
import functools
import http.server
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image, ImageChops

faulthandler.enable()
faulthandler.dump_traceback_later(480, exit=True)  # sécurité : diagnostic et arrêt si blocage
RACINE = Path(__file__).resolve().parents[1]
CAPTURES = RACINE / "sorties" / "captures"
CAPTURES.mkdir(parents=True, exist_ok=True)
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PORT = 8768


# --------------------------------------------------------------------------
# Outils de capture du tableau de bord (exécutés en fin de script)
# --------------------------------------------------------------------------
def rogner_bas(chemin, marge=40):
    """Retire la bande vide du bas d'une capture pleine page."""
    im = Image.open(chemin).convert("RGB")
    fond = Image.new("RGB", im.size, im.getpixel((5, im.height - 5)))
    boite = ImageChops.difference(im, fond).getbbox()
    if boite:
        im.crop((0, 0, im.width, min(im.height, boite[3] + marge))).save(chemin)


def capture_page(url, cible, largeur, hauteur):
    cible.unlink(missing_ok=True)
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--user-data-dir={Path(tempfile.gettempdir()) / 'edge-captures'}",
                    f"--window-size={largeur},{hauteur}", "--virtual-time-budget=20000",
                    f"--screenshot={cible}", url], check=True, timeout=180)
    # Edge rend la main avant d'avoir écrit l'image : on attend le fichier complet
    for _ in range(90):
        if cible.exists() and cible.stat().st_size > 0:
            time.sleep(1)
            return
        time.sleep(1)
    raise TimeoutError(f"capture non produite : {cible.name}")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass



# --------------------------------------------------------------------------
# 2. Formulaires QGIS (copie temporaire de la base)
# --------------------------------------------------------------------------
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayerTools,  # noqa: E402
                       QgsVectorLayerUtils)
from qgis.PyQt.QtCore import QDate  # noqa: E402
from qgis.PyQt.QtWidgets import QTabWidget  # noqa: E402

app = QgsApplication([], True)
app.initQgis()
from qgis.PyQt.QtCore import QTranslator  # noqa: E402

traduction = QTranslator()  # interface QGIS en français (messages des formulaires)
if os.environ.get("CAPTURES_SANS_TRADUCTION") != "1" and traduction.load("qgis_fr", str(Path(QgsApplication.i18nPath()))):
    app.installTranslator(traduction)
from qgis.gui import QgsAttributeEditorContext, QgsAttributeForm, QgsGui, QgsMapCanvas  # noqa: E402

QgsGui.editorWidgetRegistry().initEditors()  # widgets de formulaire (listes, dates, relations)


class OutilsEdition(QgsVectorLayerTools):
    """Outils d'édition minimaux : l'éditeur de tables liées en a besoin hors de l'application QGIS."""

    def addFeature(self, layer, defaultValues=None, defaultGeometry=None, parentWidget=None,
                   showModal=True, hideParent=False):
        return False, None

    def startEditing(self, layer):
        return layer.startEditing()

    def stopEditing(self, layer, allowCancel=True):
        return layer.commitChanges()

    def saveEdits(self, layer):
        return layer.commitChanges(False)

    def copyMoveFeatures(self, layer, request, dx=0, dy=0, errorMsg=None, topologicalEditing=False,
                         topologicalLayer=None, childrenInfoMsg=None):
        return False


canevas = QgsMapCanvas()
outils = OutilsEdition()

travail = Path(tempfile.mkdtemp())
shutil.copytree(RACINE / "donnees" / "traite", travail / "donnees" / "traite",
                ignore=shutil.ignore_patterns("*.gdb"))
shutil.copy2(RACINE / "patrimoine_chambery.qgz", travail)
projet = QgsProject.instance()
projet.read(str(travail / "patrimoine_chambery.qgz"))
bat = projet.mapLayersByName("Bâtiments communaux")[0]
vis = projet.mapLayersByName("Visites de bâtiment")[0]

# Deux visites fictives du Théâtre Charles Dullin
vis.startEditing()
for d, etat, obs in [(QDate(2025, 10, 14), "BON", "Visite annuelle, rien à signaler."),
                     (QDate(2026, 9, 22), "MOY", "Infiltration en toiture côté cour, reprise à programmer.")]:
    f = QgsVectorLayerUtils.createFeature(vis, context=vis.createExpressionContext())
    for k, v in {"id_bien": "BAT-CE-0116", "date_visite": d, "etat": etat, "affectataire": "CUL",
                 "agent": "Agent de démonstration", "observations": obs,
                 "id_visite": f"VIS-BAT-CE-0116-{d.toString('yyyyMMdd')}",
                 "source": "Visite fictive (démonstration)"}.items():
        f[k] = v
    vis.addFeature(f)
assert vis.commitChanges(), vis.commitErrors()
print("visites fictives ajoutées dans la copie temporaire")


def formulaire(couche, entite, largeur, hauteur, ajout=False):
    contexte = QgsAttributeEditorContext()
    contexte.setMapCanvas(canevas)
    contexte.setVectorLayerTools(outils)
    if ajout:
        couche.startEditing()
    f = QgsAttributeForm(couche, entite, contexte)
    if ajout:
        f.setMode(QgsAttributeEditorContext.AddFeatureMode)
    f.resize(largeur, hauteur)
    f.show()
    return f


def capturer(f, cible, onglet=None):
    """Capture un formulaire ouvert, sur l'onglet demandé. Le formulaire n'est pas fermé :
    la fermeture d'un formulaire modifié ouvrirait une boîte de dialogue bloquante."""
    if onglet is not None:
        for tabs in f.findChildren(QTabWidget):
            for i in range(tabs.count()):
                if tabs.tabText(i) == onglet:
                    tabs.setCurrentIndex(i)
    for _ in range(40):  # laisser finir les chargements asynchrones (listes liées) : environ 2 s
        app.processEvents()
        time.sleep(0.05)
    f.grab().save(str(cible))
    print(f"{cible.name} : {f.width()}x{f.height()}")


# Nouvelle visite : état « Mauvais » avec une description trop courte, le contrôle se déclenche.
# La saisie se fait sur une copie indépendante de la couche (mêmes formulaire et contraintes) :
# passer en édition la couche rattachée à la fiche du bâtiment bloquerait l'éditeur de relation.
copie_visites = vis.clone()
nouvelle = QgsVectorLayerUtils.createFeature(copie_visites, context=copie_visites.createExpressionContext())
nouvelle["id_bien"] = "BAT-CE-0116"
nouvelle["etat"] = "MAU"
nouvelle["observations"] = "Fissure"
saisie = formulaire(copie_visites, nouvelle, 820, 440, ajout=True)
capturer(saisie, CAPTURES / "formulaire_visite_visite.png", "Visite")
capturer(saisie, CAPTURES / "formulaire_visite_controle.png", "Constat")
saisie.hide()
copie_visites.rollBack()

theatre = next(bat.getFeatures("\"id_bien\" = 'BAT-CE-0116'"))
fiche = formulaire(bat, theatre, 760, 560)
for onglet in ["Identification", "Gestion", "Locaux", "Visites"]:
    capturer(fiche, CAPTURES / f"formulaire_batiment_{onglet.lower()}.png", onglet)
fiche.hide()

# Captures web en dernier : lancées avant, elles bloquaient l'éditeur de relation des formulaires
SANS_WEB = os.environ.get("CAPTURES_SANS_WEB") == "1"  # pour ne refaire que les formulaires
gestionnaire = functools.partial(Silencieux, directory=str(RACINE))
serveur = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), gestionnaire)
threading.Thread(target=serveur.serve_forever, daemon=True).start()
page = f"http://127.0.0.1:{PORT}/sorties/tableau_de_bord.html"
for nom, url, l, h in [] if SANS_WEB else [
    ("tableau_de_bord_haut", page, 1440, 1000),
    ("tableau_de_bord_page", page, 1440, 3300),
    ("vue_chantier", page + "?vue=chantier", 1440, 1600),
    ("vue_terrasses", page + "?vue=terrasses", 1440, 1600),
]:
    cible = CAPTURES / f"{nom}.png"
    capture_page(url, cible, l, h)
    if nom.endswith("_page"):
        rogner_bas(cible)
    if nom.startswith("vue_"):  # recadrage sur la carte et le panneau latéral (mise en page à 1440 px)
        Image.open(cible).crop((60, 690, 1380, 1460)).save(cible)
    print(f"{cible.name} : {Image.open(cible).size}")
serveur.shutdown()

print("Captures dans", CAPTURES)
# QGIS plante à la fermeture quand des formulaires graphiques ont été créés hors de l'application :
# les images sont écrites, on quitte donc sans passer par exitQgis()
sys.stdout.flush()
os._exit(0)
