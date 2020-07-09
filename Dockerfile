FROM osgeo/gdal

RUN apt update

RUN apt install -y python3-pip \
    libspatialindex-dev \
    ca-certificates

RUN pip3 install geopandas \
    rtree \
    pyopenssl
