export const UPSERT_STORE = `
  INSERT INTO stores (store_id, name, store_type, street_address, city, state, zip, latitude, longitude, location)
  VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, ST_SetSRID(ST_MakePoint($9, $8), 4326))
  ON CONFLICT (store_id) DO UPDATE SET
    name = EXCLUDED.name,
    store_type = EXCLUDED.store_type,
    street_address = EXCLUDED.street_address,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    zip = EXCLUDED.zip,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    location = EXCLUDED.location;
`;

export const ASSIGN_MSA = `
  UPDATE stores s
  SET msa_id = m.gid, msa_name = m.name
  FROM msa_boundaries m
  WHERE ST_Contains(m.geom, s.location) AND m.lsad = 'M1';
`;

export const CLEAR_MSA_ASSIGNMENTS = `
  UPDATE stores SET msa_id = NULL, msa_name = NULL;
`;

export const STATUS_QUERY = `
  SELECT
    (SELECT COUNT(*) FROM stores) AS total_stores,
    (SELECT COUNT(*) FROM stores WHERE msa_id IS NOT NULL) AS assigned_stores,
    (SELECT COUNT(*) FROM stores WHERE msa_id IS NULL) AS unassigned_stores,
    (SELECT COUNT(*) FROM msa_boundaries) AS total_msas,
    (SELECT COUNT(*) FROM msa_boundaries WHERE lsad = 'M1') AS metropolitan_msas,
    (SELECT COUNT(*) FROM msa_boundaries WHERE lsad = 'M2') AS micropolitan_msas;
`;

export const MSA_GEOJSON = `
  SELECT m.cbsafp, m.name, COUNT(s.store_id) AS store_count,
         ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geom, 0.01)) AS geojson
  FROM msa_boundaries m
  LEFT JOIN stores s ON s.msa_id = m.gid
  WHERE m.lsad = 'M1'
  GROUP BY m.gid, m.cbsafp, m.name, m.geom;
`;

export const STORE_POINTS = `
  SELECT store_id, name, city, state, latitude, longitude, msa_name
  FROM stores;
`;
