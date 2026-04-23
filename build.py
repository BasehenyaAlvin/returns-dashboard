#!/usr/bin/env python3
"""
Jumia Returns Dashboard — Auto Builder
Fetches Google Sheet, rebuilds dashboard, sends email + chat notifications
"""

import csv, io, json, os, sys, smtplib, urllib.request, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ════════════════════════════════════════════════════
# CONFIG — all values come from GitHub Secrets
# ════════════════════════════════════════════════════
SHEET_URL      = os.environ.get("https://docs.google.com/spreadsheets/d/e/2PACX-1vQXx7pWn3HvjECaTJAN68LH2-7wPBM6r-DtrIR6sFbhlZh_R-4Dk6skYXQjnwmwCPd84swN72TCIU-H/pub?gid=6794188&single=true&output=csv", "")
EMAIL_ENABLED  = True
EMAIL_FROM     = os.environ.get("EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_TO       = [e.strip() for e in os.environ.get("EMAIL_TO", "").split(",") if e.strip()]
EMAIL_SUBJECT  = "📊 Jumia Returns Dashboard Updated"
CHAT_ENABLED   = bool(os.environ.get("CHAT_WEBHOOK", ""))
CHAT_WEBHOOK   = os.environ.get("CHAT_WEBHOOK", "")
DASHBOARD_URL  = os.environ.get("DASHBOARD_URL", "https://returns-shipped.netlify.app/")

# ════════════════════════════════════════════════════
# STEP 1 — FETCH GOOGLE SHEET
# ════════════════════════════════════════════════════
print("=" * 50)
print("📥 Fetching data from Google Sheet...")

if not SHEET_URL:
    print("❌ ERROR: SHEET_URL secret is not set in GitHub Secrets!")
    print("   Go to: repo → Settings → Secrets → Actions → New secret")
    print("   Name: SHEET_URL  |  Value: your Google Sheet CSV URL")
    sys.exit(1)

try:
    req = urllib.request.Request(
        SHEET_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Dashboard-Bot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_csv = resp.read().decode("utf-8-sig")
    print(f"✅ Sheet fetched successfully — {len(raw_csv)//1024} KB")
except Exception as e:
    print(f"❌ ERROR: Could not fetch Google Sheet: {e}")
    print("   Make sure your sheet is published as CSV and publicly accessible.")
    sys.exit(1)

# ════════════════════════════════════════════════════
# STEP 2 — PARSE CSV INTO RECORDS
# ════════════════════════════════════════════════════
print("📊 Parsing CSV data...")

try:
    reader = csv.DictReader(io.StringIO(raw_csv))
    rows = list(reader)
    if not rows:
        print("❌ ERROR: Sheet appears to be empty!")
        sys.exit(1)
    print(f"✅ Found {len(rows)} rows with columns: {list(rows[0].keys())[:5]}...")
except Exception as e:
    print(f"❌ ERROR: Could not parse CSV: {e}")
    sys.exit(1)

records = []
for r in rows:
    try:
        usd = float(r.get("COGP(USD)", "0").replace("$", "").replace(",", "").strip() or 0)
    except:
        usd = 0.0
    try:
        age = int(r.get("Age (Days)", "0") or 0)
    except:
        age = 0
    try:
        wk = datetime.datetime.strptime(r.get("Created At", ""), "%m/%d/%Y").strftime("%Y-W%V")
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

print(f"✅ Parsed {len(records)} records successfully")

# ════════════════════════════════════════════════════
# STEP 3 — BUILD DASHBOARD HTML
# ════════════════════════════════════════════════════
print("🔨 Rebuilding dashboard...")

if not os.path.exists("template.html"):
    print("❌ ERROR: template.html not found in repo!")
    sys.exit(1)

with open("template.html", "r", encoding="utf-8") as f:
    template = f.read()

marker_start = "/*__DATA_START__*/"
marker_end   = "/*__DATA_END__*/"

if marker_start not in template or marker_end not in template:
    print("❌ ERROR: Data markers not found in template.html!")
    sys.exit(1)

data_json = json.dumps(records, separators=(",", ":"))
now = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y · %I:%M %p UTC")

start_idx = template.find(marker_start) + len(marker_start)
end_idx   = template.find(marker_end)
new_html  = template[:start_idx] + data_json + template[end_idx:]
new_html  = new_html.replace("{{LAST_UPDATED}}", now)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(new_html)

print(f"✅ index.html rebuilt — {len(new_html)//1024} KB")

# ════════════════════════════════════════════════════
# QUICK STATS FOR NOTIFICATIONS
# ════════════════════════════════════════════════════
total_returns = len(records)
total_cogp    = sum(r["u"] for r in records)
high_risk     = sum(1 for r in records if r["a"] > 21)
week_label    = datetime.datetime.now().strftime("Week %V, %Y")

print(f"📊 Stats: {total_returns} returns | ${total_cogp:,.0f} COGP | {high_risk} high risk")

# ════════════════════════════════════════════════════
# STEP 4 — SEND EMAIL
# ════════════════════════════════════════════════════
if EMAIL_ENABLED and EMAIL_FROM and EMAIL_PASSWORD and EMAIL_TO:
    print(f"📧 Sending email to {EMAIL_TO}...")
    try:
        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#f97316;padding:24px;border-radius:12px 12px 0 0;text-align:center">
            <h1 style="color:white;margin:0;font-size:22px">📊 Jumia Returns Dashboard</h1>
            <p style="color:#ffe0c8;margin:8px 0 0;font-size:14px">{week_label} — Automated Update</p>
          </div>
          <div style="background:#f9f9f9;padding:28px;border-radius:0 0 12px 12px;border:1px solid #eee">
            <p style="color:#444;font-size:15px;margin-top:0">
              Your returns dashboard has been updated with the latest data from Google Sheets.
            </p>
            <div style="display:flex;gap:12px;margin:20px 0;flex-wrap:wrap">
              <div style="background:white;border:2px solid #f97316;border-radius:10px;padding:18px;flex:1;min-width:120px;text-align:center">
                <div style="font-size:30px;font-weight:bold;color:#f97316">{total_returns:,}</div>
                <div style="color:#888;font-size:13px;margin-top:4px">Total Returns</div>
              </div>
              <div style="background:white;border:2px solid #22c55e;border-radius:10px;padding:18px;flex:1;min-width:120px;text-align:center">
                <div style="font-size:30px;font-weight:bold;color:#22c55e">${total_cogp:,.0f}</div>
                <div style="color:#888;font-size:13px;margin-top:4px">Total COGP (USD)</div>
              </div>
              <div style="background:white;border:2px solid #f43f5e;border-radius:10px;padding:18px;flex:1;min-width:120px;text-align:center">
                <div style="font-size:30px;font-weight:bold;color:#f43f5e">{high_risk:,}</div>
                <div style="color:#888;font-size:13px;margin-top:4px">🔴 High Risk (21+ days)</div>
              </div>
            </div>
            <div style="text-align:center;margin:28px 0 20px">
              <a href="{DASHBOARD_URL}"
                 style="background:#f97316;color:white;padding:14px 36px;border-radius:8px;
                        text-decoration:none;font-weight:bold;font-size:16px;display:inline-block">
                Open Live Dashboard →
              </a>
            </div>
            <p style="color:#bbb;font-size:11px;text-align:center;margin:0">
              Updated: {now} · Auto-generated by GitHub Actions
            </p>
          </div>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{EMAIL_SUBJECT} — {week_label}"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = ", ".join(EMAIL_TO)
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print(f"✅ Email sent successfully to {EMAIL_TO}")
    except Exception as e:
        print(f"⚠️  Email failed (non-fatal): {e}")
else:
    print("⏭️  Email skipped — secrets not configured")

# ════════════════════════════════════════════════════
# STEP 5 — SEND GOOGLE CHAT NOTIFICATION
# ════════════════════════════════════════════════════
if CHAT_ENABLED and CHAT_WEBHOOK:
    print("💬 Sending Google Chat notification...")
    try:
        message = {
            "cards": [{
                "header": {
                    "title": "📊 Jumia Returns Dashboard Updated",
                    "subtitle": week_label
                },
                "sections": [{
                    "widgets": [
                        {"keyValue": {"topLabel": "Total Returns",        "content": f"{total_returns:,}"}},
                        {"keyValue": {"topLabel": "Total COGP (USD)",     "content": f"${total_cogp:,.0f}"}},
                        {"keyValue": {"topLabel": "🔴 High Risk (21+ d)", "content": f"{high_risk:,} returns need action!"}},
                        {"keyValue": {"topLabel": "Last Updated",         "content": now}},
                    ]
                }, {
                    "widgets": [{
                        "buttons": [{"textButton": {
                            "text": "OPEN DASHBOARD",
                            "onClick": {"openLink": {"url": DASHBOARD_URL}}
                        }}]
                    }]
                }]
            }]
        }
        data = json.dumps(message).encode("utf-8")
        req  = urllib.request.Request(
            CHAT_WEBHOOK, data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"✅ Google Chat notification sent (HTTP {resp.status})")
    except Exception as e:
        print(f"⚠️  Chat notification failed (non-fatal): {e}")
else:
    print("⏭️  Chat skipped — CHAT_WEBHOOK secret not set")

# ════════════════════════════════════════════════════
print("=" * 50)
print("🚀 Build complete! Dashboard is ready.")
print("=" * 50)
