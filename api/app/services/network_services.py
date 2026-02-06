import os
import re
import uuid
import subprocess
from sqlalchemy import text
from app.core.database import SessionLocal

# Project root: api/app/services -> up 3 levels -> network-db
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Export result folder: use EXPORT_RESULT_DIR env (e.g. /data/result in Docker) or project's data/result
DEFAULT_EXPORT_RESULT_DIR = os.environ.get(
    "EXPORT_RESULT_DIR",
    os.path.join(_PROJECT_ROOT, "data", "result"),
)
PG_CONNECTION = "PG:host=postgis user=postgres dbname=gis password=postgres"
from app.services.imdf_service import (
    flpolyid_slices,
    get_opening_by_displayName,
    get_openings_with_name_by_displayName,
    get_unit_by_displayName,
    get_3d_units_by_displayName,
    get_buildinginfo_by_buildingCSUID,
    get_buildinginfo_by_displayName,
    get_level_by_displayName
)
from app.services.utils import calculate_feature_type
from app.services.pedestrian_service import (
    sync_pedrouterelfloorpoly_from_imdf,
    calculate_wheelchair_access,
    get_alias_name,
    insert_network_rows_into_indoor_network,
)
from app.schema.network import NetworkStagingRow

async def process_network_import(displayName:str, filePath:str):

    job_id = str(uuid.uuid4())

    shp_path = os.path.join(filePath, "3D Indoor Network.shp")

    if not os.path.exists(shp_path):
        return {"status": "error", "message": "Shapefile not found"}

    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        'PG:host=postgis user=postgres dbname=gis password=postgres',
        shp_path,
        "-nln", "public.network_staging",
        "-nlt", "LINESTRINGZ",
        "-lco", "GEOMETRY_NAME=shape",
        "-t_srs", "EPSG:2326",
        "-overwrite"
    ]

    try:
        # subprocess.run(cmd, shell=True, check=True)
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": str(e)}

    # 🔽 Now database validation + merge
    with SessionLocal() as session:
        try:
            validation = session.execute(
                text("SELECT validate_network_staging();")
            ).scalar()
# Check if validation is valid
            if not validation["valid"]:
                errors = session.execute(
                    text("SELECT * FROM network_staging_errors;")
                ).mappings().all()

                return {
                    "status": "validation_failed",
                    "errors": errors
                }
            staging_result = session.execute(text("SELECT inetworkid,ST_AsGeoJSON(shape) AS geojson, highway, oneway, emergency, wheelchair,flpolyid,crtdt, crtby, lstamddt, lstamdby, restricted, shape FROM network_staging"))
            staging_rows = [
                    dict(zip(staging_result.keys(), r))
                     for r in staging_result.fetchall()
                     ]
            # rows_result = [NetworkStagingRow.model_validate(r) for r in staging_rows]
            
            rows_result = []
            for i, r in enumerate(staging_rows):
                try:
                    rows_result.append(NetworkStagingRow.model_validate(r))
                except Exception as e:
                    # Provide helpful context: which row failed and why
                    return {
                        "status": "error",
                        "message": f"Validation failed at row index {i} (ID: {r.get('inetworkid')}). Error: {str(e)}",
                        "row_data": r  # optionally return the bad data so you can see what failed
                    }

            session.execute(text("TRUNCATE TABLE network_staging"))
            # Update only property fields; geometry (shape/geojson) from staging must not be changed.
            await update_pedestrian_fields(displayName, rows_result)
            indoor_upserted = insert_network_rows_into_indoor_network(session, displayName, rows_result)
            session.commit()
            updatepedrouteresult = await sync_pedrouterelfloorpoly_from_imdf(displayName)
            return {
                "status": "success",
                "staging_count": len(rows_result),
                "indoor_network_upserted": indoor_upserted,
                "rows": [r.model_dump() for r in rows_result],
            }

        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e)}

async def update_pedestrian_fields(displayName: str, rows: list[NetworkStagingRow]) -> list[NetworkStagingRow]:
    """
    Compute all pedestrian-related fields on each row: feattype (from units) and building/floor enrichment (from flpolyid).
    Does not replace geometry. Updates rows in place and returns the same list (updated NetworkStagingRow).
    """
    unit_doc = await get_unit_by_displayName(displayName)
    unit3d_doc = await get_3d_units_by_displayName(displayName)
    unit_features = (unit_doc or {}).get("features") or []
    unit3d_features = (unit3d_doc or {}).get("features") or []
    buildingInfo = await get_buildinginfo_by_displayName(displayName)
    opening_features = await get_opening_by_displayName(displayName)
    opening_name_features = await get_openings_with_name_by_displayName(displayName)
    level_doc = await get_level_by_displayName(displayName)
    level_features = (level_doc or {}).get("features") or []
    for level_feature in level_features:
        properties = level_feature.get("properties")
        floor_poly_id = properties.get("FloorPolyID")
        level_id = level_feature.get("id")
        for row in rows:
            if row.flpolyid == floor_poly_id:
                row.level_id = level_id
    for row in rows:
        row.displayname = displayName
        row.feattype = calculate_feature_type(row, unit_features, unit3d_features)
        flpolyid = row.flpolyid
        buildingCSUID, floorNumber = flpolyid_slices(flpolyid)
        buildingCSUIDInfo = next((doc for doc in buildingInfo if doc['buildingCSUID'] == buildingCSUID), None)
        sixDigitID = buildingCSUIDInfo.get("SixDigitID")
        floorId = f"{sixDigitID}{floorNumber}"
        row.bldgid_1 = buildingCSUIDInfo.get("BuildingID")
        row.buildingnameeng = buildingCSUIDInfo.get("Name_EN")
        row.buildingnamechi = buildingCSUIDInfo.get("Name_CH")
        matched_level_feature = next((f for f in level_features if f.get("id") == row.level_id), None)
        row.levelenglishname = matched_level_feature.get("properties", {}).get("name",{}).get("en","")
        row.levelchinesename = matched_level_feature.get("properties",{}).get("name",{}).get("zh","")
        row.floorId = floorId
        row.emergency = (
            'no' if row.feattype == 10
            else 'yes'
        )
        row.direction = (
            0 if row.oneway == 'no' 
            else -1 if row.oneway == 'reverse'
            else 1
        )
        # WheelchairBarrier / wc_Access: 1 if escalator(8), stairs(12), or wheelchair no; else 2
        row.wc_barrier = (
            1
            if (
                row.feattype == 8
                or row.feattype == 12
                or (row.wheelchair == "no")
            )
            else 2
        )
        row.wc_access = calculate_wheelchair_access(row, (opening_name_features or []))
        get_alias_name(row, opening_name_features or [])
    return rows


def _sanitize_displayname_for_filename(displayname: str) -> str:
    """Replace characters unsafe for filenames with underscore."""
    if not displayname:
        return "indoor_network"
    return re.sub(r'[^\w\-.]', "_", displayname).strip("_") or "indoor_network"


def export_indoor_network_by_displayname(
    displayname: str,
    output_dir: str | None = None,
) -> dict:
    """
    Get data from indoor_network table by displayname, write to output_dir (default data/result),
    and convert to shapefile using ogr2ogr. Returns status and path to the generated .shp.
    """
    out_dir = output_dir or DEFAULT_EXPORT_RESULT_DIR
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    safe_name = _sanitize_displayname_for_filename(displayname)
    shape_path = os.path.join(out_dir, f"{safe_name}_indoor_network.shp")
    # SQL-safe: escape single quotes in displayname
    displayname_escaped = (displayname or "").replace("'", "''")
    # Export from PostGIS: indoor_network filtered by displayname
    cmd = [
        "ogr2ogr",
        "-f", "ESRI Shapefile",
        "-overwrite",
        "-lco", "ENCODING=UTF-8",  # Force UTF-8 encoding for the DBF
        shape_path,
        PG_CONNECTION,
        "indoor_network",
        "-where", f"displayname='{displayname_escaped}'",
    ]
    
    # Ensure environment variables are set for UTF-8 handling
    env = os.environ.copy()
    env["PGCLIENTENCODING"] = "UTF8"
    env["SHAPE_ENCODING"] = "UTF-8" # Helps some GDAL versions

    try:
        subprocess.run(cmd, check=True, env=env)
        
        # Create a .cpg file to explicitly tell ArcGIS/QGIS the encoding is UTF-8
        cpg_path = os.path.splitext(shape_path)[0] + ".cpg"
        with open(cpg_path, "w", encoding="utf-8") as f:
            f.write("UTF-8")
            
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": str(e), "path": None}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create CPG file: {str(e)}", "path": None}
        
    return {
        "status": "success",
        "path": shape_path,
        "displayname": displayname,
        "output_dir": out_dir,
    }