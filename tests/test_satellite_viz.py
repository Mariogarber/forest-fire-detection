"""Focused checks for scene geometry, colour and EGIF overlays."""
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from forest_fire_detection.preprocessing.coords import egif_to_lonlat as preprocess_egif_to_lonlat
from forest_fire_detection.viz.satellite import (
    egif_to_lonlat, make_rgb, normalize_channel, plot_scene_with_fires,
    select_scene,
)


class SatelliteVisualizationTests(unittest.TestCase):
    def setUp(self):
        values = np.arange(24.0).reshape(2, 3, 4)
        self.data = xr.Dataset(
            {name: (("time", "lat", "lon"), values + i) for i, name in enumerate(("r", "g", "b"))},
            coords={"time": pd.to_datetime(["2020-01-01", "2020-01-02"]),
                    "lat": [42.0, 41.0, 40.0], "lon": [-5.0, -4.0, -3.0, -2.0]},
        )

    def tearDown(self):
        plt.close("all")

    def test_time_and_descending_lat_crop(self):
        with self.assertRaises(ValueError):
            select_scene(self.data)
        scene = select_scene(self.data, time="2020-01-01", bbox=(-4.5, 40.5, -2.5, 42.5))
        np.testing.assert_array_equal(scene.lat, [42, 41])
        np.testing.assert_array_equal(scene.lon, [-4, -3])
        self.assertEqual(scene.r.shape, (2, 2))
        with self.assertRaises(ValueError):
            select_scene(self.data, time="2020-01-01", bbox=(10, 10, 11, 11))

    def test_rgb_order_limits_and_transparency(self):
        scene = select_scene(self.data, time="2020-01-01").copy(deep=True)
        scene["g"].values[0, 0] = np.nan
        rgba = make_rgb(scene, ["r", "g", "b"], limits=[(0, 20)] * 3)
        np.testing.assert_allclose(rgba[1, 0], [0.2, 0.25, 0.3, 1])
        self.assertEqual(rgba[0, 0, 3], 0)
        np.testing.assert_allclose(normalize_channel(np.ones((2, 2))), 0)
        with self.assertRaises(ValueError):
            normalize_channel(np.full((2, 2), np.nan))

    def test_utm_conversion_and_invalid_datum(self):
        self.assertIs(egif_to_lonlat, preprocess_egif_to_lonlat)
        labels = pd.DataFrame({"CoordenadaX": [500000.0], "CoordenadaY": [0.0], "Huso": [30], "Datum": ["WGS84"]})
        converted = egif_to_lonlat(labels)
        self.assertAlmostEqual(converted.loc[0, "lon"], -3.0, places=4)
        self.assertAlmostEqual(converted.loc[0, "lat"], 0.0, places=4)
        self.assertNotIn("lon", labels)
        labels.loc[0, "Datum"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            egif_to_lonlat(labels)

    def test_overlay_keeps_map_bounds_and_point_location(self):
        labels = pd.DataFrame({"lon": [-4.0, 100.0], "lat": [41.0, 50.0]})
        ax, image, points = plot_scene_with_fires(
            self.data, labels, channels=["r", "g", "b"], time="2020-01-01"
        )
        self.assertLess(max(ax.get_xlim()), 10)
        np.testing.assert_allclose(points.get_offsets()[0], [-4, 41])
        self.assertIs(image.axes, ax)

    def test_regcan95_utm_zones(self):
        labels = pd.DataFrame({
            "CoordenadaX": [500000.0, 500000.0],
            "CoordenadaY": [0.0, 0.0],
            "Huso": [27, 28],
            "Datum": ["REGCAN95", " regcan95 "],
        })
        converted = preprocess_egif_to_lonlat(labels)
        np.testing.assert_allclose(converted["lon"], [-21.0, -15.0], atol=1e-4)
        np.testing.assert_allclose(converted["lat"], [0.0, 0.0], atol=1e-4)
        labels.loc[0, "Huso"] = 29
        with self.assertRaises(ValueError):
            preprocess_egif_to_lonlat(labels)


if __name__ == "__main__":
    unittest.main()
