import pg from "pg";
import { config } from "../config.js";

let pool: pg.Pool | null = null;

export function getPool(): pg.Pool {
  if (!pool) {
    const poolConfig = config.databaseUrl
      ? { connectionString: config.databaseUrl }
      : config.dbConfig;
    pool = new pg.Pool(poolConfig);
    pool.on("error", (err) => {
      console.error("Unexpected database pool error:", err.message);
    });
  }
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
