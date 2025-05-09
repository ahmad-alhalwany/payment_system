from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QRadioButton, QButtonGroup, QDoubleSpinBox, QAbstractSpinBox,
    QTextEdit, QMessageBox, QTabWidget, QTableWidgetItem, QWidget, QLabel,
    QProgressBar, QFrame
)
from PyQt6.QtGui import QColor, QMovie
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
import requests
from ui.custom_widgets import ModernButton
from decimal import Decimal, ROUND_HALF_UP
import re

class AmountValidator:
    """Class to handle amount validation and formatting"""
    def __init__(self):
        self.max_amount = {
            'SYP': Decimal('1000000000'),  # 1 billion SYP
            'USD': Decimal('1000000')      # 1 million USD
        }
        self.min_amount = {
            'SYP': Decimal('0.01'),
            'USD': Decimal('0.01')
        }
        self.large_amount_threshold = {
            'SYP': Decimal('10000000'),    # 10 million SYP
            'USD': Decimal('10000')        # 10 thousand USD
        }

    def validate_amount(self, amount: float, currency: str, operation_type: str) -> tuple[bool, str]:
        """Validate amount and return (is_valid, error_message)"""
        try:
            amount_dec = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Check minimum amount
            if amount_dec < self.min_amount[currency]:
                return False, f"المبلغ يجب أن يكون أكبر من {self.min_amount[currency]} {currency}"
            
            # Check maximum amount
            if amount_dec > self.max_amount[currency]:
                return False, f"المبلغ يتجاوز الحد الأقصى المسموح به ({self.max_amount[currency]:,.2f} {currency})"
            
            # Check for large amounts
            if amount_dec > self.large_amount_threshold[currency]:
                return True, f"تنبيه: المبلغ كبير ({amount_dec:,.2f} {currency})"
            
            return True, ""
            
        except Exception as e:
            return False, f"خطأ في التحقق من المبلغ: {str(e)}"

    def format_amount(self, amount: float, currency: str) -> str:
        """Format amount with proper currency symbol and thousands separator"""
        try:
            amount_dec = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if currency == 'SYP':
                return f"{amount_dec:,.2f} ل.س"
            else:
                return f"${amount_dec:,.2f}"
        except:
            return str(amount)

class AllocationWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # New signal for progress updates
    
    def __init__(self, api_url, token, branch_id, data=None, op_type="save"):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.branch_id = branch_id
        self.data = data
        self.op_type = op_type
        self.validator = AmountValidator()
    
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            if self.op_type == "save":
                # Validate amount before sending
                is_valid, error_msg = self.validator.validate_amount(
                    self.data["amount"],
                    self.data["currency"],
                    self.data["type"]
                )
                
                if not is_valid:
                    self.error.emit(error_msg)
                    return
                
                self.progress.emit("جاري إرسال الطلب...")
                response = requests.post(
                    f"{self.api_url}/branches/{self.branch_id}/allocate-funds/",
                    headers=headers,
                    json=self.data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.finished.emit(response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_data.get("message", str(error_data)))
                    except:
                        error_msg = response.text[:200]
                    self.error.emit(f"رمز الخطأ: {response.status_code}\n{error_msg}")
                    
            elif self.op_type == "delete":
                self.progress.emit("جاري حذف الرصيد...")
                
                # Delete SYP allocations
                response_syp = requests.delete(
                    f"{self.api_url}/branches/{self.branch_id}/allocations/?currency=SYP",
                    headers=headers,
                    timeout=10
                )
                
                if response_syp.status_code != 200:
                    error_syp = response_syp.json().get("detail", "") if response_syp.status_code != 200 else ""
                    self.error.emit(f"فشل في حذف رصيد الليرة: {error_syp}")
                    return
                
                self.progress.emit("تم حذف رصيد الليرة، جاري حذف رصيد الدولار...")
                
                # Delete USD allocations
                response_usd = requests.delete(
                    f"{self.api_url}/branches/{self.branch_id}/allocations/?currency=USD",
                    headers=headers,
                    timeout=10
                )
                
                if response_usd.status_code != 200:
                    error_usd = response_usd.json().get("detail", "") if response_usd.status_code != 200 else ""
                    self.error.emit(f"فشل في حذف رصيد الدولار: {error_usd}")
                    return
                
                self.finished.emit({"success": True})
                
        except requests.Timeout:
            self.error.emit("انتهت مهلة الاتصال بالخادم. يرجى المحاولة مرة أخرى.")
        except requests.ConnectionError:
            self.error.emit("فشل الاتصال بالخادم. يرجى التحقق من اتصال الإنترنت.")
        except Exception as e:
            self.error.emit(f"حدث خطأ غير متوقع: {str(e)}")

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create spinner
        self.spinner_label = QLabel()
        self.movie = QMovie(":/icons/loading.gif")  # You'll need to add this resource
        self.movie.setScaledSize(QSize(48, 48))
        self.spinner_label.setMovie(self.movie)
        self.movie.start()
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #f0f0f0;
                border-radius: 5px;
                background-color: #ffffff;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 5px;
            }
        """)
        
        # Create status label
        self.status_label = QLabel("جاري تنفيذ العملية...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        # Add widgets to layout
        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Set overlay style
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 10px;
            }
        """)
    
    def set_message(self, message):
        self.status_label.setText(message)
    
    def showEvent(self, event):
        self.movie.start()
        super().showEvent(event)
    
    def hideEvent(self, event):
        self.movie.stop()
        super().hideEvent(event)

class BranchAllocationMixin:
    """Mixin class containing allocation-related functionality"""
    def __init__(self):
        self.validator = AmountValidator()

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

        # Replace the old loading label with the new overlay
        self.loading_overlay = LoadingOverlay(dialog)
        self.loading_overlay.hide()
        main_layout.addWidget(self.loading_overlay)
        
        # Make sure the overlay covers the entire dialog
        self.loading_overlay.setGeometry(0, 0, dialog.width(), dialog.height())

        # Set tab order
        QWidget.setTabOrder(self.add_radio, self.deduct_radio)
        QWidget.setTabOrder(self.deduct_radio, self.syp_radio)
        QWidget.setTabOrder(self.syp_radio, self.usd_radio)
        QWidget.setTabOrder(self.usd_radio, self.amount_input)
        QWidget.setTabOrder(self.amount_input, self.desc_input)

        dialog.exec()

    def validate_and_save(self, dialog, branch_id):
        """Validate inputs before saving"""
        try:
            amount = self.amount_input.value()
            currency = "USD" if self.usd_radio.isChecked() else "SYP"
            operation_type = "allocation" if self.add_radio.isChecked() else "deduction"
            
            # Validate amount
            is_valid, message = self.validator.validate_amount(amount, currency, operation_type)
            
            if not is_valid:
                QMessageBox.warning(self, "خطأ في المبلغ", message)
                return
            
            # If it's a large amount, ask for confirmation
            if "تنبيه" in message:
                confirm = QMessageBox.question(
                    self,
                    "تأكيد المبلغ الكبير",
                    f"المبلغ {self.validator.format_amount(amount, currency)} كبير.\nهل أنت متأكد من المتابعة؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.No:
                    return
            
            self.save_allocation(branch_id, dialog)
            
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التحقق", f"حدث خطأ أثناء التحقق من البيانات:\n{str(e)}")

    def save_allocation(self, branch_id, dialog):
        """Save allocation/deduction to the branch with enhanced validation"""
        try:
            amount = self.amount_input.value()
            operation_type = "allocation" if self.add_radio.isChecked() else "deduction"
            currency = "USD" if self.usd_radio.isChecked() else "SYP"
            
            data = {
                "amount": round(amount, 2),
                "type": operation_type,
                "currency": currency,
                "description": self.desc_input.toPlainText().strip() or \
                              f"{'إيداع' if operation_type == 'allocation' else 'خصم'} {currency} بواسطة المدير"
            }
            
            self.loading_overlay.set_message("جاري تنفيذ العملية...")
            self.loading_overlay.show()
            self._set_buttons_enabled(False)
            
            self.allocation_worker = AllocationWorker(self.api_url, self.token, branch_id, data, op_type="save")
            self.allocation_worker.finished.connect(lambda response_data: self._on_allocation_success(response_data, branch_id, amount, currency, operation_type, dialog))
            self.allocation_worker.error.connect(lambda msg: self._on_allocation_error(msg))
            self.allocation_worker.progress.connect(lambda msg: self.loading_overlay.set_message(msg))
            self.allocation_worker.start()
            
        except Exception as e:
            self.loading_overlay.hide()
            self._set_buttons_enabled(True)
            QMessageBox.critical(self, "خطأ غير متوقع", f"حدث خطأ فادح:\n{str(e)}")

    def _on_allocation_success(self, response_data, branch_id, amount, currency, operation_type, dialog):
        self.loading_overlay.hide()
        self._set_buttons_enabled(True)
        # Find the row index for the current branch
        target_row = -1
        for row in range(self.branches_table.rowCount()):
            if self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == branch_id:
                target_row = row
                break
        if target_row != -1:
            # Update SYP balance (column 5)
            syp_item = QTableWidgetItem(f"{response_data['new_allocated_syp']:,.2f}")
            syp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.branches_table.setItem(target_row, 5, syp_item)
            # Update USD balance (column 6)
            usd_item = QTableWidgetItem(f"{response_data['new_allocated_usd']:,.2f}")
            usd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.branches_table.setItem(target_row, 6, usd_item)
            self.branches_table.viewport().update()
        QMessageBox.information(
            self, 
            "نجاح", 
            f"تم تحديث الرصيد بنجاح\nالمبلغ: {amount:,.2f} {currency}\nالنوع: {'إضافة' if operation_type == 'allocation' else 'خصم'}"
        )
        dialog.accept()

    def _on_allocation_error(self, msg):
        self.loading_overlay.hide()
        self._set_buttons_enabled(True)
        QMessageBox.warning(self, "فشل في العملية", msg)

    def delete_allocation(self, branch_id, dialog):
        """Delete all allocated funds for the branch (now threaded)"""
        try:
            confirm = QMessageBox.question(
                self,
                "تأكيد الحذف",
                "هل أنت متأكد من حذف الرصيد بالكامل؟ سيتم ضبط الرصيد على الصفر لكلا العملتين.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.loading_overlay.set_message("جاري حذف الرصيد...")
                self.loading_overlay.show()
                self._set_buttons_enabled(False)
                self.delete_worker = AllocationWorker(self.api_url, self.token, branch_id, op_type="delete")
                self.delete_worker.finished.connect(lambda _: self._on_delete_success(dialog))
                self.delete_worker.error.connect(lambda msg: self._on_delete_error(msg))
                self.delete_worker.start()
        except Exception as e:
            self.loading_overlay.hide()
            self._set_buttons_enabled(True)
            QMessageBox.critical(self, "خطأ فادح", f"حدث خطأ في النظام: {str(e)}")

    def _on_delete_success(self, dialog):
        self.loading_overlay.hide()
        self._set_buttons_enabled(True)
        QMessageBox.information(self, "نجاح", "تم حذف الرصيد بالكامل لكلا العملتين")
        self.load_branches()
        dialog.accept()

    def _on_delete_error(self, msg):
        self.loading_overlay.hide()
        self._set_buttons_enabled(True)
        QMessageBox.warning(self, "خطأ", msg)

    def _set_buttons_enabled(self, enabled: bool):
        self.save_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)            