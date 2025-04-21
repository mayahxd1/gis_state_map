import geopandas as gpd

gdf = gpd.read_file('tl_2020_us_state/tl_2020_us_state.shp')
print(gdf.head())