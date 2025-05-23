from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from ui.custom_widgets import ModernGroupBox, ModernButton
from ui.theme import Theme
import requests
from datetime import datetime

class ProfitsWorker(QThread):
    finished = pyqtSignal(object, object, object, object)
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
                f"{self.api_url}/api/branches/{self.branch_id}/profits/",
                params=self.params,
                headers=headers
            )
            summary_response = requests.get(
                f"{self.api_url}/api/branches/{self.branch_id}/profits/summary/",
                headers=headers
            )
            stats_response = requests.get(
                f"{self.api_url}/api/branches/{self.branch_id}/profits/statistics/",
                headers=headers
            )
            self.finished.emit(response, summary_response, stats_response, None)
        except Exception as e:
            self.finished.emit(None, None, None, str(e))

class ProfitsTabMixin:
    def setup_profits_tab(self):
        """Set up the profits tab with modern UI components."""
        self.profits_tab = QWidget()
        layout = QVBoxLayout()
        
        # Summary Section
        summary_group = ModernGroupBox("ملخص الأرباح", "#2ecc71")
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(40)
        summary_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Total Profits (SYP)
        self.total_profits_syp = QLabel("0 ل.س")
        self.total_profits_syp.setFont(QFont("Cairo", 22, QFont.Weight.Bold))
        self.total_profits_syp.setStyleSheet("color: #27ae60; text-align: center;")
        profits_syp_container = QWidget()
        profits_syp_layout = QVBoxLayout()
        profits_syp_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profits_syp_label = QLabel("إجمالي الأرباح (ل.س)")
        profits_syp_label.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        profits_syp_label.setStyleSheet("color: #222; text-align: center;")
        profits_syp_layout.addWidget(profits_syp_label)
        profits_syp_layout.addWidget(self.total_profits_syp)
        profits_syp_container.setLayout(profits_syp_layout)
        summary_layout.addWidget(profits_syp_container)
        
        # Total Profits (USD)
        self.total_profits_usd = QLabel("$0.00")
        self.total_profits_usd.setFont(QFont("Cairo", 22, QFont.Weight.Bold))
        self.total_profits_usd.setStyleSheet("color: #2980b9; text-align: center;")
        profits_usd_container = QWidget()
        profits_usd_layout = QVBoxLayout()
        profits_usd_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profits_usd_label = QLabel("إجمالي الأرباح ($)")
        profits_usd_label.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        profits_usd_label.setStyleSheet("color: #222; text-align: center;")
        profits_usd_layout.addWidget(profits_usd_label)
        profits_usd_layout.addWidget(self.total_profits_usd)
        profits_usd_container.setLayout(profits_usd_layout)
        summary_layout.addWidget(profits_usd_container)
        
        # Total Transactions Count
        self.total_transactions = QLabel("0")
        self.total_transactions.setFont(QFont("Cairo", 22, QFont.Weight.Bold))
        self.total_transactions.setStyleSheet("color: #8e44ad; text-align: center;")
        transactions_container = QWidget()
        transactions_layout = QVBoxLayout()
        transactions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transactions_label = QLabel("عدد التحويلات")
        transactions_label.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        transactions_label.setStyleSheet("color: #222; text-align: center;")
        transactions_layout.addWidget(transactions_label)
        transactions_layout.addWidget(self.total_transactions)
        transactions_container.setLayout(transactions_layout)
        summary_layout.addWidget(transactions_container)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Filters Section
        filters_group = ModernGroupBox("تصفية", "#3498db")
        filters_layout = QHBoxLayout()
        
        # Date Range
        date_from_label = QLabel("من تاريخ:")
        filters_layout.addWidget(date_from_label)
        
        self.profits_date_from = QDateEdit()
        self.profits_date_from.setCalendarPopup(True)
        self.profits_date_from.setDisplayFormat("dd/MM/yyyy")
        self.profits_date_from.setDate(QDate.currentDate().addMonths(-1))
        filters_layout.addWidget(self.profits_date_from)
        
        date_to_label = QLabel("إلى تاريخ:")
        filters_layout.addWidget(date_to_label)
        
        self.profits_date_to = QDateEdit()
        self.profits_date_to.setCalendarPopup(True)
        self.profits_date_to.setDisplayFormat("dd/MM/yyyy")
        self.profits_date_to.setDate(QDate.currentDate())
        filters_layout.addWidget(self.profits_date_to)
        
        # Currency Filter
        currency_label = QLabel("العملة:")
        filters_layout.addWidget(currency_label)
        
        self.profits_currency_filter = QComboBox()
        self.profits_currency_filter.addItems(["الكل", "ليرة سورية", "دولار أمريكي"])
        filters_layout.addWidget(self.profits_currency_filter)
        
        # Apply Filters Button
        apply_filters_btn = ModernButton("تطبيق", color="#2ecc71")
        apply_filters_btn.clicked.connect(self.load_profits_data)
        filters_layout.addWidget(apply_filters_btn)

        # زر تحديث جديد
        refresh_btn = ModernButton("تحديث", color="#3498db")
        refresh_btn.clicked.connect(self.force_refresh_profits)
        filters_layout.addWidget(refresh_btn)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Profits Table
        self.profits_table = QTableWidget()
        self.profits_table.setColumnCount(10)  # Increased columns
        self.profits_table.setHorizontalHeaderLabels([
            "رقم التحويل",
            "التاريخ",
            "المبلغ المستفاد",
            "نسبة الضريبة",
            "مبلغ الضريبة",
            "ربح المبلغ المستفاد",
            "ربح الضريبة",
            "إجمالي الربح",
            "العملة",
            "الحالة"
        ])
        
        # Set table properties
        self.profits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profits_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        layout.addWidget(self.profits_table)
        
        # Export Button
        export_btn = ModernButton("تصدير التقرير", color="#e67e22")
        export_btn.clicked.connect(self.export_profits_report)
        layout.addWidget(export_btn)
        
        # Set the layout
        self.profits_tab.setLayout(layout)
        
        # لا تحميل تلقائي للبيانات هنا
        # self.load_profits_data()  # تم التعليق أو الإزالة
        self._is_loading_profits = False
    
    def load_profits_data(self):
        """Load profits data using QThread"""
        if getattr(self, '_is_loading_profits', False):
            return
        self._is_loading_profits = True
        
        # مؤشر تحميل في الجدول
        self.profits_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري التحميل ...")
        loading_item.setForeground(QColor("#2980b9"))
        self.profits_table.setItem(0, 0, loading_item)
        for col in range(1, self.profits_table.columnCount()):
            self.profits_table.setItem(0, col, QTableWidgetItem(""))
            
        # إعداد المعطيات
        start_date = self.profits_date_from.date().toString("yyyy-MM-dd")
        end_date = self.profits_date_to.date().toString("yyyy-MM-dd")
        currency_filter = self.profits_currency_filter.currentText()
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        if currency_filter != "الكل":
            params["currency"] = "SYP" if currency_filter == "ليرة سورية" else "USD"
            
        # تشغيل الخيط
        self.profits_worker = ProfitsWorker(self.api_url, self.branch_id, self.token, params)
        self._profits_worker_ref = self.profits_worker  # احتفظ بمرجع إضافي
        self.profits_worker.finished.connect(self.on_profits_loaded)
        self.profits_worker.start()
    
    def on_profits_loaded(self, response, summary_response, stats_response, error):
        # لا تخرج من الدالة إلا بعد إعادة تعيين المتحول
        try:
            if error:
                self.profits_table.setRowCount(1)
                error_item = QTableWidgetItem(f"فشل التحميل: {error}")
                error_item.setForeground(QColor("#e74c3c"))
                self.profits_table.setItem(0, 0, error_item)
                for col in range(1, self.profits_table.columnCount()):
                    self.profits_table.setItem(0, col, QTableWidgetItem(""))
                self.statusBar().showMessage(f"فشل تحميل الأرباح: {error}", 5000)
                return
            if (response is None or summary_response is None or stats_response is None or
                response.status_code != 200 or summary_response.status_code != 200 or stats_response.status_code != 200):
                if response is not None:
                    print("Profits response:", getattr(response, 'text', None))
                if summary_response is not None:
                    print("Summary response:", getattr(summary_response, 'text', None))
                if stats_response is not None:
                    print("Stats response:", getattr(stats_response, 'text', None))
                self.profits_table.setRowCount(1)
                error_item = QTableWidgetItem("فشل تحميل البيانات من الخادم (تحقق من الصلاحيات أو التواريخ)")
                error_item.setForeground(QColor("#e74c3c"))
                self.profits_table.setItem(0, 0, error_item)
                for col in range(1, self.profits_table.columnCount()):
                    self.profits_table.setItem(0, col, QTableWidgetItem(""))
                self.statusBar().showMessage("فشل تحميل الأرباح: تحقق من الصلاحيات أو التواريخ أو وجود بيانات", 5000)
                return
            data = response.json()
            summary_data = summary_response.json()
            stats_data = stats_response.json()
            self.update_profits_display(data, summary_data, stats_data)
        finally:
            self._is_loading_profits = False
    
    def update_profits_display(self, data, summary_data, stats_data):
        """Update the profits display with the received data."""
        try:
            # Update summary statistics
            total_syp = data.get('total_profits_syp', 0)
            total_usd = data.get('total_profits_usd', 0)
            total_count = data.get('total_transactions', 0)
            
            # Update monthly/yearly summaries
            monthly_profits = summary_data.get('profits', {})
            monthly_syp = monthly_profits.get('SYP', 0)
            monthly_usd = monthly_profits.get('USD', 0)
            
            # Update statistics
            avg_profit_syp = stats_data.get('average_profit', {}).get('SYP', 0)
            avg_profit_usd = stats_data.get('average_profit', {}).get('USD', 0)
            highest_profit = stats_data.get('highest_profit', {})
            
            # Update summary labels with enhanced formatting
            self.total_profits_syp.setText(f"{total_syp:,.2f} ل.س")
            self.total_profits_syp.setToolTip(
                f"المتوسط: {avg_profit_syp:,.2f} ل.س\n"
                f"الشهري: {monthly_syp:,.2f} ل.س\n"
                f"من المبلغ المستفاد: {data.get('benefited_profits_syp', 0):,.2f} ل.س\n"
                f"من الضرائب: {data.get('tax_profits_syp', 0):,.2f} ل.س"
            )
            
            self.total_profits_usd.setText(f"${total_usd:,.2f}")
            self.total_profits_usd.setToolTip(
                f"المتوسط: ${avg_profit_usd:,.2f}\n"
                f"الشهري: ${monthly_usd:,.2f}\n"
                f"من المبلغ المستفاد: ${data.get('benefited_profits_usd', 0):,.2f}\n"
                f"من الضرائب: ${data.get('tax_profits_usd', 0):,.2f}"
            )
            
            self.total_transactions.setText(str(total_count))
            self.total_transactions.setToolTip(
                f"أعلى ربح: {highest_profit.get('amount', 0):,.2f} {highest_profit.get('currency', '')}\n"
                f"التاريخ: {highest_profit.get('date', '')}"
            )
            
            # Clear and populate table
            self.profits_table.setRowCount(0)
            transactions = data.get('transactions', [])
            self.profits_table.setRowCount(len(transactions))
            
            for row, tx in enumerate(transactions):
                try:
                    self.profits_table.setItem(row, 0, QTableWidgetItem(str(tx.get('id', ''))))
                    date = str(tx.get('date', ''))
                    date_item = QTableWidgetItem(date)
                    date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.profits_table.setItem(row, 1, date_item)
                    benefited_amount = float(tx.get('benefited_amount', 0))
                    benefited_item = QTableWidgetItem(f"{benefited_amount:,.2f}")
                    benefited_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.profits_table.setItem(row, 2, benefited_item)
                    tax_rate = float(tx.get('tax_rate', 0))
                    tax_rate_item = QTableWidgetItem(f"{tax_rate:.2f}%")
                    tax_rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.profits_table.setItem(row, 3, tax_rate_item)
                    tax_amount = float(tx.get('tax_amount', 0))
                    tax_item = QTableWidgetItem(f"{tax_amount:,.2f}")
                    tax_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.profits_table.setItem(row, 4, tax_item)
                    benefited_profit = float(tx.get('benefited_profit', 0))
                    benefited_profit_item = QTableWidgetItem(f"{benefited_profit:,.2f}")
                    benefited_profit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.profits_table.setItem(row, 5, benefited_profit_item)
                    tax_profit = float(tx.get('tax_profit', 0))
                    tax_profit_item = QTableWidgetItem(f"{tax_profit:,.2f}")
                    tax_profit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.profits_table.setItem(row, 6, tax_profit_item)
                    total_profit = benefited_profit + tax_profit
                    total_profit_item = QTableWidgetItem(f"{total_profit:,.2f}")
                    total_profit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if (tx.get('currency') == 'SYP' and total_profit > avg_profit_syp) or (tx.get('currency') == 'USD' and total_profit > avg_profit_usd):
                        total_profit_item.setForeground(QColor('#27ae60'))
                    self.profits_table.setItem(row, 7, total_profit_item)
                    currency_item = QTableWidgetItem(str(tx.get('currency', '')))
                    currency_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.profits_table.setItem(row, 8, currency_item)
                    status = str(tx.get('status', ''))
                    status_item = QTableWidgetItem(self.get_status_text(status))
                    status_item.setForeground(self.get_status_color(status))
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.profits_table.setItem(row, 9, status_item)
                except Exception as e:
                    print(f"Exception in filling row {row}: {e}")
        except Exception as e:
            print(f"Error in update_profits_display: {e}")
    
    def get_status_text(self, status):
        """Get Arabic text for transaction status."""
        status_map = {
            'completed': 'مكتمل',
            'processing': 'قيد المعالجة',
            'cancelled': 'ملغي',
            'pending': 'معلق'
        }
        return status_map.get(status.lower(), status)
    
    def get_status_color(self, status):
        """Get the color for a transaction status."""
        colors = {
            'completed': QColor('#27ae60'),
            'processing': QColor('#f39c12'),
            'cancelled': QColor('#c0392b'),
            'pending': QColor('#7f8c8d')
        }
        return colors.get(status.lower(), QColor('#7f8c8d'))
    
    def export_profits_report(self):
        """Export the profits report to CSV."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import csv
            
            # Get save file name
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "حفظ التقرير",
                "",
                "CSV Files (*.csv)"
            )
            
            if file_name:
                with open(file_name, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    
                    # Write headers
                    headers = [
                        "رقم التحويل", "التاريخ", "المبلغ المستفاد",
                        "نسبة الضريبة", "مبلغ الضريبة", "ربح المبلغ المستفاد",
                        "ربح الضريبة", "إجمالي الربح", "العملة", "الحالة"
                    ]
                    writer.writerow(headers)
                    
                    # Write data
                    for row in range(self.profits_table.rowCount()):
                        row_data = []
                        for col in range(self.profits_table.columnCount()):
                            item = self.profits_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                        
        except Exception as e:
            print(f"Error exporting profits report: {e}")

    def force_refresh_profits(self):
        """إعادة تحميل بيانات الأرباح بغض النظر عن حالة التحميل السابقة"""
        self._is_loading_profits = False
        self.load_profits_data() 