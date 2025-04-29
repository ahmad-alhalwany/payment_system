from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

class ModernGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 1em;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #3498db;
            }
        """)

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f6dad;
            }
        """)

class TransferDetails(QDialog):
    def __init__(self, transaction_data: dict, parent=None):
        super().__init__(parent)
        self.transaction_data = transaction_data
        self.setWindowTitle("Transfer Details")
        self.setup_ui()
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f6fa;
            }
            QLabel {
                color: #2c3e50;
                font-size: 12px;
            }
            QLabel[data="true"] {
                color: #34495e;
                font-weight: bold;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Sender Information
        sender_group = ModernGroupBox("Sender Information")
        sender_layout = QFormLayout()
        sender_layout.addRow("Name:", self.create_data_label(self.transaction_data.get("sender_name", "N/A")))
        sender_layout.addRow("Account:", self.create_data_label(self.transaction_data.get("sender_account", "N/A")))
        sender_layout.addRow("Phone:", self.create_data_label(self.transaction_data.get("sender_phone", "N/A")))
        sender_group.setLayout(sender_layout)
        layout.addWidget(sender_group)

        # Receiver Information
        receiver_group = ModernGroupBox("Receiver Information")
        receiver_layout = QFormLayout()
        receiver_layout.addRow("Name:", self.create_data_label(self.transaction_data.get("receiver_name", "N/A")))
        receiver_layout.addRow("Account:", self.create_data_label(self.transaction_data.get("receiver_account", "N/A")))
        receiver_layout.addRow("Phone:", self.create_data_label(self.transaction_data.get("receiver_phone", "N/A")))
        receiver_group.setLayout(receiver_layout)
        layout.addWidget(receiver_group)

        # Amount Details
        amount_group = ModernGroupBox("Amount Details")
        amount_layout = QFormLayout()
        amount_layout.addRow("Base Amount:", self.create_data_label(f"${self.transaction_data.get('base_amount', 0):,.2f}"))
        amount_layout.addRow("Benefited Amount:", self.create_data_label(f"${self.transaction_data.get('benefited_amount', 0):,.2f}"))
        amount_layout.addRow("Total Amount:", self.create_data_label(f"${self.transaction_data.get('total_amount', 0):,.2f}"))
        amount_layout.addRow("Tax Rate:", self.create_data_label(f"{self.transaction_data.get('tax_rate', 0)}%"))
        amount_layout.addRow("Tax Amount:", self.create_data_label(f"${self.transaction_data.get('tax_amount', 0):,.2f}"))
        amount_layout.addRow("Net Amount:", self.create_data_label(f"${self.transaction_data.get('net_amount', 0):,.2f}"))
        amount_group.setLayout(amount_layout)
        layout.addWidget(amount_group)

        # Transaction Details
        transaction_group = ModernGroupBox("Transaction Details")
        transaction_layout = QFormLayout()
        transaction_layout.addRow("Transaction ID:", self.create_data_label(self.transaction_data.get("transaction_id", "N/A")))
        transaction_layout.addRow("Status:", self.create_data_label(self.transaction_data.get("status", "N/A")))
        transaction_layout.addRow("Source Branch:", self.create_data_label(self.transaction_data.get("source_branch", "N/A")))
        transaction_layout.addRow("Destination Branch:", self.create_data_label(self.transaction_data.get("destination_branch", "N/A")))
        transaction_layout.addRow("Employee:", self.create_data_label(self.transaction_data.get("employee_name", "N/A")))
        transaction_layout.addRow("Message:", self.create_data_label(self.transaction_data.get("message", "N/A")))
        transaction_layout.addRow("Date:", self.create_data_label(self.transaction_data.get("date", "N/A")))
        transaction_group.setLayout(transaction_layout)
        layout.addWidget(transaction_group)

        # Close Button
        close_button = ModernButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)

        self.setFixedSize(500, 800)

    def create_data_label(self, text):
        label = QLabel(str(text))
        label.setProperty("data", True)
        return label 