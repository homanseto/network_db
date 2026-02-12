-------------------------------------------------------------------------------
-- Pedestrian Network Table Creation
-- Based on FGDB schema mapping from pedestrian_convert_table.json
-- and types from indoor_network
-------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pedestrian_staging (
    staging_fid SERIAL PRIMARY KEY,
    shape GEOMETRY(LineStringZ, 2326),
    "PedestrianRouteID" INTEGER,
    "CreationDate" TEXT,
    "LastAmendmentDate" TEXT,
    "FeatureType" INTEGER,
    "FloorID" INTEGER,
    "Location" INTEGER,
    "Gradient" DOUBLE PRECISION,
    "WheelchairAccess" INTEGER,
    "WheelchairBarrier" INTEGER,
    "WeatherProof" INTEGER,
    "ObstaclesType" INTEGER,
    "Direction" INTEGER,
    "BuildingID_1" INTEGER,
    "BuildingID_2" INTEGER,
    "SiteID" INTEGER,
    "AliasNameTC" TEXT,
    "AliasNameEN" TEXT,
    "TerminalID" INTEGER,
    "AccessTimeID" INTEGER,
    "CrossingFeature" TEXT,
    "ST_CODE" TEXT,
    "StreetNameTC" TEXT,
    "StreetNameEN" TEXT,
    "ModifiedBy" TEXT,
    "PositionCertainty" INTEGER,
    "DataSource" INTEGER,
    "LevelSource" INTEGER,
    "Enabled" INTEGER,
    "Shape_Length" DOUBLE PRECISION
);

CREATE TABLE pedestrian_network (
    pedrouteid INTEGER PRIMARY KEY NOT NULL CHECK (pedrouteid >= 100000000 AND pedrouteid <= 999999999),
    crtdt TEXT,
    lstamddt TEXT,
    shape GEOMETRY(LineStringZ, 2326),
    feattype INTEGER NOT NULL CHECK (feattype BETWEEN 1 AND 33),
    floorid INTEGER CHECK ((floorid >= 100000000 AND floorid <= 9999999999) OR floorid IS NULL),
    location INTEGER NOT NULL CHECK (location IN (1, 2, 3)),
    gradient DOUBLE PRECISION NOT NULL,
    wc_access INTEGER NOT NULL CHECK (wc_access IN (1, 2)),
    wc_barrier INTEGER NOT NULL CHECK (wc_barrier IN (1, 2)),
    wx_proof INTEGER NOT NULL CHECK (wx_proof IN (1, 2, 3)),
    obstype INTEGER,
    direction INTEGER NOT NULL CHECK (direction IN (0, 1, -1)),
    bldgid_1 INTEGER,
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
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong')
);

-- Index for spatial queries
CREATE INDEX IF NOT EXISTS idx_pedestrian_network_shape_3d ON pedestrian_network USING GIST (shape gist_geometry_ops_nd);

-- Trigger to automatically calculate shape_len
CREATE TRIGGER trg_calculate_pedestrian_len
BEFORE INSERT OR UPDATE ON pedestrian_network
FOR EACH ROW
EXECUTE FUNCTION update_shape_len();

-- 1. Create Pedestrian History Table
CREATE TABLE IF NOT EXISTS pedestrian_network_history (
    history_id SERIAL PRIMARY KEY,
    pedrouteid INTEGER, -- Reference to original, not PK
    operation TEXT, -- 'UPDATE' or 'DELETE'
    history_recorded_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    
    -- Original columns
    crtdt TEXT,
    lstamddt TEXT,
    shape GEOMETRY(LineStringZ, 2326),
    feattype INTEGER,
    floorid INTEGER,
    location INTEGER,
    gradient DOUBLE PRECISION,
    wc_access INTEGER,
    wc_barrier INTEGER,
    wx_proof INTEGER,
    obstype INTEGER,
    direction INTEGER,
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
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_history_pedrouteid ON pedestrian_network_history(pedrouteid);

-- 2. Create Trigger Function for History Logging
CREATE OR REPLACE FUNCTION log_pedestrian_network_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        IF NEW IS NOT DISTINCT FROM OLD THEN
            RETURN NULL;
        END IF;

        INSERT INTO pedestrian_network_history (
            pedrouteid, operation,
            crtdt, lstamddt, shape, feattype, floorid, location, 
            gradient, wc_access, wc_barrier, wx_proof, obstype, direction, 
            bldgid_1, bldgid_2, siteid, aliasnamtc, aliasnamen, terminalid, 
            acstimeid, crossfeat, st_code, st_nametc, st_nameen, modifiedby, 
            poscertain, datasrc, levelsrc, enabled, shape_len, 
            created_at, updated_at
        )
        VALUES (
            OLD.pedrouteid, 'UPDATE',
            OLD.crtdt, OLD.lstamddt, OLD.shape, OLD.feattype, OLD.floorid, OLD.location, 
            OLD.gradient, OLD.wc_access, OLD.wc_barrier, OLD.wx_proof, OLD.obstype, OLD.direction, 
            OLD.bldgid_1, OLD.bldgid_2, OLD.siteid, OLD.aliasnamtc, OLD.aliasnamen, OLD.terminalid, 
            OLD.acstimeid, OLD.crossfeat, OLD.st_code, OLD.st_nametc, OLD.st_nameen, OLD.modifiedby, 
            OLD.poscertain, OLD.datasrc, OLD.levelsrc, OLD.enabled, OLD.shape_len, 
            OLD.created_at, OLD.updated_at
        );
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO pedestrian_network_history (
            pedrouteid, operation,
            crtdt, lstamddt, shape, feattype, floorid, location, 
            gradient, wc_access, wc_barrier, wx_proof, obstype, direction, 
            bldgid_1, bldgid_2, siteid, aliasnamtc, aliasnamen, terminalid, 
            acstimeid, crossfeat, st_code, st_nametc, st_nameen, modifiedby, 
            poscertain, datasrc, levelsrc, enabled, shape_len, 
            created_at, updated_at
        )
        VALUES (
            OLD.pedrouteid, 'DELETE',
            OLD.crtdt, OLD.lstamddt, OLD.shape, OLD.feattype, OLD.floorid, OLD.location, 
            OLD.gradient, OLD.wc_access, OLD.wc_barrier, OLD.wx_proof, OLD.obstype, OLD.direction, 
            OLD.bldgid_1, OLD.bldgid_2, OLD.siteid, OLD.aliasnamtc, OLD.aliasnamen, OLD.terminalid, 
            OLD.acstimeid, OLD.crossfeat, OLD.st_code, OLD.st_nametc, OLD.st_nameen, OLD.modifiedby, 
            OLD.poscertain, OLD.datasrc, OLD.levelsrc, OLD.enabled, OLD.shape_len, 
            OLD.created_at, OLD.updated_at
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 3. Validation: Function to update timestamp (Reuse generic if available, else create specific)
-- We assume set_updated_at() exists from network_table_list.sql, but for completeness in this script:
CREATE OR REPLACE FUNCTION set_pedestrian_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (NOW() AT TIME ZONE 'Asia/Hong_Kong');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Attach Triggers
---What it does: This tells the database to "listen" every time someone tries to Modify (UPDATE) or Remove (DELETE) a row in the pedestrian_network table.
---The Action: Before the change happens (BEFORE), it runs the function log_pedestrian_network_changes().
---The Result: That function takes a snapshot of the row exactly as it was before the change and saves it into your pedestrian_network_history table.
--- Why you need it: If someone updates a route by mistake or deletes good data, you have a permanent backup in the history table showing exactly what the data looked like before the accident.
DROP TRIGGER IF EXISTS trg_pedestrian_network_history ON pedestrian_network;
CREATE TRIGGER trg_pedestrian_network_history
BEFORE UPDATE OR DELETE ON pedestrian_network
FOR EACH ROW EXECUTE FUNCTION log_pedestrian_network_changes();


---What it does: This listens specifically for Updates to existing rows.
---The Action: It runs the function set_pedestrian_updated_at().
---The Result: It automatically changes the updated_at column to the current time (NOW()).
---Why you need it: You don't have to manually update the date in your code every time you save a record. The database ensures that the updated_at field is always 100% accurate, showing the exact moment the last change occurred.
DROP TRIGGER IF EXISTS trg_set_pedestrian_updated_at ON pedestrian_network;
CREATE TRIGGER trg_set_pedestrian_updated_at
BEFORE UPDATE ON pedestrian_network
FOR EACH ROW EXECUTE FUNCTION set_pedestrian_updated_at();
