### create error table 


CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS network_staging_errors (
    INETWORKID text,
    error_type text,
    error_message text,
    created_at timestamp default now()
);

#### Validation Procedure (Production Version)
CREATE OR REPLACE FUNCTION validate_network_staging()
RETURNS json
LANGUAGE plpgsql
AS $$
DECLARE
    error_count int;
BEGIN

    -- Clean previous errors
    DELETE FROM network_staging_errors;

    ----------------------------------------------------------------
    -- 1. Geometry NULL
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID, 'GEOMETRY_NULL', 'Geometry is NULL'
    FROM network_staging
    WHERE shape IS NULL;

    ----------------------------------------------------------------
    -- 2. Invalid geometry
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID, 'INVALID_GEOMETRY', ST_IsValidReason(shape)
    FROM network_staging
    WHERE NOT ST_IsValid(shape);

    ----------------------------------------------------------------
    -- 3. Wrong SRID
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID, 'WRONG_SRID', 'SRID must be 2326'
    FROM network_staging
    WHERE ST_SRID(shape) != 2326;

    ----------------------------------------------------------------
    -- 4. Not 3D
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID, 'NOT_3D', 'Geometry must be 3D'
    FROM network_staging
    WHERE ST_NDims(shape) != 3;

    ----------------------------------------------------------------
    -- 5. Wrong type
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID,
    'WRONG_DIMENSION',
    'Geometry must be 3D (XYZ)'
    FROM network_staging
    WHERE ST_NDims(shape) != 3;

    ----------------------------------------------------------------
    -- 6. pedrouteid NULL
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT NULL, 'INETWORKID_NULL', 'INETWORKID is NULL'
    FROM network_staging
    WHERE INETWORKID IS NULL;

    ----------------------------------------------------------------
    -- 7. Duplicate pedrouteid
    ----------------------------------------------------------------
    INSERT INTO network_staging_errors (INETWORKID, error_type, error_message)
    SELECT INETWORKID, 'DUPLICATE_INETWORKID', 'Duplicate in staging'
    FROM (
        SELECT INETWORKID
        FROM network_staging
        GROUP BY INETWORKID
        HAVING COUNT(*) > 1
    ) t;

    ----------------------------------------------------------------
    -- Count errors
    ----------------------------------------------------------------
    SELECT COUNT(*) INTO error_count FROM network_staging_errors;

    RETURN json_build_object(
        'valid', error_count = 0,
        'error_count', error_count
    );

END;
$$;

#### create PedouteRelFloorPolyID 
CREATE TABLE pedrouterelfloorpoly (
    level_id text PRIMARY KEY,
    external_id SERIAL,  -- Auto-incrementing integer primary key
    floor_id BIGINT,
    floor_poly_id VARCHAR(50),
    buildingid BIGINT,
    english_name VARCHAR(255),
    chinese_name VARCHAR(255),
    data_source INTEGER DEFAULT 2,
    level_source INTEGER DEFAULT 2,
    creation_date TIMESTAMP,
    modified_by VARCHAR(50),
    last_amendment_date TIMESTAMP,
    buildingcsuid VARCHAR(50),
    buildingtype VARCHAR(255)[],  -- Array of building types
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


## Create buildingInfo table
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- Enable UUID generation

CREATE TABLE buildings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),  -- Auto-generates UUID
    displayName VARCHAR(255),
    buildingCSUID VARCHAR(50),
    buildingType TEXT[],
    region VARCHAR(10),
    teamID INTEGER,
    name_CH VARCHAR(255),
    name_EN VARCHAR(255),
    batch VARCHAR(10),
    modelID VARCHAR(50),
    type VARCHAR(255),
    sixDigitID INTEGER,
    "index" INTEGER,
    buildingID BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

### indoor_network table (aligned with api/app/schema/network.py NetworkStagingRow)
CREATE TABLE indoor_network (
    pedrouteid SERIAL PRIMARY KEY,
    displayname TEXT NOT NULL,
    inetworkid TEXT UNIQUE NOT NULL,
    highway TEXT NOT NULL,
    oneway TEXT NOT NULL,
    emergency TEXT NOT NULL,
    wheelchair TEXT NOT NULL,
    flpolyid TEXT NOT NULL,
    crtdt TEXT,
    crtby TEXT DEFAULT '03',
    lstamddt TEXT,
    lstamdby TEXT DEFAULT '03',
    restricted TEXT NOT NULL CHECK (restricted IN ('Y', 'N')),
    shape GEOMETRY(LineStringZ, 2326),
    level_id TEXT NOT NULL,
    feattype INTEGER NOT NULL CHECK (feattype IN (1, 8, 9, 10, 11, 12, 13)),
    floorid INTEGER NOT NULL CHECK (floorid >= 1000000000 AND floorid <= 9999999999),
    location INTEGER NOT NULL CHECK (location IN (1, 2, 3)),
    gradient DOUBLE PRECISION NOT NULL,
    wc_access INTEGER NOT NULL CHECK (wc_access IN (1, 2)),
    wc_barrier INTEGER NOT NULL CHECK (wc_barrier IN (1, 2)),
    direction INTEGER NOT NULL CHECK (direction IN (0, 1, -1)),
    bldgid_1 INTEGER NOT NULL,
    bldgid_2 INTEGER,
    siteid INTEGER,
    aliasnamtc TEXT NOT NULL,
    aliasnamen TEXT NOT NULL,
    terminalid INTEGER NOT NULL CHECK (terminalid >= 1000000000 AND terminalid <= 9999999999),
    acstimeid INTEGER,
    crossfeat TEXT,
    st_code TEXT,
    st_nametc TEXT,
    st_nameen TEXT,
    modifiedby TEXT DEFAULT 'LANDSD',
    poscertain INTEGER DEFAULT 1,
    datasrc INTEGER DEFAULT 1,
    levelsrc INTEGER DEFAULT 2,
    enabled INTEGER DEFAULT 1,
    shape_len DOUBLE PRECISION,
    buildnamen TEXT,
    buildnamzh TEXT,
    leveleng TEXT,
    levelzh TEXT,
    mainexit BOOLEAN
);
