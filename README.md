[![tests](https://github.com/airboxlab/era5epw/actions/workflows/tests.yml/badge.svg)](https://github.com/airboxlab/era5epw/actions/workflows/tests.yml)
![PyPI - Version](https://img.shields.io/pypi/v/era5epw.svg)
![PyPI - Downloads](https://img.shields.io/pypi/dm/era5epw.svg)
![GitHub License](https://img.shields.io/github/license/airboxlab/era5epw)

# ERA5 to EPW Converter

A tool that fetches ERA5 data and generates a full year AMY (Actual Meteorological Year) EnergyPlus Weather file (EPW).

The tool takes care of fetching the necessary data from the Copernicus Climate Data Store (CDS) and the Copernicus Atmosphere Data Store (CAMS),
processing it, and formatting it into the EPW format. It's designed for fast and efficient data retrieval.

# Installation

## Prerequisites

Make sure to register for an API key and validate licences at:

- https://cds.climate.copernicus.eu/ (ERA5 data)
- https://ads.atmosphere.copernicus.eu/ (Copernicus Atmosphere Data Store)

Then create the file `~/.cdsapirc` with the following content:

```ini
url: https://cds.climate.copernicus.eu/api/v2
key: <your_api_key>
```

Note: the URL will be dynamically managed by the script depending on the data source.
The API key doesn't vary, it's the same for both ERA5 and CAMS data.

Moreover, before proceeding, it is required to accept all the licenses in the section "Your profile" in the website of [Copernicus](https://cds.climate.copernicus.eu/profile?tab=licences).

## Install the package

### From PyPI

```bash
pip install era5epw
```

### From source

Clone the current repository and install the required dependencies using [Poetry](https://python-poetry.org/):

```bash
git clone https://github.com/airboxlab/era5epw.git
poetry install
```

# Usage

> \[!NOTE\]
> When running in a Jupyter notebook, to make progress bars and interactive widgets work, make sure to install `ipywidgets` and to enable the widgets extension.

```bash
pip install ipywidgets
# optional, not needed with Jupyter Notebook 7+
jupyter nbextension enable --py widgetsnbextension
```

## Generating EPW Files

### Command line interface

Example usage:

```bash
# using poetry, execute in local repository
poetry run era5epw_download --year 2024 --latitude 49.4 --longitude 0.1 --city-name "Le Havre" --elevation 0 --time-zone 1

# using installed binary, after pypi package installation
era5epw_download --year 2024 --latitude 49.4 --longitude 0.1 --city-name "Le Havre" --elevation 0 --time-zone 1
```

By default, the `time-zone` argument is used only to populate the `LOCATION` header and data time is UTC. Use `--apply-time-zone-to-data` to apply it to the date and time fields (this will shift the UTC time by the provided time zone offset).

Use `--help` to have a list of available options.

### Python API

Example usage:

```python
from era5epw.main import download_and_make_epw

download_and_make_epw(
    year=2025,
    latitude=48.8,
    longitude=2.4,
    city_name="Paris",
    time_zone=1,
    elevation=0,
    output_file="/tmp/era5epw_paris_2025.epw",
    apply_time_zone_to_data=True,
)
```

## Visualizing EPW Files

The package includes an interactive visualization tool for EPW files that supports three types of plots: 2D line charts, 3D surface plots, and radar (polar) plots.

### Command line interface

```bash
# List available weather series in an EPW file
era5epw_visualize path/to/file.epw --list-series

# Create a 2D line plot (default)
era5epw_visualize path/to/file.epw --series "Dry Bulb Temperature" --type 2D

# Create a 3D surface plot
era5epw_visualize path/to/file.epw --series "Wind Speed" --type 3D

# Create a radar plot showing daily min/max values
era5epw_visualize path/to/file.epw --series "Global Horizontal Radiation" --type radar

# Save visualization to HTML file
era5epw_visualize path/to/file.epw --series "Dry Bulb Temperature" --output visualization.html
```

### Python API

Use in Jupyter notebooks or Python scripts:

```python
from era5epw.visualize import visualize_epw

# Create interactive 2D plot
fig = visualize_epw(
    epw_file_path="path/to/file.epw",
    series_name="Dry Bulb Temperature",
    plot_type="2D",
    show=True  # Display immediately in Jupyter
)

# Create 3D surface plot
fig = visualize_epw(
    epw_file_path="path/to/file.epw",
    series_name="Wind Speed",
    plot_type="3D",
    show=True
)

# Create radar plot
fig = visualize_epw(
    epw_file_path="path/to/file.epw",
    series_name="Global Horizontal Radiation",
    plot_type="radar",
    show=True
)

# Save to HTML file
fig.write_html("visualization.html")
```

[![EPW Visualization](./doc/era5epw_dl_viz_notebook.gif)](./doc/era5epw_dl_viz_notebook.gif)

# Documentation

[ERA5](https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation) \
[CAMS](https://ecmwf-projects.github.io/copernicus-training-cams/intro.html) \
[EPW format](https://designbuilder.co.uk/cahelp/Content/EnergyPlusWeatherFileFormat.htm) \
[Earthkit](https://github.com/ecmwf/earthkit-data/)

Datasets home pages:

- [ERA5 hourly time-series data on single levels from 1940 to present](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries) (Experimental)
- [ERA5 Land hourly time-series data from 1950 to present](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries) (Experimental)
- [ERA5 hourly data on single levels from 1940 to present](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)
- [CAMS solar radiation time-series](https://ads.atmosphere.copernicus.eu/datasets/cams-solar-radiation-timeseries)

View your API requests and download responses at:

[CDS Requests](https://cds.climate.copernicus.eu/requests?tab=all) \
[ADS Requests](https://ads.atmosphere.copernicus.eu/requests?tab=all)

Check CDS API status at [CDS Live](https://cds.climate.copernicus.eu/live), it provides information about
congestion for each dataset.
