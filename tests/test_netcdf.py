import unittest
from pathlib import Path

import pandas as pd

from era5epw.utils import (
    concat_netcdf_files_to_df,
    load_netcdf,
    unzip_and_load_netcdf_to_df,
)


class TestNetCDF(unittest.TestCase):
    def test_load_cams_full_year(self):
        cams_file = Path(__file__).parent / "resources" / "cams_2024.nc"
        self.assertTrue(
            cams_file.exists(), f"CAMS full year NetCDF file does not exist: {cams_file}"
        )
        ds = load_netcdf(cams_file)

        nb_days_2024 = 366
        nb_hours_2024 = nb_days_2024 * 24
        for solar_var in ["GHI", "DHI", "BHI", "BNI"]:
            values = ds[solar_var].values.squeeze()
            self.assertEqual(nb_hours_2024, len(values))
            self.assertTrue((values >= 0).all())

        cams_df = ds.to_dataframe()
        cams_df.index = pd.to_datetime(cams_df.index.get_level_values("time"))
        cams_df = cams_df.reindex(
            pd.date_range(start="2024-01-01 00:00", end="2024-12-31 23:00", freq="1h"),
            method="bfill",
        )
        self.assertEqual(nb_hours_2024, len(cams_df))

    def test_concat_netcdf(self):
        # we have january and february 2024 data in separate files
        combined_ds = concat_netcdf_files_to_df(
            str(Path(__file__).parent / "resources" / "era5_2024_*.nc")
        )
        self.assertEqual((31 + 29) * 24, len(combined_ds))
        self.assertTrue((combined_ds["t2m"].values >= 0).all())
        self.assertTrue((combined_ds["d2m"].values >= 0).all())

    def test_load_zipped_netcdf(self):
        zipped_file = Path(__file__).parent / "resources" / "era5_2024.zip"
        self.assertTrue(zipped_file.exists(), f"Zipped NetCDF file does not exist: {zipped_file}")
        ds = unzip_and_load_netcdf_to_df(str(zipped_file), clean_up=True)
        self.assertTrue(isinstance(ds, pd.DataFrame))
        self.assertEqual(366 * 24, len(ds))
