import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem,
    QLineEdit, QFormLayout, QComboBox, QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt
import os
from ui.custom_widgets import ModernGroupBox, ModernButton
from config import get_api_url

class TaxManagementDialog(QDialog):
    """Dialog for managing tax rates."""
    
    def __init__(self, branch_data=None, token=None, parent=None):
        super().__init__(parent)
        self.branch_data = branch_data
        self.token = token
        self.api_url = get_api_url()
        
        self.setWindowTitle("إدارة الضرائب")
        self.setGeometry(300, 300, 400, 250)
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
        """)
        
        layout = QVBoxLayout()
        
        # Form group
        form_group = ModernGroupBox("معلومات الضريبة", "#3498db")
        form_layout = QFormLayout()
        
        # Branch ID (read-only if editing)
        branch_id_label = QLabel("رمز الفرع:")
        self.branch_id_input = QLineEdit()
        if branch_data:
            # Convert branch_id to string if it's not None
            branch_id = str(branch_data.get("branch_id", "")) if branch_data.get("branch_id") is not None else ""
            self.branch_id_input.setText(branch_id)
            self.branch_id_input.setReadOnly(True)
            self.branch_id_input.setStyleSheet("background-color: #f0f0f0;")
        else:
            self.branch_id_input.setPlaceholderText("أدخل رمز الفرع")
        form_layout.addRow(branch_id_label, self.branch_id_input)
        
        # Branch name (read-only)
        branch_name_label = QLabel("اسم الفرع:")
        self.branch_name_input = QLineEdit()
        if branch_data:
            # Convert name to string if it's not None
            branch_name = str(branch_data.get("name", "")) if branch_data.get("name") is not None else ""
            self.branch_name_input.setText(branch_name)
            self.branch_name_input.setReadOnly(True)
            self.branch_name_input.setStyleSheet("background-color: #f0f0f0;")
        else:
            self.branch_name_input.setPlaceholderText("سيتم تعبئته تلقائياً")
            self.branch_name_input.setReadOnly(True)
            self.branch_name_input.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow(branch_name_label, self.branch_name_input)
        
        # Tax rate field
        tax_rate_label = QLabel("نسبة الضريبة (%):")
        self.tax_rate_input = QLineEdit()
        self.tax_rate_input.setPlaceholderText("أدخل نسبة الضريبة")
        # Set current tax rate if it exists
        if branch_data:
            current_tax_rate = branch_data.get("tax_rate", 0.0)
            self.tax_rate_input.setText(f"{float(current_tax_rate):.2f}")
        else:
            self.tax_rate_input.setText("0.00")  # Default value
        form_layout.addRow(tax_rate_label, self.tax_rate_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_button = ModernButton("إلغاء", color="#e74c3c")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = ModernButton("حفظ", color="#2ecc71")
        save_button.clicked.connect(self.save_tax_rate)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def save_tax_rate(self):
        """Save the tax rate changes."""
        try:
            # Validate inputs
            if not self.branch_id_input.text().strip():
                QMessageBox.warning(self, "تنبيه", "الرجاء إدخال رمز الفرع")
                return
            
            # Validate tax rate
            try:
                tax_rate = float(self.tax_rate_input.text())
                if tax_rate < 0:
                    QMessageBox.warning(self, "تنبيه", "نسبة الضريبة يجب أن تكون قيمة موجبة")
                    return
            except ValueError:
                QMessageBox.warning(self, "تنبيه", "الرجاء إدخال قيمة رقمية صحيحة لنسبة الضريبة")
                return
            
            # Get branch ID and ensure it's properly formatted
            branch_id = self.branch_id_input.text().strip()
            
            # Make the API call
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            api_url = f"{self.api_url}/api/branches/{branch_id}/tax_rate/"
            
            response = requests.put(
                api_url,
                json={"tax_rate": tax_rate},
                headers=headers
            )
            
            if response.status_code == 200:
                QMessageBox.information(self, "نجاح", "تم تحديث نسبة الضريبة بنجاح")
                
                # Ensure the parent window refreshes the branches list
                if self.parent():
                    self.parent().load_branches()
                
                self.accept()
            else:
                error_msg = f"فشل تحديث نسبة الضريبة: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = error_data["detail"]
                except:
                    pass
                QMessageBox.warning(self, "خطأ", error_msg)
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self,
                "خطأ في الاتصال",
                "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ غير متوقع: {str(e)}"
            )

class TaxManagement(QWidget):
    """Tax management widget."""
    
    def __init__(self, token=None, parent=None):
        super().__init__(parent)
        self.token = token
        self.api_url = get_api_url()
        self.branches = []
        
        self.setWindowTitle("إدارة الضرائب")
        self.setGeometry(100, 100, 800, 600)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("إدارة نسب الضرائب")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.add_tax_button = ModernButton("إضافة ضريبة جديدة", color="#2ecc71")
        self.add_tax_button.clicked.connect(self.add_tax)
        buttons_layout.addWidget(self.add_tax_button)
        
        self.refresh_button = ModernButton("تحديث", color="#3498db")
        self.refresh_button.clicked.connect(self.load_branches)
        buttons_layout.addWidget(self.refresh_button)
        
        layout.addLayout(buttons_layout)
        
        # Table
        self.branches_table = QTableWidget()
        self.branches_table.setColumnCount(4)
        self.branches_table.setHorizontalHeaderLabels(["رمز الفرع", "اسم الفرع", "نسبة الضريبة (%)", "إجراءات"])
        self.branches_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.branches_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.branches_table)
        
        self.setLayout(layout)
        
        # Load branches
        self.load_branches()
    
    def load_branches(self):
        """Load branches from API."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            
            if response.status_code == 200:
                self.branches = response.json()
                self.update_table()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل الفروع: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error loading branches: {e}")
            QMessageBox.critical(
                self,
                "خطأ في الاتصال",
                "تعذر الاتصال بالخادم. الرجاء التحقق من اتصالك بالإنترنت وحالة الخادم."
            )
    
    def update_table(self):
        """Update the branches table."""
        self.branches_table.setRowCount(0)
        
        for i, branch in enumerate(self.branches):
            self.branches_table.insertRow(i)
            
            # Branch ID
            branch_id_item = QTableWidgetItem(branch.get("branch_id", ""))
            branch_id_item.setFlags(branch_id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.branches_table.setItem(i, 0, branch_id_item)
            
            # Branch name
            branch_name_item = QTableWidgetItem(branch.get("name", ""))
            branch_name_item.setFlags(branch_name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.branches_table.setItem(i, 1, branch_name_item)
            
            # Tax rate
            tax_rate = branch.get("tax_rate", 0.0)
            tax_rate_item = QTableWidgetItem(f"{tax_rate:.2f}")
            tax_rate_item.setFlags(tax_rate_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.branches_table.setItem(i, 2, tax_rate_item)
            
            # Add button
            add_button = ModernButton("إضافة/تعديل", color="#f39c12")
            add_button.clicked.connect(lambda checked, b=branch: self.add_tax(b))
            
            # Add button to table
            self.branches_table.setCellWidget(i, 3, add_button)
    
    def add_tax(self, branch=None):
        """Add or edit a tax rate."""
        if branch is None:
            # If no branch is provided, get the selected branch
            selected_rows = self.branches_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع لإضافة الضريبة")
                return
            row = selected_rows[0].row()
            branch = {
                "branch_id": self.branches_table.item(row, 0).text(),
                "name": self.branches_table.item(row, 1).text(),
                "tax_rate": float(self.branches_table.item(row, 2).text())
            }
        
        dialog = TaxManagementDialog(branch_data=branch, token=self.token, parent=self)
        if dialog.exec():
            self.load_branches()
