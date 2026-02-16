CREATE TABLE indoor_network_test (
    displayname TEXT NOT NULL,
    venue_id TEXT NOT NULL, -- Foreign key to venue.displayname (or id if we switch to that)
    pedrouteid SERIAL PRIMARY KEY NOT NULL CHECK (pedrouteid >= 1000000000 AND pedrouteid <= 9999999999),
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

-- Attach the trigger to indoor_network_test
DROP TRIGGER IF EXISTS trg_calculate_len_test ON indoor_network_test;
CREATE TRIGGER trg_calculate_len_test
BEFORE INSERT OR UPDATE ON indoor_network_test
FOR EACH ROW
EXECUTE FUNCTION update_shape_len();
--------------------------------------------------------------------------------------

-- 1. Create History Table------------------------------------------------------------
-- This table mirrors the structure of indoor_network_test but adds operation tracking
CREATE TABLE IF NOT EXISTS indoor_network_test_history (
    history_id SERIAL PRIMARY KEY,
    venue_id TEXT, -- Reference to venue, for easier querying
    pedrouteid INTEGER, -- Not a PK here, just a reference
    inetworkid TEXT,
    displayname TEXT,
    operation TEXT, -- 'UPDATE' or 'DELETE'
    history_recorded_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    
    -- Include all original columns from indoor_network_test
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

CREATE INDEX IF NOT EXISTS idx_history_inetworkid_test ON indoor_network_test_history(inetworkid);
CREATE INDEX IF NOT EXISTS idx_indoor_network_test_shape_3d ON indoor_network_test USING GIST (shape gist_geometry_ops_nd); -- 3D Index
-- history table----------------------------------------------------------


-- 2. Create Trigger Function
-- Automatically saves the OLD version of a row before an Update or Delete
--------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION log_indoor_network_test_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        -- OPTIMIZATION: Stop! If the data hasn't changed, don't save history.
        IF NEW IS NOT DISTINCT FROM OLD THEN
            RETURN NULL;
        END IF;

        INSERT INTO indoor_network_test_history (
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
        INSERT INTO indoor_network_test_history (
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
DROP TRIGGER IF EXISTS trg_indoor_network_test_history ON indoor_network_test;
CREATE TRIGGER trg_indoor_network_test_history
BEFORE UPDATE OR DELETE ON indoor_network_test
FOR EACH ROW EXECUTE FUNCTION log_indoor_network_test_changes();

DROP TRIGGER IF EXISTS trg_set_updated_at_test ON indoor_network_test;
CREATE TRIGGER trg_set_updated_at_test
BEFORE UPDATE ON indoor_network_test
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
----------------------------------------------------------------------------------
