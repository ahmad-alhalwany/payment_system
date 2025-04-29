from PyQt6.QtGui import QColor

def get_status_arabic(status):
    """Convert status to Arabic."""
    status_map = {
        "processing": "قيد المعالجة",
        "completed": "مكتمل",
        "cancelled": "ملغي",
        "rejected": "مرفوض",
        "on_hold": "معلق"
    }
    return status_map.get(status, status)

def get_status_color(status):
    """Get color for status."""
    status_colors = {
        "processing": QColor(200, 200, 255),
        "completed": QColor(200, 255, 200),
        "cancelled": QColor(255, 200, 200),
        "rejected": QColor(255, 150, 150),
        "on_hold": QColor(255, 200, 150)
    }
    return status_colors.get(status, QColor(255, 255, 255))

def get_status_text_color(status):
    """Get text color for status."""
    status_colors = {
        "pending": "#f39c12",  # Orange
        "processing": "#3498db",  # Blue
        "completed": "#2ecc71",  # Green
        "cancelled": "#e74c3c",  # Red
        "rejected": "#c0392b",  # Darker red
        "on_hold": "#f1c40f"  # Yellow
    }
    return status_colors.get(status, "#333333")

def format_currency(amount, currency):
    """Format currency values with proper symbols.
    
    Args:
        amount (float): The amount to format
        currency (str): The currency type ('USD', 'SYP', etc.)
        
    Returns:
        str: Formatted currency string with proper symbol
    """
    # Normalize currency to uppercase for comparison
    currency_upper = currency.upper() if currency else ""
    
    # Format based on currency type
    if currency_upper == "USD" or currency == "$" or currency == "دولار أمريكي" or currency == "دولار":
        return f"{amount:,.2f} $"
    elif currency_upper == "SYP" or currency == "ليرة سورية" or currency == "ل.س":
        return f"{amount:,.2f} ل.س"
    else:
        # Default fallback - use the original currency string
        return f"{amount:,.2f} {currency}"
