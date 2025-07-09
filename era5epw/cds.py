import logging
import os
import tempfile
from calendar import monthrange
from multiprocessing import Pool
from tempfile import TemporaryDirectory

import pandas as pd

from era5epw.utils import (
    execute_download_request,
    make_cds_days_list,
    unzip_and_load_netcdf_to_df,
)

url = "https://cds.climate.copernicus.eu/api"
datasets = [
    # new experimental dataset for timeseries data. Seems faster to download but not all variables are available.
    # first in the list so it is selected with higher priority.
    "reanalysis-era5-single-levels-timeseries",
    # new experimental dataset for land data. It's also faster to download but not all variables are available.
    "reanalysis-era5-land-timeseries",
    # the original dataset for single-level data. Contains all variables but is much slower to download.
    "reanalysis-era5-single-levels",
]
supported_vars_by_dataset = {
    "reanalysis-era5-single-levels-timeseries": [
        "2m_dewpoint_temperature",
        "2m_temperature",
        "total_precipitation",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "surface_pressure",
    ],
    "reanalysis-era5-land-timeseries": [
        "soil_temperature_level_1",
    ],
    "reanalysis-era5-single-levels": ["*"],
}


def make_cds_request(
    ds: str | None,
    variables: [str],
    year: int,
    month: int | None,
    latitude: float,
    longitude: float,
) -> dict[str, any]:
    """Create a CDS request for the specified parameters.

    :param ds: The dataset to use, e.g., 'reanalysis-era5-single-levels-timeseries'.
    :param variables: List of variables to request.
    :param year: The year of the data.
    :param month: The month of the data. If None, all months will be requested.
    :param latitude: The latitude for the data point.
    :param longitude: The longitude for the data point.
    :return: A dictionary representing the CDS request.
    """

    if ds is None:
        assert (
            len(variables) == 1
        ), "Dataset dynamic selection only supports single variable requests."
        # if no dataset is specified, we select the first one that supports the variable
        for dataset in datasets:
            if variables[0] in supported_vars_by_dataset[dataset] or supported_vars_by_dataset[
                dataset
            ] == ["*"]:
                ds = dataset
                break

    if month is None:
        month_start = 1
        month_end = 12
    else:
        month_start = month_end = month

    if ds in [
        "reanalysis-era5-single-levels-timeseries",
        "reanalysis-era5-land-timeseries",
    ]:
        return {
            "dataset": ds,
            "data_format": "netcdf",
            "variable": variables,
            "date": [
                f"{year}-{month_start:02d}-01/{year}-{month_end:02d}-{monthrange(year, month_end)[1]:02d}"
            ],
            "location": {"longitude": longitude, "latitude": latitude},
        }
    elif ds == "reanalysis-era5-single-levels":
        assert (
            month is not None
        ), "Month must be specified for 'reanalysis-era5-single-levels' dataset."
        return {
            "dataset": ds,
            "product_type": "reanalysis",
            "format": "netcdf",
            "variable": variables,
            "year": [str(year)],
            "month": [f"{month:02d}"],
            "day": make_cds_days_list(year, month),
            "time": [f"{i:02d}:00" for i in range(24)],
            "area": [latitude, longitude, latitude, longitude],
        }
    else:
        raise ValueError(
            f"Unsupported dataset: {ds}. Supported datasets are 'reanalysis-era5-single-levels-timeseries' and 'reanalysis-era5-single-levels'."
        )


def download_era5_data(
    variables: [str],
    year: int,
    latitude: float,
    longitude: float,
    dataset: str | None = datasets[0],
    parallel_exec_nb: int = 4,
    clean_up: bool = True,
) -> pd.DataFrame:
    """Download data from the Climate Data Store (CDS) for a specific variable and time and return
    as a DataFrame.

    :param variables: The variable to download (e.g., '2m_temperature').
    :param year: The year of the data. Full year will be downloaded.
    :param latitude: The latitude for the data point.
    :param longitude: The longitude for the data point.
    :param dataset: The dataset to use, e.g., 'reanalysis-era5-single-levels-timeseries'. If
        None, the first dataset supporting the variable will be selected.
    :param parallel_exec_nb: Number of parallel executions for downloading data. Default is
        12 (1 per month).
    :param clean_up: If True, remove individual month files after combining them into the
        target file.
    :return: A DataFrame containing the downloaded data, combined on the 'time' dimension.
    """
    if parallel_exec_nb == 1:
        # if parallel execution is not requested, we can just make a single request for the whole year
        cds_request = make_cds_request(
            ds=dataset,
            variables=variables,
            year=year,
            month=None,
            latitude=latitude,
            longitude=longitude,
        )

        with tempfile.NamedTemporaryFile(dir="/tmp", suffix=".zip", delete=clean_up) as tmp_file:
            execute_download_request(
                url, cds_request["dataset"], cds_request, target_file=tmp_file.name
            )
            return unzip_and_load_netcdf_to_df(tmp_file.name, clean_up=clean_up)

    # split the request by month and variable
    cds_requests = []
    for month in range(1, 13):
        for variable in variables:
            cds_request = make_cds_request(
                ds=dataset,
                variables=[variable],
                year=year,
                month=month,
                latitude=latitude,
                longitude=longitude,
            )
            cds_requests.append(cds_request)

    logging.info(f"Running {len(cds_requests)} requests in parallel for {year}...")

    # make temporary directory for intermediate files
    # then download each month in parallel
    with TemporaryDirectory(delete=clean_up) as tmpdir:
        intermediate_files = [
            os.path.join(tmpdir, f"era5_{year}_{month:02d}_{var}.nc")
            for month in range(1, 13)
            for var in variables
        ]

        with Pool(parallel_exec_nb) as pool:
            _result = pool.starmap(
                execute_download_request,
                [
                    (
                        url,
                        cds_request["dataset"],
                        cds_request,
                        intermediary_file,
                    )
                    for (cds_request, intermediary_file) in zip(cds_requests, intermediate_files)
                ],
            )

        dfs = []
        for file_path in intermediate_files:
            dfs.append(unzip_and_load_netcdf_to_df(file_path, clean_up=clean_up))

        # concatenate all DataFrames into a single DataFrame
        # concatenate variables along axis 1 and time along axis 0
        dfs_by_month = {}
        for df in dfs:
            month = df.index.month[0]
            if month not in dfs_by_month:
                dfs_by_month[month] = []
            dfs_by_month[month].append(df)

        # concatenate variables for each month
        dfs = [pd.concat(month_dfs, axis=1) for month_dfs in dfs_by_month.values()]

        # concatenate along the index axis
        return pd.concat(dfs, axis=0, ignore_index=False)


if __name__ == "__main__":
    df = download_era5_data(
        dataset=None,  # dynamic dataset selection based on variables
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
        year=2024,
        latitude=49.4,
        longitude=0.1,
        clean_up=False,
        parallel_exec_nb=10,
    )

    print(df.head(5))
    print(df.info())

    stl1 = df["stl1"].groupby(df["stl1"].index.month).mean() - 273.15
    print(",".join(stl1.round(1).astype(str).tolist()))
