# Timestamps de incendios e imágenes satelitales

Para cruzar los partes de incendios con las imágenes hay que expresar ambos tiempos en una zona común y tener en cuenta que una imagen se adquiere durante un intervalo, no en un instante único.

## Labels EGIF

`Detectado` recoge la primera constancia de la existencia del incendio; no es necesariamente la hora de ignición. `Extinguido` recoge la hora registrada de extinción, distinta de la de control. El parte solicita anotar los tiempos con la mayor exactitud posible. [Instrucciones del parte de incendio forestal, apartado 3.2](https://servicio.mapa.gob.es/incendios/Content/templates/InstruccionesEGIFW_2011_v%20Parte%203.6.pdf).

**Hipótesis de trabajo: las dos fechas están en la hora local del lugar del incendio.** El [anexo II del Reglamento (CE) 1737/2006](https://www.boe.es/buscar/doc.php?id=DOUE-L-2006-82294) y la [especificación de la base europea de incendios](https://data.effis.emergency.copernicus.eu/effis/reports-and-publications/effis-related-publications/eudb_tech_spec_final_2register.pdf) indican hora local para la primera alerta y la extinción. Esto respalda la hipótesis, pero no confirma directamente la zona horaria de los campos de esta exportación EGIF: la primera alerta europea y la detección del parte no tienen exactamente la misma definición, y las instrucciones españolas consultadas no especifican la zona horaria.

El CSV procesado disponible conserva la hora de detección, por ejemplo `2023-01-01 18:17:00`, y la de extinción, pero no incluye una zona horaria explícita. Al cargarlo, `read_labels_v1` interpreta ambas como hora local según la comunidad y las convierte a UTC; la tabla original devuelta conserva los valores de entrada. Conviene verificar la precisión y los posibles valores ausentes de cada registro.

El lector asigna `Atlantic/Canary` a Canarias y `Europe/Madrid` al resto, y después convierte a UTC. La diferencia depende de la fecha: en la península son UTC+1 en invierno y UTC+2 en verano. Los cambios de hora pueden producir horas locales ambiguas o inexistentes: el lector las convierte en `NaT` y deben revisarse; también rechaza los registros sin comunidad.

## Imágenes Meteosat / SEVIRI

La [guía de EUMETSAT para HRSEVIRI nivel 1.5](https://user.eumetsat.int/resources/user-guides/msg-high-rate-seviri-level-1-5-data-guide) describe un ciclo nominal de 15 minutos: unos 12,5 minutos de adquisición del disco y 2,5 de calibración, retorno y estabilización. Meteosat es geoestacionario: se trata del ciclo de barrido del instrumento, no del tiempo que tarda el satélite en dar una vuelta alrededor de la Tierra. El instante de adquisición de un punto depende de su posición dentro del barrido.

Los metadatos del Zarr del primer trimestre de 2020 recogen un producto cuyo inicio de adquisición fue `2019-12-31 23:45:10Z` y su fin `2019-12-31 23:57:43Z`; `Z` indica UTC. En el notebook, el primer nombre de archivo listado es `HRSEVIRI_20200101T0000.nc`. Esto es compatible con que el nombre represente el **final nominal del ciclo** y no el final exacto de adquisición. Es una inferencia a partir de este ejemplo: hay que verificar los metadatos de los NetCDF originales para confirmar la correspondencia individual y la convención de todos los archivos.

El preprocesamiento extrae literalmente la fecha del nombre del NetCDF y la guarda como coordenada `time` sin zona horaria explícita. No guarda en esa coordenada los tiempos reales de inicio y fin de adquisición. Los atributos globales del Zarr no deben considerarse los tiempos propios de todas las escenas del trimestre.

## Consecuencias para el cruce

- Una duración registrada de al menos 30 minutos proporciona oportunidades de observación si existen todas las imágenes del ciclo de 15 minutos y las horas registradas son fiables. No garantiza que el incendio sea visible: influyen, entre otros factores, las nubes, la intensidad y el tamaño del fuego.
- Comprueba la cadencia y los huecos del conjunto realmente usado. El script [`sync_satelite.sh`](../scripts/sync_satelite.sh) descarga únicamente archivos cuya hora termina en `00`; en ese subconjunto horario, un incendio de 30 minutos puede no coincidir con ninguna observación.
- Compara las fechas en UTC y, cuando sea posible, usa el instante de observación del punto o el intervalo real de adquisición. Un timestamp nominal de fin de ciclo no es el instante exacto en que se observó el incendio.
- La detección puede ser posterior a la ignición y la hora registrada de extinción puede diferir del fin de las llamas visibles. Esas incertidumbres afectan a las etiquetas incluso si las zonas horarias son correctas.
