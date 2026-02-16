CREATE OR REPLACE FUNCTION snap_indoor_exits_to_pedestrian(
    snap_tolerance_2d DOUBLE PRECISION DEFAULT 2.0, -- Max 2 meters distance
    snap_tolerance_z  DOUBLE PRECISION DEFAULT 5.0  -- Max 5 meters height diff
)
RETURNS TABLE (
    match_count INT,
    updated_ids INT[]
) AS $$
DECLARE
    r RECORD;
    closest_ped_point GEOMETRY;
    exit_start_point GEOMETRY;
    exit_end_point GEOMETRY;
    dist_start DOUBLE PRECISION;
    dist_end DOUBLE PRECISION;
    target_point GEOMETRY;
    point_to_move TEXT; -- 'START' or 'END'
    updated_list INT[] := '{}';
BEGIN
    -- Loop through all indoor lines marked as mainexit
    FOR r IN 
        SELECT pedrouteid, shape 
        FROM indoor_network_test 
        WHERE mainexit = true
    LOOP
        -- 1. Get Endpoints of the indoor line
        exit_start_point := ST_StartPoint(r.shape);
        exit_end_point   := ST_EndPoint(r.shape);

        -- 2. Find the CLOSET Endpoint (Start or End) from the entire pedestrian network
        --    We look for the single closest node from the pedestrian network to EITHER end of the indoor line
        
        SELECT 
            candidate_point, 
            ST_3DDistance(source_point, candidate_point) as dist_3d
        INTO closest_ped_point, dist_start
        FROM (
            -- Candidate 1: Start points of pedestrian lines
            SELECT ST_StartPoint(shape) as candidate_point FROM pedestrian_network
            UNION ALL
            -- Candidate 2: End points of pedestrian lines
            SELECT ST_EndPoint(shape) as candidate_point FROM pedestrian_network
        ) pts,
        (SELECT exit_start_point as source_point) src
        -- Optimization: only check points within tolerance
        WHERE ST_DWithin(candidate_point, src.source_point, snap_tolerance_2d)
        ORDER BY ST_3DDistance(candidate_point, src.source_point) ASC
        LIMIT 1;

        -- Check the other end of the indoor line
        SELECT 
            candidate_point, 
            ST_3DDistance(source_point, candidate_point) as dist_3d
        INTO target_point, dist_end -- temporary reuse of variables
        FROM (
            SELECT ST_StartPoint(shape) as candidate_point FROM pedestrian_network
            UNION ALL
            SELECT ST_EndPoint(shape) as candidate_point FROM pedestrian_network
        ) pts,
        (SELECT exit_end_point as source_point) src
        WHERE ST_DWithin(candidate_point, src.source_point, snap_tolerance_2d)
        ORDER BY ST_3DDistance(candidate_point, src.source_point) ASC
        LIMIT 1;

        -- 3. Determine which end to move (if any)
        point_to_move := NULL;
        
        -- Logic: Move the end that is CLOSEST to a pedestrian node, provided it is within tolerance
        IF dist_start IS NOT NULL AND (dist_end IS NULL OR dist_start < dist_end) THEN
             -- Start point is the winner
             target_point := closest_ped_point;
             point_to_move := 'START';
        ELSIF dist_end IS NOT NULL THEN
             -- End point is the winner
             target_point := target_point; -- already set in the second query
             point_to_move := 'END';
        END IF;

        -- 4. Update the Geometry if a move is required
        IF point_to_move IS NOT NULL THEN
            -- Check Z tolerance specifically if needed, though ST_3DDistance covers it implicitly
            -- If you want strict Z tolerance (e.g. max 5m vertical diff even if horizontal is 0):
            IF ABS(ST_Z(target_point) - ST_Z(
                CASE WHEN point_to_move = 'START' THEN exit_start_point ELSE exit_end_point END
            )) <= snap_tolerance_z THEN
                
                UPDATE indoor_network_test
                SET shape = ST_SetPoint(shape, 
                    CASE WHEN point_to_move = 'START' THEN 0 ELSE ST_NumPoints(shape) - 1 END, 
                    target_point
                )
                WHERE pedrouteid = r.pedrouteid;

                updated_list := array_append(updated_list, r.pedrouteid);
            END IF;
        END IF;

    END LOOP;

    RETURN QUERY SELECT array_length(updated_list, 1), updated_list;
END;
$$ LANGUAGE plpgsql;