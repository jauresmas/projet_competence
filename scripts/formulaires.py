"""
formulaires.py
Formulaires de saisie du projet QGIS : l'équivalent des règles attributaires et des
formulaires d'ArcGIS Pro, utilisable aussi sur le terrain avec QField.

  - listes déroulantes issues des domaines de valeurs ;
  - contraintes (bloquantes ou d'avertissement) écrites en expressions ;
  - valeurs par défaut calculées (surface, quartier, parcelle, voie, dates) ;
  - champs en lecture seule pour les données de référence (IGN, DGFiP) ;
  - formulaires à onglets, avec les tables liées (locaux, visites) ;
  - champ virtuel « état à la dernière visite » et action « ouvrir la fiche PDF ».
"""
from qgis.core import (Qgis, QgsAction, QgsAttributeEditorContainer, QgsAttributeEditorField,
                       QgsAttributeEditorRelation, QgsDefaultValue, QgsEditFormConfig,
                       QgsEditorWidgetSetup, QgsField, QgsFieldConstraints)
from qgis.PyQt.QtCore import QVariant

from schema import COUCHES, DOMAINES

DUR = QgsFieldConstraints.ConstraintStrengthHard
SOUPLE = QgsFieldConstraints.ConstraintStrengthSoft


def _idx(lyr, champ):
    i = lyr.fields().indexOf(champ)
    assert i >= 0, f"{lyr.name()} : champ {champ} absent"
    return i


def liste(lyr, champ, domaine):
    valeurs = [{libelle: code} for code, libelle in DOMAINES[domaine][1].items()]
    lyr.setEditorWidgetSetup(_idx(lyr, champ), QgsEditorWidgetSetup("ValueMap", {"map": valeurs}))


def date(lyr, champ):
    lyr.setEditorWidgetSetup(_idx(lyr, champ), QgsEditorWidgetSetup("DateTime", {
        "display_format": "dd/MM/yyyy", "field_format": "yyyy-MM-dd", "calendar_popup": True,
        "allow_null": True, "field_iso_format": False}))


def contrainte(lyr, champ, expression, message, force=DUR):
    i = _idx(lyr, champ)
    lyr.setConstraintExpression(i, expression, message)
    lyr.setFieldConstraint(i, QgsFieldConstraints.ConstraintExpression, force)


def obligatoire(lyr, champ, force=DUR):
    lyr.setFieldConstraint(_idx(lyr, champ), QgsFieldConstraints.ConstraintNotNull, force)


def unique(lyr, champ):
    lyr.setFieldConstraint(_idx(lyr, champ), QgsFieldConstraints.ConstraintUnique, DUR)


def defaut(lyr, champ, expression, a_la_modification=False):
    lyr.setDefaultValueDefinition(_idx(lyr, champ), QgsDefaultValue(expression, a_la_modification))


def lecture_seule(lyr, *champs):
    fc = lyr.editFormConfig()
    for champ in champs:
        fc.setReadOnly(_idx(lyr, champ), True)
    lyr.setEditFormConfig(fc)


def onglets(lyr, structure, relations=None):
    """structure : [(titre d'onglet, [champs] ou objet relation)]"""
    fc = lyr.editFormConfig()
    fc.setLayout(QgsEditFormConfig.TabLayout)
    racine = fc.invisibleRootContainer()
    racine.clear()
    for titre, contenu in structure:
        onglet = QgsAttributeEditorContainer(titre, racine)
        onglet.setType(Qgis.AttributeEditorContainerType.Tab)  # onglet, et non bloc empilé
        if isinstance(contenu, str):  # identifiant de relation
            onglet.addChildElement(QgsAttributeEditorRelation(relations[contenu], onglet))
        else:
            for champ in contenu:
                onglet.addChildElement(QgsAttributeEditorField(champ, _idx(lyr, champ), onglet))
        racine.addChildElement(onglet)
    lyr.setEditFormConfig(fc)


def configurer(couches, relations):
    """couches : {nom de table: QgsVectorLayer} ; relations : {id: QgsRelation}"""
    bat = couches["batiment_communal"]
    loc = couches["local_communal"]
    vis = couches["visite_batiment"]
    occ = couches["occupation_domaine_public"]
    id_quartiers = couches["quartier"].id()
    id_parcelles = couches["parcelle_communale"].id()
    id_voies = couches["voie"].id()

    # ---------------- Bâtiments communaux ----------------
    liste(bat, "type_bien", "dom_type_bien")
    liste(bat, "etat", "dom_etat")
    liste(bat, "affectataire", "dom_affectataire")
    date(bat, "date_maj")
    unique(bat, "id_bien")
    contrainte(bat, "id_bien", "regexp_match(\"id_bien\", '^BAT-[A-Z]{2}-[0-9]{4}$')",
               "Format attendu : BAT-<code quartier>-<4 chiffres>, identique dans la GMAO")
    obligatoire(bat, "type_bien")
    obligatoire(bat, "nom", SOUPLE)
    contrainte(bat, "nb_etages", "\"nb_etages\" IS NULL OR \"nb_etages\" BETWEEN 0 AND 30",
               "Nombre de niveaux compris entre 0 et 30")
    defaut(bat, "emprise_m2", "round($area, 1)", True)
    defaut(bat, "sdp_estimee_m2", "round(\"emprise_m2\" * \"nb_etages\")", True)
    defaut(bat, "quartier", f"array_first(overlay_within('{id_quartiers}', \"code\"))", True)
    defaut(bat, "idu_parcelle", f"array_first(overlay_intersects('{id_parcelles}', \"idu\", "
                                "sort_by_intersection_size:='des'))", True)
    defaut(bat, "etat", "'NR'")
    defaut(bat, "affectataire", "'NR'")
    defaut(bat, "source", "'Saisie service patrimoine'")
    defaut(bat, "date_maj", "now()", True)
    lecture_seule(bat, "emprise_m2", "sdp_estimee_m2", "quartier", "idu_parcelle", "nb_locaux",
                  "id_rnb", "cleabs", "usage_bdtopo", "source", "date_maj")

    # Champ virtuel : état constaté à la dernière visite (sinon état de la fiche)
    derniere = ("array_last(relation_aggregate('rel_batiment_visites', 'array_agg', \"etat\", "
                "order_by:=\"date_visite\"))")
    etats = ", ".join(f"'{k}', '{v}'" for k, v in DOMAINES["dom_etat"][1].items())
    bat.addExpressionField(f"map_get(map({etats}), coalesce({derniere}, \"etat\"))",
                           QgsField("etat_derniere_visite", QVariant.String))
    bat.setFieldAlias(_idx(bat, "etat_derniere_visite"), "État à la dernière visite")

    onglets(bat, [
        ("Identification", ["id_bien", "nom", "type_bien", "adresse", "quartier", "idu_parcelle"]),
        ("Caractéristiques", ["emprise_m2", "nb_etages", "hauteur_m", "sdp_estimee_m2",
                              "usage_bdtopo", "nb_locaux"]),
        ("Gestion", ["etat", "etat_derniere_visite", "affectataire", "id_rnb", "cleabs",
                     "source", "date_maj"]),
        ("Locaux", "rel_batiment_locaux"),
        ("Visites", "rel_batiment_visites"),
    ], relations)
    bat.setDisplayExpression("coalesce(\"nom\", 'Bâtiment ' || \"id_bien\")")

    action = QgsAction(QgsAction.OpenUrl, "Ouvrir la fiche PDF",
                       "[% @project_folder %]/sorties/fiches/[% \"id_bien\" %].pdf")
    action.setActionScopes({"Feature", "Canvas"})
    bat.actions().addAction(action)

    # ---------------- Visites de bâtiment (formulaire terrain) ----------------
    vis.setEditorWidgetSetup(_idx(vis, "id_bien"), QgsEditorWidgetSetup("RelationReference", {
        "Relation": "rel_batiment_visites", "AllowNULL": False, "ShowForm": False,
        "MapIdentification": True, "ReadOnly": False, "OrderByValue": True}))
    liste(vis, "etat", "dom_etat")
    liste(vis, "affectataire", "dom_affectataire")
    date(vis, "date_visite")
    date(vis, "date_maj")
    vis.setEditorWidgetSetup(_idx(vis, "observations"), QgsEditorWidgetSetup("TextEdit", {"IsMultiline": True}))
    vis.setEditorWidgetSetup(_idx(vis, "photo"), QgsEditorWidgetSetup("ExternalResource", {
        "DocumentViewer": 1, "DocumentViewerHeight": 0, "DocumentViewerWidth": 0,
        "FileWidget": True, "FileWidgetButton": True, "RelativeStorage": 1, "StorageMode": 0,
        "DefaultRoot": "", "FileWidgetFilter": ""}))
    defaut(vis, "date_visite", "to_date(now())")
    defaut(vis, "id_visite", "'VIS-' || \"id_bien\" || '-' || "
                             "format_date(coalesce(\"date_visite\", now()), 'yyyyMMdd')", True)
    defaut(vis, "agent", "@user_full_name")
    defaut(vis, "source", "'Saisie terrain (QField)'")
    defaut(vis, "date_maj", "now()", True)
    obligatoire(vis, "id_bien")
    obligatoire(vis, "etat")
    obligatoire(vis, "date_visite")
    unique(vis, "id_visite")
    contrainte(vis, "date_visite", "\"date_visite\" <= now()", "La date de visite ne peut pas être dans le futur")
    contrainte(vis, "etat", "\"etat\" <> 'NR'", "Une visite doit constater un état")
    contrainte(vis, "observations", "coalesce(\"etat\", '') NOT IN ('MAU', 'TMA') OR length(\"observations\") > 10",
               "Décrire les désordres quand l'état est mauvais ou très mauvais")
    lecture_seule(vis, "id_visite", "source", "date_maj")
    onglets(vis, [
        ("Visite", ["id_bien", "date_visite", "agent", "etat", "affectataire"]),
        ("Constat", ["observations", "photo"]),
        ("Suivi", ["id_visite", "source", "date_maj"]),
    ])
    vis.setDisplayExpression("\"id_visite\"")

    # ---------------- Locaux (référence DGFiP, consultation) ----------------
    loc.setReadOnly(True)
    loc.setDisplayExpression("\"id_local\" || ' (bât. ' || coalesce(\"batiment\", '?') || ', niv. ' || "
                             "coalesce(\"niveau\", '?') || ')'")

    # ---------------- Terrasses et étals ----------------
    liste(occ, "type_occupation", "dom_type_occupation")
    liste(occ, "statut", "dom_statut_autorisation")
    for champ in ("date_debut", "date_fin", "date_maj"):
        date(occ, champ)
    unique(occ, "id_occupation")
    contrainte(occ, "id_occupation", "regexp_match(\"id_occupation\", '^OCC-[0-9]{4}-[0-9]{3}$')",
               "Format attendu : OCC-<année>-<3 chiffres>")
    obligatoire(occ, "etablissement")
    obligatoire(occ, "type_occupation")
    contrainte(occ, "date_fin", "\"date_fin\" > \"date_debut\"", "La fin doit être postérieure au début")
    contrainte(occ, "num_arrete", "\"statut\" <> 'AUT' OR \"num_arrete\" IS NOT NULL",
               "Une terrasse autorisée doit porter un numéro d'arrêté")
    defaut(occ, "surface_m2", "round($area, 1)", True)
    defaut(occ, "id_voie", f"array_first(overlay_nearest('{id_voies}', \"id_voie\"))", True)
    defaut(occ, "statut", "'INS'")
    defaut(occ, "date_debut", "make_date(year(now()), 4, 1)")
    defaut(occ, "date_fin", "make_date(year(now()), 10, 31)")
    defaut(occ, "date_maj", "now()", True)
    lecture_seule(occ, "surface_m2", "id_voie", "date_maj")
    occ.setDisplayExpression("\"id_occupation\" || ' : ' || \"etablissement\"")

    # Alias identiques au modèle ; identifiant technique fid masqué dans les formulaires
    for nom, lyr in couches.items():
        if lyr.fields().indexOf("fid") >= 0:
            lyr.setEditorWidgetSetup(lyr.fields().indexOf("fid"), QgsEditorWidgetSetup("Hidden", {}))
        for champ, alias, *_ in COUCHES[nom]["champs"]:
            i = lyr.fields().indexOf(champ)
            if i >= 0:
                lyr.setFieldAlias(i, alias)
