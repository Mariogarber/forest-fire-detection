# Guía de visualización de imágenes satelitales

Esta guía usa las funciones de [`viz/satellite.py`](../src/forest_fire_detection/viz/satellite.py) desde un notebook. Permiten dibujar un canal, combinar tres canales en color, recortar por coordenadas y añadir puntos de incendios EGIF.

## 1. Preparar los datos

Se necesita un `xarray.Dataset` con canales como variables y coordenadas unidimensionales `lat` y `lon`, en grados. El dataset puede tener una dimensión `time`. Si contiene más de una fecha, hay que seleccionar una imagen; la selección es exacta y falla si esa fecha no existe. El recorte usa `(oeste, sur, este, norte)` e incluye los puntos de la rejilla situados en los límites.

En un notebook donde ya tengas abierto el dataset trimestral:

```python
import matplotlib.pyplot as plt
from forest_fire_detection.preprocessing.coords import egif_to_lonlat
from forest_fire_detection.viz.satellite import (
    COMPOSITES,
    make_rgb,
    normalize_channel,
    plot_channel,
    plot_fire_points,
    plot_rgb,
    plot_scene_with_fires,
    select_scene,
)

# Sustituye dataset_2020_q1 por el nombre de tu variable.
dataset = dataset_2020_q1
print(dataset)
print("Canales:", list(dataset.data_vars))
print("Primeras fechas:", dataset.time.values[:5])
```

También puedes abrir los NetCDF usando las funciones de preparación del proyecto:

```python
from forest_fire_detection.preprocessing.satellite import (
    SATELLITE_RAW_REPOSITORY,
    list_netcdf_files,
    load_netcdfs_by_quarters_lazy,
)

archivos = list_netcdf_files(SATELLITE_RAW_REPOSITORY)
dataset = load_netcdfs_by_quarters_lazy(archivos, year=2020, quarter=1)
```

O, si ya guardaste un trimestre en Zarr, utiliza `xr.open_zarr(ruta_al_zarr)`. Las funciones de dibujo y el cálculo de percentiles leen los píxeles de la escena seleccionada, aunque el dataset esté respaldado por Dask; un recorte ayuda a reducir el trabajo.

## 2. Mostrar un canal y hacer zoom

```python
# Escoge una fecha existente en tu dataset y comprueba su zona horaria.
fecha = "2020-01-01T12:00:00"
# Ejemplo: zona de la península ibérica, en grados.
recorte = (-6.0, 39.0, -3.0, 42.0)

ax, imagen = plot_channel(
    dataset,
    "IR10.8",
    time=fecha,
    bbox=recorte,
    cmap="inferno",
)
ax.set_title(f"IR10.8 — {fecha}")
plt.show()
```

Quita `bbox` para mostrar toda la escena. `cmap` y otros argumentos adicionales se pasan a `pcolormesh` de Matplotlib; puedes usar `vmin` y `vmax` para fijar la escala. Por defecto se añade una barra de color; `colorbar=False` la omite. La función devuelve el eje y el objeto de la imagen para personalizarlos o guardar la figura con `ax.figure.savefig("escena.png", dpi=200, bbox_inches="tight")`.

Para preparar un recorte y reutilizarlo en varias visualizaciones:

```python
escena = select_scene(dataset, time=fecha, bbox=recorte)
print(escena.sizes)
ax, imagen = plot_channel(escena, "IR10.8", cmap="gray")
```

Si ya tienes un `DataArray` de un canal, pásalo sin el nombre del canal: `plot_channel(escena["IR10.8"], cmap="gray")`.

## 3. Combinar tres canales en RGB

Los canales se indican en orden **rojo, verde y azul**. Los nombres deben existir en el dataset:

```python
ax, imagen = plot_rgb(
    dataset,
    channels=("NIR1.6", "VIS0.8", "VIS0.6"),
    time=fecha,
    bbox=recorte,
    percentiles=(2, 98),
    gamma=1.0,
)
ax.set_title("Composición RGB")
plt.show()
```

Hay dos combinaciones predefinidas, consultables con `print(COMPOSITES)`:

| Nombre | Rojo | Verde | Azul |
| --- | --- | --- | --- |
| `visible` | `VIS0.6` | `VIS0.8` | `NIR1.6` |
| `natural_color` | `NIR1.6` | `VIS0.8` | `VIS0.6` |

Por ejemplo, `plot_rgb(dataset, "natural_color", time=fecha)` usa la segunda combinación. Son composiciones para explorar datos: sus nombres no garantizan color verdadero ni calibración física.

Por defecto cada canal se escala entre los percentiles 2 y 98 de **la escena y el recorte seleccionados**. Esto facilita ver detalles, pero los colores de dos fechas o recortes no son necesariamente comparables. Para compararlos, usa los mismos límites fijos en el orden RGB, adecuados a las unidades y rangos de tus datos:

```python
# Valores ilustrativos: sustitúyelos por límites adecuados a tus canales.
limites_rgb = [(0, 100), (0, 100), (0, 100)]
ax, imagen = plot_rgb(dataset, "natural_color", time=fecha,
                      bbox=recorte, limits=limites_rgb, gamma=1.2)
```

`gamma` debe ser positivo; los píxeles sin datos en cualquiera de los tres canales quedan transparentes. Para trabajar con los datos preparados sin dibujarlos, `normalize_channel(escena["IR10.8"], limits=(0, 300))` devuelve una matriz normalizada y `make_rgb(escena, "natural_color")` devuelve una matriz RGBA. Sus límites de ejemplo deben adaptarse a las unidades reales.

## 4. Superponer puntos de incendios

El conversor EGIF necesita las columnas `CoordenadaX`, `CoordenadaY`, `Huso` y `Datum`. Devuelve una copia con columnas `lon` y `lat` en WGS84:

```python
# partes es el DataFrame procesado de EGIF que ya tienes cargado.
# Selecciona los registros que realmente quieras comparar con la imagen.
partes_seleccionados = partes.copy()  # Sustituye por tu filtro temporal.
puntos = egif_to_lonlat(partes_seleccionados)

ax, imagen, marcas = plot_scene_with_fires(
    dataset,
    puntos,
    channels="natural_color",
    time=fecha,
    bbox=recorte,
    point_kwargs={"marker": "x", "c": "red", "s": 40},
)
ax.set_title(f"Imagen y puntos de inicio — {fecha}")
ax.legend()
plt.show()
```

La función dibuja los puntos suministrados; **no filtra los partes por fecha**. Antes de compararlos con una imagen, revisa las zonas horarias y la precisión de `Detectado` y `Extinguido`: el CSV disponible conserva la hora, pero no explicita su zona horaria. Consulta [timestamps](timestamps.md) y el [diccionario EGIF](diccionario-datos-egif.md). Cada marca es un punto de inicio registrado, no el perímetro quemado; la ausencia de una marca no demuestra que no haya habido fuego.

La conversión presupone el hemisferio norte y admite `ETRS89` y `ED50` para husos 28–38, y `WGS84` para husos 1–60. Los registros sin coordenadas numéricas, datum o huso admitidos provocan un error: revísalos o filtra los registros antes de convertirlos. Si ya tienes longitud y latitud en grados, puedes usar directamente un DataFrame con columnas `lon` y `lat`.

También puedes componer el gráfico paso a paso o usar un solo canal:

```python
# Composición manual: útil para reutilizar ejes o añadir otras capas.
ax, imagen = plot_channel(dataset, "IR10.8", time=fecha, bbox=recorte)
ax, marcas = plot_fire_points(puntos, ax=ax, marker="x", c="red")
ax.legend()

# Función integrada con un solo canal.
ax, imagen, marcas = plot_scene_with_fires(
    dataset, puntos, channel="IR10.8", time=fecha, bbox=recorte,
    image_kwargs={"cmap": "inferno"}, point_kwargs={"s": 30},
)
```

La función integrada conserva los límites de la imagen si hay puntos fuera del recorte. Al usar `plot_fire_points` por separado, Matplotlib puede ampliar los límites del eje para incluirlos.

## 5. Varias imágenes en una figura

```python
fig, ejes = plt.subplots(1, 2, figsize=(12, 5))
plot_channel(dataset, "IR10.8", time=fecha, bbox=recorte,
             ax=ejes[0], cmap="inferno")
plot_rgb(dataset, "natural_color", time=fecha, bbox=recorte, ax=ejes[1])
ejes[0].set_title("IR10.8")
ejes[1].set_title("Composición RGB")
fig.tight_layout()
plt.show()
```

## Problemas frecuentes

- **Se pide seleccionar una fecha:** pasa `time=...` si hay varias observaciones, o selecciona una con `select_scene`.
- **No se encuentra la fecha:** comprueba `dataset.time.values`; no se elige automáticamente la imagen más cercana.
- **El recorte no contiene puntos:** revisa el orden `(oeste, sur, este, norte)` y los valores de `dataset.lon` y `dataset.lat`.
- **Falta un canal:** consulta `dataset.data_vars` y utiliza sus nombres exactos.
- **Falla la conversión EGIF:** revisa las columnas, sus valores y los datum y husos admitidos.
- **Los colores cambian entre imágenes:** fija `limits` para cada canal en vez de usar percentiles calculados por escena.
