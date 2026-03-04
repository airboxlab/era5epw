"""EPW file visualization tool.

This module provides interactive visualization of EPW (EnergyPlus Weather) files using
Plotly. It supports both command-line usage and API usage in Jupyter notebooks.
"""

import argparse
from pathlib import Path
from typing import Literal

import pandas as pd
import plotly.graph_objects as go

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

# Series to hide from the dropdown menu
HIDDEN_SERIES = [
    "Year",
    "Month",
    "Day",
    "Hour",
    "Minute",
    "Data Source and Uncertainty Flags",
    "Present Weather Observation",
    "Present Weather Codes",
]

# Units for each series
UNITS = {
    "Dry Bulb Temperature": "°C",
    "Dew Point Temperature": "°C",
    "Relative Humidity": "%",
    "Atmospheric Station Pressure": "Pa",
    "Extraterrestrial Horizontal Radiation": "Wh/m²",
    "Extraterrestrial Direct Normal Radiation": "Wh/m²",
    "Horizontal Infrared Radiation Intensity": "Wh/m²",
    "Global Horizontal Radiation": "Wh/m²",
    "Direct Normal Radiation": "Wh/m²",
    "Diffuse Horizontal Radiation": "Wh/m²",
    "Global Horizontal Illuminance": "lux",
    "Direct Normal Illuminance": "lux",
    "Diffuse Horizontal Illuminance": "lux",
    "Zenith Luminance": "Cd/m²",
    "Wind Direction": "degrees",
    "Wind Speed": "m/s",
    "Total Sky Cover": "",
    "Opaque Sky Cover": "",
    "Visibility": "km",
    "Ceiling Height": "m",
    "Precipitable Water": "mm",
    "Aerosol Optical Depth": "thousandths",
    "Snow Depth": "cm",
    "Days Since Last Snowfall": "",
    "Albedo": "",
    "Liquid Precipitation Depth": "mm",
    "Liquid Precipitation Quantity": "hr",
}


def read_epw_file(epw_file_path: str) -> pd.DataFrame:
    """Read and parse an EPW file into a DataFrame.

    :param epw_file_path: Path to the EPW file.
    :return: DataFrame with datetime index and weather data columns.
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


def get_visible_series(df: pd.DataFrame) -> list[str]:
    """Get list of visible series names (excluding hidden ones).

    :param df: DataFrame containing weather data.
    :return: List of visible series names.
    """
    return [col for col in df.columns if col not in HIDDEN_SERIES]


def create_2d_plot(
    df: pd.DataFrame, series_name: str, width: int = 1200, height: int = 500
) -> go.Figure:
    """Create a 2D line plot for a given weather series.

    :param df: DataFrame containing weather data.
    :param series_name: Name of the series to plot.
    :param width: Width of the plot in pixels.
    :param height: Height of the plot in pixels.
    :return: Plotly Figure object.
    """
    unit = UNITS.get(series_name, "")

    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=df.index,
            y=df[series_name],
            mode="lines",
            name=series_name,
            line=dict(color="rgb(31, 119, 180)"),
        )
    )

    fig.update_layout(
        title=dict(text=f"{series_name} Over Time", font=dict(size=16)),
        xaxis=dict(title="Date", automargin=True),
        yaxis=dict(title=f"{series_name} ({unit})" if unit else series_name, automargin=True),
        width=width,
        height=height,
        margin=dict(t=50, r=20, b=50, l=60),
        hovermode="x unified",
    )

    return fig


def create_3d_plot(
    df: pd.DataFrame, series_name: str, width: int = 1200, height: int = 750
) -> go.Figure:
    """Create a 3D surface plot showing hour vs day with data values.

    :param df: DataFrame containing weather data.
    :param series_name: Name of the series to plot.
    :param width: Width of the plot in pixels.
    :param height: Height of the plot in pixels.
    :return: Plotly Figure object.
    """
    unit = UNITS.get(series_name, "")

    # Reshape data into 2D array: rows = days, columns = hours
    per_chunk = 24
    values = df[series_name].values

    # Chunk data into days (24 hours per day)
    z_data = []
    for i in range(0, len(values), per_chunk):
        chunk = values[i : i + per_chunk]
        if len(chunk) == per_chunk:
            z_data.append(chunk)

    # Get the first date
    day_0 = df.index[0].date()

    # Create y-axis: dates for each day
    y_dates = [day_0 + pd.Timedelta(days=i) for i in range(len(z_data))]

    fig = go.Figure(
        data=[
            go.Surface(
                y=y_dates,
                x=list(range(24)),
                z=z_data,
                colorscale="Jet",
                colorbar=dict(len=0.5, title=unit if unit else ""),
            )
        ]
    )

    fig.update_layout(
        scene=dict(
            camera=dict(
                eye=dict(x=1.87, y=0.88, z=0.64),
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=-0.35),
                projection=dict(type="perspective"),
            ),
            xaxis=dict(
                title="Hour",
                ticksuffix="h",
                autorange="reversed",
            ),
            yaxis=dict(
                title="Day of Year",
            ),
            zaxis=dict(
                title=f"{series_name} ({unit})" if unit else series_name,
            ),
            aspectratio=dict(x=1, y=2, z=0.5),
        ),
        title=dict(text=f"{series_name} - 3D View", font=dict(size=16)),
        autosize=False,
        width=width,
        height=height,
        margin=dict(l=20, r=50, b=5, t=50),
    )

    return fig


def create_radar_plot(
    df: pd.DataFrame, series_name: str, width: int = 900, height: int = 700
) -> go.Figure:
    """Create a radar (polar) plot showing daily min/max values throughout the year.

    :param df: DataFrame containing weather data.
    :param series_name: Name of the series to plot.
    :param width: Width of the plot in pixels.
    :param height: Height of the plot in pixels.
    :return: Plotly Figure object.
    """
    unit = UNITS.get(series_name, "")

    # Group by date to get daily min/max
    daily_data = df.groupby(df.index.date)[series_name].agg(["min", "max"])
    daily_data["date"] = daily_data.index
    daily_data["month"] = pd.to_datetime(daily_data["date"]).dt.strftime("%b")

    # Get max value for color scaling
    max_val = daily_data["max"].max()
    min_val = daily_data["min"].min()
    val_range = max_val - min_val if max_val != min_val else 1

    # Jet colorscale function
    def jet_colorscale(normalized_value: float, alpha: float = 1.0) -> str:
        """Create a jet colorscale color."""
        val = max(0, min(1, normalized_value))

        if val < 0.25:
            r, g, b = 0, int(4 * val * 255), 255
        elif val < 0.5:
            r, g, b = 0, 255, int((1 + 4 * (0.25 - val)) * 255)
        elif val < 0.75:
            r, g, b = int(4 * (val - 0.5) * 255), 255, 0
        else:
            r, g, b = 255, int((1 + 4 * (0.75 - val)) * 255), 0

        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        return f"rgba({r}, {g}, {b}, {alpha})"

    # Create traces for each day
    traces = []
    max_angle = min(360, len(daily_data))

    # Track month changes for labels
    month_ticks = []
    current_month = ""

    for i, (idx, row) in enumerate(daily_data.iterrows()):
        theta = (i / len(daily_data)) * max_angle

        # Color based on max temperature
        color_val = (row["max"] - min_val) / val_range if val_range > 0 else 0
        color = jet_colorscale(color_val, 1.0)

        # Add month label only when month changes
        month_str = row["month"]
        if month_str != current_month:
            month_ticks.append((i, f"<b>{month_str}</b>"))
            current_month = month_str
        else:
            month_ticks.append((i, ""))

        traces.append(
            go.Scatterpolargl(
                r=[row["max"], row["min"]],
                theta=[theta, theta],
                mode="lines",
                line=dict(color=color, width=3),
                fill="toself",
                name=str(row["date"]),
                hovertemplate=(
                    f"{row['date']}<br>"
                    f"Min: {row['min']:.1f}{unit}<br>"
                    f"Max: {row['max']:.1f}{unit}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig = go.Figure(data=traces)

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                layer="above traces",
                title=dict(
                    text=f"{series_name} ({unit})" if unit else series_name,
                    font=dict(size=15),
                ),
                tickfont=dict(size=14),
                gridcolor="lightgray",
                linecolor="gray",
                linewidth=4,
            ),
            angularaxis=dict(
                direction="clockwise",
                gridcolor="lightgray",
                linecolor="gray",
                rotation=90,  # Start first day at top
                tickmode="array",
                tickvals=[t[0] for t in month_ticks],
                ticktext=[t[1] for t in month_ticks],
                tickangle=0,
                ticks="inside",
            ),
        ),
        showlegend=False,
        margin=dict(t=80, r=50, b=50, l=50),
        width=width,
        height=height,
        title=dict(
            text=f"Daily Min/Max {series_name}",
            font=dict(size=16),
            y=0.98,
        ),
        hoverlabel=dict(
            bgcolor="white",
            font=dict(size=14),
        ),
    )

    return fig


def visualize_epw(
    epw_file_path: str,
    series_name: str = "Dry Bulb Temperature",
    plot_type: Literal["2D", "3D", "radar"] = "2D",
    show: bool = True,
    renderer: Literal["notebook", "browser", "iframe"] = "notebook",
) -> go.Figure:
    """Visualize EPW weather data with interactive plots.

    :param epw_file_path: Path to the EPW file.
    :param series_name: Name of the weather series to visualize.
    :param plot_type: Type of plot: "2D", "3D", or "radar".
    :param show: If True, display the plot immediately (useful in Jupyter).
    :param renderer: Renderer to use for displaying the plot ("notebook", "browser", or
        "iframe").
    :return: Plotly Figure object.
    """
    # Read EPW file
    df = read_epw_file(epw_file_path)

    # Validate series name
    visible_series = get_visible_series(df)
    if series_name not in visible_series:
        raise ValueError(
            f"Series '{series_name}' not found. Available series: {', '.join(visible_series)}"
        )

    # Create the appropriate plot
    if plot_type == "2D":
        fig = create_2d_plot(df, series_name)
    elif plot_type == "3D":
        fig = create_3d_plot(df, series_name)
    elif plot_type == "radar":
        fig = create_radar_plot(df, series_name)
    else:
        raise ValueError(f"Invalid plot_type: {plot_type}. Must be '2D', '3D', or 'radar'.")

    if show:
        fig.show(renderer=renderer)

    return fig


def visualize_cli() -> None:
    """Command-line interface for EPW visualization."""
    parser = argparse.ArgumentParser(
        description="Visualize EPW (EnergyPlus Weather) file data with interactive plots."
    )
    parser.add_argument(
        "epw_file",
        type=str,
        help="Path to the EPW file to visualize.",
    )
    parser.add_argument(
        "--series",
        type=str,
        default="Dry Bulb Temperature",
        help="Weather series to visualize (e.g., 'Dry Bulb Temperature', 'Wind Speed').",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["2D", "3D", "radar"],
        default="2D",
        help="Type of visualization: 2D (line plot), 3D (surface plot), or radar (polar plot).",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save the plot as an HTML file. If not provided, opens in browser.",
    )
    parser.add_argument(
        "--list-series",
        action="store_true",
        help="List all available weather series in the EPW file and exit.",
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.epw_file).exists():
        print(f"Error: EPW file not found: {args.epw_file}")
        return

    # List series if requested
    if args.list_series:
        df = read_epw_file(args.epw_file)
        visible_series = get_visible_series(df)
        print("Available weather series:")
        for series in visible_series:
            unit = UNITS.get(series, "")
            print(f"  - {series}" + (f" ({unit})" if unit else ""))
        return

    # Create single visualization
    try:
        fig = visualize_epw(
            epw_file_path=args.epw_file,
            series_name=args.series,
            plot_type=args.type,
            show=False,
        )

        if args.output:
            fig.write_html(args.output)
            print(f"Visualization saved to {args.output}")
        else:
            fig.show()

    except Exception as e:
        print(f"Error creating visualization: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    visualize_cli()
