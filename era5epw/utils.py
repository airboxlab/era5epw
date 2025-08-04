import datetime
import glob
import logging
import os
import os.path
import random
import time
import zipfile
from calendar import monthrange
from types import TracebackType

import cdsapi
import pandas as pd
import xarray as xr
from ecmwf.datastores import legacy_client

_api_key = None


class QuietEra5LegacyClientLoggingContext:
    """An override of the ecmwf.datastores.legacy_client.LoggingContext to set the logging level to
    ERROR."""

    def __init__(self, logger: logging.Logger, quiet: bool, debug: bool) -> None:
        self.old_level = logger.level
        if quiet:
            # only change compared to original LoggingContext (WARNING -> ERROR)
            logger.setLevel(logging.ERROR)
        else:
            logger.setLevel(logging.DEBUG if debug else logging.INFO)

        self.new_handlers = []
        if not logger.handlers:
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            self.new_handlers.append(handler)

        self.logger = logger

    def __enter__(self) -> logging.Logger:
        return self.logger

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.logger.setLevel(self.old_level)
        for handler in self.new_handlers:
            self.logger.removeHandler(handler)


legacy_client.LoggingContext = QuietEra5LegacyClientLoggingContext


def load_api_key() -> str:
    """Load the CDS API key from environment variable or from the ~/.cdsapirc file."""
    global _api_key
    if _api_key is not None:
        return _api_key

    if os.getenv("CDSADS_API_KEY"):
        _api_key = os.getenv("CDSADS_API_KEY")
        return _api_key

    try:
        with open(os.path.expanduser("~/.cdsapirc")) as file:
            api_key = file.readlines()[-1].split(":")[-1].strip()
            assert api_key, "CDS API key is empty. Please check your ~/.cdsapirc file."
            _api_key = api_key
            return _api_key
    except FileNotFoundError:
        raise FileNotFoundError(
            "CDS API key file not found. Please create '~/.cdsapirc' with your key."
        )


def now_utc() -> datetime.datetime:
    """Get the current UTC time."""
    return datetime.datetime.now(datetime.UTC)


def make_cds_days_list(year, month) -> list[str]:
    """Generate a list of days for a given year and month.

    In case the month is in the future, return an empty list.

    :param year: The year for which to generate the days.
    :param month: The month for which to generate the days.
    :return: A list of days in the format 'DD' for the specified month and year.
    """

    now = now_utc()
    current_year, current_month, current_day = now.year, now.month, now.day

    if (current_year, current_month) < (year, month):
        return []

    days_in_month = monthrange(year, month)[1]

    if (current_year, current_month) == (year, month):
        return [f"{day:02d}" for day in range(1, min(days_in_month, current_day) + 1)]

    else:
        return [f"{day:02d}" for day in range(1, days_in_month + 1)]


def execute_download_request(url, dataset, cds_request, target_file, verbose: bool = False):
    """Execute a CDS request and download the data to the target file."""
    client = cdsapi.Client(url=url, key=load_api_key(), quiet=(not verbose))
    # wait for a random time between 0 and 10 seconds to avoid hitting the CDS API too hard
    time.sleep(random.uniform(0, 10))
    # Execute the CDS request
    logging.debug(f"Executing CDS request for dataset '{dataset}' with parameters: {cds_request}")
    client.retrieve(dataset, cds_request).download(target=target_file)


def load_netcdf(file_path) -> xr.Dataset:
    """Load a NetCDF file and return its content.

    :param file_path: Path to the NetCDF file.
    :return: xarray.Dataset containing the data from the NetCDF file.
    """
    ds = xr.open_dataset(file_path, engine="netcdf4")  # type: ignore[call-arg]

    return ds


def unzip_and_load_netcdf_to_df(file_path: str, clean_up: bool) -> pd.DataFrame:
    """Unzip a zip file containing a NetCDF file and load it into a DataFrame.

    :param file_path: Path to the zip file.
    :param clean_up: If True, remove the temporary NetCDF file after processing.
    :return: A DataFrame containing the data from the NetCDF file.
    """

    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            nc_file = zip_ref.namelist()[0]
            zip_ref.extractall("/tmp")

        tmp_file_path = os.path.join("/tmp", nc_file)
        try:
            return concat_netcdf_files_to_df(tmp_file_path, time_dim=0)
        finally:
            if clean_up:
                os.remove(tmp_file_path)

    else:
        # If the file is not a zip, assume it's a NetCDF file
        return concat_netcdf_files_to_df(file_path, time_dim=0)


def concat_netcdf_files_to_df(file_paths, time_dim: int = 0) -> pd.DataFrame:
    """Concatenate multiple NetCDF files into a single DataFrame.

    The index of the DataFrame will be a datetime index based on the 'time' dimension

    :param file_paths: List of paths to NetCDF files to merge.
    :param time_dim: The dimension to use for the time index. Default is 0 (first
        dimension).
    :return: xarray.Dataset containing the merged data.
    """
    files = glob.glob(file_paths)
    assert files, f"No NetCDF files found matching pattern: {file_paths}"
    datasets = []
    for file in files:
        try:
            df = xr.open_dataset(file).to_dataframe()
        except Exception as e:
            raise ValueError(f"Failed to read file {file}: {e}")
        # convert index to datetime by keeping the first level (time)
        df.index = pd.to_datetime(df.index.get_level_values(time_dim))
        datasets.append(df)

    combined_ds = pd.concat(datasets, axis=0).sort_index()
    return combined_ds
