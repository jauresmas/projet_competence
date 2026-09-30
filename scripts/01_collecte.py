"""
01_collecte.py
Collecte des données ouvertes sur la commune de Chambéry (INSEE 73065).

Sources :
  - BD TOPO V3 (IGN, flux WFS de la Géoplateforme) : commune, bâtiments,
    tronçons de route, voies nommées, zones d'activité ou d'intérêt
  - Cadastre Etalab : parcelles de la commune
  - Base Adresse Nationale : adresses de la Savoie
  - Ville de Chambéry (data.gouv.fr) : quartiers
  - DGFiP : fichiers des locaux et des parcelles des personnes morales 2025

Les téléchargements déjà présents ne sont pas refaits.
Lancement : python-qgis-ltr.bat 01_collecte.py
"""
import json
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BRUT = RACINE / "donnees" / "brut"
BRUT.mkdir(parents=True, exist_ok=True)

INSEE = "73065"
WFS = "https://data.geopf.fr/wfs/ows"
# Emprise large de la commune en WGS84 (lat min, lon min, lat max, lon max)
BBOX = (45.540, 5.870, 45.615, 5.975)

COUCHES_BDTOPO = [
    "commune",
    "batiment",
    "troncon_de_route",
    "voie_nommee",
    "zone_d_activite_ou_d_interet",
]

FICHIERS = {
    "cadastre_parcelles_73065.json.gz":
        "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/"
        "communes/73/73065/cadastre-73065-parcelles.json.gz",
    "ban_adresses_73.csv.gz":
        "https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-73.csv.gz",
    "quartiers-chy.zip":
        "https://static.data.gouv.fr/resources/quartiers-de-la-ville-de-chambery/"
        "20251210-161807/quartiers-chy.zip",
    "parcelles_pm_2025_57_976.zip":
        "https://data.economie.gouv.fr/api/v2/catalog/datasets/"
        "fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/"
        "fichier_des_parcelles_situation_2025_dpts_57_a_976_zip",
    "locaux_pm_2025.zip":
        "https://data.economie.gouv.fr/api/v2/catalog/datasets/"
        "fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/"
        "fichier_des_locaux_situation_2025_zip",
}


def telecharger(url, cible):
    if cible.exists():
        print(f"  déjà présent : {cible.name}")
        return
    print(f"  téléchargement : {cible.name}")
    urllib.request.urlretrieve(url, cible)


def wfs_bdtopo(couche):
    """Récupère une couche BD TOPO par pages de 5000 objets."""
    cible = BRUT / f"bdtopo_{couche}.geojson"
    if cible.exists():
        print(f"  déjà présent : {cible.name}")
        return
    objets, debut = [], 0
    while True:
        params = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": f"BDTOPO_V3:{couche}",
            "OUTPUTFORMAT": "application/json",
            "COUNT": 5000, "STARTINDEX": debut, "SORTBY": "cleabs",
        }
        if couche == "commune":
            params["CQL_FILTER"] = f"code_insee='{INSEE}'"
        else:
            params["BBOX"] = ",".join(map(str, BBOX)) + ",urn:ogc:def:crs:EPSG::4326"
        url = WFS + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=300) as r:
            page = json.load(r)
        objets += page["features"]
        print(f"  {couche} : {len(objets)} objets")
        if len(page["features"]) < 5000:
            break
        debut += 5000
    cible.write_text(json.dumps({"type": "FeatureCollection", "features": objets}),
                     encoding="utf-8")


def extraire_savoie():
    """Extrait des archives DGFiP les seuls fichiers du département 73."""
    for archive, suffixe in [("parcelles_pm_2025_57_976.zip", "NB_730.csv"),
                             ("locaux_pm_2025.zip", "B_730.csv")]:
        with zipfile.ZipFile(BRUT / archive) as z:
            nom = next(n for n in z.namelist() if n.endswith(suffixe))
            cible = BRUT / Path(nom).name
            if not cible.exists():
                cible.write_bytes(z.read(nom))
            print(f"  extrait : {cible.name}")
    with zipfile.ZipFile(BRUT / "quartiers-chy.zip") as z:
        z.extractall(BRUT / "quartiers")


if __name__ == "__main__":
    print("Fichiers ouverts")
    for nom, url in FICHIERS.items():
        telecharger(url, BRUT / nom)
    print("BD TOPO (WFS IGN)")
    for couche in COUCHES_BDTOPO:
        wfs_bdtopo(couche)
    print("Extraction Savoie")
    extraire_savoie()
    print("Collecte terminée.")
