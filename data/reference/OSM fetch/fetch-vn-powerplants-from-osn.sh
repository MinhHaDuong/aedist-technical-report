#!/usr/bin/env bash
set -euo pipefail

read -r -d '' QUERY <<'EOF' || true
[out:json][timeout:300];
area["ISO3166-1"="VN"][admin_level=2]->.vn;
(
  node["power"="plant"](area.vn);
  way["power"="plant"](area.vn);
  relation["power"="plant"](area.vn);
);
out center tags;
EOF

curl -s 'https://overpass.kumi.systems/api/interpreter' \
  --data-urlencode "data=$QUERY" -o vn.json

jq -e . vn.json >/dev/null \
&& jq -r '
  ["name","source","capacity","lat","lon"],
  (.elements[] | [
     .tags.name // "",
     .tags["plant:source"] // "",
     .tags["plant:output:electricity"] // "",
     (.lat // .center.lat),
     (.lon // .center.lon)
  ])
  | @csv
' vn.json > vn_power_plants.csv
