"""
Dashboard module for POS System
Comprehensive dashboard with role-aware cards, charts, and analytics
"""
import tkinter as tk
from tkinter import ttk, messagebox, font
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import json
from database import db
from invoice_generator import InvoiceGenerator
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import os
import subprocess
import platform

logger = logging.getLogger(__name__)


class DashboardTab:
    """Dashboard tab with comprehensive analytics and insights"""
    
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.invoice_generator = InvoiceGenerator()
        self.frame = ttk.Frame(parent)
        
        # Date range filters
        self.date_range = 'today'  # today, week, month, custom
        self.start_date = None
        self.end_date = None
        
        # Cache for performance
        self.data_cache = {}
        self.last_refresh = None
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """Create dashboard widgets"""
        # Main container with scrollbar
        canvas = tk.Canvas(self.frame, bg='white')
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main dashboard container
        main_container = ttk.Frame(scrollable_frame, padding="15")
        main_container.pack(fill='both', expand=True)
        
        # Header with title and date filter
        self._create_header(main_container)
        
        # Key metrics cards row
        self._create_metrics_cards(main_container)
        
        # Charts row
        self._create_charts_row(main_container)
        
        # Tables row (Recent Orders and Installments Due)
        self._create_tables_row(main_container)
        
        # Admin insights section (if admin)
        if self.auth_manager.is_admin():
            self._create_admin_insights(main_container)
        
        # Subscription status (bottom)
        self._create_subscription_status(main_container)
    
    def _create_header(self, parent):
        """Create dashboard header with filters"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Title
        title_font = font.Font(family="Helvetica", size=20, weight="bold")
        ttk.Label(header_frame, text="📊 Dashboard", font=title_font).pack(side='left', padx=(0, 20))
        
        # Date range filters
        filter_frame = ttk.Frame(header_frame)
        filter_frame.pack(side='right')
        
        ttk.Label(filter_frame, text="Period:").pack(side='left', padx=(0, 5))
        
        # Quick filter buttons
        self.today_btn = ttk.Button(filter_frame, text="Today", 
                                    command=lambda: self.set_date_range('today'))
        self.today_btn.pack(side='left', padx=2)
        
        self.week_btn = ttk.Button(filter_frame, text="7 Days", 
                                   command=lambda: self.set_date_range('week'))
        self.week_btn.pack(side='left', padx=2)
        
        self.month_btn = ttk.Button(filter_frame, text="30 Days", 
                                    command=lambda: self.set_date_range('month'))
        self.month_btn.pack(side='left', padx=2)
        
        # Refresh button
        ttk.Button(filter_frame, text="🔄 Refresh", 
                  command=self.refresh).pack(side='left', padx=(10, 0))
    
    def _create_metrics_cards(self, parent):
        """Create key metrics cards"""
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(fill='x', pady=(0, 15))
        
        # Configure grid
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)
        
        # Today's Orders Card
        self.orders_card = self._create_metric_card(
            cards_frame, "📦 Today's Orders", "0", "orders", 
            row=0, column=0, color='#3498db'
        )
        
        # Today's Revenue Card
        self.revenue_card = self._create_metric_card(
            cards_frame, "💰 Today's Revenue", "₹0.00", "revenue",
            row=0, column=1, color='#2ecc71'
        )
        
        # Active Users Card
        self.users_card = self._create_metric_card(
            cards_frame, "👥 Active Users", "0", "users",
            row=0, column=2, color='#9b59b6'
        )
        
        # Pending Installments Card
        self.installments_card = self._create_metric_card(
            cards_frame, "⏰ Due This Week", "0", "installments",
            row=0, column=3, color='#e74c3c'
        )
    
    def _create_metric_card(self, parent, title, value, card_id, row, column, color='#3498db'):
        """Create a single metric card"""
        card_frame = tk.Frame(parent, bg='white', relief='raised', bd=1)
        card_frame.grid(row=row, column=column, padx=5, pady=5, sticky='ew')
        
        # Inner padding
        inner_frame = tk.Frame(card_frame, bg='white')
        inner_frame.pack(padx=15, pady=15, fill='both', expand=True)
        
        # Title
        title_label = tk.Label(inner_frame, text=title, font=('Helvetica', 10), 
                              bg='white', fg='#7f8c8d')
        title_label.pack(anchor='w')
        
        # Value
        value_label = tk.Label(inner_frame, text=value, font=('Helvetica', 24, 'bold'),
                              bg='white', fg=color)
        value_label.pack(anchor='w', pady=(5, 0))
        
        # Store references for updates
        setattr(self, f"{card_id}_title_label", title_label)
        setattr(self, f"{card_id}_value_label", value_label)
        
        # Trend indicator (if applicable)
        if card_id in ['orders', 'revenue']:
            trend_label = tk.Label(inner_frame, text="", font=('Helvetica', 9),
                                  bg='white', fg='#95a5a6')
            trend_label.pack(anchor='w')
            setattr(self, f"{card_id}_trend_label", trend_label)
        
        return card_frame
    
    def _create_charts_row(self, parent):
        """Create charts row with revenue trend and order distribution"""
        charts_frame = ttk.Frame(parent)
        charts_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Revenue Trend Chart (Left)
        trend_frame = ttk.LabelFrame(charts_frame, text="📈 Revenue Trend (Last 7 Days)", 
                                     padding="10")
        trend_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.trend_figure = Figure(figsize=(6, 3), dpi=80)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_figure, trend_frame)
        self.trend_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Order Distribution Chart (Right) 
        dist_frame = ttk.LabelFrame(charts_frame, text="🍰 Order Distribution", 
                                    padding="10")
        dist_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self.dist_figure = Figure(figsize=(4, 3), dpi=80)
        self.dist_canvas = FigureCanvasTkAgg(self.dist_figure, dist_frame)
        self.dist_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_tables_row(self, parent):
        """Create tables for recent orders and pending installments"""
        tables_frame = ttk.Frame(parent)
        tables_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Recent Orders Table (Left)
        orders_frame = ttk.LabelFrame(tables_frame, text="📋 Recent Orders", padding="10")
        orders_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Orders tree
        columns = ('ID', 'Time', 'User', 'Total', 'Status')
        self.orders_tree = ttk.Treeview(orders_frame, columns=columns, show='headings', 
                                        height=8)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            if col == 'ID':
                self.orders_tree.column(col, width=60)
            elif col == 'Time':
                self.orders_tree.column(col, width=80)
            elif col == 'User':
                self.orders_tree.column(col, width=80)
            elif col == 'Total':
                self.orders_tree.column(col, width=80)
            else:
                self.orders_tree.column(col, width=70)
        
        self.orders_tree.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for orders
        orders_scroll = ttk.Scrollbar(orders_frame, orient='vertical', 
                                      command=self.orders_tree.yview)
        orders_scroll.pack(side='right', fill='y')
        self.orders_tree.configure(yscrollcommand=orders_scroll.set)
        
        # Quick print button
        ttk.Button(orders_frame, text="🖨️ Print Selected", 
                  command=self.quick_print_invoice).pack(pady=(5, 0))
        
        # Installments Due Table (Right)
        installments_frame = ttk.LabelFrame(tables_frame, text="💳 Installments Due", 
                                           padding="10")
        installments_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Installments tree
        inst_columns = ('Customer', 'Amount', 'Due Date', 'Status')
        self.installments_tree = ttk.Treeview(installments_frame, columns=inst_columns, 
                                              show='headings', height=8)
        
        for col in inst_columns:
            self.installments_tree.heading(col, text=col)
            if col == 'Customer':
                self.installments_tree.column(col, width=100)
            else:
                self.installments_tree.column(col, width=80)
        
        self.installments_tree.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for installments
        inst_scroll = ttk.Scrollbar(installments_frame, orient='vertical',
                                    command=self.installments_tree.yview)
        inst_scroll.pack(side='right', fill='y')
        self.installments_tree.configure(yscrollcommand=inst_scroll.set)
        
        # Mark as paid button
        ttk.Button(installments_frame, text="✅ Mark Paid", 
                  command=self.mark_installment_paid).pack(pady=(5, 0))
    
    def _create_admin_insights(self, parent):
        """Create admin-only insights section"""
        insights_frame = ttk.LabelFrame(parent, text="🔍 Admin Insights", padding="15")
        insights_frame.pack(fill='x', pady=(0, 15))
        
        # Create 2 columns for insights
        left_col = ttk.Frame(insights_frame)
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        right_col = ttk.Frame(insights_frame)
        right_col.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Average Order Value
        avg_frame = tk.Frame(left_col, bg='#f8f9fa', relief='flat', bd=1)
        avg_frame.pack(fill='x', pady=5)
        tk.Label(avg_frame, text="Average Order Value:", font=('Helvetica', 10),
                bg='#f8f9fa').pack(side='left', padx=10, pady=5)
        self.avg_order_label = tk.Label(avg_frame, text="₹0.00", 
                                        font=('Helvetica', 12, 'bold'),
                                        bg='#f8f9fa', fg='#27ae60')
        self.avg_order_label.pack(side='right', padx=10, pady=5)
        
        # Top Selling Items
        top_frame = tk.Frame(left_col, bg='#f8f9fa', relief='flat', bd=1)
        top_frame.pack(fill='x', pady=5)
        tk.Label(top_frame, text="Top Selling Items:", font=('Helvetica', 10),
                bg='#f8f9fa').pack(anchor='w', padx=10, pady=(5, 0))
        self.top_items_label = tk.Label(top_frame, text="Loading...", 
                                        font=('Helvetica', 9),
                                        bg='#f8f9fa', fg='#34495e', justify='left')
        self.top_items_label.pack(anchor='w', padx=10, pady=(0, 5))
        
        # Peak Hours
        peak_frame = tk.Frame(right_col, bg='#f8f9fa', relief='flat', bd=1)
        peak_frame.pack(fill='x', pady=5)
        tk.Label(peak_frame, text="Peak Hours:", font=('Helvetica', 10),
                bg='#f8f9fa').pack(side='left', padx=10, pady=5)
        self.peak_hours_label = tk.Label(peak_frame, text="Loading...", 
                                         font=('Helvetica', 10, 'bold'),
                                         bg='#f8f9fa', fg='#e67e22')
        self.peak_hours_label.pack(side='right', padx=10, pady=5)
        
        # Frequent Order Labels
        freq_frame = tk.Frame(right_col, bg='#f8f9fa', relief='flat', bd=1)
        freq_frame.pack(fill='x', pady=5)
        tk.Label(freq_frame, text="Most Used Templates:", font=('Helvetica', 10),
                bg='#f8f9fa').pack(anchor='w', padx=10, pady=(5, 0))
        self.freq_labels_label = tk.Label(freq_frame, text="Loading...", 
                                          font=('Helvetica', 9),
                                          bg='#f8f9fa', fg='#34495e', justify='left')
        self.freq_labels_label.pack(anchor='w', padx=10, pady=(0, 5))
    
    def _create_subscription_status(self, parent):
        """Create subscription status section"""
        sub_frame = ttk.LabelFrame(parent, text="📅 Subscription Status", padding="10")
        sub_frame.pack(fill='x')
        
        # Subscription info
        info_frame = ttk.Frame(sub_frame)
        info_frame.pack(fill='x')
        
        # Plan name
        plan_frame = ttk.Frame(info_frame)
        plan_frame.pack(side='left', padx=(0, 20))
        ttk.Label(plan_frame, text="Current Plan:", font=('Helvetica', 10)).pack(side='left')
        self.plan_label = ttk.Label(plan_frame, text="Premium", 
                                    font=('Helvetica', 10, 'bold'))
        self.plan_label.pack(side='left', padx=(5, 0))
        
        # Days remaining
        days_frame = ttk.Frame(info_frame)
        days_frame.pack(side='left', padx=(0, 20))
        ttk.Label(days_frame, text="Days Remaining:", font=('Helvetica', 10)).pack(side='left')
        self.days_label = ttk.Label(days_frame, text="30", 
                                    font=('Helvetica', 10, 'bold'))
        self.days_label.pack(side='left', padx=(5, 0))
        
        # Status
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(side='left')
        ttk.Label(status_frame, text="Status:", font=('Helvetica', 10)).pack(side='left')
        self.status_label = ttk.Label(status_frame, text="Active", 
                                      font=('Helvetica', 10, 'bold'))
        self.status_label.pack(side='left', padx=(5, 0))
        
        # Renew button (admin only)
        if self.auth_manager.is_admin():
            ttk.Button(info_frame, text="Renew Subscription", 
                      command=self.renew_subscription).pack(side='right')
    
    def set_date_range(self, range_type):
        """Set date range for filtering"""
        self.date_range = range_type
        now = datetime.now()
        
        if range_type == 'today':
            self.start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self.end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif range_type == 'week':
            self.start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
            self.end_date = now.replace(hour=23, minute=59, second=59)
        elif range_type == 'month':
            self.start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
            self.end_date = now.replace(hour=23, minute=59, second=59)
        
        self.refresh()
    
    def refresh(self):
        """Refresh all dashboard data"""
        try:
            # Set default date range if not set
            if not self.start_date:
                self.set_date_range('today')
                return
            
            # Update metrics
            self.update_metrics()
            
            # Update charts
            self.update_charts()
            
            # Update tables
            self.update_tables()
            
            # Update admin insights if admin
            if self.auth_manager.is_admin():
                self.update_admin_insights()
            
            # Update subscription status
            self.update_subscription_status()
            
            self.last_refresh = datetime.now()
            
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}")
            messagebox.showerror("Error", f"Failed to refresh dashboard: {str(e)}")
    
    def update_metrics(self):
        """Update metric cards with latest data"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Today's orders and revenue
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)
        
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(grand_total), 0) as revenue
            FROM orders
            WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
        """, (today_start.isoformat(), today_end.isoformat()))
        
        today_data = cursor.fetchone()
        self.orders_value_label.config(text=str(today_data['count']))
        self.revenue_value_label.config(text=f"₹{today_data['revenue']:.2f}")
        
        # Calculate trend (vs yesterday)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_end - timedelta(days=1)
        
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(grand_total), 0) as revenue
            FROM orders
            WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
        """, (yesterday_start.isoformat(), yesterday_end.isoformat()))
        
        yesterday_data = cursor.fetchone()
        
        # Calculate trends
        if yesterday_data['count'] > 0:
            order_trend = ((today_data['count'] - yesterday_data['count']) / 
                          yesterday_data['count'] * 100)
            self.orders_trend_label.config(
                text=f"{'↑' if order_trend >= 0 else '↓'} {abs(order_trend):.1f}% vs yesterday",
                fg='#27ae60' if order_trend >= 0 else '#e74c3c'
            )
        
        if yesterday_data['revenue'] > 0:
            revenue_trend = ((today_data['revenue'] - yesterday_data['revenue']) / 
                           yesterday_data['revenue'] * 100)
            self.revenue_trend_label.config(
                text=f"{'↑' if revenue_trend >= 0 else '↓'} {abs(revenue_trend):.1f}% vs yesterday",
                fg='#27ae60' if revenue_trend >= 0 else '#e74c3c'
            )
        
        # Active users count
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE active = 1")
        users_count = cursor.fetchone()['count']
        self.users_value_label.config(text=str(users_count))
        
        # Pending installments this week
        week_end = datetime.now() + timedelta(days=7)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM installments
            WHERE due_date <= ? AND status = 'pending'
        """, (week_end.isoformat(),))
        
        result = cursor.fetchone()
        installments_count = result['count'] if result else 0
        self.installments_value_label.config(text=str(installments_count))
    
    def update_charts(self):
        """Update revenue trend and order distribution charts"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Revenue Trend Chart (Last 7 days)
        self.trend_figure.clear()
        ax = self.trend_figure.add_subplot(111)
        
        dates = []
        revenues = []
        
        for i in range(6, -1, -1):
            date = datetime.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0)
            date_end = date.replace(hour=23, minute=59, second=59)
            
            cursor.execute("""
                SELECT COALESCE(SUM(grand_total), 0) as revenue
                FROM orders
                WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
            """, (date_start.isoformat(), date_end.isoformat()))
            
            revenue = cursor.fetchone()['revenue']
            dates.append(date.strftime('%a'))
            revenues.append(float(revenue))
        
        ax.plot(dates, revenues, marker='o', linestyle='-', color='#3498db', linewidth=2)
        ax.fill_between(range(len(dates)), revenues, alpha=0.3, color='#3498db')
        ax.set_xlabel('Day', fontsize=9)
        ax.set_ylabel('Revenue (₹)', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', labelsize=8)
        
        self.trend_figure.tight_layout()
        self.trend_canvas.draw()
        
        # Order Distribution Pie Chart
        self.dist_figure.clear()
        ax2 = self.dist_figure.add_subplot(111)
        
        # Get order distribution by hour
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN strftime('%H', created_at) < '12' THEN 'Morning'
                    WHEN strftime('%H', created_at) < '17' THEN 'Afternoon'
                    WHEN strftime('%H', created_at) < '21' THEN 'Evening'
                    ELSE 'Night'
                END as period,
                COUNT(*) as count
            FROM orders
            WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
            GROUP BY period
        """, (self.start_date.isoformat(), self.end_date.isoformat()))
        
        distribution = cursor.fetchall()
        
        if distribution:
            labels = [d['period'] for d in distribution]
            sizes = [d['count'] for d in distribution]
            colors = ['#3498db', '#2ecc71', '#f39c12', '#9b59b6']
            
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                   startangle=90, textprops={'fontsize': 9})
            ax2.axis('equal')
        else:
            ax2.text(0.5, 0.5, 'No data available', ha='center', va='center',
                    transform=ax2.transAxes, fontsize=10)
        
        self.dist_figure.tight_layout()
        self.dist_canvas.draw()
    
    def update_tables(self):
        """Update recent orders and installments tables"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing data
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        for item in self.installments_tree.get_children():
            self.installments_tree.delete(item)
        
        # Recent orders
        cursor.execute("""
            SELECT o.id, o.created_at, u.username, o.grand_total, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.created_at BETWEEN ? AND ?
            ORDER BY o.created_at DESC
            LIMIT 10
        """, (self.start_date.isoformat(), self.end_date.isoformat()))
        
        for order in cursor.fetchall():
            time_str = datetime.fromisoformat(order['created_at']).strftime('%H:%M')
            self.orders_tree.insert('', 'end', values=(
                f"#{order['id']:04d}",
                time_str,
                order['username'],
                f"₹{order['grand_total']:.2f}",
                order['status'].upper()
            ))
        
        # Installments due - check if table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='installments'")
        if cursor.fetchone():
            week_end = datetime.now() + timedelta(days=7)
            cursor.execute("""
                SELECT * FROM installments
                WHERE due_date <= ? AND status = 'pending'
                ORDER BY due_date
                LIMIT 10
            """, (week_end.isoformat(),))
            
            for inst in cursor.fetchall():
                due_date = datetime.fromisoformat(inst['due_date']).strftime('%m/%d')
                self.installments_tree.insert('', 'end', values=(
                    inst['customer_name'],
                    f"₹{inst['amount']:.2f}",
                    due_date,
                    inst['status'].upper()
                ), tags=('overdue',) if datetime.fromisoformat(inst['due_date']) < datetime.now() else ())
            
            # Color overdue items
            self.installments_tree.tag_configure('overdue', foreground='red')
    
    def update_admin_insights(self):
        """Update admin-only insights"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Average order value
        cursor.execute("""
            SELECT AVG(grand_total) as avg_value
            FROM orders
            WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
        """, (self.start_date.isoformat(), self.end_date.isoformat()))
        
        avg_value = cursor.fetchone()['avg_value'] or 0
        self.avg_order_label.config(text=f"₹{avg_value:.2f}")
        
        # Top selling items
        cursor.execute("""
            SELECT oi.name, SUM(oi.quantity) as total_qty
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at BETWEEN ? AND ? AND o.status = 'finalized'
            GROUP BY oi.name
            ORDER BY total_qty DESC
            LIMIT 3
        """, (self.start_date.isoformat(), self.end_date.isoformat()))
        
        top_items = cursor.fetchall()
        if top_items:
            items_text = '\n'.join([f"• {item['name']} ({int(item['total_qty'])})" for item in top_items])
            self.top_items_label.config(text=items_text)
        else:
            self.top_items_label.config(text="No data available")
        
        # Peak hours
        cursor.execute("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as count
            FROM orders
            WHERE created_at BETWEEN ? AND ? AND status = 'finalized'
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 1
        """, (self.start_date.isoformat(), self.end_date.isoformat()))
        
        peak = cursor.fetchone()
        if peak:
            hour = int(peak['hour'])
            self.peak_hours_label.config(text=f"{hour:02d}:00 - {(hour+1):02d}:00")
        else:
            self.peak_hours_label.config(text="No data")
        
        # Most used templates
        cursor.execute("""
            SELECT label, COUNT(*) as usage_count
            FROM frequent_orders
            WHERE active = 1
            GROUP BY label
            ORDER BY usage_count DESC
            LIMIT 3
        """)
        
        freq_templates = cursor.fetchall()
        if freq_templates:
            templates_text = '\n'.join([f"• {t['label']}" for t in freq_templates])
            self.freq_labels_label.config(text=templates_text)
        else:
            self.freq_labels_label.config(text="No templates found")
    
    def update_subscription_status(self):
        """Update subscription status display"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if subscription table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscription'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT * FROM subscription
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            subscription = cursor.fetchone()
            if subscription:
                self.plan_label.config(text=subscription['plan_name'])
                
                # Calculate days remaining
                end_date = datetime.fromisoformat(subscription['end_date'])
                days_remaining = (end_date - datetime.now()).days
                self.days_label.config(text=str(max(0, days_remaining)))
                
                # Set status
                status = "Active" if days_remaining > 0 else "Expired"
                self.status_label.config(
                    text=status,
                    foreground='green' if status == "Active" else 'red'
                )
            else:
                # Default values if no subscription
                self.plan_label.config(text="Trial")
                self.days_label.config(text="30")
                self.status_label.config(text="Active", foreground='green')
        else:
            # Default values if table doesn't exist
            self.plan_label.config(text="Premium")
            self.days_label.config(text="∞")
            self.status_label.config(text="Active", foreground='green')
    
    def quick_print_invoice(self):
        """Quick print selected invoice"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an order to print")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = int(item['values'][0].replace('#', ''))
        
        try:
            # Generate invoice
            pdf_path = self.invoice_generator.generate_invoice(order_id, use_snapshot=True)
            
            # Open PDF
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
    
    def mark_installment_paid(self):
        """Mark selected installment as paid"""
        selection = self.installments_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an installment")
            return
        
        item = self.installments_tree.item(selection[0])
        customer = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Mark installment for {customer} as paid?"):
            # Update in database
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE installments
                SET status = 'paid', paid_date = ?
                WHERE customer_name = ? AND status = 'pending'
                LIMIT 1
            """, (datetime.now().isoformat(), customer))
            
            conn.commit()
            
            messagebox.showinfo("Success", "Installment marked as paid")
            self.refresh()
    
    def renew_subscription(self):
        """Renew subscription (admin only)"""
        if not self.auth_manager.is_admin():
            messagebox.showerror("Error", "Admin access required")
            return
        
        # Create renewal dialog
        dialog = tk.Toplevel(self.frame)
        dialog.title("Renew Subscription")
        dialog.geometry("400x300")
        
        # Plan selection
        ttk.Label(dialog, text="Select Plan:", font=('Helvetica', 10)).pack(pady=10)
        
        plan_var = tk.StringVar(value="Premium")
        plans = [
            ("Basic - ₹999/month", "Basic"),
            ("Premium - ₹2999/month", "Premium"),
            ("Enterprise - ₹9999/month", "Enterprise")
        ]
        
        for text, value in plans:
            ttk.Radiobutton(dialog, text=text, variable=plan_var, value=value).pack(pady=5)
        
        # Duration selection
        ttk.Label(dialog, text="Duration:", font=('Helvetica', 10)).pack(pady=10)
        
        duration_var = tk.IntVar(value=30)
        durations = [
            ("1 Month (30 days)", 30),
            ("3 Months (90 days)", 90),
            ("6 Months (180 days)", 180),
            ("1 Year (365 days)", 365)
        ]
        
        for text, value in durations:
            ttk.Radiobutton(dialog, text=text, variable=duration_var, value=value).pack(pady=5)
        
        def confirm_renewal():
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Create subscription table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscription (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_name TEXT NOT NULL,
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert new subscription
            end_date = datetime.now() + timedelta(days=duration_var.get())
            cursor.execute("""
                INSERT INTO subscription (plan_name, end_date)
                VALUES (?, ?)
            """, (plan_var.get(), end_date.isoformat()))
            
            conn.commit()
            
            dialog.destroy()
            messagebox.showinfo("Success", f"Subscription renewed: {plan_var.get()} plan for {duration_var.get()} days")
            self.refresh()
        
        ttk.Button(dialog, text="Confirm Renewal", command=confirm_renewal).pack(pady=20)
    
    def get_frame(self):
        """Return the frame for this tab"""
        return self.frame
