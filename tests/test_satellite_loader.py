import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import xarray as xr

from forest_fire_detection.load.satellite import SatelliteLoader


class SatelliteLoaderTests(unittest.TestCase):
    def test_time_is_localized_to_utc_without_changing_instant(self):
        dataset = xr.Dataset(coords={"time": pd.to_datetime(["2020-01-01 12:00:00"])})
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "dataset_2020_q1.zarr").mkdir()
            with patch("forest_fire_detection.load.satellite.xr.open_zarr", return_value=dataset):
                result = SatelliteLoader(directory).load_by_quarter(2020, 1)

        self.assertEqual(result.indexes["time"][0], pd.Timestamp("2020-01-01 12:00:00", tz="UTC"))
        self.assertIsNone(dataset.indexes["time"].tz)

    def test_aware_time_is_converted_to_utc(self):
        dataset = xr.Dataset(coords={"time": pd.DatetimeIndex(["2020-01-01 12:00"], tz="Europe/Madrid")})
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "dataset_2020_q1.zarr").mkdir()
            with patch("forest_fire_detection.load.satellite.xr.open_zarr", return_value=dataset):
                result = SatelliteLoader(directory).load_by_quarter(2020, 1)

        self.assertEqual(result.indexes["time"][0], pd.Timestamp("2020-01-01 11:00:00", tz="UTC"))
