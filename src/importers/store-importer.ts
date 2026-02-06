import fs from "node:fs";
import { getPool } from "../db/connection.js";
import { UPSERT_STORE } from "../db/queries.js";

interface RawStore {
  store_id?: string;
  name?: string;
  store_type?: string;
  street_address?: string;
  city?: string;
  state?: string;
  zip?: string;
  latitude?: number;
  longitude?: number;
}

function isValidCoord(lat: number, lng: number): boolean {
  return lat >= 17 && lat <= 72 && lng >= -180 && lng <= -60;
}

export async function importStores(filePath: string): Promise<void> {
  const raw = fs.readFileSync(filePath, "utf-8");
  const stores: RawStore[] = JSON.parse(raw);

  console.log(`Read ${stores.length} stores from ${filePath}`);

  const pool = getPool();
  let imported = 0;
  let skipped = 0;

  // Batch in groups of 100
  const BATCH_SIZE = 100;
  for (let i = 0; i < stores.length; i += BATCH_SIZE) {
    const batch = stores.slice(i, i + BATCH_SIZE);
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      for (const s of batch) {
        if (!s.store_id || !s.name || s.latitude == null || s.longitude == null) {
          skipped++;
          continue;
        }
        if (!isValidCoord(s.latitude, s.longitude)) {
          skipped++;
          continue;
        }
        await client.query(UPSERT_STORE, [
          s.store_id,
          s.name,
          s.store_type ?? null,
          s.street_address ?? null,
          s.city ?? null,
          s.state ?? null,
          s.zip ?? null,
          s.latitude,
          s.longitude,
        ]);
        imported++;
      }
      await client.query("COMMIT");
    } catch (err) {
      await client.query("ROLLBACK");
      throw err;
    } finally {
      client.release();
    }

    if ((i + BATCH_SIZE) % 500 === 0 || i + BATCH_SIZE >= stores.length) {
      console.log(`  Progress: ${Math.min(i + BATCH_SIZE, stores.length)}/${stores.length}`);
    }
  }

  console.log(`Import complete: ${imported} imported, ${skipped} skipped`);
}
