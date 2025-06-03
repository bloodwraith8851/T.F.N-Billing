import os
import json
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import tkinter as tk
from tkinter import messagebox, Toplevel, Listbox, Scrollbar, RIGHT, Y, END, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Querybox, DatePickerDialog
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
import smtplib
from email.message import EmailMessage
import csv
import zipfile
import pandas as pd
import PIL.Image
import logging
import sys
import traceback

# Define debug log file path
DEBUG_LOG_FILE = os.path.join("logs", "tfn_billing_debug.log")

# Check if matplotlib is available
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    logging.warning("Matplotlib not available. Dashboard visualizations will be disabled.")

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging with both file and console handlers
logging.basicConfig(level=logging.DEBUG)

# Create file handler
file_handler = logging.FileHandler(DEBUG_LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Get the root logger and add handlers
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_function_entry_exit(func):
    """Decorator to log function entry and exit"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Entering function: {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting function: {func_name}")
            return result
        except Exception as e:
            logger.error(f"Error in function {func_name}: {str(e)}\n{traceback.format_exc()}")
            raise
    return wrapper

@log_function_entry_exit
def show_error_message(title, message, error=None):
    """Show error message in a dialog and log it"""
    if error:
        logger.error(f"{message}\nError: {str(error)}\n{traceback.format_exc()}")
        messagebox.showerror(title, f"{message}\n\nError: {str(error)}")
    else:
        logger.error(message)
        messagebox.showerror(title, message)

# Add debug logging to PDF generation
@log_function_entry_exit
def generate_pdf(data):
    """Generate PDF invoice with debug logging"""
    try:
        logger.info(f"Starting PDF generation for invoice {data['invoice_num']}")
        logger.debug(f"PDF data: {json.dumps(data, indent=2)}")
        
        invoice_number = f"TF/25-26/HR/{data['invoice_num']}"
        filename = f"output_invoices/{data['pdf_filename']}"
        
        logger.debug(f"Creating PDF: {filename}")
        logger.debug(f"Using logo from: {LOGO_PATH}")
        
        # Create output directory if it doesn't exist
        os.makedirs('output_invoices', exist_ok=True)
        
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        styleN = styles['Normal']
        styleH = styles['Heading1']

        logger.debug("Creating PDF styles")
        # Create centered styles
        centered = ParagraphStyle(
            name='centered',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=6
        )
        centered_small = ParagraphStyle(
            name='centered_small',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=10,
            spaceAfter=6
        )

        # Add some space at the top
        elements.append(Spacer(1, 30))

        logger.debug("Adding logo")
        # Logo and Title
        if check_logo():
            try:
                # Center the logo
                logo = Image(LOGO_PATH, width=30*mm, height=30*mm)
                logo.hAlign = 'CENTER'  # Center align the logo
                elements.append(logo)
                logger.debug("Logo added successfully")
            except Exception as e:
                logger.error(f"Error adding logo: {str(e)}")
                messagebox.showwarning(
                    "Logo Error",
                    "Could not add logo to invoice. The invoice will be generated without the logo."
                )

        # Add some space after logo
        elements.append(Spacer(1, 12))
        
        logger.debug("Adding header information")
        elements.append(Paragraph("<b>TAX INVOICE</b>", centered))
        elements.append(Paragraph("(Original for recipient)", centered_small))
        elements.append(Spacer(1, 12))

        # Company Info
        elements.append(Paragraph("<b>THUNDERSTORM FIBERNET</b>", centered))
        elements.append(Paragraph(
            "Supplier Address: D-2/539, Shiv Durga Vihar, Lakkarpur, Faridabad, HR - 121009",
            centered_small
        ))
        
        # Format contact info with spacing
        contact_info = (
            f"Supplier GSTIN: 06DJVPP9834G1ZD &nbsp;&nbsp;&nbsp;&nbsp; "
            f"Phone No: 8585986890 &nbsp;&nbsp;&nbsp;&nbsp; "
            f"Email: thunderstromfibernet@gmail.com"
        )
        elements.append(Paragraph(contact_info, centered_small))
        elements.append(Spacer(1, 20))  # Add more space before customer info

        logger.debug("Adding customer information")
        # Customer and Invoice Info
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
                    f"Invoice Date: {datetime.now().strftime('%d %b %Y')}<br/>"
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

        logger.debug("Calculating amounts")
        # Table Data
        base_amount, gst = calculate_amounts(float(data['total_amount']))
        discount = float(data.get('discount', 0) or 0)
        late_fee = float(data.get('late_fee', 0) or 0)
        total = float(data['total_amount']) - discount + late_fee

        logger.debug("Creating invoice table")
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
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Header row
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e3f2fd')),
            ('ALIGN', (0, 1), (0, 1), 'CENTER'),  # S.No
            ('ALIGN', (1, 1), (1, 1), 'LEFT'),    # 'Particular' left
            ('FONTSIZE', (1, 1), (1, 1), 8),      # Make 'Particular' cell smaller
            ('FONTSIZE', (0, 1), (0, 1), 9),      # S.No
            ('FONTSIZE', (2, 1), (-1, 1), 9),     # Rest of data row
            ('ALIGN', (2, 1), (-1, 1), 'CENTER'), # Center rest of data row
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

        logger.debug("Adding notes and payment status")
        # Custom Notes
        if data.get('custom_notes'):
            elements.append(Paragraph(f"<b>Notes:</b> {data['custom_notes']}", styleN))

        # Show payment status if paid
        log_status = ""
        if os.path.exists(INVOICE_LOG_FILE):
            try:
                with open(INVOICE_LOG_FILE, 'r') as f:
                    logs = json.load(f)
                for entry in logs:
                    if entry['filename'] == data['pdf_filename']:
                        if entry.get('status') == 'Paid':
                            log_status = f"<b>Payment Status:</b> Paid on {entry.get('payment_date', '')} ({entry.get('payment_method', '')})"
                        elif entry.get('status') == 'Partial':
                            log_status = f"<b>Payment Status:</b> Partial payment on {entry.get('payment_date', '')} ({entry.get('payment_method', '')})"
                        break
            except Exception as e:
                logger.error(f"Error reading payment status: {str(e)}")
        if log_status:
            elements.append(Paragraph(log_status, styleN))

        # Footer
        elements.append(Paragraph(
            "This is a computer generated bill and does not require signature.<br/>"
            "For queries and complaints contact: 8585986890",
            styleN
        ))

        logger.debug("Building final PDF")
        doc.build(elements, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
        logger.info(f"PDF generation completed successfully: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}\n{traceback.format_exc()}")
        raise

# Add debug logging to file operations
@log_function_entry_exit
def load_customers():
    """Load customer database with debug logging"""
    try:
        logger.debug(f"Loading customers from: {CUSTOMERS_FILE}")
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, 'r') as f:
                customers = json.load(f)
                logger.debug(f"Loaded {len(customers)} customers")
                return customers
        else:
            logger.warning(f"Customers file not found: {CUSTOMERS_FILE}")
            return []
    except Exception as e:
        logger.error(f"Error loading customers: {str(e)}\n{traceback.format_exc()}")
        return []

@log_function_entry_exit
def save_customer(data):
    """Save customer data with debug logging"""
    try:
        logger.debug(f"Saving customer: {json.dumps(data, indent=2)}")
        customers = load_customers()
        exists = False
        for i, cust in enumerate(customers):
            if cust['customer_id'] == data['customer_id']:
                customers[i] = data
                exists = True
                logger.debug(f"Updated existing customer: {data['customer_id']}")
                break
        if not exists:
            customers.append(data)
            logger.debug(f"Added new customer: {data['customer_id']}")
        
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
            logger.info(f"Successfully saved customer data: {data['customer_id']}")
    except Exception as e:
        logger.error(f"Error saving customer: {str(e)}\n{traceback.format_exc()}")
        raise

@log_function_entry_exit
def check_logo():
    """Check if logo exists and is valid"""
    logger.debug("Checking logo file")
    if not os.path.exists(LOGO_PATH):
        logger.warning(f"Logo file not found at {LOGO_PATH}")
        messagebox.showwarning(
            "Logo Missing",
            f"Logo file not found at {LOGO_PATH}\n\n"
            "Please add your logo file in PNG format to continue using logo features."
        )
        return False
    
    try:
        # Try to open and verify the image
        with PIL.Image.open(LOGO_PATH) as img:
            if img.format != 'PNG':
                logger.warning(f"Invalid logo format: {img.format}")
                messagebox.showwarning(
                    "Invalid Logo Format",
                    f"Logo must be in PNG format. Current format: {img.format}\n\n"
                    "Please provide a PNG image file."
                )
                return False
            logger.debug("Logo file verified successfully")
            return True
    except Exception as e:
        logger.error(f"Error reading logo file: {str(e)}")
        messagebox.showerror(
            "Invalid Logo File",
            f"Error reading logo file: {str(e)}\n\n"
            "Please ensure the file is a valid PNG image."
        )
        return False

# Initialize global variables
app = None  # Main application window
fields = {}  # Dictionary to store form fields
customer_dropdown = None  # Global reference to customer dropdown
dark_mode = True  # Track theme state
notes_frame = None  # Global reference to notes frame
logs_frame = None  # Global reference to logs frame
logs_tree = None  # Global reference to logs tree
payment_status_var = None
payment_method_var = None
form_canvas = None  # Global reference to form canvas
customers_tree = None  # Global reference to customers tree
dashboard_frame = None  # Global reference to dashboard frame
tfn_logs_frame = None  # Global reference to TFN logs frame
tfn_logs_text = None  # Global reference to TFN logs text widget

# Logs view variables
filter_logs = None  # Global reference to filter_logs function
from_date_var = None  # Global reference to from_date variable
to_date_var = None  # Global reference to to_date variable
from_date = None  # Global reference to from_date DateEntry widget
to_date = None  # Global reference to to_date DateEntry widget
search_var = None  # Global reference to search variable
status_var = None  # Global reference to status filter variable

# Summary labels
total_invoices = None
total_amount = None
paid_amount = None
pending_amount = None

# Constants and configurations
LOGO_PATH = "assets/logo.png"  # Logo path in assets directory
ICO_PATH = "assets/logo.ico"  # Icon path in assets directory
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
DEBUG_LOG_FILE = os.path.join("logs", "tfn_billing_debug.log")  # Debug log file path
current_user = {"username": None, "role": None}

def initialize_app():
    """Initialize the main application window"""
    global app
    logging.info("Initializing main application window")
    
    try:
        app = ttk.Window(themename="darkly")
        app.title("Thunderstorm Bill Generator")
        app.geometry("1000x680")
        app.minsize(1000, 680)
        
        # Create required directories
        os.makedirs("output_invoices", exist_ok=True)
        logging.info("Created output_invoices directory")
        
        return True
    except Exception as e:
        logging.error(f"Error initializing application: {str(e)}")
        return False

def start_application():
    """Start the application with login window"""
    logging.info("Starting application")
    
    if not initialize_app():
        logging.error("Failed to initialize application")
        messagebox.showerror("Error", "Failed to initialize application")
        return
    
    try:
        # Set app icon
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = PIL.Image.open(LOGO_PATH)
                app.iconphoto(True, tk.PhotoImage(file=LOGO_PATH))
                logging.info("Successfully set app icon from PNG")
            except Exception as e:
                logging.error(f"Error setting PNG icon: {str(e)}")
        
        if os.path.exists(ICO_PATH):
            try:
                app.iconbitmap(ICO_PATH)
                logging.info("Successfully set app icon from ICO")
            except Exception as e:
                logging.error(f"Error setting ICO icon: {str(e)}")
        
        # Hide main window initially
        app.withdraw()
        
        # Show login window
        logging.info("Showing login window")
        login_window()
        
        # Start main event loop
        logging.info("Starting main event loop")
        app.mainloop()
    except Exception as e:
        logging.error(f"Error starting application: {str(e)}")
        logging.error(f"Details:\nCurrent directory: {os.getcwd()}\n"
                     f"Python path: {sys.path}\n"
                     f"Files in directory: {os.listdir()}")
        messagebox.showerror("Error", f"Error starting application: {str(e)}")

def initialize_tracker():
    """Initialize the tracker file with default values if it doesn't exist"""
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'w') as f:
            json.dump({"last_invoice_number": 2058}, f)

def load_invoice_number():
    """Load the last invoice number and return the next number"""
    initialize_tracker()
    try:
        with open(TRACKER_FILE) as f:
            data = json.load(f)
            return data.get("last_invoice_number", 2058) + 1
    except (json.JSONDecodeError, FileNotFoundError):
        return 2059

def save_invoice_number(number):
    """Save the current invoice number"""
    with open(TRACKER_FILE, 'w') as f:
        json.dump({"last_invoice_number": number}, f)

def calculate_amounts(total_amount):
    """Calculate base amount and taxes from total amount"""
    base_amount = round(total_amount / (1 + 2 * GST_RATE), 2)
    gst = round(base_amount * GST_RATE, 2)
    return base_amount, gst

class Watermark(Flowable):
    """Custom flowable for watermark"""
    def __init__(self, logo_path, width=100, height=100, opacity=0.1):
        Flowable.__init__(self)
        self.logo_path = logo_path
        self.width = width
        self.height = height
        self.opacity = opacity

    def draw(self):
        # Create watermark
        if os.path.exists(self.logo_path):
            self.canv.saveState()
            self.canv.setFillAlpha(self.opacity)
            
            # Get page dimensions
            page_width, page_height = A4
            
            # Calculate center position - adjust y position to be more centered in the content area
            # Move up by 20% of page height to account for header space
            x = (page_width - self.width) / 2
            y = (page_height - self.height) / 2 + (page_height * 0.1)  # Move up by 10% of page height
            
            self.canv.translate(x, y)
            self.canv.drawImage(self.logo_path, 0, 0, self.width, self.height)
            self.canv.restoreState()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create a default admin user if file doesn't exist
        users = [{"username": "admin", "password": "admin", "role": "admin"}]
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        return users

@log_function_entry_exit
def autofill_customer_data(event=None):
    """Autofill form fields when customer is selected"""
    logger.debug("Attempting to autofill customer data")
    selected = customer_dropdown.get()
    if not selected:
        logger.debug("No customer selected, skipping autofill")
        return
    customers = load_customers()
    for cust in customers:
        if f"{cust['name']} ({cust['customer_id']})" == selected:
            logger.info(f"Autofilling data for customer: {cust['customer_id']}")
            for field in ['Name', 'Customer ID', 'Tenant Name', 'Customer Address', 'Customer GSTIN', 'Email']:
                if field.lower().replace(' ', '_') in cust:
                    fields[field].delete(0, tk.END)
                    fields[field].insert(0, cust[field.lower().replace(' ', '_')])
            logger.debug("Customer data autofill completed")
            break

@log_function_entry_exit
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    logger.info(f"Toggling theme to: {'dark' if dark_mode else 'light'}")
    
    style = ttk.Style()
    if dark_mode:
        logger.debug("Applying dark theme")
        # Dark theme colors
        style.configure(".", 
                      background='#1e1e1e',
                      foreground='white',
                      fieldbackground='#2d2d2d',
                      troughcolor='#2d2d2d',
                      arrowcolor='white')
    else:
        logger.debug("Applying light theme")
        # Light theme colors
        style.configure(".", 
                      background='#f0f0f0',
                      foreground='black',
                      fieldbackground='white',
                      troughcolor='#e0e0e0',
                      arrowcolor='black')
    
    # Update all widgets to reflect new theme
    app.update_idletasks()
    logger.debug("Theme update completed")

def update_canvas_color(e=None):
    try:
        bg_color = app.style.lookup('TFrame', 'background')
        form_canvas.configure(bg=bg_color)
    except:
        pass

def create_logs_view():
    """Create the logs view with filtering and export capabilities"""
    global logs_tree, total_invoices, total_amount, paid_amount, pending_amount
    global filter_logs, from_date_var, to_date_var, from_date, to_date, search_var, status_var
    
    # Clear any existing widgets
    for widget in logs_frame.winfo_children():
        widget.destroy()
        
    # Create main container with padding
    main_container = ttk.Frame(logs_frame, style="Custom.TFrame", padding=15)
    main_container.pack(fill="both", expand=True)

    # Create logs container
    logs_container = ttk.Frame(main_container, style="Custom.TFrame")
    logs_container.pack(fill="both", expand=True)

    # Create summary frame
    summary_frame = ttk.LabelFrame(main_container, text="Summary", padding=10, style="Custom.TLabelframe")
    summary_frame.pack(fill="x", pady=(0, 10))

    # Summary labels
    total_invoices = ttk.Label(summary_frame, text="Total Invoices: 0")
    total_invoices.pack(side="left", padx=20)
    
    total_amount = ttk.Label(summary_frame, text="Total Amount: ₹0")
    total_amount.pack(side="left", padx=20)
    
    paid_amount = ttk.Label(summary_frame, text="Paid Amount: ₹0")
    paid_amount.pack(side="left", padx=20)
    
    pending_amount = ttk.Label(summary_frame, text="Pending Amount: ₹0")
    pending_amount.pack(side="left", padx=20)

    # Add logs table with fixed column widths
    columns = ("Date", "Invoice No", "Customer", "Amount", "Status", "Payment Method")
    logs_tree = ttk.Treeview(logs_container, columns=columns, show="headings", style="Treeview")
    
    # Configure columns with specific widths and alignments
    logs_tree.heading("Date", text="Date", anchor="w")
    logs_tree.heading("Invoice No", text="Invoice No", anchor="w")
    logs_tree.heading("Customer", text="Customer", anchor="w")
    logs_tree.heading("Amount", text="Amount", anchor="e")
    logs_tree.heading("Status", text="Status", anchor="center")
    logs_tree.heading("Payment Method", text="Payment Method", anchor="center")
    
    logs_tree.column("Date", width=150, anchor="w")
    logs_tree.column("Invoice No", width=120, anchor="w")
    logs_tree.column("Customer", width=200, anchor="w")
    logs_tree.column("Amount", width=100, anchor="e")
    logs_tree.column("Status", width=100, anchor="center")
    logs_tree.column("Payment Method", width=120, anchor="center")

    # Add scrollbar
    scrollbar = ttk.Scrollbar(logs_container, orient="vertical", command=logs_tree.yview)
    logs_tree.configure(yscrollcommand=scrollbar.set)

    # Pack elements
    logs_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def update_summary():
        """Update summary statistics"""
        if not logs_tree.get_children():
            return
            
        total_count = len(logs_tree.get_children())
        total = 0
        paid = 0
        pending = 0
        
        for item in logs_tree.get_children():
            values = logs_tree.item(item)['values']
            amount = float(values[3].replace('₹', ''))
            total += amount
            if values[4] == "Paid":
                paid += amount
            else:
                pending += amount
        
        total_invoices.config(text=f"Total Invoices: {total_count}")
        total_amount.config(text=f"Total Amount: ₹{total:,.2f}")
        paid_amount.config(text=f"Paid Amount: ₹{paid:,.2f}")
        pending_amount.config(text=f"Pending Amount: ₹{pending:,.2f}")

    def filter_logs_impl(*args):
        """Filter logs based on search criteria"""
        search_text = search_var.get().lower()
        status_filter = status_var.get()
        from_date_str = from_date_var.get()
        to_date_str = to_date_var.get()
        
        # Clear tree
        for item in logs_tree.get_children():
            logs_tree.delete(item)
            
        if os.path.exists(INVOICE_LOG_FILE):
            try:
                with open(INVOICE_LOG_FILE, 'r') as f:
                    logs = json.load(f)
                    
                # Convert dates if provided
                from_date_obj = None
                to_date_obj = None
                if from_date_str:
                    from_date_obj = datetime.strptime(from_date_str, "%d-%m-%Y")
                if to_date_str:
                    to_date_obj = datetime.strptime(to_date_str, "%d-%m-%Y") + timedelta(days=1)
                
                for log in logs:
                    # Check date range
                    log_date = datetime.strptime(log.get("datetime", ""), "%d-%m-%Y %H:%M:%S")
                    if from_date_obj and log_date < from_date_obj:
                        continue
                    if to_date_obj and log_date > to_date_obj:
                        continue
                    
                    # Check status filter
                    if status_filter != "All" and log.get("status") != status_filter:
                        continue
                    
                    # Check search text
                    values = [
                        log.get("datetime", ""),
                        log.get("invoice_num", ""),
                        log.get("customer_name", ""),
                        str(log.get("amount", "")),
                        log.get("status", ""),
                        log.get("payment_method", "")
                    ]
                    
                    if search_text and not any(search_text in str(v).lower() for v in values):
                        continue
                        
                    logs_tree.insert("", "end", values=(
                        log.get("datetime", ""),
                        log.get("invoice_num", ""),
                        log.get("customer_name", ""),
                        f"₹{log.get('amount', '0')}",
                        log.get("status", "Unpaid"),
                        log.get("payment_method", "")
                    ))
                    
                update_summary()
                    
            except Exception as e:
                print(f"Error loading logs: {str(e)}")

    # Assign the implementation to the global filter_logs variable
    filter_logs = filter_logs_impl

    # Create top controls frame with better organization
    controls_frame = ttk.Frame(main_container, style="Custom.TFrame")
    controls_frame.pack(fill="x", pady=(0, 10))

    # Create a container for search and filter elements
    search_container = ttk.Frame(controls_frame, style="Custom.TFrame")
    search_container.pack(side="left", fill="x", expand=True)

    # Search frame with improved layout
    search_frame = ttk.LabelFrame(search_container, text="Search & Filter", padding=10, style="Custom.TLabelframe")
    search_frame.pack(fill="x", expand=True, padx=(0, 10))

    # Create top row for search and status
    top_row = ttk.Frame(search_frame, style="Custom.TFrame")
    top_row.pack(fill="x", pady=(0, 5))

    # Search entry with label
    search_label = ttk.Label(top_row, text="Search:", style="Custom.TLabel")
    search_label.pack(side="left", padx=(0, 5))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(top_row, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=(0, 15))

    # Status filter
    status_label = ttk.Label(top_row, text="Status:", style="Custom.TLabel")
    status_label.pack(side="left", padx=(0, 5))
    status_var = tk.StringVar(value="All")
    status_combo = ttk.Combobox(top_row, textvariable=status_var, values=["All", "Paid", "Unpaid"], 
                               state="readonly", width=15)
    status_combo.pack(side="left")

    # Create bottom row for date range
    date_frame = ttk.Frame(search_frame, style="Custom.TFrame")
    date_frame.pack(fill="x", pady=(5, 0))

    # Date range with better spacing
    date_label = ttk.Label(date_frame, text="Date Range:", style="Custom.TLabel")
    date_label.pack(side="left", padx=(0, 5))
    
    from_date_var = tk.StringVar()
    to_date_var = tk.StringVar()
    
    ttk.Label(date_frame, text="From", style="Custom.TLabel").pack(side="left", padx=(0, 5))
    from_date = ttk.DateEntry(
        date_frame,
            dateformat="%d-%m-%Y",
            firstweekday=0,
        width=15,
        bootstyle="primary"
    )
    from_date.pack(side="left", padx=(0, 10))
    
    ttk.Label(date_frame, text="To", style="Custom.TLabel").pack(side="left", padx=(0, 5))
    to_date = ttk.DateEntry(
        date_frame,
        dateformat="%d-%m-%Y",
        firstweekday=0,
        width=15,
        bootstyle="primary"
    )
    to_date.pack(side="left")

    def on_date_change(*args):
        """Update the date variables when dates are changed"""
        try:
            from_date_var.set(from_date.entry.get())
            to_date_var.set(to_date.entry.get())
            filter_logs()
        except:
            pass

    # Actions frame with better positioning
    actions_frame = ttk.Frame(controls_frame, style="Custom.TFrame")
    actions_frame.pack(side="right", padx=(0, 10))

    # Add buttons to actions frame with improved styling
    export_btn = ttk.Button(
        actions_frame,
        text="Export",
        command=export_logs,
        style="Custom.TButton",
        width=12
    )
    export_btn.pack(side="left", padx=5)

    update_btn = ttk.Button(
        actions_frame,
        text="Update Status",
        command=update_payment_status,
        style="Custom.TButton",
        width=12
    )
    update_btn.pack(side="left", padx=5)

    # Auto-refresh toggle with better positioning
    refresh_frame = ttk.Frame(controls_frame, style="Custom.TFrame")
    refresh_frame.pack(side="right")
    
    auto_refresh_var = tk.BooleanVar(value=True)
    auto_refresh_cb = ttk.Checkbutton(
        refresh_frame,
        text="Auto Refresh",
        variable=auto_refresh_var,
        style="Custom.TCheckbutton"
    )
    auto_refresh_cb.pack(side="left", padx=5)
    
    refresh_btn = ttk.Button(
        refresh_frame,
        text="🔄 Refresh",
        command=lambda: filter_logs(),
        style="Custom.TButton",
        width=10
    )
    refresh_btn.pack(side="left", padx=5)

    # Bind date changes to filter
    from_date.entry.bind('<FocusOut>', on_date_change)
    to_date.entry.bind('<FocusOut>', on_date_change)
    
    # Set initial dates (current month)
    today = datetime.now()
    first_day = today.replace(day=1)
    from_date.entry.delete(0, tk.END)
    from_date.entry.insert(0, first_day.strftime("%d-%m-%Y"))
    to_date.entry.delete(0, tk.END)
    to_date.entry.insert(0, today.strftime("%d-%m-%Y"))

    # Bind search and filter events
    search_var.trace('w', filter_logs)
    status_var.trace('w', filter_logs)
    from_date_var.trace('w', filter_logs)
    to_date_var.trace('w', filter_logs)

    # Initial load
    filter_logs()

    def auto_refresh():
        """Auto refresh the logs view every 5 seconds if enabled"""
        if auto_refresh_var.get() and logs_tree and logs_tree.winfo_exists():
            filter_logs()
        if logs_tree and logs_tree.winfo_exists():  # Only schedule next refresh if tree still exists
            logs_tree.after(5000, auto_refresh)  # Schedule next refresh in 5 seconds

    # Start auto-refresh
    auto_refresh()

@log_function_entry_exit
def refresh_logs():
    """Refresh the logs view with latest data"""
    logger.debug("Refreshing logs view")
    global logs_tree
    
    if logs_tree is None or not logs_tree.winfo_exists():
        logger.warning("Logs tree widget not available")
        return
        
    # Clear existing items
    for item in logs_tree.get_children():
        logs_tree.delete(item)
    logger.debug("Cleared existing log entries")

    # Load and display logs
    if os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                logs = json.load(f)
                logger.debug(f"Loaded {len(logs)} log entries")
                
                # Sort logs by datetime in descending order
                for log in logs:
                    try:
                        # Try to parse the datetime in either format
                        try:
                            datetime_obj = datetime.strptime(log.get("datetime", ""), "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                datetime_obj = datetime.strptime(log.get("datetime", ""), "%d-%m-%Y %H:%M:%S")
                            except ValueError:
                                logger.warning(f"Invalid datetime format in log: {log.get('datetime', '')}")
                                continue
                        
                        # Format datetime consistently
                        formatted_date = datetime_obj.strftime("%d-%m-%Y %H:%M:%S")
                        log["datetime"] = formatted_date
                    except Exception as e:
                        logger.error(f"Error processing log entry datetime: {str(e)}")
                        continue

                # Sort logs by datetime
                logs.sort(key=lambda x: datetime.strptime(x.get("datetime", "01-01-1970 00:00:00"), "%d-%m-%Y %H:%M:%S"), reverse=True)
                logger.debug("Sorted logs by datetime")
                
                for log in logs:
                    logs_tree.insert("", "end", values=(
                        log.get("datetime", ""),
                        log.get("invoice_num", ""),
                        log.get("customer_name", ""),
                        f"₹{log.get('amount', '0')}",
                        log.get("status", "Unpaid"),
                        log.get("payment_method", "")
                    ))
                logger.info("Logs view refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing logs: {str(e)}\n{traceback.format_exc()}")

@log_function_entry_exit
def refresh_tfn_logs():
    """Refresh the TFN logs display"""
    logger.debug("Refreshing TFN logs display")
    try:
        # Save current position
        current_pos = tfn_logs_text.yview()[1]
        
        # Clear current content
        tfn_logs_text.delete(1.0, tk.END)
        logger.debug("Cleared existing TFN logs display")
        
        # Read and display log file
        if os.path.exists(DEBUG_LOG_FILE):
            with open(DEBUG_LOG_FILE, 'r') as f:
                logs = f.read()
                tfn_logs_text.insert(tk.END, logs)
                logger.debug("Loaded and displayed TFN logs")
                
            # Auto-scroll to bottom if we were at bottom before
            if current_pos > 0.99:
                tfn_logs_text.see(tk.END)
                logger.debug("Auto-scrolled to bottom of logs")
                
        logger.info("TFN logs display refreshed successfully")
    except Exception as e:
        logger.error(f"Error refreshing TFN logs: {str(e)}\n{traceback.format_exc()}")

@log_function_entry_exit
def clear_tfn_logs():
    """Clear the TFN log file and display"""
    logger.info("Attempting to clear TFN logs")
    if messagebox.askyesno("Clear Logs", "Are you sure you want to clear all logs?"):
        try:
            # Clear log file
            with open(DEBUG_LOG_FILE, 'w') as f:
                f.write("")
            # Clear display
            tfn_logs_text.delete(1.0, tk.END)
            logger.info("TFN logs cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing TFN logs: {str(e)}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Failed to clear logs: {str(e)}")

@log_function_entry_exit
def filter_logs_impl(*args):
    """Filter logs based on search criteria"""
    logger.debug("Filtering logs based on search criteria")
    search_text = search_var.get().lower()
    status_filter = status_var.get()
    from_date_str = from_date_var.get()
    to_date_str = to_date_var.get()
    
    logger.debug(f"Filter criteria - Search: '{search_text}', Status: {status_filter}, "
                f"Date range: {from_date_str} to {to_date_str}")
    
    # Clear tree
    for item in logs_tree.get_children():
        logs_tree.delete(item)
        
    if os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                logs = json.load(f)
                logger.debug(f"Loaded {len(logs)} logs for filtering")
                
            # Convert dates if provided
            from_date_obj = None
            to_date_obj = None
            if from_date_str:
                from_date_obj = datetime.strptime(from_date_str, "%d-%m-%Y")
            if to_date_str:
                to_date_obj = datetime.strptime(to_date_str, "%d-%m-%Y") + timedelta(days=1)
            
            filtered_count = 0
            for log in logs:
                # Check date range
                log_date = datetime.strptime(log.get("datetime", ""), "%d-%m-%Y %H:%M:%S")
                if from_date_obj and log_date < from_date_obj:
                    continue
                if to_date_obj and log_date > to_date_obj:
                    continue
                
                # Check status filter
                if status_filter != "All" and log.get("status") != status_filter:
                    continue
                
                # Check search text
                values = [
                    log.get("datetime", ""),
                    log.get("invoice_num", ""),
                    log.get("customer_name", ""),
                    str(log.get("amount", "")),
                    log.get("status", ""),
                    log.get("payment_method", "")
                ]
                
                if search_text and not any(search_text in str(v).lower() for v in values):
                    continue
                    
                logs_tree.insert("", "end", values=(
                    log.get("datetime", ""),
                    log.get("invoice_num", ""),
                    log.get("customer_name", ""),
                    f"₹{log.get('amount', '0')}",
                    log.get("status", "Unpaid"),
                    log.get("payment_method", "")
                ))
                filtered_count += 1
                
            logger.info(f"Filtered logs: showing {filtered_count} of {len(logs)} entries")
            update_summary()
                
        except Exception as e:
            logger.error(f"Error filtering logs: {str(e)}\n{traceback.format_exc()}")

@log_function_entry_exit
def update_summary():
    """Update summary statistics in logs view"""
    logger.debug("Updating logs summary statistics")
    if not logs_tree.get_children():
        logger.debug("No logs to summarize")
        return
            
    total_count = len(logs_tree.get_children())
    total = 0
    paid = 0
    pending = 0
    
    try:
        for item in logs_tree.get_children():
            values = logs_tree.item(item)['values']
            amount = float(values[3].replace('₹', ''))
            total += amount
            if values[4] == "Paid":
                paid += amount
            else:
                pending += amount
        
        total_invoices.config(text=f"Total Invoices: {total_count}")
        total_amount.config(text=f"Total Amount: ₹{total:,.2f}")
        paid_amount.config(text=f"Paid Amount: ₹{paid:,.2f}")
        pending_amount.config(text=f"Pending Amount: ₹{pending:,.2f}")
        
        logger.info(f"Summary updated - Total: {total_count} invoices, "
                   f"Amount: ₹{total:,.2f}, Paid: ₹{paid:,.2f}, Pending: ₹{pending:,.2f}")
    except Exception as e:
        logger.error(f"Error updating summary: {str(e)}\n{traceback.format_exc()}")

@log_function_entry_exit
def on_date_change(*args):
    """Update the date variables when dates are changed"""
    logger.debug("Date filter changed")
    try:
        from_date_var.set(from_date.entry.get())
        to_date_var.set(to_date.entry.get())
        logger.debug(f"New date range: {from_date_var.get()} to {to_date_var.get()}")
        filter_logs()
    except Exception as e:
        logger.error(f"Error handling date change: {str(e)}")

@log_function_entry_exit
def validate_and_submit():
    """Validate form fields and generate invoice"""
    logger.info("Starting form validation and invoice generation")
    
    # Validate required fields
    required_fields = ["Name", "Customer ID", "Tenant Name", "Customer Address", "Plan", "Total Amount"]
    for field in required_fields:
        if not fields[field].get():
            logger.warning(f"Validation failed: {field} is required")
            messagebox.showerror("Error", f"{field} is required!")
            return

    # Validate dates
    try:
        from_date = datetime.strptime(fields["Billing Period From"].get(), "%d-%m-%Y")
        to_date = datetime.strptime(fields["Billing Period To"].get(), "%d-%m-%Y")
        if to_date < from_date:
            logger.warning("Validation failed: Invalid date range")
            messagebox.showerror("Error", "Billing Period To cannot be earlier than Billing Period From!")
            return
    except ValueError:
        logger.error("Date validation failed: Invalid date format")
        messagebox.showerror("Error", "Invalid date format! Use DD-MM-YYYY")
        return

    # Validate amount
    try:
        amount = float(fields["Total Amount"].get())
        if amount <= 0:
            logger.warning("Validation failed: Invalid amount")
            messagebox.showerror("Error", "Total Amount must be greater than 0!")
            return
    except ValueError:
        logger.error("Amount validation failed: Invalid amount format")
        messagebox.showerror("Error", "Invalid Total Amount!")
        return
            
    # Validate payment method if status is Paid
    if payment_status_var.get() == "Paid" and not payment_method_var.get():
        logger.warning("Validation failed: Payment method required for paid status")
        messagebox.showerror("Error", "Please select a payment method!")
        return

    logger.info("Form validation successful, preparing invoice data")
    
    # Prepare invoice data
    invoice_num = load_invoice_number()
    logger.debug(f"Generated invoice number: {invoice_num}")
    
    # Format filename
    current_date = datetime.now()
    month_name = current_date.strftime("%b")
    year = current_date.strftime("%Y")
    customer_name = fields["Name"].get().replace(" ", "_")
    pdf_filename = f"{customer_name}_{month_name}_{year}.pdf"
    logger.debug(f"Generated PDF filename: {pdf_filename}")
    
    invoice_data = {
        "name": fields["Name"].get(),
        "customer_id": fields["Customer ID"].get(),
        "tenant_name": fields["Tenant Name"].get(),
        "customer_address": fields["Customer Address"].get(),
        "customer_gstin": fields["Customer GSTIN"].get(),
        "billing_from": fields["Billing Period From"].get(),
        "billing_to": fields["Billing Period To"].get(),
        "plan": fields["Plan"].get(),
        "months": fields["Months"].get(),
        "total_amount": fields["Total Amount"].get(),
        "discount": fields["Discount"].get() or "0",
        "late_fee": fields["Late Fee"].get() or "0",
        "invoice_num": invoice_num,
        "pdf_filename": pdf_filename,
        "custom_notes": notes_frame.get("1.0", tk.END).strip(),
        "payment_status": payment_status_var.get(),
        "payment_method": payment_method_var.get() if payment_status_var.get() == "Paid" else ""
    }
    
    logger.debug(f"Prepared invoice data: {json.dumps(invoice_data, indent=2)}")

    try:
        # Generate PDF
        logger.info("Starting PDF generation")
        generate_pdf(invoice_data)
        
        # Save invoice number
        logger.debug(f"Saving invoice number: {invoice_num}")
        save_invoice_number(invoice_num)
        
        # Log invoice
        logger.info(f"Logging invoice: {pdf_filename}")
        log_invoice(invoice_data, invoice_data["pdf_filename"])
        
        # Refresh logs view
        if logs_tree and logs_tree.winfo_exists():
            logger.debug("Refreshing logs view")
            filter_logs()
        
        # Show success message
        logger.info("Invoice generation completed successfully")
        messagebox.showinfo(
            "Success",
            f"Invoice generated successfully!\nSaved as: {invoice_data['pdf_filename']}"
        )
        
        # Ask about email
        if messagebox.askyesno("Email Invoice", "Would you like to email this invoice?"):
            email = fields["Email"].get()
            if email:
                try:
                    logger.info(f"Attempting to send email to: {email}")
                    send_email(email, invoice_data["pdf_filename"])
                    logger.info("Email sent successfully")
                    messagebox.showinfo("Success", "Invoice sent successfully!")
                except Exception as e:
                    logger.error(f"Email sending failed: {str(e)}")
                    messagebox.showerror("Email Error", str(e))
            else:
                logger.warning("Email sending skipped: No email address provided")
                messagebox.showerror("Error", "No email address provided!")
                
    except Exception as e:
        logger.error(f"Invoice generation failed: {str(e)}\n{traceback.format_exc()}")
        messagebox.showerror("Error", f"Failed to generate invoice: {str(e)}")

@log_function_entry_exit
def send_email(to_email, pdf_file):
    """Send invoice via email"""
    logger.info(f"Preparing to send email to: {to_email}")
    
    # Email configuration
    email_config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "your-email@gmail.com",  # Replace with your email
        "password": "your-app-password"  # Replace with your app password
    }
    
    logger.debug("Creating email message")
    # Create message
    msg = EmailMessage()
    msg['Subject'] = 'Your Invoice from Thunderstorm Fibernet'
    msg['From'] = email_config["sender_email"]
    msg['To'] = to_email
    msg.set_content('Please find your invoice attached.')
    
    # Attach PDF
    pdf_path = os.path.join("output_invoices", pdf_file)
    logger.debug(f"Attaching PDF: {pdf_path}")
    with open(pdf_path, 'rb') as f:
        file_data = f.read()
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=pdf_file)
    
    # Send email
    logger.info("Connecting to SMTP server")
    with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
        server.starttls()
        logger.debug("Logging into SMTP server")
        server.login(email_config["sender_email"], email_config["password"])
        logger.debug("Sending email")
        server.send_message(msg)
    logger.info("Email sent successfully")

def create_dashboard_view():
    """Create the dashboard view with analytics and visualizations"""
    global HAS_MPL, dashboard_frame

    # Clear any existing widgets
    for widget in dashboard_frame.winfo_children():
        widget.destroy()

    def refresh_dashboard():
        """Refresh the dashboard data"""
        create_dashboard_view()

    # Create main container with padding
    dashboard_container = ttk.Frame(dashboard_frame, style="Custom.TFrame", padding=15)
    dashboard_container.pack(fill="both", expand=True)

    # Create scrollable frame
    scroll_canvas = tk.Canvas(dashboard_container, bg=app.style.lookup('TFrame', 'background'), highlightthickness=0)
    scrollbar = ttk.Scrollbar(dashboard_container, orient="vertical", command=scroll_canvas.yview)
    scrollable_frame = ttk.Frame(scroll_canvas, style="Custom.TFrame")

    # Pack scrollbar and canvas
    scrollbar.pack(side="right", fill="y")
    scroll_canvas.pack(side="left", fill="both", expand=True)

    # Create the window in the canvas with proper width
    canvas_frame = ttk.Frame(scroll_canvas, style="Custom.TFrame")
    canvas_window = scroll_canvas.create_window((0, 0), window=canvas_frame, anchor="nw", tags="canvas_frame")

    # Configure scroll region and canvas width
    def configure_scroll_region(event=None):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    def configure_canvas_width(event=None):
        width = event.width if event else scroll_canvas.winfo_width()
        scroll_canvas.itemconfig("canvas_frame", width=width)

    # Bind events
    canvas_frame.bind("<Configure>", configure_scroll_region)
    scroll_canvas.bind("<Configure>", configure_canvas_width)

    # Configure canvas scrolling
    scroll_canvas.configure(yscrollcommand=scrollbar.set)

    # Enable mouse wheel scrolling
    def _on_mousewheel(event):
        if scroll_canvas.winfo_exists():
            scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # Bind mouse wheel to the canvas and all its children
    def bind_mousewheel_to_widgets(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            bind_mousewheel_to_widgets(child)

    bind_mousewheel_to_widgets(canvas_frame)
    scroll_canvas.bind("<MouseWheel>", _on_mousewheel)

    # Content starts here - all widgets should be children of canvas_frame
    content_frame = ttk.Frame(canvas_frame, style="Custom.TFrame")
    content_frame.pack(fill="both", expand=True, padx=10)

    # Quick Stats Section
    stats_frame = ttk.LabelFrame(content_frame, text="Quick Stats", padding=10)
    stats_frame.pack(fill="x", pady=(0, 15))

    # Create grid for stats
    stats_grid = ttk.Frame(stats_frame)
    stats_grid.pack(fill="x", expand=True)

    # Configure grid columns to be evenly spaced
    for i in range(4):
        stats_grid.columnconfigure(i, weight=1)

    def create_stat_widget(parent, title, value, row, col):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
        
        ttk.Label(
            frame,
            text=title,
            style="Custom.TLabel",
            font=("Segoe UI", 10)
        ).pack()
        
        ttk.Label(
            frame,
            text=value,
            style="Custom.TLabel",
            font=("Segoe UI", 12, "bold")
        ).pack()

    # Load and process data for stats
    total_revenue = 0
    total_invoices = 0
    total_customers = set()
    unpaid_amount = 0
    this_month = datetime.now().strftime("%m-%Y")
    this_month_revenue = 0
    active_plans_set = set()  # Track unique active plans

    if os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                logs = json.load(f)
                for log in logs:
                    amount = float(log.get('amount', 0))
                    total_revenue += amount
                    total_invoices += 1
                    total_customers.add(log.get('customer_name', ''))
                    active_plans_set.add(log.get('plan', ''))  # Track plans in use
                    
                    if log.get('status') != 'Paid':
                        unpaid_amount += amount
                        
                    # Check if invoice is from current month
                    log_date = datetime.strptime(log.get('datetime', ''), "%d-%m-%Y %H:%M:%S")
                    if log_date.strftime("%m-%Y") == this_month:
                        this_month_revenue += amount
        except:
            pass

    # Create stat widgets
    create_stat_widget(stats_grid, "Total Revenue", f"₹{total_revenue:,.2f}", 0, 0)
    create_stat_widget(stats_grid, "Total Invoices", str(total_invoices), 0, 1)
    create_stat_widget(stats_grid, "Total Customers", str(len(total_customers)), 0, 2)
    create_stat_widget(stats_grid, "Pending Amount", f"₹{unpaid_amount:,.2f}", 0, 3)
    create_stat_widget(stats_grid, "This Month Revenue", f"₹{this_month_revenue:,.2f}", 1, 0)
    create_stat_widget(stats_grid, "Collection Rate", f"{(1 - unpaid_amount/total_revenue)*100:.1f}%" if total_revenue > 0 else "0%", 1, 1)
    create_stat_widget(stats_grid, "Avg. Invoice Value", f"₹{(total_revenue/total_invoices):,.2f}" if total_invoices > 0 else "₹0", 1, 2)
    create_stat_widget(stats_grid, "Active Plans", str(len(active_plans_set)), 1, 3)

    if HAS_MPL:
        # Charts Section
        charts_frame = ttk.LabelFrame(content_frame, text="Analytics", padding=10)
        charts_frame.pack(fill="x", pady=15)

        # Charts grid
        charts_grid = ttk.Frame(charts_frame)
        charts_grid.pack(fill="x", expand=True)
        charts_grid.columnconfigure(0, weight=1)
        charts_grid.columnconfigure(1, weight=1)

        def create_revenue_trend():
            """Create monthly revenue trend chart"""
            monthly_revenue = {}
            if os.path.exists(INVOICE_LOG_FILE):
                try:
                    with open(INVOICE_LOG_FILE, 'r') as f:
                        logs = json.load(f)
                        for log in logs:
                            date = datetime.strptime(log.get('datetime', ''), "%d-%m-%Y %H:%M:%S")
                            month_key = date.strftime("%b %Y")
                            amount = float(log.get('amount', 0))
                            monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + amount
                except:
                    pass

            # Sort by date
            sorted_months = sorted(monthly_revenue.keys(), 
                                 key=lambda x: datetime.strptime(x, "%b %Y"))
            
            # Create figure
            fig, ax = plt.subplots(figsize=(6, 4))
            if sorted_months:  # Only plot if we have data
                ax.plot(sorted_months, [monthly_revenue[m] for m in sorted_months], 
                       marker='o', linewidth=2, color='#1976d2')
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.xticks(rotation=45)
            else:
                ax.text(0.5, 0.5, 'No data available', 
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes)
            
            ax.set_title("Monthly Revenue Trend", pad=15)
            plt.tight_layout()
            return fig

        def create_payment_status_pie():
            """Create payment status distribution pie chart"""
            status_counts = {'Paid': 0, 'Unpaid': 0}
            if os.path.exists(INVOICE_LOG_FILE):
                try:
                    with open(INVOICE_LOG_FILE, 'r') as f:
                        logs = json.load(f)
                        for log in logs:
                            status = log.get('status', 'Unpaid')
                            status_counts[status] = status_counts.get(status, 0) + 1
                except:
                    pass

            fig, ax = plt.subplots(figsize=(6, 4))
            if sum(status_counts.values()) > 0:  # Only plot if we have data
                colors = ['#4caf50', '#f44336']
                ax.pie(status_counts.values(), labels=status_counts.keys(), 
                      autopct='%1.1f%%', colors=colors)
            else:
                ax.text(0.5, 0.5, 'No data available', 
                       horizontalalignment='center',
                       verticalalignment='center')
            
            ax.set_title("Payment Status Distribution", pad=15)
            plt.tight_layout()
            return fig

        def create_plan_distribution():
            """Create plan distribution bar chart"""
            plan_counts = {plan: 0 for plan in active_plans_set or PLANS}  # Use active plans or default plans
            if os.path.exists(INVOICE_LOG_FILE):
                try:
                    with open(INVOICE_LOG_FILE, 'r') as f:
                        logs = json.load(f)
                        for log in logs:
                            plan = log.get('plan', '')
                            if plan:  # Only count if plan exists
                                plan_counts[plan] = plan_counts.get(plan, 0) + 1
                except:
                    pass

            fig, ax = plt.subplots(figsize=(6, 4))
            if sum(plan_counts.values()) > 0:  # Only plot if we have data
                ax.bar(plan_counts.keys(), plan_counts.values(), color='#2196f3')
                plt.xticks(rotation=45)
                ax.grid(True, linestyle='--', alpha=0.7)
            else:
                ax.text(0.5, 0.5, 'No data available', 
                       horizontalalignment='center',
                       verticalalignment='center')
            
            ax.set_title("Plan Distribution", pad=15)
            plt.tight_layout()
            return fig

        # Create and pack charts
        charts = [
            ("Revenue Trend", create_revenue_trend),
            ("Payment Status", create_payment_status_pie),
            ("Plan Distribution", create_plan_distribution)
        ]

        for i, (title, create_func) in enumerate(charts):
            chart_frame = ttk.Frame(charts_grid)
            chart_frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            
            try:
                fig = create_func()
                figure_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                figure_canvas.draw()
                figure_canvas.get_tk_widget().pack(fill="both", expand=True)
            except Exception as e:
                print(f"Error creating {title} chart: {str(e)}")
                ttk.Label(
                    chart_frame,
                    text=f"Error creating chart: {str(e)}",
                    style="Custom.TLabel"
                ).pack(pady=20)

    else:
        # Show message if matplotlib is not available
        ttk.Label(
            content_frame,
            text="Install matplotlib for visualizations",
            style="Custom.TLabel",
            font=("Segoe UI", 12)
        ).pack(pady=20)

    # Recent Activity Section
    activity_frame = ttk.LabelFrame(content_frame, text="Recent Activity", padding=10)
    activity_frame.pack(fill="x", pady=15)

    # Create Treeview for recent invoices
    columns = ("Date", "Invoice No", "Customer", "Amount", "Status")
    activity_tree = ttk.Treeview(activity_frame, columns=columns, show="headings", height=5)
    
    # Configure columns
    activity_tree.heading("Date", text="Date", anchor="w")
    activity_tree.heading("Invoice No", text="Invoice No", anchor="w")
    activity_tree.heading("Customer", text="Customer", anchor="w")
    activity_tree.heading("Amount", text="Amount", anchor="e")
    activity_tree.heading("Status", text="Status", anchor="center")
    
    activity_tree.column("Date", width=150, anchor="w")
    activity_tree.column("Invoice No", width=120, anchor="w")
    activity_tree.column("Customer", width=200, anchor="w")
    activity_tree.column("Amount", width=100, anchor="e")
    activity_tree.column("Status", width=100, anchor="center")

    # Add scrollbar
    activity_scrollbar = ttk.Scrollbar(activity_frame, orient="vertical", command=activity_tree.yview)
    activity_tree.configure(yscrollcommand=activity_scrollbar.set)

    # Pack elements
    activity_tree.pack(side="left", fill="x", expand=True)
    activity_scrollbar.pack(side="right", fill="y")

    # Load recent activity
    if os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                logs = json.load(f)
                # Sort by date descending
                logs.sort(key=lambda x: datetime.strptime(x.get('datetime', ''), "%d-%m-%Y %H:%M:%S"), 
                         reverse=True)
                # Show only last 5 entries
                for log in logs[:5]:
                    activity_tree.insert("", "end", values=(
                        log.get("datetime", ""),
                        log.get("invoice_num", ""),
                        log.get("customer_name", ""),
                        f"₹{log.get('amount', '0')}",
                        log.get("status", "Unpaid")
                    ))
        except:
            pass

    # Refresh button
    refresh_btn = ttk.Button(
        content_frame,
        text="🔄 Refresh Dashboard",
        command=refresh_dashboard,
        style="Custom.TButton",
        width=20
    )
    refresh_btn.pack(pady=15)

    # Bind mousewheel to all new widgets
    bind_mousewheel_to_widgets(content_frame)

def create_tfn_logs_view():
    """Create the TFN logs view that displays debug logs"""
    global tfn_logs_frame, tfn_logs_text
    
    # Clear any existing widgets
    for widget in tfn_logs_frame.winfo_children():
        widget.destroy()

    # Create main container with padding
    main_container = ttk.Frame(tfn_logs_frame, style="Custom.TFrame", padding=15)
    main_container.pack(fill="both", expand=True)

    # Create controls frame
    controls_frame = ttk.Frame(main_container, style="Custom.TFrame")
    controls_frame.pack(fill="x", pady=(0, 10))

    # Add refresh button
    refresh_btn = ttk.Button(
        controls_frame,
        text="🔄 Refresh Logs",
        command=lambda: refresh_tfn_logs(),
        style="Custom.TButton",
        width=15
    )
    refresh_btn.pack(side="left", padx=5)

    # Add clear button
    clear_btn = ttk.Button(
        controls_frame,
        text="🗑️ Clear Logs",
        command=lambda: clear_tfn_logs(),
        style="Custom.TButton",
        width=15
    )
    clear_btn.pack(side="left", padx=5)

    # Add auto-refresh checkbox
    auto_refresh_var = tk.BooleanVar(value=True)
    auto_refresh_cb = ttk.Checkbutton(
        controls_frame,
        text="Auto Refresh",
        variable=auto_refresh_var,
        style="Custom.TCheckbutton"
    )
    auto_refresh_cb.pack(side="left", padx=20)

    # Create text widget with scrollbar
    text_frame = ttk.Frame(main_container, style="Custom.TFrame")
    text_frame.pack(fill="both", expand=True)

    # Add scrollbar
    scrollbar = ttk.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")

    # Create text widget
    tfn_logs_text = tk.Text(
        text_frame,
        wrap=tk.WORD,
        yscrollcommand=scrollbar.set,
        bg=app.style.lookup('TFrame', 'background'),
        fg=app.style.lookup('TLabel', 'foreground'),
        font=("Consolas", 10)
    )
    tfn_logs_text.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=tfn_logs_text.yview)

    def refresh_tfn_logs():
        """Refresh the logs display"""
        try:
            # Save current position
            current_pos = tfn_logs_text.yview()[1]
            
            # Clear current content
            tfn_logs_text.delete(1.0, tk.END)
            
            # Read and display log file
            if os.path.exists(DEBUG_LOG_FILE):
                with open(DEBUG_LOG_FILE, 'r') as f:
                    logs = f.read()
                    tfn_logs_text.insert(tk.END, logs)
                    
            # Auto-scroll to bottom if we were at bottom before
            if current_pos > 0.99:
                tfn_logs_text.see(tk.END)
                
        except Exception as e:
            logger.error(f"Error refreshing TFN logs: {str(e)}")

    def clear_tfn_logs():
        """Clear the log file and display"""
        if messagebox.askyesno("Clear Logs", "Are you sure you want to clear all logs?"):
            try:
                # Clear log file
                with open(DEBUG_LOG_FILE, 'w') as f:
                    f.write("")
                # Clear display
                tfn_logs_text.delete(1.0, tk.END)
                logger.info("Logs cleared by user")
            except Exception as e:
                logger.error(f"Error clearing logs: {str(e)}")

    def auto_refresh():
        """Auto refresh the logs every 2 seconds if enabled"""
        if auto_refresh_var.get() and tfn_logs_text and tfn_logs_text.winfo_exists():
            refresh_tfn_logs()
        if tfn_logs_text and tfn_logs_text.winfo_exists():
            tfn_logs_text.after(2000, auto_refresh)

    # Initial load
    refresh_tfn_logs()
    
    # Start auto-refresh
    auto_refresh()

def build_main_gui():
    global customer_dropdown, notes_frame, logs_frame, payment_status_var, payment_method_var
    global logs_tree, dashboard_frame, customers_frame, form_canvas, tfn_logs_frame

    # Set window properties
    app.geometry("1000x680")
    app.minsize(1000, 680)

    # Configure styles
    style = ttk.Style()
    
    # Main container
    main_container = ttk.Frame(app, style="Custom.TFrame")
    main_container.pack(fill="both", expand=True)

    # Create notebook for tabs
    notebook = ttk.Notebook(main_container, style="Custom.TNotebook")
    notebook.pack(fill="both", expand=True, padx=10, pady=5)

    # Billing Tab
    billing_frame = ttk.Frame(notebook, style="Custom.TFrame")
    notebook.add(billing_frame, text=" 📝 Billing ")

    # Create scrollable canvas for the form
    form_canvas = tk.Canvas(billing_frame, bg=style.lookup('TFrame', 'background'))
    scrollbar = ttk.Scrollbar(billing_frame, orient="vertical", command=form_canvas.yview)
    scrollable_frame = ttk.Frame(form_canvas, style="Custom.TFrame")

    # Configure scrolling
    scrollable_frame.bind(
        "<Configure>",
        lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all"))
    )
    form_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    form_canvas.configure(yscrollcommand=scrollbar.set)

    # Pack scrollbar and canvas
    scrollbar.pack(side="right", fill="y")
    form_canvas.pack(side="left", fill="both", expand=True)

    # Enable mouse wheel scrolling
    def _on_mousewheel(event):
        form_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    form_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Create form content
    form_content = ttk.Frame(scrollable_frame, style="Custom.TFrame", padding=20)
    form_content.pack(fill="both", expand=True)

    # Customer selection at top
    customer_frame = ttk.LabelFrame(form_content, text="Customer Selection", padding=10)
    customer_frame.pack(fill="x", pady=(0, 15))

    customers = load_customers()
    customer_list = []
    for customer in customers:
        customer_list.append(f"{customer['name']} ({customer['customer_id']})")
    
    ttk.Label(
        customer_frame,
        text="Select Existing Customer:",
        style="Custom.TLabel"
    ).pack(side="left", padx=(0, 10))
    
    customer_dropdown = ttk.Combobox(
        customer_frame,
        values=customer_list,
        state="readonly",
        width=50
    )
    customer_dropdown.pack(side="left")
    customer_dropdown.bind('<<ComboboxSelected>>', autofill_customer_data)

    # Main form section
    form_frame = ttk.LabelFrame(form_content, text="Invoice Details", padding=10)
    form_frame.pack(fill="both", expand=True, pady=(0, 15))

    # Create two columns
    left_frame = ttk.Frame(form_frame)
    left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    right_frame = ttk.Frame(form_frame)
    right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

    # Left column fields
    left_fields = [
        "Customer ID", "Name", "Tenant Name", 
        "Customer Address", "Customer GSTIN", "Email"
    ]

    for i, label in enumerate(left_fields):
        field_frame = ttk.Frame(left_frame)
        field_frame.pack(fill="x", pady=2)
        
        ttk.Label(
            field_frame,
            text=f"{label}:",
            style="Custom.TLabel",
            width=15
        ).pack(side="left", padx=(0, 5))
        
        field = ttk.Entry(field_frame, width=30)
        field.pack(side="left", fill="x", expand=True)
        fields[label] = field

    # Right column fields
    right_fields = [
        ("Plan", PLANS),
        ("Months", [str(i) for i in range(1, 13)]),
        ("Billing Period From", "date"),
        ("Billing Period To", "date"),
        ("Total Amount", None),
        ("Discount", None),
        ("Late Fee", None)
    ]

    for i, (label, values) in enumerate(right_fields):
        field_frame = ttk.Frame(right_frame)
        field_frame.pack(fill="x", pady=2)
        
        ttk.Label(
            field_frame,
            text=f"{label}:",
            style="Custom.TLabel",
            width=15
        ).pack(side="left", padx=(0, 5))
        
        if values == "date":
            field = CustomDateEntry(field_frame)
        elif values:
            field = ttk.Combobox(
                field_frame,
                values=values,
                state="readonly",
                width=27
            )
            field.set(values[0])
        else:
            field = ttk.Entry(field_frame, width=30)
        
        field.pack(side="left", fill="x", expand=True)
        fields[label] = field

    # Payment section
    payment_frame = ttk.LabelFrame(form_content, text="Payment Details", padding=10)
    payment_frame.pack(fill="x", pady=(0, 15))

    status_frame = ttk.Frame(payment_frame)
    status_frame.pack(side="left", padx=20)

    payment_status_var = tk.StringVar(value="Unpaid")
    ttk.Label(
        status_frame,
        text="Payment Status:",
        style="Custom.TLabel"
    ).pack(side="left", padx=(0, 10))

    ttk.Radiobutton(
        status_frame,
        text="Paid",
        variable=payment_status_var,
        value="Paid"
    ).pack(side="left", padx=5)

    ttk.Radiobutton(
        status_frame,
        text="Unpaid",
        variable=payment_status_var,
        value="Unpaid"
    ).pack(side="left", padx=5)

    method_frame = ttk.Frame(payment_frame)
    method_frame.pack(side="left")

    payment_method_var = tk.StringVar()
    ttk.Label(
        method_frame,
        text="Payment Method:",
        style="Custom.TLabel"
    ).pack(side="left", padx=(0, 10))

    payment_method = ttk.Combobox(
        method_frame,
        textvariable=payment_method_var,
        values=["Cash", "UPI"],
        state="readonly",
        width=15
    )
    payment_method.pack(side="left")

    # Notes section
    notes_frame = ttk.LabelFrame(form_content, text="Additional Notes", padding=10)
    notes_frame.pack(fill="x", pady=(0, 15))
    
    notes_text = tk.Text(notes_frame, height=4, width=50)
    notes_text.pack(fill="x")
    notes_frame = notes_text  # Assign to global notes_frame

    # Buttons
    button_frame = ttk.Frame(form_content)
    button_frame.pack(fill="x")

    ttk.Button(
    button_frame,
    text="Generate Invoice",
    command=validate_and_submit,
        style="Custom.TButton",
        width=20
    ).pack(side="left", padx=5)

    ttk.Button(
        button_frame,
        text="Clear Form",
        command=clear_form,
        style="Custom.TButton",
        width=15
    ).pack(side="left", padx=5)

    # Customers Tab
    customers_frame = ttk.Frame(notebook, style="Custom.TFrame")
    notebook.add(customers_frame, text=" 👥 Customers ")

    # Logs Tab
    logs_frame = ttk.Frame(notebook, style="Custom.TFrame")
    notebook.add(logs_frame, text=" 📊 Logs ")

    # Dashboard Tab
    dashboard_frame = ttk.Frame(notebook, style="Custom.TFrame")
    notebook.add(dashboard_frame, text=" 📈 Dashboard ")

    # TFN Logs Tab
    tfn_logs_frame = ttk.Frame(notebook, style="Custom.TFrame")
    notebook.add(tfn_logs_frame, text=" 🔍 TFN Logs ")

    # Create the views
    create_customers_view()
    create_logs_view()
    create_dashboard_view()
    create_tfn_logs_view()

    # Update canvas color when theme changes
    app.bind("<<ThemeChanged>>", update_canvas_color)

def create_customers_view():
    """Create the customers view with detailed customer information"""
    global customers_tree

    # Clear any existing widgets
    for widget in customers_frame.winfo_children():
        widget.destroy()

    # Create main container with padding
    main_container = ttk.Frame(customers_frame, style="Custom.TFrame", padding=15)
    main_container.pack(fill="both", expand=True)

    # Create top controls frame
    controls_frame = ttk.Frame(main_container, style="Custom.TFrame")
    controls_frame.pack(fill="x", pady=(0, 10))

    # Search frame
    search_frame = ttk.LabelFrame(controls_frame, text="Search & Filter", padding=10)
    search_frame.pack(side="left", fill="x", expand=True)

    # Search entry
    search_var = tk.StringVar()
    ttk.Label(search_frame, text="Search:", style="Custom.TLabel").pack(side="left", padx=(0, 5))
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=(0, 10))

    # Actions frame
    actions_frame = ttk.Frame(controls_frame, style="Custom.TFrame")
    actions_frame.pack(side="right", padx=5)

    def add_customer():
        """Open dialog to add new customer"""
        dialog = tk.Toplevel(app)
        dialog.title("Add New Customer")
        dialog.geometry("500x600")
        dialog.grab_set()
        if os.path.exists(ICO_PATH):
            try:
                dialog.iconbitmap(ICO_PATH)
            except Exception as e:
                print(f"Error setting dialog icon: {str(e)}")

        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Create form frame
        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill="both", expand=True)

        # Form fields
        fields = {}
        field_labels = [
            "Customer ID*", "Name*", "Tenant Name*", "Customer Address*",
            "Customer GSTIN", "Email", "Phone", "Plan",
            "Installation Date", "Notes"
        ]

        for i, label in enumerate(field_labels):
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill="x", pady=5)

            ttk.Label(
                field_frame,
                text=f"{label}:",
                style="Custom.TLabel",
                width=15
            ).pack(side="left", padx=(0, 5))

            if label == "Plan":
                # Dropdown for plans
                field = ttk.Combobox(field_frame, values=PLANS, state="readonly")
                field.set(PLANS[0])
            elif label == "Installation Date":
                # Date picker
                field = CustomDateEntry(field_frame)
            elif label == "Notes":
                # Text area for notes
                field = tk.Text(field_frame, height=3, width=30)
            else:
                # Regular entry field
                field = ttk.Entry(field_frame, width=30)

            field.pack(side="left", fill="x", expand=True)
            fields[label.replace("*", "")] = field

        def save_customer():
            # Validate required fields
            required_fields = ["Customer ID", "Name", "Tenant Name", "Customer Address"]
            for field in required_fields:
                if not fields[field].get():
                    messagebox.showerror("Error", f"{field} is required!")
                    return

            # Check for duplicate customer ID
            customer_id = fields["Customer ID"].get()
            customers = load_customers()
            if any(c["customer_id"] == customer_id for c in customers):
                messagebox.showerror("Error", "Customer ID already exists!")
                return

            # Prepare customer data
            customer_data = {
                "customer_id": fields["Customer ID"].get(),
                "name": fields["Name"].get(),
                "tenant_name": fields["Tenant Name"].get(),
                "customer_address": fields["Customer Address"].get(),
                "customer_gstin": fields["Customer GSTIN"].get(),
                "email": fields["Email"].get(),
                "phone": fields["Phone"].get(),
                "plan": fields["Plan"].get(),
                "installation_date": fields["Installation Date"].get(),
                "notes": fields["Notes"].get("1.0", tk.END).strip(),
                "created_date": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "last_modified": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }

            # Save customer
            save_customer_data(customer_data)
            refresh_customers_view()
            dialog.destroy()
            messagebox.showinfo("Success", "Customer added successfully!")

        # Buttons frame
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill="x", pady=20)

        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=dialog.destroy,
            style="Custom.TButton",
            width=15
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons_frame,
            text="Save",
            command=save_customer,
            style="Custom.TButton",
            width=15
        ).pack(side="right", padx=5)

    def edit_customer():
        """Edit selected customer"""
        selected = customers_tree.selection()
        if not selected:
            messagebox.showwarning("Edit Customer", "Please select a customer to edit!")
            return

        # Get customer data
        customer_id = customers_tree.item(selected[0])["values"][0]
        customers = load_customers()
        customer_data = next((c for c in customers if c["customer_id"] == customer_id), None)
        if not customer_data:
            return

        # Create edit dialog similar to add dialog
        dialog = tk.Toplevel(app)
        dialog.title("Edit Customer")
        dialog.geometry("500x600")
        dialog.grab_set()
        if os.path.exists(ICO_PATH):
            try:
                dialog.iconbitmap(ICO_PATH)
            except Exception as e:
                print(f"Error setting dialog icon: {str(e)}")

        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Create form frame
        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill="both", expand=True)

        # Form fields
        fields = {}
        field_labels = [
            "Customer ID*", "Name*", "Tenant Name*", "Customer Address*",
            "Customer GSTIN", "Email", "Phone", "Plan",
            "Installation Date", "Notes"
        ]

        for i, label in enumerate(field_labels):
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill="x", pady=5)

            ttk.Label(
                field_frame,
                text=f"{label}:",
                style="Custom.TLabel",
                width=15
            ).pack(side="left", padx=(0, 5))

            if label == "Plan":
                field = ttk.Combobox(field_frame, values=PLANS, state="readonly")
                field.set(customer_data.get("plan", PLANS[0]))
            elif label == "Installation Date":
                field = CustomDateEntry(field_frame)
                if customer_data.get("installation_date"):
                    field.set_date(customer_data["installation_date"])
            elif label == "Notes":
                field = tk.Text(field_frame, height=3, width=30)
                if customer_data.get("notes"):
                    field.insert("1.0", customer_data["notes"])
            else:
                field = ttk.Entry(field_frame, width=30)
                field.insert(0, customer_data.get(label.replace("*", "").lower().replace(" ", "_"), ""))
                if label == "Customer ID":
                    field.configure(state="readonly")  # Can't change customer ID

            field.pack(side="left", fill="x", expand=True)
            fields[label.replace("*", "")] = field

        def update_customer():
            # Validate required fields
            required_fields = ["Name", "Tenant Name", "Customer Address"]
            for field in required_fields:
                if not fields[field].get():
                    messagebox.showerror("Error", f"{field} is required!")
                    return

            # Update customer data
            updated_data = {
                "customer_id": customer_data["customer_id"],
                "name": fields["Name"].get(),
                "tenant_name": fields["Tenant Name"].get(),
                "customer_address": fields["Customer Address"].get(),
                "customer_gstin": fields["Customer GSTIN"].get(),
                "email": fields["Email"].get(),
                "phone": fields["Phone"].get(),
                "plan": fields["Plan"].get(),
                "installation_date": fields["Installation Date"].get(),
                "notes": fields["Notes"].get("1.0", tk.END).strip(),
                "created_date": customer_data.get("created_date", ""),
                "last_modified": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }

            # Save updated customer
            save_customer_data(updated_data)
            refresh_customers_view()
            dialog.destroy()
            messagebox.showinfo("Success", "Customer updated successfully!")

        # Buttons frame
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill="x", pady=20)

        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=dialog.destroy,
            style="Custom.TButton",
            width=15
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons_frame,
            text="Update",
            command=update_customer,
            style="Custom.TButton",
            width=15
        ).pack(side="right", padx=5)

    def delete_customer():
        """Delete selected customer"""
        selected = customers_tree.selection()
        if not selected:
            messagebox.showwarning("Delete Customer", "Please select a customer to delete!")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this customer?"):
            return

        customer_id = customers_tree.item(selected[0])["values"][0]
        customers = load_customers()
        customers = [c for c in customers if c["customer_id"] != customer_id]
        
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
        
        refresh_customers_view()
        messagebox.showinfo("Success", "Customer deleted successfully!")

    def export_customers():
        """Export customers data to Excel/CSV"""
        if not customers_tree.get_children():
            messagebox.showwarning("Export", "No data to export!")
            return

        try:
            # Get all customers data
            customers = []
            for item in customers_tree.get_children():
                values = customers_tree.item(item)["values"]
                customers.append({
                    "Customer ID": values[0],
                    "Name": values[1],
                    "Tenant Name": values[2],
                    "Address": values[3],
                    "GSTIN": values[4],
                    "Email": values[5],
                    "Phone": values[6],
                    "Plan": values[7],
                    "Installation Date": values[8],
                    "Created Date": values[9],
                    "Last Modified": values[10]
                })

            # Create DataFrame
            df = pd.DataFrame(customers)

            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
                title="Export Customers"
            )

            if file_path:
                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)
                messagebox.showinfo("Export", "Customers data exported successfully!")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # Add action buttons
    ttk.Button(
        actions_frame,
        text="Add Customer",
        command=add_customer,
        style="Custom.TButton",
        width=15
    ).pack(side="left", padx=5)

    ttk.Button(
        actions_frame,
        text="Edit Customer",
        command=edit_customer,
        style="Custom.TButton",
        width=15
    ).pack(side="left", padx=5)

    ttk.Button(
        actions_frame,
        text="Delete Customer",
        command=delete_customer,
        style="Custom.TButton",
        width=15
    ).pack(side="left", padx=5)

    ttk.Button(
        actions_frame,
        text="Export",
        command=export_customers,
        style="Custom.TButton",
        width=10
    ).pack(side="left", padx=5)

    # Create Treeview
    tree_frame = ttk.Frame(main_container)
    tree_frame.pack(fill="both", expand=True)

    # Columns
    columns = (
        "Customer ID", "Name", "Tenant Name", "Address", "GSTIN",
        "Email", "Phone", "Plan", "Installation Date",
        "Created Date", "Last Modified"
    )

    customers_tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        show="headings",
        style="Custom.Treeview"
    )

    # Configure columns
    for col in columns:
        customers_tree.heading(col, text=col, anchor="w")
        width = 150 if col in ["Name", "Tenant Name", "Address"] else 100
        customers_tree.column(col, width=width, anchor="w")

    # Add scrollbars
    y_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=customers_tree.yview)
    x_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=customers_tree.xview)
    customers_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

    # Pack elements
    y_scrollbar.pack(side="right", fill="y")
    x_scrollbar.pack(side="bottom", fill="x")
    customers_tree.pack(side="left", fill="both", expand=True)

    def refresh_customers_view():
        """Refresh the customers treeview"""
        # Clear existing items
        for item in customers_tree.get_children():
            customers_tree.delete(item)

        # Load and display customers
        customers = load_customers()
        for customer in customers:
            customers_tree.insert("", "end", values=(
                customer.get("customer_id", ""),
                customer.get("name", ""),
                customer.get("tenant_name", ""),
                customer.get("customer_address", ""),
                customer.get("customer_gstin", ""),
                customer.get("email", ""),
                customer.get("phone", ""),
                customer.get("plan", ""),
                customer.get("installation_date", ""),
                customer.get("created_date", ""),
                customer.get("last_modified", "")
            ))

    def filter_customers(*args):
        """Filter customers based on search text"""
        search_text = search_var.get().lower()
        
        # Clear existing items
        for item in customers_tree.get_children():
            customers_tree.delete(item)
        
        # Load and filter customers
        customers = load_customers()
        for customer in customers:
            # Check if search text matches any field
            if any(search_text in str(value).lower() for value in customer.values()):
                customers_tree.insert("", "end", values=(
                    customer.get("customer_id", ""),
                    customer.get("name", ""),
                    customer.get("tenant_name", ""),
                    customer.get("customer_address", ""),
                    customer.get("customer_gstin", ""),
                    customer.get("email", ""),
                    customer.get("phone", ""),
                    customer.get("plan", ""),
                    customer.get("installation_date", ""),
                    customer.get("created_date", ""),
                    customer.get("last_modified", "")
                ))

    # Bind search
    search_var.trace('w', filter_customers)

    # Initial load
    refresh_customers_view()

@log_function_entry_exit
def save_customer_data(customer_data):
    """Save customer data to the database"""
    logger.info(f"Saving customer data for ID: {customer_data['customer_id']}")
    customers = load_customers()
    
    # Check if customer exists
    exists = False
    for i, customer in enumerate(customers):
        if customer["customer_id"] == customer_data["customer_id"]:
            logger.debug(f"Updating existing customer: {customer_data['customer_id']}")
            customers[i] = customer_data  # Update existing
            exists = True
            break
    
    if not exists:
        logger.debug(f"Adding new customer: {customer_data['customer_id']}")
        customers.append(customer_data)  # Add new
    
    # Save to file
    try:
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
        logger.info(f"Customer data saved successfully: {customer_data['customer_id']}")
    except Exception as e:
        logger.error(f"Error saving customer data: {str(e)}\n{traceback.format_exc()}")
        raise

@log_function_entry_exit
def clear_form():
    """Clear all form fields properly handling different widget types"""
    logger.info("Clearing form fields")
    for field_name, widget in fields.items():
        logger.debug(f"Clearing field: {field_name}")
        if isinstance(widget, CustomDateEntry):
            widget.set_date(datetime.now())
        elif isinstance(widget, ttk.Combobox):
            if field_name == "Plan":
                widget.set(PLANS[0])
            elif field_name == "Months":
                widget.set("1")
        elif hasattr(widget, 'delete'):
            widget.delete(0, tk.END)
    logger.info("Form cleared successfully")

# After the save_customer_data function and before the if __name__ == "__main__" block

@log_function_entry_exit
def login_window():
    """Create and show the login window"""
    global app
    
    if app is None:
        logger.error("Main application window not initialized")
        return
        
    logger.info("Creating login window")
    login = tk.Toplevel(app)
    login.title("Login")
    login.geometry("300x200")
    login.grab_set()
    if os.path.exists(ICO_PATH):
        try:
            login.iconbitmap(ICO_PATH)
            logger.debug("Login window icon set successfully")
        except Exception as e:
            logger.error(f"Error setting login window icon: {str(e)}")
    
    # Center the login window
    window_width = 300
    window_height = 200
    screen_width = login.winfo_screenwidth()
    screen_height = login.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    login.geometry(f"{window_width}x{window_height}+{x}+{y}")
    logger.debug("Login window centered on screen")
    
    # Create main frame with padding
    main_frame = ttk.Frame(login, padding="20")
    main_frame.pack(fill="both", expand=True)
    
    ttk.Label(main_frame, text="Username").pack(pady=5)
    user_var = tk.StringVar()
    user_entry = ttk.Entry(main_frame, textvariable=user_var)
    user_entry.pack(pady=5)
    
    ttk.Label(main_frame, text="Password").pack(pady=5)
    pass_var = tk.StringVar()
    pass_entry = ttk.Entry(main_frame, textvariable=pass_var, show="*")
    pass_entry.pack(pady=5)
    
    msg_label = ttk.Label(main_frame, text="")
    msg_label.pack(pady=5)
    
    def do_login(event=None):
        logger.info(f"Login attempt for user: {user_var.get()}")
        users = load_users()
        for u in users:
            if u["username"] == user_var.get() and u["password"] == pass_var.get():
                logger.info(f"Successful login for user: {u['username']} with role: {u['role']}")
                current_user["username"] = u["username"]
                current_user["role"] = u["role"]
                login.grab_release()
                login.destroy()
                app.deiconify()  # Show main window
                build_main_gui()
                return
        logger.warning(f"Failed login attempt for user: {user_var.get()}")
        msg_label.config(text="Invalid credentials", foreground="red")
        pass_var.set("")  # Clear password field on failed attempt
    
    login_btn = ttk.Button(main_frame, text="Login", command=do_login, style="primary.TButton")
    login_btn.pack(pady=10)
    
    # Bind Enter key to both entry widgets and the login window itself
    user_entry.bind('<Return>', lambda e: pass_entry.focus())  # Move to password field
    pass_entry.bind('<Return>', do_login)  # Trigger login
    login.bind('<Return>', do_login)  # Allow Enter from anywhere in the window
    
    # Set initial focus to username field
    user_entry.focus()
    
    # Handle window close button
    def on_closing():
        logger.info("Application closed from login window")
        app.quit()  # Properly close the application
        
    login.protocol("WM_DELETE_WINDOW", on_closing)

@log_function_entry_exit
def log_invoice(data, pdf_filename):
    """Log invoice details to JSON file"""
    logger.info(f"Logging invoice: {pdf_filename}")
    
    if os.path.exists(INVOICE_LOG_FILE):
        try:
            with open(INVOICE_LOG_FILE, 'r') as f:
                logs = json.load(f)
                logger.debug(f"Loaded existing logs: {len(logs)} entries")
        except Exception as e:
            logger.error(f"Error loading existing logs: {str(e)}")
            logs = []
    else:
        logger.debug("No existing log file found, creating new")
        logs = []

    # Use consistent datetime format
    current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    log_entry = {
        "filename": pdf_filename,
        "datetime": current_time,
        "invoice_num": f"TF/25-26/HR/{data['invoice_num']}",
        "customer_name": data["name"],
        "customer_id": data["customer_id"],
        "amount": data["total_amount"],
        "status": data["payment_status"],
        "payment_date": datetime.now().strftime("%d-%m-%Y") if data["payment_status"] == "Paid" else "",
        "payment_method": data["payment_method"]
    }
    logger.debug(f"Created log entry: {json.dumps(log_entry, indent=2)}")
    
    logs.append(log_entry)
    try:
        with open(INVOICE_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
        logger.info("Invoice log saved successfully")
    except Exception as e:
        logger.error(f"Error saving invoice log: {str(e)}\n{traceback.format_exc()}")
        raise

@log_function_entry_exit
def export_logs():
    """Export logs to Excel/CSV"""
    logger.info("Starting logs export")
    
    if not logs_tree.get_children():
        logger.warning("Export cancelled: No data to export")
        messagebox.showwarning("Export", "No data to export!")
        return
        
    try:
        # Get all items from tree
        data = []
        for item in logs_tree.get_children():
            values = logs_tree.item(item)['values']
            data.append({
                'Date': values[0],
                'Invoice No': values[1],
                'Customer': values[2],
                'Amount': values[3].replace('₹', ''),
                'Status': values[4],
                'Payment Method': values[5]
            })
        logger.debug(f"Collected {len(data)} records for export")
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
            title="Export Logs"
        )
        
        if file_path:
            logger.info(f"Exporting logs to: {file_path}")
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
                logger.debug("Exported to Excel format")
            else:
                df.to_csv(file_path, index=False)
                logger.debug("Exported to CSV format")
            messagebox.showinfo("Export", "Logs exported successfully!")
            logger.info("Logs export completed successfully")
        else:
            logger.info("Export cancelled by user")
            
    except Exception as e:
        logger.error(f"Export error: {str(e)}\n{traceback.format_exc()}")
        messagebox.showerror("Export Error", str(e))

@log_function_entry_exit
def update_payment_status():
    """Update payment status for selected invoice"""
    logger.info("Starting payment status update")
    
    selected = logs_tree.selection()
    if not selected:
        logger.warning("No invoice selected for status update")
        messagebox.showwarning("Update Status", "Please select an invoice to update!")
        return
            
    item = logs_tree.item(selected[0])
    current_status = item['values'][4]
    invoice_no = item['values'][1]
    logger.debug(f"Selected invoice: {invoice_no}, current status: {current_status}")
        
    # Create update dialog
    dialog = tk.Toplevel(app)
    dialog.title("Update Payment Status")
    dialog.geometry("300x250")
    dialog.resizable(False, False)
    dialog.grab_set()
    
    if os.path.exists(ICO_PATH):
        try:
            dialog.iconbitmap(ICO_PATH)
            logger.debug("Dialog icon set successfully")
        except Exception as e:
            logger.error(f"Error setting dialog icon: {str(e)}")
        
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 300) // 2
    y = (dialog.winfo_screenheight() - 250) // 2
    dialog.geometry(f"300x250+{x}+{y}")
    logger.debug("Dialog window centered")
        
    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill="both", expand=True)
        
    # Status selection
    ttk.Label(frame, text="Payment Status:", style="Custom.TLabel").pack(pady=(0, 10))
    status_var = tk.StringVar(value=current_status)
    status_radio_frame = ttk.Frame(frame)
    status_radio_frame.pack(pady=(0, 15))
    ttk.Radiobutton(status_radio_frame, text="Paid", variable=status_var, value="Paid").pack(side="left", padx=10)
    ttk.Radiobutton(status_radio_frame, text="Unpaid", variable=status_var, value="Unpaid").pack(side="left", padx=10)
        
    # Payment method
    method_frame = ttk.Frame(frame)
    method_frame.pack(pady=(0, 20))
    ttk.Label(method_frame, text="Payment Method:", style="Custom.TLabel").pack(pady=(0, 5))
    method_var = tk.StringVar()
    method_combo = ttk.Combobox(method_frame, textvariable=method_var, values=["Cash", "UPI"], state="readonly", width=15)
    method_combo.pack()

    def save_status():
        new_status = status_var.get()
        payment_method = method_var.get() if new_status == "Paid" else ""
        logger.info(f"Saving new status for invoice {invoice_no}: {new_status} ({payment_method})")
            
        # Update logs file
        if os.path.exists(INVOICE_LOG_FILE):
            try:
                with open(INVOICE_LOG_FILE, 'r') as f:
                    logs = json.load(f)
                    
                for log in logs:
                    if log.get('invoice_num') == invoice_no:
                        log['status'] = new_status
                        log['payment_method'] = payment_method
                        if new_status == "Paid":
                            log['payment_date'] = datetime.now().strftime("%d-%m-%Y")
                        else:
                            log['payment_date'] = ""
                        logger.debug(f"Updated log entry: {json.dumps(log, indent=2)}")
                
                with open(INVOICE_LOG_FILE, 'w') as f:
                    json.dump(logs, f, indent=2)
                logger.info("Payment status updated successfully")
                
                # Refresh logs view
                if logs_tree and logs_tree.winfo_exists():
                    filter_logs()
                dialog.destroy()
                messagebox.showinfo("Success", "Payment status updated successfully!")
            except Exception as e:
                logger.error(f"Error updating payment status: {str(e)}\n{traceback.format_exc()}")
                messagebox.showerror("Error", f"Failed to update payment status: {str(e)}")

    # Create a bottom frame for the save button
    button_frame = ttk.Frame(frame)
    button_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
    # Add save button with custom style
    save_btn = ttk.Button(
        button_frame,
        text="Save Changes",
        command=lambda: save_status(),
        style="Custom.TButton",
        width=15
    )
    save_btn.pack(pady=(0, 10))

    def on_status_change(*args):
        if status_var.get() == "Paid":
            method_combo.configure(state="readonly")
            logger.debug("Enabled payment method selection")
        else:
            method_combo.configure(state="disabled")
            method_var.set("")
            logger.debug("Disabled payment method selection")

    # Bind status change
    status_var.trace('w', on_status_change)
    
    # Initial state
    on_status_change()
    
    # Make dialog modal
    dialog.transient(app)
    dialog.wait_window()

def draw_watermark(canvas, doc):
    if os.path.exists(LOGO_PATH):
        from reportlab.lib.utils import ImageReader
        img = ImageReader(LOGO_PATH)
        page_width, page_height = A4
        wm_width, wm_height = 450, 450  # Adjust as needed
        x = (page_width - wm_width) / 2
        y = (page_height - wm_height) / 2
        canvas.saveState()
        canvas.setFillAlpha(0.08)  # Opacity
        canvas.drawImage(img, x, y, wm_width, wm_height, mask='auto', preserveAspectRatio=True)
        canvas.restoreState()

def exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Handle keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    error_msg = f"An unexpected error occurred:\n\n{str(exc_value)}"
    try:
        messagebox.showerror("Error", error_msg)
    except:
        pass  # If we can't show the error dialog, at least we logged it

# Set up global exception handler
sys.excepthook = exception_handler

class CustomDateEntry(ttk.DateEntry):
    """Custom date entry widget that extends ttk.DateEntry with additional functionality"""
    @log_function_entry_exit
    def __init__(self, parent, **kwargs):
        # Set default date format
        kwargs['dateformat'] = '%d-%m-%Y'
        # Set first day of week to Monday (0)
        kwargs['firstweekday'] = 0
        # Set bootstyle
        kwargs['bootstyle'] = 'primary'
        # Call parent constructor
        super().__init__(parent, **kwargs)
        # Set width
        self.configure(width=27)
        logger.debug("Initialized CustomDateEntry widget")
        
    @log_function_entry_exit
    def set_date(self, date_str):
        """Set date from string in DD-MM-YYYY format"""
        try:
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%d-%m-%Y')
                self.entry.delete(0, tk.END)
                self.entry.insert(0, date_obj.strftime('%d-%m-%Y'))
                logger.debug(f"Set date from string: {date_str}")
            else:
                self.entry.delete(0, tk.END)
                self.entry.insert(0, date_str.strftime('%d-%m-%Y'))
                logger.debug(f"Set date from datetime object: {date_str}")
        except Exception as e:
            logger.warning(f"Invalid date format, using current date: {str(e)}")
            # If date is invalid, set to current date
            self.entry.delete(0, tk.END)
            self.entry.insert(0, datetime.now().strftime('%d-%m-%Y'))
            
    @log_function_entry_exit
    def get(self):
        """Get the current date string"""
        date_str = self.entry.get()
        logger.debug(f"Getting date: {date_str}")
        return date_str

# ... rest of the code ...

# Initialize and start the application
if __name__ == "__main__":
    start_application()