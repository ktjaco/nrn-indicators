--------------------------------------------------------------------------------------------------------------------------------
-- HEX GRID - Sample usage script
--------------------------------------------------------------------------------------------------------------------------------
--
-- Hugh Saalmans (@minus34)
-- 2015/04/10
--
-- DESCRIPTION:
--
-- Script creates a new table and populates it with ~14 million hexagons covering mainland US (minus Alaska), using the hex grid function.
-- Takes under 5 mins on my 8 core, 16Gb RAM commodity PC to produce the hexagons, and another 15 mins to index & cluster.
--
-- Coordinate systems (SRIDs) used:
--   input:   WGS84 lat/long - SRID 4326
--   working: US Lambert Azimuthal Equal-Area (WGS84) - SRID 2163
--   output:  WGS84 lat/long - SRID 4326
--
-- LICENSE
--
-- This work is licensed under the Apache License, Version 2: https://www.apache.org/licenses/LICENSE-2.0
--
--------------------------------------------------------------------------------------------------------------------------------

--Create table for results
DROP TABLE IF EXISTS pe_hex_grid;
CREATE TABLE pe_hex_grid (
  gid SERIAL NOT NULL PRIMARY KEY,
  geom GEOMETRY('POLYGON', 4326, 2) NOT NULL
)
WITH (OIDS=FALSE);

-- Create 1km2 hex grid (note: extents allow for the effects of the working projection used)
-- Input parameters: hex_grid(areakm2 float, xmin float, ymin float, xmax float, ymax float, inputsrid integer,
--   workingsrid integer, ouputsrid integer)
INSERT INTO pe_hex_grid (geom)
SELECT hex_grid(5, -64.47716460, 45.85311566, -61.71850330, 47.11987194, 4326, 3348, 4326);

-- Create spatial index
CREATE INDEX pe_hex_grid_geom_idx ON pe_hex_grid USING gist (geom);

-- Cluster table by spatial index (for spatial query performance)
CLUSTER pe_hex_grid USING pe_hex_grid_geom_idx;

-- Update stats on table
ANALYZE pe_hex_grid;

--Check accuracy of results (in square km)
SELECT (SELECT Count(*) FROM pe_hex_grid) AS hexagon_count,
       (SELECT (MIN(ST_Area(geom::GEOGRAPHY, FALSE)) / 1000000.0)::NUMERIC(10,3) FROM pe_hex_grid) AS min_area,
       (SELECT (MAX(ST_Area(geom::GEOGRAPHY, FALSE)) / 1000000.0)::NUMERIC(10,3) FROM pe_hex_grid) AS max_area;