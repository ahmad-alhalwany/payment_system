from PyQt6.QtWidgets import (
    QVBoxLayout, QMessageBox, QDialog, QTextEdit, QPushButton, QHBoxLayout
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
from PyQt6.QtCore import Qt
from ui.arabic_amount import number_to_arabic_words
from ui.custom_widgets import ModernButton
from datetime import datetime

class ReceiptPrinter:
    
    def __init__(self, parent=None):
        self.parent = parent
        self._receipt_cache = {}  # Cache for generated receipts
        self._printer_settings = {
            'page_size': 'A4',
            'orientation': 'Portrait',
            'margins': (10, 10, 10, 10)  # Left, Top, Right, Bottom in mm
        }

    def print_receipt(self, transaction_data):
        """Print receipt for the selected transaction with improved performance."""
        try:
            # Check cache first
            cache_key = str(transaction_data.get('id', ''))
            if cache_key in self._receipt_cache:
                cached_receipt = self._receipt_cache[cache_key]
                if self._is_cache_valid(cached_receipt, transaction_data):
                    self._print_cached_receipt(cached_receipt)
                    return

            # Generate new receipt
            amount = transaction_data.get('amount', 0) or 0
            currency = transaction_data.get('currency', 'ليرة سورية') or 'ليرة سورية'
            
            formatted_id = self._format_transaction_id(transaction_data.get('id', ''))
            amount_in_arabic = number_to_arabic_words(str(amount), currency)
            
            # Generate and cache receipt
            receipt_data = {
                'customer_copy': self._generate_customer_copy_html(transaction_data, formatted_id, amount_in_arabic),
                'system_copy': self._generate_system_copy_html(transaction_data, formatted_id, amount_in_arabic),
                'timestamp': datetime.now(),
                'transaction_id': cache_key
            }
            self._receipt_cache[cache_key] = receipt_data
            
            # Show print dialog
            print_dialog = self._create_print_dialog(transaction_data, formatted_id, amount_in_arabic)
            print_dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self.parent, "خطأ", f"حدث خطأ أثناء طباعة الإيصال: {str(e)}")

    def _is_cache_valid(self, cached_receipt, current_data):
        """Check if cached receipt is still valid."""
        # Cache is valid for 5 minutes
        cache_age = datetime.now() - cached_receipt['timestamp']
        return cache_age.total_seconds() < 300

    def _print_cached_receipt(self, cached_receipt):
        """Print from cached receipt data."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("طباعة التحويل")
        dialog.setFixedSize(1000, 600)
        
        layout = QVBoxLayout()
        content_layout = QHBoxLayout()
        
        # Customer copy
        customer_copy = QTextEdit()
        customer_copy.setReadOnly(True)
        customer_copy.setHtml(cached_receipt['customer_copy'])
        content_layout.addWidget(customer_copy)
        
        # System copy
        system_copy = QTextEdit()
        system_copy.setReadOnly(True)
        system_copy.setHtml(cached_receipt['system_copy'])
        content_layout.addWidget(system_copy)
        
        layout.addLayout(content_layout)
        
        # Print button with improved styling
        print_btn = ModernButton("طباعة", color="#3498db")
        print_btn.clicked.connect(lambda: self.send_to_printer(customer_copy, system_copy))
        layout.addWidget(print_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def send_to_printer(self, customer_copy, system_copy):
        """Send to printer with improved settings."""
        try:
            printer = QPrinter()
            printer.setPageSize(QPrinter.PageSize.A4)
            printer.setOrientation(QPrinter.Orientation.Portrait)
            
            # Set margins
            printer.setPageMargins(
                self._printer_settings['margins'][0],
                self._printer_settings['margins'][1],
                self._printer_settings['margins'][2],
                self._printer_settings['margins'][3],
                QPrinter.Unit.Millimeter
            )
            
            print_dialog = QPrintDialog(printer, self.parent)
            if print_dialog.exec() == QDialog.DialogCode.Accepted:
                # Print customer copy
                customer_doc = QTextDocument()
                customer_doc.setHtml(customer_copy.toHtml())
                customer_doc.print_(printer)
                
                # Print system copy
                system_doc = QTextDocument()
                system_doc.setHtml(system_copy.toHtml())
                system_doc.print_(printer)
                
                QMessageBox.information(self.parent, "نجاح", "تمت الطباعة بنجاح")
        except Exception as e:
            QMessageBox.warning(self.parent, "خطأ", f"حدث خطأ أثناء الطباعة: {str(e)}")

    def clear_cache(self):
        """Clear the receipt cache."""
        self._receipt_cache.clear()

    def _format_transaction_id(self, transaction_id):
        """Format transaction ID with dashes"""
        if transaction_id is None:
            return ''
        id_str = str(transaction_id)
        if id_str.isdigit() and len(id_str) >= 4:
            return '-'.join([id_str[i:i+4] for i in range(0, len(id_str), 4)])
        return id_str

    def _create_print_dialog(self, transaction, formatted_id, amount_in_arabic):
        """Create print dialog with formatted content"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("طباعة التحويل")
        dialog.setFixedSize(1000, 600)  # Increased width for side-by-side layout
        
        layout = QVBoxLayout()
        
        # Create side-by-side layout
        content_layout = QHBoxLayout()
        
        # Customer copy
        customer_copy = QTextEdit()
        customer_copy.setReadOnly(True)
        customer_copy.setHtml(self._generate_customer_copy_html(transaction, formatted_id, amount_in_arabic))
        content_layout.addWidget(customer_copy)
        
        # System copy
        system_copy = QTextEdit()
        system_copy.setReadOnly(True)
        system_copy.setHtml(self._generate_system_copy_html(transaction, formatted_id, amount_in_arabic))
        content_layout.addWidget(system_copy)
        
        layout.addLayout(content_layout)
        
        # Print button
        print_btn = self._create_print_button(customer_copy, system_copy)
        layout.addWidget(print_btn)
        
        dialog.setLayout(layout)
        return dialog

    def _generate_customer_copy_html(self, transaction, formatted_id, amount_in_arabic):
        """Generate HTML for customer copy with safe value handling"""
        # Safely get values with defaults
        date = transaction.get('date', '')
        sender = transaction.get('sender', '')
        receiver = transaction.get('receiver', '')
        receiver_mobile = transaction.get('receiver_mobile', '')
        
        # Get transaction type
        status_text = "مستلم" if transaction.get('type') == 'received' else "مرسل"
        
        # Get amounts - only show total amount
        amount = transaction.get('amount', 0)
        if amount is None:
            amount = 0
            
        currency = transaction.get('currency', '')
        if currency is None:
            currency = 'ليرة سورية'
            
        # Get branch information - ensure proper fetching from transaction data
        sending_branch = transaction.get('sending_branch_name', '')  # Updated key to match backend
        if not sending_branch:
            sending_branch = transaction.get('branch_name', '')  # Fallback
            
        destination_branch = transaction.get('destination_branch_name', '')  # Updated key to match backend
        if not destination_branch:
            destination_branch = transaction.get('destination_branch', '')  # Fallback

        return f"""
        <div style='font-family: Arial; direction: rtl; background-color: #fff; padding: 20px; margin: 0;'>
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2 style='color: #333; margin: 0;'>نسخة العميل</h2>
                </div>
                
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>رقم التحويل: </span>
                <span style='float: left;'>{formatted_id}</span>
                <div style='clear: both;'></div>
                </div>
                
            <div style='margin-bottom: 20px; text-align: center;'>
                <span style='color: #4CAF50; font-weight: bold;'>{status_text}</span>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>التاريخ: </span>
                <span style='float: left;'>{date}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المرسل: </span>
                <span style='float: left;'>{sender}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المستلم: </span>
                <span style='float: left;'>{receiver}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>رقم هاتف المستلم: </span>
                <span style='float: left;'>{receiver_mobile}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المبلغ الإجمالي: </span>
                <span style='float: left;'>{amount:,.2f} {currency}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المبلغ كتابةً: </span>
                <span style='float: left;'>{amount_in_arabic}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>من: </span>
                <span style='float: left;'>{sending_branch}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>إلى: </span>
                <span style='float: left;'>{destination_branch}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='text-align: center; color: #4CAF50; margin: 20px 0;'>
                <p style='font-weight: bold;'>يرجى الاحتفاظ بهذا الإيصال</p>
                <p style='font-weight: bold;'>يطلب تبليغ المستفيد برقم الحوالة</p>
            </div>
        </div>
        """

    def _generate_system_copy_html(self, transaction, formatted_id, amount_in_arabic):
        """Generate HTML for system copy with safe value handling"""
        # Safely get values with defaults
        date = transaction.get('date', '')
        sender = transaction.get('sender', '')
        sender_mobile = transaction.get('sender_mobile', '')
        receiver = transaction.get('receiver', '')
        receiver_mobile = transaction.get('receiver_mobile', '')
        
        # Get transaction type
        status_text = "مستلم" if transaction.get('type') == 'received' else "مرسل"
        
        # Get amounts - only show total amount
        amount = transaction.get('amount', 0)
        if amount is None:
            amount = 0
            
        currency = transaction.get('currency', '')
        if currency is None:
            currency = 'ليرة سورية'
            
        # Get branch and employee information
        sending_branch = transaction.get('sending_branch_name', '')
        if not sending_branch:
            sending_branch = transaction.get('branch_name', '')
            
        destination_branch = transaction.get('destination_branch_name', '')
        if not destination_branch:
            destination_branch = transaction.get('destination_branch', '')
            
        employee_name = transaction.get('employee_name', '')
        transaction_type = 'تحويل صادر' if transaction.get('type') == 'sent' else 'تحويل وارد'

        return f"""
        <div style='font-family: Arial; direction: rtl; background-color: #fff; padding: 20px; margin: 0;'>
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2 style='color: #4CAF50; margin: 0;'>نسخة النظام</h2>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>رقم التحويل: </span>
                <span style='float: left;'>{formatted_id}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 20px; text-align: center;'>
                <span style='color: #4CAF50; font-weight: bold;'>{status_text}</span>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>التاريخ: </span>
                <span style='float: left;'>{date}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المرسل: </span>
                <span style='float: left;'>{sender}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>رقم هاتف المرسل: </span>
                <span style='float: left;'>{sender_mobile}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المستلم: </span>
                <span style='float: left;'>{receiver}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>رقم هاتف المستلم: </span>
                <span style='float: left;'>{receiver_mobile}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المبلغ الإجمالي: </span>
                <span style='float: left;'>{amount:,.2f} {currency}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>المبلغ كتابةً: </span>
                <span style='float: left;'>{amount_in_arabic}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>الفرع المرسل: </span>
                <span style='float: left;'>{sending_branch}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>الفرع المستلم: </span>
                <span style='float: left;'>{destination_branch}</span>
                <div style='clear: both;'></div>
                        </div>
                        
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>اسم الموظف: </span>
                <span style='float: left;'>{employee_name}</span>
                <div style='clear: both;'></div>
                    </div>
                    
            <div style='margin-bottom: 10px;'>
                <span style='float: right;'>نوع التحويل: </span>
                <span style='float: left;'>{transaction_type}</span>
                <div style='clear: both;'></div>
                        </div>
                        
                        <div style='margin-top: 30px; border-top: 1px dashed #ddd; padding-top: 15px;'>
                <div style='margin-bottom: 10px;'>
                    <span style='float: right;'>اسم العميل الكامل: </span>
                    <span style='float: left;'>________________</span>
                    <div style='clear: both;'></div>
                </div>
                <div style='margin-bottom: 10px;'>
                    <span style='float: right;'>التوقيع: </span>
                    <span style='float: left;'>________________</span>
                    <div style='clear: both;'></div>
                        </div>
                    </div>
                </div>
        """

    def _create_print_button(self, customer_copy, system_copy):
        """Create styled print button"""
        print_btn = ModernButton("طباعة")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        print_btn.clicked.connect(lambda: self.send_to_printer(customer_copy, system_copy))
        return print_btn

    def print_received_transaction(self, item=None):
        """Print received transaction receipt."""
        try:
            # Get transaction data from table
            if item is None or isinstance(item, bool):
                selected_items = self.received_table.selectedItems()
                if not selected_items:
                    QMessageBox.warning(self, "تحذير", "الرجاء تحديد تحويل لطباعته")
                    return
                row = selected_items[0].row()
            else:
                row = item.row()

            # Check transaction status
            status = self.received_table.item(row, 7).text()
            if status != "مكتمل":
                QMessageBox.warning(self, "تحذير", "لا يمكن طباعة الإيصال للتحويلات غير المؤكدة")
                return

            # Collect transaction data
            amount_str = self.received_table.item(row, 4).text().replace(',', '')  # Remove commas
            
            transaction_data = {
                'id': self.received_table.item(row, 0).text(),
                'date': self.received_table.item(row, 1).text(),
                'sender': self.received_table.item(row, 2).text(),
                'receiver': self.received_table.item(row, 3).text(),
                'amount': float(amount_str),  # Convert clean string to float
                'currency': self.received_table.item(row, 5).text(),
                'receiver_governorate': self.received_table.item(row, 6).text(),
                'status': status,
                'employee_name': self.received_table.item(row, 9).text(),
                'sending_branch_name': self.received_table.item(row, 10).text(),
                'destination_branch_name': self.received_table.item(row, 11).text(),
                'branch_governorate': self.received_table.item(row, 12).text(),
                'received_status': self.received_table.item(row, 13).text(),
                'received_by': self.full_name,
                'received_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'received'
            }

            # Print the receipt using the standard print_receipt method
            self.print_receipt(transaction_data)

        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"حدث خطأ أثناء تحضير البيانات للطباعة: {str(e)}")

    def print_transaction(self, item):
        """Print outgoing transaction receipt (supports QTableView and QTableWidget)."""
        try:
            # إذا كان item عبارة عن dict (من النموذج)
            if isinstance(item, dict):
                transaction_data = item
            # إذا كان item عبارة عن transaction_id (str)
            elif isinstance(item, str):
                # ابحث عن الصف في النموذج
                model = getattr(self, 'transaction_model', None)
                if model:
                    for row in range(model.rowCount()):
                        tx = model.get_transaction(row)
                        if tx and tx.get('id') == item:
                            transaction_data = tx
                            break
                    else:
                        QMessageBox.warning(self, "خطأ", "لم يتم العثور على بيانات التحويل")
                        return
                else:
                    QMessageBox.warning(self, "خطأ", "لا يوجد نموذج بيانات")
                    return
            # إذا كان item عبارة عن QTableWidgetItem (قديم)
            else:
                row = item.row()
                # Clean amount string and convert to float
                amount_str = self.transactions_table.item(row, 4).text().replace(',', '')
                transaction_data = {
                    'id': self.transactions_table.item(row, 0).text(),
                    'date': self.transactions_table.item(row, 1).text(),
                    'sender': self.transactions_table.item(row, 2).text(),
                    'receiver': self.transactions_table.item(row, 3).text(),
                    'amount': float(amount_str),
                    'currency': self.transactions_table.item(row, 5).text(),
                    'receiver_governorate': self.transactions_table.item(row, 6).text(),
                    'status': self.transactions_table.item(row, 7).text(),
                    'employee_name': self.transactions_table.item(row, 8).text(),
                    'sending_branch_name': self.transactions_table.item(row, 9).text(),
                    'destination_branch_name': self.transactions_table.item(row, 10).text(),
                    'branch_governorate': self.transactions_table.item(row, 11).text(),
                    'type': 'sent'
                }
            # Print the receipt using the standard print_receipt method
            self.print_receipt(transaction_data)
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"حدث خطأ أثناء تحضير البيانات للطباعة: {str(e)}")            