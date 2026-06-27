"""
seed_demo_data.py — Inserts rich dummy data into the Thunderstorm Billing SQLite DB
to test the designer timeline customer profile.
Run: python seed_demo_data.py
"""
import os
import sqlite3
from datetime import datetime, timedelta
import random

DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ThunderstormBilling')
DB_FILE  = os.path.join(DATA_DIR, 'billing.db')

os.makedirs(DATA_DIR, exist_ok=True)

# ── Dummy customers ──────────────────────────────────────────────────────────
CUSTOMERS = [
    {
        'customer_id':      'TFN-DEMO-001',
        'name':             'Rajesh Kumar Sharma',
        'tenant_name':      'Sharma Residency',
        'phone':            '9876543210',
        'customer_address': 'A-12, Sector 7, Vaishali, Ghaziabad',
        'customer_gstin':   '09ABCDE1234F1Z5',
        'customer_email':   'rajesh.sharma@gmail.com',
        'notes':            'Prefers WhatsApp for reminders. Always pays on time.',
        'tags':             'VIP, Residential',
        'connection_status': 'Active',
        'created_at':       '2024-01-10',
    },
    {
        'customer_id':      'TFN-DEMO-002',
        'name':             'Priya Mehta',
        'tenant_name':      'Mehta Towers',
        'phone':            '9123456789',
        'customer_address': 'B-4, Green Park, New Delhi',
        'customer_gstin':   '',
        'customer_email':   'priya.mehta@outlook.com',
        'notes':            '3-month plan subscriber.',
        'tags':             'Residential, Monthly',
        'connection_status': 'Active',
        'created_at':       '2024-03-15',
    },
    {
        'customer_id':      'TFN-DEMO-003',
        'name':             'Aakash Fiber Solutions',
        'tenant_name':      '',
        'phone':            '9988776655',
        'customer_address': 'Plot 22, Industrial Area, Noida',
        'customer_gstin':   '09XYZAB5678G2H1',
        'customer_email':   'billing@aakashfiber.in',
        'notes':            'Corporate. Needs GST invoice for every payment.',
        'tags':             'Corporate, GST',
        'connection_status': 'Active',
        'created_at':       '2023-11-20',
    },
    {
        'customer_id':      'TFN-DEMO-004',
        'name':             'Sunita Devi',
        'tenant_name':      'Devi Bhawan',
        'phone':            '9011223344',
        'customer_address': 'C-17, Old Town, Meerut',
        'customer_gstin':   '',
        'customer_email':   '',
        'notes':            'Pays in cash. Occasional delay.',
        'tags':             'Residential, Cash',
        'connection_status': 'Suspended',
        'created_at':       '2023-08-05',
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────
PLANS = ['100 MBPS UNLIMITED', '200 MBPS UNLIMITED', '500 MBPS UNLIMITED', '1 GBPS UNLIMITED']

def make_invoices(customer, count=8):
    rows = []
    base_date = datetime.now() - timedelta(days=30 * count)
    inv_num   = random.randint(1000, 2000)
    plan      = random.choice(PLANS)
    amounts   = [399, 499, 599, 799, 999, 1199]
    amount    = random.choice(amounts)
    statuses  = ['Paid'] * 5 + ['Unpaid'] * 2 + ['Partial']

    for i in range(count):
        dt     = base_date + timedelta(days=30 * i)
        status = statuses[i % len(statuses)]
        paid   = amount if status == 'Paid' else (amount // 2 if status == 'Partial' else 0)
        method = random.choice(['Cash', 'UPI', 'Bank Transfer']) if status != 'Unpaid' else ''

        rows.append({
            'datetime':       dt.strftime('%Y-%m-%d %H:%M'),
            'customer_name':  customer['name'],
            'customer_id':    customer['customer_id'],
            'phone':          customer['phone'],
            'invoice_num':    f"INV-{inv_num + i:04d}",
            'amount':         amount,
            'paid_amount':    paid,
            'filename':       f"invoice_{inv_num + i:04d}.pdf",
            'status':         status,
            'payment_method': method,
            'payment_date':   dt.strftime('%Y-%m-%d') if status != 'Unpaid' else '',
            'plan':           plan,
        })
    return rows

# ── Seed ─────────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_FILE)
c    = conn.cursor()

inserted_customers = 0
inserted_invoices  = 0

for cust in CUSTOMERS:
    c.execute("SELECT COUNT(*) FROM customers WHERE customer_id=?", (cust['customer_id'],))
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO customers
                     (customer_id, name, tenant_name, phone, customer_address,
                      customer_gstin, customer_email, notes, tags, connection_status, created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                  (cust['customer_id'], cust['name'], cust['tenant_name'],
                   cust['phone'], cust['customer_address'], cust['customer_gstin'],
                   cust['customer_email'], cust['notes'], cust['tags'],
                   cust['connection_status'], cust['created_at']))
        inserted_customers += 1
        print(f"  + Customer: {cust['name']}")
    else:
        print(f"  - Skipped (exists): {cust['name']}")

    # Always insert invoices if none exist for this customer
    c.execute("SELECT COUNT(*) FROM invoice_log WHERE customer_id=?", (cust['customer_id'],))
    if c.fetchone()[0] == 0:
        invoices = make_invoices(cust, count=8)
        for inv in invoices:
            c.execute('''INSERT INTO invoice_log
                         (datetime, customer_name, customer_id, phone, invoice_num,
                          amount, paid_amount, filename, status, payment_method, payment_date, plan)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (inv['datetime'], inv['customer_name'], inv['customer_id'],
                       inv['phone'], inv['invoice_num'], inv['amount'],
                       inv['paid_amount'], inv['filename'], inv['status'],
                       inv['payment_method'], inv['payment_date'], inv['plan']))
            inserted_invoices += 1
        print(f"    -> {len(invoices)} invoices inserted")

conn.commit()
conn.close()

print(f"\nDone!  {inserted_customers} customers, {inserted_invoices} invoices seeded into:\n   {DB_FILE}")
