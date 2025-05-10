import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QDialog, QGroupBox, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QDate, QTimer, QThread, pyqtSignal
from ui.custom_widgets import ModernGroupBox, ModernButton
from ui.theme import Theme
import os
from typing import Optional, Dict, List
from decimal import Decimal
import logging
from config import get_api_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApiWorker(QThread):
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(Exception)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._result = None
        self._error = None
    def run(self):
        try:
            self._result = self.func(*self.args, **self.kwargs)
            self.result_ready.emit(self._result)
        except Exception as e:
            self._error = e
            self.error_occurred.emit(e)

class InventoryTab(QWidget):
    """Inventory tab for tracking receivables and profits from branches."""
    
    def __init__(self, token: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.token = token
        self.api_url = get_api_url()
        
        # Initialize update flags
        self.is_updating = False
        self.update_pending = False
        
        # Cache for branch data
        self.branch_cache = None  # None تعني لم يتم الجلب بعد
        
        # Initialize summary labels
        self.tax_collected_label = QLabel("0")
        self.transactions_count_label = QLabel("0")
        self.total_profit_label = QLabel("0")
        self.avg_tax_label = QLabel("0%")
        
        self.setup_ui()
        
        # Initialize data
        try:
            self.load_branches()
        except Exception as e:
            print(f"Error initializing UI data: {str(e)}")
            self._handle_unexpected_error(e)
        # Load initial data for the inventory tab
        try:
            self.load_data()
        except Exception as e:
            print(f"Error loading initial inventory data: {str(e)}")
            self._handle_unexpected_error(e)
        
    def setup_ui(self):
        """Set up the UI components with optimized settings."""
        layout = QVBoxLayout()
        self._setup_title(layout)
        self._setup_filter_controls(layout)
        self._setup_summary_section(layout)
        
        # Create horizontal layout for tax and profit tables
        tables_layout = QHBoxLayout()
        
        # Tax details table (full width)
        tax_details_container = QWidget()
        tax_details_layout = QVBoxLayout(tax_details_container)
        self._setup_tax_table(tax_details_layout)
        tables_layout.addWidget(tax_details_container)
        
        layout.addLayout(tables_layout)
        
        # Transaction details at the bottom
        self._setup_transaction_details(layout)
        
        # Add status bar at the bottom
        status_layout = QHBoxLayout()
        self.status_label = QLabel("جاهز")
        self.status_label.setStyleSheet(Theme.LABEL_STYLE)
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
        
        # Apply theme to widget
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_PRIMARY};
                color: {Theme.TEXT_PRIMARY};
                font-family: {Theme.FONT_PRIMARY};
                font-size: {Theme.FONT_SIZE_NORMAL};
            }}
        """)
        
    def _setup_title(self, layout: QVBoxLayout):
        """Set up the title section."""
        title = QLabel("المخزون والأرباح")
        title.setFont(QFont(Theme.FONT_PRIMARY, int(Theme.FONT_SIZE_TITLE[:-2]), QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                margin-bottom: 20px;
            }}
        """)
        layout.addWidget(title)
        
    def _setup_filter_controls(self, layout: QVBoxLayout):
        """Set up the filter controls with improved organization."""
        filter_group = ModernGroupBox("تصفية البيانات", Theme.ACCENT)
        filter_layout = QHBoxLayout()
        
        # Date filters
        self._add_date_filters(filter_layout)
        
        # Branch and currency filters
        self._add_branch_currency_filters(filter_layout)
        
        # Status filter
        status_label = QLabel("الحالة:")
        status_label.setStyleSheet(Theme.LABEL_STYLE)
        filter_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.setStyleSheet(Theme.INPUT_STYLE)
        self.status_filter.addItem("الكل", "all")
        self.status_filter.addItem("قيد المعالجة", "processing")
        self.status_filter.addItem("مكتمل", "completed")
        self.status_filter.addItem("ملغي", "cancelled")
        filter_layout.addWidget(self.status_filter)
        
        # Apply filter button
        filter_button = ModernButton("تطبيق", color=Theme.SUCCESS)
        filter_button.clicked.connect(self._apply_filters)
        filter_layout.addWidget(filter_button)
        
        # Refresh data button (بيانات المخزون فقط)
        refresh_button = ModernButton("تحديث البيانات", color=Theme.ACCENT)
        refresh_button.clicked.connect(self._refresh_data)
        filter_layout.addWidget(refresh_button)
        
        # Refresh branches button (تحديث الفروع فقط)
        refresh_branches_button = ModernButton("تحديث الفروع", color=Theme.WARNING)
        refresh_branches_button.clicked.connect(self.refresh_branches)
        filter_layout.addWidget(refresh_branches_button)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
    def _add_date_filters(self, layout: QHBoxLayout):
        """Add date filter controls."""
        date_from_label = QLabel("من تاريخ:")
        date_from_label.setStyleSheet(Theme.LABEL_STYLE)
        layout.addWidget(date_from_label)
        
        self.date_from = QDateEdit()
        self.date_from.setStyleSheet(Theme.INPUT_STYLE)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        layout.addWidget(self.date_from)
        
        date_to_label = QLabel("إلى تاريخ:")
        date_to_label.setStyleSheet(Theme.LABEL_STYLE)
        layout.addWidget(date_to_label)
        
        self.date_to = QDateEdit()
        self.date_to.setStyleSheet(Theme.INPUT_STYLE)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        layout.addWidget(self.date_to)
        
    def _add_branch_currency_filters(self, layout: QHBoxLayout):
        """Add branch and currency filter controls."""
        branch_label = QLabel("الفرع:")
        branch_label.setStyleSheet(Theme.LABEL_STYLE)
        layout.addWidget(branch_label)
        
        self.branch_filter = QComboBox()
        self.branch_filter.setStyleSheet(Theme.INPUT_STYLE)
        self.branch_filter.addItem("جميع الفروع", "all")
        layout.addWidget(self.branch_filter)
        
        currency_label = QLabel("العملة:")
        currency_label.setStyleSheet(Theme.LABEL_STYLE)
        layout.addWidget(currency_label)
        
        self.currency_filter = QComboBox()
        self.currency_filter.setStyleSheet(Theme.INPUT_STYLE)
        self.currency_filter.addItems(["الكل", "ليرة سورية (SYP)", "دولار أمريكي (USD)"])
        layout.addWidget(self.currency_filter)
        
    def _setup_summary_section(self, layout: QVBoxLayout):
        """Set up the tax summary section with statistics."""
        summary_group = ModernGroupBox("ملخص الضرائب والأرباح", Theme.ACCENT)
        summary_layout = QHBoxLayout()
        
        # Create summary widgets with themed styles
        summary_widgets = [
            ("إجمالي الضرائب المحصلة", self.tax_collected_label, Theme.ERROR),
            ("عدد التحويلات", self.transactions_count_label, Theme.ACCENT),
            ("إجمالي الأرباح", self.total_profit_label, Theme.SUCCESS),
            ("متوسط نسبة الضريبة", self.avg_tax_label, Theme.WARNING)
        ]
        
        for title, label, color in summary_widgets:
            widget = QWidget()
            widget_layout = QVBoxLayout()
            
            label.setFont(QFont(Theme.FONT_PRIMARY, int(Theme.FONT_SIZE_XLARGE[:-2]), QFont.Weight.Bold))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {color};")
            widget_layout.addWidget(label)
            
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setStyleSheet(Theme.LABEL_STYLE)
            widget_layout.addWidget(title_label)
            
            widget.setLayout(widget_layout)
            summary_layout.addWidget(widget)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
    def _setup_tax_table(self, layout):
        """Set up the tax details table."""
        # Create and configure the tax table
        tax_label = QLabel("تفاصيل الضريبة")
        tax_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: {Theme.FONT_SIZE_LARGE};
                font-weight: bold;
                margin: 10px 0;
            }}
        """)
        layout.addWidget(tax_label)
        
        self.tax_table = QTableWidget()
        self.tax_table.setColumnCount(8)
        self.tax_table.setHorizontalHeaderLabels([
            "الفرع", "نسبة الضريبة", "عدد التحويلات",
            "إجمالي المبلغ", "المبلغ المستفاد", "مبلغ الضريبة",
            "الربح", "العملة"
        ])
        self.tax_table.setStyleSheet(Theme.TABLE_STYLE)
        
        # Set table properties
        self.tax_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tax_table.verticalHeader().setVisible(False)
        self.tax_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.tax_table)
        
    def _setup_transaction_details(self, layout):
        """Set up the transaction details section."""
        transactions_label = QLabel("تفاصيل التحويلات")
        transactions_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: {Theme.FONT_SIZE_LARGE};
                font-weight: bold;
                margin: 10px 0;
            }}
        """)
        layout.addWidget(transactions_label)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(9)
        self.transactions_table.setHorizontalHeaderLabels([
            "رقم التحويل", "التاريخ", "المبلغ", "المبلغ المستفاد",
            "نسبة الضريبة", "مبلغ الضريبة", "العملة",
            "الفرع المرسل", "الفرع المستلم", "الحالة"
        ])
        self.transactions_table.setStyleSheet(Theme.TABLE_STYLE)
        
        # Set table properties
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.transactions_table)

    def optimize_table(self, table):
        """Apply performance optimizations to tables."""
        # Reduce visual updates during data loading
        table.setUpdatesEnabled(False)
        
        # Optimize rendering
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        # Optimize header
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Batch row operations
        table.setRowCount(0)
        
        # Enable updates after setup
        table.setUpdatesEnabled(True)

    def show_loading(self, message="جاري تحميل البيانات..."):
        if not hasattr(self, '_loading_label') or self._loading_label is None:
            self._loading_label = QLabel(message, self)
            self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._loading_label.setStyleSheet("background: #fffbe6; color: #e67e22; font-size: 16px; padding: 20px; border-radius: 10px;")
            self._loading_label.setGeometry(0, 0, self.width(), 60)
            self._loading_label.show()
            self.repaint()
    def hide_loading(self):
        if hasattr(self, '_loading_label') and self._loading_label:
            self._loading_label.hide()
            self._loading_label.deleteLater()
            self._loading_label = None
    def set_filter_buttons_enabled(self, enabled: bool):
        for btn_text in ["تطبيق", "تحديث البيانات", "تحديث الفروع"]:
            btns = self.findChildren(ModernButton, btn_text)
            for btn in btns:
                btn.setEnabled(enabled)

    def load_data(self):
        """Load data with optimized performance using QThread and loading indicator."""
        if self.is_updating:
            self.update_pending = True
            return
        self.is_updating = True
        try:
            self.show_loading("جاري تحميل بيانات المخزون...")
            self.set_filter_buttons_enabled(False)
            # Prepare parameters as before
            start_date = self.date_from.date().toString("yyyy-MM-dd")
            end_date = self.date_to.date().toString("yyyy-MM-dd")
            selected_branch_id = self.branch_filter.currentData()
            currency_text = self.currency_filter.currentText()
            currency = None
            if currency_text == "ليرة سورية (SYP)":
                currency = "SYP"
            elif currency_text == "دولار أمريكي (USD)":
                currency = "USD"
            status = self.status_filter.currentData()
            if status == "all":
                status = None
            params = {"start_date": start_date, "end_date": end_date}
            if selected_branch_id and selected_branch_id != "all":
                params["branch_id"] = selected_branch_id
            if currency:
                params["currency"] = currency
            if status:
                params["status"] = status
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            def api_call():
                return requests.get(
                    f"{self.api_url}/api/transactions/tax_summary/",
                    params=params,
                    headers=headers,
                    timeout=30
                )
            self.data_worker = ApiWorker(api_call)
            self.data_worker.result_ready.connect(self._on_data_loaded)
            self.data_worker.error_occurred.connect(self._handle_unexpected_error)
            self.data_worker.finished.connect(lambda: (self.hide_loading(), self.set_filter_buttons_enabled(True)))
            self.data_worker.start()
        except Exception as e:
            self._handle_unexpected_error(e)
            self.is_updating = False
            self.hide_loading()
            self.set_filter_buttons_enabled(True)
            if self.update_pending:
                self.update_pending = False
                QTimer.singleShot(1000, self.load_data)

    def _on_data_loaded(self, response):
        try:
            if response.status_code == 200:
                data = response.json()
                self._process_tax_data(data)
                self.status_label.setText("تم تحديث البيانات بنجاح")
            else:
                logger.error(f"Error Response: {response.text}")
                print(f"Error Response Text: {response.text}")
                self._handle_api_error(response)
        except Exception as e:
            self._handle_unexpected_error(e)
        finally:
            self.is_updating = False
            if self.update_pending:
                self.update_pending = False
                QTimer.singleShot(1000, self.load_data)

    def _process_tax_data(self, data):
        """Process tax data with optimized performance."""
        try:
            # Disable updates while processing
            self.tax_table.setUpdatesEnabled(False)
            self.transactions_table.setUpdatesEnabled(False)
            
            # Update summary labels
            total_amount = float(data.get('total_amount', 0))
            total_benefited = float(data.get('total_benefited_amount', 0))
            total_tax = float(data.get('total_tax_amount', 0))
            total_transactions = data.get('total_transactions', 0)
            total_profit = float(data.get('total_profit', 0))
            
            # Calculate average tax rate
            avg_tax_rate = (total_tax / total_benefited * 100) if total_benefited > 0 else 0
            
            self.tax_collected_label.setText(f"{total_tax:,.2f}")
            self.transactions_count_label.setText(f"{total_transactions:,}")
            self.total_profit_label.setText(f"{total_profit:,.2f}")  # عرض الربح الحقيقي
            self.avg_tax_label.setText(f"{avg_tax_rate:.2f}%")
            
            # Update tax table
            branch_summary = data.get('branch_summary', [])
            if not branch_summary:
                self.tax_table.setRowCount(0)
                self.tax_table.setUpdatesEnabled(True)
                self.tax_table.viewport().update()
                # Also clear transactions table if needed
                transactions = data.get('transactions', [])
                if not transactions:
                    self.transactions_table.setRowCount(0)
                    self.transactions_table.setUpdatesEnabled(True)
                    self.transactions_table.viewport().update()
                return
            self.tax_table.setRowCount(len(branch_summary))
            
            for i, branch in enumerate(branch_summary):
                items = [
                    branch.get('branch_name', ''),
                    f"{branch.get('tax_rate', 0):.2f}%",
                    str(branch.get('transaction_count', 0)),
                    f"{branch.get('total_amount', 0):,.2f}",
                    f"{branch.get('benefited_amount', 0):,.2f}",
                    f"{branch.get('tax_amount', 0):,.2f}",
                    f"{branch.get('profit', 0):,.2f}",  # عرض الربح الصحيح
                    branch.get('currency', '')
                ]
                if i < self.tax_table.rowCount():
                    for j, value in enumerate(items):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        if j in [3, 4, 5, 6]:  # Money columns
                            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        self.tax_table.setItem(i, j, item)
            
            # Update transactions table
            transactions = data.get('transactions', [])
            if not transactions:
                self.transactions_table.setRowCount(0)
                self.transactions_table.setUpdatesEnabled(True)
                self.transactions_table.viewport().update()
            else:
                self.transactions_table.setRowCount(len(transactions))
                
                for i, tx in enumerate(transactions):
                    status = tx.get('status', '')
                    status_color = self._get_status_color(status)
                    status_text = self._get_status_text(status)
                    items = [
                        tx.get('id', ''),
                        tx.get('date', ''),
                        f"{tx.get('amount', 0):,.2f}",
                        f"{tx.get('benefited_amount', 0):,.2f}",
                        f"{tx.get('tax_rate', 0):.2f}%",
                        f"{tx.get('tax_amount', 0):,.2f}",
                        tx.get('currency', ''),
                        tx.get('source_branch', ''),
                        tx.get('destination_branch', ''),
                        status_text,
                        f"{tx.get('profit', 0):,.2f}"  # عرض الربح لكل عملية
                    ]
                    # إذا كان الجدول لا يحتوي على عمود ربح أضفه (للتوافق)
                    if self.transactions_table.columnCount() < 11:
                        self.transactions_table.setColumnCount(11)
                        self.transactions_table.setHorizontalHeaderLabels([
                            "رقم التحويل", "التاريخ", "المبلغ", "المبلغ المستفاد",
                            "نسبة الضريبة", "مبلغ الضريبة", "العملة",
                            "الفرع المرسل", "الفرع المستلم", "الحالة", "الربح"
                        ])
                    if i < self.transactions_table.rowCount():
                        for j, value in enumerate(items):
                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            if j in [2, 3, 5, 10]:  # Money columns
                                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                            if j == 9:  # Status column
                                item.setForeground(status_color)
                            self.transactions_table.setItem(i, j, item)
        except Exception as e:
            logger.error(f"Error in _process_tax_data: {str(e)}")
            print(f"Error in _process_tax_data: {str(e)}")
            self._handle_unexpected_error(e)
        finally:
            # Re-enable updates
            self.tax_table.setUpdatesEnabled(True)
            self.transactions_table.setUpdatesEnabled(True)
            
            # Force refresh
            self.tax_table.viewport().update()
            self.transactions_table.viewport().update()

    def _handle_api_error(self, response):
        """Handle API error responses with improved error reporting."""
        error_msg = self._extract_error_message(response)
        logger.error(f"API Error: {error_msg}")
        
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"خطأ في تحميل البيانات: {response.status_code}")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.ERROR};
                    padding: 5px;
                    border-radius: 3px;
                    background: {Theme.BG_SECONDARY};
                }}
            """)
        
        QMessageBox.warning(
            self,
            "خطأ",
            f"فشل تحميل البيانات: {error_msg}"
        )
        
    def _handle_connection_error(self, error):
        """Handle connection errors with improved error reporting."""
        error_msg = str(error)
        logger.error(f"Connection error in InventoryTab: {error_msg}")
        
        if hasattr(self, 'status_label'):
            self.status_label.setText("خطأ في الاتصال")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.ERROR};
                    padding: 5px;
                    border-radius: 3px;
                    background: {Theme.BG_SECONDARY};
                }}
            """)
            
        QMessageBox.critical(
            self,
            "خطأ في الاتصال",
            "تعذر الاتصال بالخادم. الرجاء التحقق من:\n"
            "1. اتصال الإنترنت\n"
            "2. حالة الخادم\n"
            "3. صلاحية رمز الدخول"
        )
        
    def _handle_unexpected_error(self, error):
        """Handle unexpected errors with improved error reporting."""
        error_msg = str(error)
        logger.error(f"Error in InventoryTab: {error_msg}")
        
        if hasattr(self, 'status_label'):
            self.status_label.setText("خطأ غير متوقع")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.ERROR};
                    padding: 5px;
                    border-radius: 3px;
                    background: {Theme.BG_SECONDARY};
                }}
            """)
            
        QMessageBox.critical(
            self,
            "خطأ غير متوقع",
            f"حدث خطأ غير متوقع:\n{error_msg}"
        )
        
    def _extract_error_message(self, response):
        """Extract error message from response with improved error handling."""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                return error_data.get("detail", error_data.get("message", response.text))
            return str(error_data)
        except Exception:
            return response.text[:200] if response.text else f"HTTP Error {response.status_code}"
            
    def add_product_to_inventory(self):
        """Add a new product to inventory with validation."""
        try:
            product_data = {
                "name": self.name_edit.text().strip(),
                "price": float(self.price_edit.value()),
                "quantity": int(self.quantity_edit.value())
            }
            
            if not self._validate_product_data(product_data):
                return
                
            headers = self._get_auth_headers()
            response = requests.post(
                f"{self.api_url}/inventory/products/",
                json=product_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                QMessageBox.information(self, "نجاح", "تمت إضافة المنتج بنجاح")
                self.load_data()  # Refresh data
            else:
                self._handle_api_error(response)
                
        except Exception as e:
            self._handle_unexpected_error(e)
            
    def _validate_product_data(self, data: Dict) -> bool:
        """Validate product data before submission."""
        if not data["name"]:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال اسم المنتج")
            return False
            
        if data["price"] <= 0:
            QMessageBox.warning(self, "خطأ", "يجب أن يكون السعر أكبر من الصفر")
            return False
            
        if data["quantity"] <= 0:
            QMessageBox.warning(self, "خطأ", "يجب أن تكون الكمية أكبر من الصفر")
            return False
            
        return True
    
    def load_branches(self, force_reload=False):
        """Load branches for the branch filter dropdown using QThread. استخدم الكاش إذا كان متاحاً إلا إذا طلب إعادة تحميل صريحة."""
        if self.branch_cache is not None and not force_reload:
            self._populate_branch_filter(self.branch_cache)
            return
        try:
            if hasattr(self, 'status_label'):
                self.status_label.setText("جاري تحميل الفروع...")
            headers = self._get_auth_headers()
            def api_call():
                return requests.get(
                    f"{self.api_url}/branches/",
                    headers=headers,
                    timeout=10
                )
            self.branches_worker = ApiWorker(api_call)
            self.branches_worker.result_ready.connect(self._on_branches_loaded)
            self.branches_worker.error_occurred.connect(self._handle_connection_error)
            self.branches_worker.start()
        except Exception as e:
            self._handle_connection_error(e)

    def _on_branches_loaded(self, response):
        try:
            if response.status_code == 200:
                data = response.json()
                branches = data.get("branches", [])
                self.branch_cache = branches  # تخزين الكاش
                self._populate_branch_filter(branches)
                if hasattr(self, 'status_label'):
                    self.status_label.setText("تم تحميل الفروع بنجاح")
            else:
                print(f"Error Response: {response.text}")
                error_msg = self._extract_error_message(response)
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"خطأ في تحميل الفروع: {response.status_code}")
                    QMessageBox.warning(self, "خطأ", f"فشل تحميل الفروع: {error_msg}")
        except Exception as e:
            self._handle_unexpected_error(e)

    def _populate_branch_filter(self, branches):
        self.branch_filter.clear()
        self.branch_filter.addItem("جميع الفروع", "all")
        for branch in branches:
            if isinstance(branch, dict):
                branch_name = branch.get('name', '')
                branch_gov = branch.get('governorate', '')
                branch_id = branch.get('id')
                if branch_name and branch_id:
                    display_text = f"{branch_name} - {branch_gov}" if branch_gov else branch_name
                    self.branch_filter.addItem(display_text, branch_id)

    def refresh_branches(self):
        """Force reload branches from server and update filter."""
        self.load_branches(force_reload=True)

    def _refresh_data(self):
        """Refresh all data in the tab (بيانات المخزون فقط)."""
        try:
            self.status_label.setText("جاري تحديث البيانات...")
            self.load_data()
            self.status_label.setText("تم تحديث البيانات بنجاح")
        except Exception as e:
            self._handle_unexpected_error(e)

    def _get_auth_headers(self) -> Dict:
        """Get authentication headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _get_status_color(self, status: str) -> QColor:
        """Get color for transaction status."""
        status_colors = {
            "completed": QColor("#2ecc71"),  # Green
            "processing": QColor("#3498db"),  # Blue
            "cancelled": QColor("#e74c3c"),  # Red
            "pending": QColor("#f39c12")     # Orange
        }
        return status_colors.get(status.lower(), QColor("#95a5a6"))  # Gray for unknown status

    def _get_status_text(self, status: str) -> str:
        """Get Arabic text for transaction status."""
        status_text = {
            "completed": "مكتمل",
            "processing": "قيد المعالجة",
            "cancelled": "ملغي",
            "pending": "قيد الانتظار"
        }
        return status_text.get(status.lower(), status)

    def _apply_filters(self):
        """Apply the selected filters and load data."""
        try:
            self.status_label.setText("جاري تطبيق الفلاتر...")
            self.load_data()
            self.status_label.setText("تم تطبيق الفلاتر بنجاح")
        except Exception as e:
            self._handle_unexpected_error(e)

    def update_tax_summary(self, data):
        """Update tax summary tables with new data"""
        try:
            # Update branch summary table
            branch_summary = data.get('branch_summary', [])
            self.branch_summary_table.setRowCount(len(branch_summary))
            
            for row, branch in enumerate(branch_summary):
                self.branch_summary_table.setItem(row, 0, QTableWidgetItem(branch['branch_name']))
                self.branch_summary_table.setItem(row, 1, QTableWidgetItem(branch['governorate']))
                self.branch_summary_table.setItem(row, 2, QTableWidgetItem(f"{branch['tax_rate']:.2f}%"))
                self.branch_summary_table.setItem(row, 3, QTableWidgetItem(str(branch['transaction_count'])))
                self.branch_summary_table.setItem(row, 4, QTableWidgetItem(f"{branch['total_amount']:.2f}"))
                self.branch_summary_table.setItem(row, 5, QTableWidgetItem(f"{branch['tax_amount']:.2f}"))
                self.branch_summary_table.setItem(row, 6, QTableWidgetItem(f"{branch['profit_amount']:.2f}"))
                self.branch_summary_table.setItem(row, 7, QTableWidgetItem(branch['currency']))

            # Update transaction details table
            transactions = data.get('transactions', [])
            self.transaction_table.setRowCount(len(transactions))
            
            for row, tx in enumerate(transactions):
                self.transaction_table.setItem(row, 0, QTableWidgetItem(tx['date']))
                self.transaction_table.setItem(row, 1, QTableWidgetItem(tx['source_branch']))
                self.transaction_table.setItem(row, 2, QTableWidgetItem(tx['destination_branch']))
                self.transaction_table.setItem(row, 3, QTableWidgetItem(f"{tx['amount']:.2f}"))
                self.transaction_table.setItem(row, 4, QTableWidgetItem(f"{tx['tax_rate']:.2f}%"))
                self.transaction_table.setItem(row, 5, QTableWidgetItem(f"{tx['tax_amount']:.2f}"))
                self.transaction_table.setItem(row, 6, QTableWidgetItem(f"{tx['profit_amount']:.2f}"))
                self.transaction_table.setItem(row, 7, QTableWidgetItem(tx['currency']))

            # Update summary labels
            total_tax = data.get('total_tax_amount', 0)
            total_transactions = data.get('total_transactions', 0)
            avg_tax_rate = data.get('avg_tax_rate', 0)
            total_profit = data.get('total_profit', 0)

            self.total_tax_label.setText(f"Total Tax: {total_tax:.2f}")
            self.total_transactions_label.setText(f"Total Transactions: {total_transactions}")
            self.avg_tax_rate_label.setText(f"Average Tax Rate: {avg_tax_rate:.2f}%")
            self.total_profit_label.setText(f"Total Profit: {total_profit:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update tax summary: {str(e)}")

    def setup_tax_summary_ui(self):
        """Setup the tax summary UI components"""
        # Create summary labels
        self.total_tax_label = QLabel("Total Tax: 0.00")
        self.total_transactions_label = QLabel("Total Transactions: 0")
        self.avg_tax_rate_label = QLabel("Average Tax Rate: 0.00%")
        self.total_profit_label = QLabel("Total Profit: 0.00")

        # Create branch summary table
        self.branch_summary_table = QTableWidget()
        self.branch_summary_table.setColumnCount(8)
        self.branch_summary_table.setHorizontalHeaderLabels([
            "Branch", "Governorate", "Tax Rate", "Transactions",
            "Total Amount", "Tax Amount", "Profit", "Currency"
        ])

        # Create transaction details table
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(8)
        self.transaction_table.setHorizontalHeaderLabels([
            "Date", "Source Branch", "Destination Branch", "Amount",
            "Tax Rate", "Tax Amount", "Profit", "Currency"
        ])
