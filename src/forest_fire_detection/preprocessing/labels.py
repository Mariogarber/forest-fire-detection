import pandas as pd
import numpy as np

TYPING_LABELS_V1 = {
    "NumeroParte": str,
    "Comunidad": str,
    "Provincia": str,
    "Municipio": str,
    "ComarcaIsla": str,
    "EntidadMenor": str,
    "NumeroMunicipiosAfectados": int,
    "Cuadricula": str,
    "Huso": int,
    "CoordenadaX": float,
    "CoordenadaY": float,
    "Datum": str,
    "NumeroPuntosInicioIncendio": int,
    "Causa": str,
    "TipoInterfazAfectado": str,
    "SuperficieArbolada": float,
    "SuperficieNoArbolada": float,
    "SuperficieTotalForestal": float,
    "SuperficieAgricola": float,
    "OtrasSuperficiesNoforestales": float
}

def read_labels_v1(file_path: str) -> list[pd.DataFrame]:
    """Reads the labels from a CSV file and returns a list of DataFrames with 
    the specified data types.

    The first DataFrame in the list is the raw data, and the second DataFrame 
    is the processed data with the correct types. Dates are assumed to be
    local time and converted to UTC; ambiguous or nonexistent times become NaT.
    """
    raw_data = pd.read_csv(file_path)
    surface_columns = [column for column in raw_data.columns if "Superficie" in column]
    useful_columns = ["NumeroParte", "Comunidad", "Provincia", "Municipio", "ComarcaIsla", "EntidadMenor", "NumeroMunicipiosAfectados",
                  "Cuadricula", "Huso", "CoordenadaX", "CoordenadaY", "Datum", "NumeroPuntosInicioIncendio", "Detectado", "Extinguido",
                  "Causa", "TipoInterfazAfectado"] + surface_columns

    processed_filtered_data = raw_data[useful_columns]
    processed_typed_data = processed_filtered_data.copy()

    for column, dtype in TYPING_LABELS_V1.items():
        if dtype is float:
            values = (
                processed_typed_data[column]
                .astype("string")
                .str.strip()
                .str.replace(",", ".", regex=False)
            )
            processed_typed_data[column] = pd.to_numeric(values, errors="coerce")

    if processed_typed_data["Comunidad"].isna().any() or processed_typed_data["Comunidad"].str.strip().eq("").any():
        raise ValueError("La comunidad es necesaria para determinar la zona horaria")

    processed_typed_data = processed_typed_data.astype(TYPING_LABELS_V1)

    canarias = processed_typed_data["Comunidad"].str.strip().str.upper().eq("CANARIAS")
    for column, date_format in [("Detectado", "%Y-%m-%d %H:%M:%S"), ("Extinguido", "%d/%m/%Y %H:%M:%S")]:
        dates = pd.to_datetime(processed_typed_data[column], format=date_format)
        utc_dates = pd.Series(pd.NaT, index=dates.index, dtype="datetime64[ns, UTC]")
        for mask, timezone in [(canarias, "Atlantic/Canary"), (~canarias, "Europe/Madrid")]:
            utc_dates.loc[mask] = (
                dates.loc[mask].dt.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT")
                .dt.tz_convert("UTC")
            )
        processed_typed_data[column] = utc_dates

    processed_typed_data = processed_typed_data.sort_values(["Detectado", "Provincia", "Municipio"]).reset_index(drop=True)
    return [raw_data, processed_typed_data]
