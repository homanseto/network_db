import os
import re
import shutil
import tempfile
import uuid
import zipfile
import subprocess
import traceback
from sqlalchemy import text
from app.core.database import SessionLocal
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
from app.services.utils import (calculate_feature_type,calculate_gradient)
from app.services.pedestrian_service import (
    sync_pedrouterelfloorpoly_from_imdf,
    calculate_wheelchair_access,
    get_alias_name,
    insert_network_rows_into_indoor_network,
)
from app.schema.network import NetworkStagingRow


# Project root: api/app/services -> up 3 levels -> network-db
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Export result folder: use EXPORT_RESULT_DIR env (e.g. /data/result in Docker) or project's data/result
DEFAULT_EXPORT_RESULT_DIR = os.environ.get(
    "EXPORT_RESULT_DIR",
    os.path.join(_PROJECT_ROOT, "data", "result"),
)
PG_CONNECTION = "PG:host=postgis user=postgres dbname=gis password=postgres"
# Base path for user-provided folder paths (e.g. /data when Docker mounts host ./data here)
IMPORT_BASE_PATH = os.path.normpath(os.environ.get("IMPORT_BASE_PATH", "/data"))


def _resolve_import_folder_path(folder_path: str) -> tuple[str, str | None]:
    """
    Resolve user-provided folder path (e.g. from Windows PC) to a path inside IMPORT_BASE_PATH.
    Returns (resolved_abs_path, error_message). error_message is None if valid.
    """
    if not folder_path or not folder_path.strip():
        return "", "folder_path is required and cannot be empty"
    # Normalize: Windows backslashes -> forward slashes, strip leading/trailing slashes
    normalized = folder_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        return "", "folder_path is required and cannot be empty"
    # Prevent path traversal: no ".." in segments
    if ".." in normalized.split("/"):
        return "", "folder_path must not contain '..'"
    base_abs = os.path.abspath(IMPORT_BASE_PATH)
    full = os.path.abspath(os.path.join(base_abs, normalized))
    if not full.startswith(base_abs):
        return full, "folder_path must be inside the allowed import base path"
    return full, None


async def process_network_import_from_folder_path(display_name: str, folder_path: str) -> dict:
    """
    Run the same import as process_network_import using a user-provided folder path.
    folder_path is relative to IMPORT_BASE_PATH (e.g. 'wing/HK_1_Hong Kong City Hall/SHP').
    On Docker with ./data mounted at /data, this resolves to /data/wing/.../SHP.
    """
    resolved, err = _resolve_import_folder_path(folder_path)
    if err is not None:
        return {"status": "error", "message": err}
    return await process_network_import(display_name, resolved)


# Expected shapefile name for indoor network (must exist inside uploaded ZIP or folder)
INDOOR_NETWORK_SHP_NAME = "3D Indoor Network.shp"


def _find_folder_containing_shp(extract_dir: str, shp_name: str = INDOOR_NETWORK_SHP_NAME) -> str | None:
    """Return the path to the directory that contains shp_name (case-insensitive), or None if not found."""
    target_name = shp_name.lower()
    for root, _dirs, files in os.walk(extract_dir):
        for f in files:
            if f.lower() == target_name:
                return root
    return None


async def process_network_import_from_zip(display_name: str, zip_file_content: bytes) -> dict:
    """
    Save ZIP to a temp dir, extract it, find the folder containing '3D Indoor Network.shp',
    run process_network_import(display_name, that_folder), then clean up. Accepts ZIP format only.
    """
    if not zip_file_content or len(zip_file_content) == 0:
        return {"status": "error", "message": "Uploaded file is empty"}
    tmp_dir = tempfile.mkdtemp(prefix="network_import_")
    try:
        zip_path = os.path.join(tmp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_file_content)
        if not zipfile.is_zipfile(zip_path):
            return {"status": "error", "message": "File is not a valid ZIP archive. Please upload a ZIP file."}
        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        folder = _find_folder_containing_shp(extract_dir)
        if folder is None:
            return {
                "status": "error",
                "message": f"ZIP must contain a folder with '{INDOOR_NETWORK_SHP_NAME}' or '3D indoor network.shp'. No such file found in the archive.",
            }
        return await process_network_import(display_name, folder)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def process_network_import(displayName:str, filePath:str):

    job_id = str(uuid.uuid4())

    shp_path = os.path.join(filePath, INDOOR_NETWORK_SHP_NAME)

    # Check for exact match first; if not found, look for case-insensitive match
    if not os.path.exists(shp_path):
        found_path = None
        if os.path.exists(filePath) and os.path.isdir(filePath):
            target_lower = INDOOR_NETWORK_SHP_NAME.lower()
            for fname in os.listdir(filePath):
                if fname.lower() == target_lower:
                    found_path = os.path.join(filePath, fname)
                    break
        
        if found_path:
            shp_path = found_path
        else:
            return {"status": "error", "message": f"Shapefile '{INDOOR_NETWORK_SHP_NAME}' (or case variant) not found in {filePath}"}

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
        # Capture output to help debug ogr2ogr issues
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # Return stderr in the message
        return {"status": "error", "message": f"Ogr2ogr failed: {e.stderr}"}

    # 🔽 Now database validation + merge
    with SessionLocal() as session:
        try:
            # Execute function calling scalar() to retrieve the JSON object directly
            validation_output = session.execute(
                text("SELECT validate_network_staging();")
            ).scalar()

            # The function returns a JSON object (dict in Python), e.g. {"valid": true, "error_count": 0}
            is_valid = False
            if isinstance(validation_output, dict):
                is_valid = validation_output.get("valid", False)
            elif validation_output is None:
                 is_valid = False
            else:
                 # In case it returns a Mapping/Row proxy or other type, try attribute access or generic get
                 is_valid = getattr(validation_output, "valid", False)

            if not is_valid:
                errors = session.execute(
                    text("SELECT * FROM network_staging_errors;")
                ).mappings().all()

                # If validation failed, we return early. 
                # Note: network_staging data is RETAINED here to allow debugging the data in the DB.
                # If you prefer to clear it, you would need to truncate here.
                return {
                    "status": "validation_failed",
                    "errors": errors
                }
            
            # Select all columns + explicitly convert shape to WKB Hex for validation
            # We use ST_AsBinary -> encode hex to match Pydantic expectation of 'shape' string
            staging_result = session.execute(text("SELECT *, ST_AsGeoJSON(shape) AS geojson FROM network_staging"))
            
            staging_rows = []
            for r in staging_result.mappings().all():
                # Convert RowMapping to dict
                row_dict = dict(r)
                
                # 2. Key Step: specific handling for 'crtby' default behavior
                # If crtby is None (NULL in DB), remove it so Pydantic uses the default "03".
                if row_dict.get("crtby") is None:
                    row_dict.pop("crtby", None)
                if row_dict.get("lstamdby") is None:
                    row_dict.pop("lstamdby", None)

                staging_rows.append(row_dict)

            rows_result = []
            for i, r in enumerate(staging_rows):
                try:
                    rows_result.append(NetworkStagingRow.model_validate(r))
                except Exception as e:
                    # Provide helpful context: which row failed and why
                    return {
                        "status": "error",
                        "message": f"Pydantic Validation failed at row index {i} (ID: {r.get('inetworkid')}). Error: {str(e)}",
                        "row_data": r
                    }

            session.execute(text("TRUNCATE TABLE network_staging"))
            
            # Update only property fields; geometry (shape/geojson) from staging must not be changed.
            # update_pedestrian_fields might fail if external services are down or logic errors exist.
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
            # Print traceback to server logs for debugging
            traceback.print_exc()
            
            # Return full error details
            return {
                "status": "error", 
                "message": f"Processing failed: {str(e)}", 
                "traceback": traceback.format_exc()
            }

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
        if row.pedrouteid is not None:
            row.pedrouteid = int(row.pedrouteid)
        row.displayname = displayName
        row.feattype = calculate_feature_type(row, unit_features, unit3d_features)
        flpolyid = row.flpolyid
        buildingCSUID, floorNumber = flpolyid_slices(flpolyid)
        buildingCSUIDInfo = next((doc for doc in buildingInfo if doc['buildingCSUID'] == buildingCSUID), None)
        sixDigitID = buildingCSUIDInfo.get("SixDigitID")
        floorId = f"{sixDigitID}{floorNumber}"
        row.bldgid_1 = buildingCSUIDInfo.get("BuildingID")
        row.buildnamen = buildingCSUIDInfo.get("Name_EN")
        row.buildnamzh = buildingCSUIDInfo.get("Name_CH")
        matched_level_feature = next((f for f in level_features if f.get("id") == row.level_id), None)
        row.leveleng = matched_level_feature.get("properties", {}).get("name",{}).get("en","")
        row.levelzh = matched_level_feature.get("properties",{}).get("name",{}).get("zh","")
        row.floorid = floorId
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
        # if not mtr 
        row.location = 2
        # calculate gradient for walkways if elevation data is present (e.g. escalators)
        row.gradient = calculate_gradient(row.highway, row.geojson)
    return rows


def _sanitize_displayname_for_filename(displayname: str) -> str:
    """Replace characters unsafe for filenames with underscore."""
    if not displayname:
        return "indoor_network"
    return re.sub(r'[^\w\-.]', "_", displayname).strip("_") or "indoor_network"



def export_indoor_network_by_displayname(
    displayname: str,
    output_dir: str | None = None,
    export_type: str | None = None,  # "indoor", "pedestrian", or None (all)
    export_format: str = "shapefile",  # "shapefile" or "geojson"
) -> dict:
    """
    Get data from indoor_network table by displayname, write to output_dir (default data/result),
    and convert to shapefile using ogr2ogr with field remapping based on export_type.
    """
    import json
    
    out_dir = output_dir or DEFAULT_EXPORT_RESULT_DIR
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    safe_name = _sanitize_displayname_for_filename(displayname)
    
    # Load mapping table
    # Use relative path from this file to ensure it works in both Docker and local dev
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mapping_path = os.path.join(os.path.dirname(current_dir), "reference", "pedestrian_convert_table.json")

    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load field mapping: {str(e)}", "path": None}

    # Build SQL select based on export_type
    select_fields = []
    
    # Fields that should be cast to TEXT to preserve NULLs or handle large integers in Shapefiles
    force_text_fields = ["bldgid_2", "siteid", "terminalid", "acstimeid", "bldgid_1", "floorid"]

    for field in mapping:
        db_col = field.get("database")
        output_cats = field.get("output", [])
        
        # If export_type is None, include all fields
        # If export_type is specified, only include fields tagged with that type
        if export_type is None or export_type in output_cats:
            target_name = field.get("shapefile") if export_format == "shapefile" else field.get("geojson")
            if db_col and target_name:
                # Cast IDs to text for Shapefiles to prevent 0 instead of NULL and handle potential large ID overflows
                if export_format == "shapefile" and db_col in force_text_fields:
                    select_fields.append(f'CAST("{db_col}" AS TEXT) AS "{target_name}"')
                else:
                    select_fields.append(f'"{db_col}" AS "{target_name}"')

    if not select_fields:
        return {"status": "error", "message": "No fields selected for export", "path": None}
    
    sql_select = ", ".join(select_fields)
    displayname_escaped = (displayname or "").replace("'", "''")
    sql_query = f"SELECT {sql_select} FROM indoor_network WHERE displayname='{displayname_escaped}'"

    # Define output file extension and creation options
    if export_format.lower() == "geojson":
        ext = ".geojson"
        driver = "GeoJSON"
        lco_opts = [] # GeoJSON typically doesn't need encoding options like shapefile
    else:
        ext = ".shp"
        driver = "ESRI Shapefile"
        lco_opts = ["-lco", "ENCODING=UTF-8"]

    output_filename = f"{safe_name}_{export_type or 'all'}_network{ext}"
    output_path = os.path.join(out_dir, output_filename)

    cmd = [
        "ogr2ogr",
        "-f", driver,
        "-overwrite",
        output_path,
        PG_CONNECTION,
        "-sql", sql_query
    ] + lco_opts
    
    # Ensure environment variables are set for UTF-8 handling
    env = os.environ.copy()
    env["PGCLIENTENCODING"] = "UTF8"
    env["SHAPE_ENCODING"] = "UTF-8" # Helps some GDAL versions

    try:
        subprocess.run(cmd, check=True, env=env)
        
        # Create a .cpg file to explicitly tell ArcGIS/QGIS the encoding is UTF-8 (only for Shapefiles)
        if driver == "ESRI Shapefile":
            cpg_path = os.path.splitext(output_path)[0] + ".cpg"
            with open(cpg_path, "w", encoding="utf-8") as f:
                f.write("UTF-8")
            
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": str(e), "path": None}
    except Exception as e:
        return {"status": "error", "message": f"Export failed: {str(e)}", "path": None}
        
    return {
        "status": "success",
        "path": output_path,
        "displayname": displayname,
        "output_dir": out_dir,
    }