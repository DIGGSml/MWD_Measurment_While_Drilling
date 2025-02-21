
import netCDF4 as nc
import pandas as pd
import xarray as xr

# Method 1: Using xarray (recommended)
ds = xr.open_dataset('/workspaces/MWD_Measurment_While_Drilling/LIM_format(.bor)/59650240611100849D/data.nc')
df = ds.to_dataframe()

# List all columns (variables)
print(df.columns)