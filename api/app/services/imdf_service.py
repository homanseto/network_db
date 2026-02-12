# app/services/imdf_service.py

import json
import logging
from fastapi import HTTPException
from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.mongodb import mongo_db
from app.services.mongo_service import find_one_by_display_name, find_records_by_display_name

logger = logging.getLogger(__name__)

async def import_all_venues_to_postgis():
    """
    Fetch all IMDFVenue documents from MongoDB and insert/update them into PostGIS 'venue' table.
    Projection: MongoDB (WGS84) -> PostGIS (EPSG:2326).
    """
    try:
        venues = await get_all_venues()
        if not venues:
             return {"message": "No venues found in MongoDB to import."}

        count = 0
        engine = SessionLocal().bind

        with engine.connect() as conn:
            with conn.begin():  # Start transaction
                for doc in venues:
                    try:
                        # Document-level properties
                        region = doc.get("region")
                        display_name = doc.get("displayName")
                        
                        building_type = doc.get("buildingType")
                        
                        # Fix for potentially malformed buildingType (e.g. "", None, or single string)
                        if building_type is None or building_type == "":
                            building_type = []
                        elif not isinstance(building_type, list):
                            # If it's a single value (string/int), wrap it in a list
                            building_type = [str(building_type)]

                        # Iterate through features
                        features_data = doc.get("features", [])
                        
                        # Check if features_data is list
                        if not isinstance(features_data, list):
                            continue

                        for feature in features_data:
                            # Only process features with type 'venue' or feature_type 'venue'
                            ft = feature.get("feature_type")
                            if ft != "venue":
                                continue

                            fid = feature.get("id")
                            if not fid:
                                continue # Skip without ID

                            props = feature.get("properties", {})
                            geometry = feature.get("geometry")
                            
                            if not geometry:
                                continue # Skip without geometry

                            # Extract properties
                            category = props.get("category")
                            restriction = props.get("restriction")
                            
                            # Name (handle object or string)
                            name_field = props.get("name")
                            name_en = None
                            name_zh = None

                            if isinstance(name_field, dict):
                                name_en = name_field.get("en")
                                name_zh = name_field.get("zh")
                            elif isinstance(name_field, str): 
                                name_en = name_field # Fallback
                            
                            alt_name_field = props.get("alt_name")
                            alt_name = None
                            if isinstance(alt_name_field, dict):
                                alt_name = json.dumps(alt_name_field, ensure_ascii=False)
                            elif isinstance(alt_name_field, str):
                                alt_name = alt_name_field

                            hours = props.get("hours")
                            website = props.get("website")
                            phone = props.get("phone")
                            address_id = props.get("address_id")
                            organization_id = props.get("OrganizationID")
                            
                            display_point_geo = props.get("display_point") # GeoJSON Point

                            # Prepare Geometry JSON strings
                            shape_json = json.dumps(geometry)
                            dp_json = json.dumps(display_point_geo) if display_point_geo else None

                            # SQL Query
                            sql = text("""
                                INSERT INTO venue (
                                    id, category, restriction, name_en, name_zh,
                                    alt_name, hours, website, phone, address_id, organization_id,
                                    building_type, region, displayname,
                                    shape, display_point, created_at, updated_at
                                ) VALUES (
                                    :fid, :category, :restriction, :name_en, :name_zh,
                                    :alt_name, :hours, :website, :phone, :address_id, :organization_id,
                                    :building_type, :region, :displayname,
                                    ST_Transform(ST_GeomFromGeoJSON(:shape_json), 2326),
                                    CASE 
                                        WHEN :dp_json IS NOT NULL THEN ST_Transform(ST_GeomFromGeoJSON(:dp_json), 2326)
                                        ELSE NULL
                                    END,
                                    (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
                                    (NOW() AT TIME ZONE 'Asia/Hong_Kong')
                                )
                                ON CONFLICT (id) DO UPDATE SET
                                    category = EXCLUDED.category,
                                    restriction = EXCLUDED.restriction,
                                    name_en = EXCLUDED.name_en,
                                    name_zh = EXCLUDED.name_zh,
                                    alt_name = EXCLUDED.alt_name,
                                    hours = EXCLUDED.hours,
                                    website = EXCLUDED.website,
                                    phone = EXCLUDED.phone,
                                    address_id = EXCLUDED.address_id,
                                    organization_id = EXCLUDED.organization_id,
                                    building_type = EXCLUDED.building_type,
                                    region = EXCLUDED.region,
                                    displayname = EXCLUDED.displayname,
                                    shape = EXCLUDED.shape,
                                    display_point = EXCLUDED.display_point,
                                    updated_at = (NOW() AT TIME ZONE 'Asia/Hong_Kong');
                            """)
                            
                            # Convert dict/list params to json if needed for SQL array types
                            # building_type is TEXT[] in postgres, SQLAlchemy should handle list fine or cast
                            
                            params = {
                                "fid": fid,
                                "category": category,
                                "restriction": restriction,
                                "name_en": name_en,
                                "name_zh": name_zh,
                                "alt_name": alt_name,
                                "hours": hours,
                                "website": website,
                                "phone": phone,
                                "address_id": address_id,
                                "organization_id": organization_id,
                                "building_type": building_type, # passing list
                                "region": region,
                                "displayname": display_name,
                                "shape_json": shape_json,
                                "dp_json": dp_json
                            }

                            conn.execute(sql, params)
                            count += 1
                    except Exception as e:
                        logger.error(f"Error processing venue document {doc.get('_id')}: {str(e)}")
                        # Continue to next document or raise? 
                        # Raising here checks if transaction rolls back. 
                        # Since we are in conn.begin(), raising will rollback this batch.
                        raise e 
        
        return {"message": f"Successfully imported {count} venues to PostGIS"}

    except Exception as e:
        logger.error(f"Failed to import venues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")



async def get_all_units(limit: int = 100):
    cursor = mongo_db.IMDFUnit.find().limit(limit)
    results = []
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
        results.append(doc)
    
    return results

async def get_all_venues():
    cursor = mongo_db.IMDFVenue.find()
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

