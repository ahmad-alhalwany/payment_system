from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QAction

class MenuAuthMixin:
    """Mixin class containing menu and authentication functionality"""
    
    def create_menu_bar(self):
        """Create menu bar with logout and close options."""
        menu_bar = self.menuBar()
        
        # Create user menu
        user_menu = menu_bar.addMenu("المستخدم")
        
        # Add logout action
        logout_action = QAction("تسجيل الخروج", self)
        logout_action.triggered.connect(self.logout)
        user_menu.addAction(logout_action)
        
        # Add separator
        user_menu.addSeparator()
        
        # Add close action
        close_action = QAction("إغلاق البرنامج", self)
        close_action.triggered.connect(self.close)
        user_menu.addAction(close_action)

    def logout(self):
        """Logout and return to login screen."""
        reply = QMessageBox.question(
            self, 
            "تسجيل الخروج", 
            "هل أنت متأكد من رغبتك في تسجيل الخروج؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.close()  # Close current window
            # Create new login window
            from login_fixed import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()