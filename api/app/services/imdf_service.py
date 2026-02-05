# app/services/imdf_service.py

from app.core.mongodb import mongo_db
from app.services.mongo_service import find_one_by_display_name, find_records_by_display_name

async def get_all_units(limit: int = 100):
    cursor = mongo_db.IMDFUnit.find().limit(limit)
    results = []
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        results.append(doc)
    
    return results

async def get_venue_by_displayName(displayName: str):
    return await find_one_by_display_name("IMDFVenue", displayName)

async def get_building_by_displayName(displayName: str):
    return await find_one_by_display_name("IMDFBuilding", displayName)

async def get_unit_by_displayName(displayName: str):
    return await find_one_by_display_name("IMDFUnit", displayName)

async def get_3d_units_by_displayName(displayName: str):
    return await find_one_by_display_name("3DUnits", displayName)

async def get_level_by_displayName(displayName: str):
    return await find_one_by_display_name("IMDFLevel", displayName)

async def get_3d_floors_by_displayName(displayName: str):
    return await find_one_by_display_name("3DFloors", displayName)

async def get_opening_by_displayName(displayName: str):
    return await find_one_by_display_name("IMDFOpening", displayName)

async def get_3d_gates_by_displayName(displayName: str):
    return await find_one_by_display_name("3DGates", displayName)

async def get_buildinginfo_by_displayName(displayName: str):
    return await find_records_by_display_name("BuildingInfo", displayName)

async def get_buildinginfo_by_buildingCSUID(buildingCSUID: str):
    collection = mongo_db["BuildingInfo"]
    doc = await collection.find_one({"buildingCSUID": buildingCSUID})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def get_openings_with_name_by_displayName(displayName: str):
    """
    Fetch opening FeatureCollection by displayName, then return only features
    where feature.properties.name is not null, as an array of features.
    """
    doc = await find_one_by_display_name("IMDFOpening", displayName)
    if not doc or "features" not in doc:
        return []

    features = doc["features"]
    if not isinstance(features, list):
        return []

    return [
        f
        for f in features
        if isinstance(f.get("properties"), dict)
        and f["properties"].get("name") is not None
    ]


def flpolyid_slices(flpolyid: str):
    if not flpolyid or len(flpolyid) < 26:
        return None, None
    buildingCSUID = flpolyid[1:20]   # JS slice(1, 20)
    floorNumber = flpolyid[22:26]    # JS slice(22, 26)
    return buildingCSUID, floorNumber

async def enrich_staging_row(row: dict) -> dict | None:

    d = row.get("flpolyid") or row.get("flpoly_id")  # use actual column name
    if not d:
        return None
    buildingCSUID, floorNumber = flpolyid_slices(d)
    if buildingCSUID is None:
        return None

    buildingCSUIDInfo = await get_buildinginfo_by_buildingCSUID(buildingCSUID)
    sixDigitID = buildingCSUIDInfo.get("SixDigitID")
    floorId = f"{sixDigitID}{floorNumber}"
    if not buildingCSUIDInfo:
        # same as "continue" in your TS
        return None

    return {
        "buildingCSUID": buildingCSUID,
        "floorNumber": floorNumber,
        "floorId": floorId,
        "buildingCSUIDInfo": buildingCSUIDInfo,
    }