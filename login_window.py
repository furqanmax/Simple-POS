"""
Login window for POS system
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class LoginWindow:
    def __init__(self, auth_manager, on_success_callback):
        self.auth_manager = auth_manager
        self.on_success_callback = on_success_callback
        
        self.root = tk.Tk()
        self.root.title("POS System - Login")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self._create_widgets()
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self.login())
        
        # Focus on username field
        self.username_entry.focus()
    
    def _create_widgets(self):
        """Create login form widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="POS System Login",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30))
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(
            row=1, column=0, sticky=tk.E, padx=(0, 10), pady=5
        )
        self.username_entry = ttk.Entry(main_frame, width=25)
        self.username_entry.grid(row=1, column=1, pady=5, sticky=(tk.W, tk.E))
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(
            row=2, column=0, sticky=tk.E, padx=(0, 10), pady=5
        )
        self.password_entry = ttk.Entry(main_frame, show="*", width=25)
        self.password_entry.grid(row=2, column=1, pady=5, sticky=(tk.W, tk.E))
        
        # Login button
        self.login_button = ttk.Button(
            main_frame,
            text="Login",
            command=self.login
        )
        self.login_button.grid(row=3, column=0, columnspan=2, pady=(20, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Default credentials hint
        hint_label = ttk.Label(
            main_frame,
            text="Default admin: admin / admin123",
            font=('Helvetica', 9),
            foreground="gray"
        )
        hint_label.grid(row=5, column=0, columnspan=2, pady=(20, 0))
    
    def login(self):
        """Handle login button click"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return
        
        # Disable login button during authentication
        self.login_button.config(state='disabled')
        self.status_label.config(text="Authenticating...")
        self.root.update()
        
        try:
            user = self.auth_manager.login(username, password)
            
            if user:
                logger.info(f"User {username} logged in successfully")
                self.root.destroy()
                self.on_success_callback(user)
            else:
                self.status_label.config(text="Invalid credentials")
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus()
        except Exception as e:
            logger.error(f"Login error: {e}")
            self.status_label.config(text="Login failed. Please try again.")
        finally:
            self.login_button.config(state='normal')
    
    def show(self):
        """Display the login window"""
        self.root.mainloop()
