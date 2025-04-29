import requests
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout,
    QWidget, QTabWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, 
)
import csv
from datetime import datetime
from PyQt6.QtCore import Qt
from utils.helpers import get_status_arabic, get_status_color

class ReportsTabMixin:
    
    
    def setup_reports_tab(self):
        """Set up the reports tab with separate sections for transfers and employees."""
        layout = QVBoxLayout()
        
        # Create tab widget for different report types
        report_tabs = QTabWidget()
        report_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #ddd;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
        """)
        
        # Transfers Report Tab
        transfers_tab = QWidget()
        self.setup_transfers_report_tab(transfers_tab)
        report_tabs.addTab(transfers_tab, "تقارير التحويلات")
        
        # Employees Report Tab
        employees_tab = QWidget()
        self.setup_employees_report_tab(employees_tab)
        report_tabs.addTab(employees_tab, "تقارير الموظفين")
        
        layout.addWidget(report_tabs)
        self.reports_tab.setLayout(layout)
        
    def generate_transfer_report(self):
        """Generate transfer report with accurate filtering and sorting"""
        try:
            # Clear previous data and initialize
            self.transfer_report_table.setRowCount(0)
            self.statusBar().showMessage("جاري تحميل التقرير...")
            QApplication.processEvents()

            # Validate date selection
            if self.report_date_from.date() > self.report_date_to.date():
                QMessageBox.warning(self, "خطأ في التاريخ", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
                return

            # Get date objects for filtering
            selected_start_date = self.report_date_from.date().toPyDate()
            selected_end_date = self.report_date_to.date().toPyDate()

            # Format dates for backend requests (without time)
            date_from = self.report_date_from.date().toString("yyyy-MM-dd")
            date_to = self.report_date_to.date().toString("yyyy-MM-dd")

            # Get status filter
            status_filter = {
                "مكتمل": "completed",
                "قيد المعالجة": "processing",
                "ملغي": "cancelled",
                "مرفوض": "rejected",
                "معلق": "on_hold",
                "الكل": None
            }.get(self.status_combo.currentText())

            all_transactions = []
            transfer_type = self.transfer_type_combo.currentText()

            # Common parameters for both outgoing and incoming
            base_params = {
                "start_date": date_from,
                "end_date": date_to,
                "status": status_filter,
                "page": 1,
                "per_page": 100
            }

            # Fetch outgoing transactions (صادر)
            if transfer_type in ["صادر", "الكل"]:
                outgoing_params = base_params.copy()
                outgoing_params["branch_id"] = self.branch_id
                outgoing_page = 1
                while True:
                    outgoing_response = requests.get(
                        f"{self.api_url}/transactions/",
                        params={k: v for k, v in outgoing_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if outgoing_response.status_code == 200:
                        outgoing_data = outgoing_response.json()
                        for t in outgoing_data.get("transactions", []):
                            t["transaction_type"] = "outgoing"
                        all_transactions.extend(outgoing_data.get("transactions", []))
                        if outgoing_page >= outgoing_data.get("total_pages", 1):
                            break
                        outgoing_page += 1
                        outgoing_params["page"] = outgoing_page
                    else:
                        break

            # Fetch incoming transactions (وارد)
            if transfer_type in ["وارد", "الكل"]:
                incoming_params = base_params.copy()
                incoming_params["destination_branch_id"] = self.branch_id
                incoming_page = 1
                while True:
                    incoming_response = requests.get(
                        f"{self.api_url}/transactions/",
                        params={k: v for k, v in incoming_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if incoming_response.status_code == 200:
                        incoming_data = incoming_response.json()
                        for t in incoming_data.get("transactions", []):
                            t["transaction_type"] = "incoming"
                        all_transactions.extend(incoming_data.get("transactions", []))
                        if incoming_page >= incoming_data.get("total_pages", 1):
                            break
                        incoming_page += 1
                        incoming_params["page"] = incoming_page
                    else:
                        break

            # Client-side filtering with proper date parsing and status check
            filtered_transactions = []
            for t in all_transactions:
                try:
                    # Parse transaction date
                    transaction_date = datetime.strptime(t.get("date", ""), "%Y-%m-%d %H:%M:%S").date()
                    
                    # Check date range
                    date_valid = selected_start_date <= transaction_date <= selected_end_date
                    
                    # Check status
                    status_valid = (status_filter is None) or (t.get("status", "").lower() == status_filter)
                    
                    if date_valid and status_valid:
                        filtered_transactions.append(t)
                except Exception as e:
                    print(f"Error processing transaction {t.get('id')}: {str(e)}")

            # Sort by date descending
            filtered_transactions.sort(
                key=lambda x: datetime.strptime(x.get("date", ""), "%Y-%m-%d %H:%M:%S"),
                reverse=True
            )

            # Apply pagination
            total_items = len(filtered_transactions)
            self.report_total_pages = max(1, (total_items + self.report_per_page - 1) // self.report_per_page)
            start_idx = (self.report_current_page - 1) * self.report_per_page
            end_idx = start_idx + self.report_per_page
            transactions = filtered_transactions[start_idx:end_idx]

            # Populate table
            self.transfer_report_table.setRowCount(len(transactions))
            valid_count = 0

            for row, transaction in enumerate(transactions):
                try:
                    # Validate mandatory fields
                    required_fields = ['id', 'sender', 'receiver', 'amount', 'date', 'status']
                    if not all(field in transaction for field in required_fields):
                        continue

                    # Transaction Type
                    type_item = self.create_transaction_type_item(transaction)
                    self.transfer_report_table.setItem(row, 0, type_item)

                    # Transaction ID
                    trans_id = str(transaction.get("id", ""))
                    id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                    id_item.setToolTip(trans_id)
                    self.transfer_report_table.setItem(row, 1, id_item)

                    # Sender/Receiver
                    self.transfer_report_table.setItem(row, 2, QTableWidgetItem(transaction.get("sender", "غير معروف")))
                    self.transfer_report_table.setItem(row, 3, QTableWidgetItem(transaction.get("receiver", "غير معروف")))

                    # Amount formatting
                    amount = transaction.get("amount", 0)
                    try:
                        amount = float(amount)
                    except (TypeError, ValueError):
                        amount = 0.0
                    currency = transaction.get("currency", "ليرة سورية")
                    amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.transfer_report_table.setItem(row, 4, amount_item)

                    # Date parsing
                    raw_date = transaction.get("date", "")
                    try:
                        date_obj = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                        date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        date_str = raw_date if raw_date else "غير معروف"
                    self.transfer_report_table.setItem(row, 5, QTableWidgetItem(date_str))

                    # Status display
                    status = transaction.get("status", "").lower()
                    status_ar = get_status_arabic(status)
                    status_item = QTableWidgetItem(status_ar)
                    status_item.setBackground(get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transfer_report_table.setItem(row, 6, status_item)

                    # Branch information
                    branch_id = transaction.get("branch_id")
                    dest_branch_id = transaction.get("destination_branch_id")
                    sending_branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}" if branch_id else "غير معروف")
                    receiving_branch = self.branch_id_to_name.get(dest_branch_id, f"الفرع {dest_branch_id}" if dest_branch_id else "غير معروف")
                    self.transfer_report_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                    self.transfer_report_table.setItem(row, 8, QTableWidgetItem(receiving_branch))

                    # Employee information
                    employee_name = transaction.get("employee_name") or f"الموظف {transaction.get('employee_id', '')}"
                    self.transfer_report_table.setItem(row, 9, QTableWidgetItem(employee_name))

                    valid_count += 1

                except Exception as field_error:
                    print(f"Error processing row {row}: {str(field_error)}")
                    continue

            # Update UI
            self.update_pagination_controls()
            self.statusBar().showMessage(f"تم تحميل {valid_count} معاملة صالحة", 5000)

        except requests.exceptions.RequestException as e:
            self.handle_connection_error(e)
        except ValueError as e:
            self.handle_data_error(e)
        except Exception as e:
            self.handle_unexpected_error(e)
            
    def export_transfer_report(self):
        """Export transfer report to CSV and PDF"""
        try:
            if self.transfer_report_table.rowCount() == 0:
                QMessageBox.warning(self, "تحذير", "لا يوجد بيانات للتصدير!")
                return

            # Get save path
            path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير", "", 
                "ملفات PDF (*.pdf);;ملفات CSV (*.csv)"
            )
            
            if not path:
                return  # User cancelled

            # Prepare data
            headers = [self.transfer_report_table.horizontalHeaderItem(i).text() 
                    for i in range(self.transfer_report_table.columnCount())]
            
            rows = []
            for row in range(self.transfer_report_table.rowCount()):
                rows.append([
                    self.transfer_report_table.item(row, col).text().strip()
                    for col in range(self.transfer_report_table.columnCount())
                ])

            # Export based on file type
            try:
                if path.lower().endswith('.csv'):
                    self.export_to_csv(path, headers, rows)
                    QMessageBox.information(self, "نجاح", "تم التصدير بنجاح!")
                
            except PermissionError:
                QMessageBox.critical(self, "خطأ", "الملف مفتوح في تطبيق آخر. أغلقه ثم حاول مرة أخرى")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تجهيز البيانات: {str(e)}")
            
    def export_employee_report(self):
        """Export employee report to CSV and PDF"""
        try:
            if self.employee_report_table.rowCount() == 0:
                QMessageBox.warning(self, "تحذير", "لا يوجد بيانات للتصدير!")
                return

            # Get save path
            path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير", "", 
                "ملفات PDF (*.pdf);;ملفات CSV (*.csv)"
            )
            
            if not path:
                return  # User cancelled

            # Prepare data
            headers = [self.employee_report_table.horizontalHeaderItem(i).text() 
                    for i in range(self.employee_report_table.columnCount())]
            
            rows = []
            for row in range(self.employee_report_table.rowCount()):
                rows.append([
                    self.employee_report_table.item(row, col).text().strip()
                    for col in range(self.employee_report_table.columnCount())
                ])

            # Export based on file type
            try:
                if path.lower().endswith('.csv'):
                    self.export_to_csv(path, headers, rows)
                    QMessageBox.information(self, "نجاح", "تم التصدير بنجاح!")
                
            except PermissionError:
                QMessageBox.critical(self, "خطأ", "الملف مفتوح في تطبيق آخر. أغلقه ثم حاول مرة أخرى")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تجهيز البيانات: {str(e)}")
        
    def export_to_csv(self, path, headers, rows):
        """Export data to CSV file"""
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)                            