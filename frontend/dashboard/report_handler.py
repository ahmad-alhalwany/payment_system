from PyQt6.QtWidgets import (
    QGridLayout, QGroupBox, QLabel, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, 
    QVBoxLayout, QHBoxLayout, QHeaderView
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from ui.custom_widgets import ModernGroupBox, ModernButton
from utils.helpers import get_status_arabic, get_status_color
import requests

class ReportWorker(QThread):
    result_ready = pyqtSignal(dict, str)
    error_occurred = pyqtSignal(str)
    def __init__(self, url, headers, params, report_type):
        super().__init__()
        self.url = url
        self.headers = headers
        self.params = params
        self.report_type = report_type
    def run(self):
        try:
            response = requests.get(self.url, headers=self.headers, params=self.params)
            if response.status_code == 200:
                self.result_ready.emit(response.json(), self.report_type)
            else:
                try:
                    error_data = response.json()
                    msg = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    msg = f"HTTP {response.status_code}"
                self.error_occurred.emit(msg)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ReportHandlerMixin:
    """Mixin class handling report generation and export functionality"""
    
    def setup_reports_tab(self):
        """Set up the reports tab."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("التقارير")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Report options
        options_group = ModernGroupBox("خيارات التقرير", "#3498db")
        options_layout = QGridLayout()
        
        # Report type
        report_type_label = QLabel("نوع التقرير:")
        options_layout.addWidget(report_type_label, 0, 0)
        
        self.report_type = QComboBox()
        self.report_type.addItems(["تقرير التحويلات", "تقرير الفروع", "تقرير الموظفين"])
        options_layout.addWidget(self.report_type, 0, 1)
        
        # Date range
        date_range_label = QLabel("نطاق التاريخ:")
        options_layout.addWidget(date_range_label, 1, 0)
        
        date_range_layout = QHBoxLayout()
        
        from_date_label = QLabel("من:")
        date_range_layout.addWidget(from_date_label)
        
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-30))  # Last 30 days
        date_range_layout.addWidget(self.from_date)
        
        to_date_label = QLabel("إلى:")
        date_range_layout.addWidget(to_date_label)
        
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        date_range_layout.addWidget(self.to_date)
        
        options_layout.addLayout(date_range_layout, 1, 1)
        
        # Branch filter
        branch_filter_label = QLabel("الفرع:")
        options_layout.addWidget(branch_filter_label, 2, 0)
        
        self.report_branch_filter = QComboBox()
        options_layout.addWidget(self.report_branch_filter, 2, 1)
        
        # Generate button
        generate_button = ModernButton("إنشاء التقرير", color="#2ecc71")
        generate_button.clicked.connect(self.generate_report)
        options_layout.addWidget(generate_button, 3, 0, 1, 2)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Report preview
        preview_group = ModernGroupBox("معاينة التقرير", "#e74c3c")
        preview_layout = QVBoxLayout()
        
        self.report_table = QTableWidget()
        preview_layout.addWidget(self.report_table)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        export_pdf_button = ModernButton("تصدير PDF", color="#3498db")
        export_pdf_button.clicked.connect(self.export_pdf)
        export_layout.addWidget(export_pdf_button)
        
        export_excel_button = ModernButton("تصدير Excel", color="#f39c12")
        export_excel_button.clicked.connect(self.export_excel)
        export_layout.addWidget(export_excel_button)
        
        export_print_button = ModernButton("طباعة", color="#9b59b6")
        export_print_button.clicked.connect(self.print_report)
        export_layout.addWidget(export_print_button)
        
        preview_layout.addLayout(export_layout)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        self.reports_tab.setLayout(layout)

    def generate_report(self):
        """Generate a report based on the selected options."""
        report_type_map = {
            "تقرير التحويلات": "transactions",
            "تقرير الفروع": "branch",
            "تقرير الموظفين": "employees"
        }
        report_type = report_type_map.get(self.report_type.currentText(), "transactions")
        start_date = self.from_date.date().toString("yyyy-MM-dd")
        end_date = self.to_date.date().toString("yyyy-MM-dd")
        branch_id = self.report_branch_filter.currentData()
        if branch_id == self.api_url:
            branch_id = None
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        params = {}
        url = None
        if report_type == "transactions":
            params["start_date"] = start_date
            params["end_date"] = end_date
            if branch_id:
                params["branch_id"] = branch_id
            url = f"{self.api_url}/transactions/"
        elif report_type == "branch":
            params["start_date"] = start_date
            params["end_date"] = end_date
            if branch_id:
                params["branch_id"] = branch_id
            url = f"{self.api_url}/reports/branch/"
        elif report_type == "employees":
            if branch_id:
                params["branch_id"] = branch_id
            url = f"{self.api_url}/users/"
        else:
            self.statusBar().showMessage("نوع التقرير غير مدعوم", 5000)
            return
        self.statusBar().showMessage("جاري تحميل التقرير...")
        self.report_table.setRowCount(0)
        self.report_worker = ReportWorker(url, headers, params, report_type)
        self.report_worker.result_ready.connect(self._on_report_data_ready)
        self.report_worker.error_occurred.connect(self._on_report_error)
        self.report_worker.start()

    def _on_report_data_ready(self, data, report_type):
        if report_type == "transactions":
            items = data.get("transactions", [])
        elif report_type == "branch":
            items = []
            branch_report = data.get("branch_report", {})
            for branch_id, stats in branch_report.items():
                branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}")
                items.append({
                    "branch_id": branch_id,
                    "name": branch,
                    "total_syp": stats.get("total_syp", 0),
                    "total_usd": stats.get("total_usd", 0),
                    "count": stats.get("count", 0)
                })
        elif report_type == "employees":
            items = data.get("users", [])
        elif report_type == "daily":
            items = []
            daily_report = data.get("daily_report", {})
            for date_str, stats in daily_report.items():
                items.append({
                    "date": date_str,
                    "total_syp": stats.get("total_syp", 0),
                    "total_usd": stats.get("total_usd", 0),
                    "count": stats.get("count", 0)
                })
        else:
            items = []
        
        # Set up table columns based on report type
        if report_type == "transactions":
            self.report_table.setColumnCount(10)
            self.report_table.setHorizontalHeaderLabels([
                "النوع", "رقم التحويل", "المرسل", "المستلم", "المبلغ", 
                "التاريخ", "الحالة", "الفرع المرسل", "الفرع المستلم", "اسم الموظف"
            ])
        elif report_type == "branch":
            self.report_table.setColumnCount(5)
            self.report_table.setHorizontalHeaderLabels([
                "رقم الفرع", "اسم الفرع", "إجمالي الليرة", "إجمالي الدولار", "عدد التحويلات"
            ])
        elif report_type == "employees":
            self.report_table.setColumnCount(5)
            self.report_table.setHorizontalHeaderLabels([
                "اسم المستخدم", "الدور", "الفرع", "تاريخ الإنشاء", "الحالة"
            ])
        elif report_type == "daily":
            self.report_table.setColumnCount(4)
            self.report_table.setHorizontalHeaderLabels([
                "التاريخ", "إجمالي الليرة", "إجمالي الدولار", "عدد التحويلات"
            ])
        
        self.report_table.setRowCount(len(items))
        
        # Load branch names if not cached
        if not hasattr(self, 'branch_id_to_name') or not self.branch_id_to_name:
            self.branch_id_to_name = {}
            branches_response = self.api_client.get_branches()
            if branches_response.status_code == 200:
                branches = branches_response.json().get("branches", [])
                self.branch_id_to_name = {b["id"]: b["name"] for b in branches}
        
        for i, item in enumerate(items):
            if report_type == "transactions":
                transaction_type = self.determine_transaction_type(item)
                type_item = QTableWidgetItem(transaction_type)
                if transaction_type == "داخلي":
                    type_item.setForeground(QColor(0, 128, 0))
                elif transaction_type == "صادر":
                    type_item.setForeground(QColor(255, 0, 0))
                elif transaction_type == "وارد":
                    type_item.setForeground(QColor(0, 0, 255))
                self.report_table.setItem(i, 0, type_item)
                trans_id = str(item.get("id", ""))
                id_item = QTableWidgetItem(trans_id[:8] + "..." if len(trans_id) > 8 else trans_id)
                id_item.setToolTip(trans_id)
                self.report_table.setItem(i, 1, id_item)
                self.report_table.setItem(i, 2, QTableWidgetItem(item.get("sender", "")))
                self.report_table.setItem(i, 3, QTableWidgetItem(item.get("receiver", "")))
                amount = item.get("amount", 0)
                currency = item.get("currency", "ليرة سورية")
                amount_item = QTableWidgetItem(f"{amount:,.2f} {currency}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.report_table.setItem(i, 4, amount_item)
                date_str = item.get("date", "")
                self.report_table.setItem(i, 5, QTableWidgetItem(date_str))
                status = item.get("status", "").lower()
                status_ar = get_status_arabic(status)
                status_item = QTableWidgetItem(status_ar)
                status_item.setBackground(get_status_color(status))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.report_table.setItem(i, 6, status_item)
                branch_id = item.get("branch_id")
                sending_branch = self.branch_id_to_name.get(branch_id, f"الفرع {branch_id}" if branch_id else "غير معروف")
                self.report_table.setItem(i, 7, QTableWidgetItem(sending_branch))
                dest_branch_id = item.get("destination_branch_id")
                receiving_branch = self.branch_id_to_name.get(dest_branch_id, f"الفرع {dest_branch_id}" if dest_branch_id else "غير معروف")
                self.report_table.setItem(i, 8, QTableWidgetItem(receiving_branch))
                self.report_table.setItem(i, 9, QTableWidgetItem(item.get("employee_name", "")))
                self.report_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, item)
            elif report_type == "branch":
                self.report_table.setItem(i, 0, QTableWidgetItem(str(item.get("branch_id", ""))))
                self.report_table.setItem(i, 1, QTableWidgetItem(item.get("name", "")))
                self.report_table.setItem(i, 2, QTableWidgetItem(f"{item.get('total_syp', 0):,.2f}"))
                self.report_table.setItem(i, 3, QTableWidgetItem(f"{item.get('total_usd', 0):,.2f}"))
                self.report_table.setItem(i, 4, QTableWidgetItem(str(item.get("count", 0))))
            elif report_type == "employees":
                self.report_table.setItem(i, 0, QTableWidgetItem(item.get("username", "")))
                self.report_table.setItem(i, 1, QTableWidgetItem(item.get("role", "")))
                branch_name = self.branch_id_to_name.get(item.get("branch_id"), "غير معروف")
                self.report_table.setItem(i, 2, QTableWidgetItem(branch_name))
                self.report_table.setItem(i, 3, QTableWidgetItem(item.get("created_at", "")))
                status = "نشط" if item.get("role") != "deleted" else "محذوف"
                self.report_table.setItem(i, 4, QTableWidgetItem(status))
            elif report_type == "daily":
                self.report_table.setItem(i, 0, QTableWidgetItem(item.get("date", "")))
                self.report_table.setItem(i, 1, QTableWidgetItem(f"{item.get('total_syp', 0):,.2f}"))
                self.report_table.setItem(i, 2, QTableWidgetItem(f"{item.get('total_usd', 0):,.2f}"))
                self.report_table.setItem(i, 3, QTableWidgetItem(str(item.get("count", 0))))
        
        self.report_table.horizontalHeader().setStretchLastSection(True)
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.setSortingEnabled(True)
        self.statusBar().showMessage("تم إنشاء التقرير بنجاح", 3000)
        QMessageBox.information(self, "نجاح", "تم إنشاء التقرير بنجاح")

    def _on_report_error(self, msg):
        self.statusBar().showMessage(msg, 5000)
        QMessageBox.warning(self, "خطأ", msg)

    def export_pdf(self):
        """Export the current report as PDF."""
        if self.report_table.rowCount() == 0:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للتصدير. الرجاء إنشاء تقرير أولاً.")
            return
            
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument
            
            # Get file name from user
            file_path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير كـ PDF", "", "ملفات PDF (*.pdf)"
            )
            
            if not file_path:
                return  # User canceled
                
            # Add .pdf extension if not present
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
                
            # Create printer
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            
            # Create HTML content
            html = "<html><head><style>"
            html += "table { width: 100%; border-collapse: collapse; direction: rtl; }"
            html += "th, td { border: 1px solid #000; padding: 8px; text-align: right; }"
            html += "th { background-color: #f2f2f2; }"
            html += "h1 { text-align: center; color: #2c3e50; }"
            html += ".status-completed { background-color: #d5f5e3; }"  # Light green
            html += ".status-processing { background-color: #d6eaf8; }" # Light blue
            html += ".status-cancelled { background-color: #f5b7b1; }"  # Light red
            html += ".status-rejected { background-color: #f1948a; }"   # Darker red
            html += ".status-on_hold { background-color: #fdebd0; }"    # Light orange
            html += "</style></head><body>"
            
            # Add title based on report type
            report_title = self.report_type.currentText()
            html += f"<h1>{report_title}</h1>"
            
            # Add date range
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")
            html += f"<p style='text-align: center;'>الفترة من {from_date} إلى {to_date}</p>"
            
            # Create table
            html += "<table><tr>"
            
            # Add headers
            for col in range(self.report_table.columnCount()):
                header_text = self.report_table.horizontalHeaderItem(col).text()
                html += f"<th>{header_text}</th>"
            html += "</tr>"
            
            # Add data rows
            for row in range(self.report_table.rowCount()):
                html += "<tr>"
                
                # Get status for styling
                status_item = None
                status_class = ""
                if self.report_type.currentText() == "تقرير التحويلات":
                    status_item = self.report_table.item(row, 6)  # Status column
                    if status_item:
                        status_text = status_item.text().lower()
                        if "مكتمل" in status_text:
                            status_class = "status-completed"
                        elif "قيد المعالجة" in status_text:
                            status_class = "status-processing"
                        elif "ملغي" in status_text:
                            status_class = "status-cancelled"
                        elif "مرفوض" in status_text:
                            status_class = "status-rejected"
                        elif "معلق" in status_text:
                            status_class = "status-on_hold"
                
                for col in range(self.report_table.columnCount()):
                    item = self.report_table.item(row, col)
                    text = item.text() if item else ""
                    
                    # Apply status class to the entire row for transaction reports
                    if self.report_type.currentText() == "تقرير التحويلات" and status_class:
                        html += f"<td class='{status_class}'>{text}</td>"
                    else:
                        html += f"<td>{text}</td>"
                html += "</tr>"
            
            html += "</table></body></html>"
            
            # Print to PDF
            document = QTextDocument()
            document.setHtml(html)
            document.print(printer)
            
            QMessageBox.information(self, "نجاح", f"تم تصدير التقرير بنجاح إلى:\n{file_path}")
            
        except Exception as e:
            print(f"Error exporting to PDF: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تصدير التقرير: {str(e)}")

    def export_excel(self):
        """Export the current report as Excel."""
        if self.report_table.rowCount() == 0:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للتصدير. الرجاء إنشاء تقرير أولاً.")
            return
            
        try:
            # Get file name from user
            file_path, _ = QFileDialog.getSaveFileName(
                self, "حفظ التقرير كـ Excel", "", "ملفات Excel (*.xlsx)"
            )
            
            if not file_path:
                return  # User canceled
                
            # Add .xlsx extension if not present
            if not file_path.lower().endswith('.xlsx'):
                file_path += '.xlsx'
                
            # Create Excel workbook
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
            
            wb = openpyxl.Workbook()
            ws = wb.active
            
            # Set title based on report type
            report_title = self.report_type.currentText()
            ws.title = report_title
            
            # Add title
            ws.merge_cells('A1:G1')
            title_cell = ws['A1']
            title_cell.value = report_title
            title_cell.font = Font(size=16, bold=True)
            title_cell.alignment = Alignment(horizontal='center')
            
            # Add date range
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")
            ws.merge_cells('A2:G2')
            date_cell = ws['A2']
            date_cell.value = f"الفترة من {from_date} إلى {to_date}"
            date_cell.alignment = Alignment(horizontal='center')
            
            # Add headers
            header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            header_font = Font(bold=True)
            
            for col in range(self.report_table.columnCount()):
                header_text = self.report_table.horizontalHeaderItem(col).text()
                cell = ws.cell(row=4, column=col+1, value=header_text)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='right')
            
            # Add data rows
            for row in range(self.report_table.rowCount()):
                for col in range(self.report_table.columnCount()):
                    item = self.report_table.item(row, col)
                    text = item.text() if item else ""
                    cell = ws.cell(row=row+5, column=col+1, value=text)
                    cell.alignment = Alignment(horizontal='right')
            
            # Auto-adjust column widths
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column].width = adjusted_width
            
            # Save the workbook
            wb.save(file_path)
            
            QMessageBox.information(self, "نجاح", f"تم تصدير التقرير بنجاح إلى:\n{file_path}")
            
        except ImportError:
            QMessageBox.warning(self, "خطأ", "مكتبة openpyxl غير متوفرة. الرجاء تثبيتها باستخدام pip install openpyxl")
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تصدير التقرير: {str(e)}")

    def print_report(self):
        """Print the current report."""
        if self.report_table.rowCount() == 0:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للطباعة. الرجاء إنشاء تقرير أولاً.")
            return
            
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QTextDocument
            
            # Create printer
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            
            # Show print dialog
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            # Create HTML content
            html = "<html><head><style>"
            html += "table { width: 100%; border-collapse: collapse; direction: rtl; }"
            html += "th, td { border: 1px solid #000; padding: 8px; text-align: right; }"
            html += "th { background-color: #f2f2f2; }"
            html += "h1 { text-align: center; color: #2c3e50; }"
            html += "</style></head><body>"
            
            # Add title based on report type
            report_title = self.report_type.currentText()
            html += f"<h1>{report_title}</h1>"
            
            # Add date range
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")
            html += f"<p style='text-align: center;'>الفترة من {from_date} إلى {to_date}</p>"
            
            # Create table
            html += "<table><tr>"
            
            # Add headers
            for col in range(self.report_table.columnCount()):
                header_text = self.report_table.horizontalHeaderItem(col).text()
                html += f"<th>{header_text}</th>"
            html += "</tr>"
            
            # Add data rows
            for row in range(self.report_table.rowCount()):
                html += "<tr>"
                for col in range(self.report_table.columnCount()):
                    item = self.report_table.item(row, col)
                    text = item.text() if item else ""
                    html += f"<td>{text}</td>"
                html += "</tr>"
            
            html += "</table></body></html>"
            
            # Print
            document = QTextDocument()
            document.setHtml(html)
            document.print(printer)
            
        except Exception as e:
            print(f"Error printing report: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر طباعة التقرير: {str(e)}")

    def determine_transaction_type(self, transaction):
        """Determine transaction type based on branch information."""
        branch_id = transaction.get("branch_id")
        dest_branch_id = transaction.get("destination_branch_id")
        
        if branch_id and dest_branch_id:
            return "داخلي"  # Internal transfer between branches
        elif branch_id and not dest_branch_id:
            return "صادر"   # Outgoing transfer from branch
        elif not branch_id and dest_branch_id:
            return "وارد"   # Incoming transfer to branch
        else:
            return "غير معروف"  # Unknown type