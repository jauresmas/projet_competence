# Contrôle et intégration d'un plan de récolement

Chantier : réaménagement de la rue Croix d'Or (**fictif**, document de démonstration).  
Fichier reçu : `recolement_croix_d_or_geometre.dxf`. Contrôle du 30/09/2026.

## Synthèse

- Système de coordonnées détecté : EPSG:2154, transformé en RGF93 CC45 (EPSG:3945).
- Objets reçus : 30 ; intégrés : 25 ; archivés dans la base : 29.
- Anomalies : 1 « Bloquant corrigé », 4 « À reprendre », 4 « Information », 1 « Corrigé », 1 « À compléter ».
- Fichier produit : `base_topo_secteur_croix_d_or_maj.dxf` (l'original est conservé).

## Inventaire du fichier reçu

| Calque du prestataire | Objets | Calque Ville |
|---|---:|---|
| 0 | 2 | CTL_A_QUALIFIER |
| ARBRES | 6 | VEG_ARBRE |
| AVALOIRS | 7 | ASS_AVALOIR |
| BORDURE | 3 | VOI_BORDURE |
| CANDELABRE | 6 | ECL_CANDELABRE |
| CARTOUCHE | 1 | non intégré |
| COTATION | 3 | non intégré |
| EMPRISE_CHANTIER | 1 | REC_EMPRISE |
| MOBILIER_DIVERS | 1 | CTL_A_QUALIFIER |

## Anomalies

| Code | Gravité | Calque | Objet | Constat | Action | X (CC45) | Y (CC45) |
|---|---|---|---|---|---|---:|---:|
| C01 | Bloquant corrigé | tous | fichier | Plan livré en EPSG:2154 (Lambert 93) au lieu de CC45 | Transformation EPSG:2154 vers EPSG:3945 (pyproj) |  |  |
| C02 | À reprendre | 0 | polyligne | Objet sur le calque 0 : nature inconnue | Placé sur CTL_A_QUALIFIER, demande de précision au géomètre | 1928105.83 | 4266830.93 |
| C02 | À reprendre | 0 | polyligne | Objet sur le calque 0 : nature inconnue | Placé sur CTL_A_QUALIFIER, demande de précision au géomètre | 1928079.7 | 4266813.5 |
| C03 | À reprendre | MOBILIER_DIVERS | polyligne | Calque « MOBILIER_DIVERS » absent de la charte | Placé sur CTL_A_QUALIFIER | 1928130.85 | 4266843.1 |
| C04 | Information | CARTOUCHE, COTATION | 4 objets | Habillage du prestataire (cotations, cartouche) | Non intégré |  |  |
| C05 | Corrigé | CANDELABRE | LAMP CD-N01 | Bloc en double (même position à moins de 5 cm) | Doublon supprimé | 1928222.32 | 4266890.26 |
| C06 | À reprendre | ARBRES | TREE | Objet à 850 m de l'emprise du chantier (erreur de saisie probable) | Placé sur CTL_A_QUALIFIER, non intégré | 1929079.11 | 4266812.93 |
| C07 | À compléter | CANDELABRE | CANDELABRE CD-N03 | Attribut obligatoire HAUTEUR vide | Intégré et signalé sur CTL_A_QUALIFIER | 1928188.01 | 4266869.79 |
| C09 | Information | BORDURE | bordure | Raccord avec la bordure existante : écart de 1.40 m | À contrôler (la bordure existante est reconstituée) | 1928228.94 | 4266894.76 |
| C09 | Information | BORDURE | bordure | Raccord avec la bordure existante : écart de 1.40 m | À contrôler (la bordure existante est reconstituée) | 1928226.24 | 4266899.2 |
| C10 | Information | blocs | 19 blocs | Altitudes présentes dans les points d'insertion | Base planimétrique : objets ramenés à Z = 0 |  |  |

## Demande de reprise au prestataire

1. Livrer les plans en RGF93 CC45, système de la Ville (le Lambert 93 a été transformé cette fois).
2. Préciser la nature des objets posés sur le calque 0 et sur les calques hors charte.
3. Corriger la position de l'arbre saisi hors emprise.
4. Compléter les attributs obligatoires manquants (hauteur des candélabres).
5. Utiliser les calques et blocs de la charte (table de correspondance jointe).

![Avant / après](../sorties/recolement_avant_apres.png)
