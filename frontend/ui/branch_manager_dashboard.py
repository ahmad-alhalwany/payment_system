import requests
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QComboBox,
    QGridLayout, QPushButton, QHBoxLayout, QDateEdit, 
    QCalendarWidget, QDialogButtonBox, QDoubleSpinBox, QTextEdit, QScrollArea
)
from ui.change_password import ChangePasswordDialog
from datetime import datetime, timedelta
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal
import os
from ui.money_transfer_improved import MoneyTransferApp
from ui.user_search import UserSearchDialog
from ui.user_management_improved import AddEmployeeDialog, EditEmployeeDialog
from ui.custom_widgets import ModernGroupBox, ModernButton
from utils.helpers import get_status_arabic, get_status_color
from ui.menu_auth import MenuAuthMixin
from branch_dashboard.employees_tab import EmployeesTabMixin
from branch_dashboard.reports_tab import ReportsTabMixin
from branch_dashboard.profits_tab import ProfitsTabMixin
import time

class WorkerThread(QThread):
    finished = pyqtSignal(object)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
    def run(self):
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.result = e
        self.finished.emit(self.result)

class InitialDataWorker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
    def run(self):
        result = {'success': True, 'error': None}
        try:
            self.dashboard.load_branch_info()
            self.dashboard.update_financial_status()
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        self.finished.emit(result)

class BranchManagerDashboard(QMainWindow, MenuAuthMixin, EmployeesTabMixin, ReportsTabMixin, ProfitsTabMixin):
    """Branch Manager Dashboard for the Internal Payment System."""
    
    def __init__(self, branch_id, token=None, user_id=None, username=None, full_name=None):
        super().__init__()
        self.branch_id = branch_id
        self.token = token
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.api_url = os.environ["API_URL"]
        self.branch_id_to_name = {}
        self.current_page = 1
        self.total_pages = 1
        self.per_page = 8
        self.report_per_page = 14
        self.report_current_page = 1
        self.report_total_pages = 1
        self.current_zoom = 100
        
        # Loading state tracking
        self._is_initializing = True
        self._loading_priority = {
            'essential': False,  # Branch info and financial status
            'secondary': False,  # Employee stats and branches
            'tertiary': False   # Reports and detailed data
        }
        
        # Cache tracking variables with timestamps
        self._last_financial_update = 0
        self._last_employee_stats = 0
        self._last_branches_update = 0
        self._last_profits_update = 0
        self._last_transactions_update = 0
        
        # Cache storage
        self._branches_cache = None
        self._financial_cache = None
        self._employee_stats_cache = None
        self._profits_cache = None
        self._transactions_cache = None
        
        # Cache duration in seconds
        self.FINANCIAL_CACHE_DURATION = 30  # 30 seconds for financial data
        self.EMPLOYEE_CACHE_DURATION = 300  # 5 minutes for employee stats
        self.BRANCHES_CACHE_DURATION = 300  # 5 minutes for branches data
        self.PROFITS_CACHE_DURATION = 300   # 5 minutes for profits data
        self.TRANSACTIONS_CACHE_DURATION = 60  # 1 minute for transactions
        
        # Request tracking
        self._pending_requests = set()
        self._request_timeouts = {}
        
        # Initialize UI first
        self.setup_initial_ui()
        
        # Initialize update timers
        self.financial_update_timer = QTimer()
        self.financial_update_timer.timeout.connect(self.update_financial_status)
        self.financial_update_timer.start(self.FINANCIAL_CACHE_DURATION * 1000)
        
        # Start progressive loading
        self.initialize_data()
    
    def initialize_data(self):
        """Initialize data progressively with loading indicators in a separate thread"""
        self.statusBar().showMessage("جاري تحميل البيانات الأساسية...")
        self.loading_label = QLabel("جاري تحميل البيانات ... الرجاء الانتظار")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.centralWidget().layout().insertWidget(0, self.loading_label)
        self.setEnabled(False)
        self.initial_worker = InitialDataWorker(self)
        self.initial_worker.finished.connect(self.on_initial_data_loaded)
        self.initial_worker.start()

    def on_initial_data_loaded(self, result):
        self.setEnabled(True)
        if hasattr(self, 'loading_label'):
            self.loading_label.deleteLater()
        if result['success']:
            self.statusBar().showMessage("تم تحميل البيانات الأساسية بنجاح", 3000)
            QTimer.singleShot(500, self.load_secondary_data)
        else:
            self.statusBar().showMessage(f"فشل تحميل البيانات: {result['error']}", 5000)

    def load_secondary_data(self):
        """Load secondary data after essential data is loaded"""
        try:
            if not self._loading_priority['essential']:
                return
                
            self.statusBar().showMessage("جاري تحميل البيانات الإضافية...")
            self._loading_priority['secondary'] = True
            
            # Load branches data
            self.load_branches()
            
            # Load employee statistics
            self.load_employee_stats()
            
            # Step 3: Load tertiary data after another delay
            QTimer.singleShot(500, self.load_tertiary_data)
            
        except Exception as e:
            print(f"Error loading secondary data: {e}")
            self.statusBar().showMessage("حدث خطأ أثناء تحميل البيانات الإضافية", 5000)

    def load_tertiary_data(self):
        """Load tertiary data after secondary data is loaded"""
        try:
            if not self._loading_priority['secondary']:
                return
                
            self.statusBar().showMessage("جاري تحميل البيانات التفصيلية...")
            self._loading_priority['tertiary'] = True
            
            # Load initial profits data
            self.load_profits_data()
            
            # Load initial transactions
            self.load_transactions(branch_id=self.branch_id)
            self.load_transactions(destination_branch_id=self.branch_id)
            
            # Mark initialization as complete
            self._is_initializing = False
            self.statusBar().showMessage("تم تحميل البيانات بنجاح", 3000)
            
        except Exception as e:
            print(f"Error loading tertiary data: {e}")
            self.statusBar().showMessage("حدث خطأ أثناء تحميل البيانات التفصيلية", 5000)

    def setup_tab(self, tab_index):
        """Lazy load tab content when selected"""
        if tab_index == 0:  # Dashboard tab
            if not self._loading_priority['essential']:
                self.initialize_data()
        elif tab_index == 1:  # Employees tab
            if not self._loading_priority['secondary']:
                self.load_secondary_data()
        elif tab_index == 2:  # Transfers tab
            if not self._loading_priority['tertiary']:
                self.load_tertiary_data()
        elif tab_index == 3:  # Reports tab
            if not self._loading_priority['tertiary']:
                self.load_tertiary_data()
        elif tab_index == 4:  # Profits tab
            if not self._loading_priority['tertiary']:
                self.load_tertiary_data()

    def tab_widget_changed(self, index):
        """Handle tab changes with lazy loading"""
        self.setup_tab(index)

    def setup_initial_ui(self):
        """Set up the initial UI without loading data"""
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
        self.profits_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Set up tabs
        self.setup_dashboard_tab()
        self.setup_employees_tab()
        self.setup_transfers_tab()
        self.setup_reports_tab()
        self.setup_profits_tab()
        self.setup_settings_tab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.dashboard_tab, "الرئيسية")
        self.tab_widget.addTab(self.employees_tab, "إدارة الموظفين")
        self.tab_widget.addTab(self.transfers_tab, "التحويلات")
        self.tab_widget.addTab(self.reports_tab, "التقارير")
        self.tab_widget.addTab(self.profits_tab, "الأرباح")
        self.tab_widget.addTab(self.settings_tab, "الإعدادات")
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.tab_widget_changed)
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar().showMessage("جاري التحميل...")
    
    def load_branch_info(self):
        """Load branch information with loading indicator"""
        try:
            self.branch_name_label.setText("جاري التحميل...")
            
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}", 
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                branch = response.json()
                self.branch_name_label.setText(f"الفرع: {branch.get('name', '')}")
                self.branch_id_label.setText(branch.get('branch_id', ''))
                self.branch_name_field.setText(branch.get('name', ''))
                self.branch_location_label.setText(branch.get('location', ''))
                self.branch_governorate_label.setText(branch.get('governorate', ''))
                self.branch_governorate = branch.get('governorate', '')
            else:
                self.show_branch_info_error()
        except Exception as e:
            print(f"Error loading branch info: {e}")
            self.show_branch_info_error()

    def show_branch_info_error(self):
        """Show error state for branch information"""
        self.branch_name_label.setText("الفرع: ")
        self.branch_id_label.setText("")
        self.branch_name_field.setText("")
        self.branch_location_label.setText("")
        self.branch_governorate_label.setText("")
    
    def setup_dashboard_tab(self):
        """Set up the main dashboard tab with a modern and efficient design."""
        layout = QVBoxLayout()
        layout.setSpacing(20)  # Increased spacing between groups
        
        # Create a scroll area to handle overflow
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create a container widget for the scroll area
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)
        
        # Welcome Section with improved styling
        welcome_group = ModernGroupBox("لوحة المعلومات", "#e74c3c")
        welcome_layout = QVBoxLayout()
        welcome_layout.setSpacing(15)
        
        # Welcome message with gradient background
        welcome_label = QLabel("مرحباً بك في لوحة تحكم مدير الفرع")
        welcome_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setWordWrap(True)  # Enable word wrapping
        welcome_label.setStyleSheet("""
            color: #2c3e50;
            margin: 15px 0;
            padding: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                      stop:0 #e74c3c, stop:1 #c0392b);
            color: white;
            border-radius: 10px;
        """)
        welcome_layout.addWidget(welcome_label)
        
        # Branch info with improved styling
        self.branch_name_label = QLabel("الفرع: جاري التحميل...")
        self.branch_name_label.setFont(QFont("Arial", 16))
        self.branch_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branch_name_label.setWordWrap(True)  # Enable word wrapping
        self.branch_name_label.setStyleSheet("""
            color: #34495e;
            margin: 10px 0;
            padding: 10px;
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
        """)
        welcome_layout.addWidget(self.branch_name_label)
        
        # Current date with improved styling
        from datetime import datetime
        date_label = QLabel(f"تاريخ اليوم: {datetime.now().strftime('%Y-%m-%d')}")
        date_label.setFont(QFont("Arial", 16))
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_label.setWordWrap(True)  # Enable word wrapping
        date_label.setStyleSheet("""
            color: #34495e;
            margin: 10px 0;
            padding: 10px;
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
        """)
        welcome_layout.addWidget(date_label)
        self.date_label = date_label
        
        welcome_group.setLayout(welcome_layout)
        container_layout.addWidget(welcome_group)
        
        # Financial Status Section with improved styling
        financial_group = ModernGroupBox("الحالة المالية", "#27ae60")
        financial_layout = QGridLayout()
        financial_layout.setVerticalSpacing(20)
        financial_layout.setContentsMargins(20, 20, 20, 20)

        # Syrian Pounds Balance with improved styling
        syp_label = QLabel("الرصيد المتاح (ل.س)")
        syp_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        syp_label.setStyleSheet("color: #2c3e50;")
        syp_label.setWordWrap(True)  # Enable word wrapping
        financial_layout.addWidget(syp_label, 0, 0)
        
        self.syp_balance_label = QLabel("جاري التحميل...")
        self.syp_balance_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.syp_balance_label.setWordWrap(True)  # Enable word wrapping
        self.syp_balance_label.setStyleSheet("""
            color: #2ecc71;
            padding: 15px;
            background-color: rgba(46, 204, 113, 0.1);
            border-radius: 10px;
            border: 2px solid #2ecc71;
        """)
        financial_layout.addWidget(self.syp_balance_label, 0, 1)

        # US Dollars Balance with improved styling
        usd_label = QLabel("الرصيد المتاح ($)")
        usd_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        usd_label.setStyleSheet("color: #2c3e50;")
        usd_label.setWordWrap(True)  # Enable word wrapping
        financial_layout.addWidget(usd_label, 1, 0)
        
        self.usd_balance_label = QLabel("جاري التحميل...")
        self.usd_balance_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.usd_balance_label.setWordWrap(True)  # Enable word wrapping
        self.usd_balance_label.setStyleSheet("""
            color: #3498db;
            padding: 15px;
            background-color: rgba(52, 152, 219, 0.1);
            border-radius: 10px;
            border: 2px solid #3498db;
        """)
        financial_layout.addWidget(self.usd_balance_label, 1, 1)

        # Refresh Button with improved styling
        refresh_finance_btn = ModernButton("تحديث الرصيد", color="#3498db")
        refresh_finance_btn.setFont(QFont("Arial", 14))
        refresh_finance_btn.setMinimumHeight(50)
        refresh_finance_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_finance_btn.clicked.connect(self.load_financial_status)
        financial_layout.addWidget(refresh_finance_btn, 0, 2, 2, 1)

        financial_group.setLayout(financial_layout)
        container_layout.addWidget(financial_group)
        
        # Employee Statistics Section with improved styling
        employees_group = ModernGroupBox("إحصائيات الموظفين", "#2ecc71")
        employees_layout = QVBoxLayout()
        employees_layout.setSpacing(15)
        
        # Total Employees with improved styling
        self.employees_count = QLabel("عدد الموظفين: جاري التحميل...")
        self.employees_count.setFont(QFont("Arial", 16))
        self.employees_count.setWordWrap(True)  # Enable word wrapping
        self.employees_count.setStyleSheet("""
            color: #2c3e50;
            padding: 15px;
            background-color: rgba(46, 204, 113, 0.1);
            border-radius: 10px;
            border: 2px solid #2ecc71;
        """)
        employees_layout.addWidget(self.employees_count)
        
        # Active Employees with improved styling
        self.active_employees = QLabel("الموظفين النشطين: جاري التحميل...")
        self.active_employees.setFont(QFont("Arial", 16))
        self.active_employees.setWordWrap(True)  # Enable word wrapping
        self.active_employees.setStyleSheet("""
            color: #2c3e50;
            padding: 15px;
            background-color: rgba(46, 204, 113, 0.1);
            border-radius: 10px;
            border: 2px solid #2ecc71;
        """)
        employees_layout.addWidget(self.active_employees)
        
        employees_group.setLayout(employees_layout)
        container_layout.addWidget(employees_group)
        
        # Quick Actions Section with improved styling
        actions_group = ModernGroupBox("إجراءات سريعة", "#9b59b6")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)
        
        # Add employee button with improved styling
        add_employee_button = ModernButton("إضافة موظف جديد", color="#2ecc71")
        add_employee_button.setFont(QFont("Arial", 14))
        add_employee_button.setMinimumHeight(60)
        add_employee_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        add_employee_button.clicked.connect(self.add_employee)
        actions_layout.addWidget(add_employee_button)
        
        # Search user button with improved styling
        search_user_button = ModernButton("بحث عن مستخدم", color="#e67e22")
        search_user_button.setFont(QFont("Arial", 14))
        search_user_button.setMinimumHeight(60)
        search_user_button.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        search_user_button.clicked.connect(self.search_user)
        actions_layout.addWidget(search_user_button)
        
        # New transfer button with improved styling
        new_transfer_button = ModernButton("تحويل جديد", color="#3498db")
        new_transfer_button.setFont(QFont("Arial", 14))
        new_transfer_button.setMinimumHeight(60)
        new_transfer_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        new_transfer_button.clicked.connect(self.new_transfer)
        actions_layout.addWidget(new_transfer_button)
        
        actions_group.setLayout(actions_layout)
        container_layout.addWidget(actions_group)
        
        # Set the container as the scroll area's widget
        scroll_area.setWidget(container)
        
        # Add the scroll area to the main layout
        layout.addWidget(scroll_area)
        
        self.dashboard_tab.setLayout(layout)
        
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
                financial = branch_data.get("financial_stats", {})
                
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

    def is_date_in_range(self, date_str, start_date, end_date):
        """Helper function to validate date range"""
        try:
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
            return start_date <= transaction_date <= end_date
        except ValueError:
            return False
            
    def generate_employee_report(self):
        """Generate employee report based on filters using a background thread."""
        def fetch_employees():
            headers = {"Authorization": f"Bearer {self.token}"}
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
            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = requests.get(
                    f"{self.api_url}/reports/employees/", 
                    params=params, 
                    headers=headers,
                    timeout=10
                )
                return response
            except Exception as e:
                return e

        def handle_result(response):
            if isinstance(response, Exception):
                QMessageBox.critical(self, "خطأ", f"حدث خطأ غير متوقع:\n{str(response)}")
                self.employee_report_table.setRowCount(0)
                return
            if response.status_code == 200:
                response_data = response.json()
                employees = response_data.get("employees", 
                    response_data.get("items", 
                    response_data.get("results", [])))
                if not isinstance(employees, list):
                    QMessageBox.warning(self, "خطأ", "تنسيق البيانات غير صحيح")
                    self.employee_report_table.setRowCount(0)
                    return
                self.employee_report_table.setRowCount(len(employees))
                for row, employee in enumerate(employees):
                    username_item = QTableWidgetItem(employee.get("username", "غير معروف"))
                    self.employee_report_table.setItem(row, 0, username_item)
                    role = employee.get("role", "employee")
                    role_text = "مدير فرع" if role == "branch_manager" else "موظف"
                    role_item = QTableWidgetItem(role_text)
                    self.employee_report_table.setItem(row, 1, role_item)
                    is_active = employee.get("is_active", employee.get("active", False))
                    status_text = "نشط" if is_active else "غير نشط"
                    status_item = QTableWidgetItem(status_text)
                    color = QColor("#27ae60") if is_active else QColor("#e74c3c")
                    status_item.setForeground(color)
                    self.employee_report_table.setItem(row, 2, status_item)
                    created_at = employee.get("created_at", "غير معروف")
                    created_item = QTableWidgetItem(created_at)
                    self.employee_report_table.setItem(row, 3, created_item)
                    last_active = employee.get("last_login", employee.get("last_activity", "غير معروف"))
                    last_active_item = QTableWidgetItem(last_active)
                    self.employee_report_table.setItem(row, 4, last_active_item)
                self.statusBar().showMessage("تم تحميل التقرير بنجاح", 3000)
            else:
                try:
                    error_detail = response.json().get("detail", "فشل في تحميل البيانات")
                except Exception:
                    error_detail = "فشل في تحميل البيانات"
                QMessageBox.warning(self, "خطأ", error_detail)

        self.statusBar().showMessage("جاري تحميل تقرير الموظفين ...")
        self.employee_report_table.setRowCount(0)
        self._employee_report_thread = WorkerThread(fetch_employees)
        self._employee_report_thread.finished.connect(handle_result)
        self._employee_report_thread.start()
    
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
        """Refresh dashboard data with improved caching"""
        try:
            current_time = time.time()
            
            # Update current date
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            self.date_label.setText(f"تاريخ اليوم: {current_date}")
            
            # Load branches if cache is expired
            if not self._branches_cache or current_time - self._last_branches_update > self.BRANCHES_CACHE_DURATION:
                self.load_branches()
            
            # Load employee statistics if cache is expired
            if not self._employee_stats_cache or current_time - self._last_employee_stats > self.EMPLOYEE_CACHE_DURATION:
                self.load_employee_stats()
            
            # Update status bar
            self.statusBar().showMessage("تم تحديث البيانات بنجاح", 3000)
            
        except Exception as e:
            print(f"Error refreshing dashboard: {str(e)}")
            self.statusBar().showMessage("حدث خطأ أثناء تحديث البيانات", 5000)

    def load_employee_stats(self):
        """Load employee statistics with caching"""
        try:
            current_time = time.time()
            
            # Check cache first
            if self._employee_stats_cache and current_time - self._last_employee_stats < self.EMPLOYEE_CACHE_DURATION:
                stats = self._employee_stats_cache
                self.employees_count.setText(f"عدد الموظفين: {stats.get('total', 0)}")
                self.active_employees.setText(f"الموظفين النشطين: {stats.get('active', 0)}")
                return
                
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}/employees/stats/", 
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                stats = response.json()
                self.employees_count.setText(f"عدد الموظفين: {stats.get('total', 0)}")
                self.active_employees.setText(f"الموظفين النشطين: {stats.get('active', 0)}")
                
                # Update cache
                self._employee_stats_cache = stats
                self._last_employee_stats = current_time
            else:
                self.employees_count.setText("عدد الموظفين: 0")
                self.active_employees.setText("الموظفين النشطين: 0")
        except Exception as e:
            print(f"Error loading employee stats: {e}")
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
      
            
    def load_branches(self):
        """Load branches with improved caching"""
        try:
            current_time = time.time()
            
            # Check cache first
            if self._branches_cache and current_time - self._last_branches_update < self.BRANCHES_CACHE_DURATION:
                return self._branches_cache
                
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{self.api_url}/branches/", 
                headers=headers,
                timeout=5
            )
            
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
                            self.branch_id_to_name[branch_id] = branch_name
                            
                    except Exception as branch_error:
                        print(f"Error processing branch: {branch_error}")
                        continue
                
                # Update cache
                self._branches_cache = self.branch_id_to_name
                self._last_branches_update = current_time
                
            else:
                print(f"Failed to load branches. Status: {response.status_code}")
                self.branch_id_to_name = {}
                
        except Exception as e:
            print(f"Error loading branches: {str(e)}")
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
            
    
    def load_placeholder_transactions(self):
        """Load placeholder transaction data for testing/demo."""
        pass  # This function is no longer needed
    
    def add_employee(self):
        dialog = AddEmployeeDialog(
            is_admin=False,  # Force non-admin mode
            branch_id=self.branch_id,
            token=self.token,
            current_user_id=self.user_id  # Pass current user ID
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_employees()
    
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
            
    def change_password(self):
        """Open the change password dialog for the branch manager."""
        dialog = ChangePasswordDialog(self.token)
        dialog.exec()        
            
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
        
        info_layout.addRow("اسم المستخدم:", QLabel(self.username))
        info_layout.addRow("الاسم الكامل:", QLabel(self.full_name))
        info_layout.addRow("الدور:", QLabel("مدير فرع"))
        info_layout.addRow("رقم الفرع:", QLabel(str(self.branch_id)))
        
        # Get branch name
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/branches/{self.branch_id}", headers=headers)
            if response.status_code == 200:
                branch_data = response.json()
                branch_name = branch_data.get('name', 'غير معروف')
                branch_governorate = branch_data.get('governorate', 'غير معروف')
                info_layout.addRow("اسم الفرع:", QLabel(f"{branch_name} - {branch_governorate}"))
        except:
            info_layout.addRow("اسم الفرع:", QLabel("غير متصل"))
        
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
            <h2>دليل استخدام لوحة تحكم مدير الفرع</h2>
            
            <h3>إدارة الموظفين</h3>
            <ul>
                <li>إضافة موظفين جدد للفرع</li>
                <li>تعديل بيانات الموظفين</li>
                <li>تعطيل/تفعيل حسابات الموظفين</li>
                <li>مراقبة أداء الموظفين</li>
            </ul>
            
            <h3>إدارة التحويلات</h3>
            <ul>
                <li>مراقبة التحويلات الصادرة والواردة</li>
                <li>تصفية وبحث في التحويلات</li>
                <li>تغيير حالة التحويلات</li>
                <li>طباعة الإيصالات والتقارير</li>
            </ul>
            
            <h3>التقارير</h3>
            <ul>
                <li>تقارير أداء الفرع</li>
                <li>تقارير الموظفين</li>
                <li>تقارير التحويلات</li>
                <li>تصدير التقارير</li>
            </ul>
            
            <h3>الإعدادات</h3>
            <ul>
                <li>تغيير كلمة المرور</li>
                <li>تحديث معلومات الفرع</li>
                <li>إدارة إعدادات النظام</li>
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

    def update_financial_status(self):
        """Update financial status with loading indicator"""
        try:
            # Show loading state
            self.syp_balance_label.setText("جاري التحديث...")
            self.usd_balance_label.setText("جاري التحديث...")
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}",
                headers=headers,
                timeout=5  # Add timeout
            )
            
            if response.status_code == 200:
                branch_data = response.json()
                financial = branch_data.get("financial_stats", {})
                
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
                
                # Update cache
                self._financial_cache = {
                    'syp_balance': syp_balance,
                    'usd_balance': usd_balance,
                    'timestamp': time.time()
                }
                
            else:
                self.show_financial_error()

        except Exception as e:
            print(f"Error updating financial status: {e}")
            self.show_financial_error()

    def make_request(self, url, method="GET", params=None, data=None, cache_duration=None, cache_key=None):
        """Make an API request with caching and request tracking"""
        try:
            # Check cache first if cache is enabled
            if cache_duration and cache_key and hasattr(self, cache_key):
                cache_data = getattr(self, cache_key)
                cache_timestamp = getattr(self, f"_last_{cache_key.replace('_cache', '')}_update", 0)
                
                if cache_data and time.time() - cache_timestamp < cache_duration:
                    return cache_data
            
            # Check if there's already a pending request for this URL
            if url in self._pending_requests:
                return None
                
            # Add to pending requests
            self._pending_requests.add(url)
            
            # Make the request
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.request(
                method,
                url,
                params=params,
                json=data,
                headers=headers,
                timeout=5
            )
            
            # Remove from pending requests
            self._pending_requests.remove(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update cache if caching is enabled
                if cache_duration and cache_key:
                    setattr(self, cache_key, data)
                    setattr(self, f"_last_{cache_key.replace('_cache', '')}_update", time.time())
                
                return data
            else:
                print(f"Request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {str(e)}")
            if url in self._pending_requests:
                self._pending_requests.remove(url)
            return None

    def load_profits_data(self):
        """Load profits data with caching"""
        try:
            current_time = time.time()
            
            # Check cache first
            if (self._profits_cache and 
                current_time - self._last_profits_update < self.PROFITS_CACHE_DURATION):
                return self._profits_cache
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Make request with caching
            data = self.make_request(
                f"{self.api_url}/api/branches/{self.branch_id}/profits/",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                },
                cache_duration=self.PROFITS_CACHE_DURATION,
                cache_key="_profits_cache"
            )
            
            if data:
                self._profits_cache = data
                self._last_profits_update = current_time
                return data
                
        except Exception as e:
            print(f"Error loading profits data: {e}")
            return None

    def load_transactions(self, branch_id=None, destination_branch_id=None):
        """Load transactions with caching"""
        try:
            current_time = time.time()
            cache_key = f"transactions_{branch_id}_{destination_branch_id}"
            
            # Check cache first
            if (hasattr(self, f"_{cache_key}_cache") and 
                current_time - getattr(self, f"_last_{cache_key}_update", 0) < self.TRANSACTIONS_CACHE_DURATION):
                return getattr(self, f"_{cache_key}_cache")
            
            # Make request with caching
            params = {}
            if branch_id:
                params["branch_id"] = branch_id
            if destination_branch_id:
                params["destination_branch_id"] = destination_branch_id
            
            data = self.make_request(
                f"{self.api_url}/transactions/",
                params=params,
                cache_duration=self.TRANSACTIONS_CACHE_DURATION,
                cache_key=f"_{cache_key}_cache"
            )
            
            if data:
                setattr(self, f"_{cache_key}_cache", data)
                setattr(self, f"_last_{cache_key}_update", current_time)
                return data
                
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return None

    def clear_cache(self, cache_type=None):
        """Clear specific or all cache"""
        if cache_type:
            # Clear specific cache
            if hasattr(self, f"_{cache_type}_cache"):
                setattr(self, f"_{cache_type}_cache", None)
                setattr(self, f"_last_{cache_type}_update", 0)
        else:
            # Clear all cache
            self._branches_cache = None
            self._financial_cache = None
            self._employee_stats_cache = None
            self._profits_cache = None
            self._transactions_cache = None
            self._last_branches_update = 0
            self._last_financial_update = 0
            self._last_employee_stats = 0
            self._last_profits_update = 0
            self._last_transactions_update = 0

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
