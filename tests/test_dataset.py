import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch
import xarray as xr

from forest_fire_detection.load.dataset import (
    build_dataset_with_fire, build_dataset_without_fire, build_training_dataset,
    shuffle_dataset,
)


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.times = pd.date_range("2020-01-01", periods=5, freq="h", tz="UTC")
        data = np.broadcast_to(np.arange(5, dtype=np.float32)[:, None, None], (5, 130, 130))
        self.images = xr.Dataset(
            {name: (("time", "lat", "lon"), data + i * 10) for i, name in enumerate(("VIS0.6", "VIS0.8", "NIR1.6"))},
            coords={"time": self.times, "lat": np.arange(130)[::-1], "lon": np.arange(130)},
        )
        self.fires = pd.DataFrame({
            "Detectado": [self.times[1] + pd.Timedelta(minutes=10)],
            "Extinguido": [self.times[3]], "lon": [64.0], "lat": [65.0],
        }, index=[9])

    def test_positive_matches_first_available_scene_and_pixel(self):
        with patch("forest_fire_detection.load.dataset.egif_to_lonlat", side_effect=lambda x: x.copy()):
            dataset = build_dataset_with_fire(self.images, self.fires, pd.Timedelta(0))
        image, timestamp, label = dataset[0]
        self.assertEqual(len(dataset), 1)
        self.assertEqual(timestamp, self.times[2])
        self.assertEqual(dataset.pixel_coords[0], (64, 64))
        self.assertEqual(tuple(image.shape), (3, 128, 128))
        self.assertEqual(image[:, 0, 0].tolist(), [2, 12, 22])
        self.assertTrue(label)
        self.assertNotIn("lapsus", self.fires)

    def test_negative_excludes_full_active_interval(self):
        dataset = build_dataset_without_fire(self.images, self.fires, 3, rng=1)
        self.assertEqual({dataset[i][1] for i in range(len(dataset))}, {self.times[0], self.times[1], self.times[4]})
        for i in range(len(dataset)):
            image, timestamp, label = dataset[i]
            self.assertEqual(image[0, 0, 0].item(), self.times.get_loc(timestamp))
            self.assertFalse(label)

    def test_unknown_end_and_invalid_start_are_conservative(self):
        fires = self.fires.copy()
        fires["Extinguido"] = pd.NaT
        with self.assertRaises(ValueError):
            build_dataset_without_fire(self.images, fires, 3)
        fires["Detectado"] = pd.NaT
        with self.assertRaises(ValueError):
            build_dataset_without_fire(self.images, fires, 1)

    def test_edge_and_missing_scene_are_skipped(self):
        fires = pd.concat([self.fires, self.fires.assign(lon=0), self.fires.assign(Detectado=self.times[-1] + pd.Timedelta(hours=1), Extinguido=self.times[-1] + pd.Timedelta(hours=2))])
        with patch("forest_fire_detection.load.dataset.egif_to_lonlat", side_effect=lambda x: x.copy()):
            dataset = build_dataset_with_fire(self.images, fires, pd.Timedelta(0))
        self.assertEqual(len(dataset), 1)

    def test_shuffle_preserves_samples(self):
        with patch("forest_fire_detection.load.dataset.egif_to_lonlat", side_effect=lambda x: x.copy()):
            positive = build_dataset_with_fire(self.images, self.fires, pd.Timedelta(0))
        negative = build_dataset_without_fire(self.images, self.fires, 3, rng=1)
        mixed = shuffle_dataset(positive, negative, generator=torch.Generator().manual_seed(1))
        self.assertEqual(len(mixed), 4)
        for image, timestamp, label in mixed:
            self.assertEqual(image[0, 0, 0].item(), self.times.get_loc(timestamp))
            self.assertEqual(label, timestamp == self.times[2])

    def test_training_dataset_produces_batches_and_replaces_missing_values(self):
        images = self.images.copy(deep=True)
        images["VIS0.6"].values[2, 0, 0] = np.nan
        with patch("forest_fire_detection.load.dataset.egif_to_lonlat", side_effect=lambda x: x.copy()):
            dataset = build_training_dataset(images, self.fires, 3, pd.Timedelta(0), seed=3)
        image, seconds, label = next(iter(torch.utils.data.DataLoader(dataset, batch_size=4)))
        self.assertEqual(image.shape, (4, 3, 128, 128))
        self.assertEqual(seconds.dtype, torch.int64)
        self.assertEqual(label.dtype, torch.float32)
        self.assertEqual(label.sum().item(), 1)
        self.assertTrue(torch.isfinite(image).all())
        positive = label.bool().nonzero(as_tuple=True)[0].item()
        self.assertEqual(seconds[positive].item(), int(self.times[2].timestamp()))
        self.assertEqual(image[positive, 0, 0, 0].item(), 0)


if __name__ == "__main__":
    unittest.main()
