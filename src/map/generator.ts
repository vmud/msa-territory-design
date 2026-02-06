import fs from "node:fs";
import path from "node:path";
import { getPool } from "../db/connection.js";
import { MSA_GEOJSON, STORE_POINTS } from "../db/queries.js";
import { config } from "../config.js";
import { buildHtml } from "./template.js";

export async function exportMap(outputPath?: string): Promise<string> {
  const pool = getPool();

  console.log("Querying MSA boundaries (simplified)...");
  const msaResult = await pool.query(MSA_GEOJSON);
  console.log(`  ${msaResult.rows.length} MSA polygons`);

  console.log("Querying store locations...");
  const storeResult = await pool.query(STORE_POINTS);
  console.log(`  ${storeResult.rows.length} stores`);

  const msas = msaResult.rows.map((r) => ({
    cbsafp: r.cbsafp,
    name: r.name,
    store_count: Number(r.store_count),
    geojson: r.geojson,
  }));

  const stores = storeResult.rows.map((r) => ({
    store_id: r.store_id,
    name: r.name,
    city: r.city,
    state: r.state,
    latitude: Number(r.latitude),
    longitude: Number(r.longitude),
    msa_name: r.msa_name,
  }));

  const html = buildHtml(msas, stores);

  const dest = outputPath ?? path.join(config.outputDir, "store-msa-map.html");
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, html, "utf-8");

  const sizeMb = (Buffer.byteLength(html) / 1024 / 1024).toFixed(1);
  console.log(`Map written to ${dest} (${sizeMb} MB)`);

  return dest;
}
