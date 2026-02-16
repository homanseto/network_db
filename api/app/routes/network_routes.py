from typing import Optional, List
import os
import shutil
import tempfile
import zipfile
import io
from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from app.services.network_services import (
    export_indoor_network_by_displayname,
    import_network_from_mongo_to_test
)
from app.services.imdf_service import get_network_from_mongodb
from app.core.logger import logger

router = APIRouter()


@router.get("/export-indoor-network/")
def export_indoor_network(
    displayname: str = "KLN_256_Ho Man Tin Sports Centre",
    output_dir: Optional[str] = None,
    export_type: Optional[str] = "pedestrian", # "indoor", "pedestrian"
    export_format: str = "geojson", # "shapefile" or "geojson"
):
    """
    Export indoor_network rows for the given displayname to a shapefile or GeoJSON.
    - **export_type**: "indoor" or "pedestrian". If None (default), full data is exported.
    - **export_format**: "shapefile" (default) or "geojson".
    - **output_dir**: Optional override for export path.
    """
    logger.info(f"EXPORT REQUEST: '{displayname}' Type={export_type} Format={export_format}")
    result = export_indoor_network_by_displayname(displayname, output_dir, export_type, export_format)
    
    if result.get("status") == "error":
        logger.error(f"EXPORT FAILED: {result.get('message')}")
    else:
        logger.info(f"EXPORT SUCCESS: {result.get('path')}")
        
    return result

@router.get("/download-indoor-network-zip/")
def download_indoor_network_zip(
    displayname: str,
    type: str = "all",      # "pedestrian", "indoor", "all"
    opendata: str = "full"  # "open", "full"
):
    """
    Download a zipped file containing a ShapeFile and a GeoJSON folder for the given displayname.
    - **type**: "pedestrian", "indoor", or "all".
    - **opendata**: "open" (restricted='N' only) or "full".
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Define 3 sub-paths
        shp_dir_name = "SHP"
        geojson_dir_name = "GeoJSON"
        
        shp_full_path = os.path.join(temp_dir, shp_dir_name)
        geojson_full_path = os.path.join(temp_dir, geojson_dir_name)
        
        # 1. Export Shapefile
        # Note: export_indoor_network_by_displayname creates the output_dir if not exists.
        res_shp = export_indoor_network_by_displayname(
            displayname=displayname, 
            output_dir=shp_full_path, 
            export_type=type, 
            export_format="shapefile", 
            opendata=opendata
        )
        if res_shp.get("status") == "error":
            return res_shp

        # 2. Export GeoJSON
        res_geo = export_indoor_network_by_displayname(
            displayname=displayname, 
            output_dir=geojson_full_path, 
            export_type=type, 
            export_format="geojson", 
            opendata=opendata
        )
        if res_geo.get("status") == "error":
            return res_geo

        # 3. Zip the results into memory
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Add ShapeFiles
            for root, dirs, files in os.walk(shp_full_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Archive name should be relative to keep structure "Shapefile/..."
                    # shp_full_path is .../temp/ShapeFile
                    # We want zip to have ShapeFile/myfile.shp
                    arcname = os.path.join(shp_dir_name, file) 
                    zf.write(file_path, arcname=arcname)
            
            # Add GeoJSON files
            for root, dirs, files in os.walk(geojson_full_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(geojson_dir_name, file)
                    zf.write(file_path, arcname=arcname)

        mem_zip.seek(0)
        
        filename = f"{displayname}_{type}_{opendata}.zip"
        # Sanitize filename
        filename = filename.replace(" ", "_").replace(":", "").replace("/", "_")
        
        return StreamingResponse(
            mem_zip, 
            media_type="application/zip", 
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/mongo/search")
async def search_network_mongo(displaynames: List[str] = Body(...)):
    """
    Import 3DIndoorNetwork from MongoDB to PostgreSQL 'indoor_network_test' for the given display names.
    Expects a JSON array of strings in the request body.
    """
    if not displaynames:
        return {"status": "error", "message": "display_names list is empty"}

    logger.info(f"Starting import for {len(displaynames)} display names.")
    results = []
    
    try:
        for name in displaynames:
            res = await import_network_from_mongo_to_test(name)
            results.append({
                "display_name": name,
                "result": res
            })
            
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        logger.error(f"Import process failed: {e}")
        return {"status": "error", "message": str(e)}
