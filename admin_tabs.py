"""
Admin tabs for POS System
Contains tabs for frequent orders, order history, user management, invoice templates, and settings
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys
from PIL import Image, ImageTk
import qrcode
import io

from database import db
from models import FrequentOrderModel, OrderHistoryModel
from invoice_generator import InvoiceGenerator

logger = logging.getLogger(__name__)


class FrequentOrdersTab:
    """Tab for managing frequent order templates"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the frequent orders tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=2)
        main_container.rowconfigure(0, weight=1)
        
        # Left panel - Template list
        left_panel = ttk.LabelFrame(main_container, text="Templates", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.rowconfigure(1, weight=1)
        
        # Filter buttons
        filter_frame = ttk.Frame(left_panel)
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.show_all_var = tk.BooleanVar(value=True)
        self.show_personal_var = tk.BooleanVar(value=True)
        self.show_global_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(filter_frame, text="Personal", variable=self.show_personal_var,
                       command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_frame, text="Global", variable=self.show_global_var,
                       command=self.refresh).pack(side=tk.LEFT, padx=5)
        
        # Template listbox
        self.template_listbox = tk.Listbox(left_panel, height=15, width=30)
        self.template_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.template_listbox.bind('<<ListboxSelect>>', self.on_template_select)
        
        scrollbar = ttk.Scrollbar(left_panel, orient=tk.VERTICAL, command=self.template_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.template_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Template actions
        action_frame = ttk.Frame(left_panel)
        action_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(action_frame, text="New", command=self.new_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Edit", command=self.edit_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Delete", command=self.delete_template).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Template details
        right_panel = ttk.LabelFrame(main_container, text="Template Details", padding="10")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_panel.columnconfigure(1, weight=1)
        
        # Template name
        ttk.Label(right_panel, text="Label:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.label_var = tk.StringVar()
        self.label_entry = ttk.Entry(right_panel, textvariable=self.label_var, width=30)
        self.label_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Is global checkbox (admin only)
        if self.auth_manager.is_admin():
            self.is_global_var = tk.BooleanVar()
            ttk.Checkbutton(right_panel, text="Global Template", 
                          variable=self.is_global_var).grid(row=1, column=0, columnspan=2, pady=5)
        
        # Items frame
        items_frame = ttk.LabelFrame(right_panel, text="Items", padding="5")
        items_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        items_frame.columnconfigure(0, weight=1)
        items_frame.rowconfigure(1, weight=1)
        
        # Add item controls
        add_item_frame = ttk.Frame(items_frame)
        add_item_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(add_item_frame, text="Item:").pack(side=tk.LEFT, padx=5)
        self.item_name_var = tk.StringVar()
        ttk.Entry(add_item_frame, textvariable=self.item_name_var, width=20).pack(side=tk.LEFT)
        
        ttk.Label(add_item_frame, text="Qty:").pack(side=tk.LEFT, padx=5)
        self.item_qty_var = tk.StringVar(value="1")
        ttk.Entry(add_item_frame, textvariable=self.item_qty_var, width=8).pack(side=tk.LEFT)
        
        ttk.Label(add_item_frame, text="Price:").pack(side=tk.LEFT, padx=5)
        self.item_price_var = tk.StringVar(value="0.00")
        ttk.Entry(add_item_frame, textvariable=self.item_price_var, width=10).pack(side=tk.LEFT)
        
        ttk.Button(add_item_frame, text="Add", command=self.add_item).pack(side=tk.LEFT, padx=5)
        
        # Items tree
        columns = ('Item', 'Qty', 'Price')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            if col == 'Item':
                self.items_tree.column(col, width=200)
            else:
                self.items_tree.column(col, width=80)
        
        self.items_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        items_scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        items_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.items_tree.configure(yscrollcommand=items_scrollbar.set)
        
        # Item actions
        item_action_frame = ttk.Frame(items_frame)
        item_action_frame.grid(row=2, column=0, pady=5)
        
        ttk.Button(item_action_frame, text="Remove Item", command=self.remove_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(item_action_frame, text="Clear All", command=self.clear_items).pack(side=tk.LEFT, padx=2)
        
        # Save button
        ttk.Button(right_panel, text="Save Template", command=self.save_template).grid(
            row=3, column=0, columnspan=2, pady=20)
        
        self.template_map = {}
    
    def refresh(self):
        """Refresh the template list"""
        self.template_listbox.delete(0, tk.END)
        self.template_map = {}
        
        try:
            user_id = self.auth_manager.get_current_user()['id']
            
            # Get templates based on filters
            if self.show_personal_var.get() and self.show_global_var.get():
                templates = FrequentOrderModel.get_all(user_id, include_global=True)
            elif self.show_personal_var.get():
                templates = FrequentOrderModel.get_all(user_id, include_global=False)
            elif self.show_global_var.get():
                templates = FrequentOrderModel.get_all(None, include_global=True)
            else:
                templates = []
            
            for template in templates:
                label = template['label']
                if template['is_global']:
                    label += " [Global]"
                self.template_listbox.insert(tk.END, label)
                self.template_map[label] = template
                
        except Exception as e:
            logger.error(f"Error refreshing templates: {e}")
    
    def on_template_select(self, event):
        """Handle template selection"""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        
        label = self.template_listbox.get(selection[0])
        template = self.template_map.get(label)
        
        if template:
            self.display_template(template)
    
    def display_template(self, template):
        """Display template details"""
        self.label_var.set(template['label'])
        
        if hasattr(self, 'is_global_var'):
            self.is_global_var.set(template['is_global'])
        
        # Clear and populate items tree
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        for item in template['items']:
            self.items_tree.insert('', 'end', values=(
                item['name'],
                f"{item['quantity']:.2f}",
                f"₹{item['unit_price']:.2f}"
            ))
    
    def new_template(self):
        """Create new template"""
        self.label_var.set("")
        if hasattr(self, 'is_global_var'):
            self.is_global_var.set(False)
        self.clear_items()
        self.label_entry.focus()
    
    def edit_template(self):
        """Edit selected template"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to edit")
            return
        
        # Template is already displayed, just focus on label entry
        self.label_entry.focus()
    
    def delete_template(self):
        """Delete selected template"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to delete")
            return
        
        label = self.template_listbox.get(selection[0])
        template = self.template_map.get(label)
        
        if template and messagebox.askyesno("Confirm", f"Delete template '{template['label']}'?"):
            try:
                FrequentOrderModel.delete(template['id'])
                self.refresh()
                messagebox.showinfo("Success", "Template deleted")
            except Exception as e:
                logger.error(f"Error deleting template: {e}")
                messagebox.showerror("Error", "Failed to delete template")
    
    def add_item(self):
        """Add item to template"""
        name = self.item_name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter item name")
            return
        
        try:
            qty = float(self.item_qty_var.get())
            price = float(self.item_price_var.get())
            
            self.items_tree.insert('', 'end', values=(
                name,
                f"{qty:.2f}",
                f"₹{price:.2f}"
            ))
            
            # Clear inputs
            self.item_name_var.set("")
            self.item_qty_var.set("1")
            self.item_price_var.set("0.00")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")
    
    def remove_item(self):
        """Remove selected item"""
        selection = self.items_tree.selection()
        if selection:
            self.items_tree.delete(selection[0])
    
    def clear_items(self):
        """Clear all items"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
    
    def save_template(self):
        """Save the template"""
        label = self.label_var.get().strip()
        if not label:
            messagebox.showwarning("Warning", "Please enter a template label")
            return
        
        # Collect items
        items = []
        for item_id in self.items_tree.get_children():
            item = self.items_tree.item(item_id)
            values = item['values']
            items.append({
                'name': values[0],
                'quantity': float(values[1]),
                'unit_price': float(values[2].replace('₹', '').replace('$', ''))
            })
        
        if not items:
            messagebox.showwarning("Warning", "Template must have at least one item")
            return
        
        try:
            user_id = self.auth_manager.get_current_user()['id']
            owner_id = None if (hasattr(self, 'is_global_var') and 
                              self.is_global_var.get() and 
                              self.auth_manager.is_admin()) else user_id
            
            # Check if updating existing
            selection = self.template_listbox.curselection()
            if selection:
                template_label = self.template_listbox.get(selection[0])
                template = self.template_map.get(template_label)
                if template:
                    FrequentOrderModel.update(template['id'], label, items)
                    messagebox.showinfo("Success", "Template updated")
                else:
                    FrequentOrderModel.create(label, items, owner_id)
                    messagebox.showinfo("Success", "Template created")
            else:
                FrequentOrderModel.create(label, items, owner_id)
                messagebox.showinfo("Success", "Template created")
            
            self.refresh()
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            messagebox.showerror("Error", "Failed to save template")
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame


class OrderHistoryTab:
    """Tab for viewing order history (Admin only)"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.invoice_generator = InvoiceGenerator()
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the order history tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Filter panel
        filter_frame = ttk.LabelFrame(main_container, text="Filters", padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Date range
        ttk.Label(filter_frame, text="From:").grid(row=0, column=0, padx=5)
        self.from_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        ttk.Entry(filter_frame, textvariable=self.from_date_var, width=12).grid(row=0, column=1)
        
        ttk.Label(filter_frame, text="To:").grid(row=0, column=2, padx=5)
        self.to_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ttk.Entry(filter_frame, textvariable=self.to_date_var, width=12).grid(row=0, column=3)
        
        # Status filter
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=4, padx=5)
        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, 
                                   values=["All", "finalized", "canceled"], 
                                   state="readonly", width=10)
        status_combo.grid(row=0, column=5)
        
        # Search button
        ttk.Button(filter_frame, text="Search", command=self.refresh).grid(row=0, column=6, padx=10)
        
        # Orders tree
        columns = ('ID', 'Date', 'User', 'Items', 'Total', 'Status')
        self.orders_tree = ttk.Treeview(main_container, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            if col == 'Date':
                self.orders_tree.column(col, width=150)
            elif col == 'User':
                self.orders_tree.column(col, width=100)
            elif col == 'Items':
                self.orders_tree.column(col, width=50)
            else:
                self.orders_tree.column(col, width=100)
        
        self.orders_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=self.orders_tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.orders_tree.configure(yscrollcommand=scrollbar.set)
        
        # Actions panel
        actions_frame = ttk.Frame(main_container)
        actions_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(actions_frame, text="View Details", command=self.view_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Print Invoice", command=self.print_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Cancel Order", command=self.cancel_order).pack(side=tk.LEFT, padx=5)
    
    def refresh(self):
        """Refresh order history"""
        # Clear tree
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        try:
            # Get filter values
            from_date = self.from_date_var.get()
            to_date = self.to_date_var.get() + " 23:59:59"  # Include full day
            status = None if self.status_var.get() == "All" else self.status_var.get()
            
            # Get orders
            orders = OrderHistoryModel.get_orders(
                start_date=from_date,
                end_date=to_date,
                status=status
            )
            
            # Get item counts for each order
            conn = db.get_connection()
            cursor = conn.cursor()
            
            for order in orders:
                cursor.execute("SELECT COUNT(*) as count FROM order_items WHERE order_id = ?", 
                             (order['id'],))
                item_count = cursor.fetchone()['count']
                
                self.orders_tree.insert('', 'end', values=(
                    f"#{order['id']:06d}",
                    datetime.fromisoformat(order['created_at']).strftime('%Y-%m-%d %H:%M'),
                    order['username'],
                    item_count,
                    f"₹{order['grand_total']:.2f}",
                    order['status'].upper()
                ))
                
        except Exception as e:
            logger.error(f"Error refreshing order history: {e}")
            messagebox.showerror("Error", "Failed to load order history")
    
    def view_details(self):
        """View order details"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an order")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = int(item['values'][0].replace('#', ''))
        
        # Get order details
        details = OrderHistoryModel.get_order_details(order_id)
        if not details:
            return
        
        # Create details window
        detail_window = tk.Toplevel(self.frame)
        detail_window.title(f"Order Details - #{order_id:06d}")
        detail_window.geometry("600x500")
        
        # Order info
        info_frame = ttk.LabelFrame(detail_window, text="Order Information", padding="10")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        order = details['order']
        ttk.Label(info_frame, text=f"Order ID: #{order['id']:06d}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Date: {order['created_at']}").pack(anchor='w')
        ttk.Label(info_frame, text=f"User: {order['username']}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Status: {order['status'].upper()}").pack(anchor='w')
        
        # Items
        items_frame = ttk.LabelFrame(detail_window, text="Items", padding="10")
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('Item', 'Qty', 'Price', 'Total')
        items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            items_tree.heading(col, text=col)
            if col == 'Item':
                items_tree.column(col, width=250)
            else:
                items_tree.column(col, width=80)
        
        for item in details['items']:
            items_tree.insert('', 'end', values=(
                item['name'],
                f"{item['quantity']:.2f}",
                f"₹{item['unit_price']:.2f}",
                f"₹{item['line_total']:.2f}"
            ))
        
        items_tree.pack(fill='both', expand=True)
        
        # Totals
        totals_frame = ttk.Frame(detail_window)
        totals_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(totals_frame, text=f"Subtotal: ₹{order['subtotal']:.2f}").pack(anchor='e')
        ttk.Label(totals_frame, text=f"Tax ({order['tax_rate']}%): ₹{order['tax_total']:.2f}").pack(anchor='e')
        ttk.Label(totals_frame, text=f"Grand Total: ₹{order['grand_total']:.2f}", 
                 font=('Helvetica', 10, 'bold')).pack(anchor='e')
    
    def print_invoice(self):
        """Print invoice for selected order"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an order")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = int(item['values'][0].replace('#', ''))
        
        try:
            # Generate invoice from snapshot
            pdf_path = self.invoice_generator.generate_invoice(order_id, use_snapshot=True)
            
            # Open PDF
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                os.startfile(pdf_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', pdf_path])
            else:  # Linux
                subprocess.run(['xdg-open', pdf_path])
            
            messagebox.showinfo("Success", f"Invoice generated: {pdf_path}")
            
        except Exception as e:
            logger.error(f"Error generating invoice: {e}")
            messagebox.showerror("Error", "Failed to generate invoice")
    
    def cancel_order(self):
        """Cancel selected order"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an order")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = int(item['values'][0].replace('#', ''))
        status = item['values'][5]
        
        if status == 'CANCELED':
            messagebox.showinfo("Info", "Order is already canceled")
            return
        
        if messagebox.askyesno("Confirm", f"Cancel order #{order_id:06d}?"):
            if OrderHistoryModel.cancel_order(order_id):
                messagebox.showinfo("Success", "Order canceled")
                self.refresh()
            else:
                messagebox.showerror("Error", "Failed to cancel order")
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame


class UserManagementTab:
    """Tab for managing users (Admin only)"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the user management tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=2)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Users list
        list_frame = ttk.LabelFrame(main_container, text="Users", padding="10")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        # Users tree
        columns = ('ID', 'Username', 'Role', 'Active', 'Created')
        self.users_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            if col == 'Created':
                self.users_tree.column(col, width=150)
            else:
                self.users_tree.column(col, width=80)
        
        self.users_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        # User form
        form_frame = ttk.LabelFrame(main_container, text="User Details", padding="10")
        form_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N))
        
        # Username
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(form_frame, textvariable=self.username_var, width=20)
        self.username_entry.grid(row=0, column=1, pady=5)
        
        # Password
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(form_frame, textvariable=self.password_var, width=20, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)
        
        # Role
        ttk.Label(form_frame, text="Role:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.role_var = tk.StringVar(value="user")
        role_combo = ttk.Combobox(form_frame, textvariable=self.role_var,
                                 values=["admin", "user"], state="readonly", width=18)
        role_combo.grid(row=2, column=1, pady=5)
        
        # Active status
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form_frame, text="Active", variable=self.active_var).grid(
            row=3, column=0, columnspan=2, pady=10)
        
        # Actions
        action_frame = ttk.Frame(form_frame)
        action_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(action_frame, text="Create User", command=self.create_user).pack(pady=2)
        ttk.Button(action_frame, text="Update User", command=self.update_user).pack(pady=2)
        ttk.Button(action_frame, text="Reset Password", command=self.reset_password).pack(pady=2)
        ttk.Button(action_frame, text="Toggle Active", command=self.toggle_active).pack(pady=2)
    
    def refresh(self):
        """Refresh users list"""
        # Clear tree
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            users = self.auth_manager.get_all_users()
            
            for user in users:
                self.users_tree.insert('', 'end', values=(
                    user['id'],
                    user['username'],
                    user['role'].upper(),
                    "Yes" if user['active'] else "No",
                    datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d %H:%M')
                ))
                
        except Exception as e:
            logger.error(f"Error refreshing users: {e}")
            messagebox.showerror("Error", "Failed to load users")
    
    def create_user(self):
        """Create new user"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        role = self.role_var.get()
        
        if not username or not password:
            messagebox.showwarning("Warning", "Username and password are required")
            return
        
        if len(password) < 6:
            messagebox.showwarning("Warning", "Password must be at least 6 characters")
            return
        
        try:
            if self.auth_manager.create_user(username, password, role):
                messagebox.showinfo("Success", f"User '{username}' created successfully")
                self.username_var.set("")
                self.password_var.set("")
                self.role_var.set("user")
                self.refresh()
            else:
                messagebox.showerror("Error", "Failed to create user. Username may already exist.")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            messagebox.showerror("Error", f"Failed to create user: {str(e)}")
    
    def update_user(self):
        """Update selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user to update")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        
        # For now, just update active status
        # Role updates could be added here
        messagebox.showinfo("Info", "Use 'Toggle Active' to change user status")
    
    def reset_password(self):
        """Reset password for selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user")
            return
        
        new_password = self.password_var.get()
        if not new_password or len(new_password) < 6:
            messagebox.showwarning("Warning", "Enter a new password (min 6 characters)")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        if messagebox.askyesno("Confirm", f"Reset password for user '{username}'?"):
            try:
                self.auth_manager.change_password(user_id, new_password)
                messagebox.showinfo("Success", "Password reset successfully")
                self.password_var.set("")
            except Exception as e:
                logger.error(f"Error resetting password: {e}")
                messagebox.showerror("Error", "Failed to reset password")
    
    def toggle_active(self):
        """Toggle active status of selected user"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        current_active = item['values'][3] == "Yes"
        
        new_status = "deactivate" if current_active else "activate"
        
        if messagebox.askyesno("Confirm", f"{new_status.title()} user '{username}'?"):
            try:
                self.auth_manager.update_user_status(user_id, not current_active)
                messagebox.showinfo("Success", f"User {new_status}d successfully")
                self.refresh()
            except Exception as e:
                logger.error(f"Error updating user status: {e}")
                messagebox.showerror("Error", "Failed to update user status")
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame


class InvoiceTemplateTab:
    """Tab for managing invoice templates (Admin only)"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.frame = ttk.Frame(parent)
        self.current_template_id = None
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create the invoice template tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.pack(fill='both', expand=True)
        
        # Template selection
        select_frame = ttk.LabelFrame(main_container, text="Template Selection", padding="10")
        select_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(select_frame, text="Template:").pack(side=tk.LEFT, padx=5)
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(select_frame, textvariable=self.template_var,
                                          state="readonly", width=30)
        self.template_combo.pack(side=tk.LEFT, padx=5)
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_select)
        
        ttk.Button(select_frame, text="New", command=self.new_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(select_frame, text="Save", command=self.save_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(select_frame, text="Delete", command=self.delete_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(select_frame, text="Set Default", command=self.set_default).pack(side=tk.LEFT, padx=2)
        
        # Business info
        business_frame = ttk.LabelFrame(main_container, text="Business Information", padding="10")
        business_frame.pack(fill='x', pady=10)
        
        # Business name
        ttk.Label(business_frame, text="Business Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.business_name_var = tk.StringVar()
        ttk.Entry(business_frame, textvariable=self.business_name_var, width=40).grid(
            row=0, column=1, pady=2)
        
        # Address
        ttk.Label(business_frame, text="Address:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.address_text = tk.Text(business_frame, height=3, width=40)
        self.address_text.grid(row=1, column=1, pady=2)
        
        # Phone
        ttk.Label(business_frame, text="Phone:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.phone_var = tk.StringVar()
        ttk.Entry(business_frame, textvariable=self.phone_var, width=40).grid(
            row=2, column=1, pady=2)
        
        # Email
        ttk.Label(business_frame, text="Email:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.email_var = tk.StringVar()
        ttk.Entry(business_frame, textvariable=self.email_var, width=40).grid(
            row=3, column=1, pady=2)
        
        # Tax ID
        ttk.Label(business_frame, text="Tax ID:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.tax_id_var = tk.StringVar()
        ttk.Entry(business_frame, textvariable=self.tax_id_var, width=40).grid(
            row=4, column=1, pady=2)
        
        # Template settings
        settings_frame = ttk.LabelFrame(main_container, text="Template Settings", padding="10")
        settings_frame.pack(fill='x', pady=10)
        
        # Template name
        ttk.Label(settings_frame, text="Template Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.template_name_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.template_name_var, width=30).grid(
            row=0, column=1, pady=2)
        
        # Header title
        ttk.Label(settings_frame, text="Invoice Title:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.header_title_var = tk.StringVar(value="INVOICE")
        ttk.Entry(settings_frame, textvariable=self.header_title_var, width=30).grid(
            row=1, column=1, pady=2)
        
        # Footer text
        ttk.Label(settings_frame, text="Footer Text:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.footer_text_var = tk.StringVar(value="Thank you for your business!")
        ttk.Entry(settings_frame, textvariable=self.footer_text_var, width=30).grid(
            row=2, column=1, pady=2)
        
        # Logo upload section
        logo_frame = ttk.Frame(settings_frame)
        logo_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky='w')
        
        ttk.Label(logo_frame, text="Logo:").pack(side=tk.LEFT, padx=(0, 10))
        self.logo_path_var = tk.StringVar(value="No logo selected")
        self.logo_label = ttk.Label(logo_frame, textvariable=self.logo_path_var, width=30)
        self.logo_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(logo_frame, text="Upload Logo", command=self.upload_logo).pack(side=tk.LEFT, padx=5)
        ttk.Button(logo_frame, text="Remove Logo", command=self.remove_logo).pack(side=tk.LEFT, padx=5)
        ttk.Button(logo_frame, text="Preview Logo", command=self.preview_logo).pack(side=tk.LEFT, padx=5)
        
        # Store logo data
        self.logo_data = None
        self.logo_filename = None
        
        # Show options
        self.show_logo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Show Logo", variable=self.show_logo_var).grid(
            row=4, column=0, pady=5)
        
        self.show_date_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Show Date in Footer", variable=self.show_date_var).grid(
            row=4, column=1, pady=5)
    
    def refresh(self):
        """Refresh template list"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, is_default FROM invoice_templates ORDER BY name")
        templates = cursor.fetchall()
        
        template_names = []
        self.template_map = {}
        
        for template in templates:
            name = template['name']
            if template['is_default']:
                name += " (Default)"
            template_names.append(name)
            self.template_map[name] = template['id']
        
        self.template_combo['values'] = template_names
        
        if template_names:
            self.template_combo.current(0)
            self.on_template_select(None)
    
    def on_template_select(self, event):
        """Handle template selection"""
        selected = self.template_var.get()
        if not selected:
            return
        
        template_id = self.template_map.get(selected)
        if not template_id:
            return
        
        self.current_template_id = template_id
        self.load_template(template_id)
    
    def load_template(self, template_id):
        """Load template data"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM invoice_templates WHERE id = ?
        """, (template_id,))
        
        template = cursor.fetchone()
        if not template:
            return
        
        self.template_name_var.set(template['name'])
        
        # Load business info
        if template['business_info_json']:
            business_info = json.loads(template['business_info_json'])
            self.business_name_var.set(business_info.get('name', ''))
            self.address_text.delete('1.0', tk.END)
            self.address_text.insert('1.0', business_info.get('address', ''))
            self.phone_var.set(business_info.get('phone', ''))
            self.email_var.set(business_info.get('email', ''))
            self.tax_id_var.set(business_info.get('tax_id', ''))
        
        # Load header
        if template['header_json']:
            header = json.loads(template['header_json'])
            self.header_title_var.set(header.get('title', 'INVOICE'))
            self.show_logo_var.set(header.get('show_logo', True))
        
        # Load footer
        if template['footer_json']:
            footer = json.loads(template['footer_json'])
            self.footer_text_var.set(footer.get('text', ''))
            self.show_date_var.set(footer.get('show_date', True))
        
        # Load logo from database
        cursor.execute("""
            SELECT * FROM invoice_assets 
            WHERE template_id = ? AND type = 'logo'
            ORDER BY created_at DESC LIMIT 1
        """, (template_id,))
        
        logo_asset = cursor.fetchone()
        if logo_asset:
            self.logo_data = logo_asset['blob']
            self.logo_filename = json.loads(logo_asset['meta_json'] or '{}').get('filename', 'logo.png')
            self.logo_path_var.set(self.logo_filename)
        else:
            self.logo_data = None
            self.logo_filename = None
            self.logo_path_var.set("No logo selected")
    
    def new_template(self):
        """Create new template"""
        self.current_template_id = None
        self.template_name_var.set("")
        self.business_name_var.set("")
        self.address_text.delete('1.0', tk.END)
        self.phone_var.set("")
        self.email_var.set("")
        self.tax_id_var.set("")
        self.header_title_var.set("INVOICE")
        self.footer_text_var.set("Thank you for your business!")
        self.show_logo_var.set(True)
        self.show_date_var.set(True)
        self.logo_data = None
        self.logo_filename = None
        self.logo_path_var.set("No logo selected")
    
    def upload_logo(self):
        """Upload a logo image"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Read the image file
                with open(file_path, 'rb') as f:
                    self.logo_data = f.read()
                
                # Store filename
                import os
                self.logo_filename = os.path.basename(file_path)
                self.logo_path_var.set(self.logo_filename)
                
                messagebox.showinfo("Success", f"Logo '{self.logo_filename}' loaded successfully")
            except Exception as e:
                logger.error(f"Error loading logo: {e}")
                messagebox.showerror("Error", f"Failed to load logo: {str(e)}")
    
    def remove_logo(self):
        """Remove the current logo"""
        self.logo_data = None
        self.logo_filename = None
        self.logo_path_var.set("No logo selected")
        messagebox.showinfo("Success", "Logo removed")
    
    def preview_logo(self):
        """Preview the current logo"""
        if not self.logo_data:
            messagebox.showwarning("Warning", "No logo to preview")
            return
        
        try:
            # Create preview window
            preview_window = tk.Toplevel(self.frame)
            preview_window.title(f"Logo Preview - {self.logo_filename}")
            preview_window.geometry("400x400")
            
            # Load and display image
            from PIL import Image, ImageTk
            import io
            
            image = Image.open(io.BytesIO(self.logo_data))
            # Resize to fit preview window
            image.thumbnail((350, 350), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            label = tk.Label(preview_window, image=photo)
            label.image = photo  # Keep a reference
            label.pack(padx=20, pady=20)
            
            # Add close button
            ttk.Button(preview_window, text="Close", 
                      command=preview_window.destroy).pack(pady=10)
            
        except Exception as e:
            logger.error(f"Error previewing logo: {e}")
            messagebox.showerror("Error", f"Failed to preview logo: {str(e)}")
    
    def save_template(self):
        """Save current template"""
        name = self.template_name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Template name is required")
            return
        
        # Prepare data
        business_info = {
            'name': self.business_name_var.get(),
            'address': self.address_text.get('1.0', tk.END).strip(),
            'phone': self.phone_var.get(),
            'email': self.email_var.get(),
            'tax_id': self.tax_id_var.get()
        }
        
        header = {
            'title': self.header_title_var.get(),
            'show_logo': self.show_logo_var.get(),
            'show_business_info': True
        }
        
        footer = {
            'text': self.footer_text_var.get(),
            'show_date': self.show_date_var.get()
        }
        
        styles = {
            'font_family': 'Helvetica',
            'font_size': 10,
            'header_font_size': 14,
            'margin_top': 20,
            'margin_bottom': 20,
            'margin_left': 20,
            'margin_right': 20
        }
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.current_template_id:
                # Update existing
                cursor.execute("""
                    UPDATE invoice_templates
                    SET name = ?, header_json = ?, footer_json = ?, 
                        styles_json = ?, business_info_json = ?
                    WHERE id = ?
                """, (
                    name,
                    json.dumps(header),
                    json.dumps(footer),
                    json.dumps(styles),
                    json.dumps(business_info),
                    self.current_template_id
                ))
                messagebox.showinfo("Success", "Template updated successfully")
            else:
                # Create new
                cursor.execute("""
                    INSERT INTO invoice_templates 
                    (name, header_json, footer_json, styles_json, business_info_json, is_default)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (
                    name,
                    json.dumps(header),
                    json.dumps(footer),
                    json.dumps(styles),
                    json.dumps(business_info)
                ))
                self.current_template_id = cursor.lastrowid
                messagebox.showinfo("Success", "Template created successfully")
            
            conn.commit()
            
            # Save logo if present
            if self.logo_data:
                # Remove old logo if exists
                cursor.execute("""
                    DELETE FROM invoice_assets 
                    WHERE template_id = ? AND type = 'logo'
                """, (self.current_template_id,))
                
                # Insert new logo
                meta_json = json.dumps({
                    'filename': self.logo_filename,
                    'size': len(self.logo_data)
                })
                
                cursor.execute("""
                    INSERT INTO invoice_assets (template_id, type, storage_kind, blob, meta_json)
                    VALUES (?, 'logo', 'blob', ?, ?)
                """, (self.current_template_id, self.logo_data, meta_json))
                
                conn.commit()
                logger.info(f"Logo saved for template {self.current_template_id}")
            
            self.refresh()
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def delete_template(self):
        """Delete current template"""
        if not self.current_template_id:
            messagebox.showwarning("Warning", "No template selected")
            return
        
        if messagebox.askyesno("Confirm", f"Delete template '{self.template_name_var.get()}'?"):
            conn = db.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM invoice_templates WHERE id = ?", 
                             (self.current_template_id,))
                conn.commit()
                messagebox.showinfo("Success", "Template deleted")
                self.new_template()
                self.refresh()
            except Exception as e:
                logger.error(f"Error deleting template: {e}")
                messagebox.showerror("Error", "Failed to delete template")
    
    def set_default(self):
        """Set current template as default"""
        if not self.current_template_id:
            messagebox.showwarning("Warning", "No template selected")
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Clear all defaults
            cursor.execute("UPDATE invoice_templates SET is_default = 0")
            # Set new default
            cursor.execute("UPDATE invoice_templates SET is_default = 1 WHERE id = ?",
                         (self.current_template_id,))
            conn.commit()
            messagebox.showinfo("Success", "Template set as default")
            self.refresh()
        except Exception as e:
            logger.error(f"Error setting default template: {e}")
            messagebox.showerror("Error", "Failed to set default template")
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame


class SettingsTab:
    """Tab for system settings (Admin only)"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.load_settings()
    
    def _create_widgets(self):
        """Create the settings tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="20")
        main_container.pack(fill='both', expand=True)
        
        # General Settings
        general_frame = ttk.LabelFrame(main_container, text="General Settings", padding="15")
        general_frame.pack(fill='x', pady=(0, 20))
        
        # Currency symbol
        ttk.Label(general_frame, text="Currency Symbol:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.currency_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.currency_var, width=10).grid(
            row=0, column=1, sticky=tk.W, pady=5)
        
        # Default tax rate
        ttk.Label(general_frame, text="Default Tax Rate (%):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tax_rate_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.tax_rate_var, width=10).grid(
            row=1, column=1, sticky=tk.W, pady=5)
        
        # Page size
        ttk.Label(general_frame, text="Invoice Page Size:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.page_size_var = tk.StringVar()
        page_combo = ttk.Combobox(general_frame, textvariable=self.page_size_var,
                                 values=["A4", "Letter"], state="readonly", width=10)
        page_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Locale
        ttk.Label(general_frame, text="Locale:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.locale_var = tk.StringVar()
        locale_combo = ttk.Combobox(general_frame, textvariable=self.locale_var,
                                   values=["en_US", "en_GB", "de_DE", "fr_FR", "es_ES"],
                                   state="readonly", width=10)
        locale_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Time zone
        ttk.Label(general_frame, text="Time Zone:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.timezone_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.timezone_var, width=20).grid(
            row=4, column=1, sticky=tk.W, pady=5)
        
        # Invoice folder
        ttk.Label(general_frame, text="Invoice Folder:").grid(row=5, column=0, sticky=tk.W, pady=5)
        invoice_folder_frame = ttk.Frame(general_frame)
        invoice_folder_frame.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        self.invoice_folder_var = tk.StringVar()
        ttk.Entry(invoice_folder_frame, textvariable=self.invoice_folder_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(invoice_folder_frame, text="Browse", command=self.browse_invoice_folder).pack(side=tk.LEFT)
        
        # Save button
        save_button = ttk.Button(main_container, text="Save Settings", command=self.save_settings)
        save_button.pack(pady=20)
        
        # System info
        info_frame = ttk.LabelFrame(main_container, text="System Information", padding="15")
        info_frame.pack(fill='x', pady=20)
        
        self.info_text = tk.Text(info_frame, height=8, width=60, state='disabled')
        self.info_text.pack()
        
        self.update_system_info()
    
    def browse_invoice_folder(self):
        """Browse for invoice folder"""
        folder = filedialog.askdirectory(
            title="Select Invoice Folder",
            initialdir=self.invoice_folder_var.get() or os.path.expanduser("~")
        )
        if folder:
            self.invoice_folder_var.set(folder)
    
    def load_settings(self):
        """Load current settings from database"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        
        if settings:
            self.currency_var.set(settings['currency_symbol'])
            self.tax_rate_var.set(str(settings['default_tax_rate']))
            self.page_size_var.set(settings['page_size'])
            self.locale_var.set(settings['locale'])
            self.timezone_var.set(settings['time_zone'])
            
            # Set invoice folder, default to 'invoices' if not set
            # sqlite3.Row objects use dictionary-style access, not get() method
            invoice_folder = settings['invoice_folder'] if settings['invoice_folder'] else 'invoices'
            if not os.path.isabs(invoice_folder):
                # If relative path, make it relative to the app directory
                invoice_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), invoice_folder)
            self.invoice_folder_var.set(invoice_folder)
    
    def save_settings(self):
        """Save settings to database"""
        try:
            tax_rate = float(self.tax_rate_var.get())
            if tax_rate < 0 or tax_rate > 100:
                raise ValueError("Tax rate must be between 0 and 100")
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Create invoice folder if it doesn't exist
            invoice_folder = self.invoice_folder_var.get()
            if invoice_folder:
                os.makedirs(invoice_folder, exist_ok=True)
            
            cursor.execute("""
                UPDATE settings
                SET currency_symbol = ?, default_tax_rate = ?, locale = ?, 
                    time_zone = ?, page_size = ?, invoice_folder = ?
                WHERE id = 1
            """, (
                self.currency_var.get(),
                tax_rate,
                self.locale_var.get(),
                self.timezone_var.get(),
                self.page_size_var.get(),
                invoice_folder
            ))
            
            conn.commit()
            messagebox.showinfo("Success", "Settings saved successfully")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", "Failed to save settings")
    
    def update_system_info(self):
        """Update system information display"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get database statistics
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        order_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM invoice_templates")
        template_count = cursor.fetchone()['count']
        
        # Get database file size
        import os
        db_size = os.path.getsize("pos_system.db") / 1024  # KB
        
        info = f"""Database Statistics:
- Total Orders: {order_count}
- Total Users: {user_count}
- Invoice Templates: {template_count}
- Database Size: {db_size:.2f} KB

System Version: POS System v1.0
Python Version: {sys.version.split()[0]}
"""
        
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', info)
        self.info_text.config(state='disabled')
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame


class UserPreferencesTab:
    """Tab for user preferences (available to all users)"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.load_preferences()
    
    def _create_widgets(self):
        """Create the user preferences tab widgets"""
        # Main container
        main_container = ttk.Frame(self.frame, padding="20")
        main_container.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(main_container, text="User Preferences", 
                         font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 20))
        
        # Display Settings Frame
        display_frame = ttk.LabelFrame(main_container, text="Display Settings", padding="15")
        display_frame.pack(fill='x', pady=(0, 20))
        
        # Currency symbol preference
        ttk.Label(display_frame, text="Preferred Currency Symbol:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.currency_var = tk.StringVar()
        currency_combo = ttk.Combobox(display_frame, textvariable=self.currency_var,
                                     values=["$ (USD)", "€ (EUR)", "£ (GBP)", "¥ (JPY)", 
                                            "₹ (INR)", "¥ (CNY)", "₽ (RUB)", "R (ZAR)"],
                                     state="readonly", width=15)
        currency_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Date format preference
        ttk.Label(display_frame, text="Date Format:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.date_format_var = tk.StringVar()
        date_combo = ttk.Combobox(display_frame, textvariable=self.date_format_var,
                                 values=["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"],
                                 state="readonly", width=15)
        date_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Language preference (for future implementation)
        ttk.Label(display_frame, text="Language:").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar()
        language_combo = ttk.Combobox(display_frame, textvariable=self.language_var,
                                     values=["English", "Spanish", "French", "German", "Chinese"],
                                     state="readonly", width=15)
        language_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Invoice Settings Frame
        invoice_frame = ttk.LabelFrame(main_container, text="Invoice Preferences", padding="15")
        invoice_frame.pack(fill='x', pady=(0, 20))
        
        # Show prices with tax
        self.show_tax_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(invoice_frame, text="Show prices with tax included",
                       variable=self.show_tax_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Auto-print invoices
        self.auto_print_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(invoice_frame, text="Automatically print invoices after finalization",
                       variable=self.auto_print_var).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Default copies
        ttk.Label(invoice_frame, text="Default invoice copies:").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.copies_var = tk.IntVar(value=1)
        copies_spin = ttk.Spinbox(invoice_frame, from_=1, to=5, 
                                 textvariable=self.copies_var, width=10)
        copies_spin.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        # POS Settings Frame  
        pos_frame = ttk.LabelFrame(main_container, text="POS Preferences", padding="15")
        pos_frame.pack(fill='x', pady=(0, 20))
        
        # Default tax rate for new orders
        ttk.Label(pos_frame, text="My default tax rate (%):").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.tax_rate_var = tk.StringVar()
        ttk.Entry(pos_frame, textvariable=self.tax_rate_var, width=10).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Sound notifications
        self.sound_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pos_frame, text="Enable sound notifications",
                       variable=self.sound_var).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Auto-clear after finalize
        self.auto_clear_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pos_frame, text="Clear order after finalization",
                       variable=self.auto_clear_var).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Button Frame
        button_frame = ttk.Frame(main_container)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Save Preferences", 
                  command=self.save_preferences).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_defaults).pack(side=tk.LEFT, padx=5)
        
        # Info label
        info_label = ttk.Label(main_container, 
                             text="Note: These preferences apply only to your user account",
                             font=('Arial', 9, 'italic'))
        info_label.pack(pady=10)
        
        # System defaults info (read-only)
        system_frame = ttk.LabelFrame(main_container, text="System Defaults (Admin-set)", padding="10")
        system_frame.pack(fill='x')
        
        self.system_info_text = tk.Text(system_frame, height=4, width=60, state='disabled')
        self.system_info_text.pack()
        self.update_system_info()
    
    def load_preferences(self):
        """Load user preferences from database or use system defaults"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user preferences
        user_id = self.auth_manager.current_user['id']
        cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
        user_prefs = cursor.fetchone()
        
        # Get system defaults as fallback
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        system_settings = cursor.fetchone()
        
        if user_prefs:
            # Load user preferences
            currency = user_prefs['currency_symbol'] or system_settings['currency_symbol']
            currency_map = {
                '$': '$ (USD)', '€': '€ (EUR)', '£': '£ (GBP)', 
                '¥': '¥ (JPY)', '₹': '₹ (INR)', '₽': '₽ (RUB)', 'R': 'R (ZAR)'
            }
            self.currency_var.set(currency_map.get(currency, '₹ (INR)'))
            self.date_format_var.set(user_prefs['date_format'] or "MM/DD/YYYY")
            self.language_var.set(user_prefs['language'] or "English")
            self.tax_rate_var.set(str(user_prefs['tax_rate'] if user_prefs['tax_rate'] is not None else system_settings['default_tax_rate']))
            self.show_tax_var.set(bool(user_prefs['show_tax']))
            self.auto_print_var.set(bool(user_prefs['auto_print']))
            self.copies_var.set(user_prefs['invoice_copies'] or 1)
            self.sound_var.set(bool(user_prefs['enable_sound']))
            self.auto_clear_var.set(bool(user_prefs['auto_clear_order']))
        elif system_settings:
            # Use system defaults
            currency = system_settings['currency_symbol']
            currency_map = {
                '$': '$ (USD)', '€': '€ (EUR)', '£': '£ (GBP)', 
                '¥': '¥ (JPY)', '₹': '₹ (INR)', '₽': '₽ (RUB)'
            }
            self.currency_var.set(currency_map.get(currency, '₹ (INR)'))
            self.tax_rate_var.set(str(system_settings['default_tax_rate']))
            
            # Set other defaults
            self.date_format_var.set("MM/DD/YYYY")
            self.language_var.set("English")
            self.show_tax_var.set(True)
            self.auto_print_var.set(False)
            self.copies_var.set(1)
            self.sound_var.set(True)
            self.auto_clear_var.set(True)
    
    def save_preferences(self):
        """Save user preferences"""
        try:
            # Validate tax rate
            tax_rate = float(self.tax_rate_var.get())
            if tax_rate < 0 or tax_rate > 100:
                raise ValueError("Tax rate must be between 0 and 100")
            
            # Extract currency symbol
            currency_full = self.currency_var.get()
            currency_symbol = currency_full.split()[0] if currency_full else '₹'
            
            # Save to database
            conn = db.get_connection()
            cursor = conn.cursor()
            user_id = self.auth_manager.current_user['id']
            
            # Check if preferences exist
            cursor.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing preferences
                cursor.execute("""
                    UPDATE user_preferences
                    SET currency_symbol = ?, date_format = ?, language = ?,
                        tax_rate = ?, show_tax = ?, auto_print = ?,
                        invoice_copies = ?, enable_sound = ?, auto_clear_order = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (
                    currency_symbol,
                    self.date_format_var.get(),
                    self.language_var.get(),
                    tax_rate,
                    int(self.show_tax_var.get()),
                    int(self.auto_print_var.get()),
                    self.copies_var.get(),
                    int(self.sound_var.get()),
                    int(self.auto_clear_var.get()),
                    user_id
                ))
            else:
                # Insert new preferences
                cursor.execute("""
                    INSERT INTO user_preferences 
                    (user_id, currency_symbol, date_format, language, tax_rate,
                     show_tax, auto_print, invoice_copies, enable_sound, auto_clear_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    currency_symbol,
                    self.date_format_var.get(),
                    self.language_var.get(),
                    tax_rate,
                    int(self.show_tax_var.get()),
                    int(self.auto_print_var.get()),
                    self.copies_var.get(),
                    int(self.sound_var.get()),
                    int(self.auto_clear_var.get())
                ))
            
            conn.commit()
            
            messagebox.showinfo("Success", 
                              f"Your preferences have been saved:\n"
                              f"Currency: {currency_symbol}\n"
                              f"Tax Rate: {tax_rate}%\n"
                              f"Date Format: {self.date_format_var.get()}")
            
            logger.info(f"User {self.auth_manager.current_user['username']} saved preferences")
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            messagebox.showerror("Error", "Failed to save preferences")
    
    def reset_defaults(self):
        """Reset to default preferences"""
        if messagebox.askyesno("Confirm", "Reset all preferences to defaults?"):
            self.load_preferences()
            messagebox.showinfo("Success", "Preferences reset to defaults")
    
    def update_system_info(self):
        """Display current system-wide settings"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        
        if settings:
            info = f"""System-wide settings (set by admin):
• Default Currency: {settings['currency_symbol']}
• Default Tax Rate: {settings['default_tax_rate']}%
• Page Size: {settings['page_size']}"""
            
            self.system_info_text.config(state='normal')
            self.system_info_text.delete('1.0', tk.END)
            self.system_info_text.insert('1.0', info)
            self.system_info_text.config(state='disabled')
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame
