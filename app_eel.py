import eel
import os
import sys
import backend
import threading

# Helper for PyInstaller resource paths
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Initialize Eel with the web folder
eel.init(resource_path('web'))

# Expose backend functions to Javascript
@eel.expose
def get_dashboard_stats():
    logs = backend.load_logs()
    total_amount = sum(float(l.get('amount', 0)) for l in logs)
    paid_amount = sum(float(l.get('amount', 0)) for l in logs if str(l.get('status', '')).lower() in ['paid', 'partial'])
    pending = total_amount - paid_amount
    return {
        "revenue": total_amount,
        "paid": paid_amount,
        "pending": pending
    }

@eel.expose
def get_customers():
    return backend.load_customers()

@eel.expose
def get_history():
    return list(reversed(backend.load_logs()))

@eel.expose
def mark_invoice_paid(invoice_num):
    try:
        logs = backend.load_logs()
        for log in logs:
            if log['invoice_num'] == invoice_num:
                log['status'] = 'Paid'
                log['payment_method'] = 'Manual Entry'
                log['payment_date'] = backend.datetime.now().strftime("%d-%m-%Y")
                break
        backend.save_logs(logs)
        return {"status": "success", "message": f"Invoice {invoice_num} marked as paid."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def export_customers_csv():
    try:
        customers = backend.load_customers()
        if not customers:
            return {"status": "error", "message": "No customers found."}
        import pandas as pd
        df = pd.DataFrame(customers)
        os.makedirs('exports', exist_ok=True)
        filename = f"exports/Customers_Export_{backend.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return {"status": "success", "message": f"Exported successfully to {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def export_logs_csv():
    try:
        logs = backend.load_logs()
        if not logs:
            return {"status": "error", "message": "No invoice history found."}
        import pandas as pd
        df = pd.DataFrame(logs)
        os.makedirs('exports', exist_ok=True)
        filename = f"exports/Invoice_History_{backend.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return {"status": "success", "message": f"Exported successfully to {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def automate_whatsapp_attachment(phone, message, filename):
    """Automatically attaches and sends a PDF via WhatsApp Desktop using VBScript and Clipboard"""
    import urllib.parse
    import webbrowser
    import subprocess
    import time
    import threading
    import os

    def _auto_wa():
        # Using whatsapp:// protocol opens the native Desktop App which natively accepts file pasting
        wa_link = f"whatsapp://send?phone={phone}&text={urllib.parse.quote(message)}"
        filepath = os.path.abspath(os.path.join('output_invoices', filename))
        
        if os.path.exists(filepath):
            try:
                print(f"Preparing to send {filename} to {phone} via Desktop App...")
                
                # 1. Copy the file itself to the Windows clipboard (like Ctrl+C on a file)
                ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetFileDropList([System.Collections.Specialized.StringCollection]@('{filepath}'))"
                subprocess.run(["powershell", "-command", ps_cmd], creationflags=0x08000000)
                
                # 2. Open WhatsApp Desktop Native App
                os.startfile(wa_link)
                
                # 3. Wait 8 seconds for WhatsApp Desktop to fully load the chat
                time.sleep(8)
                
                # 4. Use PyAutoGUI for secure keyboard injection (UWP app compatible)
                import pyautogui
                
                # Click center of screen to ensure WhatsApp Desktop is strictly focused
                screenWidth, screenHeight = pyautogui.size()
                pyautogui.click(screenWidth / 2, screenHeight / 2)
                time.sleep(0.5)
                
                # Press Ctrl+V securely
                pyautogui.hotkey('ctrl', 'v')
                
                # Wait 2 seconds for attachment preview to load
                time.sleep(2)
                
                # Press Enter to send
                pyautogui.press('enter')
                
                print("WhatsApp Desktop automation script completed.")
                
            except Exception as e:
                print(f"Automation Error: {e}")

    threading.Thread(target=_auto_wa, daemon=True).start()
    return {"status": "success"}

@eel.expose
def get_plans():
    return backend.PLANS

@eel.expose
def open_pdf(filename):
    """Open a generated PDF invoice in the default viewer."""
    try:
        import webbrowser
        path = os.path.abspath(os.path.join('output_invoices', filename))
        if os.path.exists(path):
            webbrowser.open(path)
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"File not found: {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def generate_invoice(data):
    try:
        invoice_num = backend.load_invoice_number()
        
        # Format the filename: CustomerName_Month_Year.pdf
        customer_name = data.get('name', 'Customer').replace(' ', '_')
        billing_from = data.get('billing_from', '')
        
        # frontend flatpickr sends 'd-M-Y' (e.g., '01-Dec-2025')
        try:
            parts = billing_from.split('-')
            if len(parts) >= 3:
                month = parts[1]
                year = parts[2]
                month_year = f"{month}_{year}"
            else:
                # Fallback to current month if parsing fails
                month_year = backend.datetime.now().strftime("%b_%Y")
        except:
            month_year = "Unknown"
            
        # Optional: Clean any weird characters
        clean_name = "".join(c for c in customer_name if c.isalnum() or c == '_')
        
        pdf_filename = f"{clean_name}_{month_year}.pdf"
        
        invoice_data = {**data, 'invoice_num': invoice_num, 'pdf_filename': pdf_filename}
        
        backend.generate_pdf(invoice_data)
        backend.save_invoice_number(invoice_num)
        
        # Log invoice
        logs = backend.load_logs()
        from datetime import datetime as dt
        logs.append({
            "datetime": dt.now().strftime("%d-%m-%Y %H:%M"),
            "customer_name": data.get('name', ''),
            "customer_id": data.get('customer_id', ''),
            "phone": data.get('phone', ''),
            "invoice_num": f"TF/25-26/HR/{invoice_num}",
            "amount": float(data.get('total_amount', 0)),
            "filename": pdf_filename,
            "status": data.get('payment_status', 'Unpaid'),
            "payment_method": data.get('payment_method', 'None') or 'None'
        })
        backend.save_logs(logs)
        
        # Save customer (only clean customer fields, not invoice fields)
        if data.get('save_customer'):
            customer_data = {
                "name": data.get('name', ''),
                "customer_id": data.get('customer_id', ''),
                "tenant_name": data.get('tenant_name', ''),
                "phone": data.get('phone', ''),
                "customer_address": data.get('customer_address', ''),
                "customer_gstin": data.get('customer_gstin', '')
            }
            backend.save_customer(customer_data)
            
        # Open PDF
        import webbrowser
        webbrowser.open(os.path.abspath(os.path.join('output_invoices', pdf_filename)))
        
        return {"status": "success", "message": f"Invoice {invoice_num} generated! File saved as {pdf_filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@eel.expose
def get_customer_profile(customer_id):
    try:
        customers = backend.load_customers()
        logs = backend.load_logs()
        
        # Find exact customer
        customer = next((c for c in customers if c.get('customer_id') == customer_id), None)
        if not customer:
            return {"status": "error", "message": "Customer not found"}
            
        # Filter logs just for this customer (by ID for accuracy)
        customer_logs = [log for log in logs if str(log.get('customer_id')) == str(customer_id)]
        
        # Calculate stats
        total_paid = sum(float(l.get('amount', 0)) for l in customer_logs if l.get('status') == 'Paid')
        pending_dues = sum(float(l.get('amount', 0)) for l in customer_logs if l.get('status') != 'Paid')
        
        return {
            "status": "success",
            "customer": customer,
            "logs": list(reversed(customer_logs)),
            "stats": {
                "total_paid": total_paid,
                "pending_dues": pending_dues,
                "total_invoices": len(customer_logs)
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def start_app():
    # Application launch options
    try:
        eel.start('index.html', size=(1200, 800), 
                  mode='chrome', # Uses Chrome window mode (no tabs/address bar)
                  host='localhost',
                  port=0) # Automatic port
    except EnvironmentError:
        # Fallback to Edge if Chrome is not installed
        eel.start('index.html', size=(1200, 800), 
                  mode='edge',
                  host='localhost',
                  port=0)

if __name__ == '__main__':
    start_app()
