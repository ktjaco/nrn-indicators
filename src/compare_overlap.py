import geopandas as gpd
import sys
import logging
from datetime import datetime

# Set logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

startTime = datetime.now()

def main(network, net_layer, nrn, nrn_layer):

    # command line system arguments
    network = (sys.argv[1])
    net_layer = (sys.argv[2])
    nrn = (sys.argv[3])
    nrn_layer = (sys.argv[4])

    # load the two datasets that will be compared
    logger.info("Reading tested and NRN datasets.")
    net_gdf = gpd.read_file(network, layer=net_layer)
    nrn = gpd.read_file(nrn, layer=nrn_layer)

    # convert to projects CRS
    logger.info("Converting tested and NRN datasets to EPSG:3348.")
    nrn = nrn.to_crs("EPSG:3348")
    net_gdf = net_gdf.to_crs("EPSG:3348")

    # buffer "true" road network
    logger.info("Performing a 10 metre buffer on the NRN dataset.")
    buff_width = 10
    nrn_buffer = nrn.buffer(buff_width)

    logger.info("Creating buffer gdf.")
    nrn_buffer_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(nrn_buffer))

    logger.info("Clipping the tested dataset with NRN dataset.")
    nrn_clip = gpd.overlay(net_gdf, nrn_buffer_gdf, how="intersection")

    nrn_clip_length = nrn_clip.length.sum()
    net_gdf_length = net_gdf.length.sum()

    logger.info("Calculating tested network overlap percentage.")
    percentage = (nrn_clip_length / net_gdf_length) * 100
    percentage = round(percentage, 2)

    logger.info("{}% of the tested road network falls within {} metres of the NRN dataset."
                .format(percentage, buff_width))

if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("ERROR: You must supply 4 arguments. "
              "Example: python3 [GPKG path] [GPKG layer] [NRN path] [NRN layer]")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

# output execution time
print("Total execution time: ", datetime.now() - startTime)
