import os, sys
import logging
import geopandas as gpd
import urllib.request
import zipfile
from datetime import datetime
from geopandas_postgis import PostGIS
from psycopg2 import connect, extensions, sql
from sqlalchemy import *
from sqlalchemy.engine.url import URL

import helpers

# Set logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

startTime = datetime.now()

def main(osm_in, nrn_in, out, out_layer):

    # command line system arguments
    osm_in = (sys.argv[1])
    nrn_in = (sys.argv[2])
    out = (sys.argv[3])
    out_layer = (sys.argv[4])

    # database name which will be used for stage 2
    nrn_db = "nrn"

    # load sql yaml file
    sql_load = helpers.load_yaml("sql/sql.yaml")

    # default postgres connection needed to create the nrn database
    conn = connect(
        dbname="postgres",
        user="postgres",
        host="localhost",
        password="password"
    )

    # postgres database url for geoprocessing
    nrn_url = URL(
        drivername='postgresql+psycopg2', host='localhost',
        database=nrn_db, username='postgres',
        port='5432', password='password'
    )

    # engine to connect to nrn database
    engine = create_engine(nrn_url)

    # get the isolation level for autocommit
    autocommit = extensions.ISOLATION_LEVEL_AUTOCOMMIT

    # set the isolation level for the connection's cursors
    # will raise ActiveSqlTransaction exception otherwise
    conn.set_isolation_level(autocommit)

    # connect to default connection
    cursor = conn.cursor()

    # drop the nrn database if it exists, then create it if not
    try:
        logger.info("Dropping PostgreSQL database.")
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {};").format(sql.Identifier(nrn_db)))
    except Exception:
        logger.exception("Could not drop database.")

    try:
        logger.info("Creating PostgreSQL database.")
        cursor.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(nrn_db)))
    except Exception:
        logger.exception("Failed to create PostgreSQL database.")

    logger.info("Closing default PostgreSQL connection.")
    cursor.close()
    conn.close()

    # connection parameters for newly created database
    nrn_conn = connect(
        dbname=nrn_db,
        user="postgres",
        host="localhost",
        password="password"
    )

    nrn_conn.set_isolation_level(autocommit)

    # connect to nrn database
    nrn_cursor = nrn_conn.cursor()
    try:
        logger.info("Creating spatially enabled PostgreSQL database.")
        nrn_cursor.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS postgis;"))
    except Exception:
        logger.exception("Cannot create PostGIS extension.")

    try:
        logger.info("Creating grid function.")
        nrn_cursor.execute(sql.SQL(sql_load["hex_grid"]["function"]))
    except Exception:
        logger.exception("Cannot create PostGIS function.")

    logger.info("Closing NRN PostgreSQL connection.")
    nrn_cursor.close()
    nrn_conn.close()

    # Icoming OSM data
    logger.info("Reading incoming OSM data.")
    osm = gpd.read_file(osm_in)

    logger.info("Transforming incoming OSM data.")
    # osm = osm.to_crs("epsg:3347")

    # Incoming NRN GPKG
    logger.info("Reading incoming GPKG.")
    # gdf = gpd.read_file(gpkg_in, layer=layer_in)
    gdf = gpd.read_file(nrn_in)

    logger.info("Transforming incoming GPKG.")
    # gdf = gdf.to_crs("epsg:3347")
    # minx, miny, maxx, maxy = gdf.geometry.total_bounds
    # print(minx, miny, maxx, maxy)

    logger.info("Reading incoming grid.")
    # gdf = gpd.read_file(gpkg_in, layer=layer_in)
    grid = gpd.read_file("/home/kent/data/STC/lpr/grid.gpkg", driver="GPKG", layer="ab")

    logger.info("Transforming incoming grid.")
    # grid = grid.to_crs("epsg:3347")
    # minx, miny, maxx, maxy = gdf.geometry.total_bounds
    # print(minx, miny, maxx, maxy)

    logger.info("Importing GeoDataFrame into PostGIS.")
    gdf.postgis.to_postgis(con=engine, table_name="nrn", geometry='LineString', if_exists='replace')

    logger.info("Importing OSM data into PostGIS.")
    osm.postgis.to_postgis(con=engine, table_name="osm", geometry='LineString', if_exists='replace')

    logger.info("Importing grid data into PostGIS.")
    grid.postgis.to_postgis(con=engine, table_name="hex_grid", geometry='Polygon', if_exists='replace')

    # logger.info("Extracting total bounds.")
    # minx, miny, maxx, maxy = gdf.geometry.total_bounds
    # minx = minx + (-1)
    # miny = miny - (-1)
    # maxx = maxx + 1
    # maxy = maxy - 1
    # print(minx, miny, maxx, maxy)

    # logger.info("Generating hex grid based on total bounds.")
    # hex_grid_query = sql_load["gen_hex_grid"]["query"].format(minx, miny, maxx, maxy)

    # logger.info("Importing hex grid.")
    # grid = gpd.GeoDataFrame.from_postgis(hex_grid_query, engine, geom_col="geom")

    logger.info("Comparing NRN and OSM road network length.")
    length = sql_load["length"]["query"]

    logger.info("Extracting final from PostGIS.")
    gdf = gpd.GeoDataFrame.from_postgis(length, engine, geom_col="geom")
    gdf.crs = {"init": "epsg:3348"}

    # overwrite the incoming geopackage
    logger.info("Writing output GeoPackage.")
    # gdf.to_file(gpkg_out, layer=layer_out, driver='GPKG')
    gdf.to_file(out, layer=out_layer, driver="GPKG")


if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("ERROR: You must supply 2 arguments. "
              "Example: python compare_length_osm.py [/path/to/input_osm/] [/path/to/input_nrn/] [/path/to/output/]")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

# output execution time
print("Total execution time: ", datetime.now() - startTime)