-- ## Migration to create squence osm id starting from 30000
-- Start a transaction
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'osm_id_seq') THEN
        CREATE SEQUENCE osm_id_seq START 30000;
    END IF;
END
$$;