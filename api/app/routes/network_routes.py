from typing import Optional

from fastapi import APIRouter
from app.services.network_services import export_indoor_network_by_displayname

router = APIRouter()


@router.get("/export-indoor-network/")
def export_indoor_network(
    displayname: str = "KLN_256_Ho Man Tin Sports Centre",
    output_dir: Optional[str] = None,
):
    """
    Export indoor_network rows for the given displayname to a shapefile (via ogr2ogr).
    Default output folder: data/result. Pass output_dir to override (e.g. /data/result).
    """
    result = export_indoor_network_by_displayname(displayname, None)
    return result
