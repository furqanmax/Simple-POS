"""
Database initialization and connection management for POS system
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="pos_system.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def get_connection(self):
        """Get a database connection with foreign keys enabled"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Invoice templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                header_json TEXT,
                footer_json TEXT,
                styles_json TEXT,
                business_info_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                tax_rate DECIMAL(5,2) DEFAULT 0,
                tax_total DECIMAL(10,2) DEFAULT 0,
                grand_total DECIMAL(10,2) NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('finalized', 'canceled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invoice_template_id INTEGER,
                invoice_snapshot_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (invoice_template_id) REFERENCES invoice_templates(id)
            )
        """)
        
        # Order items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity DECIMAL(10,3) NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                line_total DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        
        # Frequent orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frequent_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                owner_user_id INTEGER,
                items_json TEXT NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id),
                UNIQUE(label, owner_user_id)
            )
        """)
        
        # Invoice assets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('logo', 'qr')),
                storage_kind TEXT NOT NULL CHECK (storage_kind IN ('file', 'blob')),
                path TEXT,
                blob BLOB,
                meta_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES invoice_templates(id) ON DELETE CASCADE
            )
        """)
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                currency_symbol TEXT DEFAULT '₹',
                default_tax_rate DECIMAL(5,2) DEFAULT 0,
                locale TEXT DEFAULT 'en_US',
                time_zone TEXT DEFAULT 'UTC',
                page_size TEXT DEFAULT 'A4',
                invoice_folder TEXT DEFAULT 'invoices',
                CHECK (id = 1)
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                currency_symbol TEXT,
                date_format TEXT DEFAULT 'MM/DD/YYYY',
                language TEXT DEFAULT 'English',
                tax_rate DECIMAL(5,2),
                show_tax BOOLEAN DEFAULT 1,
                auto_print BOOLEAN DEFAULT 0,
                invoice_copies INTEGER DEFAULT 1,
                enable_sound BOOLEAN DEFAULT 1,
                auto_clear_order BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Installments table for tracking payment installments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS installments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                amount DECIMAL(10,2) NOT NULL,
                due_date TIMESTAMP NOT NULL,
                paid_date TIMESTAMP,
                status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'overdue')),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        
        # Subscription table for tracking system subscription
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP NOT NULL,
                features_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add invoice_folder column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(settings)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'invoice_folder' not in columns:
            cursor.execute("ALTER TABLE settings ADD COLUMN invoice_folder TEXT DEFAULT 'invoices'")
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installments_due_date ON installments(due_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installments_status ON installments(status)")
        
        # Insert default settings if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO settings (id, currency_symbol, default_tax_rate, locale, time_zone)
            VALUES (1, '₹', 0, 'en_US', 'UTC')
        """)
        
        # Create default admin user if no users exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        if cursor.fetchone()['count'] == 0:
            # Use bcrypt directly here to avoid circular import
            import bcrypt
            admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, active)
                VALUES (?, ?, 'admin', 1)
            """, ("admin", admin_hash))
            logger.info("Created default admin user (username: admin, password: admin123)")
        
        # Create default invoice template if none exists
        cursor.execute("SELECT COUNT(*) as count FROM invoice_templates")
        if cursor.fetchone()['count'] == 0:
            default_template = {
                'header': {
                    'show_logo': True,
                    'show_business_info': True,
                    'title': 'INVOICE'
                },
                'footer': {
                    'text': 'Thank you for your business!',
                    'show_date': True
                },
                'styles': {
                    'font_family': 'Helvetica',
                    'font_size': 10,
                    'header_font_size': 14,
                    'margin_top': 20,
                    'margin_bottom': 20,
                    'margin_left': 20,
                    'margin_right': 20
                },
                'business_info': {
                    'name': 'Your Business Name',
                    'address': '123 Main Street\nCity, State 12345',
                    'phone': '(555) 123-4567',
                    'email': 'info@business.com',
                    'tax_id': 'TAX123456'
                }
            }
            
            cursor.execute("""
                INSERT INTO invoice_templates (name, is_default, header_json, footer_json, styles_json, business_info_json)
                VALUES (?, 1, ?, ?, ?, ?)
            """, (
                "Default Template",
                json.dumps(default_template['header']),
                json.dumps(default_template['footer']),
                json.dumps(default_template['styles']),
                json.dumps(default_template['business_info'])
            ))
            logger.info("Created default invoice template")
        
        conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()

# Global database instance
db = Database()
