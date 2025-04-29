from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QMessageBox, QDialog, QLineEdit, QComboBox,
    QGridLayout, QDateEdit, QDoubleSpinBox,
    QTextEdit
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QDate
from ui.custom_widgets import ModernGroupBox, ModernButton
import requests
import httpx
from fastapi import HTTPException

class TransferCore:
    """Contains all transfer-related functionality without UI dependencies"""
    
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
        # Get amounts
        base_amount = self.amount_input.value()
        benefited_amount = self.benefited_input.value()
        
        # Get current branch info
        current_branch_name = self.current_branch_label.text().split(" - ")[0]
        
        # Handle System Manager's governorate differently
        if self.branch_id == 0 or self.full_name == "System Manager":
            # For System Manager, use the selected governorate from the dropdown
            current_branch_governorate = self.sender_governorate_input.currentText()
        else:
            # For regular users, use the fixed governorate from the label
            current_branch_governorate = self.sender_governorate_label.text()
        
        # Extract currency code from the display text
        currency_text = self.currency_input.currentText()
        currency_code = currency_text.split("(")[1].split(")")[0] if "(" in currency_text else currency_text
        
        # Get destination branch tax rate and calculate tax
        dest_branch_id = self.branch_input.currentData()
        tax_rate = 0.0
        tax_amount = 0.0
        
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"} if self.user_token else {}
            response = requests.get(
                f"{self.api_url}/api/branches/{dest_branch_id}/tax_rate/",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                tax_data = response.json()
                tax_rate = float(tax_data.get("tax_rate", 0.0))
                
                # Calculate tax amount based ONLY on the benefited amount
                tax_amount = benefited_amount * (tax_rate / 100)
                
                # For logging purposes
                print(f"Base amount: {base_amount}")
                print(f"Benefited amount: {benefited_amount}")
                print(f"Tax rate: {tax_rate}%")
                print(f"Tax amount: {tax_amount}")
            else:
                print(f"Failed to get branch tax rate: {response.status_code}")
                error_msg = "Failed to get tax rate from server"
                if response.text:
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = str(error_data["detail"])
                    except:
                        pass
                QMessageBox.warning(self, "Warning", error_msg)
        except requests.RequestException as e:
            print(f"Error getting branch tax rate: {e}")
            QMessageBox.warning(self, "Warning", "Failed to connect to server for tax rate calculation")
        except Exception as e:
            print(f"Unexpected error getting branch tax rate: {e}")
            QMessageBox.warning(self, "Error", "An unexpected error occurred while calculating tax")

        # Calculate total amount (base amount + benefited amount)
        total_amount = base_amount + benefited_amount
        
        # Calculate net amount (total amount - tax)
        net_amount = total_amount - tax_amount

        # Get receiver details
        receiver_id = getattr(self, 'receiver_id_input', None)
        receiver_id = receiver_id.text() if receiver_id else ""
        
        receiver_address = getattr(self, 'receiver_address_input', None)
        receiver_address = receiver_address.text() if receiver_address else ""

        data = {
            "sender": self.sender_name_input.text(),
            "sender_mobile": self.sender_mobile_input.text(),
            "sender_id": self.sender_id_input.text(),
            "sender_address": self.sender_address_input.text(),
            "sender_governorate": current_branch_governorate,
            "sender_location": self.sender_location_input.text(),
            "receiver": self.receiver_name_input.text(),
            "receiver_mobile": self.receiver_mobile_input.text(),
            "receiver_id": receiver_id,
            "receiver_address": receiver_address,
            "receiver_governorate": self.receiver_governorate_input.currentText(),
            "receiver_location": self.receiver_location_input.text() if hasattr(self, 'receiver_location_input') else "",
            "amount": total_amount,  # Total amount before tax
            "base_amount": base_amount,  # Base amount (not taxed)
            "benefited_amount": benefited_amount,  # Amount subject to tax
            "net_amount": net_amount,  # Amount after tax deduction
            "currency": currency_code,
            "message": self.notes_input.toPlainText(),
            "employee_name": self.username,
            "branch_name": current_branch_name,
            "branch_governorate": current_branch_governorate,
            "destination_branch_id": dest_branch_id,
            "branch_id": self.branch_id,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "profit_amount": tax_amount,  # The tax amount is the profit
            "employee_id": getattr(self, 'employee_id', None)  # Add employee_id if available
        }
        return data
    
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
            
    def show_confirmation(self):
        """Show confirmation dialog before submitting transfer."""
        if not self.validate_transfer_form():
            return
        
        data = self.prepare_transfer_data()
        sending_branch_name = self.branch_id_to_name.get(self.branch_id, "غير معروف")
        destination_branch_id = data.get("destination_branch_id")
        destination_branch_name = self.branch_id_to_name.get(destination_branch_id, "غير معروف")
        
        msg = (
            f"تأكيد تفاصيل التحويل:\n\n"
            f"المرسل: {data['sender']} ({data['sender_mobile']})\n"
            f"المستلم: {data['receiver']} ({data['receiver_mobile']})\n"
            f"المبلغ: {data['amount']:,.2f} {data['currency']}\n"
            f"الضريبة: {data['tax_amount']:,.2f} {data['currency']} ({data['tax_rate']}%)\n"
            f"الصافي: {data['net_amount']:,.2f} {data['currency']}\n"
            f"من: {sending_branch_name}\n"
            f"إلى: {destination_branch_name}\n\n"
            f"هل تريد المتابعة؟"
        )
        
        reply = QMessageBox.question(
            self, "تأكيد التحويل", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.submit_transfer()
            
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

async def create_transfer(
    sender: str,
    sender_mobile: str,
    sender_id: str,
    sender_address: str,
    sender_governorate: str,
    sender_location: str,
    receiver: str,
    receiver_mobile: str,
    receiver_id: str,
    receiver_address: str,
    receiver_governorate: str,
    receiver_location: str,
    base_amount: float,
    benefited_amount: float,
    currency: str,
    message: str,
    branch_id: int,
    destination_branch_id: int,
    employee_id: int,
    employee_name: str,
) -> dict:
    """Create a new money transfer transaction."""
    try:
        # Calculate total amount
        total_amount = base_amount + benefited_amount
        
        # Get tax rate from destination branch
        tax_rate_response = await httpx.get(
            f"{settings.API_URL}/api/branches/{destination_branch_id}/tax_rate/"
        )
        tax_rate = tax_rate_response.json().get("tax_rate", 0)
        
        # Calculate tax only on benefited amount
        tax_amount = benefited_amount * (tax_rate / 100)
        
        # Prepare transaction data
        transaction_data = {
            "sender": sender,
            "sender_mobile": sender_mobile,
            "sender_id": sender_id,
            "sender_address": sender_address,
            "sender_governorate": sender_governorate,
            "sender_location": sender_location,
            "receiver": receiver,
            "receiver_mobile": receiver_mobile,
            "receiver_id": receiver_id,
            "receiver_address": receiver_address,
            "receiver_governorate": receiver_governorate,
            "receiver_location": receiver_location,
            "amount": total_amount,
            "base_amount": base_amount,
            "benefited_amount": benefited_amount,
            "currency": currency,
            "message": message,
            "branch_id": branch_id,
            "destination_branch_id": destination_branch_id,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "status": "processing"
        }
        
        # Send transaction to backend
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.API_URL}/api/transactions/",
                json=transaction_data
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Failed to create transaction: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to create transaction"
                )
                
    except Exception as e:
        logger.error(f"Error creating transfer: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )                                    