from typing import Optional

from fastapi import APIRouter
from app.services.network_services import export_indoor_network_by_displayname

router = APIRouter()


@router.get("/export-indoor-network/")
def export_indoor_network(
    displayname: str = "KLN_256_Ho Man Tin Sports Centre",
    output_dir: Optional[str] = None,
    export_type: Optional[str] = "pedestrian", # "indoor", "pedestrian"
    export_format: str = "shapefile", # "shapefile" or "geojson"
):
    """
    Export indoor_network rows for the given displayname to a shapefile or GeoJSON.
    - **export_type**: "indoor" or "pedestrian". If None (default), full data is exported.
    - **export_format**: "shapefile" (default) or "geojson".
    - **output_dir**: Optional override for export path.
    """
    result = export_indoor_network_by_displayname(displayname, output_dir, export_type, export_format)
    return result
