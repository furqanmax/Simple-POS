#!/usr/bin/env python3
"""
Main POS System Application
Point of Sale system with role-based access control
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import sys
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pos_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import application modules
from database import db
from auth import auth_manager
from login_window import LoginWindow
from pos_order_tab import POSOrderTab
from dashboard import DashboardTab
from admin_tabs import (
    FrequentOrdersTab,
    OrderHistoryTab,
    UserManagementTab,
    InvoiceTemplateTab,
    SettingsTab,
    UserPreferencesTab
)

class POSApplication:
    def __init__(self):
        self.current_user = None
        self.root = None
        self.tabs = {}
        
    def start(self):
        """Start the application with login"""
        logger.info("Starting POS System...")
        
        # Show login window
        login = LoginWindow(auth_manager, self.on_login_success)
        login.show()
    
    def on_login_success(self, user):
        """Handle successful login"""
        self.current_user = user
        logger.info(f"User {user['username']} ({user['role']}) logged in")
        self.create_main_window()
    
    def create_main_window(self):
        """Create the main application window"""
        self.root = tk.Tk()
        self.root.title(f"POS System - {self.current_user['username']} ({self.current_user['role'].title()})")
        
        # Set window size and position
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self._create_status_bar()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs based on user role
        self._create_tabs()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the main loop
        self.root.mainloop()
    
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        if auth_manager.is_admin():
            file_menu.add_command(label="Export Database", command=self.export_database)
            file_menu.add_command(label="Import Database", command=self.import_database)
            file_menu.add_separator()
        
        file_menu.add_command(label="Logout", command=self.logout)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_current_tab)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="User Guide", command=self.show_help)
    
    def _create_status_bar(self):
        """Create status bar at bottom of window"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # User info
        user_label = ttk.Label(
            self.status_bar,
            text=f"User: {self.current_user['username']} | Role: {self.current_user['role'].title()}"
        )
        user_label.pack(side=tk.LEFT, padx=10)
        
        # Current time
        self.time_label = ttk.Label(self.status_bar, text="")
        self.time_label.pack(side=tk.RIGHT, padx=10)
        self.update_time()
    
    def update_time(self):
        """Update time in status bar"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def _create_tabs(self):
        """Create tabs based on user role"""
        # Dashboard tab - available to all users (primary tab)
        dashboard_tab = DashboardTab(self.notebook, auth_manager)
        self.notebook.add(dashboard_tab.get_frame(), text="📊 Dashboard")
        self.tabs['dashboard'] = dashboard_tab
        
        # POS Order tab - available to all users
        pos_tab = POSOrderTab(self.notebook, auth_manager)
        self.notebook.add(pos_tab.get_frame(), text="📝 POS Order")
        self.tabs['pos'] = pos_tab
        
        # Frequent Orders tab - available to all users
        freq_tab = FrequentOrdersTab(self.notebook, auth_manager)
        self.notebook.add(freq_tab.get_frame(), text="⭐ Frequent Orders")
        self.tabs['frequent'] = freq_tab
        
        # User Preferences tab - available to all users
#         preferences_tab = UserPreferencesTab(self.notebook, auth_manager)
#         self.notebook.add(preferences_tab.get_frame(), text="🔧 My Preferences")
#         self.tabs['preferences'] = preferences_tab
        
        # Admin-only tabs
        if auth_manager.is_admin():
            # Order History
            history_tab = OrderHistoryTab(self.notebook, auth_manager)
            self.notebook.add(history_tab.get_frame(), text="📋 Order History")
            self.tabs['history'] = history_tab
            
            # User Management
            users_tab = UserManagementTab(self.notebook, auth_manager)
            self.notebook.add(users_tab.get_frame(), text="👥 Users")
            self.tabs['users'] = users_tab
            
            # Invoice Templates
            template_tab = InvoiceTemplateTab(self.notebook, auth_manager)
            self.notebook.add(template_tab.get_frame(), text="📄 Invoice Templates")
            self.tabs['templates'] = template_tab
            
            # Settings (System-wide, Admin only)
            settings_tab = SettingsTab(self.notebook, auth_manager)
            self.notebook.add(settings_tab.get_frame(), text="⚙️ System Settings")
            self.tabs['settings'] = settings_tab
    
    def refresh_current_tab(self):
        """Refresh the current active tab"""
        current_tab_index = self.notebook.index(self.notebook.select())
        current_tab_name = list(self.tabs.keys())[current_tab_index]
        
        if hasattr(self.tabs[current_tab_name], 'refresh'):
            self.tabs[current_tab_name].refresh()
            logger.info(f"Refreshed {current_tab_name} tab")
    
    def logout(self):
        """Logout current user"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            auth_manager.logout()
            self.root.destroy()
            self.start()  # Restart with login
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            logger.info("Application closing...")
            db.close()
            self.root.destroy()
            sys.exit(0)
    
    def export_database(self):
        """Export database for backup"""
        from tkinter import filedialog
        import shutil
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
            )
            
            if filename:
                db.close()  # Close connection before copying
                shutil.copy2("pos_system.db", filename)
                db.get_connection()  # Reopen connection
                messagebox.showinfo("Success", f"Database exported to {filename}")
                logger.info(f"Database exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting database: {e}")
            messagebox.showerror("Error", f"Failed to export database: {str(e)}")
    
    def import_database(self):
        """Import database from backup"""
        from tkinter import filedialog
        import shutil
        
        if not messagebox.askyesno("Warning", 
                                  "This will replace the current database. Continue?"):
            return
        
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
            )
            
            if filename:
                db.close()  # Close connection before replacing
                shutil.copy2(filename, "pos_system.db")
                db.get_connection()  # Reopen connection
                messagebox.showinfo("Success", 
                                  "Database imported successfully. Please restart the application.")
                logger.info(f"Database imported from {filename}")
                self.on_closing()
        except Exception as e:
            logger.error(f"Error importing database: {e}")
            messagebox.showerror("Error", f"Failed to import database: {str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """POS System v1.0

A comprehensive Point of Sale system with:
• Role-based access control
• Order management  
• Invoice generation with QR codes
• Inventory templates
• User management
• Customizable invoice templates

© 2024 POS System
"""
        messagebox.showinfo("About POS System", about_text)
    
    def show_help(self):
        """Show help/user guide"""
        help_text = """POS System User Guide

FOR ALL USERS:
• POS Order: Create new orders, add items, apply templates, print invoices
• Frequent Orders: Create and manage order templates

FOR ADMINISTRATORS:
• Order History: View and manage all orders
• Users: Create and manage user accounts
• Invoice Templates: Design custom invoice layouts
• Settings: Configure system settings

DEFAULT LOGIN:
Username: admin
Password: admin123

KEYBOARD SHORTCUTS:
• Enter: Move to next field
• F5: Refresh current tab
• Ctrl+Q: Logout
"""
        messagebox.showinfo("User Guide", help_text)


if __name__ == "__main__":
    try:
        app = POSApplication()
        app.start()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        messagebox.showerror("Critical Error", 
                           f"Application failed to start:\n{str(e)}")
        sys.exit(1)
