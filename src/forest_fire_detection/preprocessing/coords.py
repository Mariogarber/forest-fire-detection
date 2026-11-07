"""Convertir localizaciones UTM de partes EGIF a coordenadas geográficas."""

import cartopy.crs as ccrs
import numpy as np
import pandas as pd


def egif_to_lonlat(labels: pd.DataFrame) -> pd.DataFrame:
    """Añadir ``lon`` y ``lat`` en grados WGS84 a una copia de los partes.

    Requiere ``CoordenadaX`` y ``CoordenadaY`` en metros, ``Huso`` y
    ``Datum``. Admite UTM del hemisferio norte: ETRS89 y ED50 en los husos
    28–38, REGCAN95 en los husos 27–28 y WGS84 en los husos 1–60.
    Comprueba el hemisferio de los datos
    antes de llamarla. Las columnas resultantes sustituyen a las existentes.

    Una localización es el punto registrado, no el perímetro quemado. Si falta
    algún dato o la combinación de datum y huso no se admite, se lanza
    ``ValueError`` en vez de asignar una posición supuesta.
    """
    required = {"CoordenadaX", "CoordenadaY", "Huso", "Datum"}
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"Missing EGIF columns: {sorted(missing)}")
    result = labels.copy()
    x = pd.to_numeric(result["CoordenadaX"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    y = pd.to_numeric(result["CoordenadaY"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    zones = pd.to_numeric(result["Huso"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    datums = result["Datum"].astype("string").str.strip().str.upper().fillna("").to_numpy()
    if not (np.isfinite(x) & np.isfinite(y) & np.isfinite(zones)).all():
        raise ValueError("EGIF coordinates and UTM zones must be present and numeric")
    if not ((zones == np.floor(zones)) & (zones >= 1) & (zones <= 60)).all():
        raise ValueError("UTM zones must be integers between 1 and 60")
    lon = np.empty(len(result))
    lat = np.empty(len(result))
    for datum, zone in set(zip(datums, zones.astype(int))):
        if datum == "WGS84":
            epsg = 32600 + zone
        elif datum == "ETRS89" and 28 <= zone <= 38:
            epsg = 25800 + zone
        elif datum == "ED50" and 28 <= zone <= 38:
            epsg = 23000 + zone
        elif datum == "REGCAN95" and zone in (27, 28):
            epsg = 4082 if zone == 27 else 4083
        else:
            raise ValueError(f"Unsupported datum/zone: {datum!r}, {zone}")
        mask = (datums == datum) & (zones == zone)
        points = ccrs.PlateCarree().transform_points(ccrs.epsg(epsg), x[mask], y[mask])
        if not np.isfinite(points[:, :2]).all():
            raise ValueError(f"Could not transform coordinates for {datum}, zone {zone}")
        lon[mask], lat[mask] = points[:, 0], points[:, 1]
    result["lon"], result["lat"] = lon, lat
    return result
