from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDialog, QFormLayout, QGroupBox,
    QTextEdit, QMessageBox, QProgressBar
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument, QFont, QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from ui.custom_widgets import ModernButton, ModernGroupBox
from datetime import datetime
import threading
import time

class PrintWorker(QThread):
    """Worker thread for printing operations"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, doc, printer):
        super().__init__()
        self.doc = doc
        self.printer = printer
        
    def run(self):
        try:
            self.progress.emit(50)
            self.doc.print_(self.printer)
            self.progress.emit(100)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class TransactionDetailsDialog(QDialog):
    """Dialog for displaying transaction details with improved performance."""
    
    def __init__(self, transaction_data, parent=None):
        super().__init__(parent)
        self.transaction_data = transaction_data
        self._details_cache = {}  # Cache for formatted details
        self._cache_lock = threading.Lock()  # Thread-safe cache access
        self._cache_cleanup_timer = QTimer()
        self._cache_cleanup_timer.timeout.connect(self._cleanup_cache)
        self._cache_cleanup_timer.start(300000)  # Cleanup every 5 minutes
        
        self.setWindowTitle("تفاصيل التحويل")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 1.5em;
                padding: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #3498db;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
        """)
        
        self.setup_ui()
        self.load_transaction_details()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        with self._cache_lock:
            current_time = datetime.now()
            expired_keys = [
                key for key, value in self._details_cache.items()
                if (current_time - value['timestamp']).total_seconds() > 300
            ]
            for key in expired_keys:
                del self._details_cache[key]
        
    def setup_ui(self):
        """Set up the UI with improved styling and layout."""
        layout = QVBoxLayout()
        layout.setSpacing(15)  # Increased spacing between elements
        
        # Transaction info group
        trans_group = ModernGroupBox("معلومات التحويل", "#3498db")
        trans_layout = QFormLayout()
        
        # Add transaction details with improved styling
        self.transaction_id_label = QLabel()
        self.transaction_id_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        trans_layout.addRow("رقم التحويل:", self.transaction_id_label)
        
        self.date_label = QLabel()
        trans_layout.addRow("التاريخ:", self.date_label)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: bold;")
        trans_layout.addRow("الحالة:", self.status_label)
        
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)
        
        # Sender info group
        sender_group = ModernGroupBox("معلومات المرسل", "#e74c3c")
        sender_layout = QFormLayout()
        
        self.sender_name_label = QLabel()
        sender_layout.addRow("اسم المرسل:", self.sender_name_label)
        
        self.sender_mobile_label = QLabel()
        sender_layout.addRow("رقم الهاتف:", self.sender_mobile_label)
        
        self.sender_branch_label = QLabel()
        sender_layout.addRow("الفرع:", self.sender_branch_label)
        
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)
        
        # Receiver info group
        receiver_group = ModernGroupBox("معلومات المستلم", "#2ecc71")
        receiver_layout = QFormLayout()
        
        self.receiver_name_label = QLabel()
        receiver_layout.addRow("اسم المستلم:", self.receiver_name_label)
        
        self.receiver_mobile_label = QLabel()
        receiver_layout.addRow("رقم الهاتف:", self.receiver_mobile_label)
        
        self.receiver_branch_label = QLabel()
        receiver_layout.addRow("الفرع:", self.receiver_branch_label)
        
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)
        
        # Additional info group
        additional_group = ModernGroupBox("معلومات إضافية", "#9b59b6")
        additional_layout = QFormLayout()
        
        self.amount_label = QLabel()
        self.amount_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        additional_layout.addRow("المبلغ:", self.amount_label)
        
        self.currency_label = QLabel()
        additional_layout.addRow("العملة:", self.currency_label)
        
        self.employee_label = QLabel()
        additional_layout.addRow("اسم الموظف:", self.employee_label)
        
        self.created_at_label = QLabel()
        additional_layout.addRow("تاريخ الإنشاء:", self.created_at_label)
        
        additional_group.setLayout(additional_layout)
        layout.addWidget(additional_group)
        
        # Progress bar for printing
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        print_button = ModernButton("طباعة", color="#3498db")
        print_button.clicked.connect(self.print_details)
        button_layout.addWidget(print_button)
        
        close_button = ModernButton("إغلاق", color="#e74c3c")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_transaction_details(self):
        """Load transaction details with caching."""
        try:
            # Check cache first
            cache_key = str(self.transaction_data.get('id', ''))
            with self._cache_lock:
                if cache_key in self._details_cache:
                    cached_details = self._details_cache[cache_key]
                    if self._is_cache_valid(cached_details):
                        self._apply_cached_details(cached_details)
                        return
            
            # Format and display transaction details
            self.transaction_id_label.setText(str(self.transaction_data.get('id', '')))
            
            # Format date
            date_str = self.transaction_data.get('date', '')
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except:
                formatted_date = date_str
            self.date_label.setText(formatted_date)
            
            # Set status with color
            status = self.transaction_data.get('status', '')
            self.status_label.setText(self._get_status_arabic(status))
            self.status_label.setStyleSheet(f"color: {self._get_status_color(status)};")
            
            # Sender info
            self.sender_name_label.setText(self.transaction_data.get('sender', ''))
            self.sender_mobile_label.setText(self.transaction_data.get('sender_mobile', ''))
            self.sender_branch_label.setText(self.transaction_data.get('sending_branch_name', ''))
            
            # Receiver info
            self.receiver_name_label.setText(self.transaction_data.get('receiver', ''))
            self.receiver_mobile_label.setText(self.transaction_data.get('receiver_mobile', ''))
            self.receiver_branch_label.setText(self.transaction_data.get('destination_branch_name', ''))
            
            # Additional info
            amount = self.transaction_data.get('amount', 0)
            self.amount_label.setText(f"{float(amount):,.2f}")
            self.currency_label.setText(self.transaction_data.get('currency', ''))
            self.employee_label.setText(self.transaction_data.get('employee_name', ''))
            self.created_at_label.setText(self.transaction_data.get('created_at', ''))
            
            # Cache the formatted details
            details = {
                'transaction_id': str(self.transaction_data.get('id', '')),
                'date': formatted_date,
                'status': status,
                'sender_name': self.transaction_data.get('sender', ''),
                'sender_mobile': self.transaction_data.get('sender_mobile', ''),
                'sender_branch': self.transaction_data.get('sending_branch_name', ''),
                'receiver_name': self.transaction_data.get('receiver', ''),
                'receiver_mobile': self.transaction_data.get('receiver_mobile', ''),
                'receiver_branch': self.transaction_data.get('destination_branch_name', ''),
                'amount': amount,
                'currency': self.transaction_data.get('currency', ''),
                'employee': self.transaction_data.get('employee_name', ''),
                'created_at': self.transaction_data.get('created_at', ''),
                'timestamp': datetime.now()
            }
            
            with self._cache_lock:
                self._details_cache[cache_key] = details
                
        except Exception as e:
            print(f"Error loading transaction details: {e}")
            
    def _is_cache_valid(self, cached_details):
        """Check if cached details are still valid."""
        cache_age = datetime.now() - cached_details['timestamp']
        return cache_age.total_seconds() < 300
        
    def _apply_cached_details(self, cached_details):
        """Apply cached details to UI."""
        self.transaction_id_label.setText(cached_details['transaction_id'])
        self.date_label.setText(cached_details['date'])
        self.status_label.setText(self._get_status_arabic(cached_details['status']))
        self.status_label.setStyleSheet(f"color: {self._get_status_color(cached_details['status'])};")
        self.sender_name_label.setText(cached_details['sender_name'])
        self.sender_mobile_label.setText(cached_details['sender_mobile'])
        self.sender_branch_label.setText(cached_details['sender_branch'])
        self.receiver_name_label.setText(cached_details['receiver_name'])
        self.receiver_mobile_label.setText(cached_details['receiver_mobile'])
        self.receiver_branch_label.setText(cached_details['receiver_branch'])
        self.amount_label.setText(f"{float(cached_details['amount']):,.2f}")
        self.currency_label.setText(cached_details['currency'])
        self.employee_label.setText(cached_details['employee'])
        self.created_at_label.setText(cached_details['created_at'])
        
    def print_details(self):
        """Print transaction details with progress tracking."""
        try:
            # Create printer
            printer = QPrinter()
            printer.setPageSize(QPrinter.PageSize.A4)
            printer.setOrientation(QPrinter.Orientation.Portrait)
            
            # Show print dialog
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec() == QDialog.DialogCode.Accepted:
                # Create document
                doc = QTextDocument()
                doc.setHtml(self._generate_print_html())
                
                # Show progress bar
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # Create and start worker
                self.print_worker = PrintWorker(doc, printer)
                self.print_worker.progress.connect(self.progress_bar.setValue)
                self.print_worker.finished.connect(self._on_print_finished)
                self.print_worker.error.connect(self._on_print_error)
                self.print_worker.start()
                
        except Exception as e:
            print(f"Error printing details: {e}")
            
    def _on_print_finished(self):
        """Handle print completion."""
        self.progress_bar.setVisible(False)
        
    def _on_print_error(self, error_msg):
        """Handle print error."""
        self.progress_bar.setVisible(False)
        print(f"Print error: {error_msg}")
        
    def _generate_print_html(self):
        """Generate HTML for printing with improved formatting."""
        return f"""
        <div style='font-family: Arial; direction: rtl; padding: 20px;'>
            <h2 style='color: #2c3e50; text-align: center;'>تفاصيل التحويل</h2>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #3498db;'>معلومات التحويل</h3>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>رقم التحويل:</td>
                        <td style='padding: 5px;'>{self.transaction_id_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>التاريخ:</td>
                        <td style='padding: 5px;'>{self.date_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>الحالة:</td>
                        <td style='padding: 5px; color: {self._get_status_color(self.transaction_data.get('status', ''))};'>
                            {self.status_label.text()}
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #e74c3c;'>معلومات المرسل</h3>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>اسم المرسل:</td>
                        <td style='padding: 5px;'>{self.sender_name_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>رقم الهاتف:</td>
                        <td style='padding: 5px;'>{self.sender_mobile_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>الفرع:</td>
                        <td style='padding: 5px;'>{self.sender_branch_label.text()}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #2ecc71;'>معلومات المستلم</h3>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>اسم المستلم:</td>
                        <td style='padding: 5px;'>{self.receiver_name_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>رقم الهاتف:</td>
                        <td style='padding: 5px;'>{self.receiver_mobile_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>الفرع:</td>
                        <td style='padding: 5px;'>{self.receiver_branch_label.text()}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #9b59b6;'>معلومات إضافية</h3>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>المبلغ:</td>
                        <td style='padding: 5px;'>{self.amount_label.text()} {self.currency_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>اسم الموظف:</td>
                        <td style='padding: 5px;'>{self.employee_label.text()}</td>
                    </tr>
                    <tr>
                        <td style='padding: 5px; font-weight: bold;'>تاريخ الإنشاء:</td>
                        <td style='padding: 5px;'>{self.created_at_label.text()}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin-top: 30px; text-align: center; color: #7f8c8d;'>
                <p>تم الطباعة في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        """
        
    def _get_status_arabic(self, status):
        """Convert status to Arabic."""
        status_map = {
            'pending': 'قيد الانتظار',
            'processing': 'قيد المعالجة',
            'completed': 'مكتمل',
            'cancelled': 'ملغي',
            'rejected': 'مرفوض',
            'on_hold': 'معلق'
        }
        return status_map.get(status, status)
        
    def _get_status_color(self, status):
        """Get color for status."""
        status_colors = {
            'pending': '#f1c40f',    # Yellow
            'processing': '#3498db',  # Blue
            'completed': '#2ecc71',   # Green
            'cancelled': '#e74c3c',   # Red
            'rejected': '#c0392b',    # Dark Red
            'on_hold': '#95a5a6'      # Gray
        }
        return status_colors.get(status, '#000000')  # Black default