# Dictionnaire de données du SIG Patrimoine de Chambéry

Système de coordonnées : RGF93 / CC45 (EPSG:3945), celui des données de la Ville.
Formats livrés : géodatabase fichier (ArcGIS Pro) et GeoPackage (QGIS), générés par le même script.

## Classes d'entités

### Bâtiments communaux (`batiment_communal`)

Bâtiments BD TOPO situés à au moins 50 % sur une parcelle de la commune de Chambéry (fichier DGFiP des personnes morales). Géométrie : MultiPolygon. Objets : 603.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `id_bien` | Identifiant du bien | Texte (16) |  | Clé unique partagée avec la GMAO (AS-TECH) : BAT-<quartier>-<n°> |
| `nom` | Nom du bien | Texte (120) |  | Toponyme BD TOPO ou libellé à compléter |
| `type_bien` | Type de bien | Texte (3) | dom_type_bien | Famille fonctionnelle |
| `quartier` | Quartier | Texte (2) |  | Code du quartier de la Ville |
| `adresse` | Adresse | Texte (120) |  | Adresse BAN rattachée à la parcelle |
| `idu_parcelle` | Parcelle cadastrale | Texte (14) |  | Identifiant unique de parcelle |
| `emprise_m2` | Emprise au sol (m²) | Réel |  | Surface calculée en CC45 |
| `nb_etages` | Nombre d'étages | Entier |  | BD TOPO |
| `hauteur_m` | Hauteur (m) | Réel |  | BD TOPO |
| `sdp_estimee_m2` | Surface de plancher estimée (m²) | Réel |  | Emprise × nombre de niveaux, à confirmer par relevé |
| `usage_bdtopo` | Usage BD TOPO | Texte (40) |  | Usage principal selon l'IGN |
| `nb_locaux` | Nombre de locaux DGFiP | Entier |  | Locaux de la commune recensés sur la parcelle |
| `etat` | État général | Texte (3) | dom_etat | À renseigner lors des visites |
| `affectataire` | Service affectataire | Texte (3) | dom_affectataire | À renseigner |
| `id_rnb` | Identifiant(s) RNB | Texte (120) |  | Référentiel national des bâtiments |
| `cleabs` | Identifiant BD TOPO | Texte (24) |  | Lien vers la BD TOPO |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Parcelles communales (`parcelle_communale`)

Parcelles cadastrales dont la commune de Chambéry est propriétaire. Géométrie : MultiPolygon. Objets : 1948.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `idu` | Identifiant parcelle | Texte (14) |  | INSEE + préfixe + section + numéro |
| `section` | Section | Texte (2) |  |  |
| `numero` | Numéro | Texte (4) |  |  |
| `contenance_m2` | Contenance (m²) | Entier |  | Surface cadastrale |
| `adresse` | Adresse DGFiP | Texte (120) |  | Adresse fiscale |
| `batie` | Parcelle bâtie | Entier |  | 1 si des locaux communaux y sont recensés |
| `quartier` | Quartier | Texte (2) |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Locaux communaux (`local_communal`)

Locaux (au sens fiscal) appartenant à la commune. Table liée aux bâtiments par id_bien. Géométrie : aucune (table). Objets : 1066.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `id_local` | Identifiant du local | Texte (16) |  | LOC-<n°> |
| `id_bien` | Bâtiment de rattachement | Texte (16) |  | Bâtiment principal de la parcelle |
| `idu` | Parcelle | Texte (14) |  |  |
| `batiment` | Lettre de bâtiment | Texte (4) |  | Codification DGFiP |
| `entree` | Entrée | Texte (4) |  |  |
| `niveau` | Niveau | Texte (4) |  |  |
| `porte` | Porte | Texte (6) |  |  |
| `adresse` | Adresse | Texte (120) |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Référentiel des voies (`voie`)

Voies nommées de la commune, alignées sur la Base Adresse Nationale. Géométrie : MultiLineString. Objets : 782.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `id_voie` | Identifiant voie BAN | Texte (20) |  | Code FANTOIR/BAN de la voie |
| `nom` | Nom de la voie | Texte (120) |  |  |
| `type_voie` | Type de voie | Texte (30) |  | Rue, avenue, place... |
| `longueur_m` | Longueur (m) | Réel |  |  |
| `quartier` | Quartier | Texte (2) |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Tronçons de voirie (`troncon_voirie`)

Tronçons routiers BD TOPO sur la commune, rattachés au référentiel des voies. Géométrie : MultiLineString. Objets : 4873.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `cleabs` | Identifiant BD TOPO | Texte (24) |  |  |
| `id_voie` | Identifiant voie BAN | Texte (20) |  | Lien vers la couche voie |
| `nom` | Nom | Texte (120) |  |  |
| `nature` | Nature | Texte (40) |  | BD TOPO |
| `domanialite` | Domanialité | Texte (3) | dom_domanialite | Présumée à partir de la BD TOPO |
| `largeur_m` | Largeur de chaussée (m) | Réel |  |  |
| `nb_voies` | Nombre de voies | Entier |  |  |
| `sens` | Sens de circulation | Texte (7) | dom_sens |  |
| `longueur_m` | Longueur (m) | Réel |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Terrasses et étals (`occupation_domaine_public`)

Emprises autorisées d'occupation du domaine public (terrasses, étals). Géométrie : MultiPolygon. Objets : 0.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `id_occupation` | Identifiant | Texte (16) |  | OCC-<année>-<n°> |
| `type_occupation` | Type d'occupation | Texte (8) | dom_type_occupation |  |
| `etablissement` | Établissement | Texte (120) |  | Enseigne |
| `adresse` | Adresse | Texte (120) |  |  |
| `id_voie` | Voie | Texte (20) |  | Lien vers le référentiel des voies |
| `surface_m2` | Surface (m²) | Réel |  | Calculée |
| `statut` | Statut | Texte (3) | dom_statut_autorisation |  |
| `num_arrete` | N° d'arrêté | Texte (20) |  |  |
| `date_debut` | Début d'autorisation | Date |  |  |
| `date_fin` | Fin d'autorisation | Date |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Équipements et lieux d'intérêt (`equipement_public`)

Zones d'activité ou d'intérêt BD TOPO (écoles, équipements, places). Géométrie : MultiPolygon. Objets : 333.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `cleabs` | Identifiant BD TOPO | Texte (24) |  |  |
| `categorie` | Catégorie | Texte (40) |  |  |
| `nature` | Nature | Texte (60) |  |  |
| `nom` | Nom | Texte (120) |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

### Quartiers (`quartier`)

Quartiers de la Ville de Chambéry (open data Ville). Géométrie : MultiPolygon. Objets : 7.

| Champ | Alias | Type | Domaine | Description |
|---|---|---|---|---|
| `code` | Code | Texte (2) |  |  |
| `nom` | Nom du quartier | Texte (60) |  |  |
| `source` | Source | Texte (80) |  | Origine de la donnée |
| `date_maj` | Date de mise à jour | Date |  | Dernière mise à jour de l'objet |

## Domaines de valeurs

### `dom_type_bien` : Famille fonctionnelle du bien

| Code | Libellé |
|---|---|
| ADM | Administration |
| ENS | Enseignement et petite enfance |
| SPO | Sport |
| CUL | Culture et loisirs |
| REL | Édifice cultuel |
| SAN | Santé et action sociale |
| TEC | Technique et logistique |
| COM | Commerce et marché |
| LOG | Logement |
| ANX | Annexe |
| AQU | À qualifier |

### `dom_etat` : État général constaté

| Code | Libellé |
|---|---|
| BON | Bon |
| MOY | Moyen |
| MAU | Mauvais |
| TMA | Très mauvais |
| NR | Non renseigné |

### `dom_affectataire` : Service municipal affectataire

| Code | Libellé |
|---|---|
| EDU | Éducation |
| SPO | Sports |
| CUL | Culture |
| TEC | Services techniques |
| ADM | Administration générale |
| SOC | Action sociale (CCAS) |
| TIE | Mis à disposition d'un tiers |
| NR | Non renseigné |

### `dom_domanialite` : Domanialité présumée de la voie

| Code | Libellé |
|---|---|
| COM | Communale |
| DEP | Départementale |
| NAT | Nationale |
| AUT | Autoroute concédée |
| PRI | Privée |
| NR | Non déterminée |

### `dom_sens` : Sens de circulation

| Code | Libellé |
|---|---|
| DOUBLE | Double sens |
| DIRECT | Sens direct |
| INVERSE | Sens inverse |
| SANS | Sans objet |

### `dom_type_occupation` : Type d'occupation du domaine public

| Code | Libellé |
|---|---|
| TER_OUV | Terrasse ouverte |
| TER_FER | Terrasse fermée |
| ETAL_MAR | Étal de marché |
| ETAL_SAI | Étal saisonnier |
| AUTRE | Autre occupation |

### `dom_statut_autorisation` : Statut de l'autorisation

| Code | Libellé |
|---|---|
| INS | En instruction |
| AUT | Autorisée |
| REF | Refusée |
| ECH | Échue |

## Relations

- `rel_batiment_locaux` : un bâtiment communal (`id_bien`) contient 0 à n locaux (`local_communal.id_bien`). Classe de relations dans la géodatabase, relation de projet dans QGIS.
- `troncon_voirie.id_voie` renvoie à `voie.id_voie` (identifiant BAN de la voie).
