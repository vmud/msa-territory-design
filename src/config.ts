import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, "..");

dotenv.config({ path: path.join(PROJECT_ROOT, ".env") });

export const config = {
  // Use DATABASE_URL if set, otherwise build from individual PG* vars.
  // Individual params avoid URL-encoding issues with special chars in passwords.
  databaseUrl: process.env.DATABASE_URL ?? undefined,
  dbConfig: {
    user: process.env.PGUSER ?? "postgres",
    password: process.env.PGPASSWORD ?? "postgres",
    host: process.env.PGHOST ?? "localhost",
    port: parseInt(process.env.PGPORT ?? "5432", 10),
    database: process.env.PGDATABASE ?? "territory_db",
  },
  dataDir: path.join(PROJECT_ROOT, "data"),
  outputDir: path.join(PROJECT_ROOT, "output"),
};
