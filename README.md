<div align="center">

<img src="https://ui-avatars.com/api/?name=TF&background=4A6CFA&color=fff&size=128" alt="T.F.N Logo" width="128" style="border-radius: 20px; margin-bottom: 20px;">

# ⚡ THUNDERSTORM BILLING

### _Calming ISP Billing, Elevated to v2.0_

<br>

[![Version](https://img.shields.io/badge/version-2.1.0-6D5BFF?style=for-the-badge&logo=rocket)](https://github.com/bloodwraith8851/T.F.N-Billing/releases)
[![Python](https://img.shields.io/badge/python-3.10+-4A6CFA?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/license-MIT-9C27B0?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=for-the-badge&logo=windows)](https://github.com/bloodwraith8851/T.F.N-Billing/releases)

<br>

「 [✨ Features](#-features) • [🗄️ Database](#️-database-layer) • [🌊 Architecture](#-architecture) • [🚀 Setup](#-setup) • [📋 Changelog](#-changelog) • [🔮 Roadmap](#-roadmap) 」

</div>

<br>

<blockquote align="center">
  <p><i>"Transforming billing from a chore into a calming, ethereal experience."</i></p>
</blockquote>

<br>

## 🌟 About

A modern, open-source ISP billing desktop application built with Python + Eel.
Thunderstorm Billing v2.0 brings a **SQLite-powered** data layer, live **analytics charts**, enriched **customer profiles**, and a polished notification-first UX — all inside a breathtaking dark-mode glassmorphism interface.

<br>

## 🎭 The Aesthetic

<div align="center">
  <table>
    <tr>
      <td align="center"><b>☁️ Cloud Morphism</b><br>Dynamic CSS breathing effects</td>
      <td align="center"><b>✨ Stellar Particles</b><br>Responsive 3D backdrop</td>
    </tr>
    <tr>
      <td align="center"><b>🌌 Aurora Shimmer</b><br>Ethereal animated gradients</td>
      <td align="center"><b>🍃 Glass UI</b><br>Frosted-glass card clarity</td>
    </tr>
  </table>
</div>

<br>

## ✨ Features

### 🧾 Invoicing
- GST-compliant **PDF invoice generation** (ReportLab) with watermark logo
- Auto-numbered invoices with configurable prefix (`TF/25-26/HR/`)
- **Duplicate invoice detection** — warns before generating a repeat for the same customer & billing period
- Discount, late-fee, and partial payment fields

### 📊 Analytics *(v2.0 NEW)*
- **Monthly Revenue** bar chart — last 6 months at a glance
- **Plan Breakdown** donut chart — see which plans dominate
- **Collection Rate** KPI with animated SVG ring indicator
- **Outstanding Dues** panel — all unpaid invoices with days-overdue badge

### 👥 Customer Management *(v2.0 Enhanced)*
- Live **search + status filter** (Active / Suspended / Terminated)
- **Customer Profile** view — full invoice history, lifetime value, pending dues
- **Notes, Tags, Connection Status** editing per customer
- **CSV Import** — bulk-load customers from a spreadsheet

### 📜 Invoice History
- **Date-range filter** + text search + status filter
- Mark invoice as **Paid** in one click
- **WhatsApp sharing** — opens chat with pre-filled message + PDF in clipboard
- Export full history to CSV

### 🔔 Notifications & Shortcuts *(v2.0 NEW)*
- **Bell icon** — slide-out panel with last 5 invoice events
- Keyboard shortcuts: `Ctrl+N` New Invoice · `Ctrl+H` History · `Ctrl+S` Settings

### ⚙️ Settings & Maintenance
- Company details, GST rate, invoice prefix — all configurable
- **App Log Viewer** in Settings (last 150 lines of debug log)
- **Auto-update** checker — compares GitHub releases, one-click installer download
- Invoice counter reset

<br>

## 🗄️ Database Layer

> [!IMPORTANT]
> v2.0 migrates from JSON flat files to **SQLite** (`billing.db`) automatically on first launch. Your existing `customers.json` and `invoice_log.json` data is preserved and migrated — no manual steps needed.

```
billing.db
├── customers       — id, name, phone, address, gstin, notes, tags, status
└── invoice_log     — datetime, amount, plan, status, payment_method, filename
```

| Feature | JSON (v1.x) | SQLite (v2.0) |
|---|---|---|
| Speed | O(n) full-file read/write | O(1) indexed queries |
| Concurrent safety | Race conditions possible | Per-connection thread safety |
| Analytics queries | Full scan in Python | Native SQL aggregations |
| **Auto-backup** | ✗ | ✅ Daily · keeps last 7 |

`users.json`, `settings.json`, `invoice_tracker.json` remain JSON-based (lightweight, no migration needed).

<br>

## 🌊 Architecture

<details>
<summary><b>Click to expand — Technical Blueprint 🛠️</b></summary>

### Backend (`Python`)

| File | Role |
|---|---|
| `launcher.py` | Entry point — installs deps, sets up dirs, starts Eel |
| `app_eel.py` | Eel bridge — exposes all Python functions to JS |
| `backend.py` | Core logic — SQLite CRUD, PDF generation, analytics, backup |
| `installer_setup.py` | Standalone installer EXE frontend (Eel + win32com) |
| `build_installer.py` | PyInstaller build script for app + installer |

### Frontend (`Web`)

| File | Role |
|---|---|
| `web/index.html` | SPA shell — all views (Dashboard, Customers, Analytics, History, Settings) |
| `web/static/style.css` | Full design system — glassmorphism, animations, dark/light theme |
| `web/static/script.js` | All UI logic — charts, filters, notifications, keyboard shortcuts |

### Data Flow
```
User Action (JS)
    ↓  eel.function_name(data)
app_eel.py  (bridge)
    ↓  backend.function(data)
backend.py  (logic + SQLite)
    ↓  return dict
app_eel.py  → JS callback
    ↓
UI update (DOM)
```

</details>

<br>

## 🚀 Setup

### Option A — Installer (Recommended)
1. Download **`Thunderstorm_Billing_v2.0.0_Setup.exe`** from [Releases](https://github.com/bloodwraith8851/T.F.N-Billing/releases)
2. Run the installer — choose your install folder, click **Install Now**
3. Launch from the desktop shortcut

### Option B — Run from Source
```bash
# 1. Clone
git clone https://github.com/bloodwraith8851/T.F.N-Billing.git
cd T.F.N-Billing

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
python launcher.py
```

### Build the installer yourself
```bash
python build_installer.py
# Output: dist/Thunderstorm_Billing_v2.0.0_Setup.exe
```

<br>

## 📋 Changelog

### v2.0.0 — 2026-03-19
> Major release — SQLite migration, analytics, enhanced customer management

**New**
- SQLite database (`billing.db`) with one-time auto-migration from JSON
- Daily auto-backup — keeps last 7 copies in `backups/`
- Analytics view — Monthly Revenue bar chart + Plan Breakdown donut
- Collection Rate KPI with animated SVG ring
- Outstanding Dues live panel on dashboard
- Customer Profile view (notes, tags, status, invoice history, LTV)
- Notification center (bell icon, last 5 events)
- Keyboard shortcuts: `Ctrl+N` / `Ctrl+H` / `Ctrl+S`
- Date-range + status filter on Invoice History
- CSV customer import
- App Log Viewer in Settings
- Versioned installer: `Thunderstorm_Billing_vX.X.X_Setup.exe`

**Changed**
- `generate_invoice` — uses fast `append_log()` INSERT instead of full-table rewrite
- Dashboard stats include `collection_rate` and `invoice_count`
- Installer window resized to 900×640 for better layout

**Removed**
- Dead Flask API routes from `backend.py` (~120 lines)
- Unused `LOGO_PATH`, `ICO_PATH`, `calculate_amounts()` dead code

---

### v1.1.0 → v1.0.x
- Toast notifications, visual polish, installer UI, auto-update system

<br>

## 🔮 Roadmap

<details>
<summary><b>View planned features 🛰️</b></summary>

#### Phase 1 — Near-term
- [ ] MikroTik / OLT live status on dashboard
- [ ] Multi-month invoice generation

#### Phase 2 — Mid-term
- [ ] Mobile companion app (Flutter)
- [ ] Cloud sync / backup to Google Drive

#### Phase 3 — Future
- [ ] Churn prediction AI
- [ ] WhatsApp Business API integration (replace automation)

</details>

<br>

---

<div align="center">

**[🐛 Report Bug](https://github.com/bloodwraith8851/T.F.N-Billing/issues)** · **[💡 Request Feature](https://github.com/bloodwraith8851/T.F.N-Billing/issues)** · **[📦 Releases](https://github.com/bloodwraith8851/T.F.N-Billing/releases)**

<br>

**Crafted with 💜 by the Thunderstorm Team**
_Elevating ISP Management to the Stars_

</div>
