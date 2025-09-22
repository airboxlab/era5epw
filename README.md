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

Example usage:

```bash
poetry run download --year 2024 --latitude 49.4 --longitude 0.1 --city-name "Le Havre" --elevation 0 --time-zone 1
```

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
