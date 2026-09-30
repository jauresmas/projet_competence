"""
ecriture.py
Écrit les couches dans une géodatabase fichier (.gdb) ou un GeoPackage (.gpkg)
en appliquant le modèle de schema.py : domaines codés, alias de champs,
relation bâtiment / locaux.
"""
import shutil
from pathlib import Path

import pandas as pd
from osgeo import gdal, ogr, osr

from schema import COUCHES, DOMAINES, SRID

gdal.UseExceptions()

TYPES_OGR = {"str": ogr.OFTString, "int": ogr.OFTInteger,
             "real": ogr.OFTReal, "date": ogr.OFTDate}
GEOM_OGR = {"MultiPolygon": ogr.wkbMultiPolygon,
            "MultiLineString": ogr.wkbMultiLineString, None: ogr.wkbNone}


def _valeur(v, type_):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if type_ == "int":
        return int(v)
    if type_ == "real":
        return float(v)
    if type_ == "date":
        return v
    return str(v)


def ecrire_base(couches, cible):
    cible = Path(cible)
    if cible.exists():
        shutil.rmtree(cible) if cible.is_dir() else cible.unlink()
    pilote = "OpenFileGDB" if cible.suffix == ".gdb" else "GPKG"
    ds = gdal.GetDriverByName(pilote).Create(str(cible), 0, 0, 0, gdal.GDT_Unknown)

    for nom, (desc, valeurs) in DOMAINES.items():
        ds.AddFieldDomain(ogr.CreateCodedFieldDomain(
            nom, desc, ogr.OFTString, ogr.OFSTNone, valeurs))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(SRID)

    for nom, spec in COUCHES.items():
        gdf = couches[nom]
        options = ([f"LAYER_ALIAS={spec['alias']}", "TARGET_ARCGIS_VERSION=ARCGIS_PRO_3_2_OR_LATER"]
                   if pilote == "OpenFileGDB" else [])
        if spec["geom"] and pilote == "OpenFileGDB":
            options.append("CREATE_SHAPE_AREA_AND_LENGTH_FIELDS=NO")
        if pilote == "GPKG":
            options.append(f"DESCRIPTION={spec['description']}")
        lyr = ds.CreateLayer(nom, srs if spec["geom"] else None,
                             GEOM_OGR[spec["geom"]], options=options)
        for champ, alias, type_, largeur, domaine, _ in spec["champs"]:
            fd = ogr.FieldDefn(champ, TYPES_OGR[type_])
            if largeur:
                fd.SetWidth(largeur)
            fd.SetAlternativeName(alias)
            if domaine:
                fd.SetDomainName(domaine)
            lyr.CreateField(fd)

        defn = lyr.GetLayerDefn()
        lyr.StartTransaction()
        for _, row in gdf.iterrows():
            f = ogr.Feature(defn)
            for champ, _, type_, _, _, _ in spec["champs"]:
                v = _valeur(row.get(champ), type_)
                if v is None:
                    f.SetFieldNull(champ)
                elif type_ == "date":
                    f.SetField(champ, v.year, v.month, v.day, 0, 0, 0, 0)
                else:
                    f.SetField(champ, v)
            if spec["geom"] and row.geometry is not None:
                g = ogr.CreateGeometryFromWkb(row.geometry.wkb)
                f.SetGeometry(ogr.ForceTo(g, GEOM_OGR[spec["geom"]]))
            lyr.CreateFeature(f)
        lyr.CommitTransaction()
        print(f"  {cible.name} / {nom} : {len(gdf)} objets")

    ds.FlushCache()
    ds = None
    if pilote == "GPKG":
        return  # relation 1-n déclarée dans le projet QGIS (le GeoPackage ne gère que le n-n)

    # La géodatabase doit être rouverte pour y déclarer la classe de relations
    ds = gdal.OpenEx(str(cible), gdal.OF_UPDATE | gdal.OF_VECTOR)
    rel = gdal.Relationship("rel_batiment_locaux", "batiment_communal",
                            "local_communal", gdal.GRC_ONE_TO_MANY)
    rel.SetLeftTableFields(["id_bien"])
    rel.SetRightTableFields(["id_bien"])
    rel.SetType(gdal.GRT_ASSOCIATION)
    rel.SetForwardPathLabel("contient")
    rel.SetBackwardPathLabel("est situé dans")
    if not ds.AddRelationship(rel):
        raise RuntimeError(f"relation non créée dans {cible.name}")
    print(f"  {cible.name} : classe de relations rel_batiment_locaux créée")
    ds = None
