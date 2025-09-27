"""
Authentication and authorization module for POS system
"""
import bcrypt
import logging
from database import db

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.current_user = None
    
    def hash_password(self, password):
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed):
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def login(self, username, password):
        """Authenticate user and return user info if successful"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, password_hash, role, active
            FROM users
            WHERE username = ? AND active = 1
        """, (username,))
        
        user = cursor.fetchone()
        
        if user and self.verify_password(password, user['password_hash']):
            self.current_user = {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
            logger.info(f"User {username} logged in successfully")
            return self.current_user
        
        logger.warning(f"Failed login attempt for username: {username}")
        return None
    
    def logout(self):
        """Clear current user session"""
        self.current_user = None
        logger.info("User logged out")
    
    def is_admin(self):
        """Check if current user is admin"""
        return self.current_user and self.current_user['role'] == 'admin'
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def get_current_user(self):
        """Get current user info"""
        return self.current_user
    
    def create_user(self, username, password, role='user'):
        """Create a new user (admin only)"""
        if not self.is_admin():
            raise PermissionError("Only admins can create users")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, active)
                VALUES (?, ?, ?, 1)
            """, (username, password_hash, role))
            conn.commit()
            logger.info(f"Created new user: {username} with role: {role}")
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def update_user_status(self, user_id, active):
        """Activate or deactivate a user"""
        if not self.is_admin():
            raise PermissionError("Only admins can modify user status")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET active = ? WHERE id = ?
        """, (active, user_id))
        conn.commit()
        
        status = "activated" if active else "deactivated"
        logger.info(f"User {user_id} {status}")
    
    def change_password(self, user_id, new_password):
        """Change user password"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(new_password)
        cursor.execute("""
            UPDATE users SET password_hash = ? WHERE id = ?
        """, (password_hash, user_id))
        conn.commit()
        logger.info(f"Password changed for user {user_id}")
    
    def get_all_users(self):
        """Get all users (admin only)"""
        if not self.is_admin():
            raise PermissionError("Only admins can view all users")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, role, active, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        
        return cursor.fetchall()

# Helper function for backward compatibility
def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Global auth manager instance
auth_manager = AuthManager()
