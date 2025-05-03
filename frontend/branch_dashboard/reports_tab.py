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
                "page": self.report_current_page,
                "per_page": self.report_per_page
            }

            try:
                # Fetch outgoing transactions (صادر)
                if transfer_type in ["صادر", "الكل"]:
                    outgoing_params = base_params.copy()
                    outgoing_params["branch_id"] = self.branch_id
                    outgoing_response = requests.get(
                        f"{self.api_url}/reports/transactions/",
                        params={k: v for k, v in outgoing_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if outgoing_response.status_code == 200:
                        outgoing_data = outgoing_response.json()
                        for t in outgoing_data.get("items", []):
                            t["transaction_type"] = "outgoing"
                        all_transactions.extend(outgoing_data.get("items", []))
                        self.report_total_pages = outgoing_data.get("total_pages", 1)

                # Fetch incoming transactions (وارد)
                if transfer_type in ["وارد", "الكل"]:
                    incoming_params = base_params.copy()
                    incoming_params["destination_branch_id"] = self.branch_id
                    incoming_response = requests.get(
                        f"{self.api_url}/reports/transactions/",
                        params={k: v for k, v in incoming_params.items() if v is not None},
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=15
                    )
                    if incoming_response.status_code == 200:
                        incoming_data = incoming_response.json()
                        for t in incoming_data.get("items", []):
                            t["transaction_type"] = "incoming"
                        all_transactions.extend(incoming_data.get("items", []))
                        if transfer_type == "الكل":
                            self.report_total_pages = max(self.report_total_pages, incoming_data.get("total_pages", 1))
                        else:
                            self.report_total_pages = incoming_data.get("total_pages", 1)

            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "خطأ", f"فشل الاتصال بالخادم: {str(e)}")
                return

            # Sort transactions by date descending
            all_transactions.sort(
                key=lambda x: datetime.strptime(x.get("date", "1900-01-01"), "%Y-%m-%dT%H:%M:%S.%f"),
                reverse=True
            )

            # Populate table
            self.transfer_report_table.setRowCount(len(all_transactions))
            valid_count = 0

            for row, transaction in enumerate(all_transactions):
                try:
                    # Type indicator
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

                    # Date parsing and formatting
                    date_str = transaction.get("date", "")
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
                        formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            formatted_date = date_str
                    self.transfer_report_table.setItem(row, 5, QTableWidgetItem(formatted_date))

                    # Status display
                    status = transaction.get("status", "").lower()
                    status_ar = get_status_arabic(status)
                    status_item = QTableWidgetItem(status_ar)
                    status_item.setBackground(get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.transfer_report_table.setItem(row, 6, status_item)

                    # Branch information
                    sending_branch = transaction.get("sending_branch_name", "غير معروف")
                    receiving_branch = transaction.get("destination_branch_name", "غير معروف")
                    self.transfer_report_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                    self.transfer_report_table.setItem(row, 8, QTableWidgetItem(receiving_branch))

                    # Employee information
                    employee_name = transaction.get("employee_name", "غير معروف")
                    self.transfer_report_table.setItem(row, 9, QTableWidgetItem(employee_name))

                    valid_count += 1

                except Exception as field_error:
                    logger.error(f"Error processing row {row}: {str(field_error)}")
                    continue

            # Update UI
            self.update_pagination_controls()
            self.statusBar().showMessage(f"تم تحميل {valid_count} معاملة صالحة", 5000)

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء إنشاء التقرير: {str(e)}")
            
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