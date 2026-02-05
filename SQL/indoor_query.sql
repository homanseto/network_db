SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'imdf_unit'
ORDER BY ordinal_position;

SELECT 
    displayname,
    ST_GeometryType(geom) as geom_type,
    ST_Dimension(geom) as dim,
    ST_SRID(geom) as srid,
    ST_IsValid(geom) as is_valid,
    ST_NDims(geom) as num_dims,
    ST_ZMin(geom) as z_min,
    ST_ZMax(geom) as z_max,
    ST_NumGeometries(geom) as num_geometries
FROM public.imdf_unit
WHERE displayname IN (
    'KLN_329_Boundary Street Recreation Ground Boundary Street Sports Centre No1',
    'HK_112_Central Station',
    'HK_5_Queen Elizabeth Stadium'
);


SELECT * FROM public.imdf_unit WHERE displayname LIKE 'KLN_329_Boundary Street Recreation Ground Boundary Street Sports Centre No1'




SELECT id, displayname, category, level_id, 
                       ST_AsText(ST_Transform(geom, 4326)) as geom_text,
                       ST_ZMin(geom) as min_z,
                       ST_ZMax(geom) as max_z
                FROM public.imdf_unit
                WHERE displayname = 'HK_5_Queen Elizabeth Stadium'




