import geopandas as gpd
import os, sys
import logging
from datetime import datetime

sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers
import qgis_processing

# Set logger.
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

startTime = datetime.now()

def main(network, nrn, output, output_layer):

    # command line system arguments
    network = (sys.argv[1])
    nrn = (sys.argv[2])
    output = (sys.argv[3])
    output_layer = (sys.argv[4])

    # load the two datasets that will be compared
    net_gdf = gpd.read_file(network)
    nrn = gpd.read_file(nrn)






if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("ERROR: You must supply 4 arguments. "
              "Example: python compare_length_osm.py [/path/to/input_osm/] [/path/to/input_nrn/] [/path/to/output/]")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

# output execution time
print("Total execution time: ", datetime.now() - startTime)