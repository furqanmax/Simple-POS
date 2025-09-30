"""
Test Data Generator for POS System
Generates sample data for testing dashboard features
"""
import sqlite3
from datetime import datetime, timedelta
import random
import json
from database import db
from auth import hash_password

def generate_test_data():
    """Generate comprehensive test data for all features"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("🔄 Generating test data...")
    
    # 1. Create test users
    print("Creating test users...")
    test_users = [
        ('cashier1', 'pass123', 'user'),
        ('cashier2', 'pass123', 'user'),
        ('manager', 'pass123', 'admin')
    ]
    
    for username, password, role in test_users:
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, active)
                VALUES (?, ?, ?, 1)
            """, (username, hash_password(password), role))
        except:
            pass  # User might already exist
    
    # Get user IDs
    cursor.execute("SELECT id, username FROM users")
    users = {row['username']: row['id'] for row in cursor.fetchall()}
    
    # 2. Generate orders for the last 30 days
    print("Generating orders...")
    items_pool = [
        ('Coffee', 50.00), ('Tea', 30.00), ('Sandwich', 80.00),
        ('Pizza', 250.00), ('Burger', 150.00), ('Pasta', 180.00),
        ('Salad', 120.00), ('Juice', 60.00), ('Cake', 100.00),
        ('Ice Cream', 70.00), ('Soup', 90.00), ('Noodles', 110.00)
    ]
    
    now = datetime.now()
    for days_ago in range(30):
        date = now - timedelta(days=days_ago)
        
        # Generate 5-20 orders per day
        num_orders = random.randint(5, 20)
        
        for _ in range(num_orders):
            # Random time of day
            hour = random.randint(8, 22)
            minute = random.randint(0, 59)
            order_time = date.replace(hour=hour, minute=minute, second=0)
            
            # Random user
            user_id = random.choice(list(users.values()))
            
            # Random number of items (1-5)
            num_items = random.randint(1, 5)
            order_items = []
            subtotal = 0
            
            for _ in range(num_items):
                item_name, base_price = random.choice(items_pool)
                quantity = random.randint(1, 3)
                unit_price = base_price * (1 + random.uniform(-0.1, 0.1))  # ±10% variation
                line_total = quantity * unit_price
                subtotal += line_total
                
                order_items.append({
                    'name': item_name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'line_total': line_total
                })
            
            # Calculate tax and total
            tax_rate = random.choice([5, 8, 10, 12, 18])  # Different tax rates
            tax_total = subtotal * tax_rate / 100
            grand_total = subtotal + tax_total
            
            # Insert order
            cursor.execute("""
                INSERT INTO orders (user_id, subtotal, tax_rate, tax_total, grand_total,
                                  status, created_at, invoice_template_id, invoice_snapshot_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                user_id, subtotal, tax_rate, tax_total, grand_total,
                'finalized', order_time.isoformat(),
                json.dumps({'items': order_items, 'created_at': order_time.isoformat()})
            ))
            
            order_id = cursor.lastrowid
            
            # Insert order items
            for item in order_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, name, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, item['name'], item['quantity'], 
                     item['unit_price'], item['line_total']))
    
    # 3. Generate installments
    print("Generating installments...")
    customers = [
        ('Raj Kumar', '9876543210'),
        ('Priya Sharma', '9876543211'),
        ('Amit Patel', '9876543212'),
        ('Sneha Gupta', '9876543213'),
        ('Vikram Singh', '9876543214'),
        ('Anjali Mehta', '9876543215'),
        ('Rahul Verma', '9876543216'),
        ('Pooja Reddy', '9876543217')
    ]
    
    for i in range(15):
        customer_name, phone = random.choice(customers)
        amount = random.uniform(500, 5000)
        
        # Due dates: some overdue, some upcoming
        if i < 3:  # Overdue
            due_date = now - timedelta(days=random.randint(1, 10))
            status = 'pending'  # Will show as overdue in dashboard
        elif i < 8:  # Due this week
            due_date = now + timedelta(days=random.randint(1, 7))
            status = 'pending'
        else:  # Already paid or future
            due_date = now + timedelta(days=random.randint(8, 30))
            status = random.choice(['pending', 'paid'])
        
        paid_date = None
        if status == 'paid':
            paid_date = (due_date - timedelta(days=random.randint(1, 5))).isoformat()
        
        cursor.execute("""
            INSERT INTO installments (customer_name, customer_phone, amount, 
                                    due_date, paid_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (customer_name, phone, amount, due_date.isoformat(), 
             paid_date, status, f"Installment for order"))
    
    # 4. Generate frequent order templates
    print("Generating frequent order templates...")
    templates = [
        ('Morning Combo', [{'name': 'Coffee', 'quantity': 2, 'unit_price': 50},
                          {'name': 'Sandwich', 'quantity': 1, 'unit_price': 80}]),
        ('Lunch Special', [{'name': 'Pizza', 'quantity': 1, 'unit_price': 250},
                          {'name': 'Juice', 'quantity': 2, 'unit_price': 60}]),
        ('Tea Break', [{'name': 'Tea', 'quantity': 3, 'unit_price': 30},
                      {'name': 'Cake', 'quantity': 2, 'unit_price': 100}]),
        ('Family Pack', [{'name': 'Burger', 'quantity': 4, 'unit_price': 150},
                        {'name': 'Ice Cream', 'quantity': 4, 'unit_price': 70}])
    ]
    
    for label, items in templates:
        try:
            cursor.execute("""
                INSERT INTO frequent_orders (label, owner_user_id, items_json, active)
                VALUES (?, NULL, ?, 1)
            """, (label, json.dumps(items)))
        except:
            pass  # Template might already exist
    
    # 5. Add subscription data
    print("Adding subscription data...")
    try:
        end_date = now + timedelta(days=45)
        cursor.execute("""
            INSERT INTO subscription (plan_name, end_date, features_json)
            VALUES (?, ?, ?)
        """, ('Premium', end_date.isoformat(), 
             json.dumps(['Unlimited Users', 'Advanced Analytics', 
                        'Priority Support', 'Custom Reports'])))
    except:
        pass  # Subscription might already exist
    
    conn.commit()
    print("✅ Test data generated successfully!")
    
    # Print summary
    cursor.execute("SELECT COUNT(*) as count FROM orders")
    order_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM installments WHERE status = 'pending'")
    pending_installments = cursor.fetchone()['count']
    
    print(f"\n📊 Summary:")
    print(f"  - Total Orders: {order_count}")
    print(f"  - Pending Installments: {pending_installments}")
    print(f"  - Active Users: {len(users)}")
    print(f"  - Frequent Order Templates: {len(templates)}")

if __name__ == "__main__":
    generate_test_data()
