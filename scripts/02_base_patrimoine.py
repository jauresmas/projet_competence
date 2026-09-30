"""
02_base_patrimoine.py
Construit les couches du SIG Patrimoine de Chambéry à partir des données brutes,
puis les écrit dans une géodatabase fichier (ArcGIS Pro) et un GeoPackage (QGIS).

Lancement : python-qgis-ltr.bat 02_base_patrimoine.py
"""
import datetime as dt
from pathlib import Path

import geopandas as gpd
import pandas as pd

from ecriture import ecrire_base
from schema import SRID

RACINE = Path(__file__).resolve().parents[1]
BRUT = RACINE / "donnees" / "brut"
TRAITE = RACINE / "donnees" / "traite"
TRAITE.mkdir(parents=True, exist_ok=True)

INSEE = "73065"
PROPRIETAIRE = "COMMUNE DE CHAMBERY"
AUJOURDHUI = dt.date.today()


def lire_bdtopo(couche):
    gdf = gpd.read_file(BRUT / f"bdtopo_{couche}.geojson")
    gdf = gdf.set_crs(4326, allow_override=True).to_crs(SRID)
    gdf.geometry = gdf.geometry.force_2d()
    return gdf


def idu_dgfip(df):
    """Reconstitue l'identifiant de parcelle (14 caractères) depuis les fichiers DGFiP."""
    prefixe = df["Préfixe"].fillna("").str.strip().replace("", "000").str.zfill(3)
    section = df["Section"].fillna("").str.strip().str.rjust(2, "0")
    numero = df["N° plan"].fillna("").str.strip().str.zfill(4)
    return INSEE + prefixe + section + numero


def adresse_dgfip(df):
    num = df["N° voirie"].fillna("").str.lstrip("0")
    num = num.where(~num.str.startswith("9"), "")  # 9xxx = numéro fictif DGFiP
    txt = (num + " " + df["Nature voie"].fillna("") + " " + df["Nom voie"].fillna(""))
    return txt.str.split().str.join(" ").str.title()


def lire_dgfip(fichier):
    df = pd.read_csv(BRUT / fichier, sep=";", dtype=str, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    den = next(c for c in df.columns if c.startswith("Dénomination"))
    df = df[(df["Code Commune"] == INSEE[2:]) & (df[den].str.strip() == PROPRIETAIRE)].copy()
    df["idu"] = idu_dgfip(df)
    df["adresse"] = adresse_dgfip(df)
    return df


def rattacher_quartier(gdf, quartiers):
    pts = gdf.copy()
    pts.geometry = gdf.representative_point()
    j = gpd.sjoin(pts[["geometry"]], quartiers[["code", "geometry"]], how="left",
                  predicate="within")
    return j["code"].groupby(level=0).first()


# --------------------------------------------------------------------------
# 1. Référentiels : commune, quartiers
# --------------------------------------------------------------------------
print("Commune et quartiers")
commune = lire_bdtopo("commune")
quartiers = gpd.read_file(BRUT / "quartiers" / "Quartiers_CHY.shp").to_crs(SRID)
quartiers = quartiers[["code", "nom", "geometry"]].copy()
quartiers["source"] = "Ville de Chambéry, open data"

# --------------------------------------------------------------------------
# 2. Parcelles communales (cadastre Etalab + DGFiP)
# --------------------------------------------------------------------------
print("Parcelles communales")
cadastre = gpd.read_file("/vsigzip/" + str(BRUT / "cadastre_parcelles_73065.json.gz")).to_crs(SRID)
pm_parcelles = lire_dgfip("PM_25_NB_730.csv")
pm_locaux = lire_dgfip("PM_25_B_730.csv")

idu_communaux = set(pm_parcelles["idu"]) | set(pm_locaux["idu"])
parcelles = cadastre[cadastre["id"].isin(idu_communaux)].copy()
parcelles = parcelles.rename(columns={"id": "idu", "contenance": "contenance_m2"})
parcelles["numero"] = parcelles["numero"].str.zfill(4)
adr = pd.concat([pm_parcelles[["idu", "adresse"]], pm_locaux[["idu", "adresse"]]])
adr = adr[adr["adresse"] != ""].drop_duplicates("idu").set_index("idu")["adresse"]
parcelles["adresse"] = parcelles["idu"].map(adr)
parcelles["batie"] = parcelles["idu"].isin(set(pm_locaux["idu"])).astype(int)
parcelles["quartier"] = rattacher_quartier(parcelles, quartiers)
parcelles["source"] = "Cadastre Etalab ; DGFiP personnes morales 2025"
manquantes = idu_communaux - set(parcelles["idu"])
print(f"  {len(parcelles)} parcelles retrouvées, {len(manquantes)} absentes du cadastre")

# --------------------------------------------------------------------------
# 3. Bâtiments communaux
# --------------------------------------------------------------------------
print("Bâtiments communaux")
bat = lire_bdtopo("batiment")
bat = bat[(bat["etat_de_l_objet"] == "En service") & (~bat["construction_legere"].fillna(False))]
bat = bat[bat.intersects(commune.union_all())].copy()
bat["emprise_m2"] = bat.area.round(1)
bat = bat[bat["emprise_m2"] >= 15]

# Part de l'emprise sur une parcelle communale, et parcelle d'accueil principale
inter = gpd.overlay(bat[["cleabs", "geometry"]], parcelles[["idu", "geometry"]],
                    how="intersection", keep_geom_type=True)
inter["a"] = inter.area
part = inter.groupby("cleabs")["a"].sum() / bat.set_index("cleabs")["emprise_m2"]
idu_princ = inter.sort_values("a").drop_duplicates("cleabs", keep="last").set_index("cleabs")["idu"]
bat = bat[bat["cleabs"].map(part).fillna(0) >= 0.5].copy()
bat["idu_parcelle"] = bat["cleabs"].map(idu_princ)

# Nom et type depuis les zones d'activité ou d'intérêt BD TOPO
zai = lire_bdtopo("zone_d_activite_ou_d_interet")
zai = zai[zai["insee_commune"] == INSEE].copy()
TYPE_PAR_CATEGORIE = {
    "Administratif ou militaire": "ADM", "Science et enseignement": "ENS",
    "Sport": "SPO", "Culture et loisirs": "CUL", "Religieux": "REL",
    "Santé": "SAN", "Gestion des eaux": "TEC", "Industriel et commercial": "TEC",
}
zai["type_bien"] = zai["categorie"].map(TYPE_PAR_CATEGORIE)
zai.loc[zai["nature"].isin(["Marché", "Centre commercial"]), "type_bien"] = "COM"
zai.loc[zai["nature"] == "Mairie", "type_bien"] = "ADM"
# Les places, zones d'activités et sites diffus ne nomment pas un bâtiment
NATURES_NON_BATI = ["Espace public", "Zone industrielle", "Divers industriel",
                    "Divers commercial", "Aire de détente", "Aire d'accueil des gens du voyage"]
zai_bati = zai[~zai["nature"].isin(NATURES_NON_BATI) & zai["type_bien"].notna()]

j = gpd.overlay(bat[["cleabs", "geometry"]], zai_bati[["toponyme", "type_bien", "geometry"]],
                how="intersection", keep_geom_type=True)
j["a"] = j.area
j = j.sort_values("a").drop_duplicates("cleabs", keep="last").set_index("cleabs")
bat["nom"] = bat["cleabs"].map(j["toponyme"])

TYPE_PAR_USAGE = {
    "Résidentiel": "LOG", "Commercial et services": "COM", "Religieux": "REL",
    "Sportif": "SPO", "Industriel": "TEC", "Agricole": "TEC", "Annexe": "ANX",
}
bat["type_bien"] = bat["cleabs"].map(j["type_bien"])
bat["type_bien"] = bat["type_bien"].fillna(bat["usage_1"].map(TYPE_PAR_USAGE)).fillna("AQU")

# Adresse : BAN rattachée à la parcelle, sinon adresse fiscale
ban = pd.read_csv(BRUT / "ban_adresses_73.csv.gz", sep=";", dtype=str,
                  usecols=["code_insee", "numero", "rep", "nom_voie", "cad_parcelles"])
ban = ban[(ban["code_insee"] == INSEE) & ban["cad_parcelles"].notna()].copy()
ban["adresse"] = (ban["numero"] + ban["rep"].fillna("").radd(" ").str.rstrip() + " " + ban["nom_voie"])
ban = ban.assign(idu=ban["cad_parcelles"].str.split("|")).explode("idu")
ban["n"] = pd.to_numeric(ban["numero"], errors="coerce")
adr_ban = ban.sort_values("n").drop_duplicates("idu").set_index("idu")["adresse"]
bat["adresse"] = bat["idu_parcelle"].map(adr_ban).fillna(bat["idu_parcelle"].map(parcelles.set_index("idu")["adresse"]))

bat["nb_etages"] = bat["nombre_d_etages"].astype("Int64")
bat["hauteur_m"] = bat["hauteur"].round(1)
bat["sdp_estimee_m2"] = (bat["emprise_m2"] * bat["nombre_d_etages"]).round(0)
bat["usage_bdtopo"] = bat["usage_1"]
nb_loc = pm_locaux.groupby("idu").size()
bat["nb_locaux"] = bat["idu_parcelle"].map(nb_loc).fillna(0).astype(int)
bat["etat"] = "NR"
bat["affectataire"] = "NR"
bat["id_rnb"] = bat["identifiants_rnb"]
bat["quartier"] = rattacher_quartier(bat, quartiers).fillna("NC")
bat["source"] = "BD TOPO IGN ; DGFiP personnes morales 2025 ; BAN"

# Identifiant stable : quartier, puis position ouest-est / nord-sud
bat["_x"] = bat.representative_point().x.round(-1)
bat["_y"] = -bat.representative_point().y.round(-1)
bat = bat.sort_values(["quartier", "_y", "_x"])
bat["id_bien"] = "BAT-" + bat["quartier"] + "-" + (bat.groupby("quartier").cumcount() + 1).astype(str).str.zfill(4)
print(f"  {len(bat)} bâtiments communaux, dont {bat['nom'].notna().sum()} nommés")

# --------------------------------------------------------------------------
# 4. Locaux communaux (table liée)
# --------------------------------------------------------------------------
print("Locaux communaux")
bat_princ = bat.sort_values("emprise_m2").drop_duplicates("idu_parcelle", keep="last")
bat_princ = bat_princ.set_index("idu_parcelle")["id_bien"]
locaux = pm_locaux.rename(columns={"Bâtiment": "batiment", "Entrée": "entree",
                                   "Niveau": "niveau", "Porte": "porte"})
locaux = locaux[["idu", "batiment", "entree", "niveau", "porte", "adresse"]].copy()
locaux = locaux.sort_values(["idu", "batiment", "entree", "niveau", "porte"]).reset_index(drop=True)
locaux["id_local"] = "LOC-" + (locaux.index + 1).astype(str).str.zfill(5)
locaux["id_bien"] = locaux["idu"].map(bat_princ)
locaux["source"] = "DGFiP personnes morales 2025"
print(f"  {len(locaux)} locaux, {locaux['id_bien'].notna().sum()} rattachés à un bâtiment")

# --------------------------------------------------------------------------
# 5. Référentiel des voies
# --------------------------------------------------------------------------
print("Voies et tronçons")
voies = lire_bdtopo("voie_nommee")
voies = voies[voies["insee_commune"] == INSEE].copy()
voies = voies.replace({"": None})
hors_ban = voies["identifiant_voie_ban"].isna()
# Voie absente de la BAN : identifiant provisoire tiré de la BD TOPO, à régulariser
voies["id_voie"] = voies["identifiant_voie_ban"].fillna("IGN-" + voies["cleabs"].str[-10:])
voies["nom"] = voies["nom_voie_ban"].fillna(voies["nom_collaboratif"].str.title())
voies["type_voie"] = voies["type_voie"].str.capitalize()
voies["longueur_m"] = voies.length.round(1)
voies["quartier"] = rattacher_quartier(voies, quartiers)
voies["source"] = "BD TOPO IGN (voies nommées BAN)"
voies.loc[hors_ban, "source"] = "BD TOPO IGN (voie hors BAN, identifiant provisoire)"

tr = lire_bdtopo("troncon_de_route")
tr = tr[(tr["insee_commune_gauche"] == INSEE) | (tr["insee_commune_droite"] == INSEE)].copy()
tr = tr.replace({"": None})
tr["id_voie"] = tr["identifiant_voie_ban_gauche"].fillna(tr["identifiant_voie_ban_droite"])
tr["nom"] = tr["nom_voie_ban_gauche"].fillna(tr["nom_voie_ban_droite"])
classement = tr["cpx_classement_administratif"].fillna("").str.split("/").str[0]
tr["domanialite"] = classement.map({"Départementale": "DEP", "Nationale": "NAT",
                                    "Autoroute": "AUT"})
tr.loc[tr["domanialite"].isna() & (tr["prive"] == 1), "domanialite"] = "PRI"
tr.loc[tr["domanialite"].isna() & tr["nature"].isin(["Route à 1 chaussée", "Route à 2 chaussées",
                                                     "Rond-point", "Place", "Route empierrée"]),
       "domanialite"] = "COM"
tr["domanialite"] = tr["domanialite"].fillna("NR")
tr["sens"] = tr["sens_de_circulation"].map({"Double sens": "DOUBLE", "Sens direct": "DIRECT",
                                            "Sens inverse": "INVERSE", "Sans objet": "SANS"})
tr["largeur_m"] = tr["largeur_de_chaussee"]
tr["nb_voies"] = tr["nombre_de_voies"].astype("Int64")
tr["longueur_m"] = tr.length.round(1)
tr["source"] = "BD TOPO IGN"

# --------------------------------------------------------------------------
# 6. Équipements et occupation du domaine public (schéma vide, saisie volet 3)
# --------------------------------------------------------------------------
equip = zai.rename(columns={"toponyme": "nom"})
equip = equip[equip.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
equip["source"] = "BD TOPO IGN"

occupation = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=SRID)
visites = pd.DataFrame(columns=["id_visite"])  # table vide, alimentée par la saisie terrain

# --------------------------------------------------------------------------
# 7. Écriture
# --------------------------------------------------------------------------
couches = {
    "quartier": quartiers,
    "parcelle_communale": parcelles,
    "batiment_communal": bat,
    "local_communal": locaux,
    "voie": voies,
    "troncon_voirie": tr,
    "equipement_public": equip,
    "occupation_domaine_public": occupation,
    "visite_batiment": visites,
}
for gdf in couches.values():
    gdf["date_maj"] = AUJOURDHUI

ecrire_base(couches, TRAITE / "patrimoine_chambery.gdb")
ecrire_base(couches, TRAITE / "patrimoine_chambery.gpkg")
print("Base patrimoine écrite dans", TRAITE)
