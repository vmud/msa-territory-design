interface MsaFeature {
  cbsafp: string;
  name: string;
  store_count: number;
  geojson: string;
}

interface StorePoint {
  store_id: string;
  name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  msa_name: string | null;
}

export function buildHtml(msas: MsaFeature[], stores: StorePoint[]): string {
  // Build GeoJSON FeatureCollection for MSA polygons
  const msaFeatures = msas.map((m) => {
    const geometry = JSON.parse(m.geojson);
    return {
      type: "Feature" as const,
      properties: {
        cbsafp: m.cbsafp,
        name: m.name,
        store_count: m.store_count,
      },
      geometry,
    };
  });

  const msaCollection = {
    type: "FeatureCollection",
    features: msaFeatures,
  };

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Walmart Stores &times; MSA Boundaries</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    #map { width: 100vw; height: 100vh; }
    .info-panel {
      position: absolute; top: 10px; right: 10px; z-index: 1000;
      background: white; padding: 12px 16px; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family: system-ui, sans-serif;
      max-width: 320px;
    }
    .info-panel h3 { margin: 0 0 8px; font-size: 14px; color: #333; }
    .info-panel p { margin: 2px 0; font-size: 12px; color: #666; }
    .legend {
      position: absolute; bottom: 20px; left: 10px; z-index: 1000;
      background: white; padding: 10px 14px; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family: system-ui, sans-serif;
    }
    .legend-item { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 12px; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; }
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="info-panel" id="info">
    <h3>MSA Territory Map</h3>
    <p><strong>${stores.length.toLocaleString()}</strong> Walmart stores</p>
    <p><strong>${msas.length.toLocaleString()}</strong> Metropolitan Statistical Areas</p>
    <p id="hover-info" style="margin-top:8px; color:#333;"></p>
  </div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#0066cc;"></div> In MSA</div>
    <div class="legend-item"><div class="legend-dot" style="background:#cc3300;"></div> Outside MSA</div>
    <div class="legend-item"><div class="legend-dot" style="background:rgba(51,136,255,0.15); border:1px solid #3388ff;"></div> MSA boundary</div>
  </div>

  <script>
    const map = L.map('map').setView([39.5, -98.5], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    // MSA polygons
    const msaData = ${JSON.stringify(msaCollection)};

    const msaLayer = L.geoJSON(msaData, {
      style: {
        color: '#3388ff',
        weight: 1,
        fillColor: '#3388ff',
        fillOpacity: 0.08,
      },
      onEachFeature: function(feature, layer) {
        layer.on('mouseover', function(e) {
          e.target.setStyle({ fillOpacity: 0.25, weight: 2 });
          document.getElementById('hover-info').innerHTML =
            '<strong>' + feature.properties.name + '</strong><br/>' +
            feature.properties.store_count + ' stores in this MSA';
        });
        layer.on('mouseout', function(e) {
          msaLayer.resetStyle(e.target);
          document.getElementById('hover-info').innerHTML = '';
        });
      }
    }).addTo(map);

    // Store markers
    const storeData = ${JSON.stringify(stores)};

    storeData.forEach(function(s) {
      const inMsa = s.msa_name !== null;
      L.circleMarker([s.latitude, s.longitude], {
        radius: 4,
        color: inMsa ? '#0066cc' : '#cc3300',
        fillColor: inMsa ? '#0066cc' : '#cc3300',
        fillOpacity: 0.7,
        weight: 1,
      })
      .bindPopup(
        '<strong>' + s.name + '</strong><br/>' +
        s.city + ', ' + s.state + '<br/>' +
        (inMsa ? 'MSA: ' + s.msa_name : '<em>Outside MSA</em>')
      )
      .addTo(map);
    });
  </script>
</body>
</html>`;
}
