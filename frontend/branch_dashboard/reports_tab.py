import requests
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout,
    QWidget, QTabWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, 
)
import csv
from datetime import datetime
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from utils.helpers import get_status_arabic, get_status_color
from PyQt6.QtGui import QColor

class ReportWorker(QThread):
    finished = pyqtSignal(object, object)
    def __init__(self, api_url, branch_id, token, base_params, transfer_type, report_current_page, report_per_page):
        super().__init__()
        self.api_url = api_url
        self.branch_id = branch_id
        self.token = token
        self.base_params = base_params
        self.transfer_type = transfer_type
        self.report_current_page = report_current_page
        self.report_per_page = report_per_page
    def run(self):
        all_transactions = []
        total_pages = 1
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            # Fetch outgoing transactions (صادر)
            if self.transfer_type in ["صادر", "الكل"]:
                outgoing_params = self.base_params.copy()
                outgoing_params["branch_id"] = self.branch_id
                outgoing_response = requests.get(
                    f"{self.api_url}/reports/transactions/",
                    params={k: v for k, v in outgoing_params.items() if v is not None},
                    headers=headers,
                    timeout=15
                )
                if outgoing_response.status_code == 200:
                    outgoing_data = outgoing_response.json()
                    for t in outgoing_data.get("items", []):
                        t["transaction_type"] = "outgoing"
                    all_transactions.extend(outgoing_data.get("items", []))
                    total_pages = outgoing_data.get("total_pages", 1)
                else:
                    self.finished.emit(None, f"فشل تحميل التحويلات الصادرة: {outgoing_response.status_code}")
                    return
            # Fetch incoming transactions (وارد)
            if self.transfer_type in ["وارد", "الكل"]:
                incoming_params = self.base_params.copy()
                incoming_params["destination_branch_id"] = self.branch_id
                incoming_response = requests.get(
                    f"{self.api_url}/reports/transactions/",
                    params={k: v for k, v in incoming_params.items() if v is not None},
                    headers=headers,
                    timeout=15
                )
                if incoming_response.status_code == 200:
                    incoming_data = incoming_response.json()
                    for t in incoming_data.get("items", []):
                        t["transaction_type"] = "incoming"
                    all_transactions.extend(incoming_data.get("items", []))
                    if self.transfer_type == "الكل":
                        total_pages = max(total_pages, incoming_data.get("total_pages", 1))
                    else:
                        total_pages = incoming_data.get("total_pages", 1)
                else:
                    self.finished.emit(None, f"فشل تحميل التحويلات الواردة: {incoming_response.status_code}")
                    return
            self.finished.emit({"transactions": all_transactions, "total_pages": total_pages}, None)
        except Exception as e:
            self.finished.emit(None, str(e))

class EmployeeReportWorker(QThread):
    finished = pyqtSignal(object, object)
    def __init__(self, api_url, branch_id, token, params):
        super().__init__()
        self.api_url = api_url
        self.branch_id = branch_id
        self.token = token
        self.params = params
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/reports/employees/",
                params=self.params,
                headers=headers,
                timeout=15
            )
            self.finished.emit(response, None)
        except Exception as e:
            self.finished.emit(None, str(e))

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
        """Generate transfer report with QThread and loading indicator"""
        if getattr(self, '_is_loading_report', False):
            return  # منع التكرار
        self._is_loading_report = True
        self.transfer_report_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري التحميل ...")
        loading_item.setForeground(Qt.GlobalColor.blue)
        self.transfer_report_table.setItem(0, 0, loading_item)
        for col in range(1, self.transfer_report_table.columnCount()):
            self.transfer_report_table.setItem(0, col, QTableWidgetItem(""))
        self.statusBar().showMessage("جاري تحميل التقرير...")
        QApplication.processEvents()
        if self.report_date_from.date() > self.report_date_to.date():
            QMessageBox.warning(self, "خطأ في التاريخ", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
            self._is_loading_report = False
            return
        date_from = self.report_date_from.date().toString("yyyy-MM-dd")
        date_to = self.report_date_to.date().toString("yyyy-MM-dd")
        status_filter = {
            "مكتمل": "completed",
            "قيد المعالجة": "processing",
            "ملغي": "cancelled",
            "مرفوض": "rejected",
            "معلق": "on_hold",
            "الكل": None
        }.get(self.status_combo.currentText())
        transfer_type = self.transfer_type_combo.currentText()
        base_params = {
            "start_date": date_from,
            "end_date": date_to,
            "status": status_filter,
            "page": self.report_current_page,
            "per_page": self.report_per_page
        }
        self.report_worker = ReportWorker(self.api_url, self.branch_id, self.token, base_params, transfer_type, self.report_current_page, self.report_per_page)
        self.report_worker.finished.connect(self.on_report_loaded)
        self.report_worker.start()

    def on_report_loaded(self, result, error):
        self._is_loading_report = False
        if error:
            self.transfer_report_table.setRowCount(1)
            error_item = QTableWidgetItem(f"فشل التحميل: {error}")
            error_item.setForeground(Qt.GlobalColor.red)
            self.transfer_report_table.setItem(0, 0, error_item)
            for col in range(1, self.transfer_report_table.columnCount()):
                self.transfer_report_table.setItem(0, col, QTableWidgetItem(""))
            self.statusBar().showMessage(str(error), 5000)
            return
        if result is None or "transactions" not in result:
            self.transfer_report_table.setRowCount(1)
            error_item = QTableWidgetItem("فشل تحميل البيانات من الخادم")
            error_item.setForeground(Qt.GlobalColor.red)
            self.transfer_report_table.setItem(0, 0, error_item)
            for col in range(1, self.transfer_report_table.columnCount()):
                self.transfer_report_table.setItem(0, col, QTableWidgetItem(""))
            self.statusBar().showMessage("فشل تحميل البيانات من الخادم", 5000)
            return
        all_transactions = result["transactions"]
        self.report_total_pages = result["total_pages"]
        # Sort transactions by date descending
        all_transactions.sort(
            key=lambda x: datetime.strptime(x.get("date", "1900-01-01"), "%Y-%m-%dT%H:%M:%S.%f"),
            reverse=True
        )
        self.transfer_report_table.setRowCount(len(all_transactions))
        valid_count = 0
        for row, transaction in enumerate(all_transactions):
            try:
                type_item = self.create_transaction_type_item(transaction)
                self.transfer_report_table.setItem(row, 0, type_item)
                trans_id = str(transaction.get("id", ""))
                id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                id_item.setToolTip(trans_id)
                self.transfer_report_table.setItem(row, 1, id_item)
                self.transfer_report_table.setItem(row, 2, QTableWidgetItem(transaction.get("sender", "غير معروف")))
                self.transfer_report_table.setItem(row, 3, QTableWidgetItem(transaction.get("receiver", "غير معروف")))
                amount = transaction.get("amount", 0)
                try:
                    amount = float(amount)
                except (TypeError, ValueError):
                    amount = 0.0
                currency = transaction.get("currency", "ليرة سورية")
                amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.transfer_report_table.setItem(row, 4, amount_item)
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
                status = transaction.get("status", "").lower()
                status_ar = get_status_arabic(status)
                status_item = QTableWidgetItem(status_ar)
                status_item.setBackground(get_status_color(status))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.transfer_report_table.setItem(row, 6, status_item)
                sending_branch = transaction.get("sending_branch_name", "غير معروف")
                receiving_branch = transaction.get("destination_branch_name", "غير معروف")
                self.transfer_report_table.setItem(row, 7, QTableWidgetItem(sending_branch))
                self.transfer_report_table.setItem(row, 8, QTableWidgetItem(receiving_branch))
                employee_name = transaction.get("employee_name", "غير معروف")
                self.transfer_report_table.setItem(row, 9, QTableWidgetItem(employee_name))
                valid_count += 1
            except Exception as field_error:
                print(f"[DEBUG] خطأ في الصف {row}: {field_error}")
                continue
        self.update_pagination_controls()
        self.statusBar().showMessage(f"تم تحميل {valid_count} معاملة صالحة", 5000)
        
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

    def generate_employee_report(self):
        if getattr(self, '_is_loading_employee_report', False):
            return
        self._is_loading_employee_report = True
        self.employee_report_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري التحميل ...")
        loading_item.setForeground(Qt.GlobalColor.blue)
        self.employee_report_table.setItem(0, 0, loading_item)
        for col in range(1, self.employee_report_table.columnCount()):
            self.employee_report_table.setItem(0, col, QTableWidgetItem(""))
        # اجمع الفلاتر المطلوبة من الواجهة (مثال: الحالة، الدور)
        params = {}
        # مثال: params["status"] = self.status_combo.currentText() ...
        self.employee_report_worker = EmployeeReportWorker(self.api_url, self.branch_id, self.token, params)
        self.employee_report_worker.finished.connect(self.on_employee_report_loaded)
        self.employee_report_worker.start()

    def on_employee_report_loaded(self, response, error):
        self._is_loading_employee_report = False
        if error or response is None or response.status_code != 200:
            self.employee_report_table.setRowCount(1)
            error_item = QTableWidgetItem(f"فشل التحميل: {error or 'خطأ في الخادم'}")
            error_item.setForeground(Qt.GlobalColor.red)
            self.employee_report_table.setItem(0, 0, error_item)
            for col in range(1, self.employee_report_table.columnCount()):
                self.employee_report_table.setItem(0, col, QTableWidgetItem(""))
            return
        employees = response.json().get("employees", [])
        self.employee_report_table.setRowCount(len(employees))
        for row, employee in enumerate(employees):
            username_item = QTableWidgetItem(employee.get("username", "غير معروف"))
            self.employee_report_table.setItem(row, 0, username_item)
            role = employee.get("role", "employee")
            role_text = "مدير فرع" if role == "branch_manager" else "موظف"
            role_item = QTableWidgetItem(role_text)
            self.employee_report_table.setItem(row, 1, role_item)
            is_active = employee.get("is_active", employee.get("active", False))
            status_text = "نشط" if is_active else "غير نشط"
            status_item = QTableWidgetItem(status_text)
            color = QColor("#27ae60") if is_active else QColor("#e74c3c")
            status_item.setForeground(color)
            self.employee_report_table.setItem(row, 2, status_item)
            created_at = employee.get("created_at", "غير معروف")
            created_item = QTableWidgetItem(created_at)
            self.employee_report_table.setItem(row, 3, created_item)
            last_active = employee.get("last_login", employee.get("last_activity", "غير معروف"))
            last_active_item = QTableWidgetItem(last_active)
            self.employee_report_table.setItem(row, 4, last_active_item)
        self.statusBar().showMessage("تم تحميل تقرير الموظفين بنجاح", 3000)                            