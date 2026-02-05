from fastapi import UploadFile, File, APIRouter
from app.services.network_services import process_network_import

router = APIRouter()

@router.post("/import-network/")
async def import_network():
    displayName = "HK_6_Hong Kong Central Library"
    file = "/data/wing/HK_6_Hong Kong Central Library/"
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


