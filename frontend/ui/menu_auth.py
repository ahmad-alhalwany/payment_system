from PyQt6.QtWidgets import QMessageBox, QApplication, QMenuBar, QMenu, QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QLabel, QPushButton, QTextEdit
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtCore import Qt
import sys
import os
import subprocess
from ui.custom_widgets import ModernGroupBox
from ui.password_reset import PasswordResetDialog

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
        """Default refresh_data: show a message. Should be overridden in main window classes if needed."""
        QMessageBox.information(self, "تحديث البيانات", "تم تحديث البيانات بنجاح")

    def print_current_view(self):
        """Default print_current_view: show a message. Should be overridden in main window classes if needed."""
        QMessageBox.information(self, "طباعة", "لا توجد وظيفة طباعة محددة في هذه النافذة.")

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
        if hasattr(self, 'apply_zoom'):
            self.current_zoom = min(200, getattr(self, 'current_zoom', 100) + 10)
            self.apply_zoom()
        else:
            QMessageBox.information(self, "تكبير", "تم تكبير العرض")

    def zoom_out(self):
        """Zoom out view."""
        if hasattr(self, 'apply_zoom'):
            self.current_zoom = max(50, getattr(self, 'current_zoom', 100) - 10)
            self.apply_zoom()
        else:
            QMessageBox.information(self, "تصغير", "تم تصغير العرض")

    def toggle_theme(self):
        """Toggle between light and dark theme."""
        if not hasattr(self, 'is_dark_theme'):
            self.is_dark_theme = False
        
        self.is_dark_theme = not self.is_dark_theme
        
        if self.is_dark_theme:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                }
                QTableWidget {
                    background-color: #34495e;
                    color: #ecf0f1;
                    gridline-color: #2c3e50;
                }
                QHeaderView::section {
                    background-color: #1a2530;
                    color: #ecf0f1;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: white;
                    color: #2c3e50;
                }
                QTableWidget {
                    background-color: white;
                    color: #2c3e50;
                    gridline-color: #ddd;
                }
                QHeaderView::section {
                    background-color: #2c3e50;
                    color: white;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)

    def show_profile(self):
        """Show user profile."""
        profile_dialog = QDialog(self)
        profile_dialog.setWindowTitle("الملف الشخصي")
        profile_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # User info group
        info_group = ModernGroupBox("معلومات المستخدم", "#3498db")
        info_layout = QFormLayout()
        
        info_layout.addRow("اسم المستخدم:", QLabel("مدير النظام"))
        info_layout.addRow("الدور:", QLabel("مدير"))
        info_layout.addRow("الفرع:", QLabel("المركز الرئيسي"))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        button_box.rejected.connect(profile_dialog.reject)
        layout.addWidget(button_box)
        
        profile_dialog.setLayout(layout)
        profile_dialog.exec()

    def change_password(self):
        """Change user password."""
        dialog = PasswordResetDialog(is_admin=True, token=self.token)
        dialog.exec()

    def show_about(self):
        """Show about dialog."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("حول البرنامج")
        about_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Logo and title
        title = QLabel("نظام تحويل الأموال الداخلي")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Version info
        version = QLabel("الإصدار 1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Copyright
        copyright = QLabel("© 2024 جميع الحقوق محفوظة")
        copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright)
        
        # Close button
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(about_dialog.accept)
        layout.addWidget(close_button)
        
        about_dialog.setLayout(layout)
        about_dialog.exec()

    def show_help(self):
        """Show help documentation."""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("دليل المستخدم")
        help_dialog.setMinimumWidth(600)
        help_dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
            <h2>دليل استخدام لوحة تحكم المدير</h2>
            
            <h3>إدارة الفروع</h3>
            <ul>
                <li>إضافة وتعديل وحذف الفروع</li>
                <li>مراقبة أداء الفروع</li>
                <li>إدارة الموظفين في كل فرع</li>
            </ul>
            
            <h3>إدارة التحويلات</h3>
            <ul>
                <li>مراقبة جميع التحويلات في النظام</li>
                <li>تصفية وبحث في التحويلات</li>
                <li>تغيير حالة التحويلات</li>
                <li>طباعة التقارير</li>
            </ul>
            
            <h3>إدارة المستخدمين</h3>
            <ul>
                <li>إدارة حسابات المستخدمين</li>
                <li>تعيين الصلاحيات</li>
                <li>مراقبة نشاط المستخدمين</li>
            </ul>
            
            <h3>التقارير والإحصائيات</h3>
            <ul>
                <li>عرض تقارير الأداء</li>
                <li>تحليل البيانات</li>
                <li>تصدير التقارير</li>
            </ul>
            
            <h3>اختصارات لوحة المفاتيح</h3>
            <ul>
                <li>Ctrl+F: بحث</li>
                <li>Ctrl+R: تحديث</li>
                <li>Ctrl+P: طباعة</li>
                <li>F1: المساعدة</li>
            </ul>
        """)
        layout.addWidget(help_text)
        
        # Close button
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        
        help_dialog.setLayout(layout)
        help_dialog.exec()

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