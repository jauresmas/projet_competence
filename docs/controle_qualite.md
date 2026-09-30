# Contrôle qualité de la base patrimoine

Base contrôlée : `patrimoine_chambery.gpkg`, le 30/09/2026.

| Couche | Objets |
|---|---:|
| batiment_communal | 603 |
| parcelle_communale | 1948 |
| local_communal | 1066 |
| voie | 782 |
| troncon_voirie | 4873 |
| occupation_domaine_public | 0 |
| equipement_public | 333 |
| quartier | 7 |

| Couche | Contrôle | Anomalies | Exemples |
|---|---|---:|---|
| batiment_communal | Identifiant id_bien en double | OK |  |
| local_communal | Identifiant id_local en double | OK |  |
| parcelle_communale | Parcelle idu en double | OK |  |
| voie | Identifiant de voie en double | OK |  |
| batiment_communal | Bâtiment sans adresse | OK |  |
| batiment_communal | Bâtiment hors quartier | OK |  |
| batiment_communal | Type de bien à qualifier | 167 | BAT-BE-0002, BAT-BE-0004, BAT-BE-0007, BAT-BE-0009, BAT-BE-0012 |
| batiment_communal | Bâtiment sans nom | 447 | BAT-BE-0002, BAT-BE-0004, BAT-BE-0005, BAT-BE-0006, BAT-BE-0007 |
| batiment_communal | Géométrie invalide | OK |  |
| parcelle_communale | Géométrie invalide | OK |  |
| local_communal | Local sans bâtiment de rattachement | 54 | LOC-00008, LOC-00067, LOC-00075, LOC-00076, LOC-00077 |
| local_communal | Local lié à un id_bien inexistant | OK |  |
| batiment_communal | Parcelle d'accueil absente de parcelle_communale | OK |  |
| troncon_voirie | Tronçon routier sans voie nommée | 1086 | TRONROUT0000000012795513, TRONROUT0000000012795536, TRONROUT0000000012795537, TRONROUT0000000012802314, TRONROUT0000000012802331 |
| troncon_voirie | Tronçon lié à une voie absente du référentiel | 54 | TRONROUT0000000012802728, TRONROUT0000000012808439, TRONROUT0000000012808500, TRONROUT0000000012809704, TRONROUT0000000012809712 |
| batiment_communal | Valeur hors domaine (type_bien) | OK |  |
| batiment_communal | Valeur hors domaine (etat) | OK |  |
| batiment_communal | Valeur hors domaine (affectataire) | OK |  |
| troncon_voirie | Valeur hors domaine (domanialite) | OK |  |
| troncon_voirie | Valeur hors domaine (sens) | OK |  |
| occupation_domaine_public | Valeur hors domaine (type_occupation) | OK |  |
| occupation_domaine_public | Valeur hors domaine (statut) | OK |  |
| batiment_communal | Chevauchement entre bâtiments (> 1 m²) | OK |  |

Les anomalies de complétude (nom, type à qualifier) ne sont pas des erreurs :
elles forment la liste de travail à traiter avec les services et lors des visites.
