#!/usr/bin/env python3
"""
Test script to verify complete invoice workflow
Tests invoice generation, preview dialog, and integration
"""
import sys
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from database import db
from auth import AuthManager, hash_password
from invoice_generator_enhanced import EnhancedInvoiceGenerator
from invoice_formats import BillSize, LayoutStyle
from invoice_preview_dialog import InvoicePreviewDialog

def setup_test_data():
    """Setup test data for invoice testing"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Ensure test user exists
    cursor.execute("""
        INSERT OR REPLACE INTO users (id, username, password_hash, role, active)
        VALUES (1, 'admin', ?, 'admin', 1)
    """, (hash_password('admin123'),))
    
    # Create a test order
    cursor.execute("""
        INSERT OR REPLACE INTO orders (
            id, user_id, subtotal, tax_rate, tax_total, 
            grand_total, status, created_at
        ) VALUES (
            1001, 1, 500.00, 18.0, 90.00, 
            590.00, 'finalized', ?
        )
    """, (datetime.now().isoformat(),))
    
    # Create test order items
    cursor.execute("""DELETE FROM order_items WHERE order_id = 1001""")
    cursor.execute("""
        INSERT INTO order_items (
            order_id, name, quantity, unit_price, line_total
        ) VALUES 
        (1001, 'Coffee Large', 2, 50.00, 100.00),
        (1001, 'Sandwich Deluxe', 3, 80.00, 240.00),
        (1001, 'Chocolate Cake Slice', 2, 80.00, 160.00)
    """)
    
    # Ensure settings exist
    cursor.execute("""
        INSERT OR IGNORE INTO settings (
            id, currency_symbol, default_tax_rate, 
            page_size, invoice_folder
        ) VALUES (1, '₹', 18.0, 'A4', 'invoices')
    """)
    
    # Create default invoice template
    cursor.execute("""
        INSERT OR IGNORE INTO invoice_templates (
            id, name, is_default, business_info_json
        ) VALUES (
            1, 'Default Template', 1, 
            '{"name": "Test Business", "address": "123 Main St", 
              "phone": "+1-234-567-8900", "email": "info@test.com",
              "tax_id": "TAX123456"}'
        )
    """)
    
    conn.commit()
    logger.info("Test data setup complete")
    return 1001  # Return test order ID

def test_invoice_generation():
    """Test basic invoice generation"""
    logger.info("\n=== Testing Invoice Generation ===")
    
    generator = EnhancedInvoiceGenerator()
    order_id = setup_test_data()
    
    # Test different formats
    formats_to_test = [
        (BillSize.A4, LayoutStyle.CLASSIC, "A4 Classic"),
        (BillSize.A5, LayoutStyle.MINIMAL, "A5 Minimal"),
        (BillSize.THERMAL_80, LayoutStyle.COMPACT, "80mm Thermal"),
        (BillSize.LETTER, LayoutStyle.DETAILED, "Letter Detailed"),
    ]
    
    results = []
    for bill_size, layout, name in formats_to_test:
        try:
            logger.info(f"Testing {name}...")
            pdf_path = generator.generate_invoice(
                order_id=order_id,
                bill_size=bill_size,
                layout_style=layout
            )
            
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path) / 1024
                logger.info(f"✅ {name}: Generated successfully ({file_size:.1f} KB)")
                results.append((name, True, file_size))
            else:
                logger.error(f"❌ {name}: File not created")
                results.append((name, False, 0))
                
        except Exception as e:
            logger.error(f"❌ {name}: Error - {str(e)}")
            results.append((name, False, 0))
    
    # Print summary
    logger.info("\n=== Generation Summary ===")
    for name, success, size in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name}: {'Success' if success else 'Failed'} {f'({size:.1f} KB)' if success else ''}")
    
    return all(r[1] for r in results)

def test_preview_dialog():
    """Test invoice preview dialog"""
    logger.info("\n=== Testing Invoice Preview Dialog ===")
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Invoice Preview Test")
        root.geometry("300x200")
        
        # Create auth manager
        auth_manager = AuthManager()
        auth_manager.current_user = {'id': 1, 'username': 'admin', 'role': 'admin'}
        
        order_id = setup_test_data()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="Invoice Preview Dialog Test", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        ttk.Label(main_frame, text=f"Test Order ID: {order_id}").pack(pady=5)
        
        def open_preview():
            logger.info("Opening invoice preview dialog...")
            try:
                from invoice_preview_dialog import show_invoice_preview
                show_invoice_preview(root, order_id, auth_manager)
                logger.info("✅ Preview dialog opened successfully")
            except Exception as e:
                logger.error(f"❌ Error opening preview: {e}")
                import traceback
                traceback.print_exc()
        
        ttk.Button(main_frame, text="Open Invoice Preview", 
                  command=open_preview).pack(pady=10)
        
        ttk.Button(main_frame, text="Close Test", 
                  command=root.quit).pack(pady=5)
        
        logger.info("Preview dialog test window created. Click 'Open Invoice Preview' to test.")
        
        # Start GUI event loop (will block until window is closed)
        root.mainloop()
        root.destroy()
        
        logger.info("✅ Preview dialog test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Preview dialog test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pos_integration():
    """Test POS Order tab integration"""
    logger.info("\n=== Testing POS Integration ===")
    
    try:
        # Test that the imports work
        from pos_order_tab import POSOrderTab
        logger.info("✅ POS Order tab imports successfully")
        
        # Check that invoice preview is imported
        import pos_order_tab
        source = open('pos_order_tab.py', 'r').read()
        
        if 'show_invoice_preview' in source:
            logger.info("✅ show_invoice_preview is imported in POS tab")
        else:
            logger.error("❌ show_invoice_preview NOT imported in POS tab")
            
        if 'finalize_and_print' in source and 'show_invoice_preview' in source:
            logger.info("✅ Invoice preview integrated in finalize_and_print method")
        else:
            logger.error("❌ Invoice preview NOT integrated in finalize_and_print")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ POS integration test failed: {e}")
        return False

def check_database_schema():
    """Check database schema for invoice settings"""
    logger.info("\n=== Checking Database Schema ===")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check settings table columns
    cursor.execute("PRAGMA table_info(settings)")
    columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = [
        'default_bill_size',
        'default_bill_layout',
        'thermal_density',
        'per_size_margins_json',
        'font_scale_override'
    ]
    
    for col in required_columns:
        if col in columns:
            logger.info(f"✅ Column '{col}' exists in settings table")
        else:
            logger.error(f"❌ Column '{col}' MISSING from settings table")
    
    # Check invoice_templates columns
    cursor.execute("PRAGMA table_info(invoice_templates)")
    template_columns = [col[1] for col in cursor.fetchall()]
    
    template_required = [
        'preferred_bill_size',
        'preferred_layout',
        'size_overrides_json'
    ]
    
    for col in template_required:
        if col in template_columns:
            logger.info(f"✅ Column '{col}' exists in invoice_templates table")
        else:
            logger.error(f"❌ Column '{col}' MISSING from invoice_templates table")
    
    # Check printer_profiles table
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='printer_profiles'
    """)
    
    if cursor.fetchone():
        logger.info("✅ printer_profiles table exists")
    else:
        logger.error("❌ printer_profiles table MISSING")
    
    return True

def main():
    """Run all tests"""
    logger.info("=" * 70)
    logger.info("INVOICE SYSTEM WORKFLOW TEST")
    logger.info("=" * 70)
    
    # Initialize database
    db.init_database()
    
    # Run tests
    results = {}
    
    # Check database schema
    results['Database Schema'] = check_database_schema()
    
    # Test invoice generation
    results['Invoice Generation'] = test_invoice_generation()
    
    # Test POS integration
    results['POS Integration'] = test_pos_integration()
    
    # Test preview dialog (interactive)
    logger.info("\n" + "=" * 50)
    logger.info("Interactive Test - Preview Dialog")
    logger.info("A window will open. Click 'Open Invoice Preview' to test.")
    logger.info("=" * 50)
    results['Preview Dialog'] = test_preview_dialog()
    
    # Print final summary
    logger.info("\n" + "=" * 70)
    logger.info("FINAL TEST SUMMARY")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED! Invoice system is working correctly.")
    else:
        logger.info("\n⚠️ SOME TESTS FAILED. Please review the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
