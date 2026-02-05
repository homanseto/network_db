SELECT current_database();


SELECT PostGIS_version();
SELECT ST_GeomFromText('POINT(0 0)');

SELECT COUNT(*) 
FROM information_schema.tables 
WHERE table_schema = 'citydb' 
AND table_type = 'BASE TABLE';


SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'citydb' 
AND table_name = 'database_srs';

SELECT * FROM citydb.database_srs;

-- Check if key application tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'citydb' 
AND table_name IN (
    'cityobject',      -- Base table for all city objects
    'building',        -- Building features
    'room',            -- Room/interior space features
    'surface_geometry', -- Geometry storage
    'appearance',      -- Appearance/texture data
    'address',         -- Address information
    'cityobject_genericattrib', -- Generic attributes
    'citymodel'        -- City model metadata
)
ORDER BY table_name;


-- See all tables in citydb_data schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'citydb' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Count total tables
SELECT COUNT(*) as total_tables
FROM information_schema.tables 
WHERE table_schema = 'citydb' 
AND table_type = 'BASE TABLE';

SELECT 
    conname as constraint_name,
    conrelid::regclass as table_name,
    confrelid::regclass as referenced_table
FROM pg_constraint
WHERE contype = 'f'
AND connamespace = 'citydb'::regnamespace
LIMIT 10;


SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'citydb_data' 
AND table_name IN (
    'cityobject', 'building', 'room', 'surface_geometry',
    'appearance', 'address', 'cityobject_genericattrib', 'citymodel'
)
ORDER BY table_name;

SELECT * FROM citydb.feature
		
SELECT * FROM citydb.geometry_data

SELECT *  FROM citydb.tex_image;

SELECT id, classname, tablename, is_toplevel
FROM citydb.objectclass
WHERE is_toplevel = true
ORDER BY classname
LIMIT 20;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tex_image'
  AND table_schema = 'citydb';



