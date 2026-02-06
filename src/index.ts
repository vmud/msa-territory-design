#!/usr/bin/env node
import { Command } from "commander";
import { closePool, getPool } from "./db/connection.js";
import { loadMsa } from "./importers/msa-loader.js";
import { importStores } from "./importers/store-importer.js";
import { assignMsa } from "./spatial/msa-assignment.js";
import { exportMap } from "./map/generator.js";
import { STATUS_QUERY } from "./db/queries.js";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { config } from "./config.js";

const program = new Command();

program
  .name("territory-design")
  .description("MSA Territory Design - PostGIS spatial analysis for retail store territory mapping")
  .version("0.1.0");

program
  .command("load-msa")
  .description("Load Census CBSA shapefile into PostGIS")
  .option("--download", "Download shapefile first")
  .action(async (opts) => {
    try {
      await loadMsa(opts.download ?? false);
    } finally {
      await closePool();
    }
  });

program
  .command("import-stores")
  .description("Import Walmart store JSON into PostGIS")
  .requiredOption("--file <path>", "Path to stores JSON file")
  .action(async (opts) => {
    try {
      await importStores(opts.file);
    } finally {
      await closePool();
    }
  });

program
  .command("assign-msa")
  .description("Run ST_Contains spatial join to assign stores to MSAs")
  .action(async () => {
    try {
      await assignMsa();
    } finally {
      await closePool();
    }
  });

program
  .command("export-map")
  .description("Generate static HTML map from PostGIS data")
  .option("--output <path>", "Output file path", "./output/store-msa-map.html")
  .action(async (opts) => {
    try {
      await exportMap(opts.output);
    } finally {
      await closePool();
    }
  });

program
  .command("serve")
  .description("Start HTTP server for map output")
  .option("--port <n>", "Port number", "3000")
  .action((opts) => {
    const port = Number(opts.port);
    const outputDir = config.outputDir;

    const server = http.createServer((req, res) => {
      const reqPath = req.url === "/" ? "/store-msa-map.html" : req.url!;
      const filePath = path.join(outputDir, reqPath);

      // Prevent path traversal
      if (!filePath.startsWith(outputDir)) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }

      if (!fs.existsSync(filePath)) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }

      const ext = path.extname(filePath);
      const contentType = ext === ".html" ? "text/html" : "application/octet-stream";
      res.writeHead(200, { "Content-Type": contentType });
      fs.createReadStream(filePath).pipe(res);
    });

    server.listen(port, "0.0.0.0", () => {
      console.log(`Serving map at http://0.0.0.0:${port}/`);
      console.log(`Open http://<server-ip>:${port}/ from any browser on the network`);
      console.log("Press Ctrl+C to stop.");
    });
  });

program
  .command("status")
  .description("Show database counts and assignment status")
  .action(async () => {
    try {
      const pool = getPool();
      const result = await pool.query(STATUS_QUERY);
      const s = result.rows[0];

      console.log("\n  MSA Territory Design - Status");
      console.log("  ─────────────────────────────");
      console.log(`  Stores total:      ${Number(s.total_stores).toLocaleString()}`);
      console.log(`  Stores in MSA:     ${Number(s.assigned_stores).toLocaleString()}`);
      console.log(`  Stores outside:    ${Number(s.unassigned_stores).toLocaleString()}`);
      console.log(`  MSA boundaries:    ${Number(s.total_msas).toLocaleString()}`);
      console.log(`    Metropolitan:    ${Number(s.metropolitan_msas).toLocaleString()}`);
      console.log(`    Micropolitan:    ${Number(s.micropolitan_msas).toLocaleString()}`);
      console.log();
    } finally {
      await closePool();
    }
  });

program.parse();
