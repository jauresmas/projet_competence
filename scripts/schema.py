"""
schema.py
Modèle de données du SIG Patrimoine : domaines de valeurs et classes d'entités.
Ce fichier est la seule source de vérité : la géodatabase, le GeoPackage et le
dictionnaire de données sont générés à partir de lui.
"""

SRID = 3945  # RGF93 v1 / CC45, système des données de la Ville de Chambéry

# --------------------------------------------------------------------------
# Domaines de valeurs (listes codées)
# --------------------------------------------------------------------------
DOMAINES = {
    "dom_type_bien": ("Famille fonctionnelle du bien", {
        "ADM": "Administration",
        "ENS": "Enseignement et petite enfance",
        "SPO": "Sport",
        "CUL": "Culture et loisirs",
        "REL": "Édifice cultuel",
        "SAN": "Santé et action sociale",
        "TEC": "Technique et logistique",
        "COM": "Commerce et marché",
        "LOG": "Logement",
        "ANX": "Annexe",
        "AQU": "À qualifier",
    }),
    "dom_etat": ("État général constaté", {
        "BON": "Bon",
        "MOY": "Moyen",
        "MAU": "Mauvais",
        "TMA": "Très mauvais",
        "NR": "Non renseigné",
    }),
    "dom_affectataire": ("Service municipal affectataire", {
        "EDU": "Éducation",
        "SPO": "Sports",
        "CUL": "Culture",
        "TEC": "Services techniques",
        "ADM": "Administration générale",
        "SOC": "Action sociale (CCAS)",
        "TIE": "Mis à disposition d'un tiers",
        "NR": "Non renseigné",
    }),
    "dom_domanialite": ("Domanialité présumée de la voie", {
        "COM": "Communale",
        "DEP": "Départementale",
        "NAT": "Nationale",
        "AUT": "Autoroute concédée",
        "PRI": "Privée",
        "NR": "Non déterminée",
    }),
    "dom_sens": ("Sens de circulation", {
        "DOUBLE": "Double sens",
        "DIRECT": "Sens direct",
        "INVERSE": "Sens inverse",
        "SANS": "Sans objet",
    }),
    "dom_type_occupation": ("Type d'occupation du domaine public", {
        "TER_OUV": "Terrasse ouverte",
        "TER_FER": "Terrasse fermée",
        "ETAL_MAR": "Étal de marché",
        "ETAL_SAI": "Étal saisonnier",
        "AUTRE": "Autre occupation",
    }),
    "dom_statut_autorisation": ("Statut de l'autorisation", {
        "INS": "En instruction",
        "AUT": "Autorisée",
        "REF": "Refusée",
        "ECH": "Échue",
    }),
}

# --------------------------------------------------------------------------
# Classes d'entités : (nom, alias, type, largeur, domaine, description)
# Types : str, int, real, date
# --------------------------------------------------------------------------
_MAJ = [
    ("source", "Source", "str", 80, None, "Origine de la donnée"),
    ("date_maj", "Date de mise à jour", "date", None, None, "Dernière mise à jour de l'objet"),
]

COUCHES = {
    "batiment_communal": {
        "alias": "Bâtiments communaux",
        "geom": "MultiPolygon",
        "description": "Bâtiments BD TOPO situés à au moins 50 % sur une parcelle "
                       "de la commune de Chambéry (fichier DGFiP des personnes morales).",
        "champs": [
            ("id_bien", "Identifiant du bien", "str", 16, None,
             "Clé unique partagée avec la GMAO (AS-TECH) : BAT-<quartier>-<n°>"),
            ("nom", "Nom du bien", "str", 120, None, "Toponyme BD TOPO ou libellé à compléter"),
            ("type_bien", "Type de bien", "str", 3, "dom_type_bien", "Famille fonctionnelle"),
            ("quartier", "Quartier", "str", 2, None, "Code du quartier de la Ville"),
            ("adresse", "Adresse", "str", 120, None, "Adresse BAN rattachée à la parcelle"),
            ("idu_parcelle", "Parcelle cadastrale", "str", 14, None, "Identifiant unique de parcelle"),
            ("emprise_m2", "Emprise au sol (m²)", "real", None, None, "Surface calculée en CC45"),
            ("nb_etages", "Nombre d'étages", "int", None, None, "BD TOPO"),
            ("hauteur_m", "Hauteur (m)", "real", None, None, "BD TOPO"),
            ("sdp_estimee_m2", "Surface de plancher estimée (m²)", "real", None, None,
             "Emprise × nombre de niveaux, à confirmer par relevé"),
            ("usage_bdtopo", "Usage BD TOPO", "str", 40, None, "Usage principal selon l'IGN"),
            ("nb_locaux", "Nombre de locaux DGFiP", "int", None, None,
             "Locaux de la commune recensés sur la parcelle"),
            ("etat", "État général", "str", 3, "dom_etat", "À renseigner lors des visites"),
            ("affectataire", "Service affectataire", "str", 3, "dom_affectataire", "À renseigner"),
            ("id_rnb", "Identifiant(s) RNB", "str", 120, None, "Référentiel national des bâtiments"),
            ("cleabs", "Identifiant BD TOPO", "str", 24, None, "Lien vers la BD TOPO"),
        ] + _MAJ,
    },
    "parcelle_communale": {
        "alias": "Parcelles communales",
        "geom": "MultiPolygon",
        "description": "Parcelles cadastrales dont la commune de Chambéry est propriétaire.",
        "champs": [
            ("idu", "Identifiant parcelle", "str", 14, None, "INSEE + préfixe + section + numéro"),
            ("section", "Section", "str", 2, None, ""),
            ("numero", "Numéro", "str", 4, None, ""),
            ("contenance_m2", "Contenance (m²)", "int", None, None, "Surface cadastrale"),
            ("adresse", "Adresse DGFiP", "str", 120, None, "Adresse fiscale"),
            ("batie", "Parcelle bâtie", "int", None, None, "1 si des locaux communaux y sont recensés"),
            ("quartier", "Quartier", "str", 2, None, ""),
        ] + _MAJ,
    },
    "local_communal": {
        "alias": "Locaux communaux",
        "geom": None,
        "description": "Locaux (au sens fiscal) appartenant à la commune. Table liée "
                       "aux bâtiments par id_bien.",
        "champs": [
            ("id_local", "Identifiant du local", "str", 16, None, "LOC-<n°>"),
            ("id_bien", "Bâtiment de rattachement", "str", 16, None,
             "Bâtiment principal de la parcelle"),
            ("idu", "Parcelle", "str", 14, None, ""),
            ("batiment", "Lettre de bâtiment", "str", 4, None, "Codification DGFiP"),
            ("entree", "Entrée", "str", 4, None, ""),
            ("niveau", "Niveau", "str", 4, None, ""),
            ("porte", "Porte", "str", 6, None, ""),
            ("adresse", "Adresse", "str", 120, None, ""),
        ] + _MAJ,
    },
    "visite_batiment": {
        "alias": "Visites de bâtiment",
        "geom": None,
        "description": "Historique des visites de bâtiments (saisie terrain QField) : état constaté, "
                       "service affectataire, observations, photo. Table liée aux bâtiments par id_bien.",
        "champs": [
            ("id_visite", "Identifiant de la visite", "str", 24, None, "VIS-<id_bien>-<AAAAMMJJ>"),
            ("id_bien", "Bâtiment visité", "str", 16, None, "Lien vers batiment_communal"),
            ("date_visite", "Date de visite", "date", None, None, ""),
            ("agent", "Agent", "str", 60, None, "Personne ayant réalisé la visite"),
            ("etat", "État constaté", "str", 3, "dom_etat", ""),
            ("affectataire", "Service affectataire", "str", 3, "dom_affectataire", ""),
            ("observations", "Observations", "str", 250, None, "Désordres, travaux à prévoir"),
            ("photo", "Photo", "str", 250, None, "Chemin relatif de la photo prise sur le terrain"),
        ] + _MAJ,
    },
    "voie": {
        "alias": "Référentiel des voies",
        "geom": "MultiLineString",
        "description": "Voies nommées de la commune, alignées sur la Base Adresse Nationale.",
        "champs": [
            ("id_voie", "Identifiant voie BAN", "str", 20, None, "Code FANTOIR/BAN de la voie"),
            ("nom", "Nom de la voie", "str", 120, None, ""),
            ("type_voie", "Type de voie", "str", 30, None, "Rue, avenue, place..."),
            ("longueur_m", "Longueur (m)", "real", None, None, ""),
            ("quartier", "Quartier", "str", 2, None, ""),
        ] + _MAJ,
    },
    "troncon_voirie": {
        "alias": "Tronçons de voirie",
        "geom": "MultiLineString",
        "description": "Tronçons routiers BD TOPO sur la commune, rattachés au référentiel des voies.",
        "champs": [
            ("cleabs", "Identifiant BD TOPO", "str", 24, None, ""),
            ("id_voie", "Identifiant voie BAN", "str", 20, None, "Lien vers la couche voie"),
            ("nom", "Nom", "str", 120, None, ""),
            ("nature", "Nature", "str", 40, None, "BD TOPO"),
            ("domanialite", "Domanialité", "str", 3, "dom_domanialite", "Présumée à partir de la BD TOPO"),
            ("largeur_m", "Largeur de chaussée (m)", "real", None, None, ""),
            ("nb_voies", "Nombre de voies", "int", None, None, ""),
            ("sens", "Sens de circulation", "str", 7, "dom_sens", ""),
            ("longueur_m", "Longueur (m)", "real", None, None, ""),
        ] + _MAJ,
    },
    "occupation_domaine_public": {
        "alias": "Terrasses et étals",
        "geom": "MultiPolygon",
        "description": "Emprises autorisées d'occupation du domaine public (terrasses, étals).",
        "champs": [
            ("id_occupation", "Identifiant", "str", 16, None, "OCC-<année>-<n°>"),
            ("type_occupation", "Type d'occupation", "str", 8, "dom_type_occupation", ""),
            ("etablissement", "Établissement", "str", 120, None, "Enseigne"),
            ("adresse", "Adresse", "str", 120, None, ""),
            ("id_voie", "Voie", "str", 20, None, "Lien vers le référentiel des voies"),
            ("surface_m2", "Surface (m²)", "real", None, None, "Calculée"),
            ("statut", "Statut", "str", 3, "dom_statut_autorisation", ""),
            ("num_arrete", "N° d'arrêté", "str", 20, None, ""),
            ("date_debut", "Début d'autorisation", "date", None, None, ""),
            ("date_fin", "Fin d'autorisation", "date", None, None, ""),
        ] + _MAJ,
    },
    "equipement_public": {
        "alias": "Équipements et lieux d'intérêt",
        "geom": "MultiPolygon",
        "description": "Zones d'activité ou d'intérêt BD TOPO (écoles, équipements, places).",
        "champs": [
            ("cleabs", "Identifiant BD TOPO", "str", 24, None, ""),
            ("categorie", "Catégorie", "str", 40, None, ""),
            ("nature", "Nature", "str", 60, None, ""),
            ("nom", "Nom", "str", 120, None, ""),
        ] + _MAJ,
    },
    "quartier": {
        "alias": "Quartiers",
        "geom": "MultiPolygon",
        "description": "Quartiers de la Ville de Chambéry (open data Ville).",
        "champs": [
            ("code", "Code", "str", 2, None, ""),
            ("nom", "Nom du quartier", "str", 60, None, ""),
        ] + _MAJ,
    },
}

# --------------------------------------------------------------------------
# Relations 1-n : (nom, table parent, table enfant, clé, libellé aller, libellé retour)
# Classes de relations dans la géodatabase, relations de projet dans QGIS.
# --------------------------------------------------------------------------
RELATIONS = [
    ("rel_batiment_locaux", "batiment_communal", "local_communal", "id_bien",
     "contient", "est situé dans"),
    ("rel_batiment_visites", "batiment_communal", "visite_batiment", "id_bien",
     "a fait l'objet de", "concerne"),
]
