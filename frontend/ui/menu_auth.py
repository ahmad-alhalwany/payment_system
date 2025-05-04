from PyQt6.QtWidgets import QMessageBox, QApplication, QMenuBar, QMenu
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtCore import Qt
import sys
import os
import subprocess

class MenuAuthMixin:
    """Mixin class containing menu and authentication functionality"""
    
    def create_menu_bar(self):
        """Create menu bar with enhanced styling and additional menus."""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QMenuBar::item:selected {
                background-color: #34495e;
            }
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #ecf0f1;
                margin: 5px;
            }
        """)

        # File Menu
        file_menu = menu_bar.addMenu("الملف")
        
        # Add refresh action
        refresh_action = QAction("تحديث البيانات", self)
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self.refresh_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # Add print action
        print_action = QAction("طباعة", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_current_view)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        # Add close action
        close_action = QAction("إغلاق البرنامج", self)
        close_action.setShortcut("Alt+F4")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("تحرير")
        
        # Add search action
        search_action = QAction("بحث", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.show_search_dialog)
        edit_menu.addAction(search_action)
        
        # Add filter action
        filter_action = QAction("تصفية", self)
        filter_action.setShortcut("Ctrl+L")
        filter_action.triggered.connect(self.show_filter_dialog)
        edit_menu.addAction(filter_action)

        # View Menu
        view_menu = menu_bar.addMenu("عرض")
        
        # Add zoom actions
        zoom_in_action = QAction("تكبير", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("تصغير", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        view_menu.addSeparator()
        
        # Add theme toggle
        theme_action = QAction("تبديل المظهر", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)

        # User Menu
        user_menu = menu_bar.addMenu("المستخدم")
        
        # Add profile action
        profile_action = QAction("الملف الشخصي", self)
        profile_action.triggered.connect(self.show_profile)
        user_menu.addAction(profile_action)
        
        # Add change password action
        change_password_action = QAction("تغيير كلمة المرور", self)
        change_password_action.triggered.connect(self.change_password)
        user_menu.addAction(change_password_action)
        
        user_menu.addSeparator()
        
        # Add logout action
        logout_action = QAction("تسجيل الخروج", self)
        logout_action.setShortcut("Ctrl+Q")
        logout_action.triggered.connect(self.logout)
        user_menu.addAction(logout_action)

        # Help Menu
        help_menu = menu_bar.addMenu("مساعدة")
        
        # Add about action
        about_action = QAction("حول البرنامج", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Add help action
        help_action = QAction("دليل المستخدم", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

    def refresh_data(self):
        """Refresh application data."""
        if hasattr(self, 'refresh_data'):
            self.refresh_data()
        else:
            QMessageBox.information(self, "تحديث البيانات", "تم تحديث البيانات بنجاح")

    def print_current_view(self):
        """Print current view."""
        if hasattr(self, 'print_current_view'):
            self.print_current_view()
        else:
            QMessageBox.information(self, "طباعة", "تم إرسال الطلب للطباعة")

    def show_search_dialog(self):
        """Show search dialog."""
        if hasattr(self, 'show_search_dialog'):
            self.show_search_dialog()
        else:
            QMessageBox.information(self, "بحث", "فتح نافذة البحث")

    def show_filter_dialog(self):
        """Show filter dialog."""
        if hasattr(self, 'show_filter_dialog'):
            self.show_filter_dialog()
        else:
            QMessageBox.information(self, "تصفية", "فتح نافذة التصفية")

    def zoom_in(self):
        """Zoom in view."""
        if hasattr(self, 'zoom_in'):
            self.zoom_in()
        else:
            QMessageBox.information(self, "تكبير", "تم تكبير العرض")

    def zoom_out(self):
        """Zoom out view."""
        if hasattr(self, 'zoom_out'):
            self.zoom_out()
        else:
            QMessageBox.information(self, "تصغير", "تم تصغير العرض")

    def toggle_theme(self):
        """Toggle between light and dark theme."""
        if hasattr(self, 'toggle_theme'):
            self.toggle_theme()
        else:
            QMessageBox.information(self, "تبديل المظهر", "تم تبديل المظهر")

    def show_profile(self):
        """Show user profile."""
        if hasattr(self, 'show_profile'):
            self.show_profile()
        else:
            QMessageBox.information(self, "الملف الشخصي", "فتح الملف الشخصي")

    def change_password(self):
        """Change user password."""
        if hasattr(self, 'change_password'):
            self.change_password()
        else:
            QMessageBox.information(self, "تغيير كلمة المرور", "فتح نافذة تغيير كلمة المرور")

    def show_about(self):
        """Show about dialog."""
        if hasattr(self, 'show_about'):
            self.show_about()
        else:
            QMessageBox.information(self, "حول البرنامج", 
                "نظام تحويل الأموال الداخلي\nالإصدار 1.0\n© 2024")

    def show_help(self):
        """Show help documentation."""
        if hasattr(self, 'show_help'):
            self.show_help()
        else:
            QMessageBox.information(self, "دليل المستخدم", "فتح دليل المستخدم")

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