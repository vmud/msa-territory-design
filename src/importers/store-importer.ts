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

/** Validate coordinates are within US coverage (incl. Alaska, Hawaii, territories). */
function isValidUsCoord(lat: number, lng: number): boolean {
  return lat >= 17 && lat <= 72 && lng >= -180 && lng <= -60;
}

export async function importStores(filePath: string): Promise<void> {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Store file not found: ${filePath}`);
  }

  const raw = fs.readFileSync(filePath, "utf-8");
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`Invalid JSON: expected array, got ${typeof parsed}`);
  }
  const stores: RawStore[] = parsed;

  console.log(`Read ${stores.length} stores from ${filePath}`);

  const pool = getPool();
  let imported = 0;
  let skipped = 0;

  const BATCH_SIZE = 100;
  for (let i = 0; i < stores.length; i += BATCH_SIZE) {
    const batch = stores.slice(i, i + BATCH_SIZE);
    const client = await pool.connect();
    let batchImported = 0;
    try {
      await client.query("BEGIN");
      for (const s of batch) {
        if (!s.store_id || !s.name || s.latitude == null || s.longitude == null) {
          console.warn(`  Skipping store (missing fields): ${s.store_id ?? "unknown"}`);
          skipped++;
          continue;
        }
        if (!isValidUsCoord(s.latitude, s.longitude)) {
          console.warn(`  Skipping store ${s.store_id}: coords out of US range (${s.latitude}, ${s.longitude})`);
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
        batchImported++;
      }
      await client.query("COMMIT");
      imported += batchImported;
    } catch (err) {
      await client.query("ROLLBACK");
      console.error(`  Batch failed (stores ${i + 1}-${i + batch.length})`);
      throw err;
    } finally {
      client.release();
    }

    if (i % 500 === 0 || i + BATCH_SIZE >= stores.length) {
      console.log(`  Progress: ${Math.min(i + BATCH_SIZE, stores.length)}/${stores.length}`);
    }
  }

  console.log(`Import complete: ${imported} imported, ${skipped} skipped`);
}
