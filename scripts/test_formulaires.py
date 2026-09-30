"""
test_formulaires.py
Vérifie les formulaires du projet QGIS : valeurs par défaut calculées et contraintes
(saisies volontairement fausses qui doivent être refusées).
Lancement : python-qgis-ltr.bat test_formulaires.py
"""
from pathlib import Path
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayerUtils, QgsFeature, QgsFieldConstraints,
                       QgsExpressionContextUtils, QgsGeometry)
from qgis.PyQt.QtCore import QDate
app = QgsApplication([], False); app.initQgis()
R = Path(__file__).resolve().parents[1]
p = QgsProject.instance(); print("lecture projet :", p.read(str(R / "patrimoine_chambery.qgz")))
L = {l.name(): l for l in p.mapLayers().values()}
print("relations :", [r.id() for r in p.relationManager().relations().values()])
vis, bat, occ = L["Visites de bâtiment"], L["Bâtiments communaux"], L["Terrasses et étals"]

def erreurs(lyr, f):
    out = []
    for i, fld in enumerate(lyr.fields()):
        ok, errs = QgsVectorLayerUtils.validateAttribute(lyr, f, i, QgsFieldConstraints.ConstraintStrengthHard)
        if not ok: out.append(fld.name())
    return out

# 1. Visite : valeurs par défaut
ctx = vis.createExpressionContext()
f = QgsVectorLayerUtils.createFeature(vis, QgsGeometry(), {vis.fields().indexOf("id_bien"): "BAT-CE-0116"}, ctx)
print("visite par défaut :", {k: f[k] for k in ["id_visite", "date_visite", "source"]})
print("  erreurs (état vide) :", erreurs(vis, f))
f["etat"] = "MAU"; f["observations"] = "fissure"
print("  erreurs (mauvais état, observation trop courte) :", erreurs(vis, f))
f["observations"] = "Fissures en façade nord, reprise d'enduit à prévoir"; f["date_visite"] = QDate(2030, 1, 1)
print("  erreurs (date future) :", erreurs(vis, f))
f["date_visite"] = QDate.currentDate()
print("  erreurs (saisie correcte) :", erreurs(vis, f))

# 2. Bâtiment : identifiant, emprise et quartier calculés
b = next(bat.getFeatures("\"id_bien\" = 'BAT-CE-0116'"))
ctxb = bat.createExpressionContext(); ctxb.setFeature(b)
print("bâtiment : emprise calculée", bat.defaultValue(bat.fields().indexOf("emprise_m2"), b, ctxb),
      "| quartier", bat.defaultValue(bat.fields().indexOf("quartier"), b, ctxb),
      "| parcelle", bat.defaultValue(bat.fields().indexOf("idu_parcelle"), b, ctxb))
b["id_bien"] = "BAT-CE-116"; print("  erreurs (identifiant mal formé) :", erreurs(bat, b))
print("  champ virtuel état à la dernière visite :", next(bat.getFeatures("\"id_bien\" = 'BAT-CE-0116'"))["etat_derniere_visite"])
print("  actions :", [a.name() for a in bat.actions().actions()])

# 3. Terrasse autorisée sans arrêté, dates inversées
t = next(occ.getFeatures()); t["num_arrete"] = None; t["statut"] = "AUT"; t["date_fin"] = QDate(2026, 1, 1)
print("terrasse : erreurs", erreurs(occ, t))
print("onglets bâtiment :", [c.name() for c in bat.editFormConfig().tabs()])
app.exitQgis()
