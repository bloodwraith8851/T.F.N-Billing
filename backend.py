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
from logging.handlers import RotatingFileHandler

# PDF libs imported dynamically on-demand for zero-latency startup

# ================================================================
# SETUP ADVANCED LOGGING (Rotating File)
# ================================================================
DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ThunderstormBilling')
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, 'tfn_billing_debug.log')

logger = logging.getLogger('ThunderstormBilling')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    rfh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)
    
    # Also log to stdout for dev server
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

logger.info("Initializing Thunderstorm Billing Backend...")

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

# Legacy constant kept for backward-compat; use get_plans_list() for dynamic plans
PLANS = [
    "100 MBPS UNL",
    "200 MBPS UNL",
    "300 MBPS UNL",
    "400 MBPS UNL",
    "500 MBPS UNL",
]

# ================================================================
# FILE PATHS & MIGRATION
# ================================================================

DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ThunderstormBilling')

DB_FILE          = os.path.join(DATA_DIR, "billing.db")
TRACKER_FILE     = os.path.join(DATA_DIR, "invoice_tracker.json")
INVOICE_LOG_FILE = os.path.join(DATA_DIR, "invoice_log.json")   # legacy – migration source only
CUSTOMERS_FILE   = os.path.join(DATA_DIR, "customers.json")     # legacy – migration source only
SETTINGS_FILE    = os.path.join(DATA_DIR, "settings.json")
USERS_FILE       = os.path.join(DATA_DIR, "users.json")

OUTPUT_DIR       = os.path.join(DATA_DIR, "output_invoices")
BACKUPS_DIR      = os.path.join(DATA_DIR, "backups")
EXPORTS_DIR      = os.path.join(DATA_DIR, "exports")

def init_data_directories():
    for d in [DATA_DIR, OUTPUT_DIR, BACKUPS_DIR, EXPORTS_DIR]:
        os.makedirs(d, exist_ok=True)

def initialize_default_files():
    # Initialize default json files if they don't exist
    db_files = {
        USERS_FILE: '[{"username": "admin", "password": "admin", "role": "admin"}]',
        CUSTOMERS_FILE: '[]',
        TRACKER_FILE: '{"last_invoice_number": 2058}',
        INVOICE_LOG_FILE: '[]'
    }
    for filename, content in db_files.items():
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(content)

def migrate_legacy_data(legacy_dir):
    """Safely migrate user data from the executable directory to DATA_DIR."""
    init_data_directories()
    
    files_to_move = ["billing.db", "invoice_tracker.json", "customers.json", "invoice_log.json", "users.json", "settings.json", "tfn_billing_debug.log"]
    dirs_to_move = ["output_invoices", "backups", "exports"]
    
    for f in files_to_move:
        src = os.path.join(legacy_dir, f)
        dst = os.path.join(DATA_DIR, f)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                logger.info(f"Migrated {f} to {dst}")
            except Exception as e:
                logger.error(f"Failed to migrate {f}: {e}")
                
    for d in dirs_to_move:
        src_d = os.path.join(legacy_dir, d)
        dst_d = os.path.join(DATA_DIR, d)
        if os.path.exists(src_d):
            try:
                for item in os.listdir(src_d):
                    s = os.path.join(src_d, item)
                    d_item = os.path.join(dst_d, item)
                    if not os.path.exists(d_item):
                        if os.path.isfile(s):
                            shutil.copy2(s, d_item)
                logger.info(f"Migrated directory contents for {d}")
            except Exception as e:
                logger.error(f"Failed to migrate dir {d}: {e}")
                
    # After migration finishes, generate any missing defaults
    initialize_default_files()

DEFAULT_SETTINGS = {
    "company_name":       "THUNDERSTORM FIBERNET",
    "company_address":    "D-2/539, Shiv Durga Vihar, Lakkarpur, Faridabad, HR - 121009",
    "company_gstin":      "06DJVPP9834G1ZD",
    "company_phone":      "8585986890",
    "company_email":      "thunderstromfibernet@gmail.com",
    "gst_rate":           9.0,
    "invoice_prefix":     "TF/25-26/HR/",
    "place_of_supply":    "Haryana",
    "whatsapp_template":  "Hello {name}, your internet bill of \u20b9{amount} is due. Invoice: {invoice_num}. Please pay on time. Thank you!",
    "monthly_target":     0,
    "plans":              ["100 MBPS UNL", "200 MBPS UNL", "300 MBPS UNL", "400 MBPS UNL", "500 MBPS UNL"],
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
            customer_email    TEXT DEFAULT '',
            notes             TEXT DEFAULT '',
            tags              TEXT DEFAULT '',
            connection_status TEXT DEFAULT 'Active',
            created_at        TEXT DEFAULT ''
        )''')

        # Upgrade: add email column if missing (existing installs)
        try:
            c.execute("ALTER TABLE customers ADD COLUMN customer_email TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass  # Column already exists

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

        # Performance indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_log_status   ON invoice_log(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_log_customer ON invoice_log(customer_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_log_datetime ON invoice_log(datetime)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_log_filename ON invoice_log(filename)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_cust_name    ON customers(name)')

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
                customer_gstin, customer_email, notes, tags, connection_status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (data.get('customer_id',''), data.get('name',''),
             data.get('tenant_name',''), data.get('phone',''),
             data.get('customer_address',''), data.get('customer_gstin',''),
             data.get('customer_email',''), data.get('notes',''), data.get('tags',''),
             data.get('connection_status','Active'),
             data.get('created_at', datetime.now().isoformat()))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving customer: {e}")
        raise


def save_customer_full(data):
    """Save customer data along with their address and extra details to the SQLite DB."""
    try:
        logger.info(f"Saving customer profile for: {data.get('name', 'Unknown')}")
        return save_customer(data)
    except Exception as e:
        logger.error(f"Error saving customer full: {e}")
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
                    'customer_email':    row.get('customer_email','').strip(),
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
    """Revenue totals for each of the last 6 months. Handles both ISO and legacy datetime formats."""
    try:
        conn        = get_db()
        c           = conn.cursor()
        month_names = ['Jan','Feb','Mar','Apr','May','Jun',
                       'Jul','Aug','Sep','Oct','Nov','Dec']
        # YYYY-MM extracted from either format
        month_expr = _get_month_group_sql()
        labels, revenues = [], []
        for i in range(5, -1, -1):
            year, month = _month_ago(i)
            ym_str = f"{year}-{month:02d}"   # YYYY-MM
            label  = f"{month_names[month-1]} {str(year)[2:]}"
            c.execute(
                f"SELECT COALESCE(SUM(amount),0) FROM invoice_log "
                f"WHERE ({month_expr})=?",
                (ym_str,)
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

def get_plan_breakdown_filtered(date_from, date_to):
    """Invoice count grouped by plan within the selected date range."""
    try:
        conn = get_db()
        c    = conn.cursor()
        sql_date = _get_date_filter_sql()
        c.execute(
            f"SELECT plan, COUNT(*) AS cnt FROM invoice_log "
            f"WHERE plan!='' AND {sql_date} BETWEEN ? AND ? "
            f"GROUP BY plan ORDER BY cnt DESC",
            (date_from, date_to)
        )
        rows = c.fetchall()
        conn.close()
        if not rows:
            return {'plans': [], 'counts': []}
        return {'plans': [r['plan'] for r in rows], 'counts': [r['cnt'] for r in rows]}
    except Exception as e:
        logger.error(f"get_plan_breakdown_filtered error: {e}")
        return {'plans': [], 'counts': []}



def get_outstanding_dues():
    """All unpaid/partial invoices with days-overdue calculated. Handles both datetime formats."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM invoice_log WHERE status!='Paid' ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        now  = datetime.now()
        for row in rows:
            try:
                raw = row['datetime'].split(' ')[0]  # date part only
                # Auto-detect format
                if len(raw) == 10 and raw[4] == '-':
                    dt = datetime.strptime(raw, '%Y-%m-%d')   # ISO
                else:
                    dt = datetime.strptime(raw, '%d-%m-%Y')   # legacy
                row['days_overdue'] = (now - dt).days
            except Exception:
                row['days_overdue'] = 0
        return rows
    except Exception as e:
        logger.error(f"get_outstanding_dues error: {e}")
        return []


def get_collection_rate():
    """Percentage of invoices marked Paid in the current month. Handles both datetime formats."""
    try:
        conn      = get_db()
        c         = conn.cursor()
        now       = datetime.now()
        ym_str    = f"{now.year}-{now.month:02d}"   # YYYY-MM
        month_expr = _get_month_group_sql()
        c.execute(
            f"SELECT COUNT(*) FROM invoice_log WHERE ({month_expr})=?",
            (ym_str,)
        )
        total = c.fetchone()[0]
        if total == 0:
            conn.close()
            return 0.0
        c.execute(
            f"SELECT COUNT(*) FROM invoice_log WHERE ({month_expr})=? AND status='Paid'",
            (ym_str,)
        )
        paid = c.fetchone()[0]
        conn.close()
        return round((paid / total) * 100, 1)
    except Exception as e:
        logger.error(f"get_collection_rate error: {e}")
        return 0.0

# ================================================================
# DATE FILTERED ANALYTICS
# ================================================================

def _get_date_filter_sql():
    """
    Returns a SQLite expression that extracts YYYY-MM-DD from the datetime field.
    Handles both formats stored in the DB:
      - ISO format:    'YYYY-MM-DD HH:MM'  (new inserts)
      - Legacy format: 'DD-MM-YYYY HH:MM'  (old JSON-migrated rows)
    Detection: if char at position 5 (0-indexed, col 5 in 1-indexed) is '-'
               and char 8 (col 8) is '-', it's ISO. Otherwise treat as legacy.
    """
    return (
        "CASE "
        "  WHEN substr(datetime,5,1)='-' AND substr(datetime,8,1)='-' "
        "    THEN substr(datetime,1,10) "
        "  ELSE substr(datetime,7,4)||'-'||substr(datetime,4,2)||'-'||substr(datetime,1,2) "
        "END"
    )

def _get_month_group_sql():
    """
    Returns a SQLite expression that extracts YYYY-MM for monthly grouping.
    Same dual-format logic as _get_date_filter_sql.
    """
    return (
        "CASE "
        "  WHEN substr(datetime,5,1)='-' AND substr(datetime,8,1)='-' "
        "    THEN substr(datetime,1,7) "
        "  ELSE substr(datetime,7,4)||'-'||substr(datetime,4,2) "
        "END"
    )

def get_dashboard_stats_filtered(date_from, date_to):
    """Get revenue stats filtered by date range (YYYY-MM-DD)"""
    try:
        conn = get_db()
        c = conn.cursor()
        sql_date = _get_date_filter_sql()
        
        c.execute(f"SELECT COALESCE(SUM(amount),0) FROM invoice_log WHERE {sql_date} BETWEEN ? AND ?", (date_from, date_to))
        total_amount = float(c.fetchone()[0])
        
        c.execute(f"SELECT COALESCE(SUM(amount),0) FROM invoice_log WHERE status IN ('Paid','Partial') AND {sql_date} BETWEEN ? AND ?", (date_from, date_to))
        paid_amount = float(c.fetchone()[0])
        
        c.execute(f"SELECT COUNT(*) FROM invoice_log WHERE {sql_date} BETWEEN ? AND ?", (date_from, date_to))
        invoice_count = c.fetchone()[0]
        
        conn.close()
        pending = total_amount - paid_amount
        return {
            "revenue": total_amount,
            "paid": paid_amount,
            "pending": pending,
            "invoice_count": invoice_count
        }
    except Exception as e:
        logger.error(f"get_dashboard_stats_filtered error: {e}")
        return {"revenue": 0, "paid": 0, "pending": 0, "invoice_count": 0}

def get_monthly_revenue_filtered(date_from, date_to):
    """Groups revenue by day or month within the selected date range."""
    try:
        conn = get_db()
        c = conn.cursor()
        sql_date = _get_date_filter_sql()
        
        from datetime import datetime
        d1 = datetime.strptime(date_from, "%Y-%m-%d")
        d2 = datetime.strptime(date_to, "%Y-%m-%d")
        days_diff = (d2 - d1).days
        
        if days_diff <= 31:
            group_sql = f"{sql_date} as ym"
        else:
            group_sql = f"{_get_month_group_sql()} as ym"
        
        c.execute(f"""
            SELECT {group_sql}, 
                   COALESCE(SUM(amount),0) 
            FROM invoice_log 
            WHERE {sql_date} BETWEEN ? AND ? 
            GROUP BY ym 
            ORDER BY ym ASC
        """, (date_from, date_to))
        
        rows = c.fetchall()
        conn.close()
        
        month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        labels, revenues = [], []
        
        for row in rows:
            ym = row[0]
            if days_diff <= 31 and ym and len(ym) == 10:
                y = ym[0:4]
                m = int(ym[5:7])
                d = int(ym[8:10])
                labels.append(f"{d} {month_names[m-1]}")
                revenues.append(float(row[1]))
            elif ym and len(ym) >= 7:
                y = ym[0:4]
                m = int(ym[5:7])
                labels.append(f"{month_names[m-1]} {y}")
                revenues.append(float(row[1]))
                
        return {'months': labels, 'revenues': revenues}
    except Exception as e:
        logger.error(f"get_monthly_revenue_filtered error: {e}")
        return {'months': [], 'revenues': []}

def get_logs_filtered(date_from, date_to):
    """Get invoice logs filtered by date range."""
    try:
        conn = get_db()
        c = conn.cursor()
        sql_date = _get_date_filter_sql()
        
        c.execute(f"SELECT * FROM invoice_log WHERE {sql_date} BETWEEN ? AND ? ORDER BY id DESC", (date_from, date_to))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"get_logs_filtered error: {e}")
        return []

def get_collection_rate_filtered(date_from, date_to):
    """Get collection rate within the given range."""
    try:
        conn = get_db()
        c = conn.cursor()
        sql_date = _get_date_filter_sql()
        
        c.execute(f"SELECT COUNT(*) FROM invoice_log WHERE {sql_date} BETWEEN ? AND ?", (date_from, date_to))
        total = c.fetchone()[0]
        if total == 0:
            conn.close()
            return 0.0
            
        c.execute(f"SELECT COUNT(*) FROM invoice_log WHERE status='Paid' AND {sql_date} BETWEEN ? AND ?", (date_from, date_to))
        paid = c.fetchone()[0]
        conn.close()
        
        return round((paid / total) * 100, 1)
    except Exception as e:
        logger.error(f"get_collection_rate_filtered error: {e}")
        return 0.0


# ================================================================
# AUTO-BACKUP
# ================================================================

def run_auto_backup():
    """Copy billing.db to backups/ once per day; keep last 7 copies."""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        backup_file = os.path.join(BACKUPS_DIR, f'billing_{today}.db')
        
        if not os.path.exists(backup_file) and os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, backup_file)
            logger.info(f"Auto-backup: {backup_file}")
            
            # Keep only the last 7
            for old in sorted(glob.glob(os.path.join(BACKUPS_DIR, 'billing_*.db')), reverse=True)[7:]:
                os.remove(old)
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}")

# ================================================================
# MARK INVOICE PAID — Fast UPDATE path
# ================================================================

def mark_invoice_paid_db(invoice_num, method='Manual Entry'):
    """Direct SQL UPDATE — no delete/reinsert of entire table."""
    try:
        logger.info(f"Marking invoice #{invoice_num} as Paid via {method}")
        conn = get_db()
        c    = conn.cursor()
        c.execute(
            "UPDATE invoice_log SET status='Paid', payment_method=?, payment_date=? WHERE invoice_num=?",
            (method, datetime.now().strftime("%d-%m-%Y"), invoice_num)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"mark_invoice_paid_db error: {e}")
        raise

# ================================================================
# QUICK ANALYTICS HELPERS
# ================================================================

def get_recent_logs(n=5):
    """Return the N most recent invoice log entries (fast LIMIT query)."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM invoice_log ORDER BY id DESC LIMIT ?", (n,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"get_recent_logs error: {e}")
        return []


def get_unpaid_count_this_month():
    """Count of Unpaid invoices created in the current calendar month."""
    try:
        conn      = get_db()
        c         = conn.cursor()
        now       = datetime.now()
        month_str = f"{now.month:02d}-{now.year}"
        c.execute(
            "SELECT COUNT(*) FROM invoice_log "
            "WHERE substr(datetime,4,2)||'-'||substr(datetime,7,4)=? AND status='Unpaid'",
            (month_str,)
        )
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"get_unpaid_count_this_month error: {e}")
        return 0


def get_overdue_invoices():
    """Return all non-Paid invoices with severity banding by days_overdue."""
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT * FROM invoice_log WHERE status != 'Paid' ORDER BY id DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        now = datetime.now()
        for row in rows:
            try:
                dt   = datetime.strptime(row['datetime'].split(' ')[0], '%d-%m-%Y')
                days = (now - dt).days
            except Exception:
                days = 0
            row['days_overdue'] = days
            row['severity']     = (
                'critical' if days >= 30 else
                'warning'  if days >= 15 else
                'caution'  if days >= 7  else 'normal'
            )
        return rows
    except Exception as e:
        logger.error(f"get_overdue_invoices error: {e}")
        return []

# ================================================================
# WHATSAPP TEMPLATE & MONTHLY TARGET
# ================================================================

def get_whatsapp_template():
    return load_settings().get('whatsapp_template',
        'Hello {name}, your internet bill of \u20b9{amount} is due. Invoice: {invoice_num}. Please pay on time.')

def save_whatsapp_template(template):
    s = load_settings()
    s['whatsapp_template'] = template
    save_settings(s)

def get_monthly_target():
    return float(load_settings().get('monthly_target', 0))

def save_monthly_target(target):
    s = load_settings()
    s['monthly_target'] = float(target)
    save_settings(s)

# ================================================================
# PLANS MANAGEMENT
# ================================================================

def get_plans_list():
    """Load plans from settings.json (user-configurable)."""
    return load_settings().get('plans', list(PLANS))

def save_plans_list(plans):
    s = load_settings()
    s['plans'] = plans
    save_settings(s)

# ================================================================
# OPEN FOLDER IN EXPLORER
# ================================================================

def open_folder(path):
    """Open a directory in Windows Explorer."""
    try:
        safe = os.path.realpath(path)
        os.startfile(safe)
    except Exception as e:
        logger.error(f"open_folder error: {e}")

# ================================================================
# BULK INVOICE GENERATION
# ================================================================

def generate_bulk_invoices(customer_ids, plan, billing_from, billing_to, months,
                            total_amount, payment_status, payment_method):
    """Generate invoices for a list of customer IDs in one operation."""
    settings   = load_settings()
    inv_prefix = settings.get('invoice_prefix', 'TF/25-26/HR/')
    try:
        parts      = billing_from.split('-')
        month_year = f"{parts[1]}_{parts[2]}" if len(parts) >= 3 else datetime.now().strftime("%b_%Y")
    except Exception:
        month_year = datetime.now().strftime("%b_%Y")

    conn = get_db()
    c    = conn.cursor()
    c.execute(
        "SELECT * FROM customers WHERE customer_id IN (%s)" % ','.join('?' * len(customer_ids)),
        customer_ids
    )
    customers_data = [dict(r) for r in c.fetchall()]
    conn.close()

    generated, errors = 0, []
    for customer in customers_data:
        try:
            invoice_num  = load_invoice_number()
            clean_name   = "".join(ch for ch in customer['name'].replace(' ', '_') if ch.isalnum() or ch == '_')
            pdf_filename = f"{clean_name}_{month_year}.pdf"
            invoice_data = {
                'invoice_num':      invoice_num,
                'pdf_filename':     pdf_filename,
                'name':             customer['name'],
                'customer_id':      customer['customer_id'],
                'tenant_name':      customer.get('tenant_name', ''),
                'phone':            customer.get('phone', ''),
                'customer_address': customer.get('customer_address', ''),
                'customer_gstin':   customer.get('customer_gstin', ''),
                'plan':             plan,
                'months':           months,
                'billing_from':     billing_from,
                'billing_to':       billing_to,
                'total_amount':     total_amount,
                'discount':         0,
                'late_fee':         0,
                'payment_status':   payment_status,
                'payment_method':   payment_method,
                'custom_notes':     '',
            }
            generate_pdf(invoice_data)
            save_invoice_number(invoice_num)
            append_log({
                "datetime":       datetime.now().strftime("%d-%m-%Y %H:%M"),
                "customer_name":  customer['name'],
                "customer_id":    customer['customer_id'],
                "phone":          customer.get('phone', ''),
                "invoice_num":    f"{inv_prefix}{invoice_num}",
                "amount":         float(total_amount),
                "paid_amount":    0,
                "filename":       pdf_filename,
                "status":         payment_status,
                "payment_method": payment_method or 'None',
                "payment_date":   datetime.now().strftime("%d-%m-%Y") if payment_status in ['Paid', 'Partial'] else '',
                "plan":           plan,
            })
            generated += 1
        except Exception as e:
            errors.append(f"{customer.get('name','?')}: {str(e)}")
    return {"generated": generated, "errors": errors, "total": len(customer_ids)}

# ================================================================
# SAMPLE PDF PREVIEW
# ================================================================

def generate_sample_pdf():
    """Generate a dummy invoice using current company settings."""
    try:
        import webbrowser as _wb
        sample_data = {
            'invoice_num':      'SAMPLE',
            'pdf_filename':     'SAMPLE_Preview_Invoice.pdf',
            'name':             'Sample Customer',
            'customer_id':      'CUST-PREVIEW',
            'tenant_name':      'Sample Tenant',
            'phone':            '9999999999',
            'customer_address': '123 Sample Street, City, State - 000000',
            'customer_gstin':   'SAMPLE0GSTIN',
            'plan':             '200 MBPS UNL',
            'months':           1,
            'billing_from':     '01-Jun-2026',
            'billing_to':       '30-Jun-2026',
            'total_amount':     590,
            'discount':         0,
            'late_fee':         0,
            'payment_status':   'Unpaid',
            'payment_method':   'None',
            'custom_notes':     'This is a SAMPLE invoice for preview. Not a real bill.',
        }
        generate_pdf(sample_data)
        sample_path = os.path.join(OUTPUT_DIR, 'SAMPLE_Preview_Invoice.pdf')
        if os.path.exists(sample_path):
            _wb.open(sample_path)
        return {"status": "success", "message": "Sample invoice opened!"}
    except Exception as e:
        logger.error(f"generate_sample_pdf error: {e}")
        return {"status": "error", "message": str(e)}

# ================================================================
# APP LOGS
# ================================================================

def get_app_logs(lines=150):
    """Return the last N lines from the debug log file."""
    try:
        log_file = os.path.join(DATA_DIR, 'tfn_billing_debug.log')
        if not os.path.exists(log_file):
            return [f'(Log file not found at: {log_file})']
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
    import PIL.Image
    path = _logo_path()
    if not os.path.exists(path):
        return False
    try:
        with PIL.Image.open(path) as img:
            return img.format == 'PNG'
    except Exception:
        return False


class _Watermark:
    def __init__(self, logo_path, width, height, opacity=0.08):
        from reportlab.platypus import Flowable
        from reportlab.lib.pagesizes import A4
        self.logo_path = logo_path
        self.width     = width
        self.height    = height
        self.opacity   = opacity

    def draw(self, canv):
        if not os.path.exists(self.logo_path):
            return
        canv.saveState()
        canv.setFillAlpha(self.opacity)
        from reportlab.lib.pagesizes import A4
        pw, ph = A4
        canv.translate((pw - self.width) / 2, (ph - self.height) / 2)
        canv.drawImage(self.logo_path, 0, 0, self.width, self.height, mask='auto')
        canv.restoreState()


def _draw_watermark(canvas, doc):
    from reportlab.lib.units import mm
    if _check_logo():
        wm = _Watermark(_logo_path(), width=150*mm, height=150*mm)
        wm.draw(canvas)


def generate_pdf(data):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Flowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER
        import PIL.Image
        
        logger.info(f"Generating PDF invoice #{data.get('invoice_num')} for {data.get('name')}")
        cfg            = load_settings()
        gst_rate       = float(cfg.get('gst_rate', 9.0)) / 100.0
        invoice_prefix = cfg.get('invoice_prefix', 'TF/25-26/HR/')
        invoice_number = f"{invoice_prefix}{data['invoice_num']}"
        filename       = os.path.join(OUTPUT_DIR, data['pdf_filename'])

        doc      = SimpleDocTemplate(filename, pagesize=A4,
                                     rightMargin=30, leftMargin=30,
                                     topMargin=30, bottomMargin=18)
        styles   = getSampleStyleSheet()
        
        # Define a custom RoundedBackground Flowable
        class RoundedBackground(Flowable):
            def __init__(self, width, height, color):
                Flowable.__init__(self)
                self.width = width
                self.height = height
                self.color = color

            def draw(self):
                self.canv.saveState()
                self.canv.setFillColor(self.color)
                self.canv.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
                self.canv.restoreState()

        styleN   = styles['Normal']
        centered = ParagraphStyle('centered', parent=styleN,
                                  alignment=TA_CENTER, fontSize=16, spaceAfter=6)
        centered_sm = ParagraphStyle('centered_sm', parent=styleN,
                                     alignment=TA_CENTER, fontSize=10, spaceAfter=6)
        elements = [Spacer(1, 30)]

        if _check_logo():
            try:
                logo = RLImage(_logo_path(), width=30*mm, height=30*mm)
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

        # Payment status line — direct SQL lookup (no full table scan)
        try:
            _conn = get_db()
            _c    = _conn.cursor()
            _c.execute(
                "SELECT status, payment_date, payment_method FROM invoice_log "
                "WHERE filename=? ORDER BY id DESC LIMIT 1",
                (data['pdf_filename'],)
            )
            _row = _c.fetchone()
            _conn.close()
            if _row:
                _st, _pd, _pm = _row['status'], _row['payment_date'], _row['payment_method']
                if _st == 'Paid':
                    elements.append(Paragraph(
                        f"<b>Payment Status:</b> Paid on {_pd} ({_pm})", styleN))
                elif _st == 'Partial':
                    elements.append(Paragraph(
                        f"<b>Payment Status:</b> Partial payment on {_pd} ({_pm})", styleN))
        except Exception:
            pass

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
