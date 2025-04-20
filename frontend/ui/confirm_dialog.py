from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ConfirmTransactionDialog(QDialog):
    """Dialog to confirm transaction before sending."""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setWindowTitle("تأكيد التحويل")
        self.setGeometry(200, 200, 450, 500)  # Increased height for more fields
        
        # Store transaction data from kwargs
        self.transaction_data = kwargs
        
        # Set up the UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("تأكيد تفاصيل التحويل")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Format amount with commas - ensure amount is converted to float first
        try:
            amount = float(self.transaction_data.get("amount", 0))
            formatted_amount = f"{amount:,.2f}"
        except (ValueError, TypeError):
            formatted_amount = "0.00"
        
        # Create info text with all transaction details
        info_text = f"""
        <h3>معلومات المرسل:</h3>
        <p><b>الاسم:</b> {self.transaction_data.get('sender', '')}</p>
        <p><b>رقم الهاتف:</b> {self.transaction_data.get('sender_mobile', '')}</p>
        <p><b>المحافظة:</b> {self.transaction_data.get('sender_governorate', '')}</p>
        <p><b>الموقع:</b> {self.transaction_data.get('sender_location', '')}</p>
        
        <h3>معلومات المستلم:</h3>
        <p><b>الاسم:</b> {self.transaction_data.get('receiver', '')}</p>
        <p><b>رقم الهاتف:</b> {self.transaction_data.get('receiver_mobile', '')}</p>
        <p><b>المحافظة:</b> {self.transaction_data.get('receiver_governorate', '')}</p>
        <p><b>الموقع:</b> {self.transaction_data.get('receiver_location', '')}</p>
        
        <h3>تفاصيل التحويل:</h3>
        <p><b>المبلغ:</b> {formatted_amount} {self.transaction_data.get('currency', '')}</p>
        <p><b>الرسالة:</b> {self.transaction_data.get('message', 'لا توجد رسالة')}</p>
        <p><b>اسم الموظف:</b> {self.transaction_data.get('employee_name', '')}</p>
        <p><b>محافظة الفرع:</b> {self.transaction_data.get('branch_governorate', '')}</p>
        """
        
        self.info_label = QLabel(info_text)
        self.info_label.setWordWrap(True)
        self.info_label.setTextFormat(Qt.TextFormat.RichText)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        layout.addWidget(self.info_label)
        
        # Warning about transaction finality
        warning_label = QLabel("تنبيه: بعد تأكيد التحويل، لا يمكن التراجع عنه. يرجى التأكد من صحة جميع المعلومات.")
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #e74c3c; font-weight: bold; margin-top: 10px;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("تعديل")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.cancel_button)
        
        self.confirm_button = QPushButton("تأكيد وإرسال")
        self.confirm_button.clicked.connect(self.confirm_transaction)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        button_layout.addWidget(self.confirm_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def confirm_transaction(self):
        """Confirm the transaction after final validation."""
        # Perform final validation if needed
        if not self.validate_transaction():
            return
        
        # Accept the dialog to proceed with the transaction
        self.accept()
    
    def validate_transaction(self):
        """Validate the transaction data before final confirmation."""
        # Check for any missing required fields
        required_fields = ['sender', 'sender_mobile', 'receiver', 'receiver_mobile', 'amount']
        
        for field in required_fields:
            if not self.transaction_data.get(field):
                QMessageBox.warning(self, "بيانات ناقصة", f"الحقل {field} مطلوب لإتمام التحويل.")
                return False
        
        # Validate amount is positive
        try:
            amount = float(self.transaction_data.get('amount', 0))
            if amount <= 0:
                QMessageBox.warning(self, "قيمة غير صالحة", "يجب أن يكون المبلغ أكبر من صفر.")
                return False
        except (ValueError, TypeError):
            QMessageBox.warning(self, "قيمة غير صالحة", "المبلغ يجب أن يكون رقماً.")
            return False
        
        return True