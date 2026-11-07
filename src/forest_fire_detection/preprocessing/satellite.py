from glob import glob
from pathlib import Path
import xarray as xr
from datetime import datetime

SATELLITE_RAW_REPOSITORY = Path("/mnt/Datos/ESP_SAT")
SATELLITE_PROCESSED_REPOSITORY = Path("/home/marito/Documents/Projects/forest-fire-detection/data/satellite/ESP_PROCESS")

def _add_time_from_filename(ds):
    # Ejemplo: HRSEVIRI_20191231T2215.nc → 2019-12-31 22:15.
    timestamp = Path(ds.encoding["source"]).stem.rsplit("_", 1)[-1]
    return ds.expand_dims(time=[datetime.strptime(timestamp, "%Y%m%dT%H%M")])

def _select_months_for_quarter(quarter):
    if quarter == 1:
        return [1, 2, 3]
    elif quarter == 2:
        return [4, 5, 6]
    elif quarter == 3:
        return [7, 8, 9]
    elif quarter == 4:
        return [10, 11, 12]
    else:
        raise ValueError("Quarter must be between 1 and 4")

def list_netcdf_files(root):
    return sorted(Path(root).rglob("*.nc"))

def load_netcdfs_by_quarters_lazy(file_list, year, quarter):
    months = {f"{month:02d}" for month in _select_months_for_quarter(quarter)}

    files = sorted(
        f for f in file_list
        if f.parent.name in months and f.parent.parent.name == str(year)
    )

    if not files:
        raise ValueError(f"No hay archivos para {year}, trimestre {quarter}")

    print(f"Archivos seleccionados: {len(files)}")
    print(f"Primero: {files[0].name}")
    print(f"Último: {files[-1].name}")

    return xr.open_mfdataset(
        files,
        engine="h5netcdf",
        combine="by_coords",
        preprocess=_add_time_from_filename,
        chunks={"lat": 301, "lon": 458},
    )

def save_dataset_by_quarters(dataset, root):
    filename = f"dataset_{dataset.time.dt.year.values[0]}_q{((dataset.time.dt.month.values[0]-1)//3)+1}.zarr"
    path = root / filename
    dataset.to_zarr(path)
    print(f"Dataset guardado en: {path}")