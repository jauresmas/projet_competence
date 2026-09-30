"""
charte_topo.py
Charte graphique de la base topographique de la Ville (calques, couleurs, blocs)
et table de correspondance pour intégrer les plans de récolement des prestataires.
"""

SRID_VILLE = 3945  # RGF93 CC45

# calque : (couleur ACI, type de ligne, description)
CALQUES = {
    "BAT_BATI": (8, "CONTINUOUS", "Emprise du bâti"),
    "CAD_LIMITE": (94, "CONTINUOUS", "Limite parcellaire (cadastre)"),
    "VOI_AXE": (1, "DASHDOT", "Axe de voirie"),
    "VOI_BORDURE": (7, "CONTINUOUS", "Bordure de trottoir"),
    "ASS_AVALOIR": (5, "CONTINUOUS", "Avaloir d'eaux pluviales (bloc AVALOIR)"),
    "ECL_CANDELABRE": (2, "CONTINUOUS", "Candélabre d'éclairage public (bloc CANDELABRE)"),
    "VEG_ARBRE": (3, "CONTINUOUS", "Arbre d'alignement (bloc ARBRE)"),
    "TXT_VOIE": (7, "CONTINUOUS", "Nom de voie"),
    "TXT_ADRESSE": (8, "CONTINUOUS", "Numéro d'adresse"),
    "REC_EMPRISE": (6, "DASHED", "Emprise des récolements intégrés"),
    "CTL_A_QUALIFIER": (1, "CONTINUOUS", "Objet de récolement à qualifier (contrôle)"),
    "ARC_OBJET_REMPLACE": (9, "CONTINUOUS", "Objet remplacé par un récolement (archive, gelé)"),
}

# Blocs de la charte : nom -> liste d'attributs obligatoires
BLOCS = {
    "CANDELABRE": ["NUMERO", "HAUTEUR"],
    "ARBRE": ["ESSENCE", "CIRCONFERENCE"],
    "AVALOIR": [],
}

# Correspondance calques du prestataire -> calques de la Ville (None = non intégré)
CORRESPONDANCE_CALQUES = {
    "BORDURE": "VOI_BORDURE",
    "CANDELABRE": "ECL_CANDELABRE",
    "ARBRES": "VEG_ARBRE",
    "AVALOIRS": "ASS_AVALOIR",
    "EMPRISE_CHANTIER": "REC_EMPRISE",
    "COTATION": None,  # habillage du prestataire, sans valeur topographique
    "CARTOUCHE": None,
}

# Correspondance des étiquettes d'attributs de blocs
CORRESPONDANCE_ATTRIBUTS = {
    "NUM": "NUMERO", "HT": "HAUTEUR", "ESS": "ESSENCE", "CIRC": "CIRCONFERENCE",
}

# Correspondance blocs du prestataire -> blocs de la Ville
CORRESPONDANCE_BLOCS = {
    "LAMP": "CANDELABRE",
    "TREE": "ARBRE",
    "AVAL": "AVALOIR",
}

# Calques remplacés par un récolement dans son emprise
CALQUES_REMPLACABLES = ["VOI_BORDURE", "ECL_CANDELABRE", "VEG_ARBRE", "ASS_AVALOIR"]


def creer_calques_et_blocs(doc):
    """Déclare les calques, types de ligne et blocs de la charte dans un document ezdxf."""
    for lt in ["DASHDOT", "DASHED"]:
        if lt not in doc.linetypes:
            motif = [1.2, 0.8, -0.2, 0.0, -0.2] if lt == "DASHDOT" else [1.0, 0.6, -0.4]
            doc.linetypes.add(lt, pattern=motif, description=lt)
    for nom, (couleur, lt, desc) in CALQUES.items():
        if nom not in doc.layers:
            lay = doc.layers.add(nom, color=couleur, linetype=lt)
            lay.description = desc
    if "CANDELABRE" not in doc.blocks:
        b = doc.blocks.new("CANDELABRE")
        b.add_circle((0, 0), 0.25)
        b.add_line((-0.4, 0), (0.4, 0))
        b.add_line((0, -0.4), (0, 0.4))
        b.add_attdef("NUMERO", (0.35, 0.15), dxfattribs={"height": 0.25})
        b.add_attdef("HAUTEUR", (0.35, -0.25), dxfattribs={"height": 0.2})
    if "ARBRE" not in doc.blocks:
        b = doc.blocks.new("ARBRE")
        b.add_circle((0, 0), 1.5)
        b.add_circle((0, 0), 0.15)
        b.add_attdef("ESSENCE", (1.6, 0.1), dxfattribs={"height": 0.25})
        b.add_attdef("CIRCONFERENCE", (1.6, -0.3), dxfattribs={"height": 0.2})
    if "AVALOIR" not in doc.blocks:
        b = doc.blocks.new("AVALOIR")
        b.add_lwpolyline([(-0.35, -0.2), (0.35, -0.2), (0.35, 0.2), (-0.35, 0.2)], close=True)
        b.add_line((-0.35, -0.2), (0.35, 0.2))
