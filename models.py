"""
Data models and business logic for POS system
"""
import json
import logging
from datetime import datetime
from decimal import Decimal
from database import db

logger = logging.getLogger(__name__)

class OrderModel:
    def __init__(self):
        self.items = []
        self.tax_rate = Decimal('0')
        self.load_default_tax_rate()
    
    def load_default_tax_rate(self):
        """Load default tax rate from settings"""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT default_tax_rate FROM settings WHERE id = 1")
        result = cursor.fetchone()
        if result:
            self.tax_rate = Decimal(str(result['default_tax_rate']))
    
    def add_item(self, name, quantity, unit_price):
        """Add an item to the order"""
        if not name or len(name) > 128:
            raise ValueError("Item name must be 1-128 characters")
        
        quantity = Decimal(str(quantity))
        unit_price = Decimal(str(unit_price))
        
        if quantity <= 0 or quantity > 999999:
            raise ValueError("Quantity must be between 1 and 999,999")
        
        if unit_price < 0 or unit_price > Decimal('9999999.99'):
            raise ValueError("Unit price must be between 0 and 9,999,999.99")
        
        line_total = quantity * unit_price
        
        item = {
            'name': name,
            'quantity': float(quantity),
            'unit_price': float(unit_price),
            'line_total': float(line_total)
        }
        
        self.items.append(item)
        return item
    
    def remove_item(self, index):
        """Remove an item from the order"""
        if 0 <= index < len(self.items):
            del self.items[index]
    
    def update_item(self, index, name=None, quantity=None, unit_price=None):
        """Update an item in the order"""
        if 0 <= index < len(self.items):
            item = self.items[index]
            
            if name is not None:
                item['name'] = name
            
            if quantity is not None:
                quantity = Decimal(str(quantity))
                if quantity <= 0 or quantity > 999999:
                    raise ValueError("Quantity must be between 1 and 999,999")
                item['quantity'] = float(quantity)
            
            if unit_price is not None:
                unit_price = Decimal(str(unit_price))
                if unit_price < 0 or unit_price > Decimal('9999999.99'):
                    raise ValueError("Unit price must be between 0 and 9,999,999.99")
                item['unit_price'] = float(unit_price)
            
            # Recalculate line total
            item['line_total'] = item['quantity'] * item['unit_price']
    
    def clear_items(self):
        """Clear all items from the order"""
        self.items = []
    
    def get_subtotal(self):
        """Calculate subtotal of all items"""
        return sum(item['line_total'] for item in self.items)
    
    def get_tax_total(self):
        """Calculate tax amount"""
        subtotal = self.get_subtotal()
        return float(subtotal * float(self.tax_rate) / 100)
    
    def get_grand_total(self):
        """Calculate grand total including tax"""
        return self.get_subtotal() + self.get_tax_total()
    
    def set_tax_rate(self, rate):
        """Set tax rate for the order"""
        rate = Decimal(str(rate))
        if rate < 0 or rate > 100:
            raise ValueError("Tax rate must be between 0 and 100")
        self.tax_rate = rate
    
    def finalize_order(self, user_id, template_id=None):
        """Save order to database and return order ID"""
        if not self.items:
            raise ValueError("Cannot finalize an empty order")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get invoice template if not specified
            if template_id is None:
                cursor.execute("SELECT id FROM invoice_templates WHERE is_default = 1 LIMIT 1")
                result = cursor.fetchone()
                template_id = result['id'] if result else None
            
            # Create invoice snapshot
            snapshot = self.create_invoice_snapshot(template_id)
            
            # Insert order
            cursor.execute("""
                INSERT INTO orders (user_id, subtotal, tax_rate, tax_total, grand_total, 
                                  status, invoice_template_id, invoice_snapshot_json)
                VALUES (?, ?, ?, ?, ?, 'finalized', ?, ?)
            """, (
                user_id,
                self.get_subtotal(),
                float(self.tax_rate),
                self.get_tax_total(),
                self.get_grand_total(),
                template_id,
                json.dumps(snapshot)
            ))
            
            order_id = cursor.lastrowid
            
            # Insert order items
            for item in self.items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, name, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    order_id,
                    item['name'],
                    item['quantity'],
                    item['unit_price'],
                    item['line_total']
                ))
            
            conn.commit()
            logger.info(f"Order {order_id} finalized successfully")
            return order_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error finalizing order: {e}")
            raise
    
    def create_invoice_snapshot(self, template_id):
        """Create a snapshot of invoice data at finalization time"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get template data
        template_data = {}
        if template_id:
            cursor.execute("""
                SELECT name, header_json, footer_json, styles_json, business_info_json
                FROM invoice_templates WHERE id = ?
            """, (template_id,))
            
            result = cursor.fetchone()
            if result:
                template_data = {
                    'name': result['name'],
                    'header': json.loads(result['header_json'] or '{}'),
                    'footer': json.loads(result['footer_json'] or '{}'),
                    'styles': json.loads(result['styles_json'] or '{}'),
                    'business_info': json.loads(result['business_info_json'] or '{}')
                }
        
        # Get settings
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        
        snapshot = {
            'created_at': datetime.now().isoformat(),
            'items': self.items,
            'subtotal': self.get_subtotal(),
            'tax_rate': float(self.tax_rate),
            'tax_total': self.get_tax_total(),
            'grand_total': self.get_grand_total(),
            'template': template_data,
            'settings': {
                'currency_symbol': settings['currency_symbol'] if settings else '$',
                'locale': settings['locale'] if settings else 'en_US',
                'time_zone': settings['time_zone'] if settings else 'UTC',
                'page_size': settings['page_size'] if settings else 'A4'
            }
        }
        
        return snapshot


class FrequentOrderModel:
    @staticmethod
    def create(label, items, owner_user_id=None):
        """Create a new frequent order template"""
        if not label:
            raise ValueError("Label is required")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO frequent_orders (label, owner_user_id, items_json, active)
                VALUES (?, ?, ?, 1)
            """, (label, owner_user_id, json.dumps(items)))
            
            conn.commit()
            logger.info(f"Created frequent order: {label}")
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error creating frequent order: {e}")
            raise
    
    @staticmethod
    def get_all(user_id=None, include_global=True):
        """Get all frequent orders available to a user"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, label, owner_user_id, items_json, active
            FROM frequent_orders
            WHERE active = 1
        """
        
        params = []
        
        if user_id and include_global:
            query += " AND (owner_user_id = ? OR owner_user_id IS NULL)"
            params.append(user_id)
        elif user_id:
            query += " AND owner_user_id = ?"
            params.append(user_id)
        elif include_global:
            query += " AND owner_user_id IS NULL"
        
        query += " ORDER BY label"
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'label': row['label'],
                'is_global': row['owner_user_id'] is None,
                'items': json.loads(row['items_json'])
            })
        
        return results
    
    @staticmethod
    def get_by_id(frequent_order_id):
        """Get a specific frequent order by ID"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, label, owner_user_id, items_json
            FROM frequent_orders
            WHERE id = ? AND active = 1
        """, (frequent_order_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'label': row['label'],
                'is_global': row['owner_user_id'] is None,
                'items': json.loads(row['items_json'])
            }
        return None
    
    @staticmethod
    def update(frequent_order_id, label=None, items=None):
        """Update a frequent order"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if label is not None:
            updates.append("label = ?")
            params.append(label)
        
        if items is not None:
            updates.append("items_json = ?")
            params.append(json.dumps(items))
        
        if updates:
            params.append(frequent_order_id)
            query = f"UPDATE frequent_orders SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            logger.info(f"Updated frequent order {frequent_order_id}")
    
    @staticmethod
    def delete(frequent_order_id):
        """Soft delete a frequent order"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE frequent_orders SET active = 0 WHERE id = ?
        """, (frequent_order_id,))
        
        conn.commit()
        logger.info(f"Deleted frequent order {frequent_order_id}")


class OrderHistoryModel:
    @staticmethod
    def get_orders(user_id=None, start_date=None, end_date=None, status=None, limit=1000):
        """Get orders with filters"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE 1=1
        """
        
        params = []
        
        if user_id:
            query += " AND o.user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND o.created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND o.created_at <= ?"
            params.append(end_date)
        
        if status:
            query += " AND o.status = ?"
            params.append(status)
        
        query += " ORDER BY o.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    @staticmethod
    def get_order_details(order_id):
        """Get complete order details including items"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get order
        cursor.execute("""
            SELECT o.*, u.username
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return None
        
        # Get items
        cursor.execute("""
            SELECT * FROM order_items WHERE order_id = ?
        """, (order_id,))
        
        items = cursor.fetchall()
        
        return {
            'order': dict(order),
            'items': [dict(item) for item in items]
        }
    
    @staticmethod
    def cancel_order(order_id):
        """Cancel an order (admin only)"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE orders SET status = 'canceled' WHERE id = ? AND status = 'finalized'
        """, (order_id,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Order {order_id} canceled")
            return True
        return False
