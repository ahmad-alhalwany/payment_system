import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
    QDialog, QLineEdit, QFormLayout, QComboBox, QGroupBox, QGridLayout, 
    QStatusBar, QDateEdit, QDoubleSpinBox, QDialogButtonBox, QPushButton, QTextEdit
)
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal, QSize
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
import time
from datetime import datetime

class TableUpdateManager:
    """Manages efficient table updates to prevent UI freezing"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.batch_size = 50  # Number of rows to update at once
        self.update_delay = 10  # Milliseconds between batch updates
        
    def begin_update(self):
        """Prepare table for batch updates"""
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        
    def end_update(self):
        """Re-enable table updates and sorting"""
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        
    def update_table_data(self, data, column_mapping):
        """Update table data in batches to prevent UI freezing
        
        Args:
            data: List of dictionaries containing row data
            column_mapping: Dictionary mapping column indices to data keys
        """
        total_rows = len(data)
        self.table.setRowCount(total_rows)
        
        def update_batch(start_idx):
            end_idx = min(start_idx + self.batch_size, total_rows)
            
            for row in range(start_idx, end_idx):
                row_data = data[row]
                for col, key in column_mapping.items():
                    if isinstance(key, tuple):  # Custom formatting function
                        key, formatter = key
                        value = formatter(row_data.get(key, ""))
                    else:
                        value = str(row_data.get(key, ""))
                    
                    item = QTableWidgetItem(value)
                    
                    # Store original data for sorting
                    if key in ['amount', 'date']:
                        try:
                            if key == 'amount':
                                item.setData(Qt.ItemDataRole.UserRole, float(value.replace(',', '')))
                            elif key == 'date':
                                item.setData(Qt.ItemDataRole.UserRole, datetime.strptime(value, "%Y-%m-%d"))
                        except (ValueError, TypeError):
                            pass
                    
                    self.table.setItem(row, col, item)
            
            if end_idx < total_rows:
                QTimer.singleShot(self.update_delay, lambda: update_batch(end_idx))
            else:
                self.end_update()
        
        self.begin_update()
        update_batch(0)

class DataLoadThread(QThread):
    """Thread for loading dashboard data asynchronously"""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, api_url, token):
        super().__init__()
        self.api_url = api_url
        self.token = token
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل البيانات...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Load transactions
            response = requests.get(f"{self.api_url}/transactions/", headers=headers)
            if response.status_code == 200:
                transactions = response.json().get("transactions", [])
                self.data_loaded.emit({"transactions": transactions})
            else:
                self.error_occurred.emit(f"فشل تحميل البيانات: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"خطأ في تحميل البيانات: {str(e)}")

class ChartManager:
    """Manages efficient chart updates and statistics visualization"""
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self._data_cache = {}
        self._update_queue = []
        self._is_updating = False
        
    def queue_update(self, chart_type, data):
        """Queue a chart update to be processed efficiently"""
        # No-op: charts are disabled
        pass
    
    def _process_next_update(self):
        """Process the next chart update in the queue"""
        # No-op: charts are disabled
        pass
    
    def _update_transfers_chart(self, data):
        """Update transfers chart efficiently"""
        # No-op: charts are disabled
        pass
    
    def _update_amounts_chart(self, data):
        """Update amounts chart efficiently"""
        # No-op: charts are disabled
        pass

class BranchStatsLoader(QThread):
    """Asynchronous loader for branch statistics"""
    stats_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, api_url, token):
        super().__init__()
        self.api_url = api_url
        self.token = token
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل إحصائيات الفروع...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Load branch statistics
            response = requests.get(f"{self.api_url}/branches/stats/", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self.stats_loaded.emit(stats)
            else:
                self.error_occurred.emit(f"فشل تحميل إحصائيات الفروع: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"خطأ في تحميل إحصائيات الفروع: {str(e)}")

class DirectorDashboard(QMainWindow, BranchAllocationMixin, MenuAuthMixin, ReceiptPrinterMixin, ReportHandlerMixin, SettingsHandlerMixin, EmployeeManagementMixin, BranchManagementMixin):
    """Dashboard for the director role."""
    
    def __init__(self, token=None, full_name="مدير النظام"):
        super().__init__()
        BranchManagementMixin.__init__(self)
        self.token = token
        self.api_url = os.environ["API_URL"]
        self.current_page = 1
        self.total_pages = 1
        self.per_page = 7
        self.current_page_transactions = 1
        self.transactions_per_page = 15
        self.total_pages_transactions = 1
        self.api_client = APIClient(token)
        self.current_zoom = 100  # Track current zoom level
        self.full_name = full_name
        # --- Add missing QLabel attributes for stats ---
        from PyQt6.QtWidgets import QLabel
        self.employees_count = QLabel("0")
        self.transactions_count = QLabel("0")
        self.amount_total = QLabel("0")
        self.branches_count = QLabel("0")
        
        # Add timer for auto-refreshing transactions
        self.transaction_timer = QTimer(self)
        self.transaction_timer.timeout.connect(self.load_recent_transactions)
        self.transaction_timer.start(120000)  # 5000 ms = 5 seconds
        
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
        
        # Initialize chart manager
        self.chart_manager = ChartManager(self)
        
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
        """Set up the dashboard tab with a modern and minimalist design."""
        layout = QVBoxLayout()
        
        # Welcome Section with Time
        welcome_layout = QHBoxLayout()
        
        # Welcome message with current time
        welcome_group = ModernGroupBox("", "#ffffff")
        welcome_group.setStyleSheet("""
            ModernGroupBox {
                background-color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        welcome_layout_inner = QVBoxLayout()
        
        time_label = QLabel()
        time_label.setStyleSheet("color: #95a5a6; font-size: 14px;")
        
        # Update time every minute
        def update_time():
            current_time = datetime.now().strftime("%I:%M %p")
            current_date = datetime.now().strftime("%Y/%m/%d")
            time_label.setText(f"{current_time} - {current_date}")
            
        update_time()
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(update_time)
        self.time_timer.start(60000)  # Update every minute
        
        welcome_text = QLabel(f"مرحباً، {self.full_name}")
        welcome_text.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        
        welcome_layout_inner.addWidget(welcome_text)
        welcome_layout_inner.addWidget(time_label)
        welcome_group.setLayout(welcome_layout_inner)
        welcome_layout.addWidget(welcome_group, stretch=2)
        
        # Quick Actions (improved)
        actions_group = ModernGroupBox("", "#ffffff")
        actions_group.setStyleSheet("""
            ModernGroupBox {
                background-color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 10px;
            }
        """)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(30)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Helper to create a button with icon and label
        def create_action_button(icon_path, color, text, callback):
            from PyQt6.QtWidgets import QVBoxLayout, QLabel
            btn_layout = QVBoxLayout()
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn = ModernButton("", color=color)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(32, 32))
            btn.setFixedSize(56, 56)
            btn.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 28px;
                    background-color: {color};
                    color: white;
                    font-size: 18px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #222222;
                    color: #fff;
                }}
            """)
            btn.clicked.connect(callback)
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 13px; color: #2c3e50; margin-top: 6px;")
            btn_layout.addWidget(btn)
            btn_layout.addWidget(label)
            return btn_layout

        # Add Employee Button
        add_emp_layout = create_action_button(
            "assets/icons/add_user.png", "#27ae60", "إضافة موظف", self.add_employee
        )
        # New Transfer Button
        new_transfer_layout = create_action_button(
            "assets/icons/transfer.png", "#3498db", "تحويل جديد", self.new_transfer
        )
        # Reports Button
        reports_layout = create_action_button(
            "assets/icons/report.png", "#e74c3c", "التقارير", self.show_reports
        )

        actions_layout.addLayout(add_emp_layout)
        actions_layout.addLayout(new_transfer_layout)
        actions_layout.addLayout(reports_layout)
        actions_group.setLayout(actions_layout)
        welcome_layout.addWidget(actions_group, stretch=1)
        layout.addLayout(welcome_layout)
        
        # Main Content Area
        content_layout = QHBoxLayout()
        
        # Left Column - Statistics Cards
        left_column = QVBoxLayout()
        
        # Financial Status Card
        financial_card = ModernGroupBox("الحالة المالية", "#ffffff")
        financial_card.setStyleSheet("""
            ModernGroupBox {
                background-color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
            }
            QLabel {
                color: #2c3e50;
            }
        """)
        financial_layout = QVBoxLayout()
        
        # SYP Balance
        syp_layout = QHBoxLayout()
        syp_icon = QLabel("💵")
        syp_icon.setStyleSheet("font-size: 24px;")
        self.syp_balance = QLabel("0 ل.س")
        self.syp_balance.setStyleSheet("font-size: 18px; font-weight: bold; color: #27ae60;")
        syp_layout.addWidget(syp_icon)
        syp_layout.addWidget(self.syp_balance, alignment=Qt.AlignmentFlag.AlignRight)
        financial_layout.addLayout(syp_layout)
        
        # USD Balance
        usd_layout = QHBoxLayout()
        usd_icon = QLabel("💰")
        usd_icon.setStyleSheet("font-size: 24px;")
        self.usd_balance = QLabel("0 $")
        self.usd_balance.setStyleSheet("font-size: 18px; font-weight: bold; color: #2980b9;")
        usd_layout.addWidget(usd_icon)
        usd_layout.addWidget(self.usd_balance, alignment=Qt.AlignmentFlag.AlignRight)
        financial_layout.addLayout(usd_layout)
        
        financial_card.setLayout(financial_layout)
        left_column.addWidget(financial_card)
        
        # Branch Status Card
        branch_card = ModernGroupBox("حالة الفرع", "#ffffff")
        branch_card.setStyleSheet("""
            ModernGroupBox {
                background-color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        branch_layout = QVBoxLayout()
        
        # Active Employees
        emp_layout = QHBoxLayout()
        emp_icon = QLabel("👥")
        emp_icon.setStyleSheet("font-size: 24px;")
        self.active_employees = QLabel("0 موظف نشط")
        self.active_employees.setStyleSheet("font-size: 16px; color: #2c3e50;")
        emp_layout.addWidget(emp_icon)
        emp_layout.addWidget(self.active_employees, alignment=Qt.AlignmentFlag.AlignRight)
        branch_layout.addLayout(emp_layout)
        
        # Today's Transactions
        trans_layout = QHBoxLayout()
        trans_icon = QLabel("📊")
        trans_icon.setStyleSheet("font-size: 24px;")
        self.today_transactions = QLabel("0 تحويل اليوم")
        self.today_transactions.setStyleSheet("font-size: 16px; color: #2c3e50;")
        trans_layout.addWidget(trans_icon)
        trans_layout.addWidget(self.today_transactions, alignment=Qt.AlignmentFlag.AlignRight)
        branch_layout.addLayout(trans_layout)
        
        branch_card.setLayout(branch_layout)
        left_column.addWidget(branch_card)
        
        content_layout.addLayout(left_column)
        
        # Right Column - Recent Activity
        activity_card = ModernGroupBox("النشاط الحديث", "#ffffff")
        activity_card.setStyleSheet("""
            ModernGroupBox {
                background-color: #ffffff;
                border: none;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        activity_layout = QVBoxLayout()
        
        self.activity_list = QTableWidget()
        self.activity_list.setColumnCount(4)
        self.activity_list.setHorizontalHeaderLabels(["الوقت", "النوع", "التفاصيل", "الحالة"])
        self.activity_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_list.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #7f8c8d;
                border: none;
                padding: 5px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #ecf0f1;
            }
        """)
        self.activity_list.setShowGrid(False)
        self.activity_list.verticalHeader().setVisible(False)
        
        activity_layout.addWidget(self.activity_list)
        activity_card.setLayout(activity_layout)
        content_layout.addWidget(activity_card, stretch=2)
        
        layout.addLayout(content_layout)
        
        # Set up refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        self.dashboard_tab.setLayout(layout)
        self.refresh_dashboard()
        
    def refresh_dashboard(self):
        """Refresh all dashboard data."""
        try:
            # Update financial status
            self.load_financial_status()
            
            # Update branch status
            self.load_branch_status()
            
            # Update recent activity
            self.load_recent_activity()
            
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            
    def load_financial_status(self):
        """Load and display financial status."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            # For director, get total financial stats across all branches
            response = requests.get(f"{self.api_url}/financial/total/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update SYP balance
                syp_balance = data.get("total_balance_syp", 0)
                self.syp_balance.setText(f"{syp_balance:,.0f} ل.س")
                
                # Update USD balance
                usd_balance = data.get("total_balance_usd", 0)
                self.usd_balance.setText(f"{usd_balance:,.2f} $")
                
        except Exception as e:
            print(f"Error loading financial status: {e}")
            self.syp_balance.setText("غير متوفر")
            self.usd_balance.setText("غير متوفر")
            
    def load_branch_status(self):
        """Load and display overall system status."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Get total active employees across all branches
            emp_response = requests.get(
                f"{self.api_url}/users/stats/",
                headers=headers
            )
            if emp_response.status_code == 200:
                emp_data = emp_response.json()
                active_count = emp_data.get("active", 0)
                self.active_employees.setText(f"{active_count} موظف نشط")
            
            # Get today's total transactions
            today = datetime.now().strftime("%Y-%m-%d")
            trans_response = requests.get(
                f"{self.api_url}/transactions/stats/?date={today}",
                headers=headers
            )
            if trans_response.status_code == 200:
                trans_data = trans_response.json()
                trans_count = trans_data.get("total", 0)
                self.today_transactions.setText(f"{trans_count} تحويل اليوم")
                
        except Exception as e:
            print(f"Error loading branch status: {e}")
            self.active_employees.setText("غير متوفر")
            self.today_transactions.setText("غير متوفر")
            
    def load_recent_activity(self):
        """Load and display recent system-wide activity."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/activity/",  # System-wide activity endpoint
                headers=headers
            )
            
            if response.status_code == 200:
                activities = response.json().get("activities", [])
                self.activity_list.setRowCount(len(activities))
                
                for i, activity in enumerate(activities):
                    # Time
                    time_item = QTableWidgetItem(activity.get("time"))
                    time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.activity_list.setItem(i, 0, time_item)
                    
                    # Type
                    type_item = QTableWidgetItem(activity.get("type"))
                    type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.activity_list.setItem(i, 1, type_item)
                    
                    # Details
                    details_item = QTableWidgetItem(activity.get("details"))
                    self.activity_list.setItem(i, 2, details_item)
                    
                    # Status
                    status = activity.get("status", "")
                    status_item = QTableWidgetItem(get_status_arabic(status))
                    status_item.setBackground(get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.activity_list.setItem(i, 3, status_item)
                    
        except Exception as e:
            print(f"Error loading recent activity: {e}")
            # Clear the table in case of error
            self.activity_list.setRowCount(0)

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
            "الفرع المرسل", "اتجاه الصادر",
            "الفرع المستلم", "اتجاه الوارد", "اسم الموظف"
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
        """Load recent transactions with optimized table updates"""
        try:
            self.statusBar().showMessage("جاري تحميل التحويلات...")
            
            # Initialize table update manager if not exists
            if not hasattr(self, 'table_manager'):
                self.table_manager = TableUpdateManager(self.recent_transactions_table)
            
            # Create and start data loading thread
            self.load_thread = DataLoadThread(self.api_url, self.token)
            self.load_thread.data_loaded.connect(self.update_transactions_table)
            self.load_thread.error_occurred.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
            self.load_thread.progress_updated.connect(lambda msg: self.statusBar().showMessage(msg))
            self.load_thread.start()
            
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحميل البيانات: {str(e)}", 5000)

    def update_transactions_table(self, data):
        """Update transactions table with the loaded data"""
        try:
            transactions = data.get("transactions", [])
            
            # Client-side pagination
            start_index = (self.current_page - 1) * self.per_page
            end_index = start_index + self.per_page
            page_transactions = transactions[start_index:end_index]
            
            # Define column mapping
            column_mapping = {
                0: ("type", lambda x: self.create_transaction_type_item(x).text()),
                1: "id",
                2: "sender",
                3: "receiver",
                4: ("amount", lambda x: f"{float(x):,.2f}" if x else "0.00"),
                5: "date",
                6: ("status", lambda x: self._get_status_arabic(x)),
                7: "sending_branch_name",
                8: ("outgoing_direction", lambda x: "↑" if x.get("branch_id") else ""),
                9: "destination_branch_name",
                10: ("incoming_direction", lambda x: "↓" if x.get("destination_branch_id") else ""),
                11: "employee_name"
            }
            
            # Update table using the manager
            self.table_manager.update_table_data(page_transactions, column_mapping)
            
            # Update pagination info
            self.total_pages = (len(transactions) + self.per_page - 1) // self.per_page
            self.update_pagination_controls()
            
            self.statusBar().showMessage("تم تحميل التحويلات بنجاح", 3000)
            
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحديث الجدول: {str(e)}", 5000)

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

    def load_branch_stats(self):
        """Load branch statistics with optimized chart updates"""
        try:
            # Create and start stats loader thread
            self.stats_loader = BranchStatsLoader(self.api_url, self.token)
            self.stats_loader.stats_loaded.connect(self.update_branch_stats)
            self.stats_loader.error_occurred.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
            self.stats_loader.progress_updated.connect(lambda msg: self.statusBar().showMessage(msg))
            self.stats_loader.start()
            
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحميل إحصائيات الفروع: {str(e)}", 5000)

    def update_branch_stats(self, stats):
        """Update branch statistics displays efficiently"""
        try:
            # Update basic statistics
            self.branches_count.setText(str(stats.get("total_branches", 0)))
            self.employees_count.setText(str(stats.get("total_employees", 0)))
            self.transactions_count.setText(str(stats.get("total_transactions", 0)))
            self.amount_total.setText(f"{stats.get('total_amount', 0):,.2f}")
            
            # Queue chart updates
            branch_transfers = stats.get("transfers_by_branch", [])
            self.chart_manager.queue_update("transfers", branch_transfers)
            
            branch_amounts = stats.get("amounts_by_branch", [])
            self.chart_manager.queue_update("amounts", branch_amounts)
            
            self.statusBar().showMessage("تم تحديث إحصائيات الفروع بنجاح", 3000)
            
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحديث إحصائيات الفروع: {str(e)}", 5000)

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

    def show_search_dialog(self):
        """Show search dialog for transactions."""
        search_dialog = UserSearchDialog(self.token, self)
        search_dialog.exec()

    def show_filter_dialog(self):
        """Show filter dialog for transactions."""
        filter_dialog = QDialog(self)
        filter_dialog.setWindowTitle("تصفية متقدمة")
        filter_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Date range filter
        date_group = ModernGroupBox("نطاق التاريخ", "#3498db")
        date_layout = QHBoxLayout()
        
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(QLabel("من:"))
        date_layout.addWidget(self.start_date_filter)
        
        self.end_date_filter = QDateEdit()
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDate(QDate.currentDate())
        date_layout.addWidget(QLabel("إلى:"))
        date_layout.addWidget(self.end_date_filter)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # Amount range filter
        amount_group = ModernGroupBox("نطاق المبلغ", "#2ecc71")
        amount_layout = QHBoxLayout()
        
        self.min_amount_filter = QDoubleSpinBox()
        self.min_amount_filter.setRange(0, 1000000)
        self.min_amount_filter.setPrefix("$ ")
        amount_layout.addWidget(QLabel("من:"))
        amount_layout.addWidget(self.min_amount_filter)
        
        self.max_amount_filter = QDoubleSpinBox()
        self.max_amount_filter.setRange(0, 1000000)
        self.max_amount_filter.setPrefix("$ ")
        amount_layout.addWidget(QLabel("إلى:"))
        amount_layout.addWidget(self.max_amount_filter)
        
        amount_group.setLayout(amount_layout)
        layout.addWidget(amount_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(lambda: self.apply_filters(filter_dialog))
        button_box.rejected.connect(filter_dialog.reject)
        layout.addWidget(button_box)
        
        filter_dialog.setLayout(layout)
        filter_dialog.exec()

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

    def new_transfer(self):
        """Switch to admin transfer tab for a new transfer."""
        self.tabs.setCurrentIndex(4)  # Switch to admin transfer tab

    def add_employee(self):
        """Open dialog to add a new employee."""
        from ui.user_management_improved import AddEmployeeDialog
        dialog = AddEmployeeDialog(
            is_admin=True,  # Director has admin privileges
            token=self.token,
            current_user_id=None  # Director can add employees to any branch
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_dashboard()

    def show_reports(self):
        """Switch to reports tab."""
        self.tabs.setCurrentIndex(5)  # Switch to reports tab

    def create_transaction_type_item(self, transaction):
        """Return a colored QTableWidgetItem for the transaction type."""
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtGui import QColor
        ttype = transaction.get("type", "")
        if ttype == "incoming" or (transaction.get("destination_branch_id") and not transaction.get("branch_id")):
            item = QTableWidgetItem("وارد")
            item.setForeground(QColor(39, 174, 96))  # أخضر
        elif ttype == "outgoing" or (transaction.get("branch_id") and not transaction.get("destination_branch_id")):
            item = QTableWidgetItem("صادر")
            item.setForeground(QColor(52, 152, 219))  # أزرق
        elif transaction.get("branch_id") and transaction.get("destination_branch_id"):
            item = QTableWidgetItem("داخلي")
            item.setForeground(QColor(243, 156, 18))  # برتقالي
        else:
            item = QTableWidgetItem("غير معروف")
            item.setForeground(QColor(127, 140, 141))  # رمادي
        return item
