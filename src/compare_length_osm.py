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

def main(osm_in, gpkg_in, layer_in, gpkg_out, layer_out):

    # command line system arguments
    osm_in = (sys.argv[1])
    gpkg_in = (sys.argv[2])
    layer_in = (sys.argv[3])
    gpkg_out = (sys.argv[4])
    layer_out = (sys.argv[5])

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
    osm.crs = {'init': 'epsg:3348'}
    minx, miny, maxx, maxy = osm.geometry.total_bounds
    print(minx, miny, maxx, maxy)

    # Incoming NRN GPKG
    logger.info("Reading incoming GPKG.")
    gdf = gpd.read_file(gpkg_in, layer=layer_in)

    logger.info("Transforming incoming GPKG.")
    gdf.crs = {'init': 'epsg:3348'}
    minx, miny, maxx, maxy = gdf.geometry.total_bounds
    print(minx, miny, maxx, maxy)

    logger.info("Importing GeoDataFrame into PostGIS.")
    gdf.postgis.to_postgis(con=engine, table_name="nrn", geometry='LineString', if_exists='replace')

    logger.info("Importing OSM data into PostGIS.")
    osm.postgis.to_postgis(con=engine, table_name="osm", geometry='LineString', if_exists='replace')

    logger.info("Extracting total bounds.")
    minx, miny, maxx, maxy = gdf.geometry.total_bounds
    minx = minx + (-1)
    miny = miny - (-1)
    maxx = maxx + 1
    maxy = maxy - 1
    print(minx, miny, maxx, maxy)

    logger.info("Generating hex grid based on total bounds.")
    hex_grid_query = sql_load["gen_hex_grid"]["query"].format(minx, miny, maxx, maxy)

    logger.info("Generating hex grid.")
    grid = gpd.GeoDataFrame.from_postgis(hex_grid_query, engine, geom_col="geom")

    logger.info("Comparing NRN and OSM road network length.")
    length = sql_load["length"]["query"]

    logger.info("Extracting final from PostGIS.")
    gdf = gpd.GeoDataFrame.from_postgis(length, engine, geom_col="geom")

    # overwrite the incoming geopackage
    logger.info("Writing output GeoPackage.")
    gdf.to_file(gpkg_out, layer=layer_out, driver='GPKG')


if __name__ == "__main__":

    if len(sys.argv) != 6:
        print("ERROR: You must supply 4 arguments. "
              "Example: python since_revision.py [/path/to/input/*.gpkg] [/path/to/output/*.gpkg] [layer in] [layer out]")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

# output execution time
print("Total execution time: ", datetime.now() - startTime)