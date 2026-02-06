import { getPool } from "../db/connection.js";
import { ASSIGN_MSA, CLEAR_MSA_ASSIGNMENTS } from "../db/queries.js";

export async function assignMsa(): Promise<void> {
  const pool = getPool();

  console.log("Clearing existing MSA assignments...");
  await pool.query(CLEAR_MSA_ASSIGNMENTS);

  console.log("Running spatial join (ST_Contains) to assign stores to MSAs...");
  const start = Date.now();
  const result = await pool.query(ASSIGN_MSA);
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);

  console.log(`Assignment complete: ${result.rowCount} stores matched to MSAs (${elapsed}s)`);
}
