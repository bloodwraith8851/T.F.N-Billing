import os
import sys
import json
import sqlite3
import glob
import shutil
import io
import csv
import webbrowser
from datetime import datetime
import traceback
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
import PIL.Image

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ================================================================
# ASSET PATH
# ================================================================

def get_asset_path(filename):
    """Resolve asset path: checks local dir first then PyInstaller bundle."""
    local_path = os.path.join("assets", filename)
    if os.path.exists(local_path):
        return local_path
    try:
        bundled = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(bundled):
            return bundled
    except AttributeError:
        pass
    return local_path

def _logo_path():
    return get_asset_path("logo.png")

GST_RATE = 0.09

PLANS = [
    "100 MBPS UNL",
    "200 MBPS UNL",
    "300 MBPS UNL",
    "400 MBPS UNL",
    "500 MBPS UNL",
]

# ================================================================
# FILE PATHS
# ================================================================

DB_FILE          = "billing.db"
TRACKER_FILE     = "invoice_tracker.json"
INVOICE_LOG_FILE = "invoice_log.json"   # legacy – migration source only
CUSTOMERS_FILE   = "customers.json"     # legacy – migration source only
SETTINGS_FILE    = "settings.json"

DEFAULT_SETTINGS = {
    "company_name":    "THUNDERSTORM FIBERNET",
    "company_address": "D-2/539, Shiv Durga Vihar, Lakkarpur, Faridabad, HR - 121009",
    "company_gstin":   "06DJVPP9834G1ZD",
    "company_phone":   "8585986890",
    "company_email":   "thunderstromfibernet@gmail.com",
    "gst_rate":        9.0,
    "invoice_prefix":  "TF/25-26/HR/",
    "place_of_supply": "Haryana",
}

# ================================================================
# SETTINGS
# ================================================================

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return {**DEFAULT_SETTINGS, **json.loads(content)}
        return dict(DEFAULT_SETTINGS)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return dict(DEFAULT_SETTINGS)


def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise

# ================================================================
# INVOICE TRACKER
# ================================================================

def _initialize_tracker():
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'w') as f:
            json.dump({"last_invoice_number": 2058}, f)


def load_invoice_number():
    _initialize_tracker()
    try:
        with open(TRACKER_FILE) as f:
            content = f.read().strip()
            if not content:
                return 2059
            return json.loads(content).get("last_invoice_number", 2058) + 1
    except Exception as e:
        logger.error(f"Error loading invoice number: {e}")
        return 2059


def save_invoice_number(number):
    with open(TRACKER_FILE, 'w') as f:
        json.dump({"last_invoice_number": number}, f)

# ================================================================
# SQLITE DATABASE
# ================================================================

def get_db():
    """Open a fresh SQLite connection (one per operation for thread safety)."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and run one-time JSON migration."""
    try:
        conn = get_db()
        c    = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            customer_id       TEXT PRIMARY KEY,
            name              TEXT DEFAULT '',
            tenant_name       TEXT DEFAULT '',
            phone             TEXT DEFAULT '',
            customer_address  TEXT DEFAULT '',
            customer_gstin    TEXT DEFAULT '',
            notes             TEXT DEFAULT '',
            tags              TEXT DEFAULT '',
            connection_status TEXT DEFAULT 'Active',
            created_at        TEXT DEFAULT ''
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS invoice_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime       TEXT    DEFAULT '',
            customer_name  TEXT    DEFAULT '',
            customer_id    TEXT    DEFAULT '',
            phone          TEXT    DEFAULT '',
            invoice_num    TEXT    DEFAULT '',
            amount         REAL    DEFAULT 0,
            paid_amount    REAL    DEFAULT 0,
            filename       TEXT    DEFAULT '',
            status         TEXT    DEFAULT 'Unpaid',
            payment_method TEXT    DEFAULT '',
            payment_date   TEXT    DEFAULT '',
            plan           TEXT    DEFAULT ''
        )''')

        conn.commit()
        _migrate_json_to_db(conn)
        conn.close()
        logger.info("SQLite DB initialised.")
    except Exception as e:
        logger.error(f"init_db error: {e}\n{traceback.format_exc()}")


def _migrate_json_to_db(conn):
    """One-time migration of legacy JSON files into SQLite."""
    c = conn.cursor()

    # Customers
    c.execute("SELECT COUNT(*) FROM customers")
    if c.fetchone()[0] == 0 and os.path.exists(CUSTOMERS_FILE):
        try:
            with open(CUSTOMERS_FILE, 'r') as f:
                raw = f.read().strip()
            if raw:
                for cust in json.loads(raw):
                    c.execute(
                        '''INSERT OR IGNORE INTO customers
                           (customer_id, name, tenant_name, phone, customer_address,
                            customer_gstin, notes, tags, connection_status, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?)''',
                        (cust.get('customer_id',''), cust.get('name',''),
                         cust.get('tenant_name',''), cust.get('phone',''),
                         cust.get('customer_address',''), cust.get('customer_gstin',''),
                         cust.get('notes',''), cust.get('tags',''),
                         cust.get('connection_status','Active'),
                         cust.get('created_at', datetime.now().isoformat()))
                    )
                conn.commit()
                logger.info("Customer JSON migrated.")
        except Exception as e:
            logger.error(f"Customer migration error: {e}")

    # Invoice logs
    c.execute("SELECT COUNT(*) FROM invoice_log")
    if c.fetchone()[0] == 0 and os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                raw = f.read().strip()
            if raw:
                for log in json.loads(raw):
                    c.execute(
                        '''INSERT INTO invoice_log
                           (datetime, customer_name, customer_id, phone, invoice_num,
                            amount, paid_amount, filename, status, payment_method,
                            payment_date, plan)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (log.get('datetime',''), log.get('customer_name',''),
                         log.get('customer_id',''), log.get('phone',''),
                         log.get('invoice_num',''),
                         float(log.get('amount', 0)), float(log.get('paid_amount', 0)),
                         log.get('filename',''), log.get('status','Unpaid'),
                         log.get('payment_method',''), log.get('payment_date',''),
                         log.get('plan',''))
                    )
                conn.commit()
                logger.info("Invoice log JSON migrated.")
        except Exception as e:
            logger.error(f"Invoice log migration error: {e}")

# ================================================================
# CUSTOMERS
# ================================================================

def load_customers():
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM customers ORDER BY name")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Error loading customers: {e}")
        return []


def save_customer(data):
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            '''INSERT OR REPLACE INTO customers
               (customer_id, name, tenant_name, phone, customer_address,
                customer_gstin, notes, tags, connection_status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (data.get('customer_id',''), data.get('name',''),
             data.get('tenant_name',''), data.get('phone',''),
             data.get('customer_address',''), data.get('customer_gstin',''),
             data.get('notes',''), data.get('tags',''),
             data.get('connection_status','Active'),
             data.get('created_at', datetime.now().isoformat()))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving customer: {e}")
        raise


def update_customer_notes(customer_id, notes, tags, connection_status):
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            "UPDATE customers SET notes=?, tags=?, connection_status=? WHERE customer_id=?",
            (notes, tags, connection_status, customer_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating customer: {e}")
        raise


def import_customers_csv_data(csv_text):
    """Parse CSV string and upsert customers. Returns count imported."""
    try:
        reader   = csv.DictReader(io.StringIO(csv_text))
        imported = 0
        for row in reader:
            cid = row.get('customer_id', '').strip()
            if cid:
                save_customer({
                    'customer_id':       cid,
                    'name':              row.get('name','').strip(),
                    'tenant_name':       row.get('tenant_name','').strip(),
                    'phone':             row.get('phone','').strip(),
                    'customer_address':  row.get('customer_address','').strip(),
                    'customer_gstin':    row.get('customer_gstin','').strip(),
                    'notes':             row.get('notes','').strip(),
                    'tags':              row.get('tags','').strip(),
                    'connection_status': row.get('connection_status','Active').strip(),
                })
                imported += 1
        return imported
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise

# ================================================================
# INVOICE LOGS
# ================================================================

def load_logs():
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM invoice_log ORDER BY id")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Error loading logs: {e}")
        return []


def save_logs(logs):
    """Full replace of all logs (backward-compatible load/modify/save pattern)."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("DELETE FROM invoice_log")
        for log in logs:
            _insert_log(c, log)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving logs: {e}")
        raise


def append_log(log_data):
    """Append a single log entry (fast path for new invoices)."""
    try:
        conn = get_db()
        c    = conn.cursor()
        _insert_log(c, log_data)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error appending log: {e}")
        raise


def _insert_log(cursor, log):
    """Shared INSERT helper used by save_logs and append_log."""
    cursor.execute(
        '''INSERT INTO invoice_log
           (datetime, customer_name, customer_id, phone, invoice_num,
            amount, paid_amount, filename, status, payment_method,
            payment_date, plan)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (log.get('datetime',''), log.get('customer_name',''),
         log.get('customer_id',''), log.get('phone',''),
         log.get('invoice_num',''),
         float(log.get('amount', 0)), float(log.get('paid_amount', 0)),
         log.get('filename',''), log.get('status','Unpaid'),
         log.get('payment_method',''), log.get('payment_date',''),
         log.get('plan',''))
    )


def check_duplicate_invoice(customer_id, billing_from, billing_to):
    """Return True if an invoice exists for this customer in the same month/year."""
    try:
        parts = billing_from.split('-')          # "01-Mar-2026"
        if len(parts) < 3:
            return False
        month   = parts[1]
        year    = parts[2]
        pattern = f"%_{month}_{year}.pdf"
        conn    = get_db()
        c       = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM invoice_log WHERE customer_id=? AND filename LIKE ?",
            (str(customer_id), pattern)
        )
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        return False

# ================================================================
# ANALYTICS
# ================================================================

def _month_ago(n):
    """Return (year, month) for n months before today."""
    now   = datetime.now()
    month = now.month - n
    year  = now.year
    while month <= 0:
        month += 12
        year  -= 1
    return year, month


def get_monthly_revenue():
    """Revenue totals for each of the last 6 months."""
    try:
        conn        = get_db()
        c           = conn.cursor()
        month_names = ['Jan','Feb','Mar','Apr','May','Jun',
                       'Jul','Aug','Sep','Oct','Nov','Dec']
        labels, revenues = [], []
        for i in range(5, -1, -1):
            year, month = _month_ago(i)
            # datetime stored as "DD-MM-YYYY HH:MM"
            month_str = f"{month:02d}-{year}"
            label     = f"{month_names[month-1]} {str(year)[2:]}"
            c.execute(
                "SELECT COALESCE(SUM(amount),0) FROM invoice_log "
                "WHERE substr(datetime,4,2)||'-'||substr(datetime,7,4)=?",
                (month_str,)
            )
            revenues.append(float(c.fetchone()[0]))
            labels.append(label)
        conn.close()
        return {'months': labels, 'revenues': revenues}
    except Exception as e:
        logger.error(f"get_monthly_revenue error: {e}")
        return {'months': [], 'revenues': []}


def get_plan_breakdown():
    """Invoice count grouped by plan."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            "SELECT plan, COUNT(*) AS cnt FROM invoice_log "
            "WHERE plan!='' GROUP BY plan ORDER BY cnt DESC"
        )
        rows = c.fetchall()
        conn.close()
        if not rows:
            return {'plans': [], 'counts': []}
        return {'plans': [r['plan'] for r in rows], 'counts': [r['cnt'] for r in rows]}
    except Exception as e:
        logger.error(f"get_plan_breakdown error: {e}")
        return {'plans': [], 'counts': []}


def get_outstanding_dues():
    """All unpaid/partial invoices with days-overdue calculated."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM invoice_log WHERE status!='Paid' ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        now  = datetime.now()
        for row in rows:
            try:
                dt = datetime.strptime(row['datetime'].split(' ')[0], '%d-%m-%Y')
                row['days_overdue'] = (now - dt).days
            except Exception:
                row['days_overdue'] = 0
        return rows
    except Exception as e:
        logger.error(f"get_outstanding_dues error: {e}")
        return []


def get_collection_rate():
    """Percentage of invoices marked Paid in the current month."""
    try:
        conn      = get_db()
        c         = conn.cursor()
        now       = datetime.now()
        month_str = f"{now.month:02d}-{now.year}"
        c.execute(
            "SELECT COUNT(*) FROM invoice_log "
            "WHERE substr(datetime,4,2)||'-'||substr(datetime,7,4)=?",
            (month_str,)
        )
        total = c.fetchone()[0]
        if total == 0:
            conn.close()
            return 0.0
        c.execute(
            "SELECT COUNT(*) FROM invoice_log "
            "WHERE substr(datetime,4,2)||'-'||substr(datetime,7,4)=? AND status='Paid'",
            (month_str,)
        )
        paid = c.fetchone()[0]
        conn.close()
        return round((paid / total) * 100, 1)
    except Exception as e:
        logger.error(f"get_collection_rate error: {e}")
        return 0.0

# ================================================================
# AUTO-BACKUP
# ================================================================

def run_auto_backup():
    """Copy billing.db to backups/ once per day; keep last 7 copies."""
    try:
        os.makedirs('backups', exist_ok=True)
        today       = datetime.now().strftime('%Y%m%d')
        backup_file = f'backups/billing_{today}.db'
        if not os.path.exists(backup_file) and os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, backup_file)
            logger.info(f"Auto-backup: {backup_file}")
            for old in sorted(glob.glob('backups/billing_*.db'), reverse=True)[7:]:
                os.remove(old)
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}")

# ================================================================
# APP LOGS
# ================================================================

def get_app_logs(lines=150):
    """Return the last N lines from the debug log file."""
    try:
        log_file = 'tfn_billing_debug.log'
        if not os.path.exists(log_file):
            return ['(Log file not found.)']
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        return [l.rstrip('\n') for l in all_lines[-lines:]]
    except Exception as e:
        logger.error(f"get_app_logs error: {e}")
        return [f'Error reading logs: {e}']

# ================================================================
# PDF GENERATION
# ================================================================

def _check_logo():
    """Return True if a valid PNG logo exists."""
    path = _logo_path()
    if not os.path.exists(path):
        return False
    try:
        with PIL.Image.open(path) as img:
            return img.format == 'PNG'
    except Exception:
        return False


class _Watermark(Flowable):
    def __init__(self, logo_path, width, height, opacity=0.08):
        Flowable.__init__(self)
        self.logo_path = logo_path
        self.width     = width
        self.height    = height
        self.opacity   = opacity

    def draw(self):
        if not os.path.exists(self.logo_path):
            return
        self.canv.saveState()
        self.canv.setFillAlpha(self.opacity)
        pw, ph = A4
        self.canv.translate((pw - self.width) / 2, (ph - self.height) / 2)
        self.canv.drawImage(self.logo_path, 0, 0, self.width, self.height, mask='auto')
        self.canv.restoreState()


def _draw_watermark(canvas, doc):
    if _check_logo():
        wm      = _Watermark(_logo_path(), width=150*mm, height=150*mm)
        wm.canv = canvas
        wm.draw()


def generate_pdf(data):
    try:
        cfg            = load_settings()
        gst_rate       = float(cfg.get('gst_rate', 9.0)) / 100.0
        invoice_prefix = cfg.get('invoice_prefix', 'TF/25-26/HR/')
        invoice_number = f"{invoice_prefix}{data['invoice_num']}"
        filename       = f"output_invoices/{data['pdf_filename']}"
        os.makedirs('output_invoices', exist_ok=True)

        doc      = SimpleDocTemplate(filename, pagesize=A4,
                                     rightMargin=30, leftMargin=30,
                                     topMargin=30, bottomMargin=18)
        styles   = getSampleStyleSheet()
        styleN   = styles['Normal']
        centered = ParagraphStyle('centered', parent=styleN,
                                  alignment=TA_CENTER, fontSize=16, spaceAfter=6)
        centered_sm = ParagraphStyle('centered_sm', parent=styleN,
                                     alignment=TA_CENTER, fontSize=10, spaceAfter=6)
        elements = [Spacer(1, 30)]

        if _check_logo():
            try:
                logo = Image(_logo_path(), width=30*mm, height=30*mm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception as e:
                logger.warning(f"Logo load error: {e}")

        elements += [
            Spacer(1, 12),
            Paragraph("<b>TAX INVOICE</b>", centered),
            Paragraph("(Original for recipient)", centered_sm),
            Spacer(1, 12),
            Paragraph(f"<b>{cfg['company_name']}</b>", centered),
            Paragraph(f"Supplier Address: {cfg['company_address']}", centered_sm),
            Paragraph(
                f"Supplier GSTIN: {cfg['company_gstin']} &nbsp;&nbsp;&nbsp;&nbsp; "
                f"Phone No: {cfg['company_phone']} &nbsp;&nbsp;&nbsp;&nbsp; "
                f"Email: {cfg['company_email']}",
                centered_sm
            ),
            Spacer(1, 20),
        ]

        info_table = Table([[
            Paragraph(
                f"Customer Address: {data['customer_address']}<br/>"
                f"Place of Supply: {cfg['place_of_supply']}<br/>"
                f"Customer GSTIN: {data.get('customer_gstin','')}",
                styleN),
            Paragraph(
                f"Invoice Number: {invoice_number}<br/>"
                f"Invoice Date: {data.get('invoice_date', datetime.now().strftime('%d %b %Y'))}<br/>"
                f"Tenant Name: {data.get('tenant_name','')}<br/>"
                f"Customer Id: {data['customer_id']}<br/>"
                f"Billing Period: {data['billing_from']} - {data['billing_to']}<br/>"
                f"Months: {data['months']}",
                styleN),
        ]], colWidths=[250, 250])
        elements += [info_table, Spacer(1, 12)]

        base_amount = round(float(data['total_amount']) / (1 + 2 * gst_rate), 2)
        gst         = round(base_amount * gst_rate, 2)
        discount    = float(data.get('discount') or 0)
        late_fee    = float(data.get('late_fee') or 0)
        total       = float(data['total_amount']) - discount + late_fee
        gst_pct_str = f"{gst_rate * 100:.1f}%"

        tdata = [
            ["S.No", "Particular", "HSN/SAC", "Amount", "Rate", "CGST", "SGST", "Total"],
            ["1",
             f"{data['plan']} - {data['months']} Month{'s' if str(data['months']) != '1' else ''}",
             "998422",
             f"Rs. {base_amount:.2f}", gst_pct_str,
             f"Rs. {gst:.2f}", f"Rs. {gst:.2f}",
             f"Rs. {float(data['total_amount']):.2f}"],
        ]
        if discount:
            tdata.append(["", "Discount",  "", "", "", "", "", f"-Rs. {discount:.2f}"])
        if late_fee:
            tdata.append(["", "Late Fee",  "", "", "", "", "", f"+Rs. {late_fee:.2f}"])
        tdata.append(["", "Total Invoice Amount", "", "", "", "", "", f"Rs. {total:.2f}"])

        lr = len(tdata) - 1
        inv_table = Table(tdata, colWidths=[30, 120, 60, 60, 40, 60, 60, 70])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('ALIGN',      (0,0), (-1,0), 'CENTER'),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,lr-1), colors.HexColor('#e3f2fd')),
            ('ALIGN',  (0,1), (0,lr-1), 'CENTER'),
            ('ALIGN',  (1,1), (1,lr-1), 'LEFT'),
            ('FONTSIZE', (0,1), (-1,lr-1), 9),
            ('ALIGN', (2,1), (-1,lr-1), 'CENTER'),
            ('BACKGROUND', (0,lr), (-2,lr), colors.HexColor('#ffe082')),
            ('SPAN',  (1,lr), (6,lr)),
            ('ALIGN', (1,lr), (6,lr), 'LEFT'),
            ('ALIGN', (7,lr), (7,lr), 'RIGHT'),
            ('FONTNAME', (1,lr), (1,lr), 'Helvetica-Bold'),
            ('FONTNAME', (7,lr), (7,lr), 'Helvetica-Bold'),
            ('BOX',  (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements += [inv_table, Spacer(1, 12)]

        if data.get('custom_notes'):
            elements.append(Paragraph(f"<b>Notes:</b> {data['custom_notes']}", styleN))

        # Payment status line (if this PDF is being re-generated after payment)
        for entry in load_logs():
            if entry['filename'] == data['pdf_filename']:
                if entry.get('status') == 'Paid':
                    elements.append(Paragraph(
                        f"<b>Payment Status:</b> Paid on {entry.get('payment_date','')} "
                        f"({entry.get('payment_method','')})", styleN))
                elif entry.get('status') == 'Partial':
                    elements.append(Paragraph(
                        f"<b>Payment Status:</b> Partial payment on {entry.get('payment_date','')} "
                        f"({entry.get('payment_method','')})", styleN))
                break

        elements.append(Paragraph(
            f"This is a computer generated bill and does not require signature.<br/>"
            f"For queries and complaints contact: {cfg['company_phone']}",
            styleN
        ))

        doc.build(elements, onFirstPage=_draw_watermark, onLaterPages=_draw_watermark)
        return True
    except Exception as e:
        logger.error(f"PDF generation failed: {e}\n{traceback.format_exc()}")
        raise
