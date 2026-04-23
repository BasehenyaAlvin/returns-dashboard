#!/usr/bin/env python3
"""
build.py — Auto-rebuilds the Jumia Returns Dashboard
Fetches latest data from Google Sheet and injects into index.html
Run manually or via GitHub Actions every day
"""

import csv, json, io, urllib.request, datetime, os, sys

# ════════════════════════════════════════════
# YOUR GOOGLE SHEET CSV URL — paste yours here
# ════════════════════════════════════════════
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXx7pWn3HvjECaTJAN68LH2-7wPBM6r-DtrIR6sFbhlZh_R-4Dk6skYXQjnwmwCPd84swN72TCIU-H/pub?gid=6794188&single=true&output=csv"

print("📥 Fetching data from Google Sheet...")

try:
    req = urllib.request.Request(SHEET_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_csv = resp.read().decode("utf-8-sig")
    print(f"✅ Fetched {len(raw_csv)//1024} KB of CSV data")
except Exception as e:
    print(f"❌ Failed to fetch sheet: {e}")
    sys.exit(1)

# ── PARSE CSV ──
reader = csv.DictReader(io.StringIO(raw_csv))
rows = list(reader)
print(f"📊 Parsed {len(rows)} rows")

# ── TRANSFORM TO COMPACT JSON ──
records = []
for r in rows:
    try:
        usd = float(r.get("COGP(USD)", "0").replace("$","").replace(",","").strip() or 0)
    except:
        usd = 0.0
    try:
        age = int(r.get("Age (Days)", "0") or 0)
    except:
        age = 0
    try:
        from datetime import datetime as dt
        wk = dt.strptime(r.get("Created At",""), "%m/%d/%Y").strftime("%Y-W%V")
    except:
        wk = ""

    records.append({
        "k":  r.get("KAM", "").strip(),
        "v":  r.get("Vendor Name", "").strip(),
        "b":  r.get("Brand", "").strip(),
        "s":  r.get("Sku", "").strip()[:20],
        "sr": r.get("Supplier Return Reason", "").strip(),
        "cr": r.get("Customer Return Reason", "").strip()[:35],
        "sc": r.get("SC Verdict", "").strip(),
        "pt": r.get("PO Type", "").strip(),
        "u":  round(usd, 2),
        "a":  age,
        "w":  wk,
    })

data_json = json.dumps(records, separators=(",",":"))
print(f"✅ Built JSON: {len(data_json)//1024} KB, {len(records)} records")

# ── READ TEMPLATE ──
template_path = os.path.join(os.path.dirname(__file__), "template.html")
if not os.path.exists(template_path):
    print("❌ template.html not found!")
    sys.exit(1)

with open(template_path, "r", encoding="utf-8") as f:
    template = f.read()

# ── INJECT DATA ──
marker_start = "/*__DATA_START__*/"
marker_end   = "/*__DATA_END__*/"

if marker_start not in template:
    print("❌ Data markers not found in template.html!")
    sys.exit(1)

start_idx = template.find(marker_start) + len(marker_start)
end_idx   = template.find(marker_end)
new_html  = template[:start_idx] + data_json + template[end_idx:]

# ── UPDATE LAST-UPDATED TEXT ──
now = datetime.datetime.utcnow().strftime("%B %d, %Y · %I:%M %p UTC")
new_html = new_html.replace("{{LAST_UPDATED}}", now)

# ── WRITE OUTPUT ──
out_path = os.path.join(os.path.dirname(__file__), "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(new_html)

print(f"✅ index.html written ({len(new_html)//1024} KB)")
print(f"🕒 Last updated: {now}")
print("🚀 Dashboard is ready!")
