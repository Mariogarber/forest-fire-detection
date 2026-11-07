# Diccionario de datos: incendios forestales EGIF

Este documento describe las 22 columnas seleccionadas en `processed_typed_data` del notebook [`preprocessing_v1.ipynb`](../notebooks/preprocessing_v1.ipynb). Sus nombres y valores coinciden con el listado de partes de la **Estadística General de Incendios Forestales (EGIF)**, la base nacional que el MITECO elabora a partir de los partes remitidos por las comunidades autónomas. El nivel de consolidación puede variar por provincia. Una fila del listado representa un parte de incendio; no es un píxel, un perímetro ni necesariamente un municipio afectado. [1]

Las definiciones se basan principalmente en el formulario y las instrucciones del Parte de Incendio Forestal. Cuando una interpretación depende del procesamiento del notebook o no está confirmada para esta exportación, se indica expresamente. [2, 3]

## Identificación y localización administrativa

### `NumeroParte`

Identificador del parte de incendio. El procedimiento oficial establece diez dígitos: cuatro para el año, dos para el código INE de la provincia y cuatro para un número asignado preferentemente de forma correlativa. Por ejemplo, `2023010001` se interpreta como año `2023`, provincia `01` y número `0001`. Es una clave de identificación, no una cantidad con la que realizar operaciones aritméticas. El notebook la convierte a texto. [3, apartado 3.1]

### `Comunidad`

Comunidad autónoma donde se registra el fuego; por ejemplo, `EUSKADI`. Es una etiqueta administrativa, no una coordenada ni la descripción completa del área quemada. [3, apartado 3.1]

### `Provincia`

Provincia donde se registra el fuego; por ejemplo, `ALAVA`. Forma parte de la localización administrativa del parte. [3, apartado 3.1]

### `Municipio`

Término municipal **donde se inició** el incendio; por ejemplo, `ELCIEGO`. El fuego puede extenderse a otros municipios, de modo que este valor no enumera todas las localidades afectadas. Las instrucciones contemplan casos especiales de incendios iniciados en otra provincia u otro país. [3, apartado 3.1]

### `ComarcaIsla`

Comarca o isla donde se produjo el fuego; por ejemplo, `RIOJA ALAVESA`. Es una descripción territorial administrativa del suceso, no una celda geográfica de tamaño fijo. [3, apartado 3.1]

### `EntidadMenor`

Entidad de población menor asociada a la localización, como una parroquia, aldea o pedanía, cuando procede en la provincia. Es un campo opcional: un valor vacío no demuestra por sí solo que no exista una entidad menor cercana. [3, apartado 3.1]

### `NumeroMunicipiosAfectados`

Número total de términos municipales afectados por el siniestro. Por ejemplo, `1` indica un municipio afectado, mientras que `Municipio` identifica el de origen. El número no indica cuáles son los demás municipios ni qué superficie corresponde a cada uno. [3, apartado 3.1]

## Localización cartográfica

### `Cuadricula`

Código de la cuadrícula del **Mapa Militar a escala 1:250.000** correspondiente al punto de inicio; por ejemplo, `B06`. El formulario identifica esa localización mediante **hoja y cuadrícula juntas**. El notebook descarta `Hoja`, aunque estaba presente en los datos originales: por tanto, `Cuadricula` por sí sola no es una referencia cartográfica completa ni debe suponerse única en todo el país. Si se necesita esa referencia, conserva también `Hoja`. [2, 3, apartado 3.1]

Esta cuadrícula es una referencia cartográfica del origen. No representa un píxel satelital ni delimita la zona quemada.

### `Huso`

Zona de la proyección cartográfica **UTM** en la que se expresan X e Y. Por ejemplo, `30` identifica el huso 30. El mismo par numérico de coordenadas puede representar lugares distintos si se interpreta con otro huso. Para localizar un punto se necesitan conjuntamente el huso, X, Y y el datum; además, el sistema de coordenadas debe identificar el hemisferio cuando proceda. [2, 3, apartado 3.1]

### `CoordenadaX`

Coordenada UTM horizontal o **este** (*easting*) del punto de inicio registrado, en metros. Por ejemplo, `532928` no son grados de longitud ni una distancia al incendio desde el origen del mapa: es un valor de la proyección UTM. Las instrucciones indican que las coordenadas no deben situarse fuera del perímetro del incendio. [3, apartado 3.1]

### `CoordenadaY`

Coordenada UTM vertical o **norte** (*northing*) del mismo punto, en metros. Por ejemplo, `4706365` no es una latitud en grados. Junto con X, huso y datum permite representar o transformar la ubicación; no describe la extensión ni la forma de la superficie quemada. [3, apartado 3.1]

### `Datum`

Referencia geodésica en la que se tomaron las coordenadas, como `ETRS89`. Determina, junto con la proyección y el huso, cómo se sitúan los valores X e Y sobre la Tierra. Las instrucciones del parte establecen que se indique el datum y recomiendan ETRS89. No debe suponerse que todos los registros usan el mismo datum sin comprobarlo. [3, apartado 3.1]

**Ejemplo del notebook:** `Datum=ETRS89`, `Huso=30`, `CoordenadaX=532928` y `CoordenadaY=4706365` describen un punto en ETRS89 / UTM zona 30N (`EPSG:25830`). Para compararlo con datos expresados en longitud y latitud, hay que transformar el punto desde su sistema de origen al sistema de destino. El código EPSG del ejemplo no debe aplicarse automáticamente a filas con otro huso o datum. Un punto de origen tampoco equivale al perímetro quemado ni permite conocer qué píxeles ardieron.

### `NumeroPuntosInicioIncendio`

Número de puntos de inicio del incendio registrados en el parte. Un `1` indica un punto registrado; un valor mayor indica varios. El campo es un recuento: las columnas X e Y que conserva el notebook forman un único par y no aportan por sí solas las coordenadas de cada punto adicional. [3, apartado 3.1]

## Tiempo, causa e interfaz urbano-forestal

### `Detectado`

Fecha y hora de detección del incendio registradas en el parte. Detección significa el momento en que se detectó el fuego; no debe identificarse automáticamente con el momento exacto de ignición. El formulario recoge día, mes, año, hora y minutos. [2, 3, apartado 3.2]

**Tratamiento actual:** el notebook convierte el dato original a fecha y hora antes de guardar el CSV. El CSV disponible conserva la hora; por ejemplo, `2023-01-01 18:17:00`. La fecha no incluye una zona horaria explícita.

### `Extinguido`

Fecha y hora registradas de extinción. En el notebook se convierte desde el formato `día/mes/año hora:minuto:segundo`; por ejemplo, `01/01/2023 20:41:00`. La extinción es un hito distinto de la detección y del control del incendio. [2, 3, apartado 3.2]

Esta columna y `Detectado` conservan la hora en el CSV disponible, pero eso no garantiza que la duración calculada coincida exactamente con el tiempo de fuego visible. Las fechas no incluyen zona horaria explícita. La hora local es la hipótesis de trabajo respaldada por la documentación europea, pendiente de confirmación directa para esta exportación; consulta [timestamps](timestamps.md) antes de compararlas con el satélite.

### `Causa`

Causa registrada del siniestro, con un código y una descripción. En el notebook aparecen, por ejemplo, `[400] Intencionado`, `[213] Quema de restos agrícolas (viñas,etc)` y `[500] Desconocida`. El formulario distingue también si la causa es cierta o supuesta y, para incendios intencionados, recoge una motivación. [2, apartado 4]

La columna no expresa necesariamente el mismo nivel de detalle en todas las filas: una puede contener una categoría general y otra una actividad más específica. La motivación es un campo distinto y se descartó en la selección del notebook. Tampoco debe interpretarse `Desconocida` como ausencia de causa.

### `TipoInterfazAfectado`

Tipo de interfaz urbano-forestal afectada o que pudo verse afectada durante el desarrollo del incendio. La interfaz es el territorio donde entran en contacto o se intersecan los usos urbanos y forestales. El formulario contempla **compacta** (núcleo, polígono o urbanización compacta), **diseminada** (edificación o urbanización dispersa) y **aislada** (vivienda o actividad industrial aislada); se pueden indicar varias tipologías. La casilla de afectación durante el desarrollo es distinta de indicar que el incendio se inició junto a una zona de interfaz. [3, apartado 3.10.3]

En la salida del notebook aparecen cadenas como `2`, `3` y `23`, además de espacios en blanco. **No se ha confirmado el significado exacto de esos códigos en esta exportación**: no debe suponerse que `23` sea un número ordinal ni asignarse cada dígito a una tipología sin consultar el catálogo correspondiente. La documentación de EGIF indica que las tablas `CodXXXXX` relacionan códigos con textos. El campo original `AfectoZonasInterfazUrbanoForestal`, que expresa la pregunta general de afectación, quedó fuera de la selección; conservarlo ayudaría a interpretar los vacíos, que no deben convertirse automáticamente en «no». [4]

## Superficies afectadas

Las cinco columnas siguientes representan superficies afectadas o recorridas por el fuego, expresadas en **hectáreas** (1 ha = 10.000 m²). Los valores del archivo original aparecen con coma decimal; el notebook la sustituye por un punto y los convierte a números. [2, apartado 9.3]

### `SuperficieArbolada`

Superficie **forestal arbolada** afectada. Un valor `0,04` significa 0,04 ha, es decir, 400 m². No es un recuento de árboles ni identifica las especies afectadas. [2, 3]

### `SuperficieNoArbolada`

Superficie **forestal no arbolada** afectada. El detalle del parte de monte incluye, entre otras clases, monte abierto, matorral y vegetación herbácea. «No arbolada» no significa «no forestal»: es una parte de la superficie forestal. [2, 3]

### `SuperficieTotalForestal`

Superficie forestal afectada total; comprende la arbolada y la no arbolada. Por ejemplo, en la primera fila del notebook `0,00 + 2,06 = 2,06 ha`. Puede comprobarse la relación `SuperficieTotalForestal ≈ SuperficieArbolada + SuperficieNoArbolada`, admitiendo posibles diferencias de precisión o calidad de datos. No representa por sí sola toda la superficie afectada cuando también han ardido terrenos no forestales. [2, apartado 9.3]

### `SuperficieAgricola`

Superficie agrícola afectada, expresada por separado de la superficie forestal. Por ejemplo, `0,40` representa 0,40 ha agrícolas. No debe confundirse con la superficie forestal no arbolada. [2, apartado 9.3]

### `OtrasSuperficiesNoforestales`

Otras superficies no forestales afectadas que el parte recoge por separado de las agrícolas; el formulario cita las urbanas como ejemplo. Es una superficie en hectáreas, no un indicador de sí/no. [2, apartado 9.3]

Para obtener la superficie afectada incluyendo las categorías no forestales, se pueden sumar `SuperficieTotalForestal + SuperficieAgricola + OtrasSuperficiesNoforestales`, siempre que los tres valores estén disponibles. No sumes además `SuperficieArbolada` y `SuperficieNoArbolada`: ya están incluidas en el total forestal. Un valor ausente no equivale automáticamente a cero.

## Aspectos prácticos del notebook

- `pd.to_numeric(..., errors="coerce")` convierte en valores ausentes las cantidades que no se puedan interpretar como números. Conviene revisar esos casos antes de analizarlos.
- Hay cadenas visualmente vacías que contienen un espacio no separable (`\u00a0`). Conviene normalizar espacios y distinguir valores ausentes de categorías reales antes de agrupar.
- Los datos seleccionados describen sucesos registrados y sus consecuencias. Superficies, causa o extinción pueden conocerse después del inicio: si se construye un modelo que prediga en el momento de detección, utilizarlas como entradas podría introducir información futura.
- El notebook selecciona el primer archivo devuelto por `os.listdir` en la carpeta procesada. Si hay varios archivos, comprueba cuál se ha elegido antes de interpretar el conjunto final.

## Fuentes oficiales

1. [MITECO: Estadística General de Incendios Forestales (EGIF)](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html). Presenta la base, el buscador y la documentación oficial.
2. [MITECO: formulario del Parte de Incendio Forestal](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/parteincendioforestal_web_tcm30-132604.pdf). Muestra los campos y las unidades del parte.
3. [MITECO: instrucciones de cumplimentación del Parte de Incendio Forestal](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/instrucciones_parte_incendio_tcm30-512355.pdf). Describe la interpretación y cumplimentación de los campos.
4. [MITECO: interpretación de la base de datos EGIFWEB](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Interpretaci%C3%B3n%20BD_Egifweb.pdf). Explica la organización de las tablas y los catálogos de códigos.
