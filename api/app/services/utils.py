# app/services/utils.py

import json
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schema.network import NetworkStagingRow

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import transform as shapely_transform
from pyproj import Transformer

# Staging = EPSG:2326 (Hong Kong 1980 Grid, meters); units from IMDF = EPSG:4326 (WGS84, lon/lat).
_TRANSFORMER_2326_TO_4326 = Transformer.from_crs("EPSG:2326", "EPSG:4326", always_xy=True)

# Unit category -> FeatureType code (matches reference.ts UnitFeatureTypeMap)
UNIT_FEATURE_TYPE_MAP: dict[str, int] = {
    "walkway": 1,
    "room": 1,
    "unspecified": 1,
    "footbridge": 2,
    "escalator": 8,
    "elevator": 10,
    "ramp": 11,
    "movingwalkway": 9,
    "stairs": 12,
    "steps": 12,
    "staircase": 12,
    "stairlift": 13,
    "N/A": 14,
}
DEFAULT_FEATURE_TYPE = 1  # walkway


# Projection: EPSG:2326 (Hong Kong 1980 Grid System) — units are meters.
def _horizontal_distance_meters(fp: list[float], ep: list[float]) -> float:
    """
    Horizontal distance between two (x, y) points in meters.
    Assumes coordinates are in EPSG:2326 (Hong Kong 1980 Grid System), so planar distance is in meters.
    """
    dx = ep[0] - fp[0]
    dy = ep[1] - fp[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_gradient(highway: str, line: list[list[float]]) -> float:
    """
    Calculate gradient (absolute slope angle in radians) for a 3D linestring.

    - highway === "lift" means the linestring is vertical (e.g. lift/elevator);
      gradient is treated as pi/2 (vertical).
    - line: 3D linestring as list of [x, y, z] in EPSG:2326 (Hong Kong 1980); x,y in meters, z elevation.
    - Returns absolute gradient in radians (0 = flat, pi/2 = vertical).
    """
    if not line or len(line) < 2:
        return 0.0

    fp = line[0]
    ep = line[-1]
    z_value = fp[2] - ep[2]
    length = _horizontal_distance_meters(fp, ep)

    if z_value == 0:
        return 0.0
    if length == 0 or highway == "lift":
        return math.pi / 2
    return abs(math.atan2(z_value, length))


# --- calculate_feature_type (from reference.ts calculatFeatureType) ---


def _line_from_geojson(geojson_str: str) -> LineString | None:
    """Build Shapely LineString from GeoJSON string (e.g. from NetworkStagingRow.geojson). Assumes EPSG:2326."""
    try:
        data = json.loads(geojson_str)
        geom = data.get("geometry") or data
        return shape(geom)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def _transform_2326_to_4326(geom: LineString | Polygon) -> LineString | Polygon:
    """Transform geometry from EPSG:2326 (Hong Kong) to EPSG:4326 (WGS84) for comparison with unit features."""
    return shapely_transform(_TRANSFORMER_2326_TO_4326.transform, geom)


def _force_2d(geom: LineString | Polygon) -> LineString | Polygon:
    """Strip Z so geometry is 2D (XY only). Avoids shapely.force_2d which may be missing in some Shapely versions."""
    if geom is None or geom.is_empty or not getattr(geom, "has_z", False):
        return geom
    if geom.geom_type == "LineString":
        return LineString([(c[0], c[1]) for c in geom.coords])
    if geom.geom_type == "Polygon":
        exterior = [(c[0], c[1]) for c in geom.exterior.coords]
        holes = [[(c[0], c[1]) for c in ring.coords] for ring in geom.interiors]
        return Polygon(exterior, holes)
    return geom


def _polygon_from_unit_feature(unit: dict) -> Polygon | None:
    """Build Shapely Polygon from IUnitFeature geometry (2D or 3D coords)."""
    try:
        geom = unit.get("geometry")
        if not geom:
            return None
        poly = shape(geom)
        if poly.is_empty:
            return None
        if poly.has_z:
            poly = _force_2d(poly)
        return poly if poly.geom_type == "Polygon" else None
    except (TypeError, KeyError):
        return None


def _are_all_values_same(values: list[float]) -> bool:
    if not values:
        return True
    v0 = values[0]
    return all(v == v0 for v in values)


def _find_stair_lift_feature_type(
    unit: dict,
    unit3d_features: list[dict],
) -> int | None:
    """
    If unit is unspecified and (name.en === 'stairlift' or 3D UnitSubtype === '12-03'),
    return 13 (stairlift). Else None.
    """
    props = unit.get("properties") or {}
    if (props.get("category") or "").lower() != "unspecified":
        return None
    name = props.get("name")
    name_en = (name.get("en") or "").strip().lower() if isinstance(name, dict) else ""
    if name_en == "stairlift":
        return 13
    unit_poly_id = props.get("UnitPolyID")
    if unit_poly_id and unit3d_features:
        for u3 in unit3d_features:
            p3 = u3.get("properties") or {}
            if p3.get("UnitPolyID") == unit_poly_id and p3.get("UnitSubtype") == "12-03":
                return 13
    return None


def _find_max_coverage_polygon(
    line: LineString,
    unit_features: list[dict],
) -> dict | None:
    """Return the unit feature whose polygon covers the longest portion of line."""
    if not line or not line.length:
        return None
    best_unit: dict | None = None
    best_length: float = -1.0
    for unit in unit_features:
        poly = _polygon_from_unit_feature(unit)
        if not poly or poly.is_empty:
            continue
        try:
            inter = line.intersection(poly)
            if inter.is_empty:
                continue
            length = inter.length if hasattr(inter, "length") else 0.0
            if inter.geom_type == "MultiLineString":
                length = sum(g.length for g in inter.geoms)
            if length > best_length:
                best_length = length
                best_unit = unit
        except Exception:
            continue
    return best_unit


def calculate_feature_type(
    nf: "NetworkStagingRow",
    unit_features: list[dict],
    unit3d_features: list[dict],
) -> int:
    """
    Determine FeatureType for a network staging row from unit / 3D unit features.

    - nf: staging row (NetworkStagingRow) with geojson LineString.
    - unit_features: list of IUnitFeature dicts (e.g. from get_unit_by_displayName(displayName)["features"]).
    - unit3d_features: list of I3DUnitFeature dicts (e.g. from get_3d_units_by_displayName(displayName)["features"]).

    Returns FeatureType code (1 = walkway, 8 = escalator, 10 = lift, 11 = ramp, 12 = stairs, 13 = stairlift, etc.).

    Does not modify nf or its geometry. The staging geometry (geojson/shape, EPSG:2326) must remain unchanged;
    only computed properties (e.g. FeatureType) are updated when writing to the real table.
    """
    # Allow dict or Pydantic model (e.g. model_dump())
    nf_dict = nf.model_dump() if hasattr(nf, "model_dump") else nf
    geojson_str = nf_dict.get("geojson") or ""
    level_id = nf_dict.get("level_id")

    line = _line_from_geojson(geojson_str)
    if not line or line.is_empty:
        return DEFAULT_FEATURE_TYPE

    if line.has_z:
        line = _force_2d(line)
    # Staging line is EPSG:2326; unit features are EPSG:4326 — transform line to 4326 for spatial ops.
    line = _transform_2326_to_4326(line)

    # Only consider units on the same level as nf (do not intersect with units on other levels).
    # Unit and unit3d are linked by properties.UnitPolyID (same key in both).
    if level_id is not None:
        units_on_level = [
            u for u in (unit_features or [])
            if (u.get("properties") or {}).get("level_id") == level_id
        ]
    else:
        units_on_level = unit_features or []

    # Intersecting or containing units (unit_features are in EPSG:4326)
    intersecting_units: list[dict] = []
    for unit in units_on_level:
        poly = _polygon_from_unit_feature(unit)
        if not poly:
            continue
        if line.intersects(poly) or line.within(poly):
            intersecting_units.append(unit)

    if not intersecting_units:
        return UNIT_FEATURE_TYPE_MAP.get("walkway", DEFAULT_FEATURE_TYPE)

    if len(intersecting_units) == 1:
        unit = intersecting_units[0]
        stair_lift = _find_stair_lift_feature_type(unit, unit3d_features or [])
        if stair_lift is not None:
            return stair_lift
        cat = (unit.get("properties") or {}).get("category") or "walkway"
        return UNIT_FEATURE_TYPE_MAP.get(cat.lower(), DEFAULT_FEATURE_TYPE)

    # Multiple intersections
    coords = []
    try:
        data = json.loads(geojson_str)
        geom = data.get("geometry") or data
        coords = geom.get("coordinates") or []
    except Exception:
        pass
    z_values = [c[2] for c in coords if isinstance(c, (list, tuple)) and len(c) >= 3]
    if not _are_all_values_same(z_values):
        # Z differs: prefer stairs/escalator/elevator, then ramp, else walkway
        for unit in intersecting_units:
            cat = (unit.get("properties") or {}).get("category") or ""
            if cat.lower() in ("stairs", "escalator", "elevator"):
                return UNIT_FEATURE_TYPE_MAP.get(cat.lower(), DEFAULT_FEATURE_TYPE)
        for unit in intersecting_units:
            if ((unit.get("properties") or {}).get("category") or "").lower() == "ramp":
                return UNIT_FEATURE_TYPE_MAP.get("ramp", DEFAULT_FEATURE_TYPE)
        return DEFAULT_FEATURE_TYPE

    # Same Z: longest coverage unit
    longest_unit = _find_max_coverage_polygon(line, intersecting_units)
    if not longest_unit:
        return DEFAULT_FEATURE_TYPE
    stair_lift = _find_stair_lift_feature_type(longest_unit, unit3d_features or [])
    if stair_lift is not None:
        return stair_lift
    cat = (longest_unit.get("properties") or {}).get("category") or "walkway"
    return UNIT_FEATURE_TYPE_MAP.get(cat.lower(), DEFAULT_FEATURE_TYPE)
