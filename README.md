# POS System - Point of Sale Application

A comprehensive desktop Point of Sale (POS) system built with Python, featuring role-based access control, order management, invoice generation with QR codes, and customizable templates.

## Features

### For All Users
- **POS Order Management**: Create orders with custom items, apply templates, calculate taxes
- **Frequent Order Templates**: Save and reuse common order configurations
- **Invoice Generation**: Generate PDF invoices with customizable templates

### For Administrators
- **Order History**: View, search, and manage all orders
- **User Management**: Create and manage user accounts with role-based permissions
- **Invoice Template Designer**: Create custom invoice layouts with business information
- **System Settings**: Configure currency, tax rates, locales, and more

## System Requirements

- Python 3.8 or higher
- Linux/macOS/Windows operating system
- Tkinter support (GUI framework)

## Installation

### 1. Install System Dependencies

#### On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install python3-tk python3-pip python3-dev
```

#### On macOS:
```bash
# Tkinter comes pre-installed with Python on macOS
brew install python3
```

#### On Windows:
```bash
# Tkinter is included with Python installation on Windows
# Download Python from python.org
```

### 2. Install Python Dependencies

Navigate to the project directory and install required packages:

```bash
cd "/home/eshare/wordpress-6.8.1/simple pos"
pip install -r requirements.txt
```

Or install manually:
```bash
pip install Pillow reportlab qrcode bcrypt python-dateutil
```

### 3. Run the Application

```bash
python3 main.py
```

## Default Credentials

- **Username**: admin
- **Password**: admin123

**⚠️ Important**: Change the default admin password immediately after first login!

## User Guide

### 1. Login
- Enter your username and password
- The system supports two roles: Admin and User

### 2. POS Order Tab (All Users)
- **Add Items**: Enter item name, quantity, and unit price
- **Apply Templates**: Select from frequent order templates
- **Tax Settings**: Configure tax rate for the order
- **Finalize Order**: Complete the order and generate invoice
- **Print Invoice**: Generate and print PDF invoice

### 3. Frequent Orders Tab (All Users)
- **Create Templates**: Save frequently used item combinations
- **Personal vs Global**: Users see their own templates; Admins can create global templates
- **Manage Templates**: Edit or delete existing templates

### 4. Order History Tab (Admin Only)
- **Filter Orders**: Search by date range, user, or status
- **View Details**: See complete order information
- **Print Historical Invoices**: Reprint invoices from snapshots
- **Cancel Orders**: Mark orders as canceled (audit trail preserved)

### 5. User Management Tab (Admin Only)
- **Create Users**: Add new users with username/password
- **Assign Roles**: Set user as Admin or regular User
- **Manage Status**: Activate/deactivate user accounts
- **Reset Passwords**: Change user passwords

### 6. Invoice Templates Tab (Admin Only)
- **Design Templates**: Create custom invoice layouts
- **Business Information**: Add company details, logo, contact info
- **Customize Layout**: Set headers, footers, and styling
- **Set Default**: Choose which template is used by default

### 7. Settings Tab (Admin Only)
- **Currency**: Set currency symbol
- **Tax Rate**: Configure default tax rate
- **Locale**: Set language and regional settings
- **Page Size**: Choose between A4 and Letter
- **System Info**: View database statistics

## Database Structure

The system uses SQLite for data persistence with the following tables:
- `users`: User accounts and authentication
- `orders`: Order records with totals and status
- `order_items`: Individual items within orders
- `frequent_orders`: Saved order templates
- `invoice_templates`: Custom invoice designs
- `invoice_assets`: Logos and QR codes for invoices
- `settings`: System configuration

## Security Features

- **Password Hashing**: Bcrypt encryption for secure password storage
- **Role-Based Access**: Separate permissions for Admin and User roles
- **Session Management**: Secure login/logout functionality
- **Input Validation**: Comprehensive validation for all user inputs
- **Audit Trail**: Immutable order history for compliance

## Data Validation Rules

- **Item Name**: 1-128 characters
- **Quantity**: Positive decimal, min 1, max 999,999
- **Unit Price**: Non-negative, max 9,999,999.99
- **Tax Rate**: 0-100%
- **Password**: Minimum 6 characters

## Backup and Recovery

### Export Database
1. Go to File → Export Database
2. Choose location to save backup
3. Database saved as SQLite file

### Import Database
1. Go to File → Import Database
2. Select backup file
3. Restart application

## Troubleshooting

### Tkinter Not Found Error
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

### Permission Errors
- Ensure the user has write permissions in the application directory
- Check that pos_system.db is writable

### Invoice Generation Issues
- Verify reportlab is installed: `pip install reportlab`
- Check that qrcode is installed: `pip install qrcode[pil]`

## Testing Credentials

For testing purposes, you can create additional users:

1. Login as admin
2. Go to Users tab
3. Create test users with different roles:
   - Username: user1, Password: user123, Role: user
   - Username: admin2, Password: admin456, Role: admin

## Performance Considerations

- Supports 1,000+ orders with instant queries
- Indexed database fields for fast searching
- Optimized PDF generation
- Efficient memory usage

## Keyboard Shortcuts

- **Enter**: Move to next field
- **F5**: Refresh current tab
- **Tab**: Navigate between controls

## Development

### Project Structure
```
simple pos/
├── main.py              # Application entry point
├── database.py          # Database initialization and connection
├── auth.py              # Authentication and authorization
├── models.py            # Business logic and data models
├── login_window.py      # Login interface
├── pos_order_tab.py     # POS order screen
├── admin_tabs.py        # Admin-only interfaces
├── invoice_generator.py # PDF invoice generation
├── requirements.txt     # Python dependencies
├── pos_system.db        # SQLite database (created on first run)
└── README.md           # This file
```

### Adding New Features
1. Extend the database schema in `database.py`
2. Add business logic in `models.py`
3. Create UI components in respective tab files
4. Update the main application in `main.py`

## License

This POS System is provided as-is for business use. Modify and distribute according to your needs.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the user guide
3. Examine the application logs in `pos_system.log`

## Version

POS System v1.0 - Initial Release

---

**Note**: This application runs completely offline and does not require internet connectivity except for initial dependency installation.
