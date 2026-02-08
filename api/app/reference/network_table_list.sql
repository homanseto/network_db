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

### indoor network table 
CREATE TABLE indoor_network (
    pedrouteid SERIAL PRIMARY KEY,
    displayname TEXT,
    inetworkid TEXT UNIQUE,
    highway TEXT,
    oneway TEXT,
    emergency TEXT,
    wheelchair TEXT,
    flpolyid TEXT,
    crtdt TEXT,
    lstamddt TEXT,
    lstamdby TEXT,
    restricted TEXT,
    shape GEOMETRY(GeometryZ, 2326),  -- Correct syntax for 3D geometry with SRID 2326
    level_id TEXT,
    feattype TEXT,
    floorId INTEGER,
    location INTEGER,
    wc_access INTEGER,
    wc_barrier INTEGER,
    direction INTEGER,
    bldgid_1 TEXT,
    bldgid_2 TEXT,
    buildingnameeng TEXT,
    buildingnamechi TEXT,
    levelenglishname TEXT,
    levelchinesename TEXT,
    aliasnamtc TEXT,
    aliasnamen TEXT
);
