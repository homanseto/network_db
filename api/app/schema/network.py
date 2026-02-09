from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class NetworkStagingRow(BaseModel):
    """
    Row from network_staging used for validation & calculations.

    Fields here match current columns; you can safely add more later
    as the table evolves.
    """
    pedrouteid: int
    displayname: str
    inetworkid: str
    highway: str
    oneway: str      # could narrow later: Literal["yes", "no"]
    emergency: str     # e.g. "yes"/"no"
    wheelchair: str     # e.g. "yes"/"no"
    flpolyid: str
    crtdt: str        # default "03"; can be date string e.g. "28/11/2025"
    crtby:  str = "03"
    lstamddt: str  # "28/11/2025 09:21:41"
    lstamdby: str = "03"
    restricted: Literal["Y", "N"]
    shape: str                               # WKB string; you can model this more strictly later
    level_id: str          # Level UUID; filter unit_features to same level for intersection
    feattype: Literal[1,8,9,10,11,12,13]         # FeatureType code (1=walkway, 8=escalator, etc.)
    floorid: int = Field(..., ge=1_000_000_000, le=9_999_999_999)  # 10-digit number, e.g. 1009790001
    location: Literal[1, 2, 3]
    gradient: float
    wc_access: Literal[1, 2]
    wc_barrier: Literal[1, 2]
    direction: Literal[0, 1, -1]
    bldgid_1: int
    bldgid_2: Optional[int] = None
    siteid: Optional[int] = None
    aliasnamtc: str
    aliasnamen: str
    terminalid: int = Field(..., ge=1_000_000_000, le=9_999_999_999)  # 10-digit number
    acstimeid: Optional[int] = None  # exists but can be null
    crossfeat: Optional[str] = None
    st_code: Optional[str] = None
    st_nametc: Optional[str] = None
    st_nameen: Optional[str] = None
    modifiedby: str= "LANDSD"
    poscertain: int = 1
    datasrc: int = 1 
    levelsrc: int = 2
    enabled: int = 1
    shape_len: Optional[float] = None
    buildnamen: Optional[str] = None
    buildnamzh: Optional[str] = None
    leveleng: Optional[str] = None
    levelzh: Optional[str] = None
    mainexit: Optional[bool] = None  # aligns with pedestrian_convert_table.json


  




    class Config:
        # Ignore extra DB columns you haven't modeled yet,
        # so adding new columns in the table won't break validation.
        extra = "ignore"