"""
Modern UI Theme for POS System
Inspired by shadcn/ui design patterns with elegant typography and modern components
"""
import tkinter as tk
from tkinter import ttk, font
import tkinter.font as tkFont

class ModernTheme:
    """Centralized theme configuration inspired by shadcn/ui"""
    
    # Color Palette - Following shadcn's design system
    colors = {
        # Background colors
        'background': '#ffffff',
        'background_secondary': '#f9fafb',
        'background_tertiary': '#f3f4f6',
        'background_dark': '#0f172a',
        
        # Foreground colors
        'foreground': '#0f172a',
        'foreground_muted': '#64748b',
        'foreground_light': '#94a3b8',
        
        # Primary colors (Modern blue)
        'primary': '#3b82f6',
        'primary_hover': '#2563eb',
        'primary_light': '#eff6ff',
        'primary_foreground': '#ffffff',
        
        # Secondary colors (Slate)
        'secondary': '#e2e8f0',
        'secondary_hover': '#cbd5e1',
        'secondary_foreground': '#1e293b',
        
        # Accent colors
        'accent': '#8b5cf6',
        'accent_hover': '#7c3aed',
        'accent_light': '#f3e8ff',
        
        # Status colors
        'success': '#10b981',
        'success_light': '#d1fae5',
        'warning': '#f59e0b',
        'warning_light': '#fed7aa',
        'danger': '#ef4444',
        'danger_light': '#fee2e2',
        'info': '#06b6d4',
        'info_light': '#cffafe',
        
        # Border and divider
        'border': '#e2e8f0',
        'border_light': '#f1f5f9',
        'divider': '#e5e7eb',
        
        # Card and surface
        'card': '#ffffff',
        'card_hover': '#f8fafc',
        
        # Input colors
        'input_bg': '#ffffff',
        'input_border': '#e2e8f0',
        'input_focus': '#3b82f6',
        'input_placeholder': '#94a3b8',
    }
    
    # Typography - Modern font stack
    fonts = {
        # Font families
        'family_sans': ('Inter', 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', 'Arial'),
        'family_mono': ('SF Mono', 'Monaco', 'Consolas', 'Courier New'),
        
        # Font sizes (in pixels)
        'size_xs': 11,
        'size_sm': 12,
        'size_base': 14,
        'size_md': 16,
        'size_lg': 18,
        'size_xl': 20,
        'size_2xl': 24,
        'size_3xl': 30,
        'size_4xl': 36,
        
        # Font weights
        'weight_light': 'normal',
        'weight_normal': 'normal',
        'weight_medium': 'normal',
        'weight_semibold': 'bold',
        'weight_bold': 'bold',
    }
    
    # Spacing system (in pixels)
    spacing = {
        'xs': 4,
        'sm': 8,
        'md': 12,
        'lg': 16,
        'xl': 24,
        '2xl': 32,
        '3xl': 48,
    }
    
    # Border radius
    radius = {
        'none': 0,
        'sm': 4,
        'md': 6,
        'lg': 8,
        'xl': 12,
        'full': 9999,
    }
    
    @classmethod
    def initialize(cls, root):
        """Initialize the theme for the application"""
        # Configure root window
        root.configure(bg=cls.colors['background'])
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')  # Use clam as base for customization
        
        # Configure general styles
        style.configure('.',
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            fieldbackground=cls.colors['input_bg'],
            borderwidth=1,
            relief='flat',
            focuscolor=cls.colors['primary']
        )
        
        # Modern Frame styles
        style.configure('Modern.TFrame',
            background=cls.colors['background'],
            relief='flat',
            borderwidth=0
        )
        
        style.configure('Card.TFrame',
            background=cls.colors['card'],
            relief='solid',
            borderwidth=1,
            bordercolor=cls.colors['border']
        )
        
        # Modern Label styles
        style.configure('Modern.TLabel',
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            font=cls.get_font('base')
        )
        
        style.configure('Heading1.TLabel',
            font=cls.get_font('3xl', 'bold'),
            foreground=cls.colors['foreground']
        )
        
        style.configure('Heading2.TLabel',
            font=cls.get_font('2xl', 'semibold'),
            foreground=cls.colors['foreground']
        )
        
        style.configure('Heading3.TLabel',
            font=cls.get_font('xl', 'semibold'),
            foreground=cls.colors['foreground']
        )
        
        style.configure('Subtitle.TLabel',
            font=cls.get_font('md'),
            foreground=cls.colors['foreground_muted']
        )
        
        style.configure('Caption.TLabel',
            font=cls.get_font('sm'),
            foreground=cls.colors['foreground_light']
        )
        
        # Modern Button styles
        style.configure('Modern.TButton',
            font=cls.get_font('base', 'medium'),
            foreground=cls.colors['foreground'],
            background=cls.colors['secondary'],
            borderwidth=0,
            focuscolor='none',
            lightcolor=cls.colors['secondary'],
            darkcolor=cls.colors['secondary']
        )
        style.map('Modern.TButton',
            background=[('active', cls.colors['secondary_hover']),
                       ('pressed', cls.colors['secondary_hover'])]
        )
        
        # Primary Button
        style.configure('Primary.TButton',
            font=cls.get_font('base', 'semibold'),
            foreground=cls.colors['primary_foreground'],
            background=cls.colors['primary'],
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Primary.TButton',
            background=[('active', cls.colors['primary_hover']),
                       ('pressed', cls.colors['primary_hover'])]
        )
        
        # Accent Button
        style.configure('Accent.TButton',
            font=cls.get_font('base', 'semibold'),
            foreground='white',
            background=cls.colors['accent'],
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Accent.TButton',
            background=[('active', cls.colors['accent_hover']),
                       ('pressed', cls.colors['accent_hover'])]
        )
        
        # Ghost Button
        style.configure('Ghost.TButton',
            font=cls.get_font('base', 'medium'),
            foreground=cls.colors['foreground_muted'],
            background=cls.colors['background'],
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Ghost.TButton',
            background=[('active', cls.colors['background_secondary']),
                       ('pressed', cls.colors['background_tertiary'])],
            foreground=[('active', cls.colors['foreground'])]
        )
        
        # Danger Button
        style.configure('Danger.TButton',
            font=cls.get_font('base', 'semibold'),
            foreground='white',
            background=cls.colors['danger'],
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Danger.TButton',
            background=[('active', '#dc2626'),
                       ('pressed', '#b91c1c')]
        )
        
        # Success Button
        style.configure('Success.TButton',
            font=cls.get_font('base', 'semibold'),
            foreground='white',
            background=cls.colors['success'],
            borderwidth=0,
            focuscolor='none'
        )
        style.map('Success.TButton',
            background=[('active', '#059669'),
                       ('pressed', '#047857')]
        )
        
        # Modern Entry style
        style.configure('Modern.TEntry',
            font=cls.get_font('base'),
            foreground=cls.colors['foreground'],
            fieldbackground=cls.colors['input_bg'],
            bordercolor=cls.colors['input_border'],
            insertcolor=cls.colors['primary'],
            borderwidth=1,
            relief='solid'
        )
        style.map('Modern.TEntry',
            bordercolor=[('focus', cls.colors['input_focus'])],
            lightcolor=[('focus', cls.colors['input_focus'])],
            darkcolor=[('focus', cls.colors['input_focus'])]
        )
        
        # Modern Combobox style
        style.configure('Modern.TCombobox',
            font=cls.get_font('base'),
            foreground=cls.colors['foreground'],
            fieldbackground=cls.colors['input_bg'],
            background=cls.colors['input_bg'],
            bordercolor=cls.colors['input_border'],
            arrowcolor=cls.colors['foreground_muted'],
            borderwidth=1,
            relief='solid'
        )
        style.map('Modern.TCombobox',
            bordercolor=[('focus', cls.colors['input_focus'])],
            lightcolor=[('focus', cls.colors['input_focus'])],
            darkcolor=[('focus', cls.colors['input_focus'])]
        )
        
        # Modern Notebook style
        style.configure('Modern.TNotebook',
            background=cls.colors['background'],
            borderwidth=0,
            relief='flat'
        )
        style.configure('Modern.TNotebook.Tab',
            font=cls.get_font('base', 'medium'),
            background=cls.colors['background'],
            foreground=cls.colors['foreground_muted'],
            padding=[16, 8],
            borderwidth=0
        )
        style.map('Modern.TNotebook.Tab',
            background=[('selected', cls.colors['background']),
                       ('active', cls.colors['background_secondary'])],
            foreground=[('selected', cls.colors['foreground']),
                       ('active', cls.colors['foreground'])]
        )
        
        # Modern Treeview style
        style.configure('Modern.Treeview',
            font=cls.get_font('base'),
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            fieldbackground=cls.colors['background'],
            borderwidth=1,
            relief='solid',
            bordercolor=cls.colors['border']
        )
        style.configure('Modern.Treeview.Heading',
            font=cls.get_font('sm', 'semibold'),
            background=cls.colors['background_secondary'],
            foreground=cls.colors['foreground'],
            relief='flat',
            borderwidth=0
        )
        style.map('Modern.Treeview',
            background=[('selected', cls.colors['primary_light'])],
            foreground=[('selected', cls.colors['primary'])]
        )
        
        # Modern LabelFrame style
        style.configure('Modern.TLabelframe',
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            bordercolor=cls.colors['border'],
            relief='solid',
            borderwidth=1
        )
        style.configure('Modern.TLabelframe.Label',
            font=cls.get_font('base', 'semibold'),
            background=cls.colors['background'],
            foreground=cls.colors['foreground']
        )
        
        # Modern Checkbutton style
        style.configure('Modern.TCheckbutton',
            font=cls.get_font('base'),
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            focuscolor='none'
        )
        style.map('Modern.TCheckbutton',
            background=[('active', cls.colors['background'])],
            foreground=[('active', cls.colors['primary'])]
        )
        
        # Modern Radiobutton style
        style.configure('Modern.TRadiobutton',
            font=cls.get_font('base'),
            background=cls.colors['background'],
            foreground=cls.colors['foreground'],
            focuscolor='none'
        )
        style.map('Modern.TRadiobutton',
            background=[('active', cls.colors['background'])],
            foreground=[('active', cls.colors['primary'])]
        )
        
        # Modern Scrollbar style
        style.configure('Modern.Vertical.TScrollbar',
            background=cls.colors['background_secondary'],
            bordercolor=cls.colors['background_secondary'],
            arrowcolor=cls.colors['foreground_muted'],
            troughcolor=cls.colors['background_tertiary'],
            lightcolor=cls.colors['background_secondary'],
            darkcolor=cls.colors['background_secondary'],
            borderwidth=0,
            relief='flat',
            width=12
        )
        style.map('Modern.Vertical.TScrollbar',
            background=[('active', cls.colors['foreground_light']),
                       ('pressed', cls.colors['foreground_muted'])]
        )
        
        # Modern Progressbar style
        style.configure('Modern.Horizontal.TProgressbar',
            background=cls.colors['primary'],
            troughcolor=cls.colors['background_tertiary'],
            borderwidth=0,
            relief='flat',
            lightcolor=cls.colors['primary'],
            darkcolor=cls.colors['primary']
        )
        
        # Status-specific label styles
        style.configure('Success.TLabel',
            font=cls.get_font('base'),
            background=cls.colors['success_light'],
            foreground=cls.colors['success']
        )
        
        style.configure('Warning.TLabel',
            font=cls.get_font('base'),
            background=cls.colors['warning_light'],
            foreground=cls.colors['warning']
        )
        
        style.configure('Danger.TLabel',
            font=cls.get_font('base'),
            background=cls.colors['danger_light'],
            foreground=cls.colors['danger']
        )
        
        style.configure('Info.TLabel',
            font=cls.get_font('base'),
            background=cls.colors['info_light'],
            foreground=cls.colors['info']
        )
    
    @classmethod
    def get_font(cls, size='base', weight='normal'):
        """Get a font tuple with specified size and weight"""
        font_size = cls.fonts.get(f'size_{size}', cls.fonts['size_base'])
        font_weight = cls.fonts.get(f'weight_{weight}', cls.fonts['weight_normal'])
        font_family = cls.fonts['family_sans'][0]  # Use first available font
        
        return (font_family, font_size, font_weight)
    
    @classmethod
    def create_card_frame(cls, parent, **kwargs):
        """Create a modern card-style frame"""
        frame = ttk.Frame(parent, style='Card.TFrame', **kwargs)
        frame.configure(padding=cls.spacing['lg'])
        return frame
    
    @classmethod
    def create_section_frame(cls, parent, title, **kwargs):
        """Create a modern labeled section frame"""
        frame = ttk.LabelFrame(parent, text=title, style='Modern.TLabelframe', **kwargs)
        frame.configure(padding=cls.spacing['md'])
        return frame
    
    @classmethod
    def style_listbox(cls, listbox):
        """Apply modern styling to a Listbox widget"""
        listbox.configure(
            font=cls.get_font('base'),
            bg=cls.colors['background'],
            fg=cls.colors['foreground'],
            selectbackground=cls.colors['primary'],
            selectforeground=cls.colors['primary_foreground'],
            highlightthickness=1,
            highlightcolor=cls.colors['input_focus'],
            highlightbackground=cls.colors['input_border'],
            relief='solid',
            borderwidth=1,
            activestyle='none'
        )
    
    @classmethod
    def style_text(cls, text_widget):
        """Apply modern styling to a Text widget"""
        text_widget.configure(
            font=cls.get_font('base'),
            bg=cls.colors['background'],
            fg=cls.colors['foreground'],
            insertbackground=cls.colors['primary'],
            selectbackground=cls.colors['primary_light'],
            selectforeground=cls.colors['primary'],
            highlightthickness=1,
            highlightcolor=cls.colors['input_focus'],
            highlightbackground=cls.colors['input_border'],
            relief='solid',
            borderwidth=1,
            padx=cls.spacing['sm'],
            pady=cls.spacing['sm']
        )
    
    @classmethod
    def create_hover_button(cls, parent, text, command=None, style='Modern.TButton'):
        """Create a button with hover effects"""
        button = ttk.Button(parent, text=text, command=command, style=style)
        
        # Add additional hover effects if needed
        def on_enter(e):
            button.configure(cursor='hand2')
        
        def on_leave(e):
            button.configure(cursor='')
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        
        return button
    
    @classmethod
    def add_shadow(cls, widget):
        """Add a shadow effect to a widget (simulated with border)"""
        # Create a frame to simulate shadow
        shadow_frame = tk.Frame(widget.master,
                               bg=cls.colors['border'],
                               highlightthickness=0)
        shadow_frame.place(in_=widget, x=2, y=2, anchor='nw',
                          relwidth=1.0, relheight=1.0)
        widget.lift()
        return shadow_frame


class IconFont:
    """Modern icon font characters for UI elements"""
    # Using Unicode characters that work well as icons
    icons = {
        'user': '👤',
        'users': '👥',
        'settings': '⚙️',
        'document': '📄',
        'folder': '📁',
        'edit': '✏️',
        'delete': '🗑️',
        'save': '💾',
        'print': '🖨️',
        'search': '🔍',
        'filter': '🔽',
        'refresh': '🔄',
        'add': '➕',
        'remove': '➖',
        'check': '✓',
        'close': '✕',
        'info': 'ℹ️',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅',
        'star': '⭐',
        'heart': '❤️',
        'cart': '🛒',
        'money': '💰',
        'calendar': '📅',
        'clock': '🕐',
        'email': '✉️',
        'phone': '📞',
        'home': '🏠',
        'lock': '🔒',
        'unlock': '🔓',
        'eye': '👁️',
        'eye_off': '👁️‍🗨️',
        'menu': '☰',
        'grid': '⊞',
        'list': '☷',
        'arrow_up': '↑',
        'arrow_down': '↓',
        'arrow_left': '←',
        'arrow_right': '→',
        'chevron_up': '⌃',
        'chevron_down': '⌄',
        'chevron_left': '‹',
        'chevron_right': '›',
        'order': '📝',
        'invoice': '🧾',
        'receipt': '🧾',
        'package': '📦',
        'tag': '🏷️',
        'qr': '▦',
        'barcode': '┃┃┃',
    }
    
    @classmethod
    def get(cls, name):
        """Get an icon character by name"""
        return cls.icons.get(name, '')


# Utility functions for easy access
def apply_theme(root):
    """Apply the modern theme to the application"""
    ModernTheme.initialize(root)

def get_color(color_name):
    """Get a color from the theme"""
    return ModernTheme.colors.get(color_name, '#000000')

def get_font(size='base', weight='normal'):
    """Get a font configuration"""
    return ModernTheme.get_font(size, weight)

def get_icon(icon_name):
    """Get an icon character"""
    return IconFont.get(icon_name)
