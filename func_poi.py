# Imports
import osmnx as ox
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def get_osm_data(lor_gdf, tags, crs="EPSG:25833", location="Berlin, Germany"):
    # Load data
    try:
        lor_gdf = gpd.read_file(lor_gdf)
    except:
        print("Can't load LOR file")
    # Obtain coordinates of POIs
    poi = ox.geometries_from_place(location, tags=tags)
    poi_points = poi[poi.geom_type == "Point"]

    # Drop unnecessary (debatable) information
    poi = poi_points.dropna(axis=1)
    poi["name"] = poi_points["name"]

    # Project to the same coordinate system
    poi = poi.to_crs(crs)

    # We look for the intersection of all pois and our Bezirk
    poi_lor = gpd.sjoin(poi, lor_gdf, predicate="intersects")

    return poi_lor


def calc_parking_spots(poi_lor, est_parking_spots, buffer_size=20):
    # Load data
    try:
        est_parking_spots = gpd.read_file(est_parking_spots)
    except:
        print("Can't load parking spots file")

    # Define a circular region around each poi
    poi_lor_buffered = poi_lor.copy()
    poi_lor_buffered["geometry"] = poi_lor["geometry"].buffer(buffer_size)
    poi_lor_buffered = poi_lor_buffered.drop(labels=["index_right"], axis=1)

    # Intersect parking spots and area
    intersect_parking = gpd.sjoin(poi_lor_buffered, est_parking_spots)

    # Calculate parking spots
    intersect_parking["capacity"] = intersect_parking["capacity"].apply(int)
    dfpivot = pd.pivot_table(
        intersect_parking,
        index="name_left",
        columns="capacity",
        aggfunc={"capacity": len},
    )
    dfpivot.columns = dfpivot.columns.droplevel()
    dfpivot.index.names = ["name"]
    parking_counts = dfpivot.sum(axis=1)
    parking_counts = parking_counts.to_frame("No. parking spots")

    # Merge back with the main dataframe
    poi_lor_counts = poi_lor.merge(parking_counts.reset_index(), on="name", how="left")
    poi_lor_counts["No. parking spots"] = poi_lor_counts["No. parking spots"].fillna(0)

    return poi_lor_counts, poi_lor_buffered
