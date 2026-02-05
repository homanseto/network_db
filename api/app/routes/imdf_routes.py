from fastapi import APIRouter, HTTPException, Query
from app.services.imdf_service import get_all_units, get_unit_by_displayName, get_opening_by_displayName, get_3d_units_by_displayName,get_3d_gates_by_displayName

router = APIRouter(prefix="/imdf", tags=["IMDF"])

@router.get("/units")
async def read_units(limit: int = 100):
    return await get_all_units(limit)


@router.get("/units/by-displayname")
async def read_unit(displayname: str = Query(None)):
    if displayname is None:
        raise HTTPException(status_code=400, detail="Display name is required")

    units = await get_unit_by_displayName(displayname)

    if not units:
        raise HTTPException(status_code=404, detail="Unit not found")

    return units

@router.get("/openings/by-displayname")
async def read_unit(displayname: str = Query(None)):
    if displayname is None:
        raise HTTPException(status_code=400, detail="Display name is required")

    openings = await get_opening_by_displayName(displayname)

    if not openings:
        raise HTTPException(status_code=404, detail="Unit not found")

    return openings

@router.get("/3d-units/by-displayname")
async def read_unit(displayname: str = Query(None)):
    if displayname is None:
        raise HTTPException(status_code=400, detail="Display name is required")

    units = await get_3d_units_by_displayName(displayname)

    if not units:
        raise HTTPException(status_code=404, detail="3D Unit not found")

    return units

@router.get("/3d-gates/by-displayname")
async def read_unit(displayname: str = Query(None)):
    if displayname is None:
        raise HTTPException(status_code=400, detail="Display name is required")

    gates = await get_3d_gates_by_displayName(displayname)

    if not gates:
        raise HTTPException(status_code=404, detail="3D Unit not found")

    return gates
