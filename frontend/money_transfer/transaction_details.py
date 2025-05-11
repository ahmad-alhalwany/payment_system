from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDialog, QFormLayout, QGroupBox,
    QTextEdit, QMessageBox
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
from datetime import datetime

class TransactionDetailsDialog(QDialog):
    """Dialog for displaying transaction details with improved performance."""
    
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self._details_cache = {}  # Cache for formatted details
        
        self.setWindowTitle("تفاصيل التحويل")
        self.setGeometry(300, 300, 600, 500)  # Increased size for better readability
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
    
    def setup_ui(self):
        """Set up the UI components with improved layout."""
        layout = QVBoxLayout()
        layout.setSpacing(15)  # Increased spacing between elements
        
        # Transaction info group with improved styling
        transaction_group = self._create_transaction_group()
        layout.addWidget(transaction_group)
        
        # Sender info group
        sender_group = self._create_sender_group()
        layout.addWidget(sender_group)
        
        # Receiver info group
        receiver_group = self._create_receiver_group()
        layout.addWidget(receiver_group)
        
        # Additional info group
        additional_group = self._create_additional_group()
        layout.addWidget(additional_group)
        
        # Buttons with improved styling
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        print_button = QPushButton("طباعة")
        print_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
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
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def _create_transaction_group(self):
        """Create transaction info group with improved layout."""
        group = QGroupBox("معلومات التحويل")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # Add transaction details with improved formatting
        self._add_form_row(layout, "رقم التحويل:", str(self.transaction.get("id", "")), True)
        self._add_form_row(layout, "التاريخ:", self.transaction.get("date", ""), True)
        
        # Format amount with currency
        amount = self.transaction.get("amount", 0)
        formatted_amount = f"{float(amount):,.2f} {self.transaction.get('currency', '')}"
        self._add_form_row(layout, "المبلغ:", formatted_amount, True)
        
        # Add status with color
        status = self.transaction.get("status", "pending")
        status_arabic = get_status_arabic(status)
        status_label = QLabel(status_arabic)
        status_label.setStyleSheet(f"color: {get_status_text_color(status)}; font-weight: bold;")
        layout.addRow(QLabel("الحالة:"), status_label)
        
        group.setLayout(layout)
        return group
    
    def _create_sender_group(self):
        """Create sender info group with improved layout."""
        group = QGroupBox("معلومات المرسل")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        self._add_form_row(layout, "الاسم:", self.transaction.get("sender_name", ""), True)
        self._add_form_row(layout, "رقم الهاتف:", self.transaction.get("sender_mobile", ""))
        self._add_form_row(layout, "رقم الهوية:", self.transaction.get("sender_id", ""))
        self._add_form_row(layout, "العنوان:", self.transaction.get("sender_address", ""))
        
        group.setLayout(layout)
        return group
    
    def _create_receiver_group(self):
        """Create receiver info group with improved layout."""
        group = QGroupBox("معلومات المستلم")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        self._add_form_row(layout, "الاسم:", self.transaction.get("receiver_name", ""), True)
        self._add_form_row(layout, "رقم الهاتف:", self.transaction.get("receiver_mobile", ""))
        self._add_form_row(layout, "رقم الهوية:", self.transaction.get("receiver_id", ""))
        self._add_form_row(layout, "العنوان:", self.transaction.get("receiver_address", ""))
        
        group.setLayout(layout)
        return group
    
    def _create_additional_group(self):
        """Create additional info group with improved layout."""
        group = QGroupBox("معلومات إضافية")
        layout = QFormLayout()
        layout.setSpacing(10)
        
        self._add_form_row(layout, "الموظف:", self.transaction.get("employee_name", ""))
        self._add_form_row(layout, "الفرع المرسل:", self.transaction.get("sending_branch_name", ""))
        self._add_form_row(layout, "الفرع المستلم:", self.transaction.get("destination_branch_name", ""))
        self._add_form_row(layout, "محافظة الفرع:", self.transaction.get("branch_governorate", ""))
        
        # Add notes with word wrap
        notes_label = QLabel(self.transaction.get("notes", ""))
        notes_label.setWordWrap(True)
        notes_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border-radius: 4px;")
        layout.addRow(QLabel("ملاحظات:"), notes_label)
        
        group.setLayout(layout)
        return group
    
    def _add_form_row(self, layout, label_text, value, is_bold=False):
        """Add a form row with improved styling."""
        label = QLabel(label_text)
        value_label = QLabel(str(value))
        if is_bold:
            value_label.setStyleSheet("font-weight: bold;")
        layout.addRow(label, value_label)
    
    def print_transaction(self):
        """Print transaction details with improved formatting."""
        try:
            printer = QPrinter()
            printer.setPageSize(QPrinter.PageSize.A4)
            printer.setOrientation(QPrinter.Orientation.Portrait)
            
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec() == QDialog.DialogCode.Accepted:
                # Create a temporary widget for printing
                print_widget = QTextEdit()
                print_widget.setHtml(self._generate_print_html())
                
                # Print the document
                document = QTextDocument()
                document.setHtml(print_widget.toHtml())
                document.print_(printer)
                
                QMessageBox.information(self, "نجاح", "تمت الطباعة بنجاح")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء الطباعة: {str(e)}")
    
    def _generate_print_html(self):
        """Generate HTML for printing with improved formatting."""
        return f"""
        <div style='font-family: Arial; direction: rtl; padding: 20px;'>
            <h1 style='color: #2c3e50; text-align: center;'>تفاصيل التحويل</h1>
            <hr style='border: 1px solid #3498db;'>
            
            <div style='margin: 20px 0;'>
                <h2 style='color: #3498db;'>معلومات التحويل</h2>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>رقم التحويل:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('id', '')}</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>التاريخ:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('date', '')}</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>المبلغ:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('amount', '')} {self.transaction.get('currency', '')}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0;'>
                <h2 style='color: #e74c3c;'>معلومات المرسل</h2>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>الاسم:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('sender_name', '')}</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>رقم الهاتف:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('sender_mobile', '')}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0;'>
                <h2 style='color: #2ecc71;'>معلومات المستلم</h2>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>الاسم:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('receiver_name', '')}</td>
                    </tr>
                    <tr>
                        <td style='padding: 8px; border: 1px solid #ddd;'><b>رقم الهاتف:</b></td>
                        <td style='padding: 8px; border: 1px solid #ddd;'>{self.transaction.get('receiver_mobile', '')}</td>
                    </tr>
                </table>
            </div>
            
            <div style='margin: 20px 0; text-align: center; color: #7f8c8d;'>
                <p>شكراً لاستخدامكم خدماتنا</p>
                <p>تاريخ الطباعة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        """