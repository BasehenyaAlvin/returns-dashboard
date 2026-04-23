# 📊 Jumia Returns Analytics Dashboard

Auto-updating returns analytics dashboard for Jumia Uganda.

## 🔄 How it auto-updates
Every day at 5:00 AM UTC, GitHub Actions:
1. Fetches the latest data from Google Sheets (CSV export)
2. Rebuilds `index.html` with fresh data  
3. Pushes the update — Netlify detects the change and redeploys

## 📁 Files
| File | Purpose |
|------|---------|
| `index.html` | The live dashboard (auto-generated, do not edit) |
| `template.html` | Dashboard template (edit layout/styling here) |
| `build.py` | Script that fetches data + rebuilds dashboard |
| `.github/workflows/update.yml` | GitHub Actions schedule |

## 🚀 Manual update
Go to **Actions** tab → **Auto-Update Dashboard** → **Run workflow**

## 📋 Data Source
Google Sheet: Return Shipped Status — KAM FOCUS
