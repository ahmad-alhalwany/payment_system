from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtGui import QAction
import sys
import os
import subprocess

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
            # Close all windows
            for widget in QApplication.topLevelWidgets():
                widget.close()
            
            # Get the current script path
            script_path = os.path.abspath(sys.argv[0])
            
            # Start a new process with the same script
            subprocess.Popen([sys.executable, script_path])
            
            # Exit the current process
            sys.exit(0)