import os
from multiprocessing import Pool
from tempfile import TemporaryDirectory

import pandas as pd
from tqdm import tqdm

from era5epw.utils import (
    execute_download_request,
    make_cds_days_list,
    now_utc,
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
    time_zone: int | None = None,
) -> list[dict[str, any]] | None:
    """Create a CDS request for the specified parameters.

    :param ds: The dataset to use, e.g., 'reanalysis-era5-single-levels-timeseries'.
    :param variables: List of variables to request.
    :param year: The year of the data.
    :param month: The month of the data. If None, all months will be requested.
    :param latitude: The latitude for the data point.
    :param longitude: The longitude for the data point.
    :param time_zone: Time zone offset from UTC. If provided, will adjust date range to
        fetch additional data needed for time zone conversion.
    :return: A dictionary representing the CDS request if the request is valid, otherwise
        None.
    """

    now = now_utc()

    # compute the start and end months.
    if year > now.year:
        return None
    if month is None:
        month_start = 1
        month_end = 12 if year < now.year else now.month
    else:
        if (now.year, now.month) < (year, month):
            return None
        month_start = month_end = month

    # dynamic dataset selection based on variables
    if ds is None:
        assert (
            len(variables) == 1
        ), "Dataset dynamic selection only supports single variable requests."
        for dataset in datasets:
            if variables[0] in supported_vars_by_dataset[dataset] or supported_vars_by_dataset[
                dataset
            ] == ["*"]:
                ds = dataset
                break

    if ds in [
        "reanalysis-era5-single-levels-timeseries",
        "reanalysis-era5-land-timeseries",
    ]:
        last_day_of_month_end = make_cds_days_list(year, month_end)[-1]
        start_date_str = f"{year}-{month_start:02d}-01"
        end_date_str = f"{year}-{month_end:02d}-{last_day_of_month_end}"

        main_request = {
            "dataset": ds,
            "data_format": "netcdf",
            "variable": variables,
            "date": [f"{start_date_str}/{end_date_str}"],
            "location": {"longitude": longitude, "latitude": latitude},
        }

        # Adjust date range based on time zone if provided.
        # We append an additional 1-day request to cover the shifted time zone
        if time_zone is not None:
            if time_zone > 0 and month_start == 1:
                start_date_str = f"{year - 1}-12-31"
                end_date_str = f"{year - 1}-12-31"
            elif time_zone < 0 and month_end == 12:
                start_date_str = f"{year + 1}-01-01"
                end_date_str = f"{year + 1}-01-01"
            else:
                return [main_request]

            tz_request = main_request.copy()
            tz_request["date"] = [f"{start_date_str}/{end_date_str}"]
            return [main_request, tz_request]

        else:
            return [main_request]

    elif ds == "reanalysis-era5-single-levels":
        assert (
            month is not None
        ), "Month must be specified for 'reanalysis-era5-single-levels' dataset."

        main_request = {
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

        # extend the request to cover time zone shifts
        if time_zone is not None:
            if time_zone > 0 and month_start == 1:
                tz_request = main_request.copy()
                tz_request["year"] = [str(year - 1)]
                tz_request["month"] = ["12"]
                tz_request["day"] = ["31"]
                return [main_request, tz_request]
            elif time_zone < 0 and month_end == 12:
                tz_request = main_request.copy()
                tz_request["year"] = [str(year + 1)]
                tz_request["month"] = ["01"]
                tz_request["day"] = ["01"]
                return [main_request, tz_request]

        return [main_request]

    else:
        raise ValueError(
            f"Unsupported dataset: {ds}. Supported datasets are 'reanalysis-era5-single-levels-timeseries' and 'reanalysis-era5-single-levels'."
        )


def make_intermediate_file_names(tmpdir: str, cds_requests: list[dict[str, any]]) -> list[str]:
    """Generate a list of temporary file names for storing intermediate results of CDS requests.

    :param tmpdir: Temporary directory where intermediate files will be stored.
    :param cds_requests: List of CDS requests that will be executed.
    :return: List of temporary file names.
    """
    # timeseries dataset requests have a 'date' field, while single-level requests have 'month'
    requested_years_months: set[tuple[int, int]] = set()
    for cds_request in cds_requests:
        if "date" in cds_request:
            date_range = cds_request["date"][0]
            start_date_str, end_date_str = date_range.split("/")
            start_year, start_month, _ = map(int, start_date_str.split("-"))
            _, end_month, _ = map(int, end_date_str.split("-"))
            for month in range(start_month, end_month + 1):
                requested_years_months.add((start_year, month))
        elif "month" in cds_request:
            month = int(cds_request["month"][0])
            year = int(cds_request["year"][0])
            requested_years_months.add((year, month))
        else:
            raise ValueError("CDS request must contain 'date' or 'month' field.")

    assert len(requested_years_months) > 0, "No months were requested in the CDS requests."
    years_months = sorted(list(requested_years_months))

    # extract the variable names from all CDS requests
    # not using a set to preserve the order of variables
    variables = []
    for cds_request in cds_requests:
        if "variable" in cds_request:
            for var in cds_request["variable"]:
                if var not in variables:
                    variables.append(var)
        else:
            raise ValueError("CDS request must contain 'variable' or 'variables' field.")

    intermediate_files = [
        os.path.join(tmpdir, f"era5_{year}_{month:02d}_{var}.nc")
        for year, month in years_months
        for var in variables
    ]

    return intermediate_files


def download_era5_data(
    variables: [str],
    year: int,
    latitude: float,
    longitude: float,
    dataset: str | None = datasets[0],
    parallel_exec_nb: int = 4,
    clean_up: bool = True,
    verbose: bool = False,
    time_zone: int | None = None,
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
    :param verbose: If True, enable verbose logging from CDS client.
    :param time_zone: Time zone offset from UTC. If provided, will adjust date range to
        fetch additional data needed for time zone conversion.
    :return: A DataFrame containing the downloaded data, combined on the 'time' dimension.
    """
    # split the request by month and variable, handle time zone adjustments
    cds_requests = [
        make_cds_request(
            ds=dataset,
            variables=[variable],
            year=year,
            month=month,
            latitude=latitude,
            longitude=longitude,
            time_zone=time_zone,
        )
        for month in range(1, 13)
        for variable in variables
    ]
    # flatten the list of lists and remove None entries
    cds_requests = [req for sublist in cds_requests for req in sublist if req is not None]

    if len(cds_requests) == 0:
        raise ValueError(
            f"No valid CDS requests could be created for year {year} and variables {variables}."
        )

    tqdm.write(
        f"Running a total of {len(cds_requests)} requests "
        f"with {parallel_exec_nb} parallel requests for {year}..."
    )

    # make temporary directory for intermediate files
    # then download each month in parallel
    with TemporaryDirectory(delete=clean_up) as tmpdir:
        intermediate_files = make_intermediate_file_names(tmpdir, cds_requests)

        assert len(cds_requests) == len(intermediate_files), (
            "The number of CDS requests and intermediate files must match."
            f" {len(cds_requests)} requests, {len(intermediate_files)} files."
        )

        # Create progress bar for ERA5 requests
        era5_progress = tqdm(
            total=len(cds_requests), desc="ERA5 requests", unit="request", position=1, leave=False
        )

        with Pool(parallel_exec_nb) as pool:
            # Use starmap_async to execute in parallel while maintaining progress tracking
            result = pool.starmap_async(
                execute_download_request,
                [
                    (
                        url,
                        cds_request["dataset"],
                        cds_request,
                        intermediary_file,
                        verbose,
                    )
                    for (cds_request, intermediary_file) in zip(cds_requests, intermediate_files)
                ],
            )

            # Poll for completion and update progress
            while not result.ready():
                # Count completed files to update progress
                completed = sum(1 for f in intermediate_files if os.path.exists(f))
                era5_progress.n = completed
                era5_progress.refresh()
                result.wait(timeout=1)  # Check every second

            # Final update
            era5_progress.n = len(cds_requests)
            era5_progress.refresh()
            _result = result.get()

        era5_progress.close()

        dfs = [
            unzip_and_load_netcdf_to_df(file_path, clean_up=clean_up)
            for file_path in intermediate_files
        ]

        # concatenate all DataFrames into a single DataFrame
        # 1. group by year and month, then concatenate along the variable axis
        dfs_by_year_month = {}
        for df in dfs:
            idx = (df.index[0].year, df.index[0].month)
            if idx not in dfs_by_year_month:
                dfs_by_year_month[idx] = []
            dfs_by_year_month[idx].append(df)

        dfs = [
            pd.concat(year_month_dfs, axis=1)
            for year_month_dfs in dfs_by_year_month.values()
            if len(year_month_dfs) > 0
        ]

        # 2. concatenate along the index (time) axis
        return pd.concat(dfs, axis=0, ignore_index=False).sort_index().drop_duplicates()


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
        time_zone=1,
    )

    print(df.head(5))
    print(df.info())
