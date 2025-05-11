import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QLineEdit, QFormLayout, QComboBox,
    QCheckBox, QMenu, QDialogButtonBox, QPushButton, QStatusBar,
    QTableView, QMainWindow, QDateEdit, QDoubleSpinBox, QTextEdit
)
import os
from PyQt6.QtGui import QFont, QColor, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDate, QAbstractTableModel, QModelIndex, QThread
from datetime import datetime
from ui.user_search import UserSearchDialog
from ui.custom_widgets import ModernGroupBox, ModernButton
from ui.menu_auth import MenuAuthMixin
from utils.helpers import get_status_arabic, get_status_color
from money_transfer.receipt_printer import ReceiptPrinter
from money_transfer.transaction_details import TransactionDetailsDialog
from money_transfer.transfers import TransferCore
import time

class TransactionTableModel(QAbstractTableModel):
    """Efficient table model with virtual scrolling support"""
    
    HEADERS = [
        "رقم التحويل", "التاريخ", "المرسل", "المستلم", "المبلغ", "العملة",
        "محافظة المستلم", "الحالة", "النوع", "اسم الموظف", "الفرع المرسل",
        "الفرع المستلم", "محافظة الفرع"
    ]
    
    def __init__(self):
        super().__init__()
        self._data = []
        self._cached_items = {}
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
        
    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)
        
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            
            # Use caching for formatted data
            cache_key = (row, col)
            if cache_key in self._cached_items:
                return self._cached_items[cache_key]
            
            # Get raw data
            if row >= len(self._data):
                return None
            
            transaction = self._data[row]
            value = self._get_column_data(transaction, col)
            
            # Cache the formatted value
            self._cached_items[cache_key] = value
            return value
            
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Handle status colors for the status column
            if index.column() == 7:  # Status column
                status = self._data[index.row()].get("status", "")
                return get_status_color(status)
                
        return None
        
    def _get_column_data(self, transaction, col):
        """Get formatted data for a specific column"""
        try:
            if col == 0:  # ID
                return str(transaction.get("id", ""))
            elif col == 1:  # Date
                return self._format_date(transaction.get("date", ""))
            elif col == 2:  # Sender
                return transaction.get("sender", "")
            elif col == 3:  # Receiver
                return transaction.get("receiver", "")
            elif col == 4:  # Amount
                amount = transaction.get("amount", 0)
                return f"{float(amount):,.2f}" if amount else "0.00"
            elif col == 5:  # Currency
                return transaction.get("currency", "")
            elif col == 6:  # Receiver Governorate
                return transaction.get("receiver_governorate", "")
            elif col == 7:  # Status
                return get_status_arabic(transaction.get("status", ""))
            elif col == 8:  # Type
                return self._get_transaction_type(transaction)
            elif col == 9:  # Employee Name
                return transaction.get("employee_name", "")
            elif col == 10:  # Sending Branch
                return transaction.get("sending_branch_name", "")
            elif col == 11:  # Destination Branch
                return transaction.get("destination_branch_name", "")
            elif col == 12:  # Branch Governorate
                return transaction.get("branch_governorate", "")
        except Exception as e:
            print(f"Error formatting column {col}: {e}")
            return ""
            
    def _format_date(self, date_str):
        """Format date string"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")
        except:
            return date_str
            
    def _get_transaction_type(self, transaction):
        """Determine transaction type"""
        if transaction.get("type") == "sent":
            return "↑ صادر"
        elif transaction.get("type") == "received":
            return "↓ وارد"
        return "غير معروف"
        
    def update_data(self, new_data):
        """Update model data efficiently"""
        self.beginResetModel()
        self._data = new_data
        self._cached_items.clear()
        self.endResetModel()
        
    def get_transaction(self, row):
        """Get transaction data for a specific row"""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

class SearchManager:
    """Manages efficient search and filtering operations for transactions."""
    
    def __init__(self):
        self._search_cache = {}
        self._filter_cache = {}
        self._last_search_time = 0
        self._search_throttle = 0.3  # 300ms throttle
        
    def search_transactions(self, transactions, search_term, search_fields=None):
        """Efficiently search transactions with caching and throttling."""
        if not search_term:
            return transactions
            
        # Use default search fields if none specified
        if search_fields is None:
            search_fields = ['id', 'sender', 'receiver', 'sender_mobile', 'receiver_mobile']
            
        # Create cache key
        cache_key = (search_term, tuple(sorted(search_fields)))
        
        # Check cache first
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
            
        # Throttle searches
        current_time = time.time()
        if current_time - self._last_search_time < self._search_throttle:
            return self._search_cache.get(cache_key, transactions)
            
        self._last_search_time = current_time
        
        # Perform search
        search_term = search_term.lower()
        results = []
        
        for transaction in transactions:
            for field in search_fields:
                value = str(transaction.get(field, '')).lower()
                if search_term in value:
                    results.append(transaction)
                    break
                    
        # Cache results
        self._search_cache[cache_key] = results
        return results
        
    def filter_transactions(self, transactions, filters):
        """Efficiently filter transactions with caching."""
        if not filters:
            return transactions
            
        # Create cache key
        cache_key = tuple(sorted(filters.items()))
        
        # Check cache first
        if cache_key in self._filter_cache:
            return self._filter_cache[cache_key]
            
        # Apply filters
        filtered = transactions
        for field, value in filters.items():
            if value == "all":
                continue
            filtered = [t for t in filtered if str(t.get(field, '')).lower() == str(value).lower()]
            
        # Cache results
        self._filter_cache[cache_key] = filtered
        return filtered
        
    def clear_cache(self):
        """Clear search and filter caches."""
        self._search_cache.clear()
        self._filter_cache.clear()
        
    def update_cache(self, transactions):
        """Update cache with new transaction data."""
        self.clear_cache()
        # Pre-compute common searches
        self.search_transactions(transactions, '', ['id'])
        self.search_transactions(transactions, '', ['sender'])
        self.search_transactions(transactions, '', ['receiver'])

class TransferWorker(QThread):
    """Worker thread for handling transfer operations"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, api_url, data, headers):
        super().__init__()
        self.api_url = api_url
        self.data = data
        self.headers = headers
        
    def run(self):
        try:
            # Emit progress signal
            self.progress.emit("جاري التحقق من البيانات...")
            
            # Validate data
            if not self.validate_data():
                self.error.emit("بيانات غير صالحة")
                return
                
            # Emit progress signal
            self.progress.emit("جاري إرسال التحويل...")
            
            # Send transfer
            response = requests.post(
                f"{self.api_url}/transactions/",
                json=self.data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 201:
                self.finished.emit(response.json())
            else:
                error_msg = f"فشل إرسال التحويل: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        if isinstance(error_data["detail"], list):
                            error_msg = "\n".join([str(err) for err in error_data["detail"]])
                        else:
                            error_msg = str(error_data["detail"])
                except:
                    pass
                self.error.emit(error_msg)
                
        except Exception as e:
            self.error.emit(f"خطأ في الاتصال: {str(e)}")
            
    def validate_data(self):
        """Validate transfer data"""
        required_fields = [
            "sender", "sender_mobile", "receiver", "receiver_mobile",
            "amount", "currency", "destination_branch_id"
        ]
        
        for field in required_fields:
            if not self.data.get(field):
                return False
                
        return True

class LoadingOverlay(QWidget):
    """Loading overlay widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        self.status_label = QLabel("جاري المعالجة...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def set_status(self, text):
        self.status_label.setText(text)

class MoneyTransferApp(QMainWindow, ReceiptPrinter, TransferCore, MenuAuthMixin):
    """Money Transfer Application for the Internal Payment System."""
    transferCompleted = pyqtSignal()
    logoutRequested = pyqtSignal()
    
    def __init__(self, user_token=None, branch_id=None, user_id=None, user_role="employee", username=None, full_name=None):
        super().__init__()
        self.user_token = user_token
        self.branch_id = branch_id
        self.user_id = user_id
        self.user_role = user_role
        self.username = username
        self.full_name = full_name if full_name else username
        self.api_url = os.environ["API_URL"]
        self.per_page_outgoing = 18
        self.per_page_incoming = 18
        self.current_zoom = 100  # Track current zoom level
        
        # Initialize search manager
        self.search_manager = SearchManager()
        
        self.setWindowTitle("نظام تحويل الأموال الداخلي")
        self.setGeometry(100, 100, 800, 700)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Only create menu bar for regular employees
        if self.user_role == "employee":
            self.create_menu_bar()
        
        self.setup_ui()
        
        # Load initial data
        self.load_branches()
        self.load_transactions()
        self.load_received_transactions()
        
        # Pagination variables
        self.current_page_outgoing = 1
        self.total_pages_outgoing = 1
        self.per_page_outgoing = 18
        
        self.current_page_incoming = 1
        self.total_pages_incoming = 1
        self.per_page_incoming = 18
        
        # Set up refresh timer for transactions and notifications
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Set up branch refresh timer
        self.branch_timer = QTimer()
        self.branch_timer.timeout.connect(self.refresh_branches)
        self.branch_timer.start(30000)  # Refresh every 5 seconds
        
        # Add loading overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()
        
    def setup_ui(self):
        """Set up the UI components."""
        # Title
        title = QLabel("نظام تحويل الأموال")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        self.layout.addWidget(title)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
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
        
        # Create tab widgets
        self.new_transfer_tab = QWidget()
        self.transactions_tab = QWidget()
        self.notifications_tab = QWidget()
        self.receive_money_tab = QWidget()
        
        # Set up tabs
        self.setup_new_transfer_tab()
        self.setup_transactions_tab()
        self.setup_notifications_tab()
        self.setup_receive_money_tab()
        
        # Add tabs to widget
        self.tabs.addTab(self.new_transfer_tab, "تحويل جديد")
        self.tabs.addTab(self.transactions_tab, "التحويلات الصادرة")
        self.tabs.addTab(self.receive_money_tab, "التحويلات الواردة")
            
        self.layout.addWidget(self.tabs)
        
    def setup_receive_money_tab(self):
        """Set up the new receive money tab."""
        layout = QVBoxLayout()

        # Updated title
        title = QLabel("التحويلات الواردة")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        # Search button
        search_button = ModernButton("بحث", color="#3498db")
        search_button.clicked.connect(self.search_received_transactions)
        filter_layout.addWidget(search_button)
        
        # Refresh button
        refresh_button = ModernButton("تحديث", color="#2ecc71")
        refresh_button.clicked.connect(self.load_received_transactions)
        filter_layout.addWidget(refresh_button)
        
        # Filter by status
        status_label = QLabel("تصفية حسب الحالة:")
        filter_layout.addWidget(status_label)
        
        self.receive_status_filter = QComboBox()
        self.receive_status_filter.addItem("الكل", "all")
        self.receive_status_filter.addItem("قيد الانتظار", "pending")
        self.receive_status_filter.addItem("قيد المعالجة", "processing")
        self.receive_status_filter.addItem("مكتمل", "completed")
        self.receive_status_filter.addItem("ملغي", "cancelled")
        self.receive_status_filter.addItem("مرفوض", "rejected")
        self.receive_status_filter.addItem("معلق", "on_hold")
        self.receive_status_filter.currentIndexChanged.connect(self.filter_received_transactions)
        self.receive_status_filter.currentIndexChanged.connect(
            lambda: self.on_filter_change('incoming')
        )
        filter_layout.addWidget(self.receive_status_filter)
        
        # Filter by type
        type_label = QLabel("تصفية حسب النوع:")
        filter_layout.addWidget(type_label)
        
        self.receive_type_filter = QComboBox()
        self.receive_type_filter.addItem("الكل", "all")
        self.receive_type_filter.addItem("وارد", "incoming")
        self.receive_type_filter.addItem("صادر", "outgoing")
        self.receive_type_filter.currentIndexChanged.connect(self.filter_received_transactions)
        self.receive_type_filter.currentIndexChanged.connect(
            lambda: self.on_filter_change('incoming')
        )
        filter_layout.addWidget(self.receive_type_filter)
        
        layout.addLayout(filter_layout)
        
        # Received transactions table
        self.received_table = QTableWidget()
        self.received_table.setColumnCount(14)  # Changed from 13 to 14
        self.received_table.setHorizontalHeaderLabels([
            "رقم التحويل", "التاريخ", "المرسل", "المستلم", "المبلغ", "العملة", 
            "محافظة المستلم", "الحالة", "النوع", "اسم الموظف", "الفرع المرسل", 
            "الفرع المستلم", "محافظة الفرع", "مستلم؟"
        ])
        self.received_table.horizontalHeader().setStretchLastSection(True)
        self.received_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.received_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Connect double-click event
        self.received_table.itemDoubleClicked.connect(self.print_received_transaction)
        
        # Connect context menu event
        self.received_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.received_table.customContextMenuRequested.connect(self.show_received_context_menu)
        
        layout.addWidget(self.received_table)
        
        # Status bar
        status_layout = QHBoxLayout()
        
        self.receive_status_label = QLabel("جاهز")
        status_layout.addWidget(self.receive_status_label)
        
        self.receive_count_label = QLabel("عدد التحويلات: 0")
        status_layout.addWidget(self.receive_count_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(status_layout)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_button_incoming = ModernButton("السابق", color="#3498db")
        self.prev_button_incoming.clicked.connect(self.prev_page_incoming)
        pagination_layout.addWidget(self.prev_button_incoming)
        
        self.page_label_incoming = QLabel("الصفحة: 1")
        pagination_layout.addWidget(self.page_label_incoming)
        
        self.next_button_incoming = ModernButton("التالي", color="#3498db")
        self.next_button_incoming.clicked.connect(self.next_page_incoming)
        pagination_layout.addWidget(self.next_button_incoming)
        
        layout.addLayout(pagination_layout)
        
        # Buttons for received money actions
        button_layout = QHBoxLayout()
        
        # Mark as received button
        self.receive_button = ModernButton("تأكيد الاستلام", color="#2ecc71")
        self.receive_button.clicked.connect(self.mark_as_received)
        button_layout.addWidget(self.receive_button)
        
        # Print receipt button
        print_button = ModernButton("طباعة الإيصال", color="#3498db")
        print_button.clicked.connect(self.print_received_transaction)
        button_layout.addWidget(print_button)
        
        layout.addLayout(button_layout)
        
        self.receive_money_tab.setLayout(layout)
        
    def load_received_transactions(self):
        """Load received transactions for the current branch."""
        try:
            self.receive_status_label.setText("جاري تحميل بيانات التحويلات الواردة...")
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            
            # Get transactions where destination branch is current branch
            response = requests.get(
                f"{self.api_url}/transactions/?destination_branch_id={self.branch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = transactions_data.get("transactions", [])
                
                # Reset pagination
                self.current_page_incoming = 1
                self.filter_received_transactions()
                
                # Store transactions for filtering
                self.all_received_transactions = transactions
                
                # Apply current filter
                self.filter_received_transactions()
                
                # Update status
                self.receive_status_label.setText("تم تحميل بيانات التحويلات الواردة بنجاح")
                self.receive_count_label.setText(f"عدد التحويلات: {len(transactions)}")
            else:
                self.receive_status_label.setText(f"خطأ في تحميل بيانات التحويلات المستلمة: {response.status_code}")
                QMessageBox.warning(self, "خطأ", f"فشل تحميل بيانات التحويلات المستلمة: {response.text}")
        except Exception as e:
            self.receive_status_label.setText("خطأ في الاتصال")
            print(f"Error loading received transactions: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                            "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
            
    def filter_received_transactions(self):
        """Filter received transactions based on selected status and type."""
        if not hasattr(self, 'all_received_transactions'):
            return
        
        # Get filter criteria
        selected_status = self.receive_status_filter.currentData()
        selected_type = self.receive_type_filter.currentData()
        
        # Start with all transactions
        filtered_transactions = self.all_received_transactions
        
        # Apply status filter if not "all"
        if selected_status != "all":
            filtered_transactions = [t for t in filtered_transactions if t.get("status", "") == selected_status]
        
        # Apply type filter if not "all"
        if selected_type != "all":
            if selected_type == "incoming":
                # Filter for incoming transactions (destination branch is current branch)
                filtered_transactions = [t for t in filtered_transactions if t.get("destination_branch_id") == self.branch_id]
            elif selected_type == "outgoing":
                # Filter for outgoing transactions (source branch is current branch)
                filtered_transactions = [t for t in filtered_transactions if t.get("branch_id") == self.branch_id]
        
        # Pagination calculations
        self.total_pages_incoming = max(1, (len(filtered_transactions) + self.per_page_incoming - 1) // self.per_page_incoming)
        start_idx = (self.current_page_incoming - 1) * self.per_page_incoming
        end_idx = start_idx + self.per_page_incoming
        paginated_transactions = filtered_transactions[start_idx:end_idx]
        
        # Update table
        self.received_table.setRowCount(len(paginated_transactions))
        
        for i, transaction in enumerate(paginated_transactions):
            # Transaction ID
            self.received_table.setItem(i, 0, QTableWidgetItem(str(transaction.get("id", ""))))
            
            # Date
            date_str = transaction.get("date", "")
            formatted_date = date_str
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except:
                pass
            self.received_table.setItem(i, 1, QTableWidgetItem(formatted_date))
            
            # Sender
            self.received_table.setItem(i, 2, QTableWidgetItem(transaction.get("sender", "")))
            
            # Receiver
            self.received_table.setItem(i, 3, QTableWidgetItem(transaction.get("receiver", "")))
            
            # Amount
            amount = transaction.get("amount", 0)
            formatted_amount = f"{float(amount):,.2f}" if amount else "0.00"
            self.received_table.setItem(i, 4, QTableWidgetItem(formatted_amount))
            
            # Currency
            self.received_table.setItem(i, 5, QTableWidgetItem(transaction.get("currency", "")))
            
            # Receiver governorate
            self.received_table.setItem(i, 6, QTableWidgetItem(transaction.get("receiver_governorate", "")))
            
            # Status
            status = transaction.get("status", "pending")
            status_arabic = get_status_arabic(status)
            status_item = QTableWidgetItem(status_arabic)
            status_item.setBackground(get_status_color(status))
            self.received_table.setItem(i, 7, status_item)
            
            # Column 8: Type indicator
            type_item = self.create_incoming_type_item(transaction)
            self.received_table.setItem(i, 8, type_item)
            
            # Shift existing columns right by 1
            # Column 9: Employee name (previously 8)
            self.received_table.setItem(i, 9, QTableWidgetItem(transaction.get("employee_name", "")))
            
            # Column 10: Sending branch (previously 9)
            sending_branch_id = transaction.get("branch_id")
            sending_branch_name = self.branch_id_to_name.get(sending_branch_id, "غير معروف")
            self.received_table.setItem(i, 10, QTableWidgetItem(sending_branch_name))
            
            # Column 11: Destination branch (previously 10)
            dest_branch_id = transaction.get("destination_branch_id")
            dest_branch_name = self.branch_id_to_name.get(dest_branch_id, "غير معروف")
            self.received_table.setItem(i, 11, QTableWidgetItem(dest_branch_name))
            
            # Column 12: Branch governorate (previously 11)
            self.received_table.setItem(i, 12, QTableWidgetItem(transaction.get("branch_governorate", "")))
            
            # Column 13: Received status (previously 12)
            is_received = transaction.get("is_received", False)
            received_item = QTableWidgetItem("نعم" if is_received else "لا")
            received_item.setBackground(QColor(200, 255, 200) if is_received else QColor(255, 200, 200))
            self.received_table.setItem(i, 13, received_item)
        
        # Update count
        self.receive_count_label.setText(
            f"عدد التحويلات: {len(filtered_transactions)} "
            f"(الصفحة {self.current_page_incoming}/{self.total_pages_incoming})"
        )
        self.update_pagination_controls_incoming()  
        
    # Outgoing pagination controls
    def update_pagination_controls_outgoing(self):
        self.page_label_outgoing.setText(
            f"الصفحة: {self.current_page_outgoing}/{self.total_pages_outgoing}"
        )
        self.prev_button_outgoing.setEnabled(self.current_page_outgoing > 1)
        self.next_button_outgoing.setEnabled(self.current_page_outgoing < self.total_pages_outgoing)

    def prev_page_outgoing(self):
        if self.current_page_outgoing > 1:
            self.current_page_outgoing -= 1
            self.filter_transactions()

    def next_page_outgoing(self):
        if self.current_page_outgoing < self.total_pages_outgoing:
            self.current_page_outgoing += 1
            self.filter_transactions()

    # Incoming pagination controls
    def update_pagination_controls_incoming(self):
        self.page_label_incoming.setText(
            f"الصفحة: {self.current_page_incoming}/{self.total_pages_incoming}"
        )
        self.prev_button_incoming.setEnabled(self.current_page_incoming > 1)
        self.next_button_incoming.setEnabled(self.current_page_incoming < self.total_pages_incoming)

    def prev_page_incoming(self):
        if self.current_page_incoming > 1:
            self.current_page_incoming -= 1
            self.filter_received_transactions()

    def next_page_incoming(self):
        if self.current_page_incoming < self.total_pages_incoming:
            self.current_page_incoming += 1
            self.filter_received_transactions()     
        
    # Add new helper method for incoming type indicator
    def create_incoming_type_item(self, transaction):
        """Create type indicator item for incoming transactions table."""
        transfer_type = ""
        color = QColor()
        
        if transaction.get("destination_branch_id") == self.branch_id:
            transfer_type = "↓ وارد"  # Incoming - Red
            color = QColor(150, 0, 0)  # Dark red
        elif transaction.get("branch_id") == self.branch_id:
            transfer_type = "↑ صادر"  # Outgoing - Green
            color = QColor(0, 150, 0)  # Dark green
        else:
            transfer_type = "↔ آخر"    # Other
            color = QColor(100, 100, 100)
        
        item = QTableWidgetItem(transfer_type)
        item.setForeground(color)
        item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        return item
        
    def mark_as_received(self):
        """Mark selected transaction as received with additional recipient info."""
        selected_items = self.received_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "تحذير", "الرجاء تحديد تحويل لتأكيد استلامه")
            return
        
        row = selected_items[0].row()
        transaction_id = self.received_table.item(row, 0).text()
        
        # Get transaction details from the table
        transaction_data = {
            "id": transaction_id,
            "date": self.received_table.item(row, 1).text(),
            "sender": self.received_table.item(row, 2).text(),
            "receiver": self.received_table.item(row, 3).text(),
            "amount": self.received_table.item(row, 4).text(),
            "currency": self.received_table.item(row, 5).text(),
            "receiver_governorate": self.received_table.item(row, 6).text(),
            "status": self.received_table.item(row, 7).text(),
            "employee_name": self.received_table.item(row, 8).text(),
            "sending_branch": self.received_table.item(row, 9).text(),
            "destination_branch": self.received_table.item(row, 10).text(),
            "branch_governorate": self.received_table.item(row, 11).text()
        }
        
        # Create confirmation dialog
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("تأكيد استلام التحويل")
        confirm_dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Transaction info group
        trans_group = ModernGroupBox("معلومات التحويل", "#3498db")
        trans_layout = QFormLayout()
        
        trans_layout.addRow(QLabel("رقم التحويل:"), QLabel(transaction_data["id"]))
        trans_layout.addRow(QLabel("التاريخ:"), QLabel(transaction_data["date"]))
        trans_layout.addRow(QLabel("المبلغ:"), QLabel(f"{transaction_data['amount']} {transaction_data['currency']}"))
        trans_layout.addRow(QLabel("الفرع المرسل:"), QLabel(transaction_data["sending_branch"]))
        
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)
        
        # Sender info group (read-only)
        sender_group = ModernGroupBox("معلومات المرسل", "#e74c3c")
        sender_layout = QFormLayout()
        
        sender_layout.addRow(QLabel("اسم المرسل:"), QLabel(transaction_data["sender"]))
        sender_layout.addRow(QLabel("محافظة المرسل:"), QLabel(transaction_data["branch_governorate"]))
        
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)
        
        # Receiver info group (editable)
        receiver_group = ModernGroupBox("معلومات المستلم", "#2ecc71")
        receiver_layout = QFormLayout()
        
        # Receiver name
        self.receiver_name_input = QLineEdit(transaction_data["receiver"])
        receiver_layout.addRow(QLabel("اسم المستلم:"), self.receiver_name_input)
        
        # Receiver mobile
        self.receiver_mobile_input = QLineEdit()
        self.receiver_mobile_input.setPlaceholderText("أدخل رقم الهاتف")
        receiver_layout.addRow(QLabel("رقم الهاتف:"), self.receiver_mobile_input)
        
        # Receiver ID
        self.receiver_id_input = QLineEdit()
        self.receiver_id_input.setPlaceholderText("أدخل رقم الهوية")
        receiver_layout.addRow(QLabel("رقم الهوية:"), self.receiver_id_input)
        
        # Receiver address
        self.receiver_address_input = QLineEdit()
        self.receiver_address_input.setPlaceholderText("أدخل العنوان")
        receiver_layout.addRow(QLabel("العنوان:"), self.receiver_address_input)
        
        # Receiver governorate
        self.receiver_governorate_input = QComboBox()
        self.receiver_governorate_input.addItems([
            "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", 
            "إدلب", "دير الزور", "الرقة", "الحسكة", "السويداء", "درعا", "القنيطرة"
        ])
        
        # Set current governorate if it exists in the combo box
        current_gov = transaction_data["receiver_governorate"]
        index = self.receiver_governorate_input.findText(current_gov)
        if index >= 0:
            self.receiver_governorate_input.setCurrentIndex(index)
        
        receiver_layout.addRow(QLabel("المحافظة:"), self.receiver_governorate_input)
        
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)
        
        # Confirmation checkbox
        self.confirm_checkbox = QCheckBox("أؤكد استلام المبلغ بالكامل كما هو مذكور أعلاه")
        layout.addWidget(self.confirm_checkbox)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(lambda: self.finalize_receipt(transaction_data, confirm_dialog))
        button_box.rejected.connect(confirm_dialog.reject)
        layout.addWidget(button_box)
        
        confirm_dialog.setLayout(layout)
        confirm_dialog.exec()
        
        
    def finalize_receipt(self, transaction_data, dialog):
        """Finalize the receipt confirmation and print it."""
        if not self.confirm_checkbox.isChecked():
            QMessageBox.warning(self, "تحذير", "يجب تأكيد استلام المبلغ قبل المتابعة")
            return
        
        # Validate required fields
        required_fields = {
            "اسم المستلم": self.receiver_name_input.text(),
            "رقم الهاتف": self.receiver_mobile_input.text(),
            "رقم الهوية": self.receiver_id_input.text(),
            "العنوان": self.receiver_address_input.text()
        }
        
        missing_fields = [name for name, value in required_fields.items() if not value]
        if missing_fields:
            QMessageBox.warning(
                self, 
                "بيانات ناقصة",
                f"الرجاء إدخال جميع الحقول المطلوبة:\n{', '.join(missing_fields)}"
            )
            return
        
        # Prepare data
        data = {
            "transaction_id": transaction_data["id"],
            "receiver": self.receiver_name_input.text(),
            "receiver_mobile": self.receiver_mobile_input.text(),
            "receiver_id": self.receiver_id_input.text(),
            "receiver_address": self.receiver_address_input.text(),
            "receiver_governorate": self.receiver_governorate_input.currentText()
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.post(
                f"{self.api_url}/mark-transaction-received/",
                json=data,
                headers=headers
            )
            
            # Handle successful response
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تأكيد استلام التحويل بنجاح")
                dialog.accept()
                
                # Update and print receipt
                transaction_data.update(data)
                transaction_data.update({
                    "received_by": self.full_name,
                    "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "completed"
                })
                self.print_receipt(transaction_data)
                self.load_received_transactions()
            
            # Handle error responses
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "خطأ غير معروف")
                except:
                    error_msg = response.text
                    
                QMessageBox.critical(
                    self,
                    "خطأ في الخادم",
                    f"فشل تأكيد الاستلام:\nكود الخطأ: {response.status_code}\nالرسالة: {error_msg}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ في الاتصال",
                f"تعذر الاتصال بالخادم:\n{str(e)}"
            )
    
    def show_received_context_menu(self, position):
        """Show context menu for received transactions table."""
        if not self.received_table.selectedItems():
            return
        
        row = self.received_table.selectedItems()[0].row()
        transaction_id = self.received_table.item(row, 0).text()
        current_status = self.received_table.item(row, 7).text()
        is_received = self.received_table.item(row, 12).text() == "نعم"
        
        # Create context menu
        context_menu = QMenu(self)
        
        # View details action
        view_action = QAction("عرض التفاصيل", self)
        view_action.triggered.connect(lambda: self.show_transaction_details(self.received_table.item(row, 0)))
        context_menu.addAction(view_action)
        
        # Print action
        print_action = QAction("طباعة إيصال", self)
        print_action.triggered.connect(lambda: self.print_received_transaction(self.received_table.item(row, 0)))
        context_menu.addAction(print_action)
        
        # Mark as received action (if not already received)
        if not is_received:
            receive_action = QAction("تأكيد الاستلام", self)
            receive_action.triggered.connect(lambda: self.mark_as_received())
            context_menu.addAction(receive_action)
        
        # Change status action (only for managers and directors)
        if self.user_role in ["branch_manager", "director"]:
            change_status_menu = QMenu("تغيير الحالة", self)
            
            # Add status options
            statuses = [
                ("قيد الانتظار", "pending"),
                ("قيد المعالجة", "processing"),
                ("مكتمل", "completed"),
                ("ملغي", "cancelled"),
                ("مرفوض", "rejected"),
                ("معلق", "on_hold")
            ]
            
            for status_arabic, status_code in statuses:
                if status_arabic != current_status:  # Don't show current status
                    status_action = QAction(status_arabic, self)
                    status_action.triggered.connect(
                        lambda checked, tid=transaction_id, status=status_code: 
                        self.update_transaction_status(tid, status)
                    )
                    change_status_menu.addAction(status_action)
            
            context_menu.addMenu(change_status_menu)
        
        # Show the context menu
        context_menu.exec(self.received_table.mapToGlobal(position))
    
    def search_received_transactions(self):
        """Open search dialog for received transactions."""
        search_dialog = UserSearchDialog(self.user_token, self, received=True)
        search_dialog.exec()    
        
    def update_current_balance(self):
        """Hidden balance check for validation only"""
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                branch_data = response.json()
                return branch_data.get("financial_stats", {}).get("available_balance", 0)
            return 0  # Default to 0 if request fails
            
        except Exception as e:
            return 0  # Default to 0 if connection fails 
    
    def setup_transactions_tab(self):
        """Set up the transactions tab."""
        layout = QVBoxLayout()
                
        # Search and filter controls
        controls_layout = QHBoxLayout()
        
        # Updated title
        title = QLabel("التحويلات الصادرة")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Search button
        search_button = ModernButton("بحث", color="#3498db")
        search_button.clicked.connect(self.open_search_dialog)
        controls_layout.addWidget(search_button)
        
        # Refresh button
        refresh_button = ModernButton("تحديث", color="#2ecc71")
        refresh_button.clicked.connect(self.load_transactions)
        controls_layout.addWidget(refresh_button)
        
        # Update status button
        update_button = ModernButton("تحديث حالة التحويل", color="#3498db")
        update_button.clicked.connect(self.update_transaction_status)
        controls_layout.addWidget(update_button)
        
        # Filter by status
        status_label = QLabel("تصفية حسب الحالة:")
        controls_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("الكل", "all")
        self.status_filter.addItem("قيد الانتظار", "pending")
        self.status_filter.addItem("قيد المعالجة", "processing")
        self.status_filter.addItem("مكتمل", "completed")
        self.status_filter.addItem("ملغي", "cancelled")
        self.status_filter.addItem("مرفوض", "rejected")
        self.status_filter.addItem("معلق", "on_hold")
        self.status_filter.currentIndexChanged.connect(self.filter_transactions)
        self.status_filter.currentIndexChanged.connect(
            lambda: self.on_filter_change('outgoing')
        )
        controls_layout.addWidget(self.status_filter)
        
        layout.addLayout(controls_layout)
        
        # Create and set up the table model
        self.transaction_model = TransactionTableModel()
        
        # Create QTableView instead of QTableWidget
        self.transactions_table = QTableView()
        self.transactions_table.setModel(self.transaction_model)
        
        # Configure the table view
        self.transactions_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.transactions_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSortingEnabled(True)
        
        # Set up the horizontal header
        header = self.transactions_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Style the table
        self.transactions_table.setStyleSheet("""
            QTableView {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableView::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableView::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Connect signals
        self.transactions_table.doubleClicked.connect(self.on_table_double_clicked)
        self.transactions_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.transactions_table)
        
        # Status bar
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("جاهز")
        status_layout.addWidget(self.status_label)
        
        self.count_label = QLabel("عدد التحويلات: 0")
        status_layout.addWidget(self.count_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(status_layout)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.prev_button_outgoing = ModernButton("السابق", color="#3498db")
        self.prev_button_outgoing.clicked.connect(self.prev_page_outgoing)
        pagination_layout.addWidget(self.prev_button_outgoing)
        
        self.page_label_outgoing = QLabel("الصفحة: 1")
        pagination_layout.addWidget(self.page_label_outgoing)
        
        self.next_button_outgoing = ModernButton("التالي", color="#3498db")
        self.next_button_outgoing.clicked.connect(self.next_page_outgoing)
        pagination_layout.addWidget(self.next_button_outgoing)
        
        layout.addLayout(pagination_layout)
        
        self.transactions_tab.setLayout(layout)
    
    def on_table_double_clicked(self, index):
        """Handle double click on table row"""
        row = index.row()
        transaction = self.transaction_model.get_transaction(row)
        if transaction:
            self.print_transaction(transaction["id"])
    
    def setup_notifications_tab(self):
        """Set up the notifications tab."""
        layout = QVBoxLayout()
        
        # Refresh button
        refresh_button = ModernButton("تحديث الإشعارات", color="#2ecc71")
        refresh_button.clicked.connect(self.load_notifications)
        layout.addWidget(refresh_button)
        
        # Notifications table
        self.notifications_table = QTableWidget()
        self.notifications_table.setColumnCount(5)
        self.notifications_table.setHorizontalHeaderLabels([
            "رقم العملية", "رقم هاتف المستلم", "الرسالة", "الحالة", "تاريخ الإنشاء"
        ])
        self.notifications_table.horizontalHeader().setStretchLastSection(True)
        self.notifications_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.notifications_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        layout.addWidget(self.notifications_table)
        
        self.notifications_tab.setLayout(layout)
    
    def load_branches(self):
        """Load branches from the API and configure destination branch filtering."""
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            
            if response.status_code == 200:
                branches_data = response.json()
                self.branches = branches_data.get("branches", [])
                
                # Create branch ID to name mapping
                self.branch_id_to_name = {branch['id']: branch['name'] for branch in self.branches}
                
                # Initialize destination_branches for all users (including System Manager)
                # For System Manager (branch_id=0), all branches are potential destinations
                if self.branch_id == 0 or self.full_name == "System Manager":
                    # System Manager can send to any branch
                    self.destination_branches = self.branches
                    
                    # Set System Manager branch info
                    self.current_branch_label.setText("الفرع الرئيسي")
                    self.sender_governorate_label.setText("مدير النظام")
                    
                    # Make sure the sender_governorate_input is visible and enabled
                    if hasattr(self, 'sender_governorate_input'):
                        self.sender_governorate_input.setVisible(True)
                        self.sender_governorate_input.setEnabled(True)
                else:
                    # Find current branch for regular users
                    current_branch = next((b for b in self.branches if b.get('id') == self.branch_id), None)
                    
                    if current_branch:
                        # Set current branch info
                        self.current_branch_label.setText(
                            f"{current_branch.get('name', '')} - {current_branch.get('governorate', '')}"
                        )
                        self.sender_governorate_label.setText(current_branch.get('governorate', ''))
                        
                        # Store destination branches (all except current)
                        self.destination_branches = [
                            b for b in self.branches 
                            if b.get('id') != self.branch_id
                        ]
                    else:
                        QMessageBox.warning(self, "Error", "Current branch not found")
                        # Initialize empty destination branches to prevent attribute error
                        self.destination_branches = []
                
                # Update branches based on initial governorate selection
                selected_gov = self.receiver_governorate_input.currentText()
                self.update_destination_branches(selected_gov)
            else:
                QMessageBox.warning(self, "Error", "Failed to load branches")
                # Initialize empty destination branches to prevent attribute error
                self.destination_branches = []
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", 
                f"Failed to connect to server: {str(e)}")
            # Initialize empty destination branches to prevent attribute error
            self.destination_branches = []
            
    def update_destination_branches(self, selected_governorate):
        """Update available branches based on selected governorate."""
        self.branch_input.clear()
        
        # Special handling for System Manager
        if self.branch_id == 0 or self.full_name == "System Manager":
            # For System Manager, filter branches by selected governorate
            valid_branches = [
                b for b in self.destination_branches 
                if b.get('governorate') == selected_governorate
            ]
        else:
            # For regular users, filter branches by selected governorate (excluding current branch)
            valid_branches = [
                b for b in self.destination_branches 
                if b.get('governorate') == selected_governorate
            ]
        
        if not valid_branches:
            self.branch_input.addItem("لا يوجد فروع في هذه المحافظة", -1)
            self.branch_input.setEnabled(False)
        else:
            for branch in valid_branches:
                display_text = f"{branch.get('name', '')} - {branch.get('governorate', '')}"
                self.branch_input.addItem(display_text, branch.get('id'))
            self.branch_input.setEnabled(True)       
    
    def load_transactions(self):
        """Load transactions from the API."""
        try:
            self.status_label.setText("جاري تحميل بيانات التحويلات...")
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            
            url = f"{self.api_url}/transactions/"
            
            # For employees, add employee filter
            if self.user_role == "employee":
                url += f"?branch_id={self.branch_id}&employee_id={self.user_id}"
            else:
                if self.branch_id:
                    url += f"?branch_id={self.branch_id}"

            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = transactions_data.get("transactions", [])
                
                # Store transactions for filtering
                self.all_transactions = transactions
                
                # Update search manager cache
                self.search_manager.update_cache(transactions)
                
                # Reset pagination
                self.current_page_outgoing = 1
                
                # Update the model with the new data
                self.filter_transactions()
                
                # Update status
                self.status_label.setText("تم تحميل بيانات التحويلات الصادرة بنجاح")
                self.count_label.setText(f"عدد التحويلات: {len(transactions)}")
            else:
                self.status_label.setText(f"خطأ في تحميل بيانات التحويلات: {response.status_code}")
                QMessageBox.warning(self, "خطأ", f"فشل تحميل بيانات التحويلات: {response.text}")
        except Exception as e:
            self.status_label.setText("خطأ في الاتصال")
            print(f"Error loading transactions: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                            "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
            
    def filter_transactions(self):
        """Filter transactions based on selected status."""
        if not hasattr(self, 'all_transactions'):
            return
        
        # Get current filters
        filters = {
            'status': self.status_filter.currentData()
        }
        
        # Apply filters using search manager
        filtered_transactions = self.search_manager.filter_transactions(self.all_transactions, filters)
        
        # Pagination calculations
        self.total_pages_outgoing = max(1, (len(filtered_transactions) + self.per_page_outgoing - 1) // self.per_page_outgoing)
        start_idx = (self.current_page_outgoing - 1) * self.per_page_outgoing
        end_idx = start_idx + self.per_page_outgoing
        paginated_transactions = filtered_transactions[start_idx:end_idx]
        
        # Update the model with filtered and paginated data
        self.transaction_model.update_data(paginated_transactions)
        
        # Update count label and pagination controls
        self.count_label.setText(
            f"عدد التحويلات: {len(filtered_transactions)} "
            f"(الصفحة {self.current_page_outgoing}/{self.total_pages_outgoing})"
        )
        self.update_pagination_controls_outgoing()

    def refresh_data(self):
        """Refresh all data in the application."""
        self.load_transactions()
        self.status_label.setText("تم تحديث البيانات في: " + datetime.now().strftime("%H:%M:%S"))
        
    def load_notifications(self):
        """Load notifications from the API."""
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            
            response = requests.get(f"{self.api_url}/notifications/", headers=headers)
            
            if response.status_code == 200:
                notifications_data = response.json()
                notifications = notifications_data.get("notifications", [])
                
                self.notifications_table.setRowCount(len(notifications))
                
                for row_idx, notification in enumerate(notifications):
                    # Set transaction ID
                    self.notifications_table.setItem(row_idx, 0, QTableWidgetItem(notification.get("transaction_id", "")))
                    
                    # Set recipient phone
                    self.notifications_table.setItem(row_idx, 1, QTableWidgetItem(notification.get("recipient_phone", "")))
                    
                    # Set message
                    self.notifications_table.setItem(row_idx, 2, QTableWidgetItem(notification.get("message", "")))
                    
                    # Set status with color
                    status = notification.get("status", "pending")
                    status_item = QTableWidgetItem(self.get_notification_status_arabic(status))
                    status_item.setBackground(self.get_notification_status_color(status))
                    self.notifications_table.setItem(row_idx, 3, status_item)
                    
                    # Set created at
                    self.notifications_table.setItem(row_idx, 4, QTableWidgetItem(notification.get("created_at", "")))
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل الإشعارات: {response.text}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الاتصال بالخادم: {str(e)}")
    
    def get_notification_status_arabic(self, status):
        """Convert notification status to Arabic."""
        status_map = {
            "sent": "تم الإرسال",
            "pending": "قيد الانتظار",
            "failed": "فشل"
        }
        return status_map.get(status, status)
    
    def get_notification_status_color(self, status):
        """Get color for notification status."""
        status_colors = {
            "sent": QColor(200, 255, 200),  # Light green
            "pending": QColor(255, 255, 200),  # Light yellow
            "failed": QColor(255, 200, 200)  # Light red
        }
        return status_colors.get(status, QColor(255, 255, 255))  # White default
    
    def show_transaction_details(self, item):
        """Show transaction details when an item is double-clicked."""
        row = item.row()
        transaction_id = self.transactions_table.item(row, 0).text()
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.get(f"{self.api_url}/transactions/{transaction_id}", headers=headers)
            
            if response.status_code == 200:
                transaction = response.json()
                
                # Create and show details dialog
                details_dialog = TransactionDetailsDialog(transaction, self)
                details_dialog.exec()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل تفاصيل التحويل: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error loading transaction details: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def show_context_menu(self, position):
        """Show context menu for transactions table."""
        # Only show context menu if a row is selected
        if not self.transactions_table.selectedItems():
            return
        
        row = self.transactions_table.selectedItems()[0].row()
        transaction_id = self.transactions_table.item(row, 0).text()
        current_status = self.transactions_table.item(row, 7).text()
        
        # Create context menu
        context_menu = QMenu(self)
        
        # View details action
        view_action = QAction("عرض التفاصيل", self)
        view_action.triggered.connect(lambda: self.show_transaction_details(self.transactions_table.item(row, 0)))
        context_menu.addAction(view_action)
        
        # Change status action (only for managers and directors)
        if self.user_role in ["branch_manager", "director"]:
            change_status_menu = QMenu("تغيير الحالة", self)
            
            # Add status options
            statuses = [
                ("قيد الانتظار", "pending"),
                ("قيد المعالجة", "processing"),
                ("مكتمل", "completed"),
                ("ملغي", "cancelled"),
                ("مرفوض", "rejected"),
                ("معلق", "on_hold")
            ]
            
            for status_arabic, status_code in statuses:
                if status_arabic != current_status:  # Don't show current status
                    status_action = QAction(status_arabic, self)
                    status_action.triggered.connect(
                        lambda checked, tid=transaction_id, status=status_code: 
                        self.update_transaction_status(tid, status)
                    )
                    change_status_menu.addAction(status_action)
            
            context_menu.addMenu(change_status_menu)
        
        # Print action
        print_action = QAction("طباعة", self)
        print_action.triggered.connect(lambda: self.print_transaction(transaction_id))
        context_menu.addAction(print_action)
        
        # Show the context menu
        context_menu.exec(self.transactions_table.mapToGlobal(position))
    
    def update_transaction_status(self, transaction_id=None, new_status=None):
        """Update the status of a transaction."""
        # If called from context menu, both parameters will be provided
        if transaction_id and new_status:
            self._perform_status_update(transaction_id, new_status)
            return
        
        # Otherwise, show dialog to select transaction and status
        selected_indexes = self.transactions_table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "تحذير", "الرجاء تحديد تحويل لتحديث حالته")
            return
        row = selected_indexes[0].row()
        transaction_id = self.transactions_table.model().index(row, 0).data()
        
        # Create a dialog to select new status
        status_dialog = QDialog(self)
        status_dialog.setWindowTitle("تغيير حالة التحويل")
        layout = QVBoxLayout()
        
        status_label = QLabel("اختر الحالة الجديدة:")
        layout.addWidget(status_label)
        
        status_combo = QComboBox()
        statuses = [
            ("قيد الانتظار", "pending"),
            ("قيد المعالجة", "processing"),
            ("مكتمل", "completed"),
            ("ملغي", "cancelled"),
            ("مرفوض", "rejected"),
            ("معلق", "on_hold")
        ]
        
        # Add items correctly with display text and data
        for text, data in statuses:
            status_combo.addItem(text, data)
        
        layout.addWidget(status_combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(status_dialog.accept)
        button_box.rejected.connect(status_dialog.reject)
        layout.addWidget(button_box)
        
        status_dialog.setLayout(layout)
        
        if status_dialog.exec() == QDialog.DialogCode.Accepted:
            new_status = status_combo.currentData()
            self._perform_status_update(transaction_id, new_status)

    def _perform_status_update(self, transaction_id, new_status):
        """Internal method to perform the status update."""
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            data = {
                "transaction_id": transaction_id,
                "status": new_status
            }
            response = requests.post(f"{self.api_url}/update-transaction-status/", json=data, headers=headers)
            
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث حالة التحويل بنجاح")
                # Refresh both transactions and notifications
                self.load_transactions()
                self.load_notifications()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحديث حالة التحويل: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error updating transaction status: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                            "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def open_search_dialog(self):
        """Open the search dialog with optimized search functionality."""
        search_dialog = UserSearchDialog(token=self.user_token, parent=self)
        
        # Connect to search manager for efficient searching
        def perform_search(search_term):
            if not hasattr(self, 'all_transactions'):
                return []
            return self.search_manager.search_transactions(self.all_transactions, search_term)
            
        search_dialog.search_performed.connect(perform_search)
        search_dialog.exec()

    def print_transaction(self, item):
        """Print outgoing transaction receipt (يدعم QTableView مع النموذج)."""
        try:
            # إذا كان item عبارة عن dict (من النموذج)
            if isinstance(item, dict):
                transaction_data = item
            # إذا كان item عبارة عن transaction_id (str)
            elif isinstance(item, str):
                model = getattr(self, 'transaction_model', None)
                if model:
                    for row in range(model.rowCount()):
                        tx = model.get_transaction(row)
                        if tx and tx.get('id') == item:
                            transaction_data = tx
                            break
                    else:
                        QMessageBox.warning(self, "خطأ", "لم يتم العثور على بيانات التحويل")
                        return
                else:
                    QMessageBox.warning(self, "خطأ", "لا يوجد نموذج بيانات")
                    return
            else:
                # إذا كان item QTableWidgetItem (قديم)
                row = item.row()
                amount_str = self.transactions_table.item(row, 4).text().replace(',', '')
                transaction_data = {
                    'id': self.transactions_table.item(row, 0).text(),
                    'date': self.transactions_table.item(row, 1).text(),
                    'sender': self.transactions_table.item(row, 2).text(),
                    'receiver': self.transactions_table.item(row, 3).text(),
                    'amount': float(amount_str),
                    'currency': self.transactions_table.item(row, 5).text(),
                    'receiver_governorate': self.transactions_table.item(row, 6).text(),
                    'status': self.transactions_table.item(row, 7).text(),
                    'employee_name': self.transactions_table.item(row, 8).text(),
                    'sending_branch_name': self.transactions_table.item(row, 9).text(),
                    'destination_branch_name': self.transactions_table.item(row, 10).text(),
                    'branch_governorate': self.transactions_table.item(row, 11).text(),
                    'type': 'sent'
                }
            self.print_receipt(transaction_data)
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"حدث خطأ أثناء تحضير البيانات للطباعة: {str(e)}")

    def refresh_branches(self):
        """Refresh branch data and update relevant UI elements."""
        try:
            # Load updated branch data
            self.load_branches()
            
            # Update destination branches based on current governorate selection
            if hasattr(self, 'receiver_governorate_input'):
                selected_gov = self.receiver_governorate_input.currentText()
                self.update_destination_branches(selected_gov)
                
        except Exception as e:
            print(f"Error refreshing branches: {str(e)}")

    def show_search_dialog(self):
        """Show search dialog for transactions."""
        self.open_search_dialog()

    def show_filter_dialog(self):
        """Show filter dialog for transactions."""
        # Create a dialog for advanced filtering
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
        
        # Apply filters using search manager
        filtered_transactions = self.search_manager.filter_transactions(self.all_transactions, filters)
        
        # Update the model with filtered data
        self.transaction_model.update_data(filtered_transactions)
        
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
        info_layout.addRow("الدور:", QLabel(self.user_role))
        info_layout.addRow("الفرع:", QLabel(self.current_branch_label.text()))
        
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
        """Show change password dialog."""
        from ui.change_password import ChangePasswordDialog
        dialog = ChangePasswordDialog(self)
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
            <h2>دليل استخدام نظام تحويل الأموال</h2>
            <h3>التحويلات الجديدة</h3>
            <p>لإنشاء تحويل جديد:</p>
            <ol>
                <li>أدخل معلومات المرسل</li>
                <li>أدخل معلومات المستلم</li>
                <li>أدخل مبلغ التحويل</li>
                <li>انقر على زر "إرسال التحويل"</li>
            </ol>
            
            <h3>التحويلات الصادرة</h3>
            <p>لعرض وتتبع التحويلات الصادرة:</p>
            <ul>
                <li>استخدم خيارات التصفية للبحث عن تحويلات محددة</li>
                <li>انقر نقراً مزدوجاً على أي تحويل لعرض تفاصيله</li>
                <li>استخدم خيارات الطباعة لطباعة تفاصيل التحويل</li>
            </ul>
            
            <h3>التحويلات الواردة</h3>
            <p>لإدارة التحويلات الواردة:</p>
            <ul>
                <li>استخدم خيارات التصفية للبحث عن تحويلات محددة</li>
                <li>انقر على زر "تأكيد الاستلام" لتأكيد استلام التحويل</li>
                <li>استخدم خيارات الطباعة لطباعة إيصال الاستلام</li>
            </ul>
            
            <h3>اختصارات لوحة المفاتيح</h3>
            <ul>
                <li>Ctrl+N: تحويل جديد</li>
                <li>Ctrl+F: بحث</li>
                <li>Ctrl+P: طباعة</li>
                <li>Ctrl+R: تحديث</li>
                <li>F1: عرض المساعدة</li>
            </ul>
        """)
        layout.addWidget(help_text)
        
        # Close button
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        
        help_dialog.setLayout(layout)
        help_dialog.exec()

    def show_confirmation(self):
        """Show confirmation dialog before submitting transfer."""
        if not self.validate_transfer_form():
            return
            
        data = self.prepare_transfer_data()
        sending_branch_name = self.branch_id_to_name.get(self.branch_id, "غير معروف")
        destination_branch_id = data.get("destination_branch_id")
        destination_branch_name = self.branch_id_to_name.get(destination_branch_id, "غير معروف")
        
        msg = (
            f"تأكيد تفاصيل التحويل:\n\n"
            f"المرسل: {data['sender']} ({data['sender_mobile']})\n"
            f"المستلم: {data['receiver']} ({data['receiver_mobile']})\n"
            f"المبلغ: {data['amount']:,.2f} {data['currency']}\n"
            f"الضريبة: {data['tax_amount']:,.2f} {data['currency']} ({data['tax_rate']}%)\n"
            f"الصافي: {data['net_amount']:,.2f} {data['currency']}\n"
            f"من: {sending_branch_name}\n"
            f"إلى: {destination_branch_name}\n\n"
            f"هل تريد المتابعة؟"
        )
        
        reply = QMessageBox.question(
            self, "تأكيد التحويل", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.submit_transfer(data)
            
    def submit_transfer(self, data):
        """Submit the transfer using a worker thread."""
        # Show loading overlay
        self.loading_overlay.set_status("جاري إرسال التحويل...")
        self.loading_overlay.show()
        
        # Create and start worker
        self.transfer_worker = TransferWorker(
            self.api_url,
            data,
            {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
        )
        
        # Connect signals
        self.transfer_worker.finished.connect(self.handle_transfer_success)
        self.transfer_worker.error.connect(self.handle_transfer_error)
        self.transfer_worker.progress.connect(self.loading_overlay.set_status)
        
        # Start worker
        self.transfer_worker.start()
        
    def handle_transfer_success(self, response_data):
        """Handle successful transfer submission."""
        self.loading_overlay.hide()
        QMessageBox.information(self, "نجاح", "تم إرسال التحويل بنجاح")
        self.clear_form()
        self.load_transactions()
        self.load_notifications()
        self.transferCompleted.emit()
        
    def handle_transfer_error(self, error_msg):
        """Handle transfer submission error."""
        self.loading_overlay.hide()
        QMessageBox.critical(self, "خطأ", error_msg)
        
    def resizeEvent(self, event):
        """Handle window resize to update loading overlay size."""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MoneyTransferApp()
    window.show()
    sys.exit(app.exec())
