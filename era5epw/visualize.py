"""EPW file visualization tool.

This module provides interactive visualization of EPW (EnergyPlus Weather) files using
Plotly. It supports both command-line usage and API usage in Jupyter notebooks.
"""

import argparse
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from era5epw.psychrometrics import (
    humidity_ratio_from_enthalpy,
    humidity_ratio_from_vapor_pressure,
    moist_air_enthalpy,
    moist_air_specific_volume,
    saturation_humidity_ratio,
    saturation_temperature_from_enthalpy,
    vapor_pressure_from_relative_humidity,
    wet_bulb_temperature,
)
from era5epw.reader import read_epw_file

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

# Psychrometric chart curve colors
PSYCHROMETRIC_COLORS = {
    "saturation": "#212529",
    "relative_humidity": "#1f77b4",
    "enthalpy": "#ff7f0e",
    "dew_point": "#e377c2",
}

# Cyclic seasonal color scale for the day of year: winter, spring, summer, autumn, winter
SEASONAL_COLORSCALE = [
    [0.0, "#08306b"],
    [0.25, "#31a354"],
    [0.5, "#e6550d"],
    [0.75, "#c9a227"],
    [1.0, "#08306b"],
]


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


def compute_psychrometric_states(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the psychrometric state of outdoor air for each valid EPW record.

    Records with missing (out of range) dry bulb temperature, dew point temperature,
    relative humidity or station pressure are dropped.

    :param df: DataFrame containing weather data.
    :return: DataFrame with measured and calculated psychrometric values (humidity ratio in
        kg/kg dry air, enthalpy in kJ/kg dry air, vapor pressure in Pa, specific volume in
        m³/kg dry air, wet bulb temperature in °C).
    """
    t = df["Dry Bulb Temperature"]
    td = df["Dew Point Temperature"]
    rh = df["Relative Humidity"]
    p = df["Atmospheric Station Pressure"]

    # EPW missing values are out of the valid ranges
    valid = (
        t.between(-70, 70, inclusive="neither")
        & td.between(-70, 70, inclusive="neither")
        & rh.between(0, 110)
        & p.between(31000, 120000, inclusive="neither")
    )
    states = df.loc[
        valid,
        [
            "Dry Bulb Temperature",
            "Dew Point Temperature",
            "Relative Humidity",
            "Atmospheric Station Pressure",
        ],
    ].copy()

    t, rh, p = (
        states["Dry Bulb Temperature"].to_numpy(dtype=float),
        states["Relative Humidity"].to_numpy(dtype=float),
        states["Atmospheric Station Pressure"].to_numpy(dtype=float),
    )
    pw = vapor_pressure_from_relative_humidity(t, rh)
    w = humidity_ratio_from_vapor_pressure(pw, p)
    states["Humidity Ratio"] = w
    states["Enthalpy"] = moist_air_enthalpy(t, w)
    states["Wet Bulb Temperature"] = wet_bulb_temperature(t, w, p)
    states["Vapor Pressure"] = pw
    states["Specific Volume"] = moist_air_specific_volume(t, w, p)

    return states


def _psychrometric_curve(
    x: np.ndarray,
    y: np.ndarray,
    name: str,
    color: str,
    label: str,
    label_index: int,
    text_position: str,
    legend_group: str,
    show_legend: bool,
    visible: bool,
    dash: str = "solid",
    width: float = 1,
) -> go.Scatter:
    """Create a labeled psychrometric chart curve.

    :param x: Dry bulb temperatures (°C).
    :param y: Humidity ratios (g/kg dry air).
    :param name: Name of the curve family, displayed in the legend.
    :param color: Color of the curve and its label.
    :param label: Label of the curve, displayed at `label_index`.
    :param label_index: Index of the curve point where the label is displayed.
    :param text_position: Position of the label relative to the curve point.
    :param legend_group: Legend group of the curve family, to toggle all its curves at once.
    :param show_legend: Whether to display the curve in the legend.
    :param visible: Whether the curve is visible, or only displayed in the legend.
    :param dash: Dash style of the curve.
    :param width: Width of the curve.
    :return: Plotly Scatter trace.
    """
    return go.Scatter(
        x=x,
        y=y,
        mode="lines+text",
        name=name,
        legendgroup=legend_group,
        showlegend=show_legend,
        visible=True if visible else "legendonly",
        line=dict(color=color, width=width, dash=dash),
        text=[label if i == label_index else "" for i in range(len(x))],
        textposition=text_position,
        textfont=dict(color=color, size=10),
        hoverinfo="skip",
        cliponaxis=False,
    )


def create_psychrometric_plot(
    df: pd.DataFrame,
    show_relative_humidity: bool = True,
    show_enthalpy: bool = False,
    show_dew_point: bool = False,
    width: int = 1200,
    height: int = 750,
) -> go.Figure:
    """Create a psychrometric chart showing each hourly record of the year.

    Each record is displayed as a point (dry bulb temperature, humidity ratio), colored by
    its day of the year. Relative humidity, enthalpy and dew point curves are drawn at the
    median station pressure, each family with its own color. Curve families can be toggled
    by clicking on their legend entry.

    :param df: DataFrame containing weather data.
    :param show_relative_humidity: Whether relative humidity curves are initially visible.
    :param show_enthalpy: Whether enthalpy curves are initially visible.
    :param show_dew_point: Whether dew point curves are initially visible.
    :param width: Width of the plot in pixels.
    :param height: Height of the plot in pixels.
    :return: Plotly Figure object.
    """
    states = compute_psychrometric_states(df)
    if states.empty:
        raise ValueError(
            "No valid dry bulb temperature, dew point temperature, relative humidity and "
            "station pressure records found to create a psychrometric chart."
        )

    t = states["Dry Bulb Temperature"].to_numpy()
    w = states["Humidity Ratio"].to_numpy() * 1000
    pressure = float(states["Atmospheric Station Pressure"].median())

    # chart ranges
    t_min = 5 * np.floor((t.min() - 2) / 5)
    t_max = 5 * np.ceil((t.max() + 2) / 5)
    w_max = float(np.ceil(max(w.max(), 1.0) * 1.15))
    t_grid = np.linspace(t_min, t_max, 200)

    fig = go.Figure()

    # saturation curve
    w_sat = saturation_humidity_ratio(t_grid, pressure) * 1000
    in_range = w_sat <= w_max
    fig.add_trace(
        _psychrometric_curve(
            t_grid[in_range],
            w_sat[in_range],
            name="Saturation",
            color=PSYCHROMETRIC_COLORS["saturation"],
            label="100%",
            label_index=int(in_range.sum()) - 1,
            text_position="top left",
            legend_group="saturation",
            show_legend=True,
            visible=True,
            width=2,
        )
    )

    # relative humidity curves
    first = True
    for rh in range(10, 100, 10):
        w_rh = (
            humidity_ratio_from_vapor_pressure(
                vapor_pressure_from_relative_humidity(t_grid, rh), pressure
            )
            * 1000
        )
        in_range = w_rh <= w_max
        if in_range.sum() < 2:
            continue
        fig.add_trace(
            _psychrometric_curve(
                t_grid[in_range],
                w_rh[in_range],
                name="Relative Humidity (%)",
                color=PSYCHROMETRIC_COLORS["relative_humidity"],
                label=f"{rh}%",
                label_index=int(in_range.sum()) - 1,
                text_position="top left",
                legend_group="relative_humidity",
                show_legend=first,
                visible=show_relative_humidity,
            )
        )
        first = False

    # enthalpy curves, from the saturation curve (or chart edges) to zero humidity ratio
    w_corner = min(w_max, float(saturation_humidity_ratio(t_max, pressure)) * 1000)
    h_low = 1.006 * t_min
    h_high = float(moist_air_enthalpy(t_max, w_corner / 1000))
    first = True
    for h in np.arange(10 * np.ceil(h_low / 10), h_high, 10):
        t_start = max(float(saturation_temperature_from_enthalpy(h, pressure)), t_min)
        t_end = min(h / 1.006, t_max)
        if t_start >= t_end:
            continue
        t_h = np.linspace(t_start, t_end, 50)
        w_h = humidity_ratio_from_enthalpy(h, t_h) * 1000
        in_range = (w_h <= w_max) & (w_h >= 0)
        if in_range.sum() < 2:
            continue
        fig.add_trace(
            _psychrometric_curve(
                t_h[in_range],
                w_h[in_range],
                name="Enthalpy (kJ/kg)",
                color=PSYCHROMETRIC_COLORS["enthalpy"],
                label=f"{h + 0.0:g} kJ/kg",
                label_index=0,
                text_position="top left",
                legend_group="enthalpy",
                show_legend=first,
                visible=show_enthalpy,
                dash="dot",
            )
        )
        first = False

    # dew point curves: constant humidity ratio, from the saturation curve to the right edge
    first = True
    for td in np.arange(5 * np.ceil(t_min / 5), t_max, 5):
        w_td = float(saturation_humidity_ratio(td, pressure)) * 1000
        if w_td > w_max:
            continue
        fig.add_trace(
            _psychrometric_curve(
                np.array([td, t_max]),
                np.array([w_td, w_td]),
                name="Dew Point (°C)",
                color=PSYCHROMETRIC_COLORS["dew_point"],
                label=f"{td + 0.0:g}°C",
                label_index=0,
                text_position="middle left",
                legend_group="dew_point",
                show_legend=first,
                visible=show_dew_point,
                dash="dash",
            )
        )
        first = False

    # hourly records, colored by day of year
    index = pd.DatetimeIndex(states.index)
    day_of_year = (index.dayofyear - 1 + index.hour / 24).to_numpy()
    month_starts = pd.date_range(start=f"{index[0].year}-01-01", periods=12, freq="MS")
    customdata = np.column_stack(
        [
            index.strftime("%Y-%m-%d %H:%M"),
            states["Dew Point Temperature"].to_numpy(),
            states["Relative Humidity"].to_numpy(),
            states["Atmospheric Station Pressure"].to_numpy(),
            states["Enthalpy"].to_numpy(),
            states["Wet Bulb Temperature"].to_numpy(),
            states["Vapor Pressure"].to_numpy(),
            states["Specific Volume"].to_numpy(),
        ]
    ).astype(object)
    fig.add_trace(
        go.Scattergl(
            x=t,
            y=w,
            mode="markers",
            name="Hourly records",
            showlegend=False,
            marker=dict(
                size=5,
                opacity=0.8,
                color=day_of_year,
                colorscale=SEASONAL_COLORSCALE,
                cmin=0,
                cmax=366,
                colorbar=dict(
                    title="Month",
                    tickvals=(month_starts.dayofyear - 1).tolist(),
                    ticktext=month_starts.strftime("%b").tolist(),
                    len=0.75,
                ),
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Dry Bulb Temperature: %{x:.1f} °C<br>"
                "Dew Point Temperature: %{customdata[1]:.1f} °C<br>"
                "Relative Humidity: %{customdata[2]:.0f} %<br>"
                "Atmospheric Station Pressure: %{customdata[3]:.0f} Pa<br>"
                "Humidity Ratio: %{y:.2f} g/kg<br>"
                "Enthalpy: %{customdata[4]:.1f} kJ/kg<br>"
                "Wet Bulb Temperature: %{customdata[5]:.1f} °C<br>"
                "Vapor Pressure: %{customdata[6]:.0f} Pa<br>"
                "Specific Volume: %{customdata[7]:.3f} m³/kg"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"Psychrometric Chart (curves at {pressure / 1000:.1f} kPa)",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Dry Bulb Temperature (°C)",
            range=[t_min, t_max],
            dtick=5,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Humidity Ratio (g/kg dry air)",
            range=[0, w_max],
            showgrid=False,
            zeroline=False,
        ),
        legend=dict(
            title=dict(text="Curves (click to toggle):"),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        plot_bgcolor="white",
        hovermode="closest",
        hoverlabel=dict(bgcolor="white", font=dict(size=13)),
        width=width,
        height=height,
        margin=dict(t=100, r=20, b=60, l=60),
    )

    return fig


def visualize_epw(
    epw_file_path: str,
    series_name: str = "Dry Bulb Temperature",
    plot_type: Literal["2D", "3D", "radar", "psychrometric"] = "2D",
    show: bool = True,
    renderer: Literal["notebook", "browser", "iframe"] = "notebook",
    show_relative_humidity: bool = True,
    show_enthalpy: bool = False,
    show_dew_point: bool = False,
) -> go.Figure:
    """Visualize EPW weather data with interactive plots.

    :param epw_file_path: Path to the EPW file.
    :param series_name: Name of the weather series to visualize (ignored for psychrometric
        charts).
    :param plot_type: Type of plot: "2D", "3D", "radar" or "psychrometric".
    :param show: If True, display the plot immediately (useful in Jupyter).
    :param renderer: Renderer to use for displaying the plot ("notebook", "browser", or
        "iframe").
    :param show_relative_humidity: Psychrometric chart only, whether relative humidity
        curves are initially visible.
    :param show_enthalpy: Psychrometric chart only, whether enthalpy curves are initially
        visible.
    :param show_dew_point: Psychrometric chart only, whether dew point curves are initially
        visible.
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
    elif plot_type == "psychrometric":
        fig = create_psychrometric_plot(
            df,
            show_relative_humidity=show_relative_humidity,
            show_enthalpy=show_enthalpy,
            show_dew_point=show_dew_point,
        )
    else:
        raise ValueError(
            f"Invalid plot_type: {plot_type}. Must be '2D', '3D', 'radar' or 'psychrometric'."
        )

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
        choices=["2D", "3D", "radar", "psychrometric"],
        default="2D",
        help=(
            "Type of visualization: 2D (line plot), 3D (surface plot), radar (polar plot), or "
            "psychrometric (psychrometric chart of all hourly records, --series is ignored)."
        ),
    )
    parser.add_argument(
        "--relative-humidity",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Psychrometric chart: show relative humidity curves (default: shown).",
    )
    parser.add_argument(
        "--enthalpy",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Psychrometric chart: show enthalpy curves (default: hidden).",
    )
    parser.add_argument(
        "--dew-point",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Psychrometric chart: show dew point curves (default: hidden).",
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
            show_relative_humidity=args.relative_humidity,
            show_enthalpy=args.enthalpy,
            show_dew_point=args.dew_point,
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
