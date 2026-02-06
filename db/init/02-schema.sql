-- MSA Boundaries (loaded from Census TIGER/Line CBSA shapefile via shp2pgsql)
CREATE TABLE IF NOT EXISTS msa_boundaries (
    gid         SERIAL PRIMARY KEY,
    cbsafp      VARCHAR(5) NOT NULL,
    name        VARCHAR(100) NOT NULL,
    namelsad    VARCHAR(100),
    lsad        VARCHAR(2) NOT NULL,
    aland       BIGINT,
    awater      BIGINT,
    geom        GEOMETRY(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_msa_geom ON msa_boundaries USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_msa_lsad ON msa_boundaries (lsad);

-- Walmart Stores (imported from scraper JSON)
CREATE TABLE IF NOT EXISTS stores (
    id              SERIAL PRIMARY KEY,
    store_id        VARCHAR(10) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    store_type      VARCHAR(50),
    street_address  VARCHAR(300),
    city            VARCHAR(100),
    state           VARCHAR(2),
    zip             VARCHAR(10),
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    location        GEOMETRY(Point, 4326) NOT NULL,
    msa_id          INTEGER REFERENCES msa_boundaries(gid),
    msa_name        VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_stores_location ON stores USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_stores_msa ON stores (msa_id);
