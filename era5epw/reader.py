"""EPW file reader.

This module provides functionality to read EnergyPlus Weather (EPW) files and return the
data as a Pandas DataFrame for inspection and data analysis.
"""

import pandas as pd

# EPW column names as per EnergyPlus EPW format specification
EPW_COLUMNS = [
    "Year",
    "Month",
    "Day",
    "Hour",
    "Minute",
    "Data Source and Uncertainty Flags",
    "Dry Bulb Temperature",
    "Dew Point Temperature",
    "Relative Humidity",
    "Atmospheric Station Pressure",
    "Extraterrestrial Horizontal Radiation",
    "Extraterrestrial Direct Normal Radiation",
    "Horizontal Infrared Radiation Intensity",
    "Global Horizontal Radiation",
    "Direct Normal Radiation",
    "Diffuse Horizontal Radiation",
    "Global Horizontal Illuminance",
    "Direct Normal Illuminance",
    "Diffuse Horizontal Illuminance",
    "Zenith Luminance",
    "Wind Direction",
    "Wind Speed",
    "Total Sky Cover",
    "Opaque Sky Cover",
    "Visibility",
    "Ceiling Height",
    "Present Weather Observation",
    "Present Weather Codes",
    "Precipitable Water",
    "Aerosol Optical Depth",
    "Snow Depth",
    "Days Since Last Snowfall",
    "Albedo",
    "Liquid Precipitation Depth",
    "Liquid Precipitation Quantity",
]


def read_epw_file(epw_file_path: str) -> pd.DataFrame:
    """Read and parse an EPW file into a DataFrame.

    :param epw_file_path: Path to the EPW file.
    :return: DataFrame with datetime index and weather data columns.

    Example usage::

        from era5epw.reader import read_epw_file

        df = read_epw_file("path/to/file.epw")
        print(df.head())
        print(df.describe())
    """
    with open(epw_file_path) as f:
        # Skip the 8 header lines
        lines = f.readlines()

    # Data starts from line 9 (index 8)
    data_lines = lines[8:]

    # Parse data lines
    data = []
    for line in data_lines:
        if line.strip():
            data.append(line.strip().split(","))

    # Create DataFrame
    df = pd.DataFrame(data, columns=EPW_COLUMNS)

    # Convert numeric columns to float
    for col in df.columns:
        if col not in ["Year", "Month", "Day", "Hour", "Minute"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert time columns to int
    df["Year"] = df["Year"].astype(int)
    df["Month"] = df["Month"].astype(int)
    df["Day"] = df["Day"].astype(int)
    df["Hour"] = df["Hour"].astype(int)

    # Create datetime index (handle hour 24 as hour 0 of next day)
    def create_datetime(row):
        year, month, day, hour = row["Year"], row["Month"], row["Day"], row["Hour"]
        if hour == 24:
            # Hour 24 means midnight of the next day
            dt = pd.Timestamp(year=year, month=month, day=day) + pd.Timedelta(days=1)
        else:
            dt = pd.Timestamp(year=year, month=month, day=day, hour=hour)
        return dt

    df["Datetime"] = df.apply(create_datetime, axis=1)
    df.set_index("Datetime", inplace=True)

    return df
