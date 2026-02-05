### ogr2ogr command explanation###

-f format :Specifies the output format.
-t_srs :Reprojects the output data.
-s_srs :Defines the SRS of the input data.
-append :Appends data to an existing file.
-update :Updates existing features.
-nln :Specifies the output layer name.
-nlt :Forces the output geometry type.
-lco :Layer creation options (format-specific).
-where :Filters features based on a condition.
-sql :Executes an SQL query on the input data.
-select :Selects specific fields to include.
-upsert :Updates or inserts features.(not allowed with '-append)
-overwrite :Overwrites the output file.
-clipsrc :Clips the input data to a bounding box.
-unsetFid :Removes the FID from output features.
-makevalid :Repairs invalid geometries.
-progress :Shows progress information.
-preserve_fid : Preserve the original feature IDs (FIDs) from the source dataset when converting or copying data to a new format or destination.

### testing command

ogr2ogr \
 -f "PostgreSQL" \
 PG:"host=postgis user=postgres dbname=gis password=postgres" \
 "/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" \
 -nln public.network_test \
 -nlt LINESTRINGZ \
 -lco GEOMETRY_NAME=shape \
 -t_srs EPSG:2326 \
 -overwrite

### pervious command

ogr2ogr -f "PostgreSQL" PG:"dbname=3DPN host=smomms19 user=postgres password=P@ssw0rd" "C:\Users\ehmseto_01\Desktop\work2\testing\2026\1\20260122\import network\KLN_144_Cheung Sha Wan Sports Centre\SHP\3D indoor network.shp" -nln public.indoor_network_test -lco GEOMETRY_NAME=shape -t_srs EPSG:2326 -makevalid -overwrite

### check shapefile data

ogrinfo "/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" -al -so

This will display:

- Geometry type
- Feature count
- Extent
- SRID
- All attribute fields
- Field types

### append and replace command

ogr2ogr \
 -f "PostgreSQL" \
 PG:"host=postgis user=postgres dbname=gis password=postgres" \
 "/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" \
 -nln public.network_test \
 -nlt LINESTRINGZ \
 -lco GEOMETRY_NAME=shape \
 -upsert \
 -unsetFid

### debug commnad

ogr2ogr --debug ON \
 -f "PostgreSQL" \
 PG:"host=postgis user=postgres dbname=gis password=postgres" \
 "/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" \
 -nln public.network_test \
 -upsert \
 -unsetFid

ogr2ogr --debug ON\
 -f "PostgreSQL" \
 PG:"host=postgis user=postgres dbname=gis password=postgres" \
 "/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" \
 -nln public.network_test \
 -upsert

### update shapefile

ogr2ogr \
-f "PostgreSQL" \
PG:"host=postgis user=postgres dbname=gis password=postgres" \
"/data/indoor/MeiFooStation/SHP/3D Indoor Network.shp" \
-nln public.network_test \
-overwrite

ogr2ogr \
-f "PostgreSQL" \
PG:"host=postgis user=postgres dbname=gis password=postgres" \
"/data/indoor/Cheung Sha Wan Sports Centre/SHP/3D Indoor Network.shp" \
-nln public.network_test \
-nlt LINESTRINGZ \
-lco GEOMETRY_NAME=shape \
-upsert
