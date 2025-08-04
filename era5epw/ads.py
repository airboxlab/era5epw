import tempfile

import pandas as pd
import xarray as xr
from tqdm import tqdm

from era5epw.utils import execute_download_request, now_utc

url = "https://ads.atmosphere.copernicus.eu/api"
dataset = "cams-solar-radiation-timeseries"


def make_cams_solar_radiation_request(
    longitude: float,
    latitude: float,
    year: int,
    sky_type: str = "observed_cloud",
    altitude: list[str] | None = None,
    time_step: str = "1hour",
    time_reference: str = "universal_time",
) -> dict[str, any] | None:
    assert sky_type in [
        "clear",
        "observed_cloud",
    ], "Invalid sky type. Choose 'clear' or 'observed_cloud'."

    if altitude is None:
        altitude = ["0"]  # Default altitude if not specified

    now = now_utc()
    if year > now.year:
        return None  # Do not allow requests for future years

    end_day = f"{year}-12-31"
    today = now.strftime("%Y-%m-%d")
    if end_day > today:
        end_day = today

    return {
        "sky_type": sky_type,
        "location": {"longitude": longitude, "latitude": latitude},
        "altitude": altitude,
        "date": [f"{year}-01-01/{end_day}"],
        "time_step": time_step,
        "time_reference": time_reference,
        "format": "netcdf",
    }


def download_cams_solar_radiation_data(
    longitude: float,
    latitude: float,
    year: int,
    sky_type: str = "observed_cloud",
    altitude: list[str] | None = None,
    time_step: str = "1hour",
    time_reference: str = "universal_time",
    clean_up: bool = True,
) -> pd.DataFrame:
    """Download solar radiation data from the Copernicus Atmosphere Data Store (CAMS).

    :param longitude: Longitude of the location.
    :param latitude: Latitude of the location.
    :param year: Year for which to download the data.
    :param sky_type: Type of sky conditions, either "clear" or "observed_cloud".
    :param altitude: List of altitudes in meters, default is ["0"] if not specified.
    :param time_step: Time step for the data, default is "1hour".
    :param time_reference: Time reference for the data, default is "universal_time".
    :param clean_up: If True, remove the temporary file after processing.
    """
    request = make_cams_solar_radiation_request(
        longitude=longitude,
        latitude=latitude,
        year=year,
        sky_type=sky_type,
        altitude=altitude,
        time_step=time_step,
        time_reference=time_reference,
    )

    if request is None:
        raise ValueError("Cannot download data for future years.")

    with tempfile.NamedTemporaryFile(dir="/tmp", suffix=".nc", delete=clean_up) as temp_file:
        # Create progress bar for CAMS request
        cams_progress = tqdm(total=1, desc="CAMS request", unit="request", position=1, leave=False)
        execute_download_request(
            url=url,
            dataset=dataset,
            cds_request=request,
            target_file=temp_file.name,
        )
        cams_progress.update(1)
        cams_progress.close()

        tqdm.write(f"Data downloaded to {temp_file.name}")

        ds = xr.open_dataset(temp_file.name)
        df = ds.to_dataframe()
        df.index = pd.to_datetime(df.index.get_level_values("time"))
        df = df.sort_index()

    return df


if __name__ == "__main__":
    df_2024 = download_cams_solar_radiation_data(
        longitude=2.69022,
        latitude=46.98709,
        year=2024,
        sky_type="observed_cloud",
        altitude=["0"],
        time_step="1hour",
        time_reference="universal_time",
    )
    print(df_2024.head(5))
