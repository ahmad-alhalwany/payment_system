import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QComboBox, QGroupBox,
    QGridLayout, QPushButton, QHBoxLayout, QDateEdit, 
    QCalendarWidget, QDialogButtonBox, QFileDialog, 
)
from ui.change_password import ChangePasswordDialog
import csv
from datetime import datetime
from PyQt6.QtGui import QFont, QColor, QAction
from PyQt6.QtCore import Qt, QTimer, QDate
import os
from ui.money_transfer_improved import MoneyTransferApp
from ui.user_search import UserSearchDialog
from ui.user_management_improved import AddEmployeeDialog, EditEmployeeDialog

class ModernGroupBox(QGroupBox):
    """Custom styled group box."""
    
    def __init__(self, title, color="#3498db"):
        super().__init__(title)
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {color};
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {color};
            }}
        """)

class ModernButton(QPushButton):
    """Custom styled button."""
    
    def __init__(self, text, color="#3498db"):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """)
    
    def lighten_color(self, color):
        """Lighten a hex color."""
        # Simple implementation - not perfect but works for our needs
        if color.startswith('#'):
            color = color[1:]
        r = min(255, int(color[0:2], 16) + 20)
        g = min(255, int(color[2:4], 16) + 20)
        b = min(255, int(color[4:6], 16) + 20)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def darken_color(self, color):
        """Darken a hex color."""
        if color.startswith('#'):
            color = color[1:]
        r = max(0, int(color[0:2], 16) - 20)
        g = max(0, int(color[2:4], 16) - 20)
        b = max(0, int(color[4:6], 16) - 20)
        return f"#{r:02x}{g:02x}{b:02x}"

class BranchManagerDashboard(QMainWindow):
    """Branch Manager Dashboard for the Internal Payment System."""
    
    def __init__(self, branch_id, token=None, user_id=None, username=None, full_name=None):
        super().__init__()
        self.branch_id = branch_id
        self.token = token
        self.user_id = user_id  # Add this
        self.username = username  # Add this
        self.full_name = full_name  # Add this
        self.api_url = os.environ["API_URL"]
        self.branch_id_to_name = {}
        self.current_page = 1
        self.total_pages = 1
        self.per_page = 8
        self.report_per_page = 14
        self.report_current_page = 1
        self.report_total_pages = 1
        
        self.setWindowTitle("لوحة تحكم مدير الفرع - نظام التحويلات المالية")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                font-family: Arial;
            }
        """)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Logo/Title
        title_label = QLabel("نظام التحويلات المالية - لوحة تحكم مدير الفرع")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget for different sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #ddd;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
        """)
        
        # Create tabs
        self.dashboard_tab = QWidget()
        self.employees_tab = QWidget()
        self.transfers_tab = QWidget()
        self.reports_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Set up tabs
        self.setup_dashboard_tab()
        self.setup_employees_tab()
        self.setup_transfers_tab()
        self.setup_reports_tab()
        self.setup_settings_tab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.dashboard_tab, "الرئيسية")
        self.tab_widget.addTab(self.employees_tab, "إدارة الموظفين")
        self.tab_widget.addTab(self.transfers_tab, "التحويلات")
        self.tab_widget.addTab(self.reports_tab, "التقارير")
        self.tab_widget.addTab(self.settings_tab, "الإعدادات")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar().showMessage("جاهز")
        
        # Load branch info
        self.load_branches()
        self.load_branch_info()
        
        # Refresh data initially
        self.refresh_dashboard_data()
        
        # Set up refresh timer (every 5 minutes)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_dashboard_data)
        self.refresh_timer.start(10000)  # 5 minutes in milliseconds
        
        QTimer.singleShot(0, self.refresh_dashboard_data)
        
    def create_menu_bar(self):
        """Create menu bar with logout and close options."""
        # Create menu bar
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
            self.close()
            # Signal to main application to show login window
            if self.parent():
                self.parent().show_login()    
    
    def setup_dashboard_tab(self):
        """Set up the main dashboard tab."""
        layout = QVBoxLayout()
        
        # Welcome message
        welcome_group = ModernGroupBox("لوحة المعلومات", "#e74c3c")
        welcome_layout = QVBoxLayout()
        
        welcome_label = QLabel("مرحباً بك في لوحة تحكم مدير الفرع")
        welcome_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        welcome_layout.addWidget(welcome_label)
        
        self.branch_name_label = QLabel("الفرع: جاري التحميل...")
        self.branch_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(self.branch_name_label)
        
        date_label = QLabel("تاريخ اليوم: جاري التحميل...")
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(date_label)
        self.date_label = date_label
        
        welcome_group.setLayout(welcome_layout)
        layout.addWidget(welcome_group)
        
        
        # Financial Status Group
        financial_group = ModernGroupBox("الحالة المالية", "#27ae60")
        financial_layout = QGridLayout()
        
        # Reduce vertical spacing
        financial_layout.setVerticalSpacing(8)  # Reduced from default 20-25
        financial_layout.setContentsMargins(10, 10, 10, 10)  # Tighter margins

        # Syrian Pounds Balance
        self.syp_balance_label = QLabel("جاري التحميل...")
        self.syp_balance_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.syp_balance_label.setStyleSheet("color: #2ecc71;")
        financial_layout.addWidget(QLabel("الرصيد المتاح (ل.س):"), 0, 0)
        financial_layout.addWidget(self.syp_balance_label, 0, 1)

        # US Dollars Balance
        self.usd_balance_label = QLabel("جاري التحميل...")
        self.usd_balance_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.usd_balance_label.setStyleSheet("color: #3498db;")
        financial_layout.addWidget(QLabel("الرصيد المتاح ($):"), 1, 0)
        financial_layout.addWidget(self.usd_balance_label, 1, 1)

        # Refresh Button
        refresh_finance_btn = ModernButton("تحديث الرصيد", color="#3498db")
        refresh_finance_btn.clicked.connect(self.load_financial_status)
        financial_layout.addWidget(refresh_finance_btn, 0, 2, 2, 1)

        financial_group.setLayout(financial_layout)
        layout.addWidget(financial_group)
        
        # Statistics
        stats_layout = QHBoxLayout()
        
        # Employees stats
        employees_group = ModernGroupBox("إحصائيات الموظفين", "#2ecc71")
        employees_layout = QVBoxLayout()
        
        self.employees_count = QLabel("عدد الموظفين: جاري التحميل...")
        self.employees_count.setFont(QFont("Arial", 12))
        employees_layout.addWidget(self.employees_count)
        
        self.active_employees = QLabel("الموظفين النشطين: جاري التحميل...")
        self.active_employees.setFont(QFont("Arial", 12))
        employees_layout.addWidget(self.active_employees)
        
        employees_group.setLayout(employees_layout)
        stats_layout.addWidget(employees_group)
        
        # Transactions stats
        transactions_group = ModernGroupBox("إحصائيات التحويلات", "#e67e22")
        transactions_layout = QGridLayout()
        
        self.transactions_count = QLabel("عدد التحويلات: جاري التحميل...")
        self.transactions_count.setFont(QFont("Arial", 12))
        transactions_layout.addWidget(self.transactions_count)
        
        self.transactions_amount = QLabel("إجمالي مبالغ التحويلات: جاري التحميل...")
        self.transactions_amount.setFont(QFont("Arial", 12))
        transactions_layout.addWidget(self.transactions_amount)
        
        transactions_group.setLayout(transactions_layout)
        stats_layout.addWidget(transactions_group)
        
        layout.addLayout(stats_layout)
        
        # Quick actions
        actions_group = ModernGroupBox("إجراءات سريعة", "#9b59b6")
        actions_layout = QHBoxLayout()
        
        add_employee_button = ModernButton("إضافة موظف جديد", color="#2ecc71")
        add_employee_button.clicked.connect(self.add_employee)
        actions_layout.addWidget(add_employee_button)
        
        search_user_button = ModernButton("بحث عن مستخدم", color="#e67e22")
        search_user_button.clicked.connect(self.search_user)
        actions_layout.addWidget(search_user_button)
        
        new_transfer_button = ModernButton("تحويل جديد", color="#3498db")
        new_transfer_button.clicked.connect(self.new_transfer)
        actions_layout.addWidget(new_transfer_button)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Recent transactions
        recent_group = ModernGroupBox("أحدث التحويلات", "#3498db")
        recent_layout = QVBoxLayout()
        
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setColumnCount(10)  # Ensure this matches actual columns
        self.recent_transactions_table.setColumnCount(10)
        self.recent_transactions_table.setHorizontalHeaderLabels([
            "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", 
            "التاريخ", "الحالة", "الفرع المرسل", "الفرع المستلم", "اسم الموظف"
        ])
        self.recent_transactions_table.horizontalHeader().setStretchLastSection(True)
        self.recent_transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_transactions_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: 1px solid #1a2530;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QTableWidget::item[type="outgoing"] {
                background-color: #e8f5e9;
            }
            QTableWidget::item[type="incoming"] {
                background-color: #ffebee;
            }
        """)
        recent_layout.addWidget(self.recent_transactions_table)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_button = ModernButton("السابق", color="#3498db")
        self.prev_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel("الصفحة: 1")
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = ModernButton("التالي", color="#3498db")
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        
        recent_layout.addLayout(pagination_layout)
        
        # Single "Show All Transfers" button
        view_all_button = ModernButton("عرض جميع التحويلات", color="#3498db")
        view_all_button.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
        recent_layout.addWidget(view_all_button)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        self.dashboard_tab.setLayout(layout)
        
        recent_layout.addWidget(self.recent_transactions_table)
        
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        self.dashboard_tab.setLayout(layout)

        
        # Load recent transactions
        self.load_recent_transactions()
    
    def setup_employees_tab(self):
        """Set up the employees management tab."""
        layout = QVBoxLayout()
        
        # Employees table
        employees_group = ModernGroupBox("قائمة الموظفين", "#2ecc71")
        employees_layout = QVBoxLayout()
        
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(5)
        self.employees_table.setHorizontalHeaderLabels([
            "اسم المستخدم", "الدور", "الحالة", "تاريخ الإنشاء", "الإجراءات"
        ])
        self.employees_table.horizontalHeader().setStretchLastSection(True)
        self.employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.employees_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: 1px solid #1a2530;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        employees_layout.addWidget(self.employees_table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        add_employee_button = ModernButton("إضافة موظف جديد", color="#2ecc71")
        add_employee_button.clicked.connect(self.add_employee)
        buttons_layout.addWidget(add_employee_button)
        
        refresh_button = ModernButton("تحديث البيانات", color="#3498db")
        refresh_button.clicked.connect(self.load_employees)
        buttons_layout.addWidget(refresh_button)
        
        employees_layout.addLayout(buttons_layout)
        employees_group.setLayout(employees_layout)
        layout.addWidget(employees_group)
        
        self.employees_tab.setLayout(layout)
        
        # Load employees data
        self.load_employees()
        
    def load_financial_status(self):
        """Load and display financial status for the branch"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                branch_data = response.json()
                print(f"Branch data received: {branch_data}")  # Debug print
                financial = branch_data.get("financial_stats", {})
                print(f"Financial stats: {financial}")  # Debug print
                
                # Syrian Pounds Balance
                syp_balance = financial.get("available_balance_syp", financial.get("available_balance", 0))
                self.syp_balance_label.setText(f"{syp_balance:,.2f} ل.س")
                
                # Update color based on SYP balance
                if syp_balance < 500000:
                    self.syp_balance_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.syp_balance_label.setStyleSheet("color: #2ecc71; font-weight: bold;")

                # US Dollars Balance
                usd_balance = financial.get("available_balance_usd", 0)
                self.usd_balance_label.setText(f"{usd_balance:,.2f} $")
                
                # Update color based on USD balance
                if usd_balance < 1000:
                    self.usd_balance_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.usd_balance_label.setStyleSheet("color: #3498db; font-weight: bold;")

            else:
                print(f"Error response: {response.status_code}, {response.text}")  # Debug print
                self.show_financial_error()

        except Exception as e:
            print(f"Error loading financial status: {e}")
            self.show_financial_error()

    def show_financial_error(self):
        """Show error state for financial data"""
        self.syp_balance_label.setText("فشل التحميل")
        self.syp_balance_label.setStyleSheet("color: #e74c3c;")
        self.usd_balance_label.setText("فشل التحميل")
        self.usd_balance_label.setStyleSheet("color: #e74c3c;")    
    
    def setup_transfers_tab(self):
        layout = QVBoxLayout()
        
        self.money_transfer = MoneyTransferApp(
            user_token=self.token,
            branch_id=self.branch_id,
            user_id=self.user_id,
            user_role="branch_manager",
            username=self.username,
            full_name=self.full_name,  # Pass full name here
        )
        self.money_transfer.transferCompleted.connect(self.load_financial_status)
        layout.addWidget(self.money_transfer)
        
        self.transfers_tab.setLayout(layout)
        
    def setup_reports_tab(self):
        """Set up the reports tab with separate sections for transfers and employees."""
        layout = QVBoxLayout()
        
        # Create tab widget for different report types
        report_tabs = QTabWidget()
        report_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #ddd;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
        """)
        
        # Transfers Report Tab
        transfers_tab = QWidget()
        self.setup_transfers_report_tab(transfers_tab)
        report_tabs.addTab(transfers_tab, "تقارير التحويلات")
        
        # Employees Report Tab
        employees_tab = QWidget()
        self.setup_employees_report_tab(employees_tab)
        report_tabs.addTab(employees_tab, "تقارير الموظفين")
        
        layout.addWidget(report_tabs)
        self.reports_tab.setLayout(layout)
        
        
    def setup_transfers_report_tab(self, tab):
        """Set up the transfers report tab with advanced filters and table."""
        layout = QVBoxLayout(tab)
        
        # Filters Group
        filters_group = ModernGroupBox("تصفية التحويلات", "#3498db")
        filters_layout = QGridLayout()
        
        # Date Filters with Calendar Pickers
        # Start Date (default: first day of current month)
        self.report_date_from = QDateEdit()
        self.report_date_from.setDisplayFormat("yyyy-MM-dd")
        self.report_date_from.setCalendarPopup(True)
        self.report_date_from.setDate(QDate.currentDate().addDays(-QDate.currentDate().day() + 1))
        date_from_layout = QHBoxLayout()
        date_from_layout.addWidget(self.report_date_from)
        date_from_layout.addWidget(self.create_calendar_button(self.report_date_from))
        
        # End Date (default: today)
        self.report_date_to = QDateEdit()
        self.report_date_to.setDisplayFormat("yyyy-MM-dd")
        self.report_date_to.setCalendarPopup(True)
        self.report_date_to.setDate(QDate.currentDate())
        date_to_layout = QHBoxLayout()
        date_to_layout.addWidget(self.report_date_to)
        date_to_layout.addWidget(self.create_calendar_button(self.report_date_to))
        
        # Add date components to grid
        filters_layout.addWidget(QLabel("من تاريخ:"), 0, 0)
        filters_layout.addLayout(date_from_layout, 0, 1)
        filters_layout.addWidget(QLabel("إلى تاريخ:"), 1, 0)
        filters_layout.addLayout(date_to_layout, 1, 1)
        
        # Transfer Type Filter
        self.transfer_type_combo = QComboBox()
        self.transfer_type_combo.addItems(["الكل", "صادر", "وارد"])
        filters_layout.addWidget(QLabel("نوع التحويل:"), 0, 2)
        filters_layout.addWidget(self.transfer_type_combo, 0, 3)
        
        # Status Filter
        self.status_combo = QComboBox()
        self.status_combo.addItems(["الكل", "مكتمل", "قيد المعالجة", "ملغي", "مرفوض", "معلق"])
        filters_layout.addWidget(QLabel("الحالة:"), 1, 2)
        filters_layout.addWidget(self.status_combo, 1, 3)
        
        # Action Buttons
        generate_btn = ModernButton("توليد التقرير", color="#2ecc71")
        generate_btn.clicked.connect(self.generate_transfer_report)
        filters_layout.addWidget(generate_btn, 2, 0, 1, 2)
        
        export_btn = ModernButton("تصدير إلى CSV", color="#e67e22")
        export_btn.clicked.connect(self.export_transfer_report)
        filters_layout.addWidget(export_btn, 2, 2, 1, 2)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Report Table
        self.transfer_report_table = QTableWidget()
        self.transfer_report_table.setColumnCount(10)
        self.transfer_report_table.setHorizontalHeaderLabels([
            "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", 
            "التاريخ", "الحالة", "الفرع المرسل", "الفرع المستلم", "الموظف"
        ])
        self.transfer_report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transfer_report_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: 1px solid #1a2530;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Pagination Controls
        pagination_layout = QHBoxLayout()
        self.prev_report_btn = ModernButton("السابق", color="#3498db")
        self.prev_report_btn.clicked.connect(self.prev_report_page)
        pagination_layout.addWidget(self.prev_report_btn)
        
        self.report_page_label = QLabel("الصفحة: 1")
        pagination_layout.addWidget(self.report_page_label)
        
        self.next_report_btn = ModernButton("التالي", color="#3498db")
        self.next_report_btn.clicked.connect(self.next_report_page)
        pagination_layout.addWidget(self.next_report_btn)
        
        layout.addWidget(self.transfer_report_table)
        layout.addLayout(pagination_layout)
        
    def create_calendar_button(self, date_edit):
        """Create a calendar picker button for date input"""
        button = QPushButton()
        button.setText("📅")
        button.setFixedSize(30, 30)
        button.clicked.connect(lambda: self.show_calendar(date_edit))
        button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        return button

    def show_calendar(self, date_edit):
        """Show calendar dialog and update date field"""
        dialog = QDialog(self)
        dialog.setWindowTitle("اختر التاريخ")
        layout = QVBoxLayout(dialog)
        
        calendar = QCalendarWidget()
        calendar.setSelectedDate(date_edit.date())
        layout.addWidget(calendar)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            date_edit.setDate(calendar.selectedDate())   
        
    def setup_employees_report_tab(self, tab):
        """Set up the employees report tab."""
        layout = QVBoxLayout(tab)
        
        # Filters Group
        filters_group = ModernGroupBox("تصفية الموظفين", "#2ecc71")
        filters_layout = QGridLayout()
        
        # Status Filter
        self.employee_status_combo = QComboBox()
        self.employee_status_combo.addItems(["الكل", "نشط", "غير نشط"])
        filters_layout.addWidget(QLabel("الحالة:"), 0, 0)
        filters_layout.addWidget(self.employee_status_combo, 0, 1)
        
        # Role Filter
        self.role_combo = QComboBox()
        self.role_combo.addItems(["الكل", "موظف", "مدير فرع"])
        filters_layout.addWidget(QLabel("الدور:"), 1, 0)
        filters_layout.addWidget(self.role_combo, 1, 1)
        
        # Action Buttons
        generate_btn = ModernButton("توليد التقرير", color="#2ecc71")
        generate_btn.clicked.connect(self.generate_employee_report)
        filters_layout.addWidget(generate_btn, 2, 0, 1, 2)
        
        export_btn = ModernButton("تصدير إلى CSV", color="#e67e22")
        export_btn.clicked.connect(self.export_employee_report)
        filters_layout.addWidget(export_btn, 2, 2, 1, 2)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Employees Table
        self.employee_report_table = QTableWidget()
        self.employee_report_table.setColumnCount(5)
        self.employee_report_table.setHorizontalHeaderLabels([
            "اسم المستخدم", "الدور", "الحالة", "تاريخ الإنشاء", "آخر نشاط"
        ])
        self.employee_report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.employee_report_table.setStyleSheet(self.transfer_report_table.styleSheet())
        
        layout.addWidget(self.employee_report_table)     
        
    def generate_transfer_report(self):
        """Generate transfer report with accurate filtering and sorting"""
        try:
            # Clear previous data and initialize
            self.transfer_report_table.setRowCount(0)
            self.statusBar().showMessage("جاري تحميل التقرير...")
            QApplication.processEvents()

            # Validate date selection
            if self.report_date_from.date() > self.report_date_to.date():
                QMessageBox.warning(self, "خطأ في التاريخ", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
                return

            # Get date objects for filtering
            selected_start_date = self.report_date_from.date().toPyDate()
            selected_end_date = self.report_date_to.date().toPyDate()

            # Format dates for backend requests (without time)
            date_from = self.report_date_from.date().toString("yyyy-MM-dd")
            date_to = self.report_date_to.date().toString("yyyy-MM-dd")

            # Get status filter
            status_filter = {
                "مكتمل": "completed",
                "قيد المعالجة": "processing",
                "ملغي": "cancelled",
                "مرفوض": "rejected",
                "معلق": "on_hold",
                "الكل": None
            }.get(self.status_combo.currentText())

            all_transactions = []
            transfer_type = self.transfer_type_combo.currentText()

            # Common parameters for both outgoing and incoming
            base_params = {
                "start_date": date_from,
                "end_date": date_to,
                "status": status_filter,
                "page": 1,
                "per_page": 100
            }

            # Fetch outgoing transactions (صادر)
            if transfer_type in ["صادر", "الكل"]:
                outgoing_params = base_params.copy()
                outgoing_params["branch_id"] = self.branch_id
                outgoing_page = 1
                while True:
                    outgoing_response = requests.get(
                        f"{self.api_url}/transactions/",
                        params={k: v for k, v in outgoing_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if outgoing_response.status_code == 200:
                        outgoing_data = outgoing_response.json()
                        for t in outgoing_data.get("transactions", []):
                            t["transaction_type"] = "outgoing"
                        all_transactions.extend(outgoing_data.get("transactions", []))
                        if outgoing_page >= outgoing_data.get("total_pages", 1):
                            break
                        outgoing_page += 1
                        outgoing_params["page"] = outgoing_page
                    else:
                        break

            # Fetch incoming transactions (وارد)
            if transfer_type in ["وارد", "الكل"]:
                incoming_params = base_params.copy()
                incoming_params["destination_branch_id"] = self.branch_id
                incoming_page = 1
                while True:
                    incoming_response = requests.get(
                        f"{self.api_url}/transactions/",
                        params={k: v for k, v in incoming_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if incoming_response.status_code == 200:
                        incoming_data = incoming_response.json()
                        for t in incoming_data.get("transactions", []):
                            t["transaction_type"] = "incoming"
                        all_transactions.extend(incoming_data.get("transactions", []))
                        if incoming_page >= incoming_data.get("total_pages", 1):
                            break
                        incoming_page += 1
                        incoming_params["page"] = incoming_page
                    else:
                        break

            # Client-side filtering with proper date parsing and status check
            filtered_transactions = []
            for t in all_transactions:
                try:
                    # Parse transaction date
                    transaction_date = datetime.strptime(t.get("date", ""), "%Y-%m-%d %H:%M:%S").date()
                    
                    # Check date range
                    date_valid = selected_start_date <= transaction_date <= selected_end_date
                    
                    # Check status
                    status_valid = (status_filter is None) or (t.get("status", "").lower() == status_filter)
                    
                    if date_valid and status_valid:
                        filtered_transactions.append(t)
                except Exception as e:
                    print(f"Error processing transaction {t.get('id')}: {str(e)}")

            # Sort by date descending
            filtered_transactions.sort(
                key=lambda x: datetime.strptime(x.get("date", ""), "%Y-%m-%d %H:%M:%S"),
                reverse=True
            )

            # Apply pagination
            total_items = len(filtered_transactions)
            self.report_total_pages = max(1, (total_items + self.report_per_page - 1) // self.report_per_page)
            start_idx = (self.report_current_page - 1) * self.report_per_page
            end_idx = start_idx + self.report_per_page
            transactions = filtered_transactions[start_idx:end_idx]

            # Populate table
            self.transfer_report_table.setRowCount(len(transactions))
            valid_count = 0

            for row, transaction in enumerate(transactions):
                try:
                    # Validate mandatory fields
                    required_fields = ['id', 'sender', 'receiver', 'amount', 'date', 'status']
                    if not all(field in transaction for field in required_fields):
                        continue

                    # Transaction Type
                    type_item = self.create_transaction_type_item(transaction)
                    self.transfer_report_table.setItem(row, 0, type_item)

                    # Transaction ID
                    trans_id = str(transaction.get("id", ""))
                    id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                    id_item.setToolTip(trans_id)
                    self.transfer_report_table.setItem(row, 1, id_item)

                    # Sender/Receiver
                    self.transfer_report_table.setItem(row, 2, QTableWidgetItem(transaction.get("sender", "غير معروف")))
                    self.transfer_report_table.setItem(row, 3, QTableWidgetItem(transaction.get("receiver", "غير معروف")))

                    # Amount formatting
                    amount = transaction.get("amount", 0)
                    try:
                        amount = float(amount)
                    except (TypeError, ValueError):
                        amount = 0.0
                    currency = transaction.get("currency", "ليرة سورية")
                    amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.transfer_report_table.setItem(row, 4, amount_item)

                    # Date parsing
                    raw_date = transaction.get("date", "")
                    try:
                        date_obj = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                        date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        date_str = raw_date if raw_date else "غير معروف"
                    self.transfer_report_table.setItem(row, 5, QTableWidgetItem(date_str))

                    # Status display
                    status = transaction.get("status", "").lower()
                    status_ar = self.get_status_arabic(status)
                    status_item = QTableWidgetItem(status_ar)
                    status_item.setBackground(self.get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transfer_report_table.setItem(row, 6, status_item)

                    # Branch information
                    branch_id = transaction.get("branch_id")
                    dest_branch_id = transaction.get("destination_branch_id")
                    sending_branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}" if branch_id else "غير معروف")
                    receiving_branch = self.branch_id_to_name.get(dest_branch_id, f"الفرع {dest_branch_id}" if dest_branch_id else "غير معروف")
                    self.transfer_report_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                    self.transfer_report_table.setItem(row, 8, QTableWidgetItem(receiving_branch))

                    # Employee information
                    employee_name = transaction.get("employee_name") or f"الموظف {transaction.get('employee_id', '')}"
                    self.transfer_report_table.setItem(row, 9, QTableWidgetItem(employee_name))

                    valid_count += 1

                except Exception as field_error:
                    print(f"Error processing row {row}: {str(field_error)}")
                    continue

            # Update UI
            self.update_pagination_controls()
            self.statusBar().showMessage(f"تم تحميل {valid_count} معاملة صالحة", 5000)

        except requests.exceptions.RequestException as e:
            self.handle_connection_error(e)
        except ValueError as e:
            self.handle_data_error(e)
        except Exception as e:
            self.handle_unexpected_error(e)

    def is_date_in_range(self, date_str, start_date, end_date):
        """Helper function to validate date range"""
        try:
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
            return start_date <= transaction_date <= end_date
        except ValueError:
            return False
            
    def generate_employee_report(self):
        """Generate employee report based on filters."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Map UI values to API parameters
            status_map = {
                "نشط": "active",
                "غير نشط": "inactive",
                "الكل": None
            }
            role_map = {
                "موظف": "employee",
                "مدير فرع": "branch_manager",
                "الكل": None
            }

            params = {
                "status": status_map.get(self.employee_status_combo.currentText()),
                "role": role_map.get(self.role_combo.currentText()),
                "branch_id": self.branch_id
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = requests.get(
                f"{self.api_url}/reports/employees/", 
                params=params, 
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Support multiple response formats
                employees = response_data.get("employees", 
                    response_data.get("items", 
                    response_data.get("results", [])))
                
                if not isinstance(employees, list):
                    QMessageBox.warning(self, "خطأ", "تنسيق البيانات غير صحيح")
                    self.employee_report_table.setRowCount(0)
                    return
                    
                self.employee_report_table.setRowCount(len(employees))
                
                for row, employee in enumerate(employees):
                    # Username
                    username_item = QTableWidgetItem(employee.get("username", "غير معروف"))
                    self.employee_report_table.setItem(row, 0, username_item)
                    
                    # Role
                    role = employee.get("role", "employee")
                    role_text = "مدير فرع" if role == "branch_manager" else "موظف"
                    role_item = QTableWidgetItem(role_text)
                    self.employee_report_table.setItem(row, 1, role_item)
                    
                    # Status with color
                    is_active = employee.get("is_active", 
                        employee.get("active", False))
                    status_text = "نشط" if is_active else "غير نشط"
                    status_item = QTableWidgetItem(status_text)
                    
                    # Set color correctly
                    color = QColor("#27ae60") if is_active else QColor("#e74c3c")
                    status_item.setForeground(color)
                    self.employee_report_table.setItem(row, 2, status_item)
                    
                    # Creation date
                    created_at = employee.get("created_at", "غير معروف")
                    created_item = QTableWidgetItem(created_at)
                    self.employee_report_table.setItem(row, 3, created_item)
                    
                    # Last activity
                    last_active = employee.get("last_login", 
                        employee.get("last_activity", "غير معروف"))
                    last_active_item = QTableWidgetItem(last_active)
                    self.employee_report_table.setItem(row, 4, last_active_item)
                    
                self.statusBar().showMessage("تم تحميل التقرير بنجاح", 3000)
                
            else:
                error_detail = response.json().get("detail", "فشل في تحميل البيانات")
                QMessageBox.warning(self, "خطأ", error_detail)
                
        except Exception as e:
            QMessageBox.critical(
                self, 
                "خطأ", 
                f"حدث خطأ غير متوقع:\n{str(e)}"
            )
            
            
    def prev_report_page(self):
        if self.report_current_page > 1:
            self.report_current_page -= 1
            self.generate_transfer_report()

    def next_report_page(self):
        if self.report_current_page < self.report_total_pages:
            self.report_current_page += 1
            self.generate_transfer_report()

    def update_pagination_controls(self):
        """Update report pagination controls."""
        self.report_page_label.setText(f"الصفحة: {self.report_current_page}/{self.report_total_pages}")
        self.prev_report_btn.setEnabled(self.report_current_page > 1)
        self.next_report_btn.setEnabled(self.report_current_page < self.report_total_pages)
    
    def setup_settings_tab(self):
        """Set up the settings tab."""
        layout = QVBoxLayout()
        
        # Branch settings
        branch_group = ModernGroupBox("معلومات الفرع", "#3498db")
        branch_layout = QFormLayout()
        
        self.branch_id_label = QLabel("جاري التحميل...")
        branch_layout.addRow("رمز الفرع:", self.branch_id_label)
        
        self.branch_name_field = QLabel("جاري التحميل...")
        branch_layout.addRow("اسم الفرع:", self.branch_name_field)
        
        self.branch_location_label = QLabel("جاري التحميل...")
        branch_layout.addRow("موقع الفرع:", self.branch_location_label)
        
        self.branch_governorate_label = QLabel("جاري التحميل...")
        branch_layout.addRow("المحافظة:", self.branch_governorate_label)
        
        branch_group.setLayout(branch_layout)
        layout.addWidget(branch_group)
        
        # Security settings
        security_group = ModernGroupBox("إعدادات الأمان", "#e74c3c")
        security_layout = QVBoxLayout()
        
        change_password_button = ModernButton("تغيير كلمة المرور", color="#3498db")
        change_password_button.clicked.connect(self.change_password)
        security_layout.addWidget(change_password_button)
        
        security_group.setLayout(security_layout)
        layout.addWidget(security_group)
        
        self.settings_tab.setLayout(layout)
    
    def refresh_dashboard_data(self):
        """Refresh all dashboard data"""
        try:
            # Load branches first for ID-to-name mapping
            self.load_branches()
            
            # Load financial status
            self.load_financial_status()
            
            # Update current date
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            self.date_label.setText(f"تاريخ اليوم: {current_date}")
            
            # Load employee statistics
            self.load_employee_stats()
            
            # Load transaction statistics
            self.load_transaction_stats()
            
            # Load recent transactions with pagination
            self.load_recent_transactions()
            
            # Update status bar
            self.statusBar().showMessage("تم تحديث البيانات بنجاح", 3000)
            
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            self.statusBar().showMessage("حدث خطأ أثناء تحديث البيانات", 5000)
            # Attempt partial refresh
            try:
                self.load_financial_status()
                self.load_recent_transactions()
            except Exception as fallback_error:
                print(f"Fallback refresh failed: {fallback_error}")
    
    def load_branch_info(self):
        """Load branch information."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            response = requests.get(f"{self.api_url}/branches/{self.branch_id}", headers=headers)
            
            if response.status_code == 200:
                branch = response.json()
                self.branch_name_label.setText(f"الفرع: {branch.get('name', '')}")
                self.branch_id_label.setText(branch.get('branch_id', ''))
                self.branch_name_field.setText(branch.get('name', ''))
                self.branch_location_label.setText(branch.get('location', ''))
                self.branch_governorate_label.setText(branch.get('governorate', ''))
                self.branch_governorate = branch.get('governorate', '')
            else:
                # Use empty values instead of hardcoded examples
                self.branch_name_label.setText("الفرع: ")
                self.branch_id_label.setText("")
                self.branch_name_field.setText("")
                self.branch_location_label.setText("")
                self.branch_governorate_label.setText("")
        except Exception as e:
            print(f"Error loading branch info: {e}")
            # Use empty values instead of hardcoded examples
            self.branch_name_label.setText("الفرع: ")
            self.branch_id_label.setText("")
            self.branch_name_field.setText("")
            self.branch_location_label.setText("")
            self.branch_governorate_label.setText("")
    
    def load_employee_stats(self):
        """Load employee statistics for this branch."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/{self.branch_id}/employees/stats/", headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                self.employees_count.setText(f"عدد الموظفين: {stats.get('total', 0)}")
                self.active_employees.setText(f"الموظفين النشطين: {stats.get('active', 0)}")
            else:
                # For testing/demo, use placeholder data
                self.employees_count.setText("عدد الموظفين: 0")
                self.active_employees.setText("الموظفين النشطين: 0")
        except Exception as e:
            print(f"Error loading employee stats: {e}")
            # For testing/demo, use placeholder data
            self.employees_count.setText("عدد الموظفين: 0")
            self.active_employees.setText("الموظفين النشطين: 0")
    
    def load_transaction_stats(self):
        """Load transaction statistics for this branch."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/{self.branch_id}/transactions/stats/", headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                self.transactions_count.setText(f"عدد التحويلات: {stats.get('total', 0)}")
                self.transactions_amount.setText(f"إجمالي مبالغ التحويلات: {stats.get('total_amount', 0)} ليرة سورية")
            else:
                # For testing/demo, use placeholder data
                self.transactions_count.setText("عدد التحويلات: 0")
                self.transactions_amount.setText("إجمالي مبالغ التحويلات: 0 ليرة سورية")
        except Exception as e:
            print(f"Error loading transaction stats: {e}")
            # For testing/demo, use placeholder data
            self.transactions_count.setText("عدد التحويلات: 0")
            self.transactions_amount.setText("إجمالي مبالغ التحويلات: 0 ليرة سورية")
    
    def load_recent_transactions(self):
        """Load recent transactions with proper client-side pagination"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            all_transactions = []

            # Fetch ALL outgoing transactions
            outgoing_page = 1
            while True:
                outgoing_response = requests.get(
                    f"{self.api_url}/transactions/",
                    headers=headers,
                    params={
                        "branch_id": self.branch_id,
                        "page": outgoing_page,
                        "per_page": 100  # Fetch large pages to reduce requests
                    }
                )
                if outgoing_response.status_code == 200:
                    outgoing_data = outgoing_response.json()
                    all_transactions.extend(outgoing_data.get("transactions", []))
                    if outgoing_page >= outgoing_data.get("total_pages", 1):
                        break
                    outgoing_page += 1
                else:
                    break

            # Fetch ALL incoming transactions
            incoming_page = 1
            while True:
                incoming_response = requests.get(
                    f"{self.api_url}/transactions/",
                    headers=headers,
                    params={
                        "destination_branch_id": self.branch_id,
                        "page": incoming_page,
                        "per_page": 100
                    }
                )
                if incoming_response.status_code == 200:
                    incoming_data = incoming_response.json()
                    all_transactions.extend(incoming_data.get("transactions", []))
                    if incoming_page >= incoming_data.get("total_pages", 1):
                        break
                    incoming_page += 1
                else:
                    break

            # Sort all transactions by date descending
            all_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)

            # Calculate pagination
            total_items = len(all_transactions)
            self.total_pages = max(1, (total_items + self.per_page - 1) // self.per_page)
            
            # Get current page slice
            start_idx = (self.current_page - 1) * self.per_page
            end_idx = start_idx + self.per_page
            transactions = all_transactions[start_idx:end_idx]

            # Clear and populate table
            self.recent_transactions_table.setRowCount(len(transactions))

            for row, transaction in enumerate(transactions):
                # Type indicator
                type_item = self.create_transaction_type_item(transaction)
                self.recent_transactions_table.setItem(row, 0, type_item)

                # Transaction ID
                id_item = QTableWidgetItem(transaction.get("id", "")[:8] + "...")
                self.recent_transactions_table.setItem(row, 1, id_item)

                # Sender
                sender_item = QTableWidgetItem(transaction.get("sender", ""))
                self.recent_transactions_table.setItem(row, 2, sender_item)

                # Receiver
                receiver_item = QTableWidgetItem(transaction.get("receiver", ""))
                self.recent_transactions_table.setItem(row, 3, receiver_item)

                # Amount
                amount = transaction.get("amount", 0)
                currency = transaction.get("currency", "ليرة سورية")
                amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
                self.recent_transactions_table.setItem(row, 4, amount_item)

                # Date
                date_item = QTableWidgetItem(transaction.get("date", ""))
                self.recent_transactions_table.setItem(row, 5, date_item)

                # Status
                status = self.get_status_arabic(transaction.get("status", ""))
                status_item = QTableWidgetItem(status)
                status_item.setBackground(self.get_status_color(transaction.get("status", "")))
                self.recent_transactions_table.setItem(row, 6, status_item)

                # Sending Branch
                sending_branch = self.branch_id_to_name.get(
                    transaction.get("branch_id"), 
                    "غير معروف"
                )
                self.recent_transactions_table.setItem(row, 7, QTableWidgetItem(sending_branch))

                # Receiving Branch
                receiving_branch = self.branch_id_to_name.get(
                    transaction.get("destination_branch_id"),
                    "غير معروف"
                )
                self.recent_transactions_table.setItem(row, 8, QTableWidgetItem(receiving_branch))

                # Employee Name
                employee_item = QTableWidgetItem(transaction.get("employee_name", ""))
                self.recent_transactions_table.setItem(row, 9, employee_item)

            # Update pagination controls
            self.page_label.setText(f"الصفحة: {self.current_page}/{self.total_pages}")
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < self.total_pages)

        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.load_placeholder_transactions()
            self.page_label.setText("الصفحة: 1/1")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            
    def update_pagination_buttons(self):
        """Enable/disable pagination buttons based on current page"""
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def prev_page(self):
        """Navigate to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_recent_transactions()

    def next_page(self):
        """Navigate to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_recent_transactions()        
            
    def load_branches(self):
        """Load all branches for ID-to-name mapping with transaction display fixes"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                branches = response_data.get("branches", [])
                
                # Reset the branch mapping
                self.branch_id_to_name = {}
                
                for branch in branches:
                    try:
                        if not isinstance(branch, dict):
                            continue
                            
                        branch_id = branch.get('id')
                        branch_name = branch.get('name', 'Unknown Branch')
                        
                        if branch_id is not None:
                            # Store only the branch name as string
                            self.branch_id_to_name[branch_id] = branch_name
                            
                            # If you need financial data elsewhere, store it separately
                            if hasattr(self, 'branch_financial_data'):
                                self.branch_financial_data[branch_id] = {
                                    'allocated': branch.get('allocated_amount', 0.0),
                                    'stats': branch.get('financial_stats', {})
                                }
                                
                    except Exception as branch_error:
                        print(f"Error processing branch: {branch_error}")
                        continue

            else:
                print(f"Failed to load branches. Status: {response.status_code}")
                self.branch_id_to_name = {}
                
            # Force refresh of transactions after loading branches
            self.load_recent_transactions()
            
        except requests.exceptions.RequestException as e:
            print(f"Network error loading branches: {str(e)}")
            self.branch_id_to_name = {}
        except ValueError as e:
            print(f"JSON decode error: {str(e)}")
            self.branch_id_to_name = {}
        except Exception as e:
            print(f"Unexpected error loading branches: {str(e)}")
            self.branch_id_to_name = {}
            
    def create_transaction_type_item(self, transaction):
        """Create type indicator item for transactions table"""
        transfer_type = ""
        color = QColor()
        
        sending_branch = transaction.get("branch_id")
        receiving_branch = transaction.get("destination_branch_id")
        
        if sending_branch == self.branch_id:
            transfer_type = "↑ صادر"  # Outgoing
            color = QColor(0, 150, 0)  # Green
        elif receiving_branch == self.branch_id:
            transfer_type = "↓ وارد"  # Incoming
            color = QColor(150, 0, 0)  # Red
        else:
            transfer_type = "↔ أخرى"   # Other
            color = QColor(100, 100, 100)
        
        item = QTableWidgetItem(transfer_type)
        item.setForeground(color)
        item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        return item

    def get_status_arabic(self, status):
        """Convert status to Arabic."""
        status_map = {
            "processing": "قيد المعالجة",
            "completed": "مكتمل",
            "cancelled": "ملغي",
            "rejected": "مرفوض",
            "on_hold": "معلق"
        }
        return status_map.get(status, status)

    def get_status_color(self, status):
        """Get color for status."""
        status_colors = {
            "processing": QColor(200, 200, 255), # Light blue
            "completed": QColor(200, 255, 200),  # Light green
            "cancelled": QColor(255, 200, 200),  # Light red
            "rejected": QColor(255, 150, 150),   # Darker red
            "on_hold": QColor(255, 200, 150)     # Light orange
        }
        return status_colors.get(status, QColor(255, 255, 255))        
            
    
    def load_placeholder_transactions(self):
        """Load placeholder transaction data for testing/demo."""
        placeholder_transactions = []
        
        self.recent_transactions_table.setRowCount(len(placeholder_transactions))
        
        for row, transaction in enumerate(placeholder_transactions):
            type_item = self.create_transaction_type_item(transaction)
            self.recent_transactions_table.setItem(row, 0, type_item)
            
            # Transaction ID
            id_item = QTableWidgetItem(transaction.get("id", "")[:8] + "...")
            self.recent_transactions_table.setItem(row, 1, id_item)
            
            # Sender
            sender_item = QTableWidgetItem(transaction.get("sender", ""))
            self.recent_transactions_table.setItem(row, 2, sender_item)
            
            # Receiver
            receiver_item = QTableWidgetItem(transaction.get("receiver", ""))
            self.recent_transactions_table.setItem(row, 3, receiver_item)
            
            # Amount
            amount = transaction.get("amount", 0)
            currency = transaction.get("currency", "ليرة سورية")
            amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
            self.recent_transactions_table.setItem(row, 4, amount_item)
            
            # Date
            date_item = QTableWidgetItem(transaction.get("date", ""))
            self.recent_transactions_table.setItem(row, 5, date_item)
            
            # Status
            status_item = QTableWidgetItem(self.get_status_arabic(transaction.get("status", "")))
            status_item.setBackground(self.get_status_color(transaction.get("status", "")))
            self.recent_transactions_table.setItem(row, 6, status_item)
            
            # Employee Name (Column 7)
            employee_item = QTableWidgetItem(transaction.get("employee_name", ""))
            self.recent_transactions_table.setItem(row, 7, employee_item)
            
            # Receiving Branch (Column 8)
            branch_item = QTableWidgetItem(transaction.get("destination_branch_name", "غير معروف"))
            self.recent_transactions_table.setItem(row, 8, branch_item)
            
            # Receiving Governorate (Column 9)
            gov_item = QTableWidgetItem(transaction.get("receiver_governorate", ""))
            self.recent_transactions_table.setItem(row, 9, gov_item)
    
    def add_employee(self):
        dialog = AddEmployeeDialog(
            is_admin=False,  # Force non-admin mode
            branch_id=self.branch_id,
            token=self.token,
            current_user_id=self.user_id  # Pass current user ID
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_employees()
    
    def load_employees(self):
        """Load employees data for this branch with security restrictions"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}/employees/",
                headers=headers
            )
            
            if response.status_code == 200:
                employees = response.json()
                self.employees_table.setRowCount(len(employees))
                
                for row, employee in enumerate(employees):
                    # Employee ID and Role
                    employee_id = employee.get("id")
                    employee_role = employee.get("role", "employee")
                    is_manager = employee_role == "branch_manager"
                    is_current_user = str(employee_id) == str(self.user_id)

                    # Username
                    username_item = QTableWidgetItem(employee.get("username", ""))
                    self.employees_table.setItem(row, 0, username_item)
                    
                    # Role (display Arabic text)
                    role_text = "مدير فرع" if is_manager else "موظف"
                    role_item = QTableWidgetItem(role_text)
                    self.employees_table.setItem(row, 1, role_item)
                    
                    # Status
                    status_item = QTableWidgetItem("نشط")
                    status_color = QColor("#27ae60") if employee.get("active", True) else QColor("#e74c3c")
                    status_item.setForeground(status_color)
                    self.employees_table.setItem(row, 2, status_item)
                    
                    # Creation date
                    date_item = QTableWidgetItem(employee.get("created_at", ""))
                    self.employees_table.setItem(row, 3, date_item)
                    
                    # Actions
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Edit Button
                    edit_button = QPushButton("تعديل")
                    edit_button.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border-radius: 3px;
                            padding: 3px;
                        }
                        QPushButton:disabled {
                            background-color: #95a5a6;
                        }
                        QPushButton:hover:!disabled {
                            background-color: #2980b9;
                        }
                    """)
                    
                    # Delete Button
                    delete_button = QPushButton("حذف")
                    delete_button.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: white;
                            border-radius: 3px;
                            padding: 3px;
                        }
                        QPushButton:disabled {
                            background-color: #95a5a6;
                        }
                        QPushButton:hover:!disabled {
                            background-color: #c0392b;
                        }
                    """)
                    
                    # Disable actions for managers and current user
                    if is_manager or is_current_user:
                        edit_button.setEnabled(False)
                        delete_button.setEnabled(False)
                        edit_button.setToolTip("غير مسموح بتعديل المديرين أو حسابك الخاص")
                        delete_button.setToolTip("غير مسموح بحذف المديرين أو حسابك الخاص")
                    else:
                        edit_button.clicked.connect(lambda _, e=employee: self.edit_employee(e))
                        delete_button.clicked.connect(lambda _, e=employee: self.delete_employee(e))
                    
                    actions_layout.addWidget(edit_button)
                    actions_layout.addWidget(delete_button)
                    self.employees_table.setCellWidget(row, 4, actions_widget)
                    
            else:
                self.load_placeholder_employees()
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل البيانات: {response.status_code}")
                
        except Exception as e:
            print(f"Error loading employees: {e}")
            self.load_placeholder_employees()
            QMessageBox.critical(self, "خطأ", "تعذر الاتصال بالخادم")
    
    def load_placeholder_employees(self):
        """Load placeholder employee data for testing/demo."""
        placeholder_employees = []
        
        self.employees_table.setRowCount(len(placeholder_employees))
        
        for row, employee in enumerate(placeholder_employees):
            # Username
            username_item = QTableWidgetItem(employee.get("username", ""))
            self.employees_table.setItem(row, 0, username_item)
            
            # Role
            role_text = "موظف"
            role_item = QTableWidgetItem(role_text)
            self.employees_table.setItem(row, 1, role_item)
            
            # Status
            status_item = QTableWidgetItem("نشط")
            status_item.setForeground(QColor("#27ae60"))
            self.employees_table.setItem(row, 2, status_item)
            
            # Creation date
            date_item = QTableWidgetItem(employee.get("created_at", ""))
            self.employees_table.setItem(row, 3, date_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_button = QPushButton("تعديل")
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border-radius: 3px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            edit_button.clicked.connect(lambda checked, e=employee: self.edit_employee(e))
            actions_layout.addWidget(edit_button)
            
            delete_button = QPushButton("حذف")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border-radius: 3px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            delete_button.clicked.connect(lambda checked, e=employee: self.delete_employee(e))
            actions_layout.addWidget(delete_button)
            
            self.employees_table.setCellWidget(row, 4, actions_widget)
    
    def edit_employee(self, employee):
        if employee.get('id') == self.user_id:
            QMessageBox.warning(self, "تحذير", "لا يمكنك تعديل حسابك الخاص!")
            return

        dialog = EditEmployeeDialog(
            employee_data=employee,
            token=self.token,
            is_admin=False,
            current_branch_id=self.branch_id,
            current_user_id=self.user_id
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_employees()
    
    def delete_employee(self, employee):
        """Delete an employee."""
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل أنت متأكد من حذف الموظف {employee.get('username', '')}؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                response = requests.delete(f"{self.api_url}/users/{employee.get('id')}", headers=headers)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "نجاح", "تم حذف الموظف بنجاح!")
                    self.load_employees()  # Refresh the list
                else:
                    QMessageBox.warning(self, "خطأ", f"فشل حذف الموظف: {response.status_code}")
            except Exception as e:
                print(f"Error deleting employee: {e}")
                QMessageBox.warning(self, "خطأ", f"تعذر حذف الموظف: {str(e)}")
    
    def search_user(self):
        """Open user search dialog."""
        dialog = UserSearchDialog(self.token, self)
        dialog.exec()
    
    def new_transfer(self):
        """Switch to transfers tab for a new transfer."""
        self.tab_widget.setCurrentIndex(2)  # Switch to transfers tab
    
    def generate_report(self, report_type):
        """Generate a report based on the selected type and filters."""
        date_from = self.date_from_input.text()
        date_to = self.date_to_input.text()
        
        # Clear previous report
        self.report_preview.setRowCount(0)
        
        # Set up columns based on report type
        if report_type == "transactions":
            self.report_preview.setColumnCount(6)
            self.report_preview.setHorizontalHeaderLabels([
                "رقم التحويل", "التاريخ", "المرسل", "المستلم", "المبلغ", "الحالة"
            ])
        elif report_type == "employees":
            self.report_preview.setColumnCount(4)
            self.report_preview.setHorizontalHeaderLabels([
                "اسم المستخدم", "الدور", "تاريخ الإنشاء", "الحالة"
            ])
        
        # Load report data
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            params = {
                "date_from": date_from if date_from else None,
                "date_to": date_to if date_to else None,
                "branch_id": self.branch_id
            }
            
            response = requests.get(f"{self.api_url}/reports/{report_type}/", params=params, headers=headers)
            
            if response.status_code == 200:
                report_data = response.json()
                items = report_data.get("items", [])
                
                self.report_preview.setRowCount(len(items))
                
                if report_type == "transactions":
                    for row, item in enumerate(items):
                        self.report_preview.setItem(row, 0, QTableWidgetItem(item.get("id", "")))
                        self.report_preview.setItem(row, 1, QTableWidgetItem(item.get("date", "")))
                        self.report_preview.setItem(row, 2, QTableWidgetItem(item.get("sender", "")))
                        self.report_preview.setItem(row, 3, QTableWidgetItem(item.get("receiver", "")))
                        self.report_preview.setItem(row, 4, QTableWidgetItem(f"{item.get('amount', 0)} {item.get('currency', '')}"))
                        
                        status_item = QTableWidgetItem(item.get("status", ""))
                        if item.get("status") == "completed":
                            status_item.setForeground(QColor("#27ae60"))
                        elif item.get("status") == "processing":
                            status_item.setForeground(QColor("#f39c12"))
                        else:
                            status_item.setForeground(QColor("#e74c3c"))
                        self.report_preview.setItem(row, 5, status_item)
                
                elif report_type == "employees":
                    for row, item in enumerate(items):
                        self.report_preview.setItem(row, 0, QTableWidgetItem(item.get("username", "")))
                        
                        role_text = "موظف"
                        self.report_preview.setItem(row, 1, QTableWidgetItem(role_text))
                        
                        self.report_preview.setItem(row, 2, QTableWidgetItem(item.get("created_at", "")))
                        
                        status_item = QTableWidgetItem("نشط")
                        status_item.setForeground(QColor("#27ae60"))
                        self.report_preview.setItem(row, 3, status_item)
            else:
                # For testing/demo, load placeholder data
                self.load_placeholder_report(report_type)
        except Exception as e:
            print(f"Error generating report: {e}")
            # For testing/demo, load placeholder data
            self.load_placeholder_report(report_type)
    
    def load_placeholder_report(self, report_type):
        """Load placeholder report data for testing/demo."""
        if report_type == "transactions":
            placeholder_items = []
            
            self.report_preview.setRowCount(len(placeholder_items))
            
            for row, item in enumerate(placeholder_items):
                self.report_preview.setItem(row, 0, QTableWidgetItem(item.get("id", "")))
                self.report_preview.setItem(row, 1, QTableWidgetItem(item.get("date", "")))
                self.report_preview.setItem(row, 2, QTableWidgetItem(item.get("sender", "")))
                self.report_preview.setItem(row, 3, QTableWidgetItem(item.get("receiver", "")))
                self.report_preview.setItem(row, 4, QTableWidgetItem(f"{item.get('amount', 0)} {item.get('currency', '')}"))
                
                status_item = QTableWidgetItem(item.get("status", ""))
                if item.get("status") == "completed":
                    status_item.setForeground(QColor("#27ae60"))
                elif item.get("status") == "processing":
                    status_item.setForeground(QColor("#f39c12"))
                else:
                    status_item.setForeground(QColor("#e74c3c"))
                self.report_preview.setItem(row, 5, status_item)
        
        elif report_type == "employees":
            placeholder_items = []
            
            self.report_preview.setRowCount(len(placeholder_items))
            
            for row, item in enumerate(placeholder_items):
                self.report_preview.setItem(row, 0, QTableWidgetItem(item.get("username", "")))
                
                role_text = "موظف"
                self.report_preview.setItem(row, 1, QTableWidgetItem(role_text))
                
                self.report_preview.setItem(row, 2, QTableWidgetItem(item.get("created_at", "")))
                
                status_item = QTableWidgetItem("نشط")
                status_item.setForeground(QColor("#27ae60"))
                self.report_preview.setItem(row, 3, status_item)
    
    def export_transfer_report(self):
        """Export transfer report to CSV and PDF"""
        try:
            if self.transfer_report_table.rowCount() == 0:
                QMessageBox.warning(self, "تحذير", "لا يوجد بيانات للتصدير!")
                return

            # Get save path
            path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير", "", 
                "ملفات PDF (*.pdf);;ملفات CSV (*.csv)"
            )
            
            if not path:
                return  # User cancelled

            # Prepare data
            headers = [self.transfer_report_table.horizontalHeaderItem(i).text() 
                    for i in range(self.transfer_report_table.columnCount())]
            
            rows = []
            for row in range(self.transfer_report_table.rowCount()):
                rows.append([
                    self.transfer_report_table.item(row, col).text().strip()
                    for col in range(self.transfer_report_table.columnCount())
                ])

            # Export based on file type
            try:
                if path.lower().endswith('.csv'):
                    self.export_to_csv(path, headers, rows)
                    QMessageBox.information(self, "نجاح", "تم التصدير بنجاح!")
                
            except PermissionError:
                QMessageBox.critical(self, "خطأ", "الملف مفتوح في تطبيق آخر. أغلقه ثم حاول مرة أخرى")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تجهيز البيانات: {str(e)}")


    def export_employee_report(self):
        """Export employee report to CSV and PDF"""
        try:
            if self.employee_report_table.rowCount() == 0:
                QMessageBox.warning(self, "تحذير", "لا يوجد بيانات للتصدير!")
                return

            # Get save path
            path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير", "", 
                "ملفات PDF (*.pdf);;ملفات CSV (*.csv)"
            )
            
            if not path:
                return  # User cancelled

            # Prepare data
            headers = [self.employee_report_table.horizontalHeaderItem(i).text() 
                    for i in range(self.employee_report_table.columnCount())]
            
            rows = []
            for row in range(self.employee_report_table.rowCount()):
                rows.append([
                    self.employee_report_table.item(row, col).text().strip()
                    for col in range(self.employee_report_table.columnCount())
                ])

            # Export based on file type
            try:
                if path.lower().endswith('.csv'):
                    self.export_to_csv(path, headers, rows)
                    QMessageBox.information(self, "نجاح", "تم التصدير بنجاح!")
                
            except PermissionError:
                QMessageBox.critical(self, "خطأ", "الملف مفتوح في تطبيق آخر. أغلقه ثم حاول مرة أخرى")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تجهيز البيانات: {str(e)}")
        
    def export_to_csv(self, path, headers, rows):
        """Export data to CSV file"""
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)    
            
    def change_password(self):
        """Open the change password dialog for the branch manager."""
        dialog = ChangePasswordDialog(self.token)
        dialog.exec()        
            
class QDateEditCalendarPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اختر تاريخ")
        self.setLayout(QVBoxLayout())
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.layout().addWidget(self.calendar)
        
        # Set initial date from parent QDateEdit
        if parent:
            self.calendar.setSelectedDate(parent.date())
            
        # Confirm button
        btn_confirm = QPushButton("تأكيد")
        btn_confirm.clicked.connect(self.accept)
        self.layout().addWidget(btn_confirm)
        
    def selectedDate(self):
        return self.calendar.selectedDate()        
