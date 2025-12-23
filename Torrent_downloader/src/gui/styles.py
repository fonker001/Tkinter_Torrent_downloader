# src/gui/styles.py
"""
Modern styling constants for the YTS Browser
"""

COLORS = {
    # Dark theme
    'dark': {
        'background': '#0a0e17',
        'surface': '#1a1f2e',
        'surface_light': '#2a3142',
        'primary': '#00adb5',
        'primary_dark': '#00969c',
        'secondary': '#6c5ce7',
        'text': '#eeeeee',
        'text_secondary': '#a0aec0',
        'text_disabled': '#718096',
        'success': '#00d26a',
        'warning': '#ff9d00',
        'error': '#ff4757',
        'border': '#2d3748',
        'divider': '#4a5568',
    },
    
    # Light theme (optional)
    'light': {
        'background': '#f7fafc',
        'surface': '#ffffff',
        'surface_light': '#edf2f7',
        'primary': '#3182ce',
        'primary_dark': '#2c5282',
        'secondary': '#805ad5',
        'text': '#2d3748',
        'text_secondary': '#718096',
        'text_disabled': '#a0aec0',
        'success': '#38a169',
        'warning': '#d69e2e',
        'error': '#e53e3e',
        'border': '#e2e8f0',
        'divider': '#cbd5e0',
    }
}

FONTS = {
    'heading': ('Segoe UI', 20, 'bold'),
    'subheading': ('Segoe UI', 16, 'bold'),
    'body': ('Segoe UI', 11, 'normal'),
    'body_bold': ('Segoe UI', 11, 'bold'),
    'caption': ('Segoe UI', 9, 'normal'),
    'caption_bold': ('Segoe UI', 9, 'bold'),
    'mono': ('Consolas', 10, 'normal'),
}

SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 20,
    'xxl': 24,
}

BORDER_RADIUS = {
    'sm': 4,
    'md': 8,
    'lg': 12,
    'xl': 16,
}

SHADOWS = {
    'sm': {'offsetx': 0, 'offsety': 1, 'blur': 2, 'color': '#00000020'},
    'md': {'offsetx': 0, 'offsety': 4, 'blur': 6, 'color': '#00000030'},
    'lg': {'offsetx': 0, 'offsety': 10, 'blur': 15, 'color': '#00000040'},
}

ANIMATION = {
    'fast': 150,
    'normal': 300,
    'slow': 500,
}