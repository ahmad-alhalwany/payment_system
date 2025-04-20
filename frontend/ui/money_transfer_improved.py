import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QLineEdit, QFormLayout, QComboBox, QGroupBox,
    QGridLayout, QDateEdit, QDoubleSpinBox, QCheckBox, QMenu,
    QTextEdit,  QDialogButtonBox
)
import os
from PyQt6.QtGui import QFont, QColor, QAction
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime
from ui.user_search import UserSearchDialog
from ui.confirm_dialog import ConfirmTransactionDialog
from ui.arabic_amount import number_to_arabic_words

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

class MoneyTransferApp(QWidget):
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
        
        self.setWindowTitle("نظام تحويل الأموال الداخلي")
        self.setGeometry(100, 100, 800, 700)
        
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
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("نظام تحويل الأموال")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        
        # Menu button
        menu_button = ModernButton("القائمة", color="#9b59b6")
        menu_button.setFixedWidth(100)
        menu_button.clicked.connect(self.show_menu)
        header_layout.addWidget(menu_button, 0)  # No stretch
        
        layout.addLayout(header_layout)
        
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
        self.receive_money_tab = QWidget()  # New receive money tab
        
        # Set up tabs
        self.setup_new_transfer_tab()
        self.setup_transactions_tab()
        self.setup_notifications_tab()
        self.setup_receive_money_tab()  # Setup new receive money tab        
        
        # Add tabs to widget
        self.tabs.addTab(self.new_transfer_tab, "تحويل جديد")
        self.tabs.addTab(self.transactions_tab, "التحويلات الصادرة")  # Changed to Outgoing
        self.tabs.addTab(self.receive_money_tab, "التحويلات الواردة")  # Changed to Incoming
            
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
        
    def show_menu(self):
        """Show the menu with logout and close options."""
        menu = QMenu(self)
        
        # Add logout action
        logout_action = QAction("تسجيل الخروج", self)
        logout_action.triggered.connect(self.logout)
        menu.addAction(logout_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add close action
        close_action = QAction("إغلاق البرنامج", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        # Show menu at the position of the menu button
        sender = self.sender()
        if sender:
            menu.exec(sender.mapToGlobal(sender.rect().bottomLeft()))
    
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
            # Emit signal to notify parent about logout request
            self.logoutRequested.emit()
            self.close()    
        
    def on_filter_change(self, transfer_type):
        if transfer_type == 'outgoing':
            self.current_page_outgoing = 1
            self.filter_transactions()
        elif transfer_type == 'incoming':
            self.current_page_incoming = 1
            self.filter_received_transactions()        
        
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
            status_arabic = self.get_status_arabic(status)
            status_item = QTableWidgetItem(status_arabic)
            status_item.setBackground(self.get_status_color(status))
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
            
    def print_receipt(self, transaction_data):
        """Print the receipt for a received transaction."""
        # Create print dialog
        print_dialog = QDialog(self)
        print_dialog.setWindowTitle("طباعة إيصال الاستلام")
        print_dialog.setFixedSize(400, 600)
        
        layout = QVBoxLayout()
        
        # Create printable content
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
            <div style='text-align: center; font-family: Arial;'>
                <h1 style='color: #2c3e50;'>إيصال استلام أموال</h1>
                <hr>
                <div style='text-align: right;'>
                    <p><b>رقم التحويل:</b> {transaction_data['id']}</p>
                    <p><b>تاريخ التحويل:</b> {transaction_data['date']}</p>
                    <p><b>تاريخ الاستلام:</b> {transaction_data['received_at']}</p>
                    <h3 style='color: #e74c3c;'>المرسل:</h3>
                    <p>{transaction_data['sender']}</p>
                    <p>الفرع: {transaction_data['sending_branch']}</p>
                    <h3 style='color: #3498db;'>المستلم:</h3>
                    <p>{transaction_data['receiver']}</p>
                    <p>الهاتف: {transaction_data['receiver_mobile']}</p>
                    <p>الهوية: {transaction_data['receiver_id']}</p>
                    <p>العنوان: {transaction_data['receiver_address']}</p>
                    <p>المحافظة: {transaction_data['receiver_governorate']}</p>
                    <p><b>المبلغ:</b> {transaction_data['amount']} {transaction_data['currency']}</p>
                    <p><b>تم الاستلام بواسطة:</b> {transaction_data['received_by']}</p>
                    <p><b>الفرع المستلم:</b> {transaction_data['destination_branch']}</p>
                    <hr>
                    <p style='color: #95a5a6;'>شكراً لاستخدامكم خدماتنا</p>
                    <p style='color: #95a5a6;'>هذا الإيصال يؤكد استلام الأموال</p>
                    <p style='color: #95a5a6;'>التوقيع: ________________________</p>
                </div>
            </div>
        """)
        
        # Print button
        print_btn = ModernButton("طباعة", color="#27ae60")
        print_btn.clicked.connect(lambda: self.send_to_printer(content))
        
        layout.addWidget(content)
        layout.addWidget(print_btn)
        print_dialog.setLayout(layout)
        print_dialog.exec()         
    
    def print_received_transaction(self, item=None):
        """Print received transaction receipt."""
        if item is None or isinstance(item, bool):
            # Called from button, get selected row
            selected_items = self.received_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "تحذير", "الرجاء تحديد تحويل لطباعته")
                return
            row = selected_items[0].row()
        else:
            # Called from double-click
            row = item.row()
        
        transaction_id = self.received_table.item(row, 0).text()
        sending_branch = self.received_table.item(row, 10).text()  # Changed from 9 to 10
        dest_branch = self.received_table.item(row, 11).text()     # Changed from 10 to 11
        received_status = self.received_table.item(row, 13).text() # Changed from 12 to 13
        status = self.received_table.item(row, 7).text()
        
        # Check if the transfer is confirmed before allowing printing
        if status != "مكتمل":
            QMessageBox.warning(self, "تحذير", "لا يمكن طباعة الإيصال للتحويلات غير المؤكدة")
            return
        
        # Get all transaction details from the table
        transaction_data = {
            "id": transaction_id,
            "date": self.received_table.item(row, 1).text(),
            "sender": self.received_table.item(row, 2).text(),
            "receiver": self.received_table.item(row, 3).text(),
            "amount": self.received_table.item(row, 4).text(),
            "currency": self.received_table.item(row, 5).text(),
            "receiver_governorate": self.received_table.item(row, 6).text(),
            "status": status,
            "employee_name": self.received_table.item(row, 9).text(),
            "sending_branch": sending_branch,
            "destination_branch": dest_branch,
            "branch_governorate": self.received_table.item(row, 12).text(),
            "received_status": received_status,
            "received_by": self.full_name,
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Format transaction ID with dashes like in the image (1925-5814-5221)
        # If the ID is numeric, format it with dashes
        formatted_id = transaction_data['id']
        if transaction_data['id'].isdigit() and len(transaction_data['id']) >= 4:
            id_parts = []
            id_str = transaction_data['id']
            while id_str:
                if len(id_str) > 4:
                    id_parts.append(id_str[:4])
                    id_str = id_str[4:]
                else:
                    id_parts.append(id_str)
                    id_str = ""
            formatted_id = "-".join(id_parts)
        
        # Convert amount to Arabic words
        amount_in_arabic = number_to_arabic_words(transaction_data['amount'], transaction_data['currency'])
        
        # Create print dialog
        print_dialog = QDialog(self)
        print_dialog.setWindowTitle("طباعة التحويل")
        print_dialog.setFixedSize(600, 700)
        
        layout = QVBoxLayout()
        
        # Create printable content with improved layout
        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"""
            <div style='font-family: Arial; direction: rtl; background-color: #f9f9f9; padding: 0; margin: 0;'>
                <!-- Header -->
                <div style='text-align: right; padding: 10px; background-color: #e8f5e9; border-bottom: 1px solid #ddd;'>
                    <h2 style='margin: 0; color: #333;'>طباعة التحويل</h2>
                </div>
                
                <!-- Transaction Number Row -->
                <div style='margin: 15px 0; text-align: center;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #333;'>الرقم</strong>
                        </div>
                        <div style='flex: 3; text-align: center;'>
                            <strong style='font-size: 16px;'>{formatted_id}</strong>
                        </div>
                        <div style='flex: 1; text-align: center; background-color: #e8f5e9; padding: 5px; border-radius: 4px;'>
                            <strong style='color: #2e7d32;'>تسليم</strong>
                        </div>
                    </div>
                </div>
                
                <!-- Main Content -->
                <div style='margin: 0 10px;'>
                    <!-- From/To Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>من</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['sending_branch']}
                        </div>
                    </div>
                    
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>إلى</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['destination_branch']}
                        </div>
                    </div>
                    
                    <!-- Sender Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>المرسل</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['sender']}
                        </div>
                    </div>
                    
                    <!-- Receiver Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>المفوض</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['receiver']}
                        </div>
                    </div>
                    
                    <!-- Contact Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>اتصال</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data.get('receiver_mobile', '')}
                        </div>
                    </div>
                    
                    <!-- Beneficiary Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>المستفيد</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['receiver']}
                        </div>
                    </div>
                    
                    <!-- Recipient Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>المستلم</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['receiver']}
                        </div>
                    </div>
                    
                    <!-- Contact (Phone) Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>اتصال</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data.get('receiver_mobile', '')}
                        </div>
                    </div>
                    
                    <!-- Date Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>التاريخ</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['date']}
                        </div>
                    </div>
                    
                    <!-- Amount Row -->
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                        <div style='flex: 1; text-align: right;'>
                            <strong style='color: #555;'>المبلغ</strong>
                        </div>
                        <div style='flex: 5; text-align: left;'>
                            {transaction_data['amount']} {transaction_data['currency']}
                        </div>
                    </div>
                    
                    <!-- Amount in Words Row -->
                    <div style='margin-bottom: 15px; padding: 8px; background-color: #f5f5f5; border-radius: 4px;'>
                        <p style='margin: 0; text-align: right; color: #333;'>
                            {amount_in_arabic}
                        </p>
                    </div>
                </div>
                
                <!-- Footer Note -->
                <div style='margin: 15px 0; text-align: center; color: #4CAF50; font-weight: bold;'>
                    <p>يطلب تبليغ المستفيد برقم الحوالة</p>
                </div>
                
                <!-- System Section -->
                <hr style='border: none; border-top: 1px solid #ddd; margin: 20px 0;'>
                
                <div style='text-align: right; margin: 0 10px;'>
                    <h3 style='color: #4CAF50; margin-bottom: 15px;'>نسخة النظام</h3>
                    
                    <div style='margin-bottom: 8px;'>
                        <strong style='color: #555;'>بيانات فرع المرسل:</strong>
                        <span style='margin-right: 10px;'>{transaction_data['sending_branch']}</span>
                    </div>
                    
                    <div style='margin-bottom: 8px;'>
                        <strong style='color: #555;'>بيانات فرع المستلم:</strong>
                        <span style='margin-right: 10px;'>{transaction_data['destination_branch']} - {transaction_data['branch_governorate']}</span>
                    </div>
                    
                    <div style='margin-bottom: 8px;'>
                        <strong style='color: #555;'>اسم الموظف:</strong>
                        <span style='margin-right: 10px;'>{transaction_data['employee_name']}</span>
                    </div>
                    
                    <div style='margin-bottom: 8px;'>
                        <strong style='color: #555;'>نوع التحويل:</strong>
                        <span style='margin-right: 10px;'>تحويل وارد</span>
                    </div>
                    
                    <div style='margin-bottom: 8px;'>
                        <strong style='color: #555;'>حالة التحويل:</strong>
                        <span style='margin-right: 10px;'>{transaction_data['status']}</span>
                    </div>
                    
                    <div style='margin-top: 30px; border-top: 1px dashed #ddd; padding-top: 15px;'>
                        <p><strong>اسم العميل الكامل:</strong> ________________________</p>
                        <p><strong>التوقيع:</strong> ________________________</p>
                    </div>
                </div>
            </div>
        """)
        
        # Print button
        print_btn = ModernButton("طباعة", color="#4CAF50")
        print_btn.clicked.connect(lambda: self.send_to_printer(content))
        
        layout.addWidget(content)
        layout.addWidget(print_btn)
        print_dialog.setLayout(layout)
        print_dialog.exec()
    
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
    
    def setup_new_transfer_tab(self):
        """Set up the new transfer tab."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("نظام تحويل الأموال")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Current user and branch info (new section)
        info_group = ModernGroupBox("معلومات الموظف والفرع", "#9b59b6")
        info_layout = QGridLayout()
        
        employee_label = QLabel("الموظف:")
        info_layout.addWidget(employee_label, 0, 1)
        
        # Set employee name - use full_name which will be "System Manager" for the System Manager role
        self.employee_name_label = QLabel(self.full_name)
        self.employee_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.employee_name_label, 0, 0)
        
        branch_label = QLabel("الفرع الحالي:")
        info_layout.addWidget(branch_label, 0, 3)
        
        # Branch label will be set in load_branches method
        self.current_branch_label = QLabel("")
        self.current_branch_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.current_branch_label, 0, 2)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Sender information (remains the same)
        sender_group = ModernGroupBox("معلومات المرسل", "#e74c3c")
        sender_layout = QGridLayout()
        
        # Sender name
        sender_name_label = QLabel("اسم المرسل:")
        sender_layout.addWidget(sender_name_label, 0, 0)
        
        self.sender_name_input = QLineEdit()
        self.sender_name_input.setPlaceholderText("أدخل اسم المرسل")
        sender_layout.addWidget(self.sender_name_input, 0, 1)
        
        # Sender mobile
        sender_mobile_label = QLabel("رقم الهاتف:")
        sender_layout.addWidget(sender_mobile_label, 0, 2)
        
        self.sender_mobile_input = QLineEdit()
        self.sender_mobile_input.setPlaceholderText("أدخل رقم الهاتف")
        sender_layout.addWidget(self.sender_mobile_input, 0, 3)
        
        # Sender ID
        sender_id_label = QLabel("رقم الهوية:")
        sender_layout.addWidget(sender_id_label, 1, 0)
        
        self.sender_id_input = QLineEdit()
        self.sender_id_input.setPlaceholderText("أدخل رقم الهوية")
        sender_layout.addWidget(self.sender_id_input, 1, 1)
        
        # Sender address
        sender_address_label = QLabel("العنوان:")
        sender_layout.addWidget(sender_address_label, 1, 2)
        
        self.sender_address_input = QLineEdit()
        self.sender_address_input.setPlaceholderText("أدخل العنوان")
        sender_layout.addWidget(self.sender_address_input, 1, 3)
        
        # Sender governorate (now fixed and read-only)
        sender_governorate_label = QLabel("المحافظة:")
        sender_layout.addWidget(sender_governorate_label, 2, 0)
        
        # For System Manager, we'll use a dropdown instead of a fixed label
        if self.branch_id == 0 or self.full_name == "System Manager":
            self.sender_governorate_input = QComboBox()
            self.sender_governorate_input.addItems([
                "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", 
                "إدلب", "دير الزور", "الرقة", "الحسكة", "السويداء", "درعا", "القنيطرة"
            ])
            sender_layout.addWidget(self.sender_governorate_input, 2, 1)
            # Hide the label that would be set in load_branches
            self.sender_governorate_label = QLabel("")
            self.sender_governorate_label.setVisible(False)
        else:
            # For regular users, use the fixed label as before
            self.sender_governorate_label = QLabel("")  # Will be populated in load_branches
            self.sender_governorate_label.setStyleSheet("font-weight: bold;")
            sender_layout.addWidget(self.sender_governorate_label, 2, 1)
        
        # Sender location
        sender_location_label = QLabel("المنطقة:")
        sender_layout.addWidget(sender_location_label, 2, 2)
        
        self.sender_location_input = QLineEdit()
        self.sender_location_input.setPlaceholderText("أدخل المنطقة")
        sender_layout.addWidget(self.sender_location_input, 2, 3)
        
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)
        
        # Receiver information - REMOVED region, address, and ID number fields
        receiver_group = ModernGroupBox("معلومات المستلم", "#3498db")
        receiver_layout = QGridLayout()
        
        # Receiver name
        receiver_name_label = QLabel("اسم المستلم:")
        receiver_layout.addWidget(receiver_name_label, 0, 0)
        
        self.receiver_name_input = QLineEdit()
        self.receiver_name_input.setPlaceholderText("أدخل اسم المستلم")
        receiver_layout.addWidget(self.receiver_name_input, 0, 1)
        
        # Receiver mobile
        receiver_mobile_label = QLabel("رقم الهاتف:")
        receiver_layout.addWidget(receiver_mobile_label, 0, 2)
        
        self.receiver_mobile_input = QLineEdit()
        self.receiver_mobile_input.setPlaceholderText("أدخل رقم الهاتف")
        receiver_layout.addWidget(self.receiver_mobile_input, 0, 3)
        
        # Receiver governorate (kept as it might be needed for branch selection)
        receiver_governorate_label = QLabel("المحافظة:")
        receiver_layout.addWidget(receiver_governorate_label, 1, 0)
        
        self.receiver_governorate_input = QComboBox()
        self.receiver_governorate_input.addItems([
            "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", 
            "إدلب", "دير الزور", "الرقة", "الحسكة", "السويداء", "درعا", "القنيطرة"
        ])
        self.receiver_governorate_input.currentTextChanged.connect(self.update_destination_branches)
        receiver_layout.addWidget(self.receiver_governorate_input, 1, 1)
        
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)
        
        # Transfer information (remains the same)
        transfer_group = ModernGroupBox("معلومات التحويل", "#2ecc71")
        transfer_layout = QGridLayout()
        
        # Amount row
        amount_label = QLabel("المبلغ:")
        transfer_layout.addWidget(amount_label, 0, 0)
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 1000000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(100)
        self.amount_input.setValue(0)
        transfer_layout.addWidget(self.amount_input, 0, 1)
        
        # Benefited amount (new field)
        benefited_label = QLabel("المبلغ المستفاد (اختياري):")
        transfer_layout.addWidget(benefited_label, 0, 2)
        
        self.benefited_input = QDoubleSpinBox()
        self.benefited_input.setRange(0, 1000000000)
        self.benefited_input.setDecimals(2)
        self.benefited_input.setSingleStep(100)
        self.benefited_input.setValue(0)
        transfer_layout.addWidget(self.benefited_input, 0, 3)
        
        # Currency
        currency_label = QLabel("العملة:")
        transfer_layout.addWidget(currency_label, 1, 0)
        
        self.currency_input = QComboBox()
        self.currency_input.addItems([
            "ليرة سورية (SYP)", 
            "دولار أمريكي (USD)", 
            "يورو (EUR)", 
            "ريال سعودي (SAR)", 
            "جنيه إسترليني (GBP)"
        ])
        transfer_layout.addWidget(self.currency_input, 1, 1)
        
        # Branch
        branch_label = QLabel("الفرع المستلم:")
        transfer_layout.addWidget(branch_label, 1, 2)
        
        self.branch_input = QComboBox()
        transfer_layout.addWidget(self.branch_input, 1, 3)
        # Enable branch selection for all users to allow sending to any branch
        self.branch_input.setEnabled(True)
        transfer_layout.addWidget(self.branch_input, 1, 3)
        
        # Date
        date_label = QLabel("التاريخ:")
        transfer_layout.addWidget(date_label, 2, 0)
        
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        transfer_layout.addWidget(self.date_input, 2, 1)
        
        # Notes
        notes_label = QLabel("ملاحظات:")
        transfer_layout.addWidget(notes_label, 2, 2)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("أدخل أي ملاحظات إضافية")
        self.notes_input.setMaximumHeight(80)
        transfer_layout.addWidget(self.notes_input, 2, 3)
        
        transfer_group.setLayout(transfer_layout)
        layout.addWidget(transfer_group)
        
        # Buttons (remain the same)
        buttons_layout = QHBoxLayout()
        
        clear_button = ModernButton("مسح", color="#e74c3c")
        clear_button.clicked.connect(self.clear_form)
        buttons_layout.addWidget(clear_button)
        
        save_button = ModernButton("حفظ", color="#3498db")
        save_button.clicked.connect(self.save_transfer)
        buttons_layout.addWidget(save_button)
        
        submit_button = ModernButton("إرسال", color="#2ecc71")
        submit_button.clicked.connect(self.show_confirmation)
        buttons_layout.addWidget(submit_button)
        
        layout.addLayout(buttons_layout)
        
        self.new_transfer_tab.setLayout(layout)
        
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
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(13)
        self.transactions_table.setHorizontalHeaderLabels([
            "رقم التحويل", "التاريخ", "المرسل", "المستلم", "المبلغ", "العملة", 
            "محافظة المستلم", "الحالة", "النوع", "اسم الموظف", "الفرع المرسل", 
            "الفرع المستلم", "محافظة الفرع"
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
        self.transactions_table.itemDoubleClicked.connect(self.print_transaction)
        
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
                
                # Reset pagination
                self.current_page_outgoing = 1
                self.filter_transactions()
                
                # Create a mapping of branch IDs to names for quick lookup
                self.branch_id_to_name = {branch['id']: branch['name'] for branch in self.branches}
                
                # Apply current filter
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
    
    def filter_transactions(self):
        """Filter transactions based on selected status."""
        if not hasattr(self, 'all_transactions'):
            return
        
        selected_status = self.status_filter.currentData()
        
        if selected_status == "all":
            filtered_transactions = self.all_transactions
        else:
            filtered_transactions = [t for t in self.all_transactions if t.get("status", "") == selected_status]
        
        # Pagination calculations
        self.total_pages_outgoing = max(1, (len(filtered_transactions) + self.per_page_outgoing - 1) // self.per_page_outgoing)
        start_idx = (self.current_page_outgoing - 1) * self.per_page_outgoing
        end_idx = start_idx + self.per_page_outgoing
        paginated_transactions = filtered_transactions[start_idx:end_idx]
        
        # Update table
        self.transactions_table.setRowCount(len(paginated_transactions))
        
        for i, transaction in enumerate(paginated_transactions):
            # Set all columns IN ORDER
            self.transactions_table.setItem(i, 0, QTableWidgetItem(str(transaction.get("id", ""))))  # Col 0
            self.transactions_table.setItem(i, 1, QTableWidgetItem(self.format_date(transaction.get("date", ""))))  # Col 1
            self.transactions_table.setItem(i, 2, QTableWidgetItem(transaction.get("sender", "")))  # Col 2
            self.transactions_table.setItem(i, 3, QTableWidgetItem(transaction.get("receiver", "")))  # Col 3
            self.transactions_table.setItem(i, 4, QTableWidgetItem(self.format_amount(transaction.get("amount", 0))))  # Col 4
            self.transactions_table.setItem(i, 5, QTableWidgetItem(transaction.get("currency", "")))  # Col 5
            self.transactions_table.setItem(i, 6, QTableWidgetItem(transaction.get("receiver_governorate", "")))  # Col 6
            
            # Status - Col 7
            status = transaction.get("status", "pending")
            status_item = QTableWidgetItem(self.get_status_arabic(status))
            status_item.setBackground(self.get_status_color(status))
            self.transactions_table.setItem(i, 7, status_item)
            
            # Type - Col 8
            type_item = self.create_type_item(transaction)
            self.transactions_table.setItem(i, 8, type_item)
            
            # Remaining columns
            self.transactions_table.setItem(i, 9, QTableWidgetItem(transaction.get("employee_name", "")))  # Col 9
            self.transactions_table.setItem(i, 10, QTableWidgetItem(transaction.get("sending_branch_name", "غير معروف")))  # Col 10
            self.transactions_table.setItem(i, 11, QTableWidgetItem(transaction.get("destination_branch_name", "غير معروف")))  # Col 11
            self.transactions_table.setItem(i, 12, QTableWidgetItem(transaction.get("branch_governorate", "")))  # Col 12
        
        self.count_label.setText(
            f"عدد التحويلات: {len(filtered_transactions)} "
            f"(الصفحة {self.current_page_outgoing}/{self.total_pages_outgoing})"
        )
        self.update_pagination_controls_outgoing()


    # Helper methods
    def format_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            return date_str

    def format_amount(self, amount):
        return f"{float(amount):,.2f}" if amount else "0.00"

    def create_type_item(self, transaction):
        transfer_type = ""
        color = QColor()
        
        # For outgoing transactions
        if transaction.get("branch_id") == self.branch_id:
            transfer_type = "↑ صادر"  # Outgoing
            color = QColor(0, 150, 0)  # Dark green
        # For incoming transactions (shouldn't appear in outgoing tab)
        elif transaction.get("destination_branch_id") == self.branch_id:
            transfer_type = "↓ وارد"  # Incoming
            color = QColor(150, 0, 0)  # Dark red
        else:
            transfer_type = "غير معروف"
            color = QColor(100, 100, 100)
        
        item = QTableWidgetItem(transfer_type)
        item.setForeground(color)
        item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        return item
    
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
    
    def clear_form(self):
        """Clear the new transfer form."""
        # Clear sender information
        self.sender_name_input.clear()
        self.sender_mobile_input.clear()
        self.sender_id_input.clear()
        self.sender_address_input.clear()
        self.sender_location_input.clear()
        
        # Clear receiver information
        self.receiver_name_input.clear()
        self.receiver_mobile_input.clear()
        self.receiver_governorate_input.setCurrentIndex(0)
        
        # Clear transfer information
        self.amount_input.setValue(0)
        self.benefited_input.setValue(0)
        self.currency_input.setCurrentIndex(0)
        self.date_input.setDate(QDate.currentDate())
        self.notes_input.clear()
    
    def show_confirmation(self):
        """Show confirmation dialog before submitting transfer."""
        if not self.validate_transfer_form():
            return
        
        # Prepare data
        data = self.prepare_transfer_data()
        
        # Safely extract currency code
        currency_text = data["currency"]
        try:
            # Try to extract code from parentheses
            currency_code = currency_text.split("(")[1].split(")")[0]
        except IndexError:
            # If no parentheses, use the full text
            currency_code = currency_text
        
        confirm_dialog = ConfirmTransactionDialog(
            parent=self,
            sender=data["sender"],
            sender_mobile=data["sender_mobile"],
            sender_governorate=data["sender_governorate"],
            sender_location=data["sender_location"],
            receiver=data["receiver"],
            receiver_mobile=data["receiver_mobile"],
            receiver_governorate=data["receiver_governorate"],
            amount=str(data["amount"]),
            currency=currency_code,
            message=data["message"],
            employee_name=data["employee_name"],
            branch_governorate=data["branch_governorate"]
        )

        if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
            self.submit_transfer()
    
    def submit_transfer(self):
        """Submit the transfer for processing."""
        # Prepare data
        data = self.prepare_transfer_data()
        data["status"] = "processing"
        
        # Debug print
        print("Data being sent:", data)
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.post(f"{self.api_url}/transactions/", json=data, headers=headers)
            
            if response.status_code == 201:
                QMessageBox.information(self, "نجاح", "تم إرسال التحويل بنجاح")
                self.clear_form()
                self.load_transactions()
                self.load_notifications()
                # Update balance and notify parent
                self.update_current_balance()
                self.transferCompleted.emit()  # Emit signal to update dashboard
            else:
                # Print the full error response
                print("Error response:", response.text)
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
                QMessageBox.warning(self, "خطأ", error_msg)
        except Exception as e:
            print(f"Error submitting transfer: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                            "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def save_transfer(self):
        """Save the transfer as a draft."""
        # Validate required fields
        if not self.validate_transfer_form():
            return
        
        # Prepare data
        data = self.prepare_transfer_data()
        data["status"] = "pending"  # Draft status
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.post(f"{self.api_url}/transactions/", json=data, headers=headers)
            
            if response.status_code == 201:
                QMessageBox.information(self, "نجاح", "تم حفظ التحويل بنجاح")
                self.clear_form()
                self.load_transactions()
            else:
                error_msg = f"فشل إرسال التحويل: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        details = error_data["detail"]
                        if isinstance(details, list):
                            # Convert each error into a readable string
                            error_msg = "\n".join([f"{err.get('loc', [''])[-1]}: {err.get('msg', '')}" for err in details])
                        else:
                            error_msg = details
                except:
                    pass
                QMessageBox.warning(self, "خطأ", error_msg)
        
        # Add missing except block for the outer try
        except Exception as e:
            print(f"Error saving transfer: {e}")
            QMessageBox.critical(self, "خطأ في الاتصال", 
                            "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم.")
    
    def validate_transfer_form(self):
        """Validate the transfer form with balance checks and enhanced validation"""
        # Validate sender information
        if not self.sender_name_input.text().strip():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم المرسل الصحيح")
            return False
        
        sender_mobile = self.sender_mobile_input.text().strip()
        if len(sender_mobile) != 10 or not sender_mobile.isdigit():
            QMessageBox.warning(self, "خطأ", "رقم هاتف المرسل يجب أن يكون 10 أرقام فقط")
            return False
        
        # Validate receiver information
        receiver_name = self.receiver_name_input.text().strip()
        if not receiver_name or len(receiver_name) < 4:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم مستلم صحيح (4 أحرف على الأقل)")
            return False
        
        receiver_mobile = self.receiver_mobile_input.text().strip()
        if len(receiver_mobile) != 10 or not receiver_mobile.isdigit():
            QMessageBox.warning(self, "خطأ", "رقم هاتف المستلم يجب أن يكون 10 أرقام فقط")
            return False
        
        # Validate amount
        base_amount = self.amount_input.value()
        benefited_amount = self.benefited_input.value()
        total_amount = base_amount + benefited_amount
        
        if total_amount <= 0:
            QMessageBox.warning(self, "خطأ", "المبلغ الإجمالي يجب أن يكون أكبر من الصفر")
            return False
        
        # Validate branch selection
        if self.branch_input.currentData() in [-1, None]:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع مستلم صحيح من القائمة")
            return False
        
        # Get currency code
        currency_text = self.currency_input.currentText()
        if "(" not in currency_text or ")" not in currency_text:
            QMessageBox.warning(self, "خطأ", "تنسيق العملة غير صحيح")
            return False
        currency_code = currency_text.split("(")[1].split(")")[0]
        
        # Skip balance check for System Manager
        if self.branch_id == 0 or self.full_name == "System Manager":
            # System Manager has unlimited funds, no need to check balance
            pass
        else:
            # Hidden balance check through API for regular branches
            try:
                headers = {"Authorization": f"Bearer {self.user_token}"}
                response = requests.get(
                    f"{self.api_url}/branches/{self.branch_id}",
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    branch_data = response.json()
                    financial_stats = branch_data.get("financial_stats", {})
                    
                    # Check balance based on currency
                    if currency_code == "SYP":
                        available_balance = financial_stats.get("available_balance_syp", financial_stats.get("available_balance", 0))
                    elif currency_code == "USD":
                        available_balance = financial_stats.get("available_balance_usd", 0)
                    else:
                        # For other currencies, default to SYP balance
                        available_balance = financial_stats.get("available_balance_syp", financial_stats.get("available_balance", 0))
                    
                    if total_amount > available_balance:
                        QMessageBox.warning(
                            self, 
                            "رصيد غير كافي",
                            f"لا يوجد رصيد كافي بعملة {currency_code} لإتمام هذه العملية\nالرجاء التواصل مع المدير"
                        )
                        return False
                else:
                    QMessageBox.warning(
                        self,
                        "خطأ في التحقق",
                        "تعذر التحقق من الرصيد المتاح. الرجاء المحاولة لاحقاً"
                    )
                    return False
                    
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "خطأ في الاتصال",
                    "تعذر الاتصال بالخادم. الرجاء التحقق من اتصال الإنترنت"
                )
                return False
        
        # Validate employee information
        # Special handling for System Manager account
        if self.branch_id == 0 or self.user_role == "director" or self.full_name == "System Manager":
            # System Manager is always valid, no need to verify employee information
            pass
        elif not self.username or not self.branch_id:
            QMessageBox.warning(self, "خطأ", "تعذر التحقق من معلومات الموظف")
            return False

        return True
    
    def prepare_transfer_data(self):
        """Prepare transfer data for submission."""
        # Calculate total amount
        dest_branch_id = self.branch_input.currentData()
        base_amount = self.amount_input.value()
        benefited_amount = self.benefited_input.value()
        total_amount = base_amount + benefited_amount

        # Get current branch info
        current_branch_name = self.current_branch_label.text().split(" - ")[0]
        current_branch_governorate = self.sender_governorate_label.text()
        
        # Extract currency code from the display text
        currency_text = self.currency_input.currentText()
        currency_code = currency_text.split("(")[1].split(")")[0]

        data = {
            "sender": self.sender_name_input.text(),
            "sender_mobile": self.sender_mobile_input.text(),
            "sender_id": self.sender_id_input.text(),
            "sender_address": self.sender_address_input.text(),
            "sender_governorate": current_branch_governorate,
            "sender_location": self.sender_location_input.text(),
            "receiver": self.receiver_name_input.text(),
            "receiver_mobile": self.receiver_mobile_input.text(),
            "receiver_governorate": self.receiver_governorate_input.currentText(),
            "receiver_location": "",  # Empty string if not needed
            "amount": total_amount,
            "base_amount": base_amount,
            "benefited_amount": benefited_amount,
            "currency": currency_code,
            "message": self.notes_input.toPlainText(),
            "employee_name": self.username,
            "branch_name": current_branch_name,
            "branch_governorate": current_branch_governorate,
            "destination_branch_id": dest_branch_id,
            "branch_id": self.branch_id
        }
        return data
    
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
        selected_items = self.transactions_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "تحذير", "الرجاء تحديد تحويل لتحديث حالته")
            return
        
        row = selected_items[0].row()
        transaction_id = self.transactions_table.item(row, 0).text()
        
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
    
    def print_transaction(self, item):
        """Handle transaction double-click to print."""
        try:
            row = item.row()
            transaction_data = {
                "id": self.transactions_table.item(row, 0).text(),
                "date": self.transactions_table.item(row, 1).text(),
                "sender": self.transactions_table.item(row, 2).text(),
                "receiver": self.transactions_table.item(row, 3).text(),
                "amount": self.transactions_table.item(row, 4).text(),
                "currency": self.transactions_table.item(row, 5).text(),
                "receiver_governorate": self.transactions_table.item(row, 6).text(),
                "status": self.transactions_table.item(row, 7).text(),
                "employee_name": self.transactions_table.item(row, 8).text(),
                "sending_branch": self.transactions_table.item(row, 9).text(),
                "destination_branch": self.transactions_table.item(row, 10).text(),
                "branch_governorate": self.transactions_table.item(row, 11).text()
            }
            
            # Format transaction ID with dashes like in the image (1925-5814-5221)
            # If the ID is numeric, format it with dashes
            formatted_id = transaction_data['id']
            if transaction_data['id'].isdigit() and len(transaction_data['id']) >= 4:
                id_parts = []
                id_str = transaction_data['id']
                while id_str:
                    if len(id_str) > 4:
                        id_parts.append(id_str[:4])
                        id_str = id_str[4:]
                    else:
                        id_parts.append(id_str)
                        id_str = ""
                formatted_id = "-".join(id_parts)
            
            # Convert amount to Arabic words
            amount_in_arabic = number_to_arabic_words(transaction_data['amount'], transaction_data['currency'])
            
            # Create print dialog
            print_dialog = QDialog(self)
            print_dialog.setWindowTitle("طباعة التحويل")
            print_dialog.setFixedSize(600, 700)
            
            layout = QVBoxLayout()
            
            # Create printable content with improved layout
            content = QTextEdit()
            content.setReadOnly(True)
            content.setHtml(f"""
                <div style='font-family: Arial; direction: rtl; background-color: #f9f9f9; padding: 0; margin: 0;'>
                    <!-- Header -->
                    <div style='text-align: right; padding: 10px; background-color: #e8f5e9; border-bottom: 1px solid #ddd;'>
                        <h2 style='margin: 0; color: #333;'>طباعة التحويل</h2>
                    </div>
                    
                    <!-- Transaction Number Row -->
                    <div style='margin: 15px 0; text-align: center;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #333;'>الرقم</strong>
                            </div>
                            <div style='flex: 3; text-align: center;'>
                                <strong style='font-size: 16px;'>{formatted_id}</strong>
                            </div>
                            <div style='flex: 1; text-align: center; background-color: #e8f5e9; padding: 5px; border-radius: 4px;'>
                                <strong style='color: #2e7d32;'>إرسال</strong>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Main Content -->
                    <div style='margin: 0 10px;'>
                        <!-- From/To Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>من</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['sending_branch']}
                            </div>
                        </div>
                        
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>إلى</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['destination_branch']}
                            </div>
                        </div>
                        
                        <!-- Sender Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>المرسل</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['sender']}
                            </div>
                        </div>
                        
                        <!-- Receiver Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>المفوض</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['receiver']}
                            </div>
                        </div>
                        
                        <!-- Contact Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>اتصال</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data.get('receiver_mobile', '')}
                            </div>
                        </div>
                        
                        <!-- Beneficiary Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>المستفيد</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['receiver']}
                            </div>
                        </div>
                        
                        <!-- Recipient Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>المستلم</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['receiver']}
                            </div>
                        </div>
                        
                        <!-- Contact (Phone) Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>اتصال</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data.get('receiver_mobile', '')}
                            </div>
                        </div>
                        
                        <!-- Date Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>التاريخ</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['date']}
                            </div>
                        </div>
                        
                        <!-- Amount Row -->
                        <div style='display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 8px;'>
                            <div style='flex: 1; text-align: right;'>
                                <strong style='color: #555;'>المبلغ</strong>
                            </div>
                            <div style='flex: 5; text-align: left;'>
                                {transaction_data['amount']} {transaction_data['currency']}
                            </div>
                        </div>
                        
                        <!-- Amount in Words Row -->
                        <div style='margin-bottom: 15px; padding: 8px; background-color: #f5f5f5; border-radius: 4px;'>
                            <p style='margin: 0; text-align: right; color: #333;'>
                                {amount_in_arabic}
                            </p>
                        </div>
                    </div>
                    
                    <!-- Footer Note -->
                    <div style='margin: 15px 0; text-align: center; color: #4CAF50; font-weight: bold;'>
                        <p>يطلب تبليغ المستفيد برقم الحوالة</p>
                    </div>
                    
                    <!-- System Section -->
                    <hr style='border: none; border-top: 1px solid #ddd; margin: 20px 0;'>
                    
                    <div style='text-align: right; margin: 0 10px;'>
                        <h3 style='color: #4CAF50; margin-bottom: 15px;'>نسخة النظام</h3>
                        
                        <div style='margin-bottom: 8px;'>
                            <strong style='color: #555;'>بيانات فرع المرسل:</strong>
                            <span style='margin-right: 10px;'>{transaction_data['sending_branch']}</span>
                        </div>
                        
                        <div style='margin-bottom: 8px;'>
                            <strong style='color: #555;'>بيانات فرع المستلم:</strong>
                            <span style='margin-right: 10px;'>{transaction_data['destination_branch']} - {transaction_data['branch_governorate']}</span>
                        </div>
                        
                        <div style='margin-bottom: 8px;'>
                            <strong style='color: #555;'>اسم الموظف:</strong>
                            <span style='margin-right: 10px;'>{transaction_data['employee_name']}</span>
                        </div>
                        
                        <div style='margin-bottom: 8px;'>
                            <strong style='color: #555;'>نوع التحويل:</strong>
                            <span style='margin-right: 10px;'>تحويل صادر</span>
                        </div>
                        
                        <div style='margin-bottom: 8px;'>
                            <strong style='color: #555;'>حالة التحويل:</strong>
                            <span style='margin-right: 10px;'>{transaction_data['status']}</span>
                        </div>
                        
                        <div style='margin-top: 30px; border-top: 1px dashed #ddd; padding-top: 15px;'>
                            <p><strong>اسم العميل الكامل:</strong> ________________________</p>
                            <p><strong>التوقيع:</strong> ________________________</p>
                        </div>
                    </div>
                </div>
            """)
            
            # Print button
            print_btn = ModernButton("طباعة", color="#4CAF50")
            print_btn.clicked.connect(lambda: self.send_to_printer(content))
            
            layout.addWidget(content)
            layout.addWidget(print_btn)
            print_dialog.setLayout(layout)
            print_dialog.exec()

        except Exception as e:
            print(f"Printing error: {str(e)}")
            QMessageBox.warning(self, "خطأ في الطباعة", "حدث خطأ أثناء تحضير البيانات للطباعة")
            
            # Print button
            print_btn = ModernButton("طباعة", color="#27ae60")
            print_btn.clicked.connect(lambda: self.send_to_printer(content))
            
            layout.addWidget(content)
            layout.addWidget(print_btn)
            print_dialog.setLayout(layout)
            print_dialog.exec()

        except Exception as e:
            print(f"Printing error: {str(e)}")
            QMessageBox.warning(self, "خطأ في الطباعة", "حدث خطأ أثناء تحضير البيانات للطباعة")

    def send_to_printer(self, content):
        """Handle actual printing functionality."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        
        printer = QPrinter()
        print_dialog = QPrintDialog(printer, self)
        
        if print_dialog.exec() == QDialog.DialogCode.Accepted:
            content.print(printer)
    
    def open_search_dialog(self):
        """Open the search dialog."""
        search_dialog = UserSearchDialog(token=self.user_token, parent=self)
        search_dialog.exec()

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
        sender_name_value = QLabel(self.transaction.get("sender_name", ""))
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
        sender_address_value = QLabel(self.transaction.get("sender_address", ""))
        sender_layout.addRow(sender_address_label, sender_address_value)
        
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)
        
        # Receiver info group
        receiver_group = QGroupBox("معلومات المستلم")
        receiver_layout = QFormLayout()
        
        # Receiver name
        receiver_name_label = QLabel("الاسم:")
        receiver_name_value = QLabel(self.transaction.get("receiver_name", ""))
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
        receiver_address_value = QLabel(self.transaction.get("receiver_address", ""))
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
        branch_label = QLabel("الفرع المرسل:")
        branch_value = QLabel(self.transaction.get("sending_branch_name", ""))
        additional_layout.addRow(branch_label, branch_value)
        
        # Destination branch
        dest_branch_label = QLabel("الفرع المستلم:")
        dest_branch_value = QLabel(self.transaction.get("destination_branch_name", ""))
        additional_layout.addRow(dest_branch_label, dest_branch_value)
        
        # Add currency
        currency_label = QLabel("العملة:")
        currency_value = QLabel(self.transaction.get("currency", ""))
        currency_value.setStyleSheet("font-weight: bold;")
        transaction_layout.addRow(currency_label, currency_value)
        
        # Add branch governorate
        branch_gov_label = QLabel("محافظة الفرع:")
        branch_gov_value = QLabel(self.transaction.get("branch_governorate", ""))
        branch_gov_value.setStyleSheet("font-weight: bold;")
        transaction_layout.addRow(branch_gov_label, branch_gov_value)
            
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
        """Print the transaction details."""
        # Create printable content
        printer = QPrinter()
        print_dialog = QPrintDialog(printer, self)
        
        if print_dialog.exec() == QDialog.DialogCode.Accepted:
            # Create a temporary widget to hold the print content
            print_widget = QTextEdit()
            print_widget.setHtml(f"""
                <div style='text-align: center; font-family: Arial;'>
                    <h1 style='color: #2c3e50;'>تفاصيل التحويل</h1>
                    <hr>
                    <div style='text-align: right;'>
                        <p><b>رقم التحويل:</b> {self.transaction.get('id', '')}</p>
                        <p><b>التاريخ:</b> {self.transaction.get('date', '')}</p>
                        <h3 style='color: #e74c3c;'>المرسل:</h3>
                        <p>{self.transaction.get('sender_name', '')}</p>
                        <p>الهاتف: {self.transaction.get('sender_mobile', '')}</p>
                        <p>الهوية: {self.transaction.get('sender_id', '')}</p>
                        <p>العنوان: {self.transaction.get('sender_address', '')}</p>
                        <h3 style='color: #3498db;'>المستلم:</h3>
                        <p>{self.transaction.get('receiver_name', '')}</p>
                        <p>الهاتف: {self.transaction.get('receiver_mobile', '')}</p>
                        <p>الهوية: {self.transaction.get('receiver_id', '')}</p>
                        <p>العنوان: {self.transaction.get('receiver_address', '')}</p>
                        <p><b>المبلغ:</b> {self.transaction.get('amount', '')}</p>
                        <p><b>حالة التحويل:</b> {self.get_status_arabic(self.transaction.get('status', ''))}</p>
                        <p><b>الموظف:</b> {self.transaction.get('employee_name', '')}</p>
                        <p><b>الفرع:</b> {self.transaction.get('branch_name', '')}</p>
                        <p><b>ملاحظات:</b> {self.transaction.get('notes', '')}</p>
                        <hr>
                        <p style='color: #95a5a6;'>شكراً لاستخدامكم خدماتنا</p>
                    </div>
                </div>
            """)
            print_widget.print(printer)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MoneyTransferApp()
    window.show()
    sys.exit(app.exec())
