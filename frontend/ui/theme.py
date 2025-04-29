"""
Theme configuration for the application.
Provides consistent colors, typography, and component styles.
"""

class Theme:
    # Color Palette
    PRIMARY = "#2c3e50"      # Dark Blue - Main color
    SECONDARY = "#34495e"    # Darker Blue - Secondary elements
    ACCENT = "#3498db"       # Light Blue - Highlights and accents
    SUCCESS = "#2ecc71"      # Green - Success states
    WARNING = "#f1c40f"      # Yellow - Warning states
    ERROR = "#e74c3c"        # Red - Error states
    INFO = "#3498db"         # Blue - Information states
    
    # Background Colors
    BG_PRIMARY = "#ffffff"   # White - Primary background
    BG_SECONDARY = "#f8f9fa" # Light Gray - Secondary background
    BG_TERTIARY = "#ecf0f1"  # Lighter Gray - Tertiary background
    
    # Text Colors
    TEXT_PRIMARY = "#2c3e50"   # Dark Blue - Primary text
    TEXT_SECONDARY = "#7f8c8d" # Gray - Secondary text
    TEXT_LIGHT = "#ffffff"     # White - Light text
    
    # Border Colors
    BORDER = "#dcdde1"
    
    # Font Families
    FONT_PRIMARY = "Arial"
    FONT_SECONDARY = "Tahoma"
    
    # Font Sizes
    FONT_SIZE_SMALL = "12px"
    FONT_SIZE_NORMAL = "14px"
    FONT_SIZE_LARGE = "16px"
    FONT_SIZE_XLARGE = "18px"
    FONT_SIZE_TITLE = "24px"
    
    # Component Styles
    BUTTON_STYLE = """
        QPushButton {
            background-color: %(bg_color)s;
            color: #ffffff;
            border: none;
            border-radius: 5px;
            padding: 8px 15px;
            font-family: Arial;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: %(hover_color)s;
        }
        QPushButton:pressed {
            background-color: %(pressed_color)s;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
    """
    
    TABLE_STYLE = """
        QTableWidget {
            background-color: white;
            border: 1px solid #dcdde1;
            border-radius: 5px;
            gridline-color: #f5f6fa;
        }
        QTableWidget::item {
            padding: 5px;
            border-bottom: 1px solid #f5f6fa;
        }
        QHeaderView::section {
            background-color: #2c3e50;
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
    """
    
    GROUP_BOX_STYLE = """
        QGroupBox {
            border: 1px solid #dcdde1;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
            background-color: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
            color: %(title_color)s;
        }
    """
    
    INPUT_STYLE = """
        QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
            border: 1px solid #dcdde1;
            border-radius: 5px;
            padding: 5px;
            background-color: white;
            selection-background-color: #3498db;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
            border: 2px solid #3498db;
        }
    """
    
    TAB_STYLE = """
        QTabWidget::pane {
            border: 1px solid #dcdde1;
            border-radius: 5px;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 8px 15px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: #2c3e50;
            color: white;
        }
    """
    
    LABEL_STYLE = """
        QLabel {
            color: #2c3e50;
            font-family: Arial;
        }
    """
    
    STATUS_BAR_STYLE = """
        QStatusBar {
            background-color: #f8f9fa;
            color: #2c3e50;
        }
    """
    
    @classmethod
    def get_button_style(cls, color):
        """Get button style with specific color."""
        return cls.BUTTON_STYLE % {
            'bg_color': color,
            'hover_color': cls._adjust_color(color, 1.1),
            'pressed_color': cls._adjust_color(color, 0.9)
        }
    
    @classmethod
    def get_group_box_style(cls, title_color):
        """Get group box style with specific title color."""
        return cls.GROUP_BOX_STYLE % {
            'title_color': title_color
        }
    
    @staticmethod
    def _adjust_color(hex_color, factor):
        """Adjust color brightness by factor."""
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:], 16)
        
        # Adjust values
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}" 