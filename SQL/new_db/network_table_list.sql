### create error table 

--------network_staging_errors-------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS network_staging_errors (
    INETWORKID text,
    error_type text,
    error_message text,
    created_at timestamp default now()
);
-------------------------------------------------------------

---------------- Validation Procedure (Production Version)-----------------
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
-------------------------------------------------------------------------------

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
    pedrouteid SERIAL PRIMARY KEY NOT NULL CHECK (floorid >= 1000000000 AND floorid <= 9999999999),
    displayname TEXT NOT NULL,
    inetworkid TEXT UNIQUE NOT NULL,
    highway TEXT NOT NULL,
    oneway TEXT NOT NULL CHECK (oneway IN ('yes', 'reverse', 'no')),
    emergency TEXT NOT NULL CHECK (emergency IN ('yes', 'no')),
    wheelchair TEXT NOT NULL CHECK (emergency IN ('yes', 'no')),
    flpolyid TEXT NOT NULL,
    crtdt TEXT,
    crtby TEXT DEFAULT '03',
    lstamddt TEXT,
    lstamdby TEXT DEFAULT '03',
    restricted TEXT NOT NULL CHECK (restricted IN ('Y', 'N')),
    shape GEOMETRY(LineStringZ, 2326),
    feattype INTEGER NOT NULL CHECK (feattype IN (1, 8, 9, 10, 11, 12, 13)),
    floorid INTEGER NOT NULL CHECK (floorid >= 1000000000 AND floorid <= 9999999999),
    location INTEGER NOT NULL CHECK (location IN (1, 2, 3)),
    gradient DOUBLE PRECISION NOT NULL,
    wc_access INTEGER NOT NULL CHECK (wc_access IN (1, 2)),
    wc_barrier INTEGER NOT NULL CHECK (wc_barrier IN (1, 2)),
    wx_proof INTEGER NOT NULL CHECK (wx_proof IN (1, 2)) DEFAULT 1,
    obstype INTEGER,
    direction INTEGER NOT NULL CHECK (direction IN (0, 1, -1)),
    bldgid_1 INTEGER NOT NULL,
    bldgid_2 INTEGER,
    siteid INTEGER,
    aliasnamtc TEXT NOT NULL,
    aliasnamen TEXT NOT NULL,
    terminalid INTEGER CHECK (terminalid >= 1000000000 AND terminalid <= 9999999999),
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
    level_id TEXT NOT NULL,
    buildnamen TEXT,
    buildnamzh TEXT,
    leveleng TEXT,
    levelzh TEXT,
    mainexit BOOLEAN,
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong')
);

-- OPTION A: PostGIS Automatic Level Calculation Trigger
-- This function calculates the 3D length of the shape automatically on INSERT or UPDATE.
CREATE OR REPLACE FUNCTION update_shape_len()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure using 3D Length (LineStringZ)
    -- This handles slope distances accurately (e.g. ramps, stairs)
    NEW.shape_len := ST_3DLength(NEW.shape);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach the trigger to indoor_network
DROP TRIGGER IF EXISTS trg_calculate_len ON indoor_network;
CREATE TRIGGER trg_calculate_len
BEFORE INSERT OR UPDATE ON indoor_network
FOR EACH ROW
EXECUTE FUNCTION update_shape_len();
--------------------------------------------------------------------------------------

-- 1. Create History Table------------------------------------------------------------
-- This table mirrors the structure of indoor_network but adds operation tracking
CREATE TABLE IF NOT EXISTS indoor_network_history (
    history_id SERIAL PRIMARY KEY,
    pedrouteid INTEGER, -- Not a PK here, just a reference
    inetworkid TEXT,
    displayname TEXT,
    operation TEXT, -- 'UPDATE' or 'DELETE'
    history_recorded_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    
    -- Include all original columns from indoor_network
    highway TEXT,
    oneway TEXT,
    emergency TEXT,
    wheelchair TEXT,
    flpolyid TEXT,
    crtdt TEXT,
    crtby TEXT,
    lstamddt TEXT,
    lstamdby TEXT,
    restricted TEXT,
    shape GEOMETRY(LineStringZ, 2326),
    feattype INTEGER,
    floorid INTEGER,
    location INTEGER,
    gradient DOUBLE PRECISION,
    wc_access INTEGER,
    wc_barrier INTEGER,
    wx_proof INTEGER,
    direction INTEGER,
    obstype INTEGER,
    bldgid_1 INTEGER,
    bldgid_2 INTEGER,
    siteid INTEGER,
    aliasnamtc TEXT,
    aliasnamen TEXT,
    terminalid INTEGER,
    acstimeid INTEGER,
    crossfeat TEXT,
    st_code TEXT,
    st_nametc TEXT,
    st_nameen TEXT,
    modifiedby TEXT,
    poscertain INTEGER,
    datasrc INTEGER,
    levelsrc INTEGER,
    enabled INTEGER,
    shape_len DOUBLE PRECISION,
    level_id TEXT,
    buildnamen TEXT,
    buildnamzh TEXT,
    leveleng TEXT,
    levelzh TEXT,
    mainexit BOOLEAN,
    -- Also track the timestamps from the original row
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_history_inetworkid ON indoor_network_history(inetworkid);
CREATE INDEX IF NOT EXISTS idx_indoor_network_shape_3d ON indoor_network USING GIST (shape gist_geometry_ops_nd); -- 3D Index
-- history table----------------------------------------------------------


-- 2. Create Trigger Function
-- Automatically saves the OLD version of a row before an Update or Delete
--------------------------------------------------------------------------------
-- 3. Update the Trigger Function (Run the full definition)
CREATE OR REPLACE FUNCTION log_indoor_network_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        -- OPTIMIZATION: Stop! If the data hasn't changed, don't save history.
        IF NEW IS NOT DISTINCT FROM OLD THEN
            RETURN NULL;
        END IF;

        INSERT INTO indoor_network_history (
            pedrouteid, inetworkid, displayname, operation,
            highway, oneway, emergency, wheelchair, flpolyid, crtdt, crtby, 
            lstamddt, lstamdby, restricted, shape, feattype, floorid, location, 
            gradient, wc_access, wc_barrier, wx_proof, direction, obstype, bldgid_1, bldgid_2, siteid, 
            aliasnamtc, aliasnamen, terminalid, acstimeid, crossfeat, st_code, 
            st_nametc, st_nameen, modifiedby, poscertain, datasrc, levelsrc, 
            enabled, shape_len, level_id, buildnamen, buildnamzh, leveleng, 
            levelzh, mainexit, created_at, updated_at
        )
        VALUES (
            OLD.pedrouteid, OLD.inetworkid, OLD.displayname, 'UPDATE',
            OLD.highway, OLD.oneway, OLD.emergency, OLD.wheelchair, OLD.flpolyid, OLD.crtdt, OLD.crtby, 
            OLD.lstamddt, OLD.lstamdby, OLD.restricted, OLD.shape, OLD.feattype, OLD.floorid, OLD.location, 
            OLD.gradient, OLD.wc_access, OLD.wc_barrier, OLD.wx_proof, OLD.direction, OLD.obstype, OLD.bldgid_1, OLD.bldgid_2, OLD.siteid, 
            OLD.aliasnamtc, OLD.aliasnamen, OLD.terminalid, OLD.acstimeid, OLD.crossfeat, OLD.st_code, 
            OLD.st_nametc, OLD.st_nameen, OLD.modifiedby, OLD.poscertain, OLD.datasrc, OLD.levelsrc, 
            OLD.enabled, OLD.shape_len, OLD.level_id, OLD.buildnamen, OLD.buildnamzh, OLD.leveleng, 
            OLD.levelzh, OLD.mainexit, OLD.created_at, OLD.updated_at
        );
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO indoor_network_history (
            pedrouteid, inetworkid, displayname, operation,
            highway, oneway, emergency, wheelchair, flpolyid, crtdt, crtby,
            lstamddt, lstamdby, restricted, shape, feattype, floorid, location,
            gradient, wc_access, wc_barrier, wx_proof, direction, obstype, bldgid_1, bldgid_2, siteid,
            aliasnamtc, aliasnamen, terminalid, acstimeid, crossfeat, st_code,
            st_nametc, st_nameen, modifiedby, poscertain, datasrc, levelsrc,
            enabled, shape_len, level_id, buildnamen, buildnamzh, leveleng,
            levelzh, mainexit, created_at, updated_at
        )
        VALUES (
            OLD.pedrouteid, OLD.inetworkid, OLD.displayname, 'DELETE',
            OLD.highway, OLD.oneway, OLD.emergency, OLD.wheelchair, OLD.flpolyid, OLD.crtdt, OLD.crtby,
            OLD.lstamddt, OLD.lstamdby, OLD.restricted, OLD.shape, OLD.feattype, OLD.floorid, OLD.location,
            OLD.gradient, OLD.wc_access, OLD.wc_barrier, OLD.wx_proof, OLD.direction, OLD.obstype, OLD.bldgid_1, OLD.bldgid_2, OLD.siteid, 
            OLD.aliasnamtc, OLD.aliasnamen, OLD.terminalid, OLD.acstimeid, OLD.crossfeat, OLD.st_code, 
            OLD.st_nametc, OLD.st_nameen, OLD.modifiedby, OLD.poscertain, OLD.datasrc, OLD.levelsrc,
            OLD.enabled, OLD.shape_len, OLD.level_id, OLD.buildnamen, OLD.buildnamzh, OLD.leveleng,
            OLD.levelzh, OLD.mainexit, OLD.created_at, OLD.updated_at
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
--------------------------------------------------------------------------------

-- 4. Create Trigger Function: Auto-Update Timestamp
-- This keeps the "updated_at" column fresh.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (NOW() AT TIME ZONE 'Asia/Hong_Kong');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
--------------------------------------------------------------------------------


-- 5. Attach the Triggers to the Main Table--------------------------------------
DROP TRIGGER IF EXISTS trg_indoor_network_history ON indoor_network;
CREATE TRIGGER trg_indoor_network_history
BEFORE UPDATE OR DELETE ON indoor_network
FOR EACH ROW EXECUTE FUNCTION log_indoor_network_changes();

DROP TRIGGER IF EXISTS trg_set_updated_at ON indoor_network;
CREATE TRIGGER trg_set_updated_at
BEFORE UPDATE ON indoor_network
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
----------------------------------------------------------------------------------


