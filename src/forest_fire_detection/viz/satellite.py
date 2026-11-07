"""Composable plots for georeferenced satellite scenes and EGIF fire reports.

Scenes use one-dimensional ``lat`` and ``lon`` coordinates in degrees. Select
an image time explicitly when the dataset contains more than one observation.
EGIF locations are ignition points, not burned perimeters or negative labels.
"""

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from forest_fire_detection.preprocessing.coords import egif_to_lonlat


# Channel order is red, green, blue. These are display composites, not
# calibrated true-colour imagery. The caller may pass any three channels.
COMPOSITES = {
    "visible": ("VIS0.6", "VIS0.8", "NIR1.6"),
    "natural_color": ("NIR1.6", "VIS0.8", "VIS0.6"),
    "infrared": ("IR3.9", "IR8.7", "IR9.7")
}


def select_scene(data, *, time=None, bbox=None):
    """Select one time and optionally crop to (west, south, east, north).

    Bounds are inclusive and in degrees; ascending and descending coordinate
    axes are both supported. Time selection is exact, never silently nearest.
    """
    if "time" in data.dims:
        if time is None:
            if data.sizes["time"] != 1:
                raise ValueError("Select a time explicitly for a multi-time dataset")
            data = data.isel(time=0, drop=True)
        else:
            data = data.sel(time=time, drop=True)
            if "time" in data.dims:
                raise ValueError("time must select exactly one observation")
    elif time is not None:
        raise ValueError("The input has no time dimension")

    for coord in ("lat", "lon"):
        if coord not in data.coords or data[coord].dims != (coord,):
            raise ValueError(f"Expected a one-dimensional {coord} coordinate")
        values = np.asarray(data[coord].values)
        diffs = np.diff(values)
        if not len(values) or not np.isfinite(values).all() or not (np.all(diffs > 0) or np.all(diffs < 0)):
            raise ValueError(f"{coord} coordinates must be finite and strictly monotonic")

    if bbox is not None:
        if len(bbox) != 4:
            raise ValueError("bbox must be (west, south, east, north)")
        west, south, east, north = bbox
        if not np.isfinite(bbox).all() or west >= east or south >= north:
            raise ValueError("bbox must have finite bounds with west < east and south < north")
        data = data.where((data.lon >= west) & (data.lon <= east), drop=True)
        data = data.where((data.lat >= south) & (data.lat <= north), drop=True)
        if not data.sizes["lon"] or not data.sizes["lat"]:
            raise ValueError("bbox contains no grid points")
    return data


def normalize_channel(channel, *, limits=None, percentiles=(2, 98), gamma=1.0):
    """Scale a 2-D channel to [0, 1], preserving missing pixels as NaN.

    Limits default to finite-pixel percentiles of the selected scene. Pass
    fixed ``limits=(low, high)`` for comparable colours across scenes. A
    constant finite channel is displayed as zero; a wholly missing one errors.
    """
    values = np.asarray(channel, dtype=float)
    if values.ndim != 2:
        raise ValueError("A channel must be two-dimensional")
    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError("Channel has no finite pixels")
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError("gamma must be positive and finite")
    if limits is None:
        if len(percentiles) != 2 or not 0 <= percentiles[0] < percentiles[1] <= 100:
            raise ValueError("percentiles must satisfy 0 <= low < high <= 100")
        low, high = np.percentile(values[finite], percentiles)
    else:
        if len(limits) != 2 or not np.isfinite(limits).all() or limits[0] >= limits[1]:
            raise ValueError("limits must be finite and strictly increasing")
        low, high = limits
    result = np.full(values.shape, np.nan)
    result[finite] = 0 if high == low else np.clip((values[finite] - low) / (high - low), 0, 1) ** (1 / gamma)
    return result


def make_rgb(scene, channels, *, limits=None, percentiles=(2, 98), gamma=1.0):
    """Build an RGBA array from three named channels in red, green, blue order.

    ``limits`` may contain one (low, high) pair per channel, or None entries
    for percentile scaling. Pixels missing from any channel are transparent.
    The returned array follows the scene's latitude and longitude order.
    """
    if isinstance(channels, str):
        if channels not in COMPOSITES:
            raise ValueError(f"Unknown composite {channels!r}; choose from {tuple(COMPOSITES)}")
        channels = COMPOSITES[channels]
    if len(channels) != 3:
        raise ValueError("Exactly three channels are required")
    if limits is None:
        limits = (None, None, None)
    if len(limits) != 3:
        raise ValueError("limits must contain three pairs or None entries")
    layers = []
    for name, bounds in zip(channels, limits):
        if name not in scene:
            raise KeyError(f"Channel {name!r} is absent from the dataset")
        array = scene[name]
        if set(array.dims) != {"lat", "lon"}:
            raise ValueError(f"Channel {name!r} must have only lat and lon dimensions; select a time first")
        layers.append(normalize_channel(array.transpose("lat", "lon").values, limits=bounds, percentiles=percentiles, gamma=gamma))
    rgb = np.stack(layers, axis=-1)
    alpha = np.isfinite(rgb).all(axis=-1).astype(float)
    return np.dstack((np.nan_to_num(rgb), alpha))


def _axes(ax):
    if ax is None:
        _, ax = plt.subplots()
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    return ax


def plot_channel(data, channel=None, *, time=None, bbox=None, ax=None, colorbar=True, **kwargs):
    """Draw a single channel; return (axes, image). kwargs go to pcolormesh."""
    scene = select_scene(data, time=time, bbox=bbox)
    if isinstance(scene, xr.Dataset):
        if channel is None:
            raise ValueError("Choose a channel from the dataset")
        scene = scene[channel]
    elif channel is not None:
        raise ValueError("Do not pass channel when plotting a DataArray")
    if set(scene.dims) != {"lat", "lon"}:
        raise ValueError("The selected channel must have only lat and lon dimensions")
    ax = _axes(ax)
    image = ax.pcolormesh(scene.lon, scene.lat, scene.transpose("lat", "lon"), shading="nearest", **kwargs)
    if colorbar:
        ax.figure.colorbar(image, ax=ax, label=scene.attrs.get("units", ""))
    return ax, image


def plot_rgb(data, channels, *, time=None, bbox=None, limits=None, percentiles=(2, 98), gamma=1.0, ax=None, **kwargs):
    """Draw a three-channel composite; return (axes, image)."""
    scene = select_scene(data, time=time, bbox=bbox)
    rgba = make_rgb(scene, channels, limits=limits, percentiles=percentiles, gamma=gamma)
    ax = _axes(ax)
    image = ax.pcolormesh(scene.lon, scene.lat, rgba, shading="nearest", **kwargs)
    return ax, image


def plot_fire_points(labels, *, ax=None, lon="lon", lat="lat", **kwargs):
    """Overlay supplied longitude/latitude points; return (axes, scatter).

    Filter reports by date beforehand, using a verified common timezone. This
    function does not infer that unmarked locations are fire-free.
    """
    if lon not in labels or lat not in labels:
        raise ValueError("Labels need longitude and latitude columns; use egif_to_lonlat for EGIF")
    ax = _axes(ax)
    options = {"marker": "x", "c": "red", "s": 40, "label": "Punto de inicio registrado"}
    options.update(kwargs)
    points = ax.scatter(labels[lon], labels[lat], **options)
    return ax, points


def plot_scene_with_fires(data, labels, *, channel=None, channels=None, time=None, bbox=None, ax=None, image_kwargs=None, point_kwargs=None):
    """Plot a channel or RGB composite and overlay already selected fire points.

    Pass exactly one of ``channel`` or ``channels``. Labels must have lon/lat;
    use egif_to_lonlat first if needed. Returned artists can be customized.
    """
    if (channel is None) == (channels is None):
        raise ValueError("Choose exactly one of channel or channels")
    image_kwargs = {} if image_kwargs is None else dict(image_kwargs)
    point_kwargs = {} if point_kwargs is None else dict(point_kwargs)
    if channels is None:
        ax, image = plot_channel(data, channel, time=time, bbox=bbox, ax=ax, **image_kwargs)
    else:
        ax, image = plot_rgb(data, channels, time=time, bbox=bbox, ax=ax, **image_kwargs)
    # Keep the image limits: scatter otherwise expands them to include distant fires.
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    ax, points = plot_fire_points(labels, ax=ax, **point_kwargs)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return ax, image, points
