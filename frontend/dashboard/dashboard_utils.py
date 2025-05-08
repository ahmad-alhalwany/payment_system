from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
    QDialogButtonBox, QPushButton, QTextEdit
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from ui.custom_widgets import ModernGroupBox
from ui.user_search import UserSearchDialog

class DashboardUtilsMixin:
    def apply_filters(self, dialog):
        """Apply the selected filters."""
        filters = {
            'start_date': self.start_date_filter.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date_filter.date().toString("yyyy-MM-dd"),
            'min_amount': self.min_amount_filter.value(),
            'max_amount': self.max_amount_filter.value()
        }
        
        # Apply filters to transactions
        self.filter_transactions(filters)
        dialog.accept()

    def zoom_in(self):
        """Zoom in the view."""
        self.current_zoom = min(200, self.current_zoom + 10)
        self.apply_zoom()

    def zoom_out(self):
        """Zoom out the view."""
        self.current_zoom = max(50, self.current_zoom - 10)
        self.apply_zoom()

    def apply_zoom(self):
        """Apply the current zoom level to the UI."""
        zoom_factor = self.current_zoom / 100
        self.setStyleSheet(f"""
            QWidget {{
                font-size: {zoom_factor}em;
            }}
            QTableWidget {{
                font-size: {zoom_factor}em;
            }}
            QLabel {{
                font-size: {zoom_factor}em;
            }}
            QPushButton {{
                font-size: {zoom_factor}em;
            }}
        """)

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
        """Show user profile dialog."""
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

    def search_user(self):
        """Open user search dialog."""
        dialog = UserSearchDialog(self.token, self)
        dialog.exec()

    def closeEvent(self, event):
        """Clean up timers and resources when closing."""
        # Stop all timers
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'transaction_timer'):
            self.transaction_timer.stop()
        if hasattr(self, 'time_timer'):
            self.time_timer.stop()
        
        # Accept the close event
        event.accept() 