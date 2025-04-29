from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QRadioButton, QButtonGroup, QDoubleSpinBox, QAbstractSpinBox,
    QTextEdit, QMessageBox, QTabWidget, QTableWidgetItem, QWidget
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import requests
from ui.custom_widgets import ModernButton

class BranchAllocationMixin:
    """Mixin class containing allocation-related functionality"""
    def allocate_funds(self):
        """Open dialog to allocate/deduct funds from branch with enhanced currency handling."""
        selected_rows = self.branches_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع لتعيين الرصيد")
            return
        
        row = selected_rows[0].row()
        branch_id = self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        branch_name = self.branches_table.item(row, 1).text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"إدارة رصيد الفرع - {branch_name}")
        dialog.setGeometry(200, 200, 500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QGroupBox {
                margin-top: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding-top: 15px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QRadioButton {
                padding: 8px;
                font-size: 14px;
                spacing: 8px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                min-height: 80px;
            }
            QDoubleSpinBox {
                padding: 8px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Operation type section
        type_group = QGroupBox("نوع العملية")
        type_layout = QHBoxLayout()
        self.operation_type = QButtonGroup()
        
        self.add_radio = QRadioButton("إضافة رصيد")
        self.deduct_radio = QRadioButton("خصم رصيد")
        self.add_radio.setChecked(True)
        
        type_layout.addWidget(self.add_radio)
        type_layout.addWidget(self.deduct_radio)
        self.operation_type.addButton(self.add_radio)
        self.operation_type.addButton(self.deduct_radio)
        type_group.setLayout(type_layout)
        main_layout.addWidget(type_group)

        # Currency selection section
        currency_group = QGroupBox("اختر العملة")
        currency_layout = QHBoxLayout()
        self.currency_group = QButtonGroup()
        
        self.syp_radio = QRadioButton("ليرة سورية (ل.س)")
        self.usd_radio = QRadioButton("دولار أمريكي ($)")
        self.syp_radio.setChecked(True)
        
        # Set object names for testing
        self.syp_radio.setObjectName("syp_radio")
        self.usd_radio.setObjectName("usd_radio")
        
        currency_layout.addWidget(self.syp_radio)
        currency_layout.addWidget(self.usd_radio)
        self.currency_group.addButton(self.syp_radio)
        self.currency_group.addButton(self.usd_radio)
        currency_group.setLayout(currency_layout)
        main_layout.addWidget(currency_group)

        # Amount input section
        amount_group = QGroupBox("المبلغ")
        amount_layout = QVBoxLayout()
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 100000000)
        self.amount_input.setValue(0.0)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.amount_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.amount_input.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        # Currency prefix handling
        def update_currency_prefix():
            currency = "SYP" if self.syp_radio.isChecked() else "USD"
            self.amount_input.setPrefix("ل.س " if currency == "SYP" else "$ ")
            self.amount_input.setSuffix("")
        
        self.syp_radio.toggled.connect(update_currency_prefix)
        self.usd_radio.toggled.connect(update_currency_prefix)
        update_currency_prefix()  # Initial update
        
        amount_layout.addWidget(self.amount_input)
        amount_group.setLayout(amount_layout)
        main_layout.addWidget(amount_group)

        # Description section
        desc_group = QGroupBox("الوصف (اختياري)")
        desc_layout = QVBoxLayout()
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("مثال: إيداع نقدي بتاريخ 2024-01-01")
        self.desc_input.setMaximumHeight(80)
        desc_layout.addWidget(self.desc_input)
        desc_group.setLayout(desc_layout)
        main_layout.addWidget(desc_group)

        # Button section
        button_layout = QHBoxLayout()
        
        self.delete_button = ModernButton("حذف الرصيد بالكامل", color="#e67e22")
        self.delete_button.clicked.connect(lambda: self.delete_allocation(branch_id, dialog))
        
        self.cancel_button = ModernButton("إلغاء", color="#e74c3c")
        self.cancel_button.clicked.connect(dialog.reject)
        
        self.save_button = ModernButton("حفظ التغييرات", color="#2ecc71")
        self.save_button.clicked.connect(lambda: self.validate_and_save(dialog, branch_id))
        
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

        # Set tab order
        QWidget.setTabOrder(self.add_radio, self.deduct_radio)
        QWidget.setTabOrder(self.deduct_radio, self.syp_radio)
        QWidget.setTabOrder(self.syp_radio, self.usd_radio)
        QWidget.setTabOrder(self.usd_radio, self.amount_input)
        QWidget.setTabOrder(self.amount_input, self.desc_input)

        dialog.exec()

    def validate_and_save(self, dialog, branch_id):
        """Validate inputs before saving"""
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "خطأ", "المبلغ يجب أن يكون أكبر من الصفر")
            return
            
        if not self.syp_radio.isChecked() and not self.usd_radio.isChecked():
            QMessageBox.warning(self, "خطأ", "الرجاء اختيار نوع العملة")
            return
            
        self.save_allocation(branch_id, dialog)
        
    def save_allocation(self, branch_id, dialog):
        """Save allocation/deduction to the branch with enhanced validation"""
        try:
            # Validate inputs
            amount = self.amount_input.value()
            if amount <= 0:
                QMessageBox.warning(self, "خطأ في الإدخال", "يرجى إدخال مبلغ أكبر من الصفر")
                return

            # Get operation details with explicit type conversion
            operation_type = "allocation" if self.add_radio.isChecked() else "deduction"
            currency = "USD" if self.usd_radio.isChecked() else "SYP"
            
            # Validate currency selection
            if not self.syp_radio.isChecked() and not self.usd_radio.isChecked():
                QMessageBox.warning(self, "خطأ", "الرجاء اختيار نوع العملة (ل.س أو $)")
                return

            # Prepare request data
            data = {
                "amount": round(amount, 2),
                "type": operation_type,
                "currency": currency,
                "description": self.desc_input.toPlainText().strip() or 
                              f"{'إيداع' if operation_type == 'allocation' else 'خصم'} {currency} بواسطة المدير"
            }

            # Make API request
            response = requests.post(
                f"{self.api_url}/branches/{branch_id}/allocate-funds/",
                headers={"Authorization": f"Bearer {self.token}"},
                json=data,
                timeout=10  # Add timeout
            )

            # Handle response
            if response.status_code == 200:
                QMessageBox.information(
                    self, 
                    "نجاح", 
                    f"تم تحديث الرصيد بنجاح\n"
                    f"المبلغ: {amount:,.2f} {currency}\n"
                    f"النوع: {'إضافة' if operation_type == 'allocation' else 'خصم'}"
                )
                # Refresh data and close dialog
                self.load_branches()
                self.load_branches_for_filter()  # Refresh filters if needed
                dialog.accept()
            else:
                error_msg = "خطأ غير معروف"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", error_data.get("message", str(error_data)))
                except:
                    error_msg = response.text[:200]  # Show first 200 chars of error
                
                QMessageBox.warning(
                    self, 
                    "فشل في العملية", 
                    f"رمز الخطأ: {response.status_code}\n{error_msg}"
                )

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(
                self, 
                "خطأ في الاتصال", 
                f"تعذر الاتصال بالخادم:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "خطأ غير متوقع", 
                f"حدث خطأ فادح:\n{str(e)}"
            )
            
    def delete_allocation(self, branch_id, dialog):
        """Delete all allocated funds for the branch"""
        try:
            confirm = QMessageBox.question(
                self,
                "تأكيد الحذف",
                "هل أنت متأكد من حذف الرصيد بالكامل؟ سيتم ضبط الرصيد على الصفر لكلا العملتين.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                headers = {"Authorization": f"Bearer {self.token}"}
                
                # Delete SYP allocations
                response_syp = requests.delete(
                    f"{self.api_url}/branches/{branch_id}/allocations/?currency=SYP",
                    headers=headers
                )
                
                # Delete USD allocations
                response_usd = requests.delete(
                    f"{self.api_url}/branches/{branch_id}/allocations/?currency=USD",
                    headers=headers
                )
                
                if response_syp.status_code == 200 and response_usd.status_code == 200:
                    QMessageBox.information(self, "نجاح", "تم حذف الرصيد بالكامل لكلا العملتين")
                    self.load_branches()
                    dialog.accept()
                else:
                    error_syp = response_syp.json().get("detail", "") if response_syp.status_code != 200 else ""
                    error_usd = response_usd.json().get("detail", "") if response_usd.status_code != 200 else ""
                    error = error_syp + " " + error_usd
                    QMessageBox.warning(self, "خطأ", f"فشل في الحذف: {error}")
                    
        except Exception as e:
            QMessageBox.critical(self, "خطأ فادح", f"حدث خطأ في النظام: {str(e)}")            