import os
import json
from datetime import datetime, timedelta
import traceback
import logging

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import smtplib
from email.message import EmailMessage

# For PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_CENTER
import PIL.Image

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants and configurations
LOGO_PATH = "assets/logo.png"
ICO_PATH = "assets/logo.ico"
GST_RATE = 0.09  # 9% GST
PLANS = [
    "100 MBPS UNL",
    "200 MBPS UNL",
    "300 MBPS UNL",
    "400 MBPS UNL",
    "500 MBPS UNL"
]

# File paths
TRACKER_FILE = "invoice_tracker.json"
INVOICE_LOG_FILE = "invoice_log.json"
CUSTOMERS_FILE = "customers.json"
USERS_FILE = "users.json"


def initialize_tracker():
    """Initialize the tracker file with default values if it doesn't exist"""
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'w') as f:
            json.dump({"last_invoice_number": 2058}, f)

def load_invoice_number():
    initialize_tracker()
    try:
        with open(TRACKER_FILE) as f:
            content = f.read().strip()
            if not content:
                return 2058
            data = json.loads(content)
            return data.get("last_invoice_number", 2058) + 1
    except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Error loading invoice number: {str(e)}")
        return 2059

def save_invoice_number(number):
    with open(TRACKER_FILE, 'w') as f:
        json.dump({"last_invoice_number": number}, f)

def calculate_amounts(total_amount):
    base_amount = round(total_amount / (1 + 2 * GST_RATE), 2)
    gst = round(base_amount * GST_RATE, 2)
    return base_amount, gst

def load_customers():
    try:
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        return []
    except Exception as e:
        logger.error(f"Error loading customers: {str(e)}")
        return []

def save_customer(data):
    try:
        customers = load_customers()
        exists = False
        for i, cust in enumerate(customers):
            if cust['customer_id'] == data['customer_id']:
                customers[i] = data
                exists = True
                break
        if not exists:
            customers.append(data)
        
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving customer: {str(e)}")
        raise

def load_logs():
    try:
        if os.path.exists(INVOICE_LOG_FILE):
            with open(INVOICE_LOG_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        return []
    except Exception as e:
        logger.error(f"Error loading logs: {str(e)}")
        return []

def save_logs(logs):
    with open(INVOICE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def check_logo():
    if not os.path.exists(LOGO_PATH):
        return False
    try:
        with PIL.Image.open(LOGO_PATH) as img:
            if img.format != 'PNG':
                return False
            return True
    except:
        return False

class Watermark(Flowable):
    def __init__(self, logo_path, width=100, height=100, opacity=0.1):
        Flowable.__init__(self)
        self.logo_path = logo_path
        self.width = width
        self.height = height
        self.opacity = opacity

    def draw(self):
        if os.path.exists(self.logo_path):
            self.canv.saveState()
            self.canv.setFillAlpha(self.opacity)
            page_width, page_height = A4
            x = (page_width - self.width) / 2
            y = (page_height - self.height) / 2 + (page_height * 0.1)
            self.canv.translate(x, y)
            # Use mask='auto' to respect PNG transparency, preventing the grey box issue
            self.canv.drawImage(self.logo_path, 0, 0, self.width, self.height, mask='auto')
            self.canv.restoreState()

def draw_watermark(canvas, doc):
    if check_logo():
        watermark = Watermark(LOGO_PATH, width=150*mm, height=150*mm, opacity=0.08)
        watermark.canv = canvas
        watermark.draw()

def generate_pdf(data):
    try:
        invoice_number = f"TF/25-26/HR/{data['invoice_num']}"
        filename = f"output_invoices/{data['pdf_filename']}"
        os.makedirs('output_invoices', exist_ok=True)
        
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        styleN = styles['Normal']
        
        centered = ParagraphStyle(name='centered', parent=styles['Normal'], alignment=TA_CENTER, fontSize=16, spaceAfter=6)
        centered_small = ParagraphStyle(name='centered_small', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=6)

        elements.append(Spacer(1, 30))

        if check_logo():
            try:
                logo = Image(LOGO_PATH, width=30*mm, height=30*mm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception as e:
                logger.error(f"Error adding logo: {str(e)}")

        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<b>TAX INVOICE</b>", centered))
        elements.append(Paragraph("(Original for recipient)", centered_small))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("<b>THUNDERSTORM FIBERNET</b>", centered))
        elements.append(Paragraph("Supplier Address: D-2/539, Shiv Durga Vihar, Lakkarpur, Faridabad, HR - 121009", centered_small))
        
        contact_info = (
            f"Supplier GSTIN: 06DJVPP9834G1ZD &nbsp;&nbsp;&nbsp;&nbsp; "
            f"Phone No: 8585986890 &nbsp;&nbsp;&nbsp;&nbsp; "
            f"Email: thunderstromfibernet@gmail.com"
        )
        elements.append(Paragraph(contact_info, centered_small))
        elements.append(Spacer(1, 20))

        info_data = [
            [
                Paragraph(
                    f"Customer Address: {data['customer_address']}<br/>"
                    f"Place of Supply: Haryana<br/>"
                    f"Customer GSTIN: {data.get('customer_gstin', '')}",
                    styleN
                ),
                Paragraph(
                    f"Invoice Number: {invoice_number}<br/>"
                    f"Invoice Date: {data.get('invoice_date', datetime.now().strftime('%d %b %Y'))}<br/>"
                    f"Tenant Name: {data['tenant_name']}<br/>"
                    f"Customer Id: {data['customer_id']}<br/>"
                    f"Billing Period: {data['billing_from']} - {data['billing_to']}<br/>"
                    f"Months: {data['months']}",
                    styleN
                )
            ]
        ]
        info_table = Table(info_data, colWidths=[250, 250])
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        base_amount, gst = calculate_amounts(float(data['total_amount']))
        discount = float(data.get('discount', 0) or 0)
        late_fee = float(data.get('late_fee', 0) or 0)
        total = float(data['total_amount']) - discount + late_fee

        table_data = [
            ["S.No", "Particular", "HSN/SAC", "Amount", "Rate", "CGST", "SGST", "Total"],
            ["1", f"{data['plan']} - {data['months']} Month{'s' if data['months'] != '1' else ''}", "998422", f"Rs. {base_amount:.2f}", "9.0%", f"Rs. {gst:.2f}", f"Rs. {gst:.2f}", f"Rs. {float(data['total_amount']):.2f}"],
        ]
        if discount:
            table_data.append(["", "Discount", "", "", "", "", "", f"-Rs. {discount:.2f}"])
        if late_fee:
            table_data.append(["", "Late Fee", "", "", "", "", "", f"+Rs. {late_fee:.2f}"])
        table_data.append(["", "Total Invoice Amount", "", "", "", "", "", f"Rs. {total:.2f}"])
        
        table = Table(table_data, colWidths=[30, 120, 60, 60, 40, 60, 60, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e3f2fd')),
            ('ALIGN', (0, 1), (0, 1), 'CENTER'),
            ('ALIGN', (1, 1), (1, 1), 'LEFT'),  
            ('FONTSIZE', (1, 1), (1, 1), 8),    
            ('FONTSIZE', (0, 1), (0, 1), 9),    
            ('FONTSIZE', (2, 1), (-1, 1), 9),   
            ('ALIGN', (2, 1), (-1, 1), 'CENTER'),
            ('BACKGROUND', (0, 2), (-2, 2), colors.HexColor('#ffe082')),
            ('SPAN', (1, 2), (6, 2)),
            ('ALIGN', (1, 2), (6, 2), 'LEFT'),
            ('ALIGN', (7, 2), (7, 2), 'RIGHT'),
            ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
            ('FONTNAME', (7, 2), (7, 2), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        if data.get('custom_notes'):
            elements.append(Paragraph(f"<b>Notes:</b> {data['custom_notes']}", styleN))

        log_status = ""
        logs = load_logs()
        for entry in logs:
            if entry['filename'] == data['pdf_filename']:
                if entry.get('status') == 'Paid':
                    log_status = f"<b>Payment Status:</b> Paid on {entry.get('payment_date', '')} ({entry.get('payment_method', '')})"
                elif entry.get('status') == 'Partial':
                    log_status = f"<b>Payment Status:</b> Partial payment on {entry.get('payment_date', '')} ({entry.get('payment_method', '')})"
                break
        if log_status:
            elements.append(Paragraph(log_status, styleN))

        elements.append(Paragraph(
            "This is a computer generated bill and does not require signature.<br/>"
            "For queries and complaints contact: 8585986890",
            styleN
        ))

        doc.build(elements, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
        return True
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}\n{traceback.format_exc()}")
        raise

# API Endpoints
@app.route('/')
def index():
    return send_file('templates/index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    logs = load_logs()
    total_invoices = len(logs)
    total_amount = sum(float(l.get('amount', 0)) for l in logs)
    paid_amount = sum(float(l.get('amount', 0)) for l in logs if l.get('status', '').lower() == 'paid')
    pending_amount = total_amount - paid_amount
    
    # Calculate some basic metrics for the charts
    # ...
    return jsonify({
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'recent_logs': logs[-10:] if logs else []
    })

@app.route('/api/customers', methods=['GET'])
def api_get_customers():
    return jsonify(load_customers())

@app.route('/api/customers', methods=['POST'])
def api_add_customer():
    data = request.json
    try:
        save_customer(data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/invoices/next_number', methods=['GET'])
def get_next_invoice_number():
    return jsonify({"next_number": load_invoice_number()})

@app.route('/api/invoices/generate', methods=['POST'])
def api_generate_invoice():
    data = request.json
    invoice_num = load_invoice_number()
    
    current_date = datetime.now()
    month_name = current_date.strftime("%B")
    pdf_filename = f"{data['customer_id']}_{month_name}_Invoice.pdf"
    
    invoice_data = {**data, 'invoice_num': invoice_num, 'pdf_filename': pdf_filename}
    
    try:
        generate_pdf(invoice_data)
        save_invoice_number(invoice_num)
        
        # Log it
        logs = load_logs()
        discount = float(data.get('discount', 0) or 0)
        late_fee = float(data.get('late_fee', 0) or 0)
        total = float(data['total_amount']) - discount + late_fee
        
        log_entry = {
            "datetime": current_date.strftime("%d-%m-%Y %H:%M:%S"),
            "customer_name": data['name'],
            "invoice_num": f"TF/25-26/HR/{invoice_num}",
            "amount": total,
            "filename": pdf_filename,
            "status": data.get('payment_status', 'Unpaid'),
            "payment_method": data.get('payment_method', '')
        }
        if data.get('payment_status') in ['Paid', 'Partial']:
            log_entry['payment_date'] = current_date.strftime("%d-%m-%Y")
            
        logs.append(log_entry)
        save_logs(logs)

        # Save customer if requested
        if data.get('save_customer'):
            customer_data = {
                "name": data['name'],
                "customer_id": data['customer_id'],
                "tenant_name": data.get('tenant_name', ''),
                "customer_address": data['customer_address'],
                "customer_gstin": data.get('customer_gstin', ''),
                "email": data.get('email', '')
            }
            save_customer(customer_data)
            
        return jsonify({"success": True, "filename": pdf_filename, "invoice_num": invoice_num})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/invoices/logs', methods=['GET'])
def api_get_logs():
    return jsonify(load_logs())

@app.route('/api/invoices/<filename>/view', methods=['GET'])
def view_invoice(filename):
    path = os.path.join('output_invoices', filename)
    if os.path.exists(path):
        return send_file(path)
    return "Not found", 404

def run_server():
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()
