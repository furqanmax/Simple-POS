"""
POS Order tab for creating and managing orders
"""
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
import logging
from models import OrderModel, FrequentOrderModel
from invoice_generator import InvoiceGenerator
from invoice_generator_enhanced import EnhancedInvoiceGenerator
from invoice_preview_dialog import show_invoice_preview
from invoice_formats import BillSize, LayoutStyle
from database import db
import subprocess
import platform
import os

logger = logging.getLogger(__name__)

class POSOrderTab:
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.order_model = OrderModel()
        self.invoice_generator = InvoiceGenerator()
        self.currency_symbol = '₹'  # Default currency
        
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self.load_user_preferences()
        
    def _create_widgets(self):
        """Create the order tab widgets"""
        # Main container with padding
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=2)
        main_container.rowconfigure(1, weight=1)
        
        # Left panel - Item entry
        left_panel = ttk.LabelFrame(main_container, text="Add Item", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        
        # Item name
        ttk.Label(left_panel, text="Item Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.item_name_var = tk.StringVar()
        self.item_name_entry = ttk.Entry(left_panel, textvariable=self.item_name_var, width=30)
        self.item_name_entry.grid(row=0, column=1, pady=2, padx=(5, 0))
        
        # Quantity
        ttk.Label(left_panel, text="Quantity:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.quantity_var = tk.StringVar(value="1")
        self.quantity_entry = ttk.Entry(left_panel, textvariable=self.quantity_var, width=30)
        self.quantity_entry.grid(row=1, column=1, pady=2, padx=(5, 0))
        
        # Unit price
        ttk.Label(left_panel, text="Unit Price:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.price_var = tk.StringVar(value="0.00")
        self.price_entry = ttk.Entry(left_panel, textvariable=self.price_var, width=30)
        self.price_entry.grid(row=2, column=1, pady=2, padx=(5, 0))
        
        # Add item button
        self.add_item_button = ttk.Button(left_panel, text="Add Item", command=self.add_item)
        self.add_item_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Frequent order section
        freq_frame = ttk.LabelFrame(left_panel, text="Frequent Orders", padding="10")
        freq_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
        ttk.Label(freq_frame, text="Select Template:").grid(row=0, column=0, sticky=tk.W)
        self.freq_order_var = tk.StringVar()
        self.freq_order_combo = ttk.Combobox(freq_frame, textvariable=self.freq_order_var, 
                                            state="readonly", width=25)
        self.freq_order_combo.grid(row=1, column=0, pady=5)
        
        self.apply_freq_button = ttk.Button(freq_frame, text="Apply Template", 
                                           command=self.apply_frequent_order)
        self.apply_freq_button.grid(row=2, column=0, pady=5)
        
        # Tax settings
        tax_frame = ttk.LabelFrame(left_panel, text="Tax Settings", padding="10")
        tax_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
        ttk.Label(tax_frame, text="Tax Rate (%):").grid(row=0, column=0, sticky=tk.W)
        self.tax_rate_var = tk.StringVar(value=str(float(self.order_model.tax_rate)))
        self.tax_rate_entry = ttk.Entry(tax_frame, textvariable=self.tax_rate_var, width=10)
        self.tax_rate_entry.grid(row=0, column=1, padx=5)
        
        self.update_tax_button = ttk.Button(tax_frame, text="Update Tax", 
                                           command=self.update_tax_rate)
        self.update_tax_button.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Right panel - Order items
        right_panel = ttk.LabelFrame(main_container, text="Current Order", padding="10")
        right_panel.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Items tree view
        columns = ('Item', 'Qty', 'Price', 'Total')
        self.items_tree = ttk.Treeview(right_panel, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            if col == 'Item':
                self.items_tree.column(col, width=200)
            else:
                self.items_tree.column(col, width=80, anchor=tk.E)
        
        self.items_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.items_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        # Item actions
        item_actions_frame = ttk.Frame(right_panel)
        item_actions_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(item_actions_frame, text="Remove Selected", 
                  command=self.remove_selected_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(item_actions_frame, text="Clear All", 
                  command=self.clear_order).pack(side=tk.LEFT, padx=5)
        
        # Totals frame
        totals_frame = ttk.Frame(right_panel)
        totals_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        # Subtotal
        ttk.Label(totals_frame, text="Subtotal:", font=('Helvetica', 10)).grid(
            row=0, column=0, sticky=tk.E, padx=5)
        self.subtotal_label = ttk.Label(totals_frame, text="₹0.00", font=('Helvetica', 10, 'bold'))
        self.subtotal_label.grid(row=0, column=1, sticky=tk.W)
        
        # Tax
        ttk.Label(totals_frame, text="Tax:", font=('Helvetica', 10)).grid(
            row=1, column=0, sticky=tk.E, padx=5)
        self.tax_label = ttk.Label(totals_frame, text="₹0.00", font=('Helvetica', 10))
        self.tax_label.grid(row=1, column=1, sticky=tk.W)
        
        # Grand total
        ttk.Label(totals_frame, text="Grand Total:", font=('Helvetica', 12, 'bold')).grid(
            row=2, column=0, sticky=tk.E, padx=5)
        self.total_label = ttk.Label(totals_frame, text="₹0.00", font=('Helvetica', 12, 'bold'), 
                                    foreground='green')
        self.total_label.grid(row=2, column=1, sticky=tk.W)
        
        # Action buttons
        actions_frame = ttk.Frame(right_panel)
        actions_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        self.finalize_button = ttk.Button(actions_frame, text="Finalize Order", 
                                         command=self.finalize_order,
                                         style='Accent.TButton')
        self.finalize_button.pack(side=tk.LEFT, padx=5)
        
        self.print_button = ttk.Button(actions_frame, text="Finalize & Print", 
                                       command=self.finalize_and_print)
        self.print_button.pack(side=tk.LEFT, padx=5)
        
        # Load frequent orders
        self.load_frequent_orders()
        
        # Bind Enter key for quick item addition
        self.item_name_entry.bind('<Return>', lambda e: self.quantity_entry.focus())
        self.quantity_entry.bind('<Return>', lambda e: self.price_entry.focus())
        self.price_entry.bind('<Return>', lambda e: self.add_item())
    
    def add_item(self):
        """Add item to current order"""
        try:
            name = self.item_name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter item name")
                return
            
            quantity = float(self.quantity_var.get())
            unit_price = float(self.price_var.get())
            
            # Add to model
            item = self.order_model.add_item(name, quantity, unit_price)
            
            # Add to tree view
            self.items_tree.insert('', 'end', values=(
                item['name'],
                f"{item['quantity']:.2f}",
                f"{self.currency_symbol}{item['unit_price']:.2f}",
                f"{self.currency_symbol}{item['line_total']:.2f}"
            ))
            
            # Update totals
            self.update_totals()
            
            # Clear input fields
            self.item_name_var.set("")
            self.quantity_var.set("1")
            self.price_var.set("0.00")
            self.item_name_entry.focus()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.error(f"Error adding item: {e}")
            messagebox.showerror("Error", "Failed to add item")
    
    def remove_selected_item(self):
        """Remove selected item from order"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return
        
        # Get index
        item = self.items_tree.item(selection[0])
        index = self.items_tree.index(selection[0])
        
        # Remove from model
        self.order_model.remove_item(index)
        
        # Remove from tree
        self.items_tree.delete(selection[0])
        
        # Update totals
        self.update_totals()
    
    def clear_order(self):
        """Clear all items from current order"""
        if self.order_model.items:
            if messagebox.askyesno("Confirm", "Clear all items from the order?"):
                self.order_model.clear_items()
                for item in self.items_tree.get_children():
                    self.items_tree.delete(item)
                self.update_totals()
    
    def load_user_preferences(self):
        """Load user preferences for currency and tax rate"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Get user preferences
            user_id = self.auth_manager.get_current_user()['id']
            cursor.execute("""
                SELECT currency_symbol, tax_rate 
                FROM user_preferences 
                WHERE user_id = ?
            """, (user_id,))
            
            user_prefs = cursor.fetchone()
            
            if user_prefs:
                # Use user's currency preference
                if user_prefs['currency_symbol']:
                    self.currency_symbol = user_prefs['currency_symbol']
                
                # Set user's default tax rate
                if user_prefs['tax_rate'] is not None:
                    self.tax_rate_var.set(str(user_prefs['tax_rate']))
                    self.order_model.set_tax_rate(float(user_prefs['tax_rate']))
            else:
                # Load system defaults
                cursor.execute("SELECT currency_symbol, default_tax_rate FROM settings WHERE id = 1")
                settings = cursor.fetchone()
                if settings:
                    self.currency_symbol = settings['currency_symbol'] or '₹'
                    self.tax_rate_var.set(str(settings['default_tax_rate']))
                    self.order_model.set_tax_rate(float(settings['default_tax_rate']))
                    
            self.load_frequent_orders()
            self.update_totals()
            
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
            # Set defaults on error
            self.currency_symbol = '₹'
            self.tax_rate_var.set("0")
    
    def update_totals(self):
        """Update the totals display"""
        subtotal = self.order_model.get_subtotal()
        tax = self.order_model.get_tax_total()
        total = self.order_model.get_grand_total()
        
        # Use the currency symbol from preferences
        self.subtotal_label.config(text=f"{self.currency_symbol}{subtotal:.2f}")
        self.tax_label.config(text=f"{self.currency_symbol}{tax:.2f}")
        self.total_label.config(text=f"{self.currency_symbol}{total:.2f}")
    
    def update_tax_rate(self):
        """Update tax rate for current order"""
        try:
            rate = float(self.tax_rate_var.get())
            self.order_model.set_tax_rate(rate)
            self.update_totals()
            messagebox.showinfo("Success", f"Tax rate updated to {rate}%")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def load_frequent_orders(self):
        """Load frequent order templates"""
        try:
            user_id = self.auth_manager.get_current_user()['id']
            templates = FrequentOrderModel.get_all(user_id, include_global=True)
            
            template_names = []
            self.template_map = {}
            
            for template in templates:
                label = template['label']
                if template['is_global']:
                    label += " (Global)"
                template_names.append(label)
                self.template_map[label] = template
            
            self.freq_order_combo['values'] = template_names
            
        except Exception as e:
            logger.error(f"Error loading frequent orders: {e}")
    
    def apply_frequent_order(self):
        """Apply selected frequent order template"""
        selected = self.freq_order_var.get()
        if not selected:
            messagebox.showwarning("Warning", "Please select a template")
            return
        
        template = self.template_map.get(selected)
        if not template:
            return
        
        # Clear current order
        if self.order_model.items:
            if not messagebox.askyesno("Confirm", 
                                      "This will clear current items. Continue?"):
                return
        
        self.order_model.clear_items()
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Apply template items
        for item in template['items']:
            try:
                added_item = self.order_model.add_item(
                    item['name'],
                    item['quantity'],
                    item['unit_price']
                )
                
                self.items_tree.insert('', 'end', values=(
                    added_item['name'],
                    f"{added_item['quantity']:.2f}",
                    f"{self.currency_symbol}{added_item['unit_price']:.2f}",
                    f"{self.currency_symbol}{added_item['line_total']:.2f}"
                ))
            except Exception as e:
                logger.error(f"Error applying template item: {e}")
        
        self.update_totals()
        messagebox.showinfo("Success", f"Applied template: {template['label']}")
    
    def finalize_order(self):
        """Finalize the current order"""
        if not self.order_model.items:
            messagebox.showwarning("Warning", "Cannot finalize an empty order")
            return
        
        if not messagebox.askyesno("Confirm", "Finalize this order?"):
            return
        
        try:
            user_id = self.auth_manager.get_current_user()['id']
            order_id = self.order_model.finalize_order(user_id)
            
            # Clear the order
            self.order_model = OrderModel()
            for item in self.items_tree.get_children():
                self.items_tree.delete(item)
            self.update_totals()
            
            messagebox.showinfo("Success", f"Order #{order_id} finalized successfully!")
            return order_id
            
        except Exception as e:
            logger.error(f"Error finalizing order: {e}")
            messagebox.showerror("Error", f"Failed to finalize order: {str(e)}")
            return None
    
    def finalize_and_print(self):
        """Finalize order and show invoice preview for printing"""
        order_id = self.finalize_order()
        if order_id:
            # Show invoice preview dialog with format selection
            show_invoice_preview(self.parent, order_id, self.auth_manager)
    
    def print_invoice(self, order_id):
        """Generate and print invoice with format selection"""
        try:
            # Show invoice preview dialog for format selection and printing
            show_invoice_preview(self.parent, order_id, self.auth_manager)
            
        except Exception as e:
            logger.error(f"Error showing invoice preview: {e}")
            # Fallback to original generator if enhanced fails
            try:
                pdf_path = self.invoice_generator.generate_invoice(order_id)
                messagebox.showinfo("Success", f"Invoice generated: {pdf_path}")
            except Exception as e2:
                logger.error(f"Error generating invoice: {e2}")
                messagebox.showerror("Error", "Failed to generate invoice")
    
    def refresh(self):
        """Refresh the tab with latest preferences"""
        self.load_user_preferences()
        logger.info("POS Order tab refreshed with latest preferences")
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame
