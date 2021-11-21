# Imports
import osmnx as ox
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def get_osm_data(lor_gdf, tags, crs="EPSG:25833", location="Berlin, Germany"):
    """
    get_osm_data [summary]

    Parameters
    ----------
    lor_gdf : str
        path to the lor data (i.e. lor_friedrichshain_kreuzberg.geojson)
    tags : dict
        dictionary containing as many tags from OSM (e.g. {"amenity": ["restaurant", "cafe", "fast_food", "bar", "pub", "ice_cream"]}) you want
    crs : str, optional
        Coordinate system, by default "EPSG:25833"
    location : str, optional
        City you want to obtain OSM data from, by default "Berlin, Germany"

    Returns
    -------
    obj
        geopandas dataframe containing merged LOR and POI data
    """
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


def calc_parking_spots(poi_lor, est_parking_spots, agg_func="len", buffer_size=20):
    """
    Calculate the number of parking spots for each POI.

    Parameters
    ----------
    poi_lor : geopandas dataframe
        Dataframe containing POIs within Kreuzberg-Friedrichshain
    est_parking_spots : str
        Path to the estimated parking spots data (i.e. estimated_parking_spots_kfz.geojson)
    agg_func : str, optional
        Aggregation function: accepts "len" and "sum" (by default "len"). Len ignores capacity, sum multiplies capacity with individual points.
    buffer_size : int, optional
        Size of the buffer (in meters) around each POI, by default 20
        (currently a circle, but can easily be changed in any other polygon)

    Returns
    -------
    geopandas dataframe
        Idx0: Dataframe containing POIs within Kreuzberg-Friedrichshain with the number of parking spots for each POI.
        Idx1: Dataframe containing POIs within Kreuzberg-Friedrichshain with polygon coordinates representing the radius around each POI.

    """

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
    if agg_func == "len":
        dfpivot = pd.pivot_table(
            intersect_parking,
            index="name_left",
            columns="capacity",
            aggfunc={"capacity": len},
        )
    else:
        dfpivot = pd.pivot_table(
            intersect_parking,
            index="name_left",
            columns="capacity",
            aggfunc={"capacity": np.sum},
        )
    dfpivot.columns = dfpivot.columns.droplevel()
    dfpivot.index.names = ["name"]
    parking_counts = dfpivot.sum(axis=1)
    parking_counts = parking_counts.to_frame("No. parking spots")

    # Merge back with the main dataframe
    poi_lor_counts = poi_lor.merge(parking_counts.reset_index(), on="name", how="left")
    poi_lor_counts["No. parking spots"] = poi_lor_counts["No. parking spots"].fillna(0)

    return poi_lor_counts, poi_lor_buffered
