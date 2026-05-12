import logging
import os
from multiprocessing import Pool

import pandas as pd
import xarray as xr
from tqdm.auto import tqdm

from era5epw.utils import now_utc

# Earth Data Hub base URL template
EDH_URL_TEMPLATE = (
    "https://edh:{token}@data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr"
)

# Mapping from CDS variable names to EDH short names
CDS_TO_EDH_VARS = {
    "2m_temperature": "t2m",
    "2m_dewpoint_temperature": "d2m",
    "surface_pressure": "sp",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "total_cloud_cover": "tcc",
    "uv_visible_albedo_for_direct_radiation": "aluvd",
    "snow_depth": "sd",
    "soil_temperature_level_1": "stl1",
    "total_precipitation": "tp",
}

# Variables available in the EDH dataset
EDH_AVAILABLE_VARS = list(CDS_TO_EDH_VARS.values())

_edh_token = None


def load_edh_token() -> str:
    """Load the Earth Data Hub personal access token from environment variable or file.

    The token is looked up in order:
    1. Environment variable EDH_TOKEN
    2. File ~/.edh_token (plain text, first line)
    """
    global _edh_token
    if _edh_token is not None:
        return _edh_token

    if os.getenv("EDH_TOKEN"):
        _edh_token = os.getenv("EDH_TOKEN")
        return _edh_token

    token_file = os.path.expanduser("~/.edh_token")
    try:
        with open(token_file) as f:
            token = f.readline().strip()
            assert token, "EDH token is empty. Please check your ~/.edh_token file."
            _edh_token = token
            return _edh_token
    except FileNotFoundError:
        raise FileNotFoundError(
            "Earth Data Hub token not found. Set the EDH_TOKEN environment variable "
            "or create '~/.edh_token' with your personal access token."
        )


def _normalize_longitude_input(longitude: float) -> float:
    """Convert longitude from [-180, 180] range to [0, 360] range used by EDH.

    :param longitude: Longitude in [-180, 180] range.
    :return: Longitude in [0, 360] range.
    """
    if longitude < 0:
        return 360.0 + longitude
    return longitude


def _normalize_longitude_output(longitude: float) -> float:
    """Convert longitude from [0, 360] range back to [-180, 180] range.

    :param longitude: Longitude in [0, 360] range.
    :return: Longitude in [-180, 180] range.
    """
    if longitude > 180:
        return longitude - 360.0
    return longitude


def _fetch_edh_chunk(args: tuple[str, list[str], str, str, float, float]) -> pd.DataFrame:
    """Fetch a chunk of data from EDH for a specific time range.

    This function is designed to be called in parallel via multiprocessing.

    :param args: Tuple of (url, variables, start_date, end_date, latitude, longitude_edh)
    :return: DataFrame with the fetched data.
    """
    url, variables, start_date, end_date, latitude, longitude_edh = args

    ds = xr.open_dataset(url, engine="zarr", chunks={})
    subset = ds[variables]
    time_slice = subset.sel(valid_time=slice(start_date, end_date))
    point = time_slice.sel(
        latitude=latitude,
        longitude=longitude_edh,
        method="nearest",
    )

    # Actual download happens here when compute() is called
    df = point.compute().to_dataframe()
    # Drop non-essential coordinate columns that come from the zarr dataset
    cols_to_drop = [c for c in ["latitude", "longitude", "number", "surface"] if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    return df


def download_era5_data_edh(
    variables: list[str],
    year: int,
    latitude: float,
    longitude: float,
    parallel_exec_nb: int = 4,
    time_zone: int | None = None,
) -> pd.DataFrame:
    """Download ERA5 data from Earth Data Hub (EDH) for a specific year and location.

    Data is lazily loaded from a zarr archive and only downloaded upon compute(). The
    longitude range in EDH is [0, 360], so user inputs are normalized automatically.

    :param variables: List of CDS-style variable names (e.g., '2m_temperature').
    :param year: The year of the data. Full year will be downloaded.
    :param latitude: The latitude for the data point.
    :param longitude: The longitude for the data point (in [-180, 180] range).
    :param parallel_exec_nb: Number of parallel executions for downloading data chunks.
    :param time_zone: Time zone offset from UTC. If provided, will adjust date range to
        fetch additional data needed for time zone conversion.
    :return: A DataFrame containing the downloaded data, combined on the 'valid_time'
        dimension.
    """
    token = load_edh_token()
    url = EDH_URL_TEMPLATE.format(token=token)

    # Map CDS variable names to EDH short names
    edh_vars = []
    for var in variables:
        if var in CDS_TO_EDH_VARS:
            edh_var = CDS_TO_EDH_VARS[var]
            if edh_var not in edh_vars:
                edh_vars.append(edh_var)
        else:
            logging.warning(f"Variable '{var}' is not available in Earth Data Hub. Skipping.")

    if not edh_vars:
        raise ValueError(
            f"None of the requested variables are available in Earth Data Hub: {variables}"
        )

    # Normalize longitude to [0, 360] range
    longitude_edh = _normalize_longitude_input(longitude)

    # Check data availability: EDH data is available until last closed month
    now = now_utc()
    if year > now.year:
        raise ValueError(
            f"Cannot download data for year {year}. "
            f"Earth Data Hub data is available until the last closed month."
        )

    # Split into monthly chunks for parallel processing
    chunks: list[tuple[str, list[str], str, str, float, float]] = []

    # Determine the months to fetch
    if time_zone is not None and time_zone > 0:
        # Add previous year's last day
        chunks.append(
            (
                url,
                edh_vars,
                f"{year - 1}-12-31",
                f"{year - 1}-12-31T23:59:59",
                latitude,
                longitude_edh,
            )
        )

    for month in range(1, 13):
        if year == now.year and month > now.month:
            break  # Skip future months
        month_start = f"{year}-{month:02d}-01"
        if month == 12:
            month_end = f"{year}-12-31T23:59:59"
        else:
            month_end = f"{year}-{month + 1:02d}-01"
        chunks.append((url, edh_vars, month_start, month_end, latitude, longitude_edh))

    if time_zone is not None and time_zone < 0:
        # Add next year's first day
        chunks.append(
            (
                url,
                edh_vars,
                f"{year + 1}-01-01",
                f"{year + 1}-01-01T23:59:59",
                latitude,
                longitude_edh,
            )
        )

    if not chunks:
        raise ValueError(
            f"No valid data chunks could be created for year {year} and variables {variables}."
        )

    tqdm.write(
        f"Fetching {len(chunks)} chunks from Earth Data Hub "
        f"with {parallel_exec_nb} parallel requests for {year}..."
    )

    # Create progress bar for EDH requests
    edh_progress = tqdm(
        total=len(chunks), desc="EDH requests", unit="chunk", position=1, leave=False
    )

    dfs: list[pd.DataFrame] = []
    with Pool(parallel_exec_nb) as pool:
        result = pool.map_async(_fetch_edh_chunk, chunks)

        while not result.ready():
            result.wait(timeout=1)

        dfs = result.get()

    edh_progress.n = len(chunks)
    edh_progress.refresh()
    edh_progress.close()

    # Concatenate all DataFrames and sort by index
    combined_df = pd.concat(dfs, axis=0, ignore_index=False).sort_index().drop_duplicates()

    # Rename 'aluvd' to 'aluvp' to match what main.py expects from CDS output
    if "aluvd" in combined_df.columns:
        combined_df = combined_df.rename(columns={"aluvd": "aluvp"})

    # Rename 'sd' to 'sde' to match what main.py expects from CDS (ERA5-Land) output
    if "sd" in combined_df.columns:
        combined_df = combined_df.rename(columns={"sd": "sde"})

    return combined_df


if __name__ == "__main__":
    df = download_era5_data_edh(
        variables=[
            "2m_temperature",
            "2m_dewpoint_temperature",
            "surface_pressure",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_cloud_cover",
            "uv_visible_albedo_for_direct_radiation",
            "snow_depth",
            "total_precipitation",
            "soil_temperature_level_1",
        ],
        year=2025,
        latitude=47.2184,
        longitude=-1.5533,
        parallel_exec_nb=4,
        time_zone=1,
    )

    print(df.head(5))
    print(df.info())
