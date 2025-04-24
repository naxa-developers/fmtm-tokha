DO $$
DECLARE
    seq_exists BOOLEAN;
    seq_start BIGINT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = 'osm_id_seq'
    ) INTO seq_exists;

    IF seq_exists THEN
        SELECT start_value INTO seq_start
        FROM pg_sequences
        WHERE schemaname = 'public' AND sequencename = 'osm_id_seq';

        IF seq_start = 30000 THEN
            ALTER SEQUENCE osm_id_seq RESTART WITH 12000;
        END IF;
    END IF;
END
$$;
