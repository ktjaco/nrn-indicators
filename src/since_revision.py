import os, sys
import logging
import geopandas as gpd
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

def main(gpkg_in, gpkg_out, layer_in, layer_out):

    # command line system arguments
    gpkg_in = (sys.argv[1])
    gpkg_out = (sys.argv[2])
    layer_in = (sys.argv[3])
    layer_out = (sys.argv[4])

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

    # incoming NRN gpkg
    logger.info("Reading incoming GeoPackage.")
    gdf = gpd.read_file(gpkg_in, layer=layer_in)

    # reproject to epsg:3348
    logger.info("Reprojecting to EPSG:3348.")
    gdf = gdf.to_crs({'init': 'epsg:3348'})

    # calculate years since revision using current year (startTime.year) and "REVDATE"
    logger.info("Calculating years since last revision using current year")
    gdf["SINREV"] = startTime.year - gdf["REVDATE"].str[:4].astype("int64")

    # create representative point for each line segment
    logger.info("Generating representative point for each line segment.")
    gdf["geometry"] = gdf.geometry.representative_point()

    logger.info("Extracting total bounds.")
    minx, miny, maxx, maxy = gdf.geometry.total_bounds

    logger.info("Importing GeoDataFrame into PostGIS.")
    gdf.postgis.to_postgis(con=engine, table_name="reprept", geometry='POINT', if_exists='replace')

    logger.info("Generating hex grid based on total bounds.")
    hex_grid_query = sql_load["gen_hex_grid"]["query"].format(minx, miny, maxx, maxy)

    logger.info("Generating hex grid.")
    grid = gpd.GeoDataFrame.from_postgis(hex_grid_query, engine, geom_col="geom")

    logger.info("Aggregating mean years since last revision over hex grid.")
    aggregate = sql_load["aggregate"]["query"]

    logger.info("Extracting aggregations from PostGIS.")
    gdf = gpd.GeoDataFrame.from_postgis(aggregate, engine, geom_col="geom")

    # overwrite the incoming geopackage
    logger.info("Writing final GeoPackage layer.")
    gdf.to_file(gpkg_out, layer=layer_out, driver="GPKG")


if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("ERROR: You must supply 4 arguments. "
              "Example: python since_revision.py [/path/to/input/*.gpkg] [/path/to/output/*.gpkg] [layer in] [layer out]")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

# output execution time
print("Total execution time: ", datetime.now() - startTime)