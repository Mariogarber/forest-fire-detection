from .labels import read_labels_v1
import pandas as pd
from .coords import egif_to_lonlat

def read_labels(file_path: str, version: str = "v1") -> list[pd.DataFrame]:
    """Reads the labels from a CSV file and returns a list of DataFrames with 
    the specified data types based on the version.

    The first DataFrame in the list is the raw data, and the second DataFrame 
    is the processed data with the correct types.

    Args:
        file_path (str): The path to the CSV file containing the labels.
        version (str, optional): The version of the label format. Defaults to "v1".

    Returns:
        list[pd.DataFrame]: A list containing the raw and processed DataFrames.
    """
    if version == "v1":
        return read_labels_v1(file_path)
    raise ValueError(f"Unsupported version: {version}")