import os
from typing import List
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.network_services import (
    process_network_import,
    process_network_import_from_folder_path,
    process_network_import_from_zip,
)

router = APIRouter()


class ImportFromPathRequest(BaseModel):
    """Request body for import-network-from-path. folder_path is relative to the server's import base (e.g. /data in Docker)."""
    folder_path: str = Field(..., description="Path to folder containing '3D Indoor Network.shp', relative to import base (e.g. wing/HK_1_Hong Kong City Hall/SHP). Use forward slashes; backslashes from Windows are accepted.")
    displayname: str = Field(..., description="Display name for the building/venue (e.g. HK_1_Hong Kong City Hall). Must match IMDF data.")


from app.services.imdf_service import import_all_venues_to_postgis

@router.post("/import-venues")
async def trigger_import_venues():
    """
    Triggers the migration of all Venue data from MongoDB to PostGIS 'venue' table.
    """
    return await import_all_venues_to_postgis()

@router.post("/import-network-upload/")
async def import_network_upload(
    files: List[UploadFile] = File(..., description="List of ZIP files. Each ZIP must contain '3D Indoor Network.shp' (or case-insensitive equivalent). Display name is derived from zip filename."),
):
    """
    Import network from multiple uploaded ZIP files.
    - **files**: List of ZIP archives.
    - **DisplayName**: Derived from the filename (e.g., 'HK_1_City Hall.zip' -> 'HK_1_City Hall').
    - **Processing**: Sequential to ensure database staging table integrity.
    """
    results = []
    
    for file in files:
        # 1. Basic validation
        if not file.filename or not file.filename.lower().endswith(".zip"):
            results.append({
                "filename": file.filename,
                "status": "error", 
                "message": "File must be a ZIP archive (.zip)"
            })
            continue

        # 2. Derive Display Name
        displayname = os.path.splitext(os.path.basename(file.filename))[0]

        try:
            # 3. Read and Process
            content = await file.read()
            result = await process_network_import_from_zip(displayname, content)
            
            # 4. Format Result
            results.append({
                "filename": file.filename,
                "displayname": displayname,
                **result
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "displayname": displayname,
                "status": "error",
                "message": str(e)
            })
            
    return results


@router.post("/import-network-from-path/")
async def import_network_from_path(body: ImportFromPathRequest):
    """
    Import network from a folder path. The folder must contain '3D Indoor Network.shp'.
    On Docker, the host folder (e.g. Windows PC) should be mounted under the container's import base
    (default /data). Pass the path relative to that base, e.g. wing/HK_1_Hong Kong City Hall/SHP.
    Performs the same validation and processing as POST /import-network/.
    """
    result = await process_network_import_from_folder_path(body.displayname, body.folder_path)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/import-network/")
async def import_network():
    displayName = "KLN_256_Ho Man Tin Sports Centre"
    file = "/data/wing/KLN_256_Ho Man Tin Sports Centre/SHP/"
    result = await process_network_import( displayName,file)
    return result

# @router.post("/import-network/")
# # async def import_network(file: UploadFile = File(...)):
# async def import_network():
#     job_id = str(uuid.uuid4())
#     # upload_path = f"/tmp/{job_id}.zip"
#     # # 1. Save file
#     # with open(upload_path, "wb") as f:
#     #     f.write(await file.read())

#     # # 2. Unzip
#     # unzip_dir = f"/tmp/{job_id}/"
#     # os.system(f"unzip {upload_path} -d {unzip_dir}")
    
#     unzip_dir = "/data/indoor/Sha Tin Station/SHP"

#     # Check if the file exists
#     if not os.path.exists(f"{unzip_dir}/3D Indoor Network.shp"):
#         return {"status": "error", "message": "Input file not found"}

#     # 3. Run ogr2ogr (single line so shell runs one command; order: dst then src)
#     dst = 'PG:"host=postgis user=postgres dbname=gis password=postgres"'
#     src = f'"{unzip_dir}/3D Indoor Network.shp"'
#     cmd = (
#         f"ogr2ogr -f PostgreSQL {dst} {src}"
#         f" -nln public.network_staging -nlt LINESTRINGZ"
#         f" -lco GEOMETRY_NAME=shape -t_srs EPSG:2326 -overwrite"
#     )

#     try:

#         subprocess.run(cmd, shell=True, check=True)
#         return {"status": "success"}
#     except subprocess.CalledProcessError as e:
#         return {"status": "error", "message": str(e)}


