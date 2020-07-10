import fiona
import geopandas as gpd
import os, sys
import logging
from datetime import datetime

sys.path.insert(1, os.path.join(sys.path[0], ".."))
# import helpers
# import qgis_processing

# Set logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

startTime = datetime.now()

def main(network, nrn, nrn_layer):

    # command line system arguments
    network = (sys.argv[1])
    nrn = (sys.argv[2])
    nrn_layer = (sys.argv[3])
    # output = (sys.argv[4])

    # load the two datasets that will be compared
    net_gdf = gpd.read_file(network)
    nrn = gpd.read_file(nrn, layer=nrn_layer)

    # convert to projects CRS
    nrn = nrn.to_crs("EPSG:3348")
    net_gdf = net_gdf.to_crs("EPSG:3348")

    # buffer "true" road network
    nrn_buffer = nrn.buffer(10)

    logger.info("Creating buffer gdf.")
    nrn_buffer_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(nrn_buffer))
    # nrn_buffer_gdf = nrn_buffer_gdf.to_crs("EPSG:3348")

    # clip tested road network
    # logger.info("Simplify buffer.")
    # nrn_buffer_gdf_sim = nrn_buffer_gdf.simplify(0.2, preserve_topology=True)

    # net_gdf_sindex = net_gdf.sindex
    # nrn_buffer_gdf_sim_sindex = nrn_buffer_gdf_sim.sindex

    logger.info("Clipping...")
    nrn_clip = gpd.overlay(net_gdf, nrn_buffer_gdf, how="intersection")


    logger.info("Printing...")
    nrn_clip.to_file("../data/interim/output.gpkg", layer="nrn_clip", driver="GPKG")
    net_gdf.to_file("../data/interim/output.gpkg", layer="network", driver="GPKG")
    nrn_buffer_gdf.to_file("../data/interim/output.gpkg", layer="nrn_buffer", driver="GPKG")

    sys.exit(1)




if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("ERROR: You must supply 4 arguments. "
              "Example: python..")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])

# output execution time
print("Total execution time: ", datetime.now() - startTime)