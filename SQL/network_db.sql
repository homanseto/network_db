SELECT * FROM network_test

SELECT
    pedrouteid,
	aliasnamen,
	aliasnamtc,
	levelid,
    ST_AsGeoJSON(shape) AS geojson
FROM network_test;

SELECT f_geometry_column, type, srid
FROM geometry_columns
WHERE f_table_name = 'network_test';


SELECT
    a.attname,
    format_type(a.atttypid, a.atttypmod)
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
WHERE c.relname = 'network_test'
AND a.attname = 'shape';


SELECT ST_NDims(shape)
FROM network_test
LIMIT 5;


ALTER TABLE network_test
DROP CONSTRAINT network_test_pkey;

ALTER TABLE public.network_test
ADD PRIMARY KEY (pedrouteid);

SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM
    information_schema.columns
WHERE
    table_name = 'network_test';

#####
ALTER TABLE network_test
ADD COLUMN new_shape geometry(LINESTRINGZ, 2326);

UPDATE network_test
SET new_shape = ST_Force3DZ(shape::geometry(LINESTRINGZ, 2326));

ALTER TABLE network_test
DROP COLUMN shape;

ALTER TABLE network_test
RENAME COLUMN new_shape TO shape;

####
ALTER TABLE public.network_test
ALTER COLUMN shape
TYPE geometry(LINESTRINGZ, 2326)
USING ST_SetSRID(shape, 2326);


