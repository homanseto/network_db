-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-------------------------------------------------------------------------------
-- Venue Table
-------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS venue (
    -- Identification
    id TEXT PRIMARY KEY,                    -- Properties.id as Primary Key
    -- Properties
    category TEXT ,
    restriction TEXT,
    name_en TEXT NOT NULL,
    name_zh TEXT,
    alt_name TEXT,
    hours TEXT,
    website TEXT,
    phone TEXT,
    address_id TEXT NOT NULL,
    organization_id TEXT,
    
    -- Additional Metadata
    building_type TEXT[],                           -- Array for buildingType e.g. ["EDB"]
    region TEXT,                                    -- e.g. "KLNE"
    displayname TEXT,                              -- e.g. "KLNE_45_..."

    -- Geometry Columns (SRID 2326 2D) - Accepts both Polygon and MultiPolygon
    shape GEOMETRY(Geometry, 2326),
    display_point GEOMETRY(Point, 2326),

    -- Audit Timestamps (Using HK Time Zone)
    created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),
    updated_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Hong_Kong'),

    -- Constraint to allow only Polygon or MultiPolygon
    CONSTRAINT enforce_dims_shape CHECK (ST_NDims(shape) = 2),
    CONSTRAINT enforce_geotype_shape CHECK (GeometryType(shape) IN ('POLYGON', 'MULTIPOLYGON'))
);

-- Index on Geometry (2D Spatial Indexing)
CREATE INDEX IF NOT EXISTS idx_venue_shape ON venue USING GIST (shape);
CREATE INDEX IF NOT EXISTS idx_venue_display_point ON venue USING GIST (display_point);

-------------------------------------------------------------------------------
-- Trigger: Auto-Update Timestamp
-------------------------------------------------------------------------------
-- Reusing the function if it exists, or creating a specific one for venue if needed.
-- Assuming 'set_updated_at' exists from network_table_list.sql, but defining here for safety.

CREATE OR REPLACE FUNCTION set_venue_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (NOW() AT TIME ZONE 'Asia/Hong_Kong');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_venue_updated_at ON venue;
CREATE TRIGGER trg_set_venue_updated_at
BEFORE UPDATE ON venue
FOR EACH ROW EXECUTE FUNCTION set_venue_updated_at();
