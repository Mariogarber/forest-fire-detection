import xarray as xr
from pathlib import Path
from forest_fire_detection.preprocessing.satellite import SATELLITE_PROCESSED_REPOSITORY

class SatelliteLoader:
    def __init__(self, root=SATELLITE_PROCESSED_REPOSITORY):
        self.root = Path(root)

    def load_by_quarter(self, year, quarter):
        filename = f"dataset_{year}_q{quarter}.zarr"
        path = self.root / filename
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el dataset: {path}")
        dataset = xr.open_zarr(path)
        # Los timestamps del archivo son horas UTC sin zona horaria explícita.
        time_index = dataset.indexes["time"]
        if time_index.tz is None:
            time_index = time_index.tz_localize("UTC")
        else:
            time_index = time_index.tz_convert("UTC")
        return dataset.assign_coords(time=time_index)
