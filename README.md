# MSA Territory Design POC

PostGIS spatial analysis for retail store territory mapping. Loads Walmart store locations and US Census MSA (Metropolitan Statistical Area) boundaries into PostGIS, assigns stores to MSAs via spatial join, and generates an interactive Leaflet map.

## Quick Start

```bash
# Prerequisites: Docker, Node.js 20+
npm install
docker compose up -d

# Load MSA boundaries (downloads ~500 MB shapefile)
npx tsx src/index.ts load-msa --download

# Import Walmart stores
npx tsx src/index.ts import-stores --file ./data/input/stores_latest.json

# Assign stores to MSAs
npx tsx src/index.ts assign-msa

# Check status
npx tsx src/index.ts status

# Generate map
npx tsx src/index.ts export-map

# Serve map (accessible from any browser on the network)
npx tsx src/index.ts serve --port 3000
```

## Data Sources

- **Walmart stores**: JSON from retail-store-scraper project
- **MSA boundaries**: Census TIGER/Line 2024 CBSA shapefile

## Tech Stack

- Node.js / TypeScript
- PostgreSQL 16 + PostGIS 3.4 (Docker)
- Leaflet (CDN, self-contained HTML output)
- commander.js (CLI)
- node-postgres (`pg`)
