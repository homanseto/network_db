import json
from typing import TYPE_CHECKING

from sqlalchemy import text
from shapely.geometry import shape

from app.core.database import SessionLocal

if TYPE_CHECKING:
    from app.schema.network import NetworkStagingRow
from app.services.imdf_service import get_buildinginfo_by_displayName, get_level_by_displayName, flpolyid_slices, get_buildinginfo_by_buildingCSUID
from app.services.utils import _line_from_geojson, _transform_2326_to_4326, _force_2d

# nf = EPSG:2326, opening features = EPSG:4326. 0.1 m buffer (ref: turf.buffer(..., 0.1/1000, { units: "kilometers" })); in 4326 use ~0.1/111320 deg
BUFFER_DEGREES_0_1M = 0.1 / 111_320

# facilityMap from reference.ts: feattype code -> English and Chinese names
FACILITY_MAP: dict[int, dict[str, str]] = {
    8: {"name_en": "Escalator", "name_zh": "扶手電梯"},
    9: {"name_en": "Travelator", "name_zh": "自動行人道"},
    10: {"name_en": "Lift", "name_zh": "升降機"},
    11: {"name_en": "Ramp", "name_zh": "斜道"},
    12: {"name_en": "Staircase", "name_zh": "樓梯"},
    13: {"name_en": "Stairlift", "name_zh": "輪椅升降台"},
}


def calculate_wheelchair_access(nf: "NetworkStagingRow", opening_features: list[dict]) -> int:
    """
    WheelchairAccess (wc_access): 1 if nf is a ramp (feattype 11) and nf line intersects
    a 0.1m buffer of any opening on the same level; else 2.
    nf geometry is EPSG:2326; opening features are EPSG:4326 (from get_opening_by_displayName).
    """
    nf_dict = nf.model_dump() if hasattr(nf, "model_dump") else nf if hasattr(nf, "model_dump") else nf
    if (nf_dict.get("feattype") or 0) != 11:
        return 2

    level_id = nf_dict.get("level_id")
    if not level_id:
        return 2

    # Openings on same level (opening has properties.level_id in EPSG:4326)
    on_level = [
        f for f in (opening_features or [])
        if (f.get("properties") or {}).get("level_id") == level_id
    ]
    if not on_level:
        return 2

    geojson_str = nf_dict.get("geojson") or ""
    line_2326 = _line_from_geojson(geojson_str)
    if not line_2326 or line_2326.is_empty:
        return 2
    line_2326 = _force_2d(line_2326) if line_2326.has_z else line_2326
    line_4326 = _transform_2326_to_4326(line_2326)

    for opening in on_level:
        geom = opening.get("geometry")
        if not geom:
            continue
        try:
            open_line = shape(geom)
            if open_line.is_empty or open_line.geom_type != "LineString":
                continue
            if open_line.has_z:
                open_line = _force_2d(open_line)
            buffer_poly = open_line.buffer(BUFFER_DEGREES_0_1M)
            if buffer_poly.is_empty:
                continue
            if line_4326.intersects(buffer_poly):
                return 1
        except (TypeError, KeyError):
            continue
    return 2


def get_alias_name(nf: "NetworkStagingRow", opening_features: list[dict]) -> None:
    """
    Update aliasnamen and aliasnamtc on nf from reference.ts getAliasName.
    opening_features = get_openings_with_name_by_displayName (only features with name !== null).
    nf geometry EPSG:2326; opening features EPSG:4326.
    """
    nf_dict = nf.model_dump() if hasattr(nf, "model_dump") else nf
    level_id = nf_dict.get("level_id")
    feattype = nf_dict.get("feattype")
    building_eng = (nf_dict.get("buildingnameeng") or "").strip()
    building_zh = (nf_dict.get("buildingnamechi") or "").strip()
    level_eng = (nf_dict.get("levelenglishname") or "").strip()
    level_zh = (nf_dict.get("levelchinesename") or "").strip()

    facility = FACILITY_MAP.get(feattype) if isinstance(feattype, int) else None
    exits = [
        f for f in (opening_features or [])
        if (f.get("properties") or {}).get("level_id") == level_id
    ]

    geojson_str = nf_dict.get("geojson") or ""
    line_2326 = _line_from_geojson(geojson_str)
    if not line_2326 or line_2326.is_empty:
        line_4326 = None
    else:
        line_2326 = _force_2d(line_2326) if line_2326.has_z else line_2326
        line_4326 = _transform_2326_to_4326(line_2326)

    if exits and line_4326 is not None:
        match_exit = False
        for e in exits:
            geom = e.get("geometry")
            if not geom:
                continue
            try:
                open_line = shape(geom)
                if open_line.is_empty or open_line.geom_type != "LineString":
                    continue
                if open_line.has_z:
                    open_line = _force_2d(open_line)
                buffer_poly = open_line.buffer(BUFFER_DEGREES_0_1M)
                if buffer_poly.is_empty or not line_4326.intersects(buffer_poly):
                    continue
                props = e.get("properties") or {}
                name_obj = props.get("name") or {}
                exit_en = (name_obj.get("en") or "").strip()
                exit_zh = (name_obj.get("zh") or "").strip()
                if facility:
                    nf.aliasnamen = f"{building_eng} {exit_en} {facility['name_en']}".strip()
                    nf.aliasnamtc = "".join((f"{building_zh}{exit_zh}{facility['name_zh']}").split())
                else:
                    nf.aliasnamen = f"{building_eng} {exit_en}".strip()
                    nf.aliasnamtc = "".join((f"{building_zh}{exit_zh}").split())
                match_exit = True
                break
            except (TypeError, KeyError):
                continue
        if not match_exit:
            if facility:
                nf.aliasnamen = f"{building_eng} {facility['name_en']}".strip()
                nf.aliasnamtc = "".join((f"{building_zh}{facility['name_zh']}").split())
            else:
                nf.aliasnamen = f"{building_eng} {level_eng}".strip()
                nf.aliasnamtc = "".join((f"{building_zh}{level_zh}").split())
    else:
        if facility:
            nf.aliasnamen = f"{building_eng} {facility['name_en']}".strip()
            nf.aliasnamtc = "".join((f"{building_zh}{facility['name_zh']}").split())
        else:
            nf.aliasnamen = f"{building_eng} {level_eng}".strip()
            nf.aliasnamtc = "".join((f"{building_zh}{level_zh}").split())


# SRID for Hong Kong 1980 Grid (indoor network geometry with Z)
INDOOR_NETWORK_SRID = 2326

UPSERT_INDOOR_NETWORK = text("""
INSERT INTO indoor_network (
  displayname, inetworkid, highway, oneway, emergency, wheelchair,
  flpolyid, crtdt, lstamddt, lstamdby, restricted,
  shape, level_id, feattype, floorId, location, wc_access, wc_barrier, direction,
  bldgid_1, buildingnameeng, buildingnamechi, levelenglishname, levelchinesename,
  aliasnamtc, aliasnamen
)
VALUES (
  :displayname, :inetworkid, :highway, :oneway, :emergency, :wheelchair,
  :flpolyid, :crtdt, :lstamddt, :lstamdby, :restricted,
  ST_GeomFromText(:shape_wkt, :srid), :level_id, :feattype, :floorId, :location, :wc_access, :wc_barrier, :direction,
  :bldgid_1, :buildingnameeng, :buildingnamechi, :levelenglishname, :levelchinesename,
  :aliasnamtc, :aliasnamen
)
ON CONFLICT (inetworkid) DO UPDATE SET
  displayname       = EXCLUDED.displayname,
  highway           = EXCLUDED.highway,
  oneway            = EXCLUDED.oneway,
  emergency         = EXCLUDED.emergency,
  wheelchair        = EXCLUDED.wheelchair,
  flpolyid          = EXCLUDED.flpolyid,
  crtdt             = EXCLUDED.crtdt,
  lstamddt          = EXCLUDED.lstamddt,
  lstamdby          = EXCLUDED.lstamdby,
  restricted        = EXCLUDED.restricted,
  shape             = EXCLUDED.shape,
  level_id          = EXCLUDED.level_id,
  feattype          = EXCLUDED.feattype,
  floorId           = EXCLUDED.floorId,
  location          = EXCLUDED.location,
  wc_access         = EXCLUDED.wc_access,
  wc_barrier        = EXCLUDED.wc_barrier,
  direction         = EXCLUDED.direction,
  bldgid_1          = EXCLUDED.bldgid_1,
  buildingnameeng   = EXCLUDED.buildingnameeng,
  buildingnamechi   = EXCLUDED.buildingnamechi,
  levelenglishname  = EXCLUDED.levelenglishname,
  levelchinesename  = EXCLUDED.levelchinesename,
  aliasnamtc        = EXCLUDED.aliasnamtc,
  aliasnamen        = EXCLUDED.aliasnamen
""")


def _geojson_to_wkt_2326(geojson_str: str) -> str | None:
    """Convert GeoJSON string (EPSG:2326 coordinates) to WKT for PostGIS. Preserves Z."""
    if not geojson_str or not geojson_str.strip():
        return None
    try:
        data = json.loads(geojson_str)
        geom_data = data.get("geometry") or data
        geom = shape(geom_data)
        if geom is None or geom.is_empty:
            return None
        return geom.wkt
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def insert_network_rows_into_indoor_network(session, displayname: str, rows: list["NetworkStagingRow"]) -> int:
    """
    Upsert processed network staging rows into indoor_network.
    Shape is inserted as geometry SRID 2326 with Z from each row's GeoJSON.
    Returns the number of rows upserted.
    """
    from app.schema.network import NetworkStagingRow as NSR
    count = 0
    for row in rows:
        if not isinstance(row, NSR):
            continue
        shape_wkt = _geojson_to_wkt_2326(row.geojson or "")
        if shape_wkt is None:
            continue
        try:
            floor_id_val = row.floorId
            if floor_id_val is not None and not isinstance(floor_id_val, int):
                s = str(floor_id_val).strip()
                floor_id_val = int(s) if s.isdigit() else None
        except (TypeError, ValueError):
            floor_id_val = None
        feattype_str = str(row.feattype) if row.feattype is not None else None
        bldgid_str = str(row.bldgid_1) if row.bldgid_1 is not None else None
        session.execute(
            UPSERT_INDOOR_NETWORK,
            {
                "displayname": displayname,
                "inetworkid": row.inetworkid,
                "highway": row.highway or "",
                "oneway": row.oneway or "",
                "emergency": row.emergency or "",
                "wheelchair": row.wheelchair or "",
                "flpolyid": row.flpolyid or "",
                "crtdt": row.crtdt,
                "lstamddt": row.lstamddt,
                "lstamdby": row.lstamdby or "",
                "restricted": row.restricted or "",
                "shape_wkt": shape_wkt,
                "srid": INDOOR_NETWORK_SRID,
                "level_id": row.level_id,
                "feattype": feattype_str,
                "floorId": floor_id_val,
                "location": row.location if row.location is not None else 2,
                "wc_access": row.wc_access,
                "wc_barrier": row.wc_barrier,
                "direction": row.direction,
                "bldgid_1": bldgid_str,
                "buildingnameeng": row.buildingnameeng,
                "buildingnamechi": row.buildingnamechi,
                "levelenglishname": row.levelenglishname,
                "levelchinesename": row.levelchinesename,
                "aliasnamtc": row.aliasnamtc,
                "aliasnamen": row.aliasnamen,
            },
        )
        count += 1
    return count


UPSERT_PEDROUTE_REL_FLOORPOLY = text("""
INSERT INTO pedrouterelfloorpoly (
  level_id,
  floor_id,
  floor_poly_id,
  buildingid,
  english_name,
  chinese_name,
  buildingcsuid,
  buildingtype,
  creation_date,
  last_amendment_date,
  modified_by
)
VALUES (
  :level_id,
  :floor_id,
  :floor_poly_id,
  :buildingid,
  :english_name,
  :chinese_name,
  :buildingcsuid,
  :buildingtype,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP,
  :modified_by
)
ON CONFLICT (level_id) DO UPDATE SET
  floor_id           = EXCLUDED.floor_id,
  floor_poly_id      = EXCLUDED.floor_poly_id,
  buildingid        = EXCLUDED.buildingid,
  english_name       = EXCLUDED.english_name,
  chinese_name       = EXCLUDED.chinese_name,
  buildingcsuid      = EXCLUDED.buildingcsuid,
  buildingtype       = EXCLUDED.buildingtype,
  last_amendment_date= CURRENT_TIMESTAMP,
  modified_by        = EXCLUDED.modified_by
;
""")
async def sync_pedrouterelfloorpoly_from_imdf(displayName: str, modified_by: str = "system"):
    level_doc = await get_level_by_displayName(displayName)
    if not level_doc or not isinstance(level_doc.get("features"), list):
        return {"status": "error", "message": "Level data not found or invalid"}

    upserted = 0
    skipped = []

    with SessionLocal() as session:
        try:
            for feat in level_doc["features"]:
                level_id = feat.get("id")
                props = feat.get("properties") or {}

                floor_poly_id = props.get("FloorPolyID")  # your d / flpolyid
                if not level_id or not floor_poly_id:
                    skipped.append({"reason": "missing_level_id_or_floorpolyid", "feature_id": level_id})
                    continue

                buildingcsuid, floorNumber = flpolyid_slices(floor_poly_id)
                if not buildingcsuid or not floorNumber:
                    skipped.append({"reason": "bad_floorpolyid_format", "feature_id": level_id, "FloorPolyID": floor_poly_id})
                    continue

                buildingInfo = await get_buildinginfo_by_buildingCSUID(buildingcsuid)
                if not buildingInfo:
                    skipped.append({"reason": "no_buildinginfo_for_buildingcsuid", "feature_id": level_id, "buildingcsuid": buildingcsuid})
                    continue

                # BuildingID is in your example docs
                buildingid = buildingInfo.get("BuildingID")

                # level name is an object: { "en": "...", "zh": "..." }
                name_obj = props.get("name") or {}
                english_name = name_obj.get("en")
                chinese_name = name_obj.get("zh")

                # floor_id rule: from your earlier enrichment pattern:
                # floor_id = SixDigitID + floorNumber
                sixDigitID = buildingInfo.get("SixDigitID")
                floor_id = None
                if sixDigitID is not None and floorNumber is not None:
                    floor_id = int(f"{sixDigitID}{floorNumber}")

                buildingtype = buildingInfo.get("buildingType")  # array in Mongo

                session.execute(
                    UPSERT_PEDROUTE_REL_FLOORPOLY,
                    {
                        "level_id": level_id,
                        "floor_id": floor_id,
                        "floor_poly_id": floor_poly_id,
                        "buildingid": buildingid,
                        "english_name": english_name,
                        "chinese_name": chinese_name,
                        "buildingcsuid": buildingcsuid,
                        "buildingtype": buildingtype,
                        "modified_by": modified_by,
                    },
                )
                upserted += 1

            session.commit()
            return {"status": "success", "upserted": upserted, "skipped": skipped}
        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e)}
