from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.pedestrian_service import import_pedestrian_from_fgdb
from app.core.logger import logger

router = APIRouter()

class ImportFGDBRequest(BaseModel):
    fgdb_path: str

@router.post("/import-pedestrian-fgdb/")
async def import_pedestrian_route():
    """
    Imports 'PedestrianRoute' from FGDB. 
    Performs an UPSERT: Updates existing IDs (logging history) and Inserts new IDs.
    """
    pedestrina_path = "/data/pedestrian/3DPN_20260130/3DPN_P2.gdb/"
    logger.info(f"IMPORT REQUEST: FGDB at {pedestrina_path}")
    result = await import_pedestrian_from_fgdb(pedestrina_path)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
        
    return result