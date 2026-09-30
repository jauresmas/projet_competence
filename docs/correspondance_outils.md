# Correspondance des outils : ce projet, ArcGIS Pro et AutoCAD

Ce démonstrateur a été réalisé sans licence ArcGIS Pro ni AutoCAD. Chaque tâche a été faite
avec un outil équivalent ; ce tableau indique l'outil utilisé et celui qui serait employé au poste.
Les livrables restent au format de ces logiciels : géodatabase fichier (.gdb) et DAO (DXF, charte
convertible en fichier de normes .dws).

## Base de données (ArcGIS Pro)

| Tâche | Réalisé avec | Au poste, dans ArcGIS Pro |
|---|---|---|
| Modèle de données : domaines, alias, relations | Géodatabase fichier écrite par GDAL (`02`, `ecriture.py`) | Domaines, alias, classes de relations dans le catalogue |
| Formulaires de saisie à onglets, tables liées | Formulaire QGIS (`formulaires.py`) | *Forms* (Form Designer) |
| Contrôles de saisie (format d'identifiant, dates, champs obligatoires) | Contraintes d'expression QGIS | Règles attributaires de contrainte (Arcade) : `scripts/arcgis/regles_attributaires.py`, **non testé** |
| Valeurs calculées (surface, quartier, parcelle, identifiant de visite) | Valeurs par défaut QGIS | Règles attributaires de calcul (Arcade), même script |
| Contrôle qualité (unicité, géométrie, intégrité, chevauchements) | Script `03` | *Check Geometry*, topologie, *Data Reviewer* |
| Saisie terrain des visites de bâtiments | Projet QField (`qfield/`) | Field Maps ou Survey123 |
| Chaîne de traitement graphique | Modeleur QGIS (`modeles/integration_recolement.model3`) | ModelBuilder |

## Cartographie (ArcGIS Pro)

| Tâche | Réalisé avec | Au poste, dans ArcGIS Pro |
|---|---|---|
| Plans en série (une page par terrasse, par bâtiment) | Atlas QGIS (`06`, `10`) | *Map Series* |
| Plans de manifestation et de voirie | Mise en page QGIS (`06`) | *Layout* |
| Tableau de bord | Page HTML Leaflet (`12`) | ArcGIS Dashboards, Experience Builder |
| Open data | GeoJSON, CSV, descripteur Frictionless (`11`) | ArcGIS Hub, portail open data |

## Récolement (AutoCAD)

| Tâche | Réalisé avec | Au poste, dans AutoCAD |
|---|---|---|
| Charte de calques et de blocs | `charte_topo.py`, `donnees/autocad/charte_ville_normes.dxf` | Fichier de normes `.dws` |
| Vérifier un plan reçu | Contrôles C02, C03, C07 (`09`) | `_CHECKSTANDARDS`, `_QSELECT`, `_DATAEXTRACTION` |
| Système de coordonnées | pyproj, modèle QGIS | AutoCAD Map 3D : `_MAPCSASSIGN` |
| Traduire les calques du prestataire | Table de correspondance (`09`, modèle QGIS) | `_LAYTRANS` |
| Supprimer les doublons, nettoyer | Contrôle C05, audit ezdxf | `_OVERKILL`, `_AUDIT`, `_-PURGE` |
| Archiver l'existant et intégrer | Calque gelé `ARC_OBJET_REMPLACE` (`09`) | `_LAYMCH`, `_LAYFRZ`, `_XATTACH` / `_BIND` |

Procédure complète : [procedure_autocad_recolement.md](procedure_autocad_recolement.md).
