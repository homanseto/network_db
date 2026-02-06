from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class NetworkStagingRow(BaseModel):
    """
    Row from network_staging used for validation & calculations.

    Fields here match current columns; you can safely add more later
    as the table evolves.
    """

    inetworkid: str
    geojson: str
    highway: str
    oneway: str      # could narrow later: Literal["yes", "no"]
    emergency: Optional[str] = None      # e.g. "yes"/"no"
    wheelchair: Optional[str] = None     # e.g. "yes"/"no"
    flpolyid: str
    crtdt: Optional[str] = None          # default "03"; can be date string e.g. "28/11/2025"
    crtby:  Optional[str] = "03"
    lstamddt: Optional[str] = None  # "28/11/2025 09:21:41"
    lstamdby: Optional[str] = "03"
    restricted: str                     # e.g. "Y"/"N" (for later use)
    shape: str                               # WKB string; you can model this more strictly later
    level_id: Optional[str] = None         # Level UUID; filter unit_features to same level for intersection
    feattype: Optional[int] = None         # FeatureType code (1=walkway, 8=escalator, etc.)
    floorId: Optional[int] = None          # Computed from SixDigitID + floorNumber
    location: Optional[int] = 2
    wc_access: Optional[int] = None
    wc_barrier: Optional[int] = None
    direction: Optional[int] = None
    bldgid_1: Optional[int] = None
    buildingnameeng: Optional[str] = None
    buildingnamechi: Optional[str] = None
    levelenglishname: Optional[str] = None
    levelchinesename: Optional[str] = None
    aliasaamtc: Optional[str] = None
    aliasnamen: Optional[str] = None
    displayname: Optional[str] = None
    pedrouteid: Optional[int] = None

  




    class Config:
        # Ignore extra DB columns you haven't modeled yet,
        # so adding new columns in the table won't break validation.
        extra = "ignore"