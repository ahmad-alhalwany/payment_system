import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QLineEdit, QFormLayout, QComboBox, QGroupBox,
    QGridLayout, QDateEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QMenu,
    QStatusBar, QSplitter, QFrame
)
from PyQt6.QtGui import QFont, QColor, QAction, QIcon
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer
import os
from ui.user_search import UserSearchDialog

class TransactionHistory(QWidget):
    """Widget for displaying and managing transaction history."""
    
    def __init__(self, user_token=None, branch_id=None, user_id=None, user_role="employee"):
        super().__init__()
        self.user_token = user_token
        self.branch_id = branch_id
        self.user_id = user_id
        self.user_role = user_role
        self.api_url = os.environ["API_URL"]
        
        self.setup_ui()
        self.load_transactions()
        
        # Set up refresh timer (every 2 minutes)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_transactions)
        self.refresh_timer.start(30000)  # 2 minutes in milliseconds
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("سجل التحويلات")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        # Add spacer to push buttons to the right
        header_layout.addStretch()
        
        # Filter button
        self.filter_button = QPushButton("تصفية")
        self.filter_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.filter_button.clicked.connect(self.show_filter_dialog)
        header_layout.addWidget(self.filter_button)
        
        # Refresh button
        self.refresh_button = QPushButton("تحديث")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.refresh_button.clicked.connect(self.load_transactions)
        header_layout.addWidget(self.refresh_button)
        
        # Export button
        self.export_button = QPushButton("تصدير")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.export_button.clicked.connect(self.export_transactions)
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(8)
        self.transactions_table.setHorizontalHeaderLabels([
            "رقم التحويل", "التاريخ", "المرسل", "المستلم", "المبلغ", "الحالة", "الموظف", "الملاحظات"
        ])
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transactions_table.setStyleSheet("""
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
        self.transactions_table.itemDoubleClicked.connect(self.show_transaction_details)
        
        # Connect context menu event
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
        
        self.setLayout(layout)
    
    def load_transactions(self):
        """Load transactions from the API."""
        self.status_label.setText("جاري تحميل البيانات...")
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            
            # Build URL based on role and branch
            url = f"{self.api_url}/transactions/"
            if self.branch_id and self.user_role != "director":
                url += f"?branch_id={self.branch_id}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = transactions_data.get("transactions", [])
                
                # Update table
                self.transactions_table.setRowCount(len(transactions))
                
                for i, transaction in enumerate(transactions):
                    # Transaction ID
                    self.transactions_table.setItem(i, 0, QTableWidgetItem(str(transaction.get("id", ""))))
                    
                    # Date
                    date_str = transaction.get("date", "")
                    formatted_date = date_str
                    try:
                        # Try to parse and format the date
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                    except:
                        pass
                    self.transactions_table.setItem(i, 1, QTableWidgetItem(formatted_date))
                    
                    # Sender
                    self.transactions_table.setItem(i, 2, QTableWidgetItem(transaction.get("sender", "")))
                    
                    # Receiver
                    self.transactions_table.setItem(i, 3, QTableWidgetItem(transaction.get("receiver", "")))
                    
                    # Amount
                    amount = transaction.get("amount", 0)
                    formatted_amount = f"{float(amount):,.2f}" if amount else "0.00"
                    self.transactions_table.setItem(i, 4, QTableWidgetItem(formatted_amount))
                    
                    # Status
                    status = transaction.get("status", "pending")
                    status_arabic = self.get_status_arabic(status)
                    status_item = QTableWidgetItem(status_arabic)
                    
                    # Color-code status
                    status_item.setBackground(self.get_status_color(status))
                    self.transactions_table.setItem(i, 5, status_item)
                    
                    # Employee
                    self.transactions_table.setItem(i, 6, QTableWidgetItem(transaction.get("employee_name", "")))
                    
                    # Notes
                    self.transactions_table.setItem(i, 7, QTableWidgetItem(transaction.get("notes", "")))
                
                # Update status
                self.status_label.setText("تم تحميل البيانات بنجاح")
                self.count_label.setText(f"عدد التحويلات: {len(transactions)}")
            else:
                self.status_label.setText(f"خطأ في تحميل البيانات: {response.status_code}")
                QMessageBox.warning(self, "خطأ", f"فشل تحميل بيانات التحويلات: رمز الحالة {response.status_code}")
        except Exception as e:
            self.status_label.setText("خطأ في الاتصال")
            print(f"Error loading transactions: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def get_status_arabic(self, status):
        """Convert status to Arabic."""
        status_map = {
            "pending": "قيد الانتظار",
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
            "pending": QColor(255, 255, 200),  # Light yellow
            "processing": QColor(200, 200, 255),  # Light blue
            "completed": QColor(200, 255, 200),  # Light green
            "cancelled": QColor(255, 200, 200),  # Light red
            "rejected": QColor(255, 150, 150),  # Darker red
            "on_hold": QColor(255, 200, 150)  # Light orange
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
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def show_context_menu(self, position):
        """Show context menu for transactions table."""
        # Only show context menu if a row is selected
        if not self.transactions_table.selectedItems():
            return
        
        row = self.transactions_table.selectedItems()[0].row()
        transaction_id = self.transactions_table.item(row, 0).text()
        current_status = self.transactions_table.item(row, 5).text()
        
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
    
    def update_transaction_status(self, transaction_id, new_status):
        """Update the status of a transaction."""
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            data = {
                "transaction_id": transaction_id,
                "status": new_status
            }
            response = requests.post(f"{self.api_url}/update-transaction-status/", json=data, headers=headers)
            
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث حالة التحويل بنجاح")
                self.load_transactions()  # Refresh the list
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحديث حالة التحويل: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error updating transaction status: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def print_transaction(self, transaction_id):
        """Print a transaction."""
        # This is a placeholder - in a real app, you would implement actual printing
        QMessageBox.information(self, "طباعة", f"سيتم طباعة التحويل رقم {transaction_id}")
    
    def show_filter_dialog(self):
        """Show dialog for filtering transactions."""
        filter_dialog = TransactionFilterDialog(self)
        if filter_dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_filters(filter_dialog.get_filters())
    
    def apply_filters(self, filters):
        """Apply filters to transactions."""
        self.status_label.setText("جاري تطبيق التصفية...")
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            
            # Build URL with query parameters
            url = f"{self.api_url}/transactions/"
            query_params = []
            
            if self.branch_id and self.user_role != "director":
                query_params.append(f"branch_id={self.branch_id}")
            
            if filters.get("start_date"):
                query_params.append(f"start_date={filters['start_date']}")
            
            if filters.get("end_date"):
                query_params.append(f"end_date={filters['end_date']}")
            
            if filters.get("status"):
                query_params.append(f"status={filters['status']}")
            
            if filters.get("min_amount"):
                query_params.append(f"min_amount={filters['min_amount']}")
            
            if filters.get("max_amount"):
                query_params.append(f"max_amount={filters['max_amount']}")
            
            if filters.get("sender"):
                query_params.append(f"sender={filters['sender']}")
            
            if filters.get("receiver"):
                query_params.append(f"receiver={filters['receiver']}")
            
            if query_params:
                url += "?" + "&".join(query_params)
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                transactions_data = response.json()
                transactions = transactions_data.get("transactions", [])
                
                # Update table
                self.transactions_table.setRowCount(len(transactions))
                
                for i, transaction in enumerate(transactions):
                    # Transaction ID
                    self.transactions_table.setItem(i, 0, QTableWidgetItem(str(transaction.get("id", ""))))
                    
                    # Date
                    date_str = transaction.get("date", "")
                    formatted_date = date_str
                    try:
                        # Try to parse and format the date
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                    except:
                        pass
                    self.transactions_table.setItem(i, 1, QTableWidgetItem(formatted_date))
                    
                    # Sender
                    self.transactions_table.setItem(i, 2, QTableWidgetItem(transaction.get("sender", "")))
                    
                    # Receiver
                    self.transactions_table.setItem(i, 3, QTableWidgetItem(transaction.get("receiver", "")))
                    
                    # Amount
                    amount = transaction.get("amount", 0)
                    formatted_amount = f"{float(amount):,.2f}" if amount else "0.00"
                    self.transactions_table.setItem(i, 4, QTableWidgetItem(formatted_amount))
                    
                    # Status
                    status = transaction.get("status", "pending")
                    status_arabic = self.get_status_arabic(status)
                    status_item = QTableWidgetItem(status_arabic)
                    
                    # Color-code status
                    status_item.setBackground(self.get_status_color(status))
                    self.transactions_table.setItem(i, 5, status_item)
                    
                    # Employee
                    self.transactions_table.setItem(i, 6, QTableWidgetItem(transaction.get("employee_name", "")))
                    
                    # Notes
                    self.transactions_table.setItem(i, 7, QTableWidgetItem(transaction.get("notes", "")))
                
                # Update status
                self.status_label.setText("تم تطبيق التصفية بنجاح")
                self.count_label.setText(f"عدد التحويلات: {len(transactions)}")
            else:
                self.status_label.setText(f"خطأ في تطبيق التصفية: {response.status_code}")
                QMessageBox.warning(self, "خطأ", f"فشل تطبيق التصفية: رمز الحالة {response.status_code}")
        except Exception as e:
            self.status_label.setText("خطأ في الاتصال")
            print(f"Error applying filters: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                               "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def export_transactions(self):
        """Export transactions to a file."""
        # This is a placeholder - in a real app, you would implement actual export functionality
        QMessageBox.information(self, "تصدير", "سيتم تصدير التحويلات إلى ملف")

class TransactionDetailsDialog(QDialog):
    """Dialog for displaying transaction details."""
    
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        
        self.setWindowTitle("تفاصيل التحويل")
        self.setGeometry(300, 300, 500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3498db;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Transaction info group
        transaction_group = QGroupBox("معلومات التحويل")
        transaction_layout = QFormLayout()
        
        # Transaction ID
        transaction_id_label = QLabel("رقم التحويل:")
        transaction_id_value = QLabel(str(self.transaction.get("id", "")))
        transaction_id_value.setStyleSheet("font-weight: bold;")
        transaction_layout.addRow(transaction_id_label, transaction_id_value)
        
        # Date
        date_label = QLabel("التاريخ:")
        date_value = QLabel(self.transaction.get("date", ""))
        date_value.setStyleSheet("font-weight: bold;")
        transaction_layout.addRow(date_label, date_value)
        
        # Amount
        amount_label = QLabel("المبلغ:")
        amount = self.transaction.get("amount", 0)
        formatted_amount = f"{float(amount):,.2f}" if amount else "0.00"
        amount_value = QLabel(formatted_amount)
        amount_value.setStyleSheet("font-weight: bold;")
        transaction_layout.addRow(amount_label, amount_value)
        
        # Status
        status_label = QLabel("الحالة:")
        status = self.transaction.get("status", "pending")
        status_arabic = self.get_status_arabic(status)
        status_value = QLabel(status_arabic)
        status_value.setStyleSheet(f"font-weight: bold; color: {self.get_status_text_color(status)};")
        transaction_layout.addRow(status_label, status_value)
        
        transaction_group.setLayout(transaction_layout)
        layout.addWidget(transaction_group)
        
        # Sender info group
        sender_group = QGroupBox("معلومات المرسل")
        sender_layout = QFormLayout()
        
        # Sender name
        sender_name_label = QLabel("الاسم:")
        sender_name_value = QLabel(self.transaction.get("sender", ""))
        sender_name_value.setStyleSheet("font-weight: bold;")
        sender_layout.addRow(sender_name_label, sender_name_value)
        
        # Sender mobile
        sender_mobile_label = QLabel("رقم الهاتف:")
        sender_mobile_value = QLabel(self.transaction.get("sender_mobile", ""))
        sender_layout.addRow(sender_mobile_label, sender_mobile_value)
        
        # Sender ID
        sender_id_label = QLabel("رقم الهوية:")
        sender_id_value = QLabel(self.transaction.get("sender_id", ""))
        sender_layout.addRow(sender_id_label, sender_id_value)
        
        # Sender address
        sender_address_label = QLabel("العنوان:")
        sender_address_value = QLabel(self.transaction.get("sender_location", ""))
        sender_layout.addRow(sender_address_label, sender_address_value)
        
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)
        
        # Receiver info group
        receiver_group = QGroupBox("معلومات المستلم")
        receiver_layout = QFormLayout()
        
        # Receiver name
        receiver_name_label = QLabel("الاسم:")
        receiver_name_value = QLabel(self.transaction.get("receiver", ""))
        receiver_name_value.setStyleSheet("font-weight: bold;")
        receiver_layout.addRow(receiver_name_label, receiver_name_value)
        
        # Receiver mobile
        receiver_mobile_label = QLabel("رقم الهاتف:")
        receiver_mobile_value = QLabel(self.transaction.get("receiver_mobile", ""))
        receiver_layout.addRow(receiver_mobile_label, receiver_mobile_value)
        
        # Receiver ID
        receiver_id_label = QLabel("رقم الهوية:")
        receiver_id_value = QLabel(self.transaction.get("receiver_id", ""))
        receiver_layout.addRow(receiver_id_label, receiver_id_value)
        
        # Receiver address
        receiver_address_label = QLabel("العنوان:")
        receiver_address_value = QLabel(self.transaction.get("receiver_location", ""))
        receiver_layout.addRow(receiver_address_label, receiver_address_value)
        
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)
        
        # Additional info group
        additional_group = QGroupBox("معلومات إضافية")
        additional_layout = QFormLayout()
        
        # Employee
        employee_label = QLabel("الموظف:")
        employee_value = QLabel(self.transaction.get("employee_name", ""))
        additional_layout.addRow(employee_label, employee_value)
        
        # Branch
        branch_label = QLabel("الفرع:")
        branch_value = QLabel(self.transaction.get("branch_name", ""))
        additional_layout.addRow(branch_label, branch_value)
        
        # Notes
        notes_label = QLabel("ملاحظات:")
        notes_value = QLabel(self.transaction.get("notes", ""))
        notes_value.setWordWrap(True)
        additional_layout.addRow(notes_label, notes_value)
        
        additional_group.setLayout(additional_layout)
        layout.addWidget(additional_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        print_button = QPushButton("طباعة")
        print_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        print_button.clicked.connect(self.print_transaction)
        buttons_layout.addWidget(print_button)
        
        close_button = QPushButton("إغلاق")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def get_status_arabic(self, status):
        """Convert status to Arabic."""
        status_map = {
            "pending": "قيد الانتظار",
            "processing": "قيد المعالجة",
            "completed": "مكتمل",
            "cancelled": "ملغي",
            "rejected": "مرفوض",
            "on_hold": "معلق"
        }
        return status_map.get(status, status)
    
    def get_status_text_color(self, status):
        """Get text color for status."""
        status_colors = {
            "pending": "#f39c12",  # Orange
            "processing": "#3498db",  # Blue
            "completed": "#2ecc71",  # Green
            "cancelled": "#e74c3c",  # Red
            "rejected": "#c0392b",  # Darker red
            "on_hold": "#f1c40f"  # Yellow
        }
        return status_colors.get(status, "#333333")  # Dark gray default
    
    def print_transaction(self):
        """Print the transaction."""
        # This is a placeholder - in a real app, you would implement actual printing
        QMessageBox.information(self, "طباعة", f"سيتم طباعة التحويل رقم {self.transaction.get('id', '')}")

class TransactionFilterDialog(QDialog):
    """Dialog for filtering transactions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("تصفية التحويلات")
        self.setGeometry(300, 300, 400, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3498db;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
            QDateEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Date filter group
        date_group = QGroupBox("تصفية حسب التاريخ")
        date_layout = QFormLayout()
        
        # Start date
        start_date_label = QLabel("من تاريخ:")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))  # Default to 1 month ago
        date_layout.addRow(start_date_label, self.start_date_edit)
        
        # End date
        end_date_label = QLabel("إلى تاريخ:")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())  # Default to today
        date_layout.addRow(end_date_label, self.end_date_edit)
        
        # Use date filter checkbox
        self.use_date_filter = QCheckBox("تطبيق تصفية التاريخ")
        self.use_date_filter.setChecked(False)
        date_layout.addRow("", self.use_date_filter)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # Amount filter group
        amount_group = QGroupBox("تصفية حسب المبلغ")
        amount_layout = QFormLayout()
        
        # Min amount
        min_amount_label = QLabel("الحد الأدنى:")
        self.min_amount_spin = QDoubleSpinBox()
        self.min_amount_spin.setRange(0, 1000000000)
        self.min_amount_spin.setDecimals(2)
        self.min_amount_spin.setSingleStep(100)
        amount_layout.addRow(min_amount_label, self.min_amount_spin)
        
        # Max amount
        max_amount_label = QLabel("الحد الأقصى:")
        self.max_amount_spin = QDoubleSpinBox()
        self.max_amount_spin.setRange(0, 1000000000)
        self.max_amount_spin.setDecimals(2)
        self.max_amount_spin.setSingleStep(100)
        self.max_amount_spin.setValue(1000000)  # Default to a high value
        amount_layout.addRow(max_amount_label, self.max_amount_spin)
        
        # Use amount filter checkbox
        self.use_amount_filter = QCheckBox("تطبيق تصفية المبلغ")
        self.use_amount_filter.setChecked(False)
        amount_layout.addRow("", self.use_amount_filter)
        
        amount_group.setLayout(amount_layout)
        layout.addWidget(amount_group)
        
        # Status filter group
        status_group = QGroupBox("تصفية حسب الحالة")
        status_layout = QFormLayout()
        
        # Status combo
        status_label = QLabel("الحالة:")
        self.status_combo = QComboBox()
        self.status_combo.addItem("الكل", "")
        self.status_combo.addItem("قيد الانتظار", "pending")
        self.status_combo.addItem("قيد المعالجة", "processing")
        self.status_combo.addItem("مكتمل", "completed")
        self.status_combo.addItem("ملغي", "cancelled")
        self.status_combo.addItem("مرفوض", "rejected")
        self.status_combo.addItem("معلق", "on_hold")
        status_layout.addRow(status_label, self.status_combo)
        
        # Use status filter checkbox
        self.use_status_filter = QCheckBox("تطبيق تصفية الحالة")
        self.use_status_filter.setChecked(False)
        status_layout.addRow("", self.use_status_filter)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Person filter group
        person_group = QGroupBox("تصفية حسب الأشخاص")
        person_layout = QFormLayout()
        
        # Sender
        sender_label = QLabel("المرسل:")
        self.sender_input = QLineEdit()
        person_layout.addRow(sender_label, self.sender_input)
        
        # Receiver
        receiver_label = QLabel("المستلم:")
        self.receiver_input = QLineEdit()
        person_layout.addRow(receiver_label, self.receiver_input)
        
        # Use person filter checkbox
        self.use_person_filter = QCheckBox("تطبيق تصفية الأشخاص")
        self.use_person_filter.setChecked(False)
        person_layout.addRow("", self.use_person_filter)
        
        person_group.setLayout(person_layout)
        layout.addWidget(person_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        reset_button = QPushButton("إعادة تعيين")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        reset_button.clicked.connect(self.reset_filters)
        buttons_layout.addWidget(reset_button)
        
        apply_button = QPushButton("تطبيق")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        apply_button.clicked.connect(self.accept)
        buttons_layout.addWidget(apply_button)
        
        cancel_button = QPushButton("إلغاء")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def reset_filters(self):
        """Reset all filters to default values."""
        # Reset date filters
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit.setDate(QDate.currentDate())
        self.use_date_filter.setChecked(False)
        
        # Reset amount filters
        self.min_amount_spin.setValue(0)
        self.max_amount_spin.setValue(1000000)
        self.use_amount_filter.setChecked(False)
        
        # Reset status filter
        self.status_combo.setCurrentIndex(0)
        self.use_status_filter.setChecked(False)
        
        # Reset person filters
        self.sender_input.clear()
        self.receiver_input.clear()
        self.use_person_filter.setChecked(False)
    
    def get_filters(self):
        """Get the filter values as a dictionary."""
        filters = {}
        
        # Date filters
        if self.use_date_filter.isChecked():
            filters["start_date"] = self.start_date_edit.date().toString("yyyy-MM-dd")
            filters["end_date"] = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # Amount filters
        if self.use_amount_filter.isChecked():
            filters["min_amount"] = self.min_amount_spin.value()
            filters["max_amount"] = self.max_amount_spin.value()
        
        # Status filter
        if self.use_status_filter.isChecked() and self.status_combo.currentData():
            filters["status"] = self.status_combo.currentData()
        
        # Person filters
        if self.use_person_filter.isChecked():
            if self.sender_input.text():
                filters["sender"] = self.sender_input.text()
            if self.receiver_input.text():
                filters["receiver"] = self.receiver_input.text()
        
        return filters

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransactionHistory()
    window.show()
    sys.exit(app.exec())
