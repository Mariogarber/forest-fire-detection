"""Muestras georreferenciadas de escenas satelitales y partes EGIF.

Las fechas se interpretan en UTC. Los negativos solo indican que no hay un
incendio registrado activo en ese instante; no prueban la ausencia de fuego.
"""

import numpy as np
import pandas as pd
import torch
from torch.utils.data import ConcatDataset, Dataset, Subset

from forest_fire_detection.preprocessing import egif_to_lonlat
from forest_fire_detection.resample.data_augmentation import SATELLITE_TRANSFORMS_V1


DEFAULT_CHANNELS = ("IR10.8", "IR12.0", "IR13.4",
                    "IR3.9", "IR8.7", "IR9.7",
                    "NIR1.6", "VIS0.6", "VIS0.8",
                    "WV6.2", "WV7.3")
CROP_SIZE = 128


def _grid(raw_images, channels):
    if "time" not in raw_images.dims or not raw_images.sizes["time"]:
        raise ValueError("Se necesita al menos una escena con dimensión time")
    times = pd.DatetimeIndex(pd.to_datetime(raw_images.indexes["time"], utc=True)).as_unit("ns")
    if times.hasnans or not times.is_monotonic_increasing or not times.is_unique:
        raise ValueError("Las fechas de las escenas deben ser únicas y estar ordenadas")
    axes = []
    for name in ("lat", "lon"):
        if name not in raw_images.coords or raw_images[name].dims != (name,):
            raise ValueError(f"La coordenada {name} debe ser unidimensional")
        values = np.asarray(raw_images[name].values, dtype=float)
        diff = np.diff(values)
        if len(values) < CROP_SIZE or not np.isfinite(values).all() or not (np.all(diff > 0) or np.all(diff < 0)):
            raise ValueError(f"La coordenada {name} debe ser monótona y tener al menos {CROP_SIZE} píxeles")
        axes.append(values)
    for channel in channels:
        if channel not in raw_images or set(raw_images[channel].dims) != {"time", "lat", "lon"}:
            raise ValueError(f"El canal {channel!r} debe tener dimensiones time, lat y lon")
    return times, axes[0], axes[1]


def _pixel(coord, values):
    if not np.isfinite(coord) or not values.min() <= coord <= values.max():
        raise ValueError("La coordenada está fuera de la cobertura satelital")
    index = int(np.abs(values - coord).argmin())
    if index < CROP_SIZE // 2 or index + CROP_SIZE // 2 > len(values):
        raise ValueError("No se puede obtener un recorte completo en el borde")
    return index


class ForestFireDataset(Dataset):
    """Una muestra por índice de escena, posición de píxel y etiqueta."""

    def __init__(self, raw_images, scene_indices, has_fire, pixel_coords, channels=DEFAULT_CHANNELS):
        self.images = raw_images
        self.channels = tuple(channels)
        self.times, _, _ = _grid(raw_images, self.channels)
        self.scene_indices = list(scene_indices)
        self.has_fire = list(has_fire)
        self.pixel_coords = list(pixel_coords)
        if not (len(self.scene_indices) == len(self.has_fire) == len(self.pixel_coords)):
            raise ValueError("Cada muestra necesita una escena, etiqueta y posición")
        for scene_index, (x, y) in zip(self.scene_indices, self.pixel_coords):
            if not 0 <= scene_index < len(self.times) or not (CROP_SIZE // 2 <= x <= raw_images.sizes["lon"] - CROP_SIZE // 2 and CROP_SIZE // 2 <= y <= raw_images.sizes["lat"] - CROP_SIZE // 2):
                raise ValueError("Índice de escena o recorte fuera de rango")

    def crop(self, idx):
        x, y = self.pixel_coords[idx]
        scene = self.images.isel(time=self.scene_indices[idx], lat=slice(y - 64, y + 64), lon=slice(x - 64, x + 64))
        image = np.stack([scene[name].transpose("lat", "lon").values for name in self.channels])
        image = torch.as_tensor(image.copy(), dtype=torch.float32)
        if hasattr(self, "transform") and self.transform is not None:
            image = self.transform(image)
        return image

    def __len__(self):
        return len(self.scene_indices)

    def __getitem__(self, idx):
        return self.crop(idx), self.times[self.scene_indices[idx]], self.has_fire[idx]


def build_dataset_without_fire(raw_images, fire_data, n_samples, *, channels=DEFAULT_CHANNELS, rng=None):
    """Muestrear escenas sin ningún incendio registrado activo en ese instante.

    Un fin desconocido se considera activo indefinidamente. Una detección
    desconocida impide determinar los negativos y provoca un error.
    """
    times, lat, lon = _grid(raw_images, tuple(channels))
    if not isinstance(n_samples, (int, np.integer)) or n_samples < 0:
        raise ValueError("n_samples debe ser un entero no negativo")
    detected = pd.DatetimeIndex(pd.to_datetime(fire_data["Detectado"], utc=True)).as_unit("ns")
    extinguished = pd.DatetimeIndex(pd.to_datetime(fire_data["Extinguido"], utc=True)).as_unit("ns")
    if detected.hasnans:
        raise ValueError("No se pueden determinar negativos con fechas de detección desconocidas")
    if ((~extinguished.isna()) & (extinguished < detected)).any():
        raise ValueError("Hay incendios extinguidos antes de su detección")
    # Búsqueda sobre intervalos ordenados, incluyendo ambos extremos.
    order = np.argsort(detected.asi8)
    starts = detected.asi8[order]
    ends = extinguished.asi8.copy()
    ends[extinguished.isna()] = np.iinfo(np.int64).max
    ends = np.maximum.accumulate(ends[order])
    positions = np.searchsorted(starts, times.asi8, side="right") - 1
    active = np.zeros(len(times), dtype=bool)
    mask = positions >= 0
    active[mask] = ends[positions[mask]] >= times.asi8[mask]
    available = np.flatnonzero(~active)
    if n_samples > len(available):
        raise ValueError(f"Solo hay {len(available)} instantes sin incendios registrados para {n_samples} muestras")
    rng = np.random.default_rng(rng)
    indices = rng.choice(available, size=n_samples, replace=False)
    xs = rng.integers(64, len(lon) - 64 + 1, size=n_samples)
    ys = rng.integers(64, len(lat) - 64 + 1, size=n_samples)
    return ForestFireDataset(raw_images, indices, [False] * n_samples, list(zip(xs, ys)), channels)


def build_dataset_with_fire(raw_images, fire_data, detection_offset: pd.Timedelta, *, channels=DEFAULT_CHANNELS):
    """Asociar cada parte a la primera escena disponible durante el incendio.

    Se omiten los partes sin recorte completo o sin escena entre detección y
    extinción. El filtro de duración conserva el significado original.
    """
    times, lat, lon = _grid(raw_images, tuple(channels))
    detected = pd.to_datetime(fire_data["Detectado"], utc=True)
    extinguished = pd.to_datetime(fire_data["Extinguido"], utc=True)
    eligible = fire_data.loc[
        ((extinguished - detected) >= detection_offset)
        & (detected <= times[-1])
        & (extinguished >= times[0])
    ]
    geo = egif_to_lonlat(eligible)
    indices, coords = [], []
    for _, row in geo.iterrows():
        start = pd.to_datetime(row["Detectado"], utc=True)
        end = pd.to_datetime(row["Extinguido"], utc=True)
        index = times.searchsorted(start, side="left")
        if index == len(times) or times[index] > end:
            continue
        try:
            x, y = _pixel(row["lon"], lon), _pixel(row["lat"], lat)
        except ValueError:
            continue
        indices.append(index)
        coords.append((x, y))
    return ForestFireDataset(raw_images, indices, [True] * len(indices), coords, channels)


def shuffle_dataset(dataset_with_fire, dataset_without_fire, *, generator=None):
    """Mezclar muestras completas sin cargar ni concatenar las escenas."""
    combined = ConcatDataset([dataset_with_fire, dataset_without_fire])
    return Subset(combined, torch.randperm(len(combined), generator=generator).tolist())


class TrainingDataset(Dataset):
    """Adaptar muestras a tensores agrupables por el DataLoader de PyTorch.

    Devuelve imagen float32 (3, 128, 128), instante UTC en segundos Unix
    int64 y etiqueta float32 escalar (0 o 1). Los valores no finitos de la
    imagen se sustituyen por cero; los canales no se normalizan ni se convierten
    a color visible. La lectura de las imágenes sigue siendo diferida.
    """

    def __init__(self, dataset):
        self.dataset = dataset
        self.transform = SATELLITE_TRANSFORMS_V1

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        image, timestamp, label = self.dataset[idx]
        image = torch.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)

        if hasattr(self, "transform") and self.transform is not None:
            image = self.transform(image)
        seconds = pd.Timestamp(timestamp).as_unit("ns").value // 1_000_000_000
        return image, torch.tensor(seconds, dtype=torch.int64), torch.tensor(label, dtype=torch.float32)


def build_training_dataset(raw_images, fire_data, n_samples_without_fire, detection_offset, *, channels=DEFAULT_CHANNELS, seed=0):
    """Construir el dataset de entrenamiento desde escenas y partes del notebook.

    fire_data debe incluir todos los partes disponibles, también los que se
    detectaron antes del periodo de las escenas, para excluir negativos activos.
    La semilla controla tanto el muestreo de negativos como el orden mezclado.
    """
    positive = build_dataset_with_fire(raw_images, fire_data, detection_offset, channels=channels)
    negative = build_dataset_without_fire(raw_images, fire_data, n_samples_without_fire, channels=channels, rng=seed)
    generator = torch.Generator().manual_seed(seed)
    return TrainingDataset(shuffle_dataset(positive, negative, generator=generator))
