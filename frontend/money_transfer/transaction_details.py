from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDialog, QFormLayout, QGroupBox,
    QTextEdit,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

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
        status_arabic = get_status_arabic(status)
        status_value = QLabel(status_arabic)
        status_value.setStyleSheet(f"font-weight: bold; color: {get_status_text_color(status)};")
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
        
        self.setLayout(layout)  # Dark gray default
    
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
                        <p><b>حالة التحويل:</b> {get_status_arabic(self.transaction.get('status', ''))}</p>
                        <p><b>الموظف:</b> {self.transaction.get('employee_name', '')}</p>
                        <p><b>الفرع:</b> {self.transaction.get('branch_name', '')}</p>
                        <p><b>ملاحظات:</b> {self.transaction.get('notes', '')}</p>
                        <hr>
                        <p style='color: #95a5a6;'>شكراً لاستخدامكم خدماتنا</p>
                    </div>
                </div>
            """)
            print_widget.print(printer)