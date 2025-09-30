"""
Invoice Preview Dialog with Format Selection
Interactive dialog for previewing invoices with different sizes and layouts
"""
import tkinter as tk
from tkinter import ttk, messagebox, font
import logging
from typing import Optional, Callable
import os
import subprocess
import platform
from datetime import datetime

from invoice_formats import BillSize, LayoutStyle, BillFormatRegistry
from invoice_generator_enhanced import EnhancedInvoiceGenerator

logger = logging.getLogger(__name__)


class InvoicePreviewDialog:
    """Dialog for invoice preview with format selection"""
    
    def __init__(self, parent, order_id: int, auth_manager):
        self.parent = parent
        self.order_id = order_id
        self.auth_manager = auth_manager
        self.selected_size = BillSize.A4
        self.selected_layout = LayoutStyle.CLASSIC
        self.preview_path = None
        self.generator = EnhancedInvoiceGenerator()
        self.registry = BillFormatRegistry()
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Invoice Preview - Order #{order_id:04d}")
        self.dialog.geometry("900x700")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_default_settings()
        self._generate_preview()
    
    def _create_widgets(self):
        """Create dialog widgets"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Top toolbar with format selection
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill='x', pady=(0, 10))
        
        # Size selection
        ttk.Label(toolbar_frame, text="Bill Size:", font=('Helvetica', 10)).pack(side='left', padx=(0, 5))
        
        self.size_var = tk.StringVar()
        self.size_combo = ttk.Combobox(toolbar_frame, textvariable=self.size_var, 
                                       state='readonly', width=20)
        
        # Populate size options
        size_options = []
        for size in BillSize:
            size_options.append(f"{size.display_name} ({size.width_mm}×{size.height_mm}mm)")
        self.size_combo['values'] = size_options
        self.size_combo.current(3)  # Default to A4
        self.size_combo.pack(side='left', padx=(0, 15))
        self.size_combo.bind('<<ComboboxSelected>>', self._on_size_changed)
        
        # Layout style selection
        ttk.Label(toolbar_frame, text="Layout:", font=('Helvetica', 10)).pack(side='left', padx=(0, 5))
        
        self.layout_var = tk.StringVar()
        self.layout_combo = ttk.Combobox(toolbar_frame, textvariable=self.layout_var,
                                         state='readonly', width=15)
        self.layout_combo['values'] = ['Classic', 'Minimal', 'Compact', 'Detailed']
        self.layout_combo.current(0)  # Default to Classic
        self.layout_combo.pack(side='left', padx=(0, 15))
        self.layout_combo.bind('<<ComboboxSelected>>', self._on_layout_changed)
        
        # Refresh preview button
        ttk.Button(toolbar_frame, text="🔄 Refresh Preview", 
                  command=self._generate_preview).pack(side='left', padx=5)
        
        # Preview info label
        self.info_label = ttk.Label(toolbar_frame, text="", 
                                   font=('Helvetica', 9), foreground='gray')
        self.info_label.pack(side='right')
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # Preview area with scrollbars
        preview_container = ttk.Frame(main_frame)
        preview_container.pack(fill='both', expand=True, pady=10)
        
        # Canvas for preview
        self.preview_canvas = tk.Canvas(preview_container, bg='#f0f0f0')
        v_scrollbar = ttk.Scrollbar(preview_container, orient='vertical', 
                                   command=self.preview_canvas.yview)
        h_scrollbar = ttk.Scrollbar(preview_container, orient='horizontal',
                                   command=self.preview_canvas.xview)
        
        self.preview_canvas.configure(yscrollcommand=v_scrollbar.set,
                                     xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.preview_canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        # Preview placeholder
        self.preview_frame = ttk.Frame(self.preview_canvas, relief='solid', borderwidth=1)
        self.preview_window = self.preview_canvas.create_window(
            0, 0, anchor='nw', window=self.preview_frame
        )
        
        # Loading label
        self.loading_label = ttk.Label(self.preview_frame, 
                                      text="Generating preview...",
                                      font=('Helvetica', 14))
        self.loading_label.pack(padx=50, pady=50)
        
        # Format info panel
        info_frame = ttk.LabelFrame(main_frame, text="Format Information", padding="10")
        info_frame.pack(fill='x', pady=(5, 10))
        
        # Create info grid
        self.info_grid = ttk.Frame(info_frame)
        self.info_grid.pack(fill='x')
        
        # Info labels
        self.create_info_row("Page Size:", "", 0)
        self.create_info_row("Printable Area:", "", 1)
        self.create_info_row("Margins:", "", 2)
        self.create_info_row("Characters/Line:", "", 3)
        self.create_info_row("Printer Compatibility:", "", 4)
        
        # Bottom action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Left side - settings buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side='left')
        
        ttk.Button(left_buttons, text="⚙️ Set as Default", 
                  command=self._save_as_default).pack(side='left', padx=2)
        
        ttk.Button(left_buttons, text="💾 Save PDF", 
                  command=self._save_pdf).pack(side='left', padx=2)
        
        # Right side - action buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side='right')
        
        self.print_button = ttk.Button(right_buttons, text="🖨️ Print", 
                                       command=self._print_invoice,
                                       style='Primary.TButton')
        self.print_button.pack(side='left', padx=5)
        
        ttk.Button(right_buttons, text="Close", 
                  command=self.dialog.destroy).pack(side='left', padx=5)
    
    def create_info_row(self, label: str, value: str, row: int):
        """Create an info row in the info grid"""
        label_widget = ttk.Label(self.info_grid, text=label, 
                                font=('Helvetica', 9, 'bold'))
        label_widget.grid(row=row, column=0, sticky='w', padx=(0, 10), pady=2)
        
        value_widget = ttk.Label(self.info_grid, text=value, 
                                font=('Helvetica', 9))
        value_widget.grid(row=row, column=1, sticky='w', pady=2)
        
        # Store reference for updates
        setattr(self, f"info_{row}_value", value_widget)
    
    def _on_size_changed(self, event=None):
        """Handle size selection change"""
        index = self.size_combo.current()
        self.selected_size = list(BillSize)[index]
        
        # Auto-select appropriate layout for thermal
        if self.selected_size.is_thermal:
            self.layout_combo.set('Compact')
            self.selected_layout = LayoutStyle.COMPACT
        
        self._update_format_info()
        self._generate_preview()
    
    def _on_layout_changed(self, event=None):
        """Handle layout selection change"""
        layout_map = {
            'Classic': LayoutStyle.CLASSIC,
            'Minimal': LayoutStyle.MINIMAL,
            'Compact': LayoutStyle.COMPACT,
            'Detailed': LayoutStyle.DETAILED
        }
        self.selected_layout = layout_map[self.layout_var.get()]
        self._generate_preview()
    
    def _update_format_info(self):
        """Update format information display"""
        config = self.registry.get_default_config(self.selected_size, self.selected_layout)
        
        # Page size
        if self.selected_size.is_continuous:
            size_text = f"{self.selected_size.width_mm}mm (continuous)"
        else:
            size_text = f"{self.selected_size.width_mm} × {self.selected_size.height_mm}mm"
        self.info_0_value.config(text=size_text)
        
        # Printable area
        if self.selected_size.is_continuous:
            printable_text = f"{config.printable_width_mm:.1f}mm width"
        else:
            printable_text = f"{config.printable_width_mm:.1f} × {config.printable_height_mm:.1f}mm"
        self.info_1_value.config(text=printable_text)
        
        # Margins
        margins_text = f"T:{config.margins.top} R:{config.margins.right} B:{config.margins.bottom} L:{config.margins.left}mm"
        self.info_2_value.config(text=margins_text)
        
        # Characters per line (for thermal)
        if self.selected_size.is_thermal:
            chars_text = f"{config.chars_per_line} characters"
        else:
            chars_text = "N/A (proportional font)"
        self.info_3_value.config(text=chars_text)
        
        # Printer compatibility
        if self.selected_size.is_thermal:
            compat_text = "Thermal printers only"
        elif self.selected_size in [BillSize.A3]:
            compat_text = "Large format printers"
        else:
            compat_text = "Standard printers"
        self.info_4_value.config(text=compat_text)
    
    def _generate_preview(self):
        """Generate preview PDF and display it"""
        try:
            # Check if widgets still exist
            if not self.dialog.winfo_exists():
                return
                
            # Update loading state
            if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
                self.loading_label.config(text="Generating preview...")
                self.dialog.update()
            
            # Generate preview PDF
            self.preview_path = self.generator.generate_invoice(
                self.order_id,
                bill_size=self.selected_size,
                layout_style=self.selected_layout,
                preview_only=True
            )
            
            # Update info label if it exists
            if hasattr(self, 'info_label') and self.info_label.winfo_exists():
                file_size = os.path.getsize(self.preview_path) / 1024
                self.info_label.config(
                    text=f"Preview generated • {file_size:.1f} KB • {datetime.now().strftime('%H:%M:%S')}"
                )
            
            # Display preview (simplified - would need PDF viewer integration)
            self._display_preview_placeholder()
            
            # Update format info
            self._update_format_info()
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
                self.loading_label.config(text=f"Error: {str(e)}")
            else:
                messagebox.showerror("Preview Error", f"Failed to generate preview: {str(e)}")
    
    def _display_preview_placeholder(self):
        """Display a placeholder for the preview"""
        # Check if preview_frame still exists
        if not hasattr(self, 'preview_frame') or not self.preview_frame.winfo_exists():
            return
            
        # Clear previous content
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Create preview representation
        preview_content = ttk.Frame(self.preview_frame)
        preview_content.pack(padx=20, pady=20)
        
        # Simulate page based on size
        if self.selected_size.is_thermal:
            page_width = 200
            page_height = 400
        elif self.selected_size == BillSize.A3:
            page_width = 420
            page_height = 594
        elif self.selected_size == BillSize.A5:
            page_width = 210
            page_height = 297
        else:  # A4
            page_width = 297
            page_height = 420
        
        # Page representation
        page_frame = tk.Frame(preview_content, bg='white', 
                             width=page_width, height=page_height,
                             relief='solid', borderwidth=1)
        page_frame.pack()
        
        # Page content placeholder
        content_frame = tk.Frame(page_frame, bg='white')
        content_frame.place(relx=0.1, rely=0.05, relwidth=0.8, relheight=0.9)
        
        # Header
        tk.Label(content_frame, text="INVOICE PREVIEW", 
                font=('Helvetica', 14, 'bold'),
                bg='white').pack(pady=10)
        
        tk.Label(content_frame, text=f"Order #{self.order_id:04d}",
                font=('Helvetica', 12),
                bg='white').pack()
        
        # Size indicator
        tk.Label(content_frame, text=f"{self.selected_size.display_name}",
                font=('Helvetica', 10),
                bg='white', fg='gray').pack(pady=5)
        
        tk.Label(content_frame, text=f"Layout: {self.selected_layout.value}",
                font=('Helvetica', 10),
                bg='white', fg='gray').pack()
        
        # Sample content lines
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=10)
        
        for i in range(5):
            line_frame = tk.Frame(content_frame, bg='#e0e0e0', height=10)
            line_frame.pack(fill='x', pady=2, padx=20)
        
        # Footer
        tk.Label(content_frame, text="Powered by POS System",
                font=('Helvetica', 8),
                bg='white', fg='gray').pack(side='bottom', pady=10)
        
        # Update scroll region
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox('all'))
    
    def _save_as_default(self):
        """Save current selection as default"""
        try:
            from database import db
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Update settings
            cursor.execute("""
                UPDATE settings 
                SET default_bill_size = ?, default_bill_layout = ?
                WHERE id = 1
            """, (self.selected_size.name, self.selected_layout.value))
            
            conn.commit()
            
            messagebox.showinfo("Success", 
                              f"Default format set to {self.selected_size.display_name} - {self.selected_layout.value}")
            
        except Exception as e:
            logger.error(f"Error saving default settings: {e}")
            messagebox.showerror("Error", "Failed to save default settings")
    
    def _save_pdf(self):
        """Save the preview PDF to a custom location"""
        if not self.preview_path:
            messagebox.showwarning("Warning", "No preview generated yet")
            return
        
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"invoice_{self.order_id}_{self.selected_size.name.lower()}.pdf"
        )
        
        if filename:
            try:
                import shutil
                shutil.copy(self.preview_path, filename)
                messagebox.showinfo("Success", f"Invoice saved to {filename}")
            except Exception as e:
                logger.error(f"Error saving PDF: {e}")
                messagebox.showerror("Error", "Failed to save PDF")
    
    def _print_invoice(self):
        """Print the invoice with current settings"""
        if not self.preview_path:
            messagebox.showwarning("Warning", "No preview generated yet")
            return
        
        try:
            # Generate final invoice (not preview)
            final_path = self.generator.generate_invoice(
                self.order_id,
                bill_size=self.selected_size,
                layout_style=self.selected_layout,
                preview_only=False
            )
            
            # Open for printing
            if platform.system() == 'Windows':
                os.startfile(final_path, "print")
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['lpr', final_path])
            else:  # Linux
                subprocess.run(['lpr', final_path])
            
            messagebox.showinfo("Success", f"Invoice sent to printer")
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"Error printing invoice: {e}")
            messagebox.showerror("Print Error", f"Failed to print invoice: {str(e)}")
    
    def _load_default_settings(self):
        """Load default size and layout from settings"""
        try:
            from database import db
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT default_bill_size, default_bill_layout 
                FROM settings WHERE id = 1
            """)
            
            result = cursor.fetchone()
            if result:
                # Set default size if exists
                if 'default_bill_size' in result.keys() and result['default_bill_size']:
                    try:
                        default_size = BillSize[result['default_bill_size']]
                        index = list(BillSize).index(default_size)
                        self.size_combo.current(index)
                        self.selected_size = default_size
                    except (KeyError, ValueError):
                        pass
                
                # Set default layout if exists
                if 'default_bill_layout' in result.keys() and result['default_bill_layout']:
                    layout_map = {
                        'classic': 'Classic',
                        'minimal': 'Minimal',
                        'compact': 'Compact',
                        'detailed': 'Detailed'
                    }
                    if result['default_bill_layout'] in layout_map:
                        self.layout_combo.set(layout_map[result['default_bill_layout']])
                        self.selected_layout = LayoutStyle(result['default_bill_layout'])
        
        except Exception as e:
            logger.error(f"Error loading default settings: {e}")


def show_invoice_preview(parent, order_id: int, auth_manager):
    """Show invoice preview dialog"""
    dialog = InvoicePreviewDialog(parent, order_id, auth_manager)
    return dialog
