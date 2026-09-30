# Procédure AutoCAD : intégrer un plan de récolement dans la base topographique

Procédure de référence pour AutoCAD (ou AutoCAD Map 3D pour l'étape du système de coordonnées).
Les commandes sont données sous leur **nom international préfixé par `_`**, qui fonctionne dans
toutes les langues d'AutoCAD. Chaque étape correspond à un contrôle automatisé du script
`09_integration_recolement.py` (codes C01 à C10 du rapport de contrôle).

Fichiers : `donnees/topo/recolement_croix_d_or_geometre.dxf` (livraison du géomètre, fictive),
`donnees/topo/base_topo_secteur_croix_d_or.dxf` (base de la Ville), `donnees/autocad/charte_ville_normes.dxf`.

## 0. Préparer le fichier de normes (une seule fois)

1. Convertir `charte_ville_normes.dxf` en DWG (DWG TrueView : *DWG Convert*, ou AutoCAD : `_SAVEAS`).
2. Renommer le DWG obtenu en `charte_ville_normes.dws`. Un fichier de normes AutoCAD est un DWG
   qui ne contient que les calques, types de ligne, styles et blocs de référence.

## 1. Contrôler le fichier reçu

| Étape | Commande | Ce qu'on vérifie | Contrôle Python |
|---|---|---|---|
| Ouvrir le récolement, repérer l'emprise | `_OPEN`, `_ZOOM` puis `_E` (étendue) | Un objet très éloigné signale une erreur de saisie | C06 |
| Lire les coordonnées | `_ID` sur un point | X ≈ 940 000 : Lambert 93 ; X ≈ 1 928 000 : CC45 | C01 |
| Associer la charte | `_STANDARDS`, ajouter `charte_ville_normes.dws` | | |
| Vérifier les normes | `_CHECKSTANDARDS` | Calques, types de ligne, styles absents de la charte | C03 |
| Objets sur le calque 0 | `_QSELECT` (Calque = 0) | Objets sans nature | C02 |
| Attributs des blocs | `_ATTEDIT` ou `_DATAEXTRACTION` | Hauteur de candélabre, essence d'arbre renseignées | C07 |

## 2. Mettre en cohérence

| Étape | Commande | Action | Contrôle Python |
|---|---|---|---|
| Système de coordonnées (Map 3D) | `_MAPCSASSIGN` (RGF93.LAMB93), puis attacher dans un dessin en `RGF93.CC45` | Reprojection Lambert 93 vers CC45 | C01 |
| Traduire les calques | `_LAYTRANS`, charger la charte, associer selon la table ci-dessous | Calques du prestataire renommés | C03 |
| Remplacer les blocs | `_-INSERT` avec `=` (redéfinition) ou `_BLOCKREPLACE` (Express Tools) | Blocs LAMP, TREE, AVAL remplacés par les blocs de la charte | |
| Supprimer les doublons | `_OVERKILL` | Candélabre saisi deux fois | C05 |
| Écarter l'habillage | `_LAYFRZ` sur COTATION et CARTOUCHE, puis suppression | Non intégrés | C04 |
| Nettoyer | `_AUDIT` (corriger : Oui), `_-PURGE` (Tout) | Fichier sain et léger | |

## 3. Intégrer dans la base

| Étape | Commande | Action |
|---|---|---|
| Archiver l'existant du chantier | `_SELECT` dans l'emprise, `_LAYMCH` vers `ARC_OBJET_REMPLACE`, puis `_LAYFRZ` | Historique conservé, calque gelé |
| Insérer le récolement | `_XATTACH` puis `_XREF` > *Lier* (`_BIND`), ou copier-coller avec coordonnées d'origine (`_PASTEORIG`) | Objets à leur position réelle |
| Contrôler les raccords | `_DIST` entre bordures neuves et existantes | Écart signalé au géomètre si > 0,50 m (C09) |
| Extraire l'inventaire | `_DATAEXTRACTION` | Tableau des candélabres, arbres, avaloirs |
| Mettre en page | Présentation avec cartouche, `_PLOT` vers PDF | Plan de récolement intégré |

## Table de correspondance (à saisir dans `_LAYTRANS`)

| Calque du prestataire | Calque de la Ville |
|---|---|
| BORDURE | VOI_BORDURE |
| CANDELABRE | ECL_CANDELABRE |
| ARBRES | VEG_ARBRE |
| AVALOIRS | ASS_AVALOIR |
| EMPRISE_CHANTIER | REC_EMPRISE |
| COTATION | non intégré (habillage) |
| CARTOUCHE | non intégré (habillage) |
| 0, MOBILIER_DIVERS | CTL_A_QUALIFIER (demande de précision au géomètre) |

| Bloc du prestataire | Bloc de la Ville | Attributs |
|---|---|---|
| LAMP | CANDELABRE | NUM → NUMERO, HT → HAUTEUR |
| TREE | ARBRE | ESS → ESSENCE, CIRC → CIRCONFERENCE |
| AVAL | AVALOIR | aucun |

## Calques de la charte

| Calque | Couleur (ACI) | Type de ligne | Contenu |
|---|---:|---|---|
| BAT_BATI | 8 | CONTINUOUS | Emprise du bâti |
| CAD_LIMITE | 94 | CONTINUOUS | Limite parcellaire (cadastre) |
| VOI_AXE | 1 | DASHDOT | Axe de voirie |
| VOI_BORDURE | 7 | CONTINUOUS | Bordure de trottoir |
| ASS_AVALOIR | 5 | CONTINUOUS | Avaloir d'eaux pluviales (bloc AVALOIR) |
| ECL_CANDELABRE | 2 | CONTINUOUS | Candélabre d'éclairage public (bloc CANDELABRE) |
| VEG_ARBRE | 3 | CONTINUOUS | Arbre d'alignement (bloc ARBRE) |
| TXT_VOIE | 7 | CONTINUOUS | Nom de voie |
| TXT_ADRESSE | 8 | CONTINUOUS | Numéro d'adresse |
| REC_EMPRISE | 6 | DASHED | Emprise des récolements intégrés |
| CTL_A_QUALIFIER | 1 | CONTINUOUS | Objet de récolement à qualifier (contrôle) |
| ARC_OBJET_REMPLACE | 9 | CONTINUOUS | Objet remplacé par un récolement (archive, gelé) |

Même démarche automatisée : `modeles/integration_recolement.model3` (modèle graphique QGIS) et `scripts/09_integration_recolement.py` (contrôles complets et rapport).
