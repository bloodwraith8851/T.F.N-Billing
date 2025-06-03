# Thunderstorm Bill Generator

A comprehensive billing and invoice management system for Thunderstorm Fibernet.

## Features

- Generate professional invoices with custom templates
- Manage customer database
- Track payment status and history
- Real-time analytics dashboard
- Comprehensive logging system
- Dark/Light theme support

## Installation

1. Make sure you have Python 3.8 or higher installed
2. Clone or download this repository
3. Run the launcher:
   ```bash
   python launcher.py
   ```
   The launcher will automatically:
   - Create necessary directories
   - Install required dependencies
   - Initialize the database
   - Start the application

## Default Login

- Username: admin
- Password: admin

## Directory Structure

- `assets/` - Contains logo and icon files
- `logs/` - Application logs
- `output_invoices/` - Generated PDF invoices
- `main.py` - Main application code
- `launcher.py` - Application launcher and setup
- `requirements.txt` - Python package dependencies

## Dependencies

- ttkbootstrap>=1.10.1 - Modern themed widgets
- reportlab>=4.0.4 - PDF generation
- Pillow>=10.0.0 - Image processing
- matplotlib>=3.7.1 - Analytics visualizations
- pandas>=2.0.3 - Data processing

## Development

To modify the application:
1. Make changes to `main.py` or other source files
2. Test changes by running `launcher.py`
3. For deployment, use PyInstaller:
   ```bash
   pyinstaller --onefile --windowed --icon=assets/logo.ico launcher.py
   ```

## Logging

The application maintains comprehensive logs in:
- `logs/tfn_billing_debug.log` - Detailed debug logs
- Console output - Info level logs
- TFN Logs tab - Real-time log viewer

## Support

For issues or questions:
1. Check the logs in `logs/tfn_billing_debug.log`
2. Use the TFN Logs tab in the application
3. Contact support at thunderstromfibernet@gmail.com 