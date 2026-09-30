"""
regles_attributaires.py  (ArcGIS Pro, ArcPy)

NON TESTÉ SOUS ARCGIS PRO : écrit sans licence ArcGIS disponible, à valider avant usage.

Installe dans patrimoine_chambery.gdb les règles attributaires (Arcade) équivalentes aux
formulaires du projet QGIS (scripts/formulaires.py) :

  - règles de calcul : emprise, surface de plancher estimée, quartier, parcelle, date de
    mise à jour, surface des terrasses, identifiant de visite ;
  - règles de contrainte : format des identifiants, cohérence des dates, arrêté obligatoire,
    description des désordres, état constaté lors d'une visite.

Lancement : fenêtre Python d'ArcGIS Pro, ou « propy regles_attributaires.py »
"""
from pathlib import Path

import arcpy

GDB = str(Path(__file__).resolve().parents[2] / "donnees" / "traite" / "patrimoine_chambery.gdb")
arcpy.env.workspace = GDB


def calcul(table, nom, champ, arcade, evenements="INSERT;UPDATE", description=""):
    arcpy.management.AddAttributeRule(
        in_table=table, name=nom, type="CALCULATION", script_expression=arcade,
        is_editable="EDITABLE", triggering_events=evenements, field=champ, description=description)
    print(f"  calcul    {table}.{champ} : {nom}")


def contrainte(table, nom, arcade, code, message, evenements="INSERT;UPDATE"):
    arcpy.management.AddAttributeRule(
        in_table=table, name=nom, type="CONSTRAINT", script_expression=arcade,
        is_editable="EDITABLE", triggering_events=evenements, error_code=code, error_message=message)
    print(f"  contrainte {table} : {nom}")


# ---------------------------------------------------------------- Bâtiments
calcul("batiment_communal", "Emprise calculée", "emprise_m2",
       "Round(Area($feature, 'square-meters'), 1)")
calcul("batiment_communal", "Surface de plancher estimée", "sdp_estimee_m2", """
if (IsEmpty($feature.nb_etages)) { return null }
return Round(Area($feature, 'square-meters') * $feature.nb_etages, 0)""")
calcul("batiment_communal", "Quartier par position", "quartier", """
var q = First(Intersects(FeatureSetByName($datastore, 'quartier', ['code'], true), Centroid($feature)))
return IIf(IsEmpty(q), 'NC', q.code)""")
calcul("batiment_communal", "Parcelle par position", "idu_parcelle", """
var p = First(Intersects(FeatureSetByName($datastore, 'parcelle_communale', ['idu'], true), Centroid($feature)))
return IIf(IsEmpty(p), $feature.idu_parcelle, p.idu)""")
calcul("batiment_communal", "Date de mise à jour", "date_maj", "Today()")
contrainte("batiment_communal", "Format de l'identifiant GMAO", """
var id = $feature.id_bien
if (IsEmpty(id) || Count(id) != 11) { return false }
var q = Mid(id, 4, 2)
return Left(id, 4) == 'BAT-' && Mid(id, 6, 1) == '-' && Upper(q) == q
       && !IsNan(Number(Right(id, 4)))""", 1001,
           "Format attendu : BAT-<code quartier>-<4 chiffres>, identique dans la GMAO")
contrainte("batiment_communal", "Nombre de niveaux plausible", """
var n = $feature.nb_etages
return IsEmpty(n) || (n >= 0 && n <= 30)""", 1002, "Nombre de niveaux compris entre 0 et 30")

# ---------------------------------------------------------------- Visites
calcul("visite_batiment", "Identifiant de visite", "id_visite", """
var d = IIf(IsEmpty($feature.date_visite), Today(), $feature.date_visite)
return 'VIS-' + $feature.id_bien + '-' + Text(d, 'YYYYMMDD')""")
calcul("visite_batiment", "Date de mise à jour", "date_maj", "Today()")
contrainte("visite_batiment", "Date de visite passée", """
return !IsEmpty($feature.date_visite) && $feature.date_visite <= Now()""", 2001,
           "La date de visite ne peut pas être dans le futur")
contrainte("visite_batiment", "État constaté", """
return !IsEmpty($feature.etat) && $feature.etat != 'NR'""", 2002, "Une visite doit constater un état")
contrainte("visite_batiment", "Désordres décrits", """
if (!Includes(['MAU', 'TMA'], $feature.etat)) { return true }
return !IsEmpty($feature.observations) && Count($feature.observations) > 10""", 2003,
           "Décrire les désordres quand l'état est mauvais ou très mauvais")
contrainte("visite_batiment", "Bâtiment existant", """
var b = Filter(FeatureSetByName($datastore, 'batiment_communal', ['id_bien'], false),
               'id_bien = @id', {'id': $feature.id_bien})
return Count(b) == 1""", 2004, "La visite doit porter sur un bâtiment de la base")

# ---------------------------------------------------------------- Terrasses et étals
calcul("occupation_domaine_public", "Surface calculée", "surface_m2",
       "Round(Area($feature, 'square-meters'), 1)")
calcul("occupation_domaine_public", "Voie la plus proche", "id_voie", """
var voies = FeatureSetByName($datastore, 'voie', ['id_voie'], true)
var proches = Intersects(voies, Buffer($feature, 15, 'meters'))
var meilleure = null; var dmin = Infinity
for (var v in proches) { var d = Distance($feature, v, 'meters'); if (d < dmin) { dmin = d; meilleure = v.id_voie } }
return IIf(IsEmpty(meilleure), $feature.id_voie, meilleure)""")
contrainte("occupation_domaine_public", "Format de l'identifiant", """
var id = $feature.id_occupation
return !IsEmpty(id) && Count(id) == 12 && Left(id, 4) == 'OCC-'
       && !IsNan(Number(Mid(id, 4, 4))) && !IsNan(Number(Right(id, 3)))""", 3001,
           "Format attendu : OCC-<année>-<3 chiffres>")
contrainte("occupation_domaine_public", "Période cohérente", """
return IsEmpty($feature.date_debut) || IsEmpty($feature.date_fin) || $feature.date_fin > $feature.date_debut""",
           3002, "La fin doit être postérieure au début")
contrainte("occupation_domaine_public", "Arrêté obligatoire", """
return $feature.statut != 'AUT' || !IsEmpty($feature.num_arrete)""", 3003,
           "Une terrasse autorisée doit porter un numéro d'arrêté")

print("Règles attributaires installées dans", GDB)
