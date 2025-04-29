from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QComboBox,
    QTableWidget, QTableWidgetItem, QGroupBox, QRadioButton, QButtonGroup, QMessageBox,
    QHeaderView, QTabWidget, QWidget, QFormLayout, QDialogButtonBox, QTextEdit, QApplication
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
import requests
from ui.custom_widgets import ModernGroupBox, ModernButton
from datetime import datetime
import os
from money_transfer.receipt_printer import ReceiptPrinter

class UserSearchDialog(QDialog):
    """Dialog for searching and viewing user and transaction information."""
    
    def __init__(self, token=None,  parent=None, received=False):
        super().__init__(parent)
        self.token = token
        self.api_url = os.environ["API_URL"]
        self.received = received
        
        self.setWindowTitle("بحث المستخدمين والتحويلات")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
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
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("بحث المستخدمين والتحويلات")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.users_tab = QWidget()
        self.transfers_tab = QWidget()
        
        # Set up tabs
        self.setup_users_tab()
        self.setup_transfers_tab()
        
        # Add tabs to widget
        self.tabs.addTab(self.users_tab, "المستخدمين")
        self.tabs.addTab(self.transfers_tab, "التحويلات")
        
        # Set active tab based on received parameter
        if received:
            self.tabs.setCurrentIndex(1)  # Transfers tab
        
        main_layout.addWidget(self.tabs)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.close_button = ModernButton("إغلاق", color="#e74c3c")
        self.close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_button)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
    
    def _get_status_arabic(self, status):
        """Convert status code to Arabic display text with consistent translation."""
        status_map = {
            "pending": "قيد الانتظار",
            "completed": "تم الاستلام",
            "cancelled": "ملغي",
            "processing": "قيد المعالجة",
            "rejected": "مرفوض",
            "on_hold": "معلق"
        }
        return status_map.get(status, status)
    
    def setup_users_tab(self):
        """Set up the users tab with search functionality."""
        layout = QVBoxLayout()
        
        # Search group
        search_group = ModernGroupBox("بحث العملاء (مرسلين/مستلمين)", "#3498db")
        search_layout = QVBoxLayout()
        
        # Search criteria
        criteria_layout = QHBoxLayout()
        
        # Radio buttons for search type
        self.user_search_type_group = QButtonGroup(self)
        
        # Name search
        self.name_radio = QRadioButton("بحث بالاسم")
        self.name_radio.setChecked(True)  # Default selection
        self.user_search_type_group.addButton(self.name_radio)
        criteria_layout.addWidget(self.name_radio)
        
        # Mobile search
        self.mobile_radio = QRadioButton("بحث برقم الهاتف")
        self.user_search_type_group.addButton(self.mobile_radio)
        criteria_layout.addWidget(self.mobile_radio)
        
        # ID search
        self.id_radio = QRadioButton("بحث برقم الهوية")
        self.user_search_type_group.addButton(self.id_radio)
        criteria_layout.addWidget(self.id_radio)
        
        # Governorate search
        self.governorate_radio = QRadioButton("بحث بالمحافظة")
        self.user_search_type_group.addButton(self.governorate_radio)
        criteria_layout.addWidget(self.governorate_radio)
        
        # User type search
        self.user_type_radio = QRadioButton("بحث بنوع المستخدم")
        self.user_search_type_group.addButton(self.user_type_radio)
        criteria_layout.addWidget(self.user_type_radio)
        
        search_layout.addLayout(criteria_layout)
        
        # User type selection (visible when user_type_radio is selected)
        self.user_type_layout = QHBoxLayout()
        
        user_type_label = QLabel("نوع المستخدم:")
        self.user_type_layout.addWidget(user_type_label)
        
        self.user_type_combo = QComboBox()
        self.user_type_combo.addItem("المرسل", "sender")
        self.user_type_combo.addItem("المستلم", "receiver")
        self.user_type_layout.addWidget(self.user_type_combo)
        
        search_layout.addLayout(self.user_type_layout)
        
        # Search input
        search_input_layout = QHBoxLayout()
        
        search_label = QLabel("كلمة البحث:")
        search_input_layout.addWidget(search_label)
        
        self.user_search_input = QLineEdit()
        self.user_search_input.setPlaceholderText("أدخل كلمة البحث...")
        search_input_layout.addWidget(self.user_search_input)
        
        self.user_search_button = ModernButton("بحث", color="#3498db")
        self.user_search_button.clicked.connect(self.search_users)
        search_input_layout.addWidget(self.user_search_button)
        
        search_layout.addLayout(search_input_layout)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Results group
        results_group = ModernGroupBox("نتائج البحث", "#2ecc71")
        results_layout = QVBoxLayout()
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(["الاسم", "رقم الهاتف", "المحافظة", "الموقع", "رقم الهوية", "النوع"])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        results_layout.addWidget(self.users_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # User info group
        user_info_group = ModernGroupBox("معلومات المستخدم", "#3498db")
        user_info_layout = QVBoxLayout()
        
        # User info will be displayed here when a user is selected
        self.user_info_label = QLabel("اختر مستخدمًا من نتائج البحث لعرض معلوماته")
        self.user_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_info_layout.addWidget(self.user_info_label)
        
        user_info_group.setLayout(user_info_layout)
        layout.addWidget(user_info_group)
        
        # Connect selection change
        self.users_table.itemSelectionChanged.connect(self.on_user_selection_changed)
        
        # Connect radio button changes
        self.user_type_radio.toggled.connect(self.toggle_user_type_visibility)
        
        # Initially hide user type selection
        self.toggle_user_type_visibility()
        
        self.user_search_input.returnPressed.connect(self.search_users)  # Trigger search on Enter
        
        self.users_tab.setLayout(layout)
    
    def setup_transfers_tab(self):
        """Set up the transfers tab with search functionality."""
        layout = QVBoxLayout()
        
        # Search group
        search_group = ModernGroupBox("بحث التحويلات", "#e74c3c")
        search_layout = QVBoxLayout()
        
        # Search criteria
        criteria_layout = QHBoxLayout()
        
        # Radio buttons for search type
        self.transfer_search_type_group = QButtonGroup(self)
        
        # Transaction ID search
        self.transaction_id_radio = QRadioButton("بحث برقم التحويل")
        self.transaction_id_radio.setChecked(True)  # Default selection
        self.transfer_search_type_group.addButton(self.transaction_id_radio)
        criteria_layout.addWidget(self.transaction_id_radio)
        
        # Sender name search
        self.sender_name_radio = QRadioButton("بحث باسم المرسل")
        self.transfer_search_type_group.addButton(self.sender_name_radio)
        criteria_layout.addWidget(self.sender_name_radio)
        
        # Receiver name search
        self.receiver_name_radio = QRadioButton("بحث باسم المستلم")
        self.transfer_search_type_group.addButton(self.receiver_name_radio)
        criteria_layout.addWidget(self.receiver_name_radio)
        
        # Status search
        self.status_radio = QRadioButton("بحث بالحالة")
        self.transfer_search_type_group.addButton(self.status_radio)
        criteria_layout.addWidget(self.status_radio)
        
        # Date search
        self.date_radio = QRadioButton("بحث بالتاريخ")
        self.transfer_search_type_group.addButton(self.date_radio)
        criteria_layout.addWidget(self.date_radio)
        
        search_layout.addLayout(criteria_layout)
        
        # Status selection (visible when status_radio is selected)
        self.status_layout = QHBoxLayout()
        
        status_label = QLabel("الحالة:")
        self.status_layout.addWidget(status_label)
        
        self.status_combo = QComboBox()
        self.status_combo.addItem("قيد الانتظار", "pending")
        self.status_combo.addItem("قيد المعالجة", "processing")
        self.status_combo.addItem("مكتمل", "completed")
        self.status_combo.addItem("ملغي", "cancelled")
        self.status_combo.addItem("مرفوض", "rejected")
        self.status_combo.addItem("معلق", "on_hold")
        self.status_layout.addWidget(self.status_combo)
        
        search_layout.addLayout(self.status_layout)
        
        # Search input
        search_input_layout = QHBoxLayout()
        
        search_label = QLabel("كلمة البحث:")
        search_input_layout.addWidget(search_label)
        
        self.transfer_search_input = QLineEdit()
        self.transfer_search_input.setPlaceholderText("أدخل كلمة البحث...")
        search_input_layout.addWidget(self.transfer_search_input)
        
        self.transfer_search_button = ModernButton("بحث", color="#e74c3c")
        self.transfer_search_button.clicked.connect(self.search_transfers)
        search_input_layout.addWidget(self.transfer_search_button)
        
        search_layout.addLayout(search_input_layout)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Results group
        results_group = ModernGroupBox("نتائج البحث", "#f39c12")
        results_layout = QVBoxLayout()
        
        self.transfers_table = QTableWidget()
        self.transfers_table.setColumnCount(8)
        self.transfers_table.setHorizontalHeaderLabels([
            "رقم التحويل", "المرسل", "المستلم", "المبلغ", "العملة", "الفرع المستلم", "الحالة", "التاريخ"
        ])
        self.transfers_table.horizontalHeader().setStretchLastSection(True)
        self.transfers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transfers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        results_layout.addWidget(self.transfers_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.view_details_button = ModernButton("عرض التفاصيل", color="#2ecc71")
        self.view_details_button.clicked.connect(self.view_transfer_details)
        self.view_details_button.setEnabled(False)  # Disabled until a transfer is selected
        action_layout.addWidget(self.view_details_button)
        
        self.print_button = ModernButton("طباعة التحويل", color="#3498db")
        self.print_button.clicked.connect(self.print_transfer)
        self.print_button.setEnabled(False)  # Disabled until a transfer is selected
        action_layout.addWidget(self.print_button)
        
        self.add_receiver_button = ModernButton("إضافة معلومات المستلم", color="#9b59b6")
        self.add_receiver_button.clicked.connect(self.add_receiver_info)
        self.add_receiver_button.setEnabled(False)  # Disabled until a transfer is selected
        action_layout.addWidget(self.add_receiver_button)
        
        layout.addLayout(action_layout)
        
        # Connect selection change
        self.transfers_table.itemSelectionChanged.connect(self.on_transfer_selection_changed)
        
        # Connect radio button changes
        self.status_radio.toggled.connect(self.toggle_status_visibility)
        
        # Initially hide status selection
        self.toggle_status_visibility()
        
        self.transfers_tab.setLayout(layout)
    
    def toggle_user_type_visibility(self):
        """Toggle visibility of user type selection based on radio button state."""
        is_visible = self.user_type_radio.isChecked()
        for i in range(self.user_type_layout.count()):
            item = self.user_type_layout.itemAt(i).widget()
            if item:
                item.setVisible(is_visible)
    
    def toggle_status_visibility(self):
        """Toggle visibility of status selection based on radio button state."""
        is_visible = self.status_radio.isChecked()
        for i in range(self.status_layout.count()):
            item = self.status_layout.itemAt(i).widget()
            if item:
                item.setVisible(is_visible)
    
    def search_users(self):
        """Search for customers (senders/receivers) based on the selected criteria."""
        search_term = self.user_search_input.text().strip()
        if not search_term and not self.user_type_radio.isChecked():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال كلمة البحث")
            return

        # Only send non-empty parameters
        params = {}
        if self.name_radio.isChecked() and search_term:
            params["name"] = search_term
        if self.mobile_radio.isChecked() and search_term:
            params["mobile"] = search_term
        if self.id_radio.isChecked() and search_term:
            params["id_number"] = search_term
        if self.governorate_radio.isChecked() and search_term:
            params["governorate"] = search_term
        if self.user_type_radio.isChecked():
            user_type_value = self.user_type_combo.currentData()
            if user_type_value:
                params["user_type"] = user_type_value

        # Show loading indicator
        self.users_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري البحث...")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.users_table.setItem(0, 0, loading_item)
        for col in range(1, self.users_table.columnCount()):
            self.users_table.setItem(0, col, QTableWidgetItem(""))
        self.user_search_button.setEnabled(False)
        self.user_search_button.setText("جاري البحث...")
        QApplication.processEvents()

        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/customers/", params=params, headers=headers, timeout=10)
            self.users_table.setRowCount(0)
            if response.status_code == 200:
                customers = response.json().get("customers", [])
                if not customers:
                    QMessageBox.information(self, "نتائج البحث", "لم يتم العثور على نتائج مطابقة لمعايير البحث")
                    return
                self.users_table.setRowCount(len(customers))
                for i, cust in enumerate(customers):
                    user_type = cust.get("user_type", "")
                    if user_type == "sender":
                        name = cust.get("sender_name", "غير متوفر") or "غير متوفر"
                        mobile = cust.get("sender_mobile", "غير متوفر") or "غير متوفر"
                        governorate = cust.get("sender_governorate", "غير متوفر") or "غير متوفر"
                        location = cust.get("sender_location", "غير متوفر") or "غير متوفر"
                        id_number = cust.get("sender_id", "غير متوفر") or "غير متوفر"
                    else:
                        name = cust.get("receiver_name", "غير متوفر") or "غير متوفر"
                        mobile = cust.get("receiver_mobile", "غير متوفر") or "غير متوفر"
                        governorate = cust.get("receiver_governorate", "غير متوفر") or "غير متوفر"
                        location = cust.get("receiver_location", "غير متوفر") or "غير متوفر"
                        id_number = cust.get("receiver_id", "غير متوفر") or "غير متوفر"
                    name_item = QTableWidgetItem(name)
                    name_item.setData(Qt.ItemDataRole.UserRole, cust)
                    self.users_table.setItem(i, 0, name_item)
                    self.users_table.setItem(i, 1, QTableWidgetItem(mobile))
                    self.users_table.setItem(i, 2, QTableWidgetItem(governorate))
                    self.users_table.setItem(i, 3, QTableWidgetItem(location))
                    self.users_table.setItem(i, 4, QTableWidgetItem(id_number))
                    user_type_arabic = "مرسل" if user_type == "sender" else "مستلم"
                    type_item = QTableWidgetItem(user_type_arabic)
                    type_item.setBackground(QColor(200, 255, 200) if user_type == "sender" else QColor(255, 200, 200))
                    self.users_table.setItem(i, 5, type_item)
                self.users_table.sortItems(0, Qt.SortOrder.AscendingOrder)
            elif response.status_code == 401:
                QMessageBox.warning(self, "خطأ في المصادقة", "انتهت صلاحية الجلسة. الرجاء تسجيل الدخول مرة أخرى.")
            elif response.status_code == 404:
                QMessageBox.warning(self, "خطأ", "لم يتم العثور على المورد المطلوب")
            else:
                QMessageBox.warning(self, "خطأ", f"فشل البحث: رمز الحالة {response.status_code}")
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "خطأ في الاتصال", "انتهت مهلة الاتصال بالخادم. الرجاء المحاولة مرة أخرى.")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "خطأ في الاتصال", "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت.")
        except Exception as e:
            print(f"Error searching users: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
        finally:
            self.user_search_button.setEnabled(True)
            self.user_search_button.setText("بحث")
    
    def search_transfers(self):
        """Search for transfers based on the selected criteria."""
        search_term = self.transfer_search_input.text().strip()
        if not search_term and not self.status_radio.isChecked():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال كلمة البحث")
            return
        
        # Determine search type
        search_type = "transaction_id"  # Default
        if self.sender_name_radio.isChecked():
            search_type = "sender_name"
        elif self.receiver_name_radio.isChecked():
            search_type = "receiver_name"
        elif self.status_radio.isChecked():
            search_type = "status"
            search_term = self.status_combo.currentData()
        elif self.date_radio.isChecked():
            search_type = "date"
        
        # Only send non-empty parameters
        params = {}
        if search_type == "transaction_id" and search_term:
            params["id"] = search_term
        elif search_type == "sender_name" and search_term:
            params["sender"] = search_term
        elif search_type == "receiver_name" and search_term:
            params["receiver"] = search_term
        elif search_type == "status" and search_term:
            params["status"] = search_term
        elif search_type == "date" and search_term:
            params["date"] = search_term

        # Show loading indicator
        self.transfers_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري البحث...")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transfers_table.setItem(0, 0, loading_item)
        for col in range(1, self.transfers_table.columnCount()):
            self.transfers_table.setItem(0, col, QTableWidgetItem(""))
        
        # Disable search button during search
        self.transfer_search_button.setEnabled(False)
        self.transfer_search_button.setText("جاري البحث...")
        
        # Process events to update UI
        QApplication.processEvents()
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Use the standard /transactions/ endpoint with query parameters instead of custom search endpoint
            response = requests.get(f"{self.api_url}/transactions/", params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = transactions_data.get("transactions", [])
                
                if not transactions:
                    QMessageBox.information(self, "نتائج البحث", "لم يتم العثور على تحويلات مطابقة لمعايير البحث")
                    return
                
                self.transfers_table.setRowCount(len(transactions))
                
                for i, transaction in enumerate(transactions):
                    # Create transaction ID item and store transaction data
                    id_item = QTableWidgetItem(str(transaction.get("id", "")))
                    id_item.setData(Qt.ItemDataRole.UserRole, transaction)
                    self.transfers_table.setItem(i, 0, id_item)
                    
                    # Set other columns
                    self.transfers_table.setItem(i, 1, QTableWidgetItem(transaction.get("sender", "")))
                    self.transfers_table.setItem(i, 2, QTableWidgetItem(transaction.get("receiver", "")))
                    self.transfers_table.setItem(i, 3, QTableWidgetItem(str(transaction.get("amount", ""))))
                    self.transfers_table.setItem(i, 4, QTableWidgetItem(transaction.get("currency", "")))
                    self.transfers_table.setItem(i, 5, QTableWidgetItem(transaction.get("receiver_governorate", "")))
                    
                    # Map status values to Arabic
                    status = transaction.get("status", "")
                    status_arabic = self._get_status_arabic(status)
                    
                    status_item = QTableWidgetItem(status_arabic)
                    
                    # Color-code status
                    if status_arabic == "تم الاستلام":
                        status_item.setBackground(QColor(200, 255, 200))  # Light green
                    elif status_arabic == "ملغي":
                        status_item.setBackground(QColor(255, 200, 200))  # Light red
                    elif status_arabic == "قيد المعالجة":
                        status_item.setBackground(QColor(255, 255, 200))  # Light yellow
                    elif status_arabic == "مرفوض":
                        status_item.setBackground(QColor(255, 150, 150))  # Darker red
                    elif status_arabic == "معلق":
                        status_item.setBackground(QColor(200, 200, 255))  # Light blue
                    
                    self.transfers_table.setItem(i, 6, status_item)
                    self.transfers_table.setItem(i, 7, QTableWidgetItem(transaction.get("date", "")))
                
                # Sort by date (newest first) for better usability
                self.transfers_table.sortItems(7, Qt.SortOrder.DescendingOrder)
            elif response.status_code == 401:
                QMessageBox.warning(self, "خطأ في المصادقة", "انتهت صلاحية الجلسة. الرجاء تسجيل الدخول مرة أخرى.")
            elif response.status_code == 404:
                QMessageBox.warning(self, "خطأ", "لم يتم العثور على المورد المطلوب")
            else:
                QMessageBox.warning(self, "خطأ", f"فشل البحث: رمز الحالة {response.status_code}")
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "خطأ في الاتصال", "انتهت مهلة الاتصال بالخادم. الرجاء المحاولة مرة أخرى.")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "خطأ في الاتصال", "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت.")
        except Exception as e:
            print(f"Error searching transfers: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
        finally:
            # Re-enable search button
            self.transfer_search_button.setEnabled(True)
            self.transfer_search_button.setText("بحث")
    
    def on_user_selection_changed(self):
        """Handle selection change in the users table."""
        selected_rows = self.users_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        if has_selection:
            row = selected_rows[0].row()
            user = self.users_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
            if not user:
                self.user_info_label.setText("لم يتم العثور على بيانات المستخدم")
                return
            user_type = user.get('user_type')
            if user_type == "sender":
                self.user_info_label.setText(
                    f"<b>الاسم:</b> {user.get('sender_name', 'غير متوفر')}<br>"
                    f"<b>رقم الهاتف:</b> {user.get('sender_mobile', 'غير متوفر')}<br>"
                    f"<b>رقم الهوية:</b> {user.get('sender_id', 'غير متوفر')}<br>"
                    f"<b>المحافظة:</b> {user.get('sender_governorate', 'غير متوفر')}<br>"
                    f"<b>الموقع:</b> {user.get('sender_location', 'غير متوفر')}<br>"
                    f"<b>النوع:</b> مرسل<br>"
                )
            else:
                self.user_info_label.setText(
                    f"<b>الاسم:</b> {user.get('receiver_name', 'غير متوفر')}<br>"
                    f"<b>رقم الهاتف:</b> {user.get('receiver_mobile', 'غير متوفر')}<br>"
                    f"<b>رقم الهوية:</b> {user.get('receiver_id', 'غير متوفر')}<br>"
                    f"<b>المحافظة:</b> {user.get('receiver_governorate', 'غير متوفر')}<br>"
                    f"<b>الموقع:</b> {user.get('receiver_location', 'غير متوفر')}<br>"
                    f"<b>النوع:</b> مستلم<br>"
                )
            self.user_info_label.setTextFormat(Qt.TextFormat.RichText)
    
    def on_transfer_selection_changed(self):
        """Handle selection change in the transfers table."""
        selected_rows = self.transfers_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        self.view_details_button.setEnabled(has_selection)
        self.print_button.setEnabled(has_selection)
        
        # Only enable add receiver info button if transfer is pending
        if has_selection:
            row = selected_rows[0].row()
            status_item = self.transfers_table.item(row, 6)
            if not status_item:
                return
                
            status_text = status_item.text()
            
            # Enable add receiver info button only for pending or processing transfers
            self.add_receiver_button.setEnabled(
                status_text in ["قيد الانتظار", "قيد المعالجة"]
            )
    
    def view_transfer_details(self):
        """View detailed information about the selected transfer."""
        selected_rows = self.transfers_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        transaction = self.transfers_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if not transaction:
            QMessageBox.warning(self, "خطأ", "لم يتم العثور على بيانات التحويل")
            return
        
        # Create a dialog to display detailed information
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle("تفاصيل التحويل")
        details_dialog.setGeometry(150, 150, 600, 500)
        details_dialog.setStyleSheet("""
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
        <b>الفرع المرسل:</b> {transaction.get('branch_name', '')}<br>
        <b>الفرع المستلم:</b> {transaction.get('destination_branch_name', '')}<br>
        <b>الموظف:</b> {transaction.get('employee_name', '')}<br>
        <b>الحالة:</b> {self._get_status_arabic(transaction.get('status', ''))}<br>
        <b>تم الاستلام:</b> {'نعم' if transaction.get('is_received', False) else 'لا'}<br>
        """
        
        details_label = QLabel(details_text)
        details_label.setTextFormat(Qt.TextFormat.RichText)
        details_label.setWordWrap(True)
        details_layout.addWidget(details_label)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Close button
        close_button = ModernButton("إغلاق", color="#e74c3c")
        close_button.clicked.connect(details_dialog.accept)
        layout.addWidget(close_button)
        
        details_dialog.setLayout(layout)
        details_dialog.exec()
    
    def print_transfer(self):
        """Print the selected transfer using ReceiptPrinter."""
        selected_rows = self.transfers_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        transaction = self.transfers_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not transaction:
            QMessageBox.warning(self, "خطأ", "لم يتم العثور على بيانات التحويل")
            return
        # Use ReceiptPrinter to print
        printer = ReceiptPrinter(self)
        printer.print_receipt(transaction)
    
    def add_receiver_info(self):
        """Add or update receiver information for the selected transfer."""
        selected_rows = self.transfers_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        transaction = self.transfers_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if not transaction:
            QMessageBox.warning(self, "خطأ", "لم يتم العثور على بيانات التحويل")
            return
            
        # Create dialog for adding receiver info
        receiver_dialog = QDialog(self)
        receiver_dialog.setWindowTitle("إضافة معلومات المستلم")
        receiver_dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Transaction info group
        trans_group = ModernGroupBox("معلومات التحويل", "#3498db")
        trans_layout = QFormLayout()
        
        trans_layout.addRow(QLabel("رقم التحويل:"), QLabel(str(transaction.get("id", ""))))
        trans_layout.addRow(QLabel("التاريخ:"), QLabel(transaction.get("date", "")))
        trans_layout.addRow(QLabel("المبلغ:"), QLabel(f"{transaction.get('amount', '')} {transaction.get('currency', '')}"))
        
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)
        
        # Receiver info group (editable)
        receiver_group = ModernGroupBox("معلومات المستلم", "#2ecc71")
        receiver_layout = QFormLayout()
        
        # Receiver name
        self.receiver_name_input = QLineEdit(transaction.get("receiver", ""))
        receiver_layout.addRow(QLabel("اسم المستلم:"), self.receiver_name_input)
        
        # Receiver mobile
        self.receiver_mobile_input = QLineEdit(transaction.get("receiver_mobile", ""))
        self.receiver_mobile_input.setPlaceholderText("أدخل رقم الهاتف")
        receiver_layout.addRow(QLabel("رقم الهاتف:"), self.receiver_mobile_input)
        
        # Receiver ID
        self.receiver_id_input = QLineEdit(transaction.get("receiver_id", ""))
        self.receiver_id_input.setPlaceholderText("أدخل رقم الهوية")
        receiver_layout.addRow(QLabel("رقم الهوية:"), self.receiver_id_input)
        
        # Receiver address
        self.receiver_address_input = QLineEdit(transaction.get("receiver_address", ""))
        self.receiver_address_input.setPlaceholderText("أدخل العنوان")
        receiver_layout.addRow(QLabel("العنوان:"), self.receiver_address_input)
        
        # Receiver governorate
        self.receiver_governorate_input = QComboBox()
        self.receiver_governorate_input.addItems([
            "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", 
            "إدلب", "دير الزور", "الرقة", "الحسكة", "السويداء", "درعا", "القنيطرة"
        ])
        
        # Set current governorate if it exists in the combo box
        current_gov = transaction.get("receiver_governorate", "")
        index = self.receiver_governorate_input.findText(current_gov)
        if index >= 0:
            self.receiver_governorate_input.setCurrentIndex(index)
        
        receiver_layout.addRow(QLabel("المحافظة:"), self.receiver_governorate_input)
        
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(lambda: self.save_receiver_info(transaction.get("id", ""), receiver_dialog))
        button_box.rejected.connect(receiver_dialog.reject)
        layout.addWidget(button_box)
        
        receiver_dialog.setLayout(layout)
        receiver_dialog.exec()
    
    def save_receiver_info(self, transaction_id, dialog):
        """Save receiver information for the transaction."""
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
        
        # Show loading indicator
        QApplication.processEvents()
        
        try:
            # Prepare data for direct update to transaction
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Get the transaction first
            response = requests.get(f"{self.api_url}/transactions/{transaction_id}", headers=headers, timeout=10)
            if response.status_code != 200:
                QMessageBox.critical(
                    self,
                    "خطأ في الخادم",
                    f"فشل الحصول على معلومات التحويل:\nكود الخطأ: {response.status_code}"
                )
                return
                
            transaction_data = response.json()
            
            # Update receiver information
            transaction_data["receiver"] = self.receiver_name_input.text()
            transaction_data["receiver_mobile"] = self.receiver_mobile_input.text()
            transaction_data["receiver_id"] = self.receiver_id_input.text()
            transaction_data["receiver_address"] = self.receiver_address_input.text()
            transaction_data["receiver_governorate"] = self.receiver_governorate_input.currentText()
            
            # Send update request
            update_response = requests.put(
                f"{self.api_url}/transactions/{transaction_id}",
                json=transaction_data,
                headers=headers,
                timeout=10
            )
            
            # Handle response
            if update_response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث معلومات المستلم بنجاح")
                dialog.accept()
                
                # Refresh the transfers table
                self.search_transfers()
            else:
                try:
                    error_data = update_response.json()
                    error_msg = error_data.get("detail", "خطأ غير معروف")
                except:
                    error_msg = update_response.text
                    
                QMessageBox.critical(
                    self,
                    "خطأ في الخادم",
                    f"فشل تحديث معلومات المستلم:\nكود الخطأ: {update_response.status_code}\nالرسالة: {error_msg}"
                )
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "خطأ في الاتصال", "انتهت مهلة الاتصال بالخادم. الرجاء المحاولة مرة أخرى.")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "خطأ في الاتصال", "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت.")
        except Exception as e:
            print(f"Error saving receiver info: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
