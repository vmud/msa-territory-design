import { execSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { config } from "../config.js";

function ensureDockerRunning(cwd: string): void {
  const result = spawnSync(
    "docker", ["compose", "ps", "--services", "--filter", "status=running"],
    { cwd, encoding: "utf-8" },
  );
  if (result.status !== 0 || !result.stdout.includes("db")) {
    throw new Error(
      "Docker container 'db' is not running.\nStart it with: docker compose up -d",
    );
  }
}

export async function downloadCbsa(): Promise<void> {
  const scriptPath = path.join(config.dataDir, "..", "scripts", "download-cbsa.sh");
  console.log("Running download script...");
  spawnSync("bash", [scriptPath], { stdio: "inherit" });
}

export async function loadMsa(download: boolean): Promise<void> {
  const shapeDir = path.join(config.dataDir, "shapefiles", "cbsa");
  const projectDir = path.join(config.dataDir, "..");

  if (download) {
    await downloadCbsa();
  }

  // Verify shapefile exists
  const shpFile = path.join(shapeDir, "tl_2024_us_cbsa.shp");
  if (!fs.existsSync(shpFile)) {
    throw new Error(
      `Shapefile not found at ${shpFile}\nRun with --download to fetch it, or place it manually.`,
    );
  }

  // Verify Docker container is running
  ensureDockerRunning(projectDir);

  console.log("Loading CBSA shapefile into PostGIS via shp2pgsql...");

  // shp2pgsql flags: -s 4326 (SRID), -d (drop+create), -I (create GiST index)
  // The shapefile is volume-mounted at /data/shapefiles/cbsa/ in the container

  // Step 1: Generate SQL from shapefile, then pipe to psql
  // Use two separate steps to detect shp2pgsql failures (pipeline hides exit codes)
  console.log("  Step 1/3: Loading shapefile into raw table...");

  const shp2pgsqlResult = spawnSync(
    "docker", [
      "compose", "exec", "-T", "db",
      "shp2pgsql", "-s", "4326", "-d", "-I",
      "/data/shapefiles/cbsa/tl_2024_us_cbsa.shp",
      "msa_boundaries_raw",
    ],
    { cwd: projectDir, maxBuffer: 200 * 1024 * 1024 },
  );

  if (shp2pgsqlResult.status !== 0) {
    const stderr = shp2pgsqlResult.stderr?.toString() ?? "";
    throw new Error(`shp2pgsql failed (exit ${shp2pgsqlResult.status}): ${stderr}`);
  }

  // Pipe the generated SQL into psql
  const psqlLoadResult = spawnSync(
    "docker", [
      "compose", "exec", "-T", "db",
      "psql", "-U", "postgres", "-d", "territory_db",
    ],
    { input: shp2pgsqlResult.stdout, cwd: projectDir, stdio: ["pipe", "pipe", "inherit"] },
  );

  if (psqlLoadResult.status !== 0) {
    throw new Error("psql failed to load shapefile SQL. Check PostGIS logs.");
  }

  console.log("  Step 2/3: Copying to schema table...");
  console.warn("  Note: This clears existing store-to-MSA assignments. Run 'assign-msa' after.");

  const migrateSql = `
    -- Clear FK references before truncate to avoid cascade surprises
    UPDATE stores SET msa_id = NULL, msa_name = NULL;

    -- Clear existing MSA data
    TRUNCATE msa_boundaries RESTART IDENTITY;

    -- Copy from raw table to schema table
    INSERT INTO msa_boundaries (cbsafp, name, namelsad, lsad, aland, awater, geom)
    SELECT cbsafp, name, namelsad, lsad, aland::bigint, awater::bigint, geom
    FROM msa_boundaries_raw;

    -- Drop raw table
    DROP TABLE IF EXISTS msa_boundaries_raw;
  `;

  // Pipe SQL via stdin (no shell interpolation — fixes shell injection)
  const psqlMigrateResult = spawnSync(
    "docker", [
      "compose", "exec", "-T", "db",
      "psql", "-U", "postgres", "-d", "territory_db",
    ],
    { input: migrateSql, cwd: projectDir, stdio: ["pipe", "pipe", "inherit"] },
  );

  if (psqlMigrateResult.status !== 0) {
    throw new Error("Migration SQL failed. Check PostGIS logs.");
  }

  console.log("  Step 3/3: Verifying...");
  const countResult = execSync(
    'docker compose exec -T db psql -U postgres -d territory_db -t -c "SELECT COUNT(*) FROM msa_boundaries;"',
    { cwd: projectDir },
  ).toString().trim();

  console.log(`MSA load complete: ${countResult} boundaries loaded`);
}
