import eel
import os
import sys
import json
import webbrowser
import backend
import threading
import subprocess
import time
import pandas as pd
from datetime import datetime
from backend import OUTPUT_DIR, EXPORTS_DIR

# Helper for PyInstaller resource paths
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Initialize Eel with the web folder
eel.init(resource_path('web'))

# Initialize SQLite database (creates tables + migrates JSON on first run)
backend.init_db()

# Start auto-backup in background
threading.Thread(target=backend.run_auto_backup, daemon=True).start()

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@eel.expose
def get_dashboard_stats():
    logs         = backend.load_logs()
    total_amount = sum(float(l.get('amount', 0)) for l in logs)
    paid_amount  = sum(float(l.get('amount', 0)) for l in logs
                       if str(l.get('status', '')).lower() in ['paid', 'partial'])
    pending      = total_amount - paid_amount
    return {
        "revenue":         total_amount,
        "paid":            paid_amount,
        "pending":         pending,
        "invoice_count":   len(logs),
        "collection_rate": backend.get_collection_rate()
    }

@eel.expose
def get_monthly_revenue():
    return backend.get_monthly_revenue()

@eel.expose
def get_monthly_revenue_filtered(date_from, date_to):
    return backend.get_monthly_revenue_filtered(date_from, date_to)

@eel.expose
def get_plan_breakdown():
    return backend.get_plan_breakdown()

@eel.expose
def get_plan_breakdown_filtered(date_from, date_to):
    return backend.get_plan_breakdown_filtered(date_from, date_to)

@eel.expose
def get_outstanding_dues():
    return backend.get_outstanding_dues()

@eel.expose
def get_filtered_dashboard(date_from, date_to):
    """
    date_from / date_to: "YYYY-MM-DD"
    Returns all dashboard data filtered to that range in one go.
    """
    return {
        "stats":   backend.get_dashboard_stats_filtered(date_from, date_to),
        "monthly": backend.get_monthly_revenue_filtered(date_from, date_to),
        "logs":    backend.get_logs_filtered(date_from, date_to),
        "collection_rate": backend.get_collection_rate_filtered(date_from, date_to)
    }

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────


@eel.expose
def get_customers():
    return backend.load_customers()

@eel.expose
def update_customer_notes(customer_id, notes, tags, connection_status):
    try:
        backend.update_customer_notes(customer_id, notes, tags, connection_status)
        return {"status": "success", "message": "Customer updated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def import_customers_csv_data(csv_text):
    try:
        count = backend.import_customers_csv_data(csv_text)
        return {"status": "success", "message": f"Imported {count} customer(s)."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def get_customer_profile(customer_id):
    try:
        customers = backend.load_customers()
        logs      = backend.load_logs()

        customer = next((c for c in customers if c.get('customer_id') == customer_id), None)
        if not customer:
            return {"status": "error", "message": "Customer not found"}

        customer_logs = [l for l in logs if str(l.get('customer_id')) == str(customer_id)]

        total_paid   = sum(float(l.get('amount', 0)) for l in customer_logs if l.get('status') == 'Paid')
        pending_dues = sum(float(l.get('amount', 0)) for l in customer_logs if l.get('status') != 'Paid')

        return {
            "status":   "success",
            "customer": customer,
            "logs":     list(reversed(customer_logs)),
            "stats": {
                "total_paid":     total_paid,
                "pending_dues":   pending_dues,
                "total_invoices": len(customer_logs)
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── INVOICE HISTORY ───────────────────────────────────────────────────────────

@eel.expose
def get_history():
    return list(reversed(backend.load_logs()))

@eel.expose
def mark_invoice_paid(invoice_num):
    try:
        backend.mark_invoice_paid_db(invoice_num, method='Manual Entry')
        return {"status": "success", "message": f"Invoice {invoice_num} marked as paid."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def mark_invoice_paid_with_method(invoice_num, method):
    try:
        backend.mark_invoice_paid_db(invoice_num, method=method)
        return {"status": "success", "message": f"Invoice {invoice_num} marked as paid via {method}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def check_duplicate_invoice(customer_id, billing_from, billing_to):
    try:
        return backend.check_duplicate_invoice(customer_id, billing_from, billing_to)
    except Exception as e:
        return False

# ── INVOICE GENERATION ────────────────────────────────────────────────────────

@eel.expose
def generate_invoice(data):
    try:
        invoice_num   = backend.load_invoice_number()
        settings      = backend.load_settings()
        inv_prefix    = settings.get('invoice_prefix', 'TF/25-26/HR/')

        customer_name = data.get('name', 'Customer').replace(' ', '_')
        billing_from  = data.get('billing_from', '')

        try:
            parts      = billing_from.split('-')  # "01-Mar-2026"
            month_year = f"{parts[1]}_{parts[2]}" if len(parts) >= 3 else datetime.now().strftime("%b_%Y")
        except Exception:
            month_year = datetime.now().strftime("%b_%Y")

        clean_name   = "".join(ch for ch in customer_name if ch.isalnum() or ch == '_')
        pdf_filename = f"{clean_name}_{month_year}.pdf"
        invoice_data = {**data, 'invoice_num': invoice_num, 'pdf_filename': pdf_filename}

        backend.generate_pdf(invoice_data)
        backend.save_invoice_number(invoice_num)

        backend.append_log({
            "datetime":       datetime.now().strftime("%d-%m-%Y %H:%M"),
            "customer_name":  data.get('name', ''),
            "customer_id":    data.get('customer_id', ''),
            "phone":          data.get('phone', ''),
            "invoice_num":    f"{inv_prefix}{invoice_num}",
            "amount":         float(data.get('total_amount', 0)),
            "paid_amount":    0,
            "filename":       pdf_filename,
            "status":         data.get('payment_status', 'Unpaid'),
            "payment_method": data.get('payment_method', 'None') or 'None',
            "payment_date":   datetime.now().strftime("%d-%m-%Y") if data.get('payment_status') in ['Paid','Partial'] else '',
            "plan":           data.get('plan', ''),
        })

        if data.get('save_customer'):
            backend.save_customer({
                "name":             data.get('name', ''),
                "customer_id":      data.get('customer_id', ''),
                "tenant_name":      data.get('tenant_name', ''),
                "phone":            data.get('phone', ''),
                "customer_address": data.get('customer_address', ''),
                "customer_gstin":   data.get('customer_gstin', ''),
            })

        webbrowser.open(os.path.join(OUTPUT_DIR, pdf_filename))

        return {"status": "success",
                "message": f"Invoice {invoice_num} generated! Saved as {pdf_filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── EXPORT ────────────────────────────────────────────────────────────────────

@eel.expose
def export_customers_csv():
    try:
        customers = backend.load_customers()
        if not customers:
            return {"status": "error", "message": "No customers to export."}
        filename = os.path.join(EXPORTS_DIR, f"Customers_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        pd.DataFrame(customers).to_csv(filename, index=False)
        backend.open_folder(EXPORTS_DIR)
        return {"status": "success", "message": f"Exported {len(customers)} customers. Folder opened."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def export_logs_csv():
    try:
        logs = backend.load_logs()
        if not logs:
            return {"status": "error", "message": "No logs to export."}
        filename = os.path.join(EXPORTS_DIR, f"Invoice_History_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        pd.DataFrame(logs).to_csv(filename, index=False)
        backend.open_folder(EXPORTS_DIR)
        return {"status": "success", "message": f"Exported {len(logs)} invoices. Folder opened."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── PDF / WHATSAPP ─────────────────────────────────────────────────────────────

@eel.expose
def open_pdf(filename):
    try:
        # Sanitize: prevent directory traversal
        safe_name = os.path.basename(filename)
        path = os.path.join(OUTPUT_DIR, safe_name)
        if os.path.exists(path):
            webbrowser.open(path)
            return {"status": "success"}
        return {"status": "error", "message": f"File not found: {safe_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def automate_whatsapp_attachment(phone, message, filename):
    import urllib.parse, webbrowser

    def _auto_wa():
        wa_link  = f"whatsapp://send?phone={phone}&text={urllib.parse.quote(message)}"
        # Sanitize filename to prevent path traversal
        safe_name = os.path.basename(filename)
        filepath  = os.path.join(OUTPUT_DIR, safe_name)
        if os.path.exists(filepath):
            try:
                ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetFileDropList([System.Collections.Specialized.StringCollection]@('{filepath}'))"
                subprocess.run(["powershell", "-command", ps_cmd], creationflags=0x08000000)
                os.startfile(wa_link)
                time.sleep(8)
                import pyautogui
                sw, sh = pyautogui.size()
                pyautogui.click(sw / 2, sh / 2)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(2)
                pyautogui.press('enter')
            except Exception as e:
                print(f"Automation Error: {e}")

    threading.Thread(target=_auto_wa, daemon=True).start()
    return {"status": "success"}

# ── PLANS / SETTINGS ──────────────────────────────────────────────────────────

@eel.expose
def get_plans():
    return backend.get_plans_list()

@eel.expose
def save_plans(plans):
    try:
        backend.save_plans_list(plans)
        return {"status": "success", "message": "Plans saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def get_settings():
    return backend.load_settings()

@eel.expose
def save_settings_data(data):
    try:
        backend.save_settings(data)
        return {"status": "success", "message": "Settings saved successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def get_version():
    try:
        version_file = resource_path("version.json")
        with open(version_file, 'r') as f:
            return json.load(f).get("version", "?")
    except Exception:
        return "?"

@eel.expose
def reset_invoice_counter():
    try:
        backend.save_invoice_number(2058)
        return {"status": "success", "message": "Invoice counter reset to 2059."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── APP LOGS ──────────────────────────────────────────────────────────────────

@eel.expose
def get_app_logs():
    return backend.get_app_logs(150)

# ── AUTO-UPDATE ───────────────────────────────────────────────────────────────

@eel.expose
def check_for_updates():
    try:
        import requests as _req
        repo = "bloodwraith8851/T.F.N-Billing"
        url  = f"https://api.github.com/repos/{repo}/releases/latest"
        version_file = resource_path("version.json")
        if not os.path.exists(version_file):
            return {"status": "error", "message": "version.json not found"}
        with open(version_file, 'r') as f:
            local_version = json.load(f).get("version", "0.0.0")

        response = _req.get(url, timeout=10)
        if response.status_code == 404:
            return {"status": "no_update", "local": local_version,
                    "message": "No releases found on GitHub yet."}

        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release.get("tag_name", "").replace("v", "")
            if not latest_version:
                return {"status": "no_update", "local": local_version}

            try:
                latest_tuple = tuple(int(x) for x in latest_version.split('.'))
                local_tuple  = tuple(int(x) for x in local_version.split('.'))
            except ValueError:
                latest_tuple = local_tuple = (0,)

            if latest_tuple > local_tuple:
                assets       = latest_release.get("assets", [])
                installer_url = next(
                    (a.get("browser_download_url") for a in assets if "Setup.exe" in a.get("name","")), None
                ) or next(
                    (a.get("browser_download_url") for a in assets if a.get("name","").endswith(".exe")), None
                )
                return {
                    "status":  "update_available",
                    "local":   local_version,
                    "latest":  latest_version,
                    "notes":   latest_release.get("body", ""),
                    "url":     installer_url
                }

        return {"status": "no_update", "local": local_version}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def download_and_install_update(url):
    if not url:
        return {"status": "error", "message": "No download URL provided"}

    def _do_update():
        dest_path = ""
        try:
            temp_dir  = os.environ.get("TEMP", os.path.expanduser("~"))
            dest_path = os.path.join(temp_dir, "Thunderstorm_Billing_Update_Setup.exe")
            response  = requests.get(url, stream=True, timeout=30, allow_redirects=True)
            response.raise_for_status()
            total_size     = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            eel.update_download_status(f"Downloading... {percent}%")
            eel.update_download_status("Finalizing... Launching Installer")
            if os.path.exists(dest_path):
                subprocess.Popen([dest_path], shell=True)
                time.sleep(1)
                os._exit(0)
            else:
                raise Exception("Downloaded file not found on disk.")
        except Exception as e:
            try:
                eel.update_download_status(f"Update Failed: {e}")
                eel.handle_update_error(str(e))
            except:
                pass

    threading.Thread(target=_do_update, daemon=True).start()
    return {"status": "success"}

# ── NEW EXPOSED FUNCTIONS ─────────────────────────────────────────────────────

@eel.expose
def get_recent_logs_eel(n=5):
    return backend.get_recent_logs(n)

@eel.expose
def get_unpaid_count_this_month():
    return backend.get_unpaid_count_this_month()

@eel.expose
def get_overdue_invoices():
    return backend.get_overdue_invoices()

@eel.expose
def get_whatsapp_template():
    return backend.get_whatsapp_template()

@eel.expose
def save_whatsapp_template(template):
    try:
        backend.save_whatsapp_template(template)
        return {"status": "success", "message": "WhatsApp template saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def get_monthly_target():
    return backend.get_monthly_target()

@eel.expose
def save_monthly_target(target):
    try:
        backend.save_monthly_target(target)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def generate_sample_pdf():
    return backend.generate_sample_pdf()

@eel.expose
def open_exports_folder():
    backend.open_folder(EXPORTS_DIR)
    return {"status": "success"}

@eel.expose
def save_customer_full(data):
    try:
        backend.save_customer_full(data)
        return {"status": "success", "message": "Customer saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def generate_bulk_invoices(customer_ids, plan, billing_from, billing_to, months,
                           total_amount, payment_status, payment_method):
    try:
        result = backend.generate_bulk_invoices(
            customer_ids, plan, billing_from, billing_to, int(months),
            float(total_amount), payment_status, payment_method
        )
        return {"status": "success", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── APP START ─────────────────────────────────────────────────────────────────

def start_app():
    try:
        eel.start('index.html', size=(1280, 820),
                  mode='chrome', host='localhost', port=0)
    except EnvironmentError:
        eel.start('index.html', size=(1280, 820),
                  mode='edge',   host='localhost', port=0)

if __name__ == '__main__':
    start_app()
