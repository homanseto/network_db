from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class NetworkStagingRow(BaseModel):
    """
    Row from network_staging used for validation & calculations.

    Fields here match current columns; you can safely add more later
    as the table evolves.
    """
    pedrouteid: Optional[int] = None
    displayname: Optional[str] = None
    inetworkid: str
    highway: str
    oneway: Optional[Literal["yes", "reverse", "no"]]    # could narrow later: Literal["yes", "no"]
    emergency: Optional[Literal["yes", "no"]]      # e.g. "yes"/"no"
    wheelchair: Optional[Literal["yes", "no"]]       # e.g. "yes"/"no"
    flpolyid: str
    crtdt: str        # default "03"; can be date string e.g. "28/11/2025"
    crtby:  str = "03"
    lstamddt: str  # "28/11/2025 09:21:41"
    lstamdby: str = "03"
    restricted: Optional[Literal["Y", "N"]] = None
    shape: str                               # WKB string; you can model this more strictly later
    level_id: Optional[str] = None          # Level UUID; filter unit_features to same level for intersection
    feattype: Optional[Literal[1,8,9,10,11,12,13]] = None        # FeatureType code (1=walkway, 8=escalator, etc.)
    floorid: Optional[int] = Field(None, ge=1_000_000_000, le=9_999_999_999)  # 10-digit number, e.g. 1009790001
    location: Optional[Literal[1, 2, 3]] = None
    gradient: Optional[float] = 0.0
    wc_access: Optional[Literal[1, 2]] = None
    wc_barrier: Optional[Literal[1, 2]] = None
    wx_proof: Optional[Literal[1, 2]] = None
    direction: Optional[Literal[0, 1, -1]] = None
    obstype:Optional[int] = None
    bldgid_1: Optional[int] = None
    bldgid_2: Optional[int] = None
    siteid: Optional[int] = None
    aliasnamtc: Optional[str] = None
    aliasnamen: Optional[str] = None
    terminalid: Optional[int] = Field(None, ge=1_000_000_000, le=9_999_999_999)  # 10-digit number
    acstimeid: Optional[int] = None  # exists but can be null
    crossfeat: Optional[str] = None
    st_code: Optional[str] = None
    st_nametc: Optional[str] = None
    st_nameen: Optional[str] = None
    modifiedby: Optional[str] = "LANDSD"
    poscertain: Optional[int] = 1
    datasrc: Optional[int] = 1
    levelsrc: Optional[int] = 2
    enabled: Optional[int] = 1
    shape_len: Optional[float] = None
    buildnamen: Optional[str] = None
    buildnamzh: Optional[str] = None
    leveleng: Optional[str] = None
    levelzh: Optional[str] = None
    mainexit: Optional[bool] = None  # aligns with 
    geojson: str # GeoJSON geometry; can be dict or other structure


  




    class Config:
        # Ignore extra DB columns you haven't modeled yet,
        # so adding new columns in the table won't break validation.
        extra = "ignore"