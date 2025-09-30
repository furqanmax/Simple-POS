#!/usr/bin/env python3
"""
Script to update existing database to use Indian Rupees as the default currency
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def update_database_currency():
    """Update the database to set Indian Rupees as default currency"""
    
    try:
        # Connect to the database
        conn = sqlite3.connect('pos_system.db')
        cursor = conn.cursor()
        
        logger.info("Connected to database successfully")
        
        # Update the settings table to set Indian Rupee as default currency
        cursor.execute("""
            UPDATE settings 
            SET currency_symbol = '₹' 
            WHERE id = 1
        """)
        
        rows_updated = cursor.rowcount
        logger.info(f"Updated {rows_updated} row(s) in settings table")
        
        # Check if any user preferences exist with old currency
        cursor.execute("""
            SELECT COUNT(*) FROM user_preferences 
            WHERE currency_symbol = '$'
        """)
        
        dollar_users = cursor.fetchone()[0]
        
        if dollar_users > 0:
            # Automatically update user preferences from $ to ₹
            logger.info(f"Found {dollar_users} user(s) with $ currency preference")
            logger.info("Updating all user preferences to use ₹...")
            
            cursor.execute("""
                UPDATE user_preferences 
                SET currency_symbol = '₹' 
                WHERE currency_symbol = '$'
            """)
            logger.info(f"Updated {cursor.rowcount} user preference(s)")
        
        # Commit the changes
        conn.commit()
        logger.info("Database updated successfully!")
        
        # Display current settings
        cursor.execute("SELECT currency_symbol, default_tax_rate FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        
        if settings:
            logger.info(f"Current settings:")
            logger.info(f"  Currency Symbol: {settings[0]}")
            logger.info(f"  Default Tax Rate: {settings[1]}%")
        
        conn.close()
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("POS System Currency Update Script")
    print("This will update the default currency to Indian Rupees (₹)")
    print("=" * 60)
    
    # Auto-run without user interaction
    print("\nProceeding with currency update...")
    update_database_currency()
