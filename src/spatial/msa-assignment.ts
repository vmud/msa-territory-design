import { getPool } from "../db/connection.js";
import { ASSIGN_MSA, CLEAR_MSA_ASSIGNMENTS } from "../db/queries.js";

export async function assignMsa(): Promise<void> {
  const pool = getPool();
  const client = await pool.connect();

  try {
    await client.query("BEGIN");

    console.log("Clearing existing MSA assignments...");
    await client.query(CLEAR_MSA_ASSIGNMENTS);

    console.log("Running spatial join (ST_Contains) to assign stores to Metropolitan MSAs...");
    console.log("  Note: Only Metropolitan (M1) areas are used. Micropolitan (M2) stores show as 'Outside MSA'.");
    const start = Date.now();
    const result = await client.query(ASSIGN_MSA);
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);

    await client.query("COMMIT");
    console.log(`Assignment complete: ${result.rowCount} stores matched to MSAs (${elapsed}s)`);
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
