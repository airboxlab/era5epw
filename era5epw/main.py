import logging
import os.path
from argparse import ArgumentParser
from datetime import datetime

import numpy as np
import pandas as pd
from tqdm import tqdm

from era5epw.ads import download_cams_solar_radiation_data
from era5epw.cds import download_era5_data


def get_first_weekday_of_year(y: int) -> str:
    first_weekday_of_year = pd.Timestamp(y, 1, 1).dayofweek
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
        first_weekday_of_year
    ]


def calc_rh(dry_bulb_temp: np.ndarray, dew_point_temp: np.ndarray) -> np.ndarray:
    """Calculate relative humidity from temperature and dew point temperature.

    :param dry_bulb_temp: Temperature in Celsius.
    :param dew_point_temp: Dew point temperature in Celsius.
    """
    es = 6.112 * np.exp((17.67 * dry_bulb_temp) / (dry_bulb_temp + 243.5))
    esd = 6.112 * np.exp((17.67 * dew_point_temp) / (dew_point_temp + 243.5))
    return np.round(100 * esd / es, 1)


def calc_monthly_soil_temperature(soil_temp: pd.DataFrame | pd.Series) -> pd.Series:
    """Compute monthly average soil temperature at 0-7 cm depth (level 1)

    :param soil_temp: Soil temperature data at 0-7 cm depth in Kelvin.
    :return: Monthly average soil temperature in Celsius.
    """
    return soil_temp.groupby(soil_temp.index.month).mean() - 273.15


def is_leap_year(y: int) -> bool:
    """Check if a year is a leap year."""
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def make_data_period_end_date(df: pd.DataFrame) -> str:
    """Return the data period end date string for the EPW header.

    :param df: DataFrame containing the weather data.
    :return: End date string in the format "MM/DD".
    """
    return df.iloc[-1][["Month", "Day"]].astype(int).astype(str).str.cat(sep="/")


def create_args() -> ArgumentParser:
    """Create argument parser for command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a full year EPW file from ERA5 and CAMS data."
    )
    parser.add_argument(
        "--year", type=int, default=2023, help="Year for which to generate the EPW file."
    )
    parser.add_argument("--latitude", type=float, default=48.5, help="Latitude of the location.")
    parser.add_argument("--longitude", type=float, default=2.5, help="Longitude of the location.")
    parser.add_argument(
        "--parallel-requests",
        type=int,
        default=10,
        required=False,
        help="Number of parallel requests to make on CDS API.",
    )
    parser.add_argument(
        "--city-name", type=str, default="Paris", help="Name of the city for the EPW file."
    )
    parser.add_argument("--time-zone", type=int, default=1, help="Time zone offset from UTC.")
    parser.add_argument(
        "--elevation", type=int, default=35, help="Elevation of the location in meters."
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=f"/tmp/era5epw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.epw",
        help="Output file path for the generated EPW file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging from CDS client.",
    )
    return parser


def download_and_make_epw(
    year: int,
    latitude: float,
    longitude: float,
    city_name: str,
    time_zone: int,
    elevation: int,
    output_file: str,
    parallel_exec_nb: int = 10,
    verbose: bool = False,
) -> None:
    """Generate a full year EPW file from ERA5 and CAMS data.

    :param year: Year for which to generate the EPW file.
    :param latitude: Latitude of the location.
    :param longitude: Longitude of the location.
    :param city_name: Name of the city for the EPW file.
    :param time_zone: Time zone offset from UTC.
    :param elevation: Elevation of the location in meters.
    :param output_file: Path to save the generated EPW file.
    :param parallel_exec_nb: Number of parallel requests to make on CDS (ERA5 allows 10 per
        minute).
    :param verbose: If True, enable verbose logging from CDS client.
    """
    start_time = datetime.now()

    # Create overall progress bar for the two main download phases
    overall_progress = tqdm(total=2, desc="Overall progress", unit="phase", position=0)

    overall_progress.set_description("Downloading ERA5 data")
    era5_df = download_era5_data(
        variables=[
            "2m_temperature",
            "2m_dewpoint_temperature",
            "surface_pressure",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_cloud_cover",
            "uv_visible_albedo_for_direct_radiation",
            "snow_depth",
            "soil_temperature_level_1",
            "total_precipitation",
        ],
        year=year,
        latitude=latitude,
        longitude=longitude,
        parallel_exec_nb=parallel_exec_nb,
        dataset=None,  # dynamic dataset selection based on variables
        verbose=verbose,
    )
    overall_progress.update(1)  # ERA5 download completed

    overall_progress.set_description("Downloading CAMS solar radiation data")
    cams_df = download_cams_solar_radiation_data(
        longitude=longitude,
        latitude=latitude,
        year=year,
    )
    overall_progress.update(1)  # CAMS download completed
    overall_progress.close()

    # CAMS data has a (tz?) shift compared to ERA5, so we need to align them
    # interpolate first hour of the year with the first hour of CAMS
    if cams_df.index[0] != pd.Timestamp(f"{year}-01-01 00:00"):
        cams_df = cams_df.reindex(
            pd.date_range(start=f"{year}-01-01 00:00", end=cams_df.index[-1], freq="1h"),
            method="bfill",
        )

    # Align ERA5 and CAMS dataframes to the same time range
    # their indices may not match exactly, especially when the year is not complete (e.g. current year)
    era5_df, cams_df = era5_df.align(cams_df, join="inner", axis=0)
    assert era5_df.index.equals(cams_df.index), "Time indices of ERA5 and CAMS data do not match"

    # Extract variables, convert to correct units
    temp_C = era5_df["t2m"].values - 273.15  # K to C
    dew_C = era5_df["d2m"].values - 273.15  # K to C
    press = era5_df["sp"].values  # Pa
    u10 = era5_df["u10"].values  # m/s
    v10 = era5_df["v10"].values  # m/s
    cloud = era5_df["tcc"].values * 10  # Fraction to okta (0-10 scale)
    uv_visible_albedo = era5_df["aluvp"].values  # (0-1 scale)
    snow_depth = era5_df["sd"].values * 100  # m to cm
    total_precipitation = era5_df["tp"].values * 1000  # m to mm
    ghi = cams_df["GHI"].values  # Global horizontal all sky irradiation in Wh/m^2
    bni = cams_df["BNI"].values  # Direct normal all sky irradiation in Wh/m^2
    bhi = cams_df["BHI"].values  # Direct horizontal all sky irradiation in Wh/m^2
    dhi = cams_df["DHI"].values  # Diffuse horizontal irradiation in Wh/m^2

    # Calculate wind speed and direction
    wind_speed = np.sqrt(u10**2 + v10**2)
    wind_dir = (180 + np.degrees(np.arctan2(u10, v10))) % 360

    # Time index
    times = pd.to_datetime(era5_df.index.values)

    # Create DataFrame
    df = pd.DataFrame(
        {
            "Year": times.year,
            "Month": times.month,
            "Day": times.day,
            "Hour": times.hour + 1,  # EPW hours start at 1
            "Minute": 0,
            "Data Source and Uncertainty Flags": "9",
            "Dry Bulb Temperature": np.round(temp_C, 1),  # C
            "Dew Point Temperature": np.round(dew_C, 1),  # C
            "Relative Humidity": calc_rh(temp_C, dew_C),  # %
            "Atmospheric Station Pressure": np.round(press, 0),  # Pa
            "Extraterrestrial Horizontal Radiation": 9999,  # Wh/m^2
            "Extraterrestrial Direct Normal Radiation": 9999,  # Wh/m^2
            "Horizontal Infrared Radiation Intensity": 9999,  # Wh/m^2 - TODO
            "Global Horizontal Radiation": np.round(ghi, 1),  # Wh/m^2
            "Direct Normal Radiation": np.round(bni, 1),  # Wh/m^2
            "Diffuse Horizontal Radiation": np.round(dhi, 1),  # Wh/m^2
            "Global Horizontal Illuminance": np.round(110 * ghi, 0),  # Lux
            "Direct Normal Illuminance": np.round(105 * bni, 0),  # Lux
            "Diffuse Horizontal Illuminance": np.round(119 * dhi, 0),  # Lux
            "Zenith Luminance": 9999,  # Cd/m^2 - TODO
            "Wind Direction": np.round(wind_dir, 0),  # degrees
            "Wind Speed": np.round(wind_speed, 1),  # m/s
            "Total Sky Cover": np.round(cloud, 0),
            "Opaque Sky Cover": np.round(cloud, 0),
            "Visibility": 9999,  # km
            "Ceiling Height": 77777,  # m - TODO
            # 0 = Weather observation made; 9 = Weather observation not made, or missing
            "Present Weather Observation": 0,
            "Present Weather Codes": 999999999,  # see doc
            "Precipitable Water": 999,  # mm
            "Aerosol Optical Depth": 999,  # thousandths
            "Snow Depth": np.round(snow_depth, 1),  # cm
            "Days Since Last Snowfall": 99,
            "Albedo": np.round(uv_visible_albedo, 1),  # (0 - 1 scale)
            "Liquid Precipitation Depth": np.round(total_precipitation, 1),  # mm
            "Liquid Precipitation Quantity": 1,
        }
    )

    ground_temps = "1,3.5,,,," + ",".join(
        calc_monthly_soil_temperature(era5_df["stl1"]).round(1).astype(str).tolist()
    )
    if "nan" in ground_temps:
        logging.warning(
            "Soil temperature data at level 1 (0-7 cm) contains NaN values. "
            "Setting number of monthly soil temperatures to 0."
        )
        ground_temps = "0"

    data_period_end_date = make_data_period_end_date(df)

    # Write header
    epw_header = [
        f"LOCATION,{city_name},,,ERA5 (ECMWF),n/a,{latitude:.2f},{longitude:.2f},{time_zone},{elevation}",
        "DESIGN CONDITIONS,0",
        "TYPICAL/EXTREME PERIODS,0",
        f"GROUND TEMPERATURES,{ground_temps}",
        f"HOLIDAYS/DAYLIGHT SAVINGS,{'Yes' if is_leap_year(year) else 'No'},0,0,0",
        "COMMENTS 1,Data from ERA5 and CAMS via CDSAPI",
        "COMMENTS 2,Processed with Python - Provided with love by the Foobot Team",
        f"DATA PERIODS,1,1,Data,{get_first_weekday_of_year(year)},1/1,{data_period_end_date}",
    ]

    with open(output_file, "w") as f:
        for line in epw_header:
            f.write(line + "\n")
        df.to_csv(f, index=False, header=False)

    end_time = datetime.now()
    tqdm.write(f"EPW file written as {output_file}. Took {end_time - start_time} to generate.")


def download():
    from era5epw.logcfg import init_logging

    args = create_args().parse_args()

    # Initialize logging with verbosity setting
    init_logging(verbose=args.verbose)

    tqdm.write(
        f"Generating EPW file for {args.city_name} ({args.latitude}, {args.longitude}) in {args.year}..."
    )

    if os.path.exists(args.output_file):
        tqdm.write(f"Output file {args.output_file} already exists. It will be overwritten.")

    download_and_make_epw(
        year=args.year,
        latitude=args.latitude,
        longitude=args.longitude,
        city_name=args.city_name,
        time_zone=args.time_zone,
        elevation=args.elevation,
        output_file=args.output_file,
        parallel_exec_nb=args.parallel_requests,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    download()
