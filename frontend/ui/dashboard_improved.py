import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
    QDialog, QLineEdit, QFormLayout, QComboBox, QGroupBox, QGridLayout, 
    QStatusBar
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QDate
from ui.money_transfer_improved import MoneyTransferApp
from dashboard.branch_management import BranchManagementMixin
from ui.user_search import UserSearchDialog
from ui.custom_widgets import ModernGroupBox, ModernButton
from utils.helpers import get_status_arabic, get_status_color, format_currency
from api.client import APIClient
from dashboard.branch_allocation import BranchAllocationMixin
from ui.menu_auth import MenuAuthMixin
from dashboard.receipt_printer import ReceiptPrinterMixin
from dashboard.report_handler import ReportHandlerMixin
from dashboard.settings_handler import SettingsHandlerMixin
from dashboard.employee_management import EmployeeManagementMixin

import os

class DirectorDashboard(QMainWindow, BranchAllocationMixin, MenuAuthMixin, ReceiptPrinterMixin, ReportHandlerMixin, SettingsHandlerMixin, EmployeeManagementMixin, BranchManagementMixin):
    """Dashboard for the director role."""
    
    def __init__(self, token=None):
        super().__init__()
        self.token = token
        self.api_url = os.environ["API_URL"]
        self.current_page = 1
        self.total_pages = 1
        self.per_page = 7
        self.current_page_transactions = 1
        self.transactions_per_page = 15
        self.total_pages_transactions = 1
        self.api_client = APIClient(token)
        
        # Add timer for auto-refreshing transactions
        self.transaction_timer = QTimer(self)
        self.transaction_timer.timeout.connect(self.load_recent_transactions)
        self.transaction_timer.start(30000)  # 5000 ms = 5 seconds
        
        self.setWindowTitle("لوحة تحكم المدير")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.7);
            }
            QTabBar::tab {
                background-color: #ddd;
                padding: 10px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Logo/Title
        logo_label = QLabel("نظام التحويلات المالية")
        logo_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(logo_label)
        
        # Spacer
        header_layout.addStretch()
        
        # User info
        user_info = QLabel("مدير النظام")
        user_info.setFont(QFont("Arial", 12))
        user_info.setStyleSheet("color: #7f8c8d;")
        header_layout.addWidget(user_info)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Dashboard tab
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "لوحة المعلومات")
        
        # Branches tab
        self.branches_tab = QWidget()
        self.setup_branches_tab()
        self.tabs.addTab(self.branches_tab, "الفروع")
        
        # Employees tab
        self.employees_tab = QWidget()
        self.setup_employees_tab()
        self.tabs.addTab(self.employees_tab, "الموظفين")
        
        # Transactions tab
        self.transactions_tab = QWidget()
        self.setup_transactions_tab()
        self.tabs.addTab(self.transactions_tab, "التحويلات")
        
        # Admin Money Transfer tab
        self.admin_transfer_tab = QWidget()
        self.setup_admin_transfer_tab()
        self.tabs.addTab(self.admin_transfer_tab, "تحويل الأموال")
        
        # Reports tab
        self.reports_tab = QWidget()
        self.setup_reports_tab()
        self.tabs.addTab(self.reports_tab, "التقارير")
        
        # Inventory tab (new)
        self.inventory_tab = QWidget()
        self.setup_inventory_tab()
        self.tabs.addTab(self.inventory_tab, "المخزون")
        
        # Settings tab
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "الإعدادات")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("جاهز")
        
        # Load initial data
        self.load_dashboard_data()
        self.load_branches()
        self.load_employees()
        self.load_transactions()
        
        # Load branch filters for all tabs at once
        self.load_branches_for_filter()
        
        # Initialize branch_id_to_name mapping if not already done
        if not hasattr(self, 'branch_id_to_name'):
            self.branch_id_to_name = {}
        
        # Set up timers for automatic refresh
        self.branch_timer = QTimer()
        self.branch_timer.timeout.connect(self.refresh_branches)
        self.branch_timer.start(30000)  # Refresh every 5 seconds
        
    def setup_admin_transfer_tab(self):
        """Set up the admin money transfer tab with unrestricted capabilities."""
        layout = QVBoxLayout()
        
        # Create the money transfer widget for System Manager with unrestricted capabilities
        self.admin_transfer_widget = MoneyTransferApp(
            user_token=self.token,
            branch_id=0,  # Main Branch with branch number 0
            user_id=0,    # System Manager ID is 0
            user_role="director",  # Special role for unrestricted access
            username="system_manager",
            full_name="System Manager",  # Set employee name to "System Manager"
        )
        
        layout.addWidget(self.admin_transfer_widget)
        self.admin_transfer_tab.setLayout(layout)    
    
    def setup_dashboard_tab(self):
        """Set up the dashboard tab with statistics and charts."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("لوحة المعلومات")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Statistics cards
        stats_layout = QHBoxLayout()
        
        # Branches card
        self.branches_card = ModernGroupBox("الفروع", "#3498db")
        branches_layout = QVBoxLayout()
        self.branches_count = QLabel("0")
        self.branches_count.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.branches_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branches_count.setStyleSheet("color: #3498db;")
        branches_layout.addWidget(self.branches_count)
        branches_label = QLabel("إجمالي الفروع")
        branches_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        branches_layout.addWidget(branches_label)
        self.branches_card.setLayout(branches_layout)
        stats_layout.addWidget(self.branches_card)
        
        # Employees card
        self.employees_card = ModernGroupBox("الموظفين", "#2ecc71")
        employees_layout = QVBoxLayout()
        self.employees_count = QLabel("0")
        self.employees_count.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.employees_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.employees_count.setStyleSheet("color: #2ecc71;")
        employees_layout.addWidget(self.employees_count)
        employees_label = QLabel("إجمالي الموظفين")
        employees_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        employees_layout.addWidget(employees_label)
        self.employees_card.setLayout(employees_layout)
        stats_layout.addWidget(self.employees_card)
        
        # Transactions card
        self.transactions_card = ModernGroupBox("التحويلات", "#e74c3c")
        transactions_layout = QVBoxLayout()
        self.transactions_count = QLabel("0")
        self.transactions_count.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.transactions_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transactions_count.setStyleSheet("color: #e74c3c;")
        transactions_layout.addWidget(self.transactions_count)
        transactions_label = QLabel("إجمالي التحويلات")
        transactions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transactions_layout.addWidget(transactions_label)
        self.transactions_card.setLayout(transactions_layout)
        stats_layout.addWidget(self.transactions_card)
        
        # Amount card
        self.amount_card = ModernGroupBox("المبالغ", "#f39c12")
        amount_layout = QVBoxLayout()
        self.amount_total = QLabel("0")
        self.amount_total.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.amount_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_total.setStyleSheet("color: #f39c12;")
        amount_layout.addWidget(self.amount_total)
        amount_label = QLabel("إجمالي المبالغ")
        amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        amount_layout.addWidget(amount_label)
        self.amount_card.setLayout(amount_layout)
        stats_layout.addWidget(self.amount_card)
        
        layout.addLayout(stats_layout)
        
        # Charts section - replaced with placeholder since matplotlib is not available
        charts_layout = QHBoxLayout()
        
        # Statistics by Branch
        stats_group = ModernGroupBox("إحصائيات الفروع", "#3498db")
        stats_layout = QHBoxLayout()
        
        # Transfers by Branch
        transfers_group = QGroupBox("التحويلات حسب الفرع")
        transfers_layout = QVBoxLayout()
        
        self.transfers_bars = QLabel()
        self.transfers_bars.setTextFormat(Qt.TextFormat.RichText)
        self.transfers_bars.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transfers_bars.setStyleSheet("font-family: Arial; color: #333;")
        transfers_layout.addWidget(self.transfers_bars)
        
        transfers_group.setLayout(transfers_layout)
        stats_layout.addWidget(transfers_group)
        
        # Amounts by Branch
        amounts_group = QGroupBox("المبالغ حسب الفرع")
        amounts_layout = QVBoxLayout()
        
        self.amounts_bars = QLabel()
        self.amounts_bars.setTextFormat(Qt.TextFormat.RichText)
        self.amounts_bars.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amounts_bars.setStyleSheet("font-family: Arial; color: #333;")
        amounts_layout.addWidget(self.amounts_bars)
        
        amounts_group.setLayout(amounts_layout)
        stats_layout.addWidget(amounts_group)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addLayout(charts_layout)
        
        # Recent transactions
        recent_group = ModernGroupBox("أحدث التحويلات", "#3498db")
        recent_layout = QVBoxLayout()
        
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setColumnCount(11)  # Increased to 11 columns
        self.recent_transactions_table.setHorizontalHeaderLabels([
            "النوع", "رقم التحويل", 
            "المرسل",  "المستلم", "المبلغ", "التاريخ", "الحالة", "الفرع الصادر",
            "اتجاه الصادر","الفرع الوارد", "اتجاه الوارد", "اسم الموظف"
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
        
        recent_layout.addWidget(self.recent_transactions_table)
        recent_layout.addLayout(pagination_layout)
        
        # View all button
        view_all_button = ModernButton("عرض جميع التحويلات", color="#3498db")
        view_all_button.clicked.connect(lambda: self.tabs.setCurrentIndex(3))  # Switch to transactions tab
        recent_layout.addWidget(view_all_button)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # Load branch statistics
        self.load_branch_stats()
        
        self.dashboard_tab.setLayout(layout)
        self.load_recent_transactions()
        
    def create_transaction_type_item(self, transaction):
        """Enhanced direction indicators"""
        transfer_type = ""
        color = QColor()
        
        has_outgoing = transaction.get("branch_id") is not None
        has_incoming = transaction.get("destination_branch_id") is not None
        
        if has_outgoing and has_incoming:
            if transaction["branch_id"] == transaction["destination_branch_id"]:
                transfer_type = "↔ داخلي"
                color = QColor(150, 150, 0)  # Yellow
            else:
                transfer_type = "↔ بين فروع"
                color = QColor(0, 0, 150)  # Blue
        elif has_outgoing:
            transfer_type = "↑ صادر"
            color = QColor(0, 150, 0)  # Green
        elif has_incoming:
            transfer_type = "↓ وارد"
            color = QColor(150, 0, 0)  # Red
        else:
            transfer_type = "↔ نظامي"
            color = QColor(100, 100, 100)  # Gray
        
        item = QTableWidgetItem(transfer_type)
        item.setForeground(color)
        item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        return item
    
    def setup_employees_tab(self):
        """Set up the employees tab with proper filtering controls."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("إدارة الموظفين")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Filter controls
        filter_group = ModernGroupBox("تصفية الموظفين", "#3498db")
        filter_layout = QGridLayout()
        
        # Branch filter
        branch_label = QLabel("الفرع:")
        self.branch_filter = QComboBox()
        self.branch_filter.setMinimumWidth(250)
        self.load_branches_for_filter()
        self.branch_filter.currentIndexChanged.connect(self.filter_employees)
        
        # Search field
        search_label = QLabel("بحث:")
        self.employee_search = QLineEdit()
        self.employee_search.setPlaceholderText("ابحث باسم الموظف أو المعرف")
        self.employee_search.textChanged.connect(self.filter_employees)
        
        # Add widgets to filter layout
        filter_layout.addWidget(branch_label, 0, 0)
        filter_layout.addWidget(self.branch_filter, 0, 1)
        filter_layout.addWidget(search_label, 1, 0)
        filter_layout.addWidget(self.employee_search, 1, 1)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Employees table
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(5)
        self.employees_table.setHorizontalHeaderLabels([
            "اسم المستخدم", "الدور", "الفرع", "تاريخ الإنشاء", "الحالة"
        ])
        self.employees_table.horizontalHeader().setStretchLastSection(True)
        self.employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.employees_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.employees_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.employees_table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        add_employee_button = ModernButton("إضافة موظف", color="#2ecc71")
        add_employee_button.clicked.connect(self.add_employee)
        buttons_layout.addWidget(add_employee_button)
        
        edit_employee_button = ModernButton("تعديل الموظف", color="#3498db")
        edit_employee_button.clicked.connect(self.edit_employee)
        buttons_layout.addWidget(edit_employee_button)
        
        delete_employee_button = ModernButton("حذف الموظف", color="#e74c3c")
        delete_employee_button.clicked.connect(self.delete_employee)
        buttons_layout.addWidget(delete_employee_button)
        
        reset_password_button = ModernButton("إعادة تعيين كلمة المرور", color="#f39c12")
        reset_password_button.clicked.connect(self.reset_password)
        buttons_layout.addWidget(reset_password_button)
        
        refresh_button = ModernButton("تحديث", color="#9b59b6")
        refresh_button.clicked.connect(self.load_employees)
        buttons_layout.addWidget(refresh_button)
        
        layout.addLayout(buttons_layout)
        
        self.employee_search.textChanged.connect(self.filter_employees)
        
        self.employees_tab.setLayout(layout)
        
        self.load_employees()  # Initial load
    
    def setup_transactions_tab(self):
        """Set up the transactions tab."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("إدارة التحويلات")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Filter
        filter_layout = QHBoxLayout()
        
        filter_branch_label = QLabel("تصفية حسب الفرع:")
        filter_layout.addWidget(filter_branch_label)
        
        self.transaction_branch_filter = QComboBox()
        self.transaction_branch_filter.setMinimumWidth(150)
        self.transaction_branch_filter.currentIndexChanged.connect(self.filter_transactions)
        filter_layout.addWidget(self.transaction_branch_filter)
        
        filter_type_label = QLabel("نوع التصفية:")
        filter_layout.addWidget(filter_type_label)
        
        self.transaction_type_filter = QComboBox()
        self.transaction_type_filter.addItems(["الكل", "الواردة", "الصادرة", "متعلقة بالفرع"])
        self.transaction_type_filter.setMinimumWidth(150)
        self.transaction_type_filter.currentIndexChanged.connect(self.filter_transactions)
        filter_layout.addWidget(self.transaction_type_filter)
        
        # Add status filter using the provided statuses list
        status_filter_label = QLabel("تصفية حسب الحالة:")
        filter_layout.addWidget(status_filter_label)
        
        self.status_filter = QComboBox()
        # Add "All" option first
        self.status_filter.addItem("الكل", "all")
        
        # Add status options from the provided list
        statuses = [
            ("قيد الانتظار", "pending"),
            ("قيد المعالجة", "processing"),
            ("مكتمل", "completed"),
            ("ملغي", "cancelled"),
            ("مرفوض", "rejected"),
            ("معلق", "on_hold")
        ]
        
        for status_arabic, status_code in statuses:
            self.status_filter.addItem(status_arabic, status_code)
            
        self.status_filter.setMinimumWidth(150)
        self.status_filter.currentIndexChanged.connect(self.filter_transactions)
        filter_layout.addWidget(self.status_filter)
        
        filter_layout.addStretch()
        
        search_button = ModernButton("بحث", color="#3498db")
        search_button.clicked.connect(self.search_transaction)
        filter_layout.addWidget(search_button)
        
        layout.addLayout(filter_layout)
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(11)
        self.transactions_table.setHorizontalHeaderLabels([
            "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", "التاريخ", "الحالة", 
            "الفرع المرسل", "اتجاه الصادر", "الفرع المستلم", "اتجاه الوارد", "اسم الموظف"
        ])
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transactions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.transactions_table.setStyleSheet("""
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
        
        layout.addWidget(self.transactions_table)
        
        # Add pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_trans_button = ModernButton("السابق", color="#3498db")
        self.prev_trans_button.clicked.connect(self.prev_trans_page)
        pagination_layout.addWidget(self.prev_trans_button)
        
        self.trans_page_label = QLabel("الصفحة: 1")
        pagination_layout.addWidget(self.trans_page_label)
        
        self.next_trans_button = ModernButton("التالي", color="#3498db")
        self.next_trans_button.clicked.connect(self.next_trans_page)
        pagination_layout.addWidget(self.next_trans_button)
        
        layout.addLayout(pagination_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        view_transaction_button = ModernButton("عرض التفاصيل", color="#3498db")
        view_transaction_button.clicked.connect(self.view_transaction)
        buttons_layout.addWidget(view_transaction_button)
        
        update_status_button = ModernButton("تحديث الحالة", color="#f39c12")
        update_status_button.clicked.connect(self.update_transaction_status)
        buttons_layout.addWidget(update_status_button)
        
        print_receipt_button = ModernButton("طباعة الإيصال", color="#2ecc71")
        print_receipt_button.clicked.connect(self.print_receipt)
        buttons_layout.addWidget(print_receipt_button)
        
        refresh_button = ModernButton("تحديث", color="#9b59b6")
        refresh_button.clicked.connect(self.load_transactions)
        buttons_layout.addWidget(refresh_button)
        
        layout.addLayout(buttons_layout)
        
        self.transactions_tab.setLayout(layout)
    
    def load_dashboard_data(self):
        """Load data for the dashboard."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Load all dashboard components
            self.load_branch_stats()  # This now updates branches count
            
            # Get employee stats
            response = requests.get(f"{self.api_url}/users/stats/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.employees_count.setText(str(data.get("total", 0)))
            
            # Get transaction stats
            response = requests.get(f"{self.api_url}/transactions/stats/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.transactions_count.setText(str(data.get("total", 0)))
                self.amount_total.setText(f"{data.get('total_amount', 0):,.2f}")
            
            # Load recent transactions
            self.load_recent_transactions()
            
        except Exception as e:
            print(f"Error loading dashboard data: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل بيانات لوحة المعلومات: {str(e)}")
    
    def load_recent_transactions(self):
        """Load recent transactions with directional branch information"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/transactions/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                all_transactions = data.get("transactions", [])
                
                # Client-side pagination
                self.total_pages = (len(all_transactions) + self.per_page - 1) // self.per_page
                start_index = (self.current_page - 1) * self.per_page
                end_index = start_index + self.per_page
                transactions = all_transactions[start_index:end_index]
                
                # Create branch name mapping
                if not hasattr(self, 'branch_id_to_name'):
                    self.branch_id_to_name = {}
                    branches_response = self.api_client.get_branches()
                    if branches_response.status_code == 200:
                        branches = branches_response.json().get("branches", [])
                        self.branch_id_to_name = {b["id"]: b["name"] for b in branches}
                
                # Set column count and headers (if not already done)
                self.recent_transactions_table.setColumnCount(12)
                self.recent_transactions_table.setHorizontalHeaderLabels([
                    "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", 
                    "التاريخ", "الحالة", "الفرع المرسل", "اتجاه الصادر",
                    "الفرع المستلم", "اتجاه الوارد", "اسم الموظف"
                ])
                
                # Clear the table first
                self.recent_transactions_table.setRowCount(0)
                
                self.recent_transactions_table.setRowCount(len(transactions))
                
                for row, transaction in enumerate(transactions):
                    # Transaction Type
                    type_item = self.create_transaction_type_item(transaction)
                    self.recent_transactions_table.setItem(row, 0, type_item)
                    
                    # Transaction ID
                    trans_id = str(transaction.get("id", ""))
                    id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                    id_item.setToolTip(trans_id)
                    self.recent_transactions_table.setItem(row, 1, id_item)
                    
                    # Sender/Receiver
                    self.recent_transactions_table.setItem(row, 2, QTableWidgetItem(transaction.get("sender", "")))
                    self.recent_transactions_table.setItem(row, 3, QTableWidgetItem(transaction.get("receiver", "")))
                    
                    # Amount with proper currency formatting
                    amount = transaction.get("amount", 0)
                    currency = transaction.get("currency", "ليرة سورية")
                    formatted_amount = format_currency(amount, currency)
                    amount_item = QTableWidgetItem(formatted_amount)
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.recent_transactions_table.setItem(row, 4, amount_item)
                    
                    # Date
                    date_str = transaction.get("date", "")
                    self.recent_transactions_table.setItem(row, 5, QTableWidgetItem(date_str))
                    
                    # Status
                    status = transaction.get("status", "").lower()
                    status_ar = get_status_arabic(status)
                    status_item = QTableWidgetItem(status_ar)
                    status_item.setBackground(get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.recent_transactions_table.setItem(row, 6, status_item)
                    
                    # Sending Branch and Direction
                    branch_id = transaction.get("branch_id")
                    sending_branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}" if branch_id else "غير معروف")
                    self.recent_transactions_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                    
                    # Outgoing Direction Indicator
                    outgoing_direction = QTableWidgetItem("↑" if branch_id else "")
                    outgoing_direction.setForeground(QColor(0, 150, 0))  # Green color
                    outgoing_direction.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.recent_transactions_table.setItem(row, 8, outgoing_direction)
                    
                    # Receiving Branch and Direction
                    dest_branch_id = transaction.get("destination_branch_id")
                    receiving_branch = self.branch_id_to_name.get(dest_branch_id, f"الفرع {dest_branch_id}" if dest_branch_id else "غير معروف")
                    self.recent_transactions_table.setItem(row, 9, QTableWidgetItem(receiving_branch))
                    
                    # Incoming Direction Indicator
                    incoming_direction = QTableWidgetItem("↓" if dest_branch_id else "")
                    incoming_direction.setForeground(QColor(150, 0, 0))  # Red color
                    incoming_direction.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.recent_transactions_table.setItem(row, 10, incoming_direction)
                    
                    # Employee
                    self.recent_transactions_table.setItem(row, 11, QTableWidgetItem(transaction.get("employee_name", "")))

                self.update_pagination_controls()
                
        except Exception as e:
            print(f"Error loading recent transactions: {e}")
            self.statusBar().showMessage(f"خطأ في تحميل التحويلات: {str(e)}", 5000)

    def update_pagination_controls(self):
        """Update pagination controls."""
        self.page_label.setText(f"الصفحة: {self.current_page}/{self.total_pages}")
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def prev_page(self):
        """Navigate to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_recent_transactions()

    def next_page(self):
        """Navigate to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_recent_transactions()     
    
    def load_transactions(self, branch_id=None, filter_type="all", status=None):
        """Load transactions data with pagination and matching recent transactions style"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            url = f"{self.api_url}/transactions/"
            params = {}
            
            # Handle branch filtering
            if branch_id and isinstance(branch_id, (int, str)) and branch_id != self.api_url:
                try:
                    if isinstance(branch_id, str) and branch_id.isdigit():
                        branch_id = int(branch_id)
                    params["branch_id"] = branch_id
                except:
                    print(f"Invalid branch_id: {branch_id}")
            
            # Handle filter type
            if filter_type != "all":
                params["filter_type"] = filter_type
                
            # Handle status filtering
            if status and status != "all":
                params["status"] = status
            
            # Fetch all transactions
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                all_transactions = data.get("transactions", [])
                
                # Setup pagination
                self.transactions_per_page = 15
                self.total_pages_transactions = (len(all_transactions) + self.transactions_per_page - 1) // self.transactions_per_page
                start_index = (self.current_page_transactions - 1) * self.transactions_per_page
                end_index = start_index + self.transactions_per_page
                transactions = all_transactions[start_index:end_index]
                
                # Initialize table structure
                self.transactions_table.setColumnCount(12)
                self.transactions_table.setHorizontalHeaderLabels([
                    "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", 
                    "التاريخ", "الحالة", "الفرع المرسل", "اتجاه الصادر",
                    "الفرع المستلم", "اتجاه الوارد", "اسم الموظف"
                ])
                self.transactions_table.setRowCount(len(transactions))
                
                # Load branch names if not cached
                if not hasattr(self, 'branch_id_to_name'):
                    self.branch_id_to_name = {}
                    branches_response = self.api_client.get_branches()
                    if branches_response.status_code == 200:
                        branches = branches_response.json().get("branches", [])
                        self.branch_id_to_name = {b["id"]: b["name"] for b in branches}
                
                # Populate table rows
                for row, transaction in enumerate(transactions):
                    # Transaction Type
                    type_item = self.create_transaction_type_item(transaction)
                    self.transactions_table.setItem(row, 0, type_item)
                    
                    # Transaction ID
                    trans_id = str(transaction.get("id", ""))
                    id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                    id_item.setToolTip(trans_id)
                    self.transactions_table.setItem(row, 1, id_item)
                    
                    # Sender/Receiver
                    self.transactions_table.setItem(row, 2, QTableWidgetItem(transaction.get("sender", "")))
                    self.transactions_table.setItem(row, 3, QTableWidgetItem(transaction.get("receiver", "")))
                    
                    # Amount with proper currency formatting
                    amount = transaction.get("amount", 0)
                    currency = transaction.get("currency", "ليرة سورية")
                    formatted_amount = format_currency(amount, currency)
                    amount_item = QTableWidgetItem(formatted_amount)
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.transactions_table.setItem(row, 4, amount_item)
                    
                    # Date
                    date_str = transaction.get("date", "")
                    self.transactions_table.setItem(row, 5, QTableWidgetItem(date_str))
                    
                    # Status
                    status = transaction.get("status", "").lower()
                    status_ar = get_status_arabic(status)
                    status_item = QTableWidgetItem(status_ar)
                    status_item.setBackground(get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transactions_table.setItem(row, 6, status_item)
                    
                    # Branch information and directions
                    branch_id = transaction.get("branch_id")
                    dest_branch_id = transaction.get("destination_branch_id")
                    
                    # Sending Branch
                    sending_branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}" if branch_id else "غير معروف")
                    self.transactions_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                    
                    # Outgoing Direction
                    outgoing_direction = QTableWidgetItem("↑" if branch_id else "")
                    outgoing_direction.setForeground(QColor(0, 150, 0))
                    outgoing_direction.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transactions_table.setItem(row, 8, outgoing_direction)
                    
                    # Receiving Branch
                    receiving_branch = self.branch_id_to_name.get(dest_branch_id, f"الفرع {dest_branch_id}" if dest_branch_id else "غير معروف")
                    self.transactions_table.setItem(row, 9, QTableWidgetItem(receiving_branch))
                    
                    # Incoming Direction
                    incoming_direction = QTableWidgetItem("↓" if dest_branch_id else "")
                    incoming_direction.setForeground(QColor(150, 0, 0))
                    incoming_direction.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transactions_table.setItem(row, 10, incoming_direction)
                    
                    # Employee
                    self.transactions_table.setItem(row, 11, QTableWidgetItem(transaction.get("employee_name", "")))
                    
                    # Store transaction data
                    self.transactions_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, transaction)
                
                self.update_trans_pagination_controls()
                
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل التحويلات: رمز الحالة {response.status_code}")
        
        except Exception as e:
            print(f"Error loading transactions: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل التحويلات: {str(e)}")
    # Add these helper methods to the class
    def update_trans_pagination_controls(self):
        """Update transactions pagination controls."""
        self.trans_page_label.setText(f"الصفحة: {self.current_page_transactions}/{self.total_pages_transactions}")
        self.prev_trans_button.setEnabled(self.current_page_transactions > 1)
        self.next_trans_button.setEnabled(self.current_page_transactions < self.total_pages_transactions)

    def prev_trans_page(self):
        """Navigate to previous transactions page."""
        if self.current_page_transactions > 1:
            self.current_page_transactions -= 1
            self.load_transactions()

    def next_trans_page(self):
        """Navigate to next transactions page."""
        if self.current_page_transactions < self.total_pages_transactions:
            self.current_page_transactions += 1
            self.load_transactions()

    def show_no_results_message(self):
        self.employees_table.setRowCount(1)
        no_results = QTableWidgetItem("لا توجد نتائج")
        no_results.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.employees_table.setItem(0, 0, no_results)
        self.employees_table.setSpan(0, 0, 1, 5)
            
            
    def get_branch_name(self, branch_id):
        if not branch_id:
            return "غير محدد"
        
        # البحث في القائمة المنسدلة للفروع
        for index in range(self.branch_filter.count()):
            if self.branch_filter.itemData(index) == branch_id:
                return self.branch_filter.itemText(index)
        
        # إذا لم يتم العثور، جلب الاسم من الخادم
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/{branch_id}", headers=headers)
            if response.status_code == 200:
                return response.json().get("name", "غير محدد")
        except:
            pass
        
        return "غير محدد"    
    
    def filter_transactions(self):
        """Filter transactions by branch, type, and status."""
        # Get branch ID from the branch filter dropdown
        branch_id = self.transaction_branch_filter.currentData()
        # Ensure branch_id is not the API URL and is valid
        if branch_id == self.api_url or branch_id == "":
            branch_id = None
            
        # Map filter type from dropdown index to API parameter
        filter_type_map = {
            0: "all",
            1: "incoming",
            2: "outgoing",
            3: "branch_related"
        }
        
        filter_type = filter_type_map.get(self.transaction_type_filter.currentIndex(), "all")
        
        # Get status filter value
        status = self.status_filter.currentData()
        # Only pass status if it's not "all"
        if status == "all":
            status = None
        
        # Reset pagination to first page when applying filters
        self.current_page_transactions = 1
        
        # Load transactions with all filter parameters
        self.load_transactions(branch_id, filter_type, status)
    
    def search_user(self):
        """Open user search dialog."""
        dialog = UserSearchDialog(self.token, self)
        dialog.exec()
    
    def reset_password(self):
        """Reset password for the selected employee."""
        selected_rows = self.employees_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف لإعادة تعيين كلمة المرور")
            return
        
        row = selected_rows[0].row()
        employee_data = self.employees_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        employee_username = employee_data.get("username", "")
        
        # Create a dialog to reset password
        dialog = QDialog(self)
        dialog.setWindowTitle(f"إعادة تعيين كلمة المرور: {employee_username}")
        dialog.setGeometry(150, 150, 400, 200)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Password fields
        form_layout = QFormLayout()
        
        new_password_label = QLabel("كلمة المرور الجديدة:")
        new_password_input = QLineEdit()
        new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(new_password_label, new_password_input)
        
        confirm_password_label = QLabel("تأكيد كلمة المرور:")
        confirm_password_input = QLineEdit()
        confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(confirm_password_label, confirm_password_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_button = ModernButton("إلغاء", color="#e74c3c")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = ModernButton("حفظ", color="#2ecc71")
        
        def reset_password_action():
            new_password = new_password_input.text()
            confirm_password = confirm_password_input.text()
            
            if not new_password:
                QMessageBox.warning(dialog, "تنبيه", "الرجاء إدخال كلمة المرور الجديدة")
                return
            
            if new_password != confirm_password:
                QMessageBox.warning(dialog, "تنبيه", "كلمة المرور وتأكيدها غير متطابقين")
                return
            
            try:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                data = {
                    "username": employee_username,
                    "new_password": new_password
                }
                response = requests.post(f"{self.api_url}/reset-password/", json=data, headers=headers)
                
                if response.status_code == 200:
                    QMessageBox.information(dialog, "نجاح", "تم إعادة تعيين كلمة المرور بنجاح")
                    dialog.accept()
                else:
                    error_msg = f"فشل إعادة تعيين كلمة المرور: رمز الحالة {response.status_code}"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = error_data["detail"]
                    except:
                        pass
                    
                    QMessageBox.warning(dialog, "خطأ", error_msg)
            except Exception as e:
                print(f"Error resetting password: {e}")
                QMessageBox.warning(dialog, "خطأ", f"تعذر إعادة تعيين كلمة المرور: {str(e)}")
        
        save_button.clicked.connect(reset_password_action)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def view_transaction(self):
        """View details of the selected transaction."""
        selected_rows = self.transactions_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد تحويل للعرض")
            return
        
        row = selected_rows[0].row()
        transaction = self.transactions_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Create a dialog to display transaction details
        dialog = QDialog(self)
        dialog.setWindowTitle("تفاصيل التحويل")
        dialog.setGeometry(150, 150, 500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("تفاصيل التحويل")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Transaction details
        details_group = ModernGroupBox("معلومات التحويل", "#3498db")
        details_layout = QVBoxLayout()
        
        # Format transaction details
        details_text = f"""
        <b>رقم التحويل:</b> {transaction.get('id', '')}<br>
        <b>التاريخ:</b> {transaction.get('date', '')}<br>
        <br>
        <b>المرسل:</b> {transaction.get('sender', '')}<br>
        <b>رقم هاتف المرسل:</b> {transaction.get('sender_mobile', '')}<br>
        <b>محافظة المرسل:</b> {transaction.get('sender_governorate', '')}<br>
        <b>موقع المرسل:</b> {transaction.get('sender_location', '')}<br>
        <br>
        <b>المستلم:</b> {transaction.get('receiver', '')}<br>
        <b>رقم هاتف المستلم:</b> {transaction.get('receiver_mobile', '')}<br>
        <b>محافظة المستلم:</b> {transaction.get('receiver_governorate', '')}<br>
        <b>موقع المستلم:</b> {transaction.get('receiver_location', '')}<br>
        <br>
        <b>المبلغ:</b> {transaction.get('amount', '')} {transaction.get('currency', '')}<br>
        <b>الرسالة:</b> {transaction.get('message', '')}<br>
        <br>
        <b>الفرع:</b> {transaction.get('branch_governorate', '')}<br>
        <b>الموظف:</b> {transaction.get('employee_name', '')}<br>
        <b>الحالة:</b> {transaction.get('status', '')}
        """
        
        details_label = QLabel(details_text)
        details_label.setTextFormat(Qt.TextFormat.RichText)
        details_label.setWordWrap(True)
        details_layout.addWidget(details_label)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Close button
        close_button = ModernButton("إغلاق", color="#e74c3c")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def update_transaction_status(self):
        """Update status of the selected transaction."""
        selected_rows = self.transactions_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد تحويل لتحديث الحالة")
            return
        
        row = selected_rows[0].row()
        transaction = self.transactions_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        transaction_id = transaction.get('id', '')
        
        # Create a dialog to update status
        dialog = QDialog(self)
        dialog.setWindowTitle("تحديث حالة التحويل")
        dialog.setGeometry(150, 150, 400, 200)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Status selection
        form_layout = QFormLayout()
        
        status_label = QLabel("الحالة:")
        status_combo = QComboBox()
        status_combo.addItems(["قيد الانتظار", "تم الاستلام", "ملغي"])
        
        # Set current status
        current_status = transaction.get('status', '')
        if current_status == "completed":
            status_combo.setCurrentText("تم الاستلام")
        elif current_status == "cancelled":
            status_combo.setCurrentText("ملغي")
        else:
            status_combo.setCurrentText("قيد الانتظار")
        
        form_layout.addRow(status_label, status_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_button = ModernButton("إلغاء", color="#e74c3c")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = ModernButton("حفظ", color="#2ecc71")
        
        def update_status_action():
            # Map Arabic status to English
            status_map = {
                "قيد الانتظار": "processing",
                "تم الاستلام": "completed",
                "ملغي": "cancelled"
            }
            
            new_status = status_map.get(status_combo.currentText(), "processing")
            
            try:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                data = {
                    "transaction_id": transaction_id,
                    "status": new_status
                }
                response = requests.post(f"{self.api_url}/update-transaction-status/", json=data, headers=headers)
                
                if response.status_code == 200:
                    QMessageBox.information(dialog, "نجاح", "تم تحديث حالة التحويل بنجاح")
                    dialog.accept()
                    self.load_transactions()  # Refresh the transactions list
                else:
                    error_msg = f"فشل تحديث حالة التحويل: رمز الحالة {response.status_code}"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = error_data["detail"]
                    except:
                        pass
                    
                    QMessageBox.warning(dialog, "خطأ", error_msg)
            except Exception as e:
                print(f"Error updating transaction status: {e}")
                QMessageBox.warning(dialog, "خطأ", f"تعذر تحديث حالة التحويل: {str(e)}")
        
        save_button.clicked.connect(update_status_action)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        dialog.exec()

    def search_transaction(self):
        """Open transaction search dialog."""
        from ui.user_search import UserSearchDialog
        dialog = UserSearchDialog(token=self.token, parent=self, received=True)
        dialog.exec()
    def setup_inventory_tab(self):
        """Set up the inventory tab for tracking tax receivables and profits."""
        from dashboard.inventory import InventoryTab
        
        layout = QVBoxLayout()
        
        # Create the inventory tab widget with token
        print(f"\n=== Setting up Inventory Tab in Dashboard ===")
        print(f"Token available: {'Yes' if self.token else 'No'}")
        self.inventory_widget = InventoryTab(token=self.token, parent=self)
        layout.addWidget(self.inventory_widget)
        
        self.inventory_tab.setLayout(layout)

    def refresh_branches(self):
        """Refresh branch data and update relevant UI elements."""
        try:
            # Load updated branch data
            self.load_branches()
            self.load_branches_for_filter()
            
            # If admin transfer widget exists, refresh its branch data
            if hasattr(self, 'admin_transfer_widget'):
                self.admin_transfer_widget.load_branches()
                
        except Exception as e:
            print(f"Error refreshing branches: {str(e)}")
