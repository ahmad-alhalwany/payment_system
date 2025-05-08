import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
    QDialog, QLineEdit, QFormLayout, QComboBox, QGridLayout, 
    QStatusBar, QDateEdit, QDoubleSpinBox, QDialogButtonBox
)
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, QDate, QSize
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
from ui.user_management_improved import AddEmployeeDialog
from dashboard.inventory import InventoryTab
from ui.user_search import UserSearchDialog
from ui.password_reset import PasswordResetDialog
from dashboard.manage import TableUpdateManager, DashboardCacheManager, DataLoadThread, ChartManager, BranchStatsLoader, TabDataManager
from dashboard.dashboard_utils import DashboardUtilsMixin

import os
import time
from datetime import datetime

class DirectorDashboard(QMainWindow, BranchAllocationMixin, MenuAuthMixin, ReceiptPrinterMixin, ReportHandlerMixin, SettingsHandlerMixin, EmployeeManagementMixin, BranchManagementMixin, DashboardUtilsMixin):
    """Dashboard for the director role."""
    
    def __init__(self, token=None, full_name="مدير النظام"):
        super().__init__()
        BranchManagementMixin.__init__(self)
        EmployeeManagementMixin.__init__(self)
        DashboardUtilsMixin.__init__(self)
        self.token = token
        self.api_url = os.environ["API_URL"]
        self.current_page = 1
        self.total_pages = 1
        self.per_page = 7
        self.current_page_transactions = 1
        self.transactions_per_page = 15
        self.total_pages_transactions = 1
        self.api_client = APIClient(token)
        self.current_zoom = 100
        self.full_name = full_name
        
        # Add smart loading variables
        self._is_initial_load = True
        self._current_tab = 0
        self._data_cache = {
            'basic_stats': {'data': None, 'timestamp': 0},
            'branches': {'data': None, 'timestamp': 0},
            'employees': {'data': None, 'timestamp': 0},
            'transactions': {'data': None, 'timestamp': 0},
            'financial': {'data': None, 'timestamp': 0},
            'users': {'data': None, 'timestamp': 0},
            'activity': {'data': None, 'timestamp': 0}
        }
        self.cache_duration = 600  # 10 minutes cache duration
        
        # --- Add missing QLabel attributes for stats ---
        self.employees_count = QLabel("0")
        self.transactions_count = QLabel("0")
        self.amount_total = QLabel("0")
        self.branches_count = QLabel("0")
        
        # Modify timer intervals and combine updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.smart_update)
        self.update_timer.start(600000)  # 10 minutes
        
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(60000)  # 1 minute
        
        self.setWindowTitle("لوحة تحكم المدير")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Setup UI components
        self.setup_ui_components()
        
        # Load basic data
        self.load_basic_dashboard_data()
        
        # Connect tab change signal
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Initialize cache manager
        self.cache_manager = DashboardCacheManager.getInstance()
        
        # Modify timer intervals
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.smart_update)
        self.update_timer.start(300000)  # 5 minutes instead of 30 seconds
        
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(60000)  # Keep 1 minute for time updates
        
        # Load initial data
        self.load_initial_data()
        
        # Initialize tab data manager
        self.tab_manager = TabDataManager(self)
        
        # Modify timer intervals
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_background_tasks)
        self.update_timer.start(5000)  # Check every 5 seconds
        
        # Setup UI with loading indicators
        self.setup_ui_with_loading()

    def setup_ui_with_loading(self):
        """Setup UI with loading indicators for each tab"""
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab:
                # Add loading overlay
                loading_overlay = QLabel(tab)
                loading_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                loading_overlay.setText("جاري التحميل...")
                loading_overlay.setStyleSheet("""
                    QLabel {
                        background-color: rgba(255, 255, 255, 0.8);
                        color: #2c3e50;
                        font-size: 16px;
                        padding: 20px;
                        border-radius: 10px;
                    }
                """)
                loading_overlay.hide()
                setattr(tab, 'loading_overlay', loading_overlay)
    
    def show_loading(self, tab, show=True):
        """Show/hide loading overlay for a tab"""
        if hasattr(tab, 'loading_overlay'):
            if show:
                tab.loading_overlay.show()
                tab.loading_overlay.raise_()
            else:
                tab.loading_overlay.hide()
    
    def process_background_tasks(self):
        """Process background tasks like preloading"""
        self.tab_manager.process_preload_queue()
    
    def on_tab_changed(self, index):
        """Handle tab change with improved loading"""
        current_tab = self.tabs.widget(index)
        if not current_tab:
            return
            
        tab_name = current_tab.objectName()
        
        # Show loading indicator
        self.show_loading(current_tab, True)
        
        # Load current tab data
        self.tab_manager.load_tab_data(tab_name)
        
        # Preload next tab data
        next_index = (index + 1) % self.tabs.count()
        next_tab = self.tabs.widget(next_index)
        if next_tab:
            self.tab_manager.preload_tab_data(next_tab.objectName())
    
    def handle_loaded_data(self, data):
        """Handle loaded data with loading indicators"""
        try:
            current_tab = self.tabs.currentWidget()
            
            if "basic_stats" in data:
                self.update_basic_stats(data["basic_stats"])
            if "transactions" in data:
                self.update_transactions_table(data["transactions"])
            if "activity" in data and hasattr(self, 'activity_list'):
                self.update_recent_activity_list(data["activity"])
                
            # Hide loading indicator for current tab
            if current_tab:
                self.show_loading(current_tab, False)
                
        except Exception as e:
            print(f"Error handling loaded data: {e}")
            self.statusBar().showMessage(f"خطأ في تحديث البيانات: {str(e)}", 5000)
            
            # Ensure loading indicator is hidden even on error
            if current_tab:
                self.show_loading(current_tab, False)

    def load_initial_data(self):
        """Load initial dashboard data efficiently"""
        # Start loading thread for all data
        self.load_thread = DataLoadThread(self.api_url, self.token, 'all')
        self.load_thread.data_loaded.connect(self.handle_loaded_data)
        self.load_thread.error_occurred.connect(self.handle_load_error)
        self.load_thread.progress_updated.connect(lambda msg: self.statusBar().showMessage(msg))
        self.load_thread.start()

    def handle_load_error(self, error_msg):
        """Handle loading errors"""
        QMessageBox.warning(self, "خطأ", error_msg)

    def smart_update(self):
        """Smart update mechanism that only updates necessary data"""
        current_tab = self.tabs.currentWidget()
        if not current_tab:
            return

        # Determine what type of data to load based on current tab
        load_type = 'basic'  # Default to basic stats
        if current_tab == self.transactions_tab:
            load_type = 'transactions'
        elif current_tab == self.activity_tab:
            load_type = 'activity'

        # Start loading thread for specific data type
        self.load_thread = DataLoadThread(self.api_url, self.token, load_type)
        self.load_thread.data_loaded.connect(self.handle_loaded_data)
        self.load_thread.error_occurred.connect(self.handle_load_error)
        self.load_thread.start()

    def refresh_dashboard(self):
        """Manual refresh triggered by user"""
        # Clear cache
        self.cache_manager.clear()
        # Load all data
        self.load_initial_data()

    def load_basic_dashboard_data(self):
        """Load only essential dashboard data with combined requests"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Combine multiple requests into one batch
            stats = {}
            
            # Get all stats in parallel
            responses = {
                'branches': requests.get(f"{self.api_url}/branches/stats/", headers=headers),
                'users': requests.get(f"{self.api_url}/users/stats/", headers=headers),
                'financial': requests.get(f"{self.api_url}/financial/total/", headers=headers)
            }
            
            # Process responses
            for key, response in responses.items():
                if response.status_code == 200:
                    stats.update(response.json())
            
            # Get today's transactions
            today = datetime.now().strftime("%Y-%m-%d")
            trans_response = requests.get(f"{self.api_url}/transactions/stats/?date={today}", headers=headers)
            if trans_response.status_code == 200:
                stats.update(trans_response.json())
            
            # Update cache and UI
            self._update_cache('basic_stats', stats)
            self.update_basic_stats(stats)
            
            # Load basic branch list for filters
            self.load_basic_branches()
            
        except Exception as e:
            print(f"Error loading basic dashboard data: {e}")
            self.statusBar().showMessage(f"خطأ في تحميل البيانات الأساسية: {str(e)}", 5000)

    def refresh_current_tab(self):
        """Refresh data for current tab with smart caching"""
        try:
            if self._current_tab == 0:  # Dashboard
                if not self._is_cache_valid('activity'):
                    self.load_recent_activity()
                if not self._is_cache_valid('financial'):
                    self.load_financial_status()
                if not self._is_cache_valid('branches'):
                    self.load_branch_status()
            elif self._current_tab == 1:  # Branches
                if not self._is_cache_valid('branches'):
                    self.load_branches()
            elif self._current_tab == 2:  # Employees
                if not self._is_cache_valid('users'):
                    self.load_employees()
            elif self._current_tab == 3:  # Transactions
                if not self._is_cache_valid('transactions'):
                    self.load_transactions()
        except Exception as e:
            print(f"Error refreshing current tab: {e}")

    def load_basic_branches(self):
        """Load only essential branch data for filters with caching"""
        try:
            # Check cache first
            cached_branches = self._get_cached_data('branches')
            if cached_branches:
                self.update_branch_filters(cached_branches)
                return
                
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            if response.status_code == 200:
                branches_data = response.json()
                if isinstance(branches_data, dict):
                    branches = branches_data.get("branches", [])
                    self._update_cache('branches', branches_data)  # Store the complete response
                    self.update_branch_filters(branches_data)
        except Exception as e:
            print(f"Error loading basic branches: {e}")

    def update_time(self):
        """Update time display"""
        try:
            current_time = datetime.now().strftime("%I:%M %p")
            current_date = datetime.now().strftime("%Y/%m/%d")
            if hasattr(self, 'time_label'):
                self.time_label.setText(f"{current_time} - {current_date}")
        except Exception as e:
            print(f"Error updating time: {e}")

    def _get_cached_data(self, cache_key):
        """Get data from cache if valid"""
        try:
            cache = self._data_cache.get(cache_key)
            if cache and self._is_cache_valid(cache_key):
                return cache['data']
            return None
        except Exception as e:
            print(f"Error getting cached data for {cache_key}: {e}")
            return None

    def _update_cache(self, cache_key, data):
        """Update cache with new data"""
        try:
            if data is not None:
                self._data_cache[cache_key] = {
                    'data': data,
                    'timestamp': time.time()
                }
        except Exception as e:
            print(f"Error updating cache for {cache_key}: {e}")

    def _clear_cache(self, cache_key=None):
        """Clear specific cache or all caches."""
        if cache_key:
            self._data_cache[cache_key] = {'data': None, 'timestamp': 0}
        else:
            for key in self._data_cache:
                self._data_cache[key] = {'data': None, 'timestamp': 0}

    def _is_cache_valid(self, cache_key):
        """Check if cache is still valid."""
        cache = self._data_cache.get(cache_key)
        return cache and time.time() - cache['timestamp'] < self.cache_duration

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
        
        # Add refresh button
        refresh_button = ModernButton("تحديث البيانات", color="#3498db")
        refresh_button.clicked.connect(self.manual_refresh)
        refresh_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        
        welcome_layout_inner.addWidget(welcome_text)
        welcome_layout_inner.addWidget(time_label)
        welcome_layout_inner.addWidget(refresh_button)
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
        
    def manual_refresh(self):
        """Manually refresh all dashboard data with optimized loading"""
        try:
            # Clear all caches
            self._clear_cache()
            
            # Load combined basic stats
            self.load_combined_basic_stats()
            
            # Load current tab data
            self.refresh_current_tab()
            
            self.statusBar().showMessage("تم تحديث البيانات بنجاح", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحديث البيانات: {str(e)}", 5000)
    
    def refresh_dashboard(self):
        """Refresh all dashboard data with optimized caching."""
        try:
            # Check if we need to update basic stats
            if not self._is_cache_valid('basic_stats'):
                self.load_combined_basic_stats()
            else:
                # Use cached data
                cached_stats = self._get_cached_data('basic_stats')
                if cached_stats:
                    self.update_basic_stats(cached_stats)
            
            # Update recent activity only if needed
            if not self._is_cache_valid('activity'):
                self.load_recent_activity()
            
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            self.statusBar().showMessage(f"خطأ في تحديث لوحة المعلومات: {str(e)}", 5000)
    
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
        """Load recent activity data."""
        try:
            # Check cache first
            cached_activity = self.cache_manager.get('activity')
            if cached_activity:
                self.update_recent_activity_list(cached_activity)
                return

            # If not in cache, load from server
            self.load_thread = DataLoadThread(self.api_url, self.token, 'activity')
            self.load_thread.data_loaded.connect(self.handle_loaded_data)
            self.load_thread.error_occurred.connect(self.handle_load_error)
            self.load_thread.start()
            
        except Exception as e:
            print(f"Error loading recent activity: {e}")
            self.statusBar().showMessage(f"خطأ في تحميل النشاطات الحديثة: {str(e)}", 5000)

    def update_recent_activity_list(self, activities):
        """Update the recent activity list with new data."""
        try:
            if not hasattr(self, 'activity_list'):
                return
                
            self.activity_list.setRowCount(len(activities))
            
            for i, activity in enumerate(activities):
                # Time
                time_item = QTableWidgetItem(activity.get("time", ""))
                time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.activity_list.setItem(i, 0, time_item)
                
                # Type
                type_item = QTableWidgetItem(activity.get("type", ""))
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.activity_list.setItem(i, 1, type_item)
                
                # Details
                details_item = QTableWidgetItem(activity.get("details", ""))
                self.activity_list.setItem(i, 2, details_item)
                
                # Status
                status = activity.get("status", "")
                status_item = QTableWidgetItem(get_status_arabic(status))
                status_item.setBackground(get_status_color(status))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.activity_list.setItem(i, 3, status_item)
                
            # Resize columns to content
            self.activity_list.resizeColumnsToContents()
            
            # Update last refresh time if exists
            if hasattr(self, 'last_refresh_label'):
                current_time = datetime.now().strftime("%I:%M %p")
                self.last_refresh_label.setText(f"آخر تحديث: {current_time}")
                
        except Exception as e:
            print(f"Error updating activity list: {e}")
            self.statusBar().showMessage("خطأ في تحديث قائمة النشاطات", 5000)

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
        refresh_button.clicked.connect(self.refresh_employees)
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
        """Load data for the dashboard with caching."""
        try:
            # Load combined basic stats
            self.load_combined_basic_stats()
            
            # Load recent transactions only if needed
            if self.tabs.currentIndex() == 0:  # Only load if on dashboard tab
                self.load_recent_transactions()
            
        except Exception as e:
            print(f"Error loading dashboard data: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل بيانات لوحة المعلومات: {str(e)}")
    
    def load_recent_transactions(self):
        """Load recent transactions with optimized table updates and caching"""
        try:
            self.statusBar().showMessage("جاري تحميل التحويلات...")
            
            # Check cache first
            cached_transactions = self._get_cached_data('transactions')
            if cached_transactions:
                self.update_transactions_table({'transactions': cached_transactions})
                return
            
            # Initialize table update manager if not exists
            if not hasattr(self, 'table_manager'):
                self.table_manager = TableUpdateManager(self.recent_transactions_table)
            
            # Create and start data loading thread
            self.load_thread = DataLoadThread(self.api_url, self.token, 'transactions')
            self.load_thread.data_loaded.connect(self._handle_transactions_data)
            self.load_thread.error_occurred.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
            self.load_thread.progress_updated.connect(lambda msg: self.statusBar().showMessage(msg))
            self.load_thread.start()
            
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في تحميل البيانات: {str(e)}", 5000)

    def _handle_transactions_data(self, data):
        """Handle loaded transactions data and update cache"""
        try:
            transactions = data.get("transactions", [])
            # Update cache
            self._update_cache('transactions', transactions)
            # Update table
            self.update_transactions_table(data)
        except Exception as e:
            self.statusBar().showMessage(f"خطأ في معالجة البيانات: {str(e)}", 5000)

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
    
    def reset_password(self):
        """Reset password for the selected employee."""
        selected_rows = self.employees_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف لإعادة تعيين كلمة المرور")
            return
        
        row = selected_rows[0].row()
        employee_data = self.employees_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        employee_username = employee_data.get("username", "")
        
        # Use the dedicated password reset dialog
        dialog = PasswordResetDialog(is_admin=True, token=self.token)
        dialog.username_input.setText(employee_username)
        dialog.username_input.setReadOnly(True)  # Prevent changing username
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
        dialog = UserSearchDialog(token=self.token, parent=self, received=True)
        dialog.exec()
    def setup_inventory_tab(self):
        """Set up the inventory tab for tracking tax receivables and profits."""
        
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

    def new_transfer(self):
        """Switch to admin transfer tab for a new transfer."""
        self.tabs.setCurrentIndex(4)  # Switch to admin transfer tab

    def add_employee(self):
        """Open dialog to add a new employee."""
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

    def load_branches_for_filter(self):
        """Load branches for filter dropdowns with caching"""
        try:
            # Check cache first
            cached_branches = self._get_cached_data('branches')
            if not cached_branches:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                response = requests.get(f"{self.api_url}/branches/", headers=headers)
                if response.status_code == 200:
                    cached_branches = response.json()
                    self._update_cache('branches', cached_branches)
                else:
                    return

            branches = cached_branches.get("branches", [])
            
            # Update branch filter if it exists
            if hasattr(self, 'branch_filter'):
                self.branch_filter.clear()
                self.branch_filter.addItem("الكل", None)
            
            # Update transaction branch filter if it exists
            if hasattr(self, 'transaction_branch_filter'):
                self.transaction_branch_filter.clear()
                self.transaction_branch_filter.addItem("الكل", None)
            
            for branch in branches:
                if isinstance(branch, dict):
                    branch_id = branch.get("id")
                    branch_name = branch.get("name", "")
                    
                    if branch_id is not None and branch_name:
                        if hasattr(self, 'branch_filter'):
                            self.branch_filter.addItem(branch_name, branch_id)
                        
                        if hasattr(self, 'transaction_branch_filter'):
                            self.transaction_branch_filter.addItem(branch_name, branch_id)
                
        except Exception as e:
            print(f"Error loading branches for filter: {e}")

    def setup_ui_components(self):
        """Setup basic UI components"""
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
        
        # Initialize all tabs
        self.initialize_tabs()
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("جاهز")
        
        # Initialize branch_id_to_name mapping
        if not hasattr(self, 'branch_id_to_name'):
            self.branch_id_to_name = {}
        
        # Initialize chart manager
        self.chart_manager = ChartManager(self)

    def initialize_tabs(self):
        """Initialize all tabs without loading their data"""
        # Dashboard tab
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "لوحة المعلومات")
        
        # Branches tab
        self.branches_tab = QWidget()
        self.setup_branches_tab()
        self.tabs.addTab(self.branches_tab, "الفروع")
        
        # Employees tab - Initialize UI only
        self.employees_tab = QWidget()
        self.setup_employees_tab_ui()
        self.tabs.addTab(self.employees_tab, "الموظفين")
        
        # Transactions tab
        self.transactions_tab = QWidget()
        self.setup_transactions_tab()
        self.tabs.addTab(self.transactions_tab, "التحويلات")
        
        # Admin Money Transfer tab
        self.admin_transfer_tab = QWidget()
        self.setup_admin_transfer_tab()
        self.tabs.addTab(self.admin_transfer_tab, "تحويل الأموال")
        
        # Reports tab - Initialize UI only
        self.reports_tab = QWidget()
        self.setup_reports_tab_ui()
        self.tabs.addTab(self.reports_tab, "التقارير")
        
        # Inventory tab - Initialize UI only
        self.inventory_tab = QWidget()
        self.setup_inventory_tab_ui()
        self.tabs.addTab(self.inventory_tab, "المخزون")
        
        # Settings tab
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "الإعدادات")

    def setup_employees_tab_ui(self):
        """Set up the employees tab UI without loading data"""
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
        refresh_button.clicked.connect(self.refresh_employees)
        buttons_layout.addWidget(refresh_button)
        
        layout.addLayout(buttons_layout)
        
        self.employees_tab.setLayout(layout)

    def setup_reports_tab_ui(self):
        """Set up the reports tab UI without loading data"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("التقارير")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Add loading indicator
        self.reports_loading = QLabel("جاري تحميل التقارير...")
        self.reports_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reports_loading.setVisible(False)
        layout.addWidget(self.reports_loading)
        
        # Add placeholder for reports content
        self.reports_content = QWidget()
        layout.addWidget(self.reports_content)
        
        self.reports_tab.setLayout(layout)

    def setup_inventory_tab_ui(self):
        """Set up the inventory tab UI without loading data"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("المخزون")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Add loading indicator
        self.inventory_loading = QLabel("جاري تحميل بيانات المخزون...")
        self.inventory_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inventory_loading.setVisible(False)
        layout.addWidget(self.inventory_loading)
        
        # Add placeholder for inventory content
        self.inventory_content = QWidget()
        layout.addWidget(self.inventory_content)
        
        self.inventory_tab.setLayout(layout)

    def on_tab_changed(self, index):
        """Handle tab change and load necessary data"""
        if index == self._current_tab:
            return
            
        self._current_tab = index
        
        # Load tab specific data
        if index == 0:  # Dashboard
            self.load_dashboard_details()
        elif index == 1:  # Branches
            self.load_branches_details()
        elif index == 2:  # Employees
            self.load_employees_details()
        elif index == 3:  # Transactions
            self.load_transactions_details()
        elif index == 4:  # Money Transfer
            self.load_money_transfer_details()
        elif index == 5:  # Reports
            self.load_reports_details()
        elif index == 6:  # Inventory
            self.load_inventory_details()
        elif index == 7:  # Settings
            self.load_settings_details()

    def setup_auto_refresh(self):
        """Setup automatic refresh timers with optimized intervals"""
        # Basic stats refresh every 10 minutes
        self.basic_refresh_timer = QTimer()
        self.basic_refresh_timer.timeout.connect(self.load_combined_basic_stats)
        self.basic_refresh_timer.start(600000)  # 10 minutes
        
        # Current tab refresh every minute
        self.tab_refresh_timer = QTimer()
        self.tab_refresh_timer.timeout.connect(self.refresh_current_tab)
        self.tab_refresh_timer.start(60000)  # 1 minute

    def load_combined_basic_stats(self):
        """Load all basic statistics in one combined request"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Check if we have valid cached data
            if self._is_cache_valid('basic_stats'):
                self.update_basic_stats(self._get_cached_data('basic_stats'))
                return
                
            # Make parallel requests for all basic stats
            responses = {
                'branches': requests.get(f"{self.api_url}/branches/stats/", headers=headers),
                'users': requests.get(f"{self.api_url}/users/stats/", headers=headers),
                'financial': requests.get(f"{self.api_url}/financial/total/", headers=headers)
            }
            
            # Combine all responses
            combined_stats = {}
            for key, response in responses.items():
                if response.status_code == 200:
                    combined_stats.update(response.json())
                else:
                    print(f"Error loading {key} stats: {response.status_code}")
            
            # Update cache with combined data
            self._update_cache('basic_stats', combined_stats)
            
            # Update UI with new data
            self.update_basic_stats(combined_stats)
            
            # Also update individual caches
            if 'branches' in responses and responses['branches'].status_code == 200:
                self._update_cache('branches', responses['branches'].json())
            if 'users' in responses and responses['users'].status_code == 200:
                self._update_cache('users', responses['users'].json())
            if 'financial' in responses and responses['financial'].status_code == 200:
                self._update_cache('financial', responses['financial'].json())
            
        except Exception as e:
            print(f"Error loading combined basic stats: {e}")
            self.statusBar().showMessage(f"خطأ في تحميل البيانات الأساسية: {str(e)}", 5000)

    def update_basic_stats(self, data):
        """Update basic statistics with combined data."""
        try:
            # Update branch stats
            if 'branches' in data:
                branch_stats = data['branches']
                self.branch_count_label.setText(str(branch_stats.get('total', 0)))
                self.active_branches_label.setText(str(branch_stats.get('active', 0)))
                self.inactive_branches_label.setText(str(branch_stats.get('inactive', 0)))
            
            # Update user stats
            if 'users' in data:
                user_stats = data['users']
                self.total_users_label.setText(str(user_stats.get('total', 0)))
                self.active_users_label.setText(str(user_stats.get('active', 0)))
                self.inactive_users_label.setText(str(user_stats.get('inactive', 0)))
            
            # Update financial stats
            if 'financial' in data:
                financial_stats = data['financial']
                self.total_balance_label.setText(f"{financial_stats.get('total_balance', 0):,.2f}")
                self.total_income_label.setText(f"{financial_stats.get('total_income', 0):,.2f}")
                self.total_expenses_label.setText(f"{financial_stats.get('total_expenses', 0):,.2f}")
            
            # Update cache timestamp
            self._update_cache('basic_stats', data)
            
        except Exception as e:
            print(f"Error updating basic stats: {e}")
            self.statusBar().showMessage(f"خطأ في تحديث الإحصائيات الأساسية: {str(e)}", 5000)

    def update_branch_filters(self, branches):
        """Update branch filters with basic branch data"""
        try:
            # Ensure branches is a list
            if isinstance(branches, dict):
                branches = branches.get("branches", [])
            elif not isinstance(branches, list):
                print(f"Invalid branches data type: {type(branches)}")
                return

            # Update branch filter if it exists
            if hasattr(self, 'branch_filter'):
                self.branch_filter.clear()
                self.branch_filter.addItem("الكل", None)
            
            # Update transaction branch filter if it exists
            if hasattr(self, 'transaction_branch_filter'):
                self.transaction_branch_filter.clear()
                self.transaction_branch_filter.addItem("الكل", None)
            
            # Add branches to filters
            for branch in branches:
                if isinstance(branch, dict):
                    branch_id = branch.get("id")
                    branch_name = branch.get("name", "")
                    
                    if branch_id is not None and branch_name:
                        if hasattr(self, 'branch_filter'):
                            self.branch_filter.addItem(branch_name, branch_id)
                        
                        if hasattr(self, 'transaction_branch_filter'):
                            self.transaction_branch_filter.addItem(branch_name, branch_id)
                
        except Exception as e:
            print(f"Error updating branch filters: {e}")

    def load_dashboard_details(self):
        """Load detailed dashboard data"""
        try:
            if not self._is_cache_valid('basic_stats'):
                self.load_basic_dashboard_data()
            self.load_recent_activity()
            self.load_financial_status()
            self.load_branch_status()
        except Exception as e:
            print(f"Error loading dashboard details: {e}")

    def load_branches_details(self):
        """Load detailed branch data"""
        try:
            if not self._is_cache_valid('branches'):
                self.load_branches()
            self.load_branch_stats()
        except Exception as e:
            print(f"Error loading branch details: {e}")

    def load_employees_details(self):
        """Load detailed employee data"""
        try:
            # Show loading indicator
            if hasattr(self, 'employees_table'):
                self.employees_table.setRowCount(0)
                self.employees_table.setRowCount(1)
                loading_item = QTableWidgetItem("جاري تحميل البيانات...")
                loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.employees_table.setItem(0, 0, loading_item)
                self.employees_table.setSpan(0, 0, 1, 5)
            
            # Load data if not in cache or cache is invalid
            if not self._is_cache_valid('employees'):
                self.load_employees()
            
            # Load branch filter data
            self.load_branches_for_filter()
            
        except Exception as e:
            print(f"Error loading employee details: {e}")

    def load_transactions_details(self):
        """Load detailed transaction data"""
        try:
            if not self._is_cache_valid('transactions'):
                self.load_transactions()
            self.load_transaction_stats()
        except Exception as e:
            print(f"Error loading transaction details: {e}")

    def load_money_transfer_details(self):
        """Load money transfer tab data"""
        try:
            if hasattr(self, 'admin_transfer_widget'):
                self.admin_transfer_widget.load_branches()
        except Exception as e:
            print(f"Error loading money transfer details: {e}")

    def load_reports_details(self):
        """Load reports tab data"""
        try:
            # Show loading indicator
            if hasattr(self, 'reports_loading'):
                self.reports_loading.setVisible(True)
            
            # Initialize report handler if not exists
            if not hasattr(self, 'report_handler'):
                from dashboard.report_handler import ReportHandlerMixin
                self.report_handler = ReportHandlerMixin()
                self.report_handler.set_api_client(self.token, self.api_url)
                self.report_handler.set_parent(self)
                
                # Create reports content layout if not exists
                if not hasattr(self, 'reports_content_layout'):
                    self.reports_content_layout = QVBoxLayout()
                    self.reports_content.setLayout(self.reports_content_layout)
                
                # Setup report handler UI
                self.report_handler.setup_reports_tab()
                
                # Add the reports tab widget to our layout
                self.reports_content_layout.addWidget(self.report_handler.reports_tab)
            
            # Generate initial report
            self.report_handler.generate_report()
            
            # Hide loading indicator
            if hasattr(self, 'reports_loading'):
                self.reports_loading.setVisible(False)
            
        except Exception as e:
            print(f"Error loading reports details: {e}")
            if hasattr(self, 'reports_loading'):
                self.reports_loading.setVisible(False)
            self.statusBar().showMessage(f"خطأ في تحميل التقارير: {str(e)}", 5000)

    def load_inventory_details(self):
        """Load inventory tab data"""
        try:
            # Show loading indicator
            if hasattr(self, 'inventory_loading'):
                self.inventory_loading.setVisible(True)
            
            # Initialize inventory widget if not exists
            if not hasattr(self, 'inventory_widget'):
                from dashboard.inventory import InventoryTab
                self.inventory_widget = InventoryTab(token=self.token, parent=self)
                
                # Create inventory content layout if not exists
                if not hasattr(self, 'inventory_content_layout'):
                    self.inventory_content_layout = QVBoxLayout()
                    self.inventory_content.setLayout(self.inventory_content_layout)
                
                # Add inventory widget to layout
                self.inventory_content_layout.addWidget(self.inventory_widget)
            
            # Load inventory data
            self.inventory_widget.load_data()
            
            # Hide loading indicator
            if hasattr(self, 'inventory_loading'):
                self.inventory_loading.setVisible(False)
            
        except Exception as e:
            print(f"Error loading inventory details: {e}")
            if hasattr(self, 'inventory_loading'):
                self.inventory_loading.setVisible(False)
            self.statusBar().showMessage(f"خطأ في تحميل بيانات المخزون: {str(e)}", 5000)

    def load_settings_details(self):
        """Load settings tab data"""
        try:
            if hasattr(self, 'settings_handler'):
                self.settings_handler.load_settings()
        except Exception as e:
            print(f"Error loading settings details: {e}")

    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        cache = self._data_cache.get(cache_key)
        if not cache:
            return False
        return time.time() - cache['timestamp'] < self.cache_duration

    def _update_cache(self, cache_key, data):
        """Update cache with new data"""
        self._data_cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    def _get_cached_data(self, cache_key):
        """Get data from cache if valid"""
        cache = self._data_cache.get(cache_key)
        if cache and self._is_cache_valid(cache_key):
            return cache['data']
        return None

    def load_employee_stats(self):
        """Load employee statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/users/stats/", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self._update_cache('users', stats)
                # Update employee count if needed
                if hasattr(self, 'employees_count'):
                    self.employees_count.setText(str(stats.get("total", 0)))
        except Exception as e:
            print(f"Error loading employee stats: {e}")

    def load_transaction_stats(self):
        """Load transaction statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            today = datetime.now().strftime("%Y-%m-%d")
            response = requests.get(f"{self.api_url}/transactions/stats/?date={today}", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self._update_cache('transactions', stats)
                # Update transaction count if needed
                if hasattr(self, 'transactions_count'):
                    self.transactions_count.setText(str(stats.get("total", 0)))
        except Exception as e:
            print(f"Error loading transaction stats: {e}")

    def refresh_employees(self):
        self._employees_cache = None
        self.load_employees()
