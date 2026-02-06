import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { config } from "../config.js";

export async function downloadCbsa(): Promise<void> {
  const scriptPath = path.join(config.dataDir, "..", "scripts", "download-cbsa.sh");
  console.log("Running download script...");
  execSync(`bash "${scriptPath}"`, { stdio: "inherit" });
}

export async function loadMsa(download: boolean): Promise<void> {
  const shapeDir = path.join(config.dataDir, "shapefiles", "cbsa");

  if (download) {
    await downloadCbsa();
  }

  // Verify shapefile exists
  const shpFile = path.join(shapeDir, "tl_2024_us_cbsa.shp");
  if (!fs.existsSync(shpFile)) {
    console.error(`Shapefile not found at ${shpFile}`);
    console.error("Run with --download to fetch it, or place it manually.");
    process.exit(1);
  }

  console.log("Loading CBSA shapefile into PostGIS via shp2pgsql...");

  // Drop existing data and reload
  // shp2pgsql flags: -s 4326 (SRID), -d (drop+create), -I (create GiST index)
  // The shapefile is volume-mounted at /data/shapefiles/cbsa/ in the container
  const shp2pgsqlCmd = [
    "docker", "compose", "exec", "-T", "db",
    "shp2pgsql", "-s", "4326", "-d", "-I",
    "/data/shapefiles/cbsa/tl_2024_us_cbsa.shp",
    "msa_boundaries_raw",
  ].join(" ");

  const psqlCmd = [
    "docker", "compose", "exec", "-T", "db",
    "psql", "-U", "postgres", "-d", "territory_db",
  ].join(" ");

  // shp2pgsql creates its own table structure, so we load into a raw table
  // then copy the columns we need into our schema table
  console.log("  Step 1/3: Loading shapefile into raw table...");
  execSync(`${shp2pgsqlCmd} | ${psqlCmd}`, {
    stdio: ["pipe", "pipe", "inherit"],
    cwd: path.join(config.dataDir, ".."),
  });

  console.log("  Step 2/3: Copying to schema table...");
  const migrateSql = `
    -- Clear existing data
    TRUNCATE msa_boundaries RESTART IDENTITY CASCADE;

    -- Copy from raw table to schema table
    INSERT INTO msa_boundaries (cbsafp, name, namelsad, lsad, aland, awater, geom)
    SELECT cbsafp, name, namelsad, lsad, aland::bigint, awater::bigint, geom
    FROM msa_boundaries_raw;

    -- Drop raw table
    DROP TABLE IF EXISTS msa_boundaries_raw;
  `;

  execSync(
    `echo ${JSON.stringify(migrateSql)} | ${psqlCmd}`,
    { stdio: ["pipe", "pipe", "inherit"], cwd: path.join(config.dataDir, "..") },
  );

  console.log("  Step 3/3: Verifying...");
  const countResult = execSync(
    `${psqlCmd} -t -c "SELECT COUNT(*) FROM msa_boundaries;"`,
    { cwd: path.join(config.dataDir, "..") },
  ).toString().trim();

  console.log(`MSA load complete: ${countResult} boundaries loaded`);
}
