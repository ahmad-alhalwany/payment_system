import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QWidget, 
    QTabWidget, QLabel, QHeaderView, QFormLayout, QPushButton
)

from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from ui.branch_management_improved import AddBranchDialog, EditBranchDialog
from ui.custom_widgets import ModernGroupBox, ModernButton
from ui.theme import Theme
import requests
from ui.tax_management import TaxManagementDialog
from config import get_api_url
import time

API_BASE_URL = get_api_url()

class BranchDataCache:
    """Cache for branch data to reduce API calls and improve performance"""
    
    def __init__(self, cache_duration=300):  # 5 minutes default cache duration
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_duration = cache_duration
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._cleanup_expired_cache)
        self._update_timer.start(60000)  # Cleanup every minute
        
    def get(self, key):
        """Get cached data if it exists and is not expired"""
        if key in self._cache:
            if time.time() - self._cache_timestamps[key] < self._cache_duration:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._cache_timestamps[key]
        return None
        
    def set(self, key, value):
        """Cache data with current timestamp"""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        
    def invalidate(self, key=None):
        """Invalidate specific cache entry or all cache if no key provided"""
        if key:
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            
    def _cleanup_expired_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp >= self._cache_duration
        ]
        for key in expired_keys:
            del self._cache[key]
            del self._cache_timestamps[key]

class BranchManagementMixin:
    """Mixin handling all branch-related operations"""
    
    def __init__(self):
        """Initialize the mixin with cache, batch processing, and auto-refresh timer"""
        self.branch_cache = BranchDataCache()
        self._batch_size = 50  # Number of rows to process at once
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._process_batch)
        self._pending_updates = []
        # Auto-refresh timer for branches table (every 90 seconds)
        self._branches_auto_refresh_timer = QTimer()
        self._branches_auto_refresh_timer.setInterval(90000)  # 90,000 ms = 90 seconds
        self._branches_auto_refresh_timer.timeout.connect(self._auto_refresh_branches)
        self._branches_auto_refresh_timer.start()
        # Temporary local cache for updated tax rates
        self._local_tax_cache = {}
        
    def _process_batch(self):
        """Process a batch of pending updates"""
        if not self._pending_updates:
            self._update_timer.stop()
            return
            
        batch = self._pending_updates[:self._batch_size]
        self._pending_updates = self._pending_updates[self._batch_size:]
        
        for update_func in batch:
            update_func()
            
        if self._pending_updates:
            self._update_timer.start(50)  # Process next batch after 50ms
            
    def _queue_update(self, update_func):
        """Queue an update function for batch processing"""
        self._pending_updates.append(update_func)
        if not self._update_timer.isActive():
            self._update_timer.start(50)

    def _auto_refresh_branches(self):
        """Auto-refresh the branches table and show a message."""
        self.branch_cache.invalidate('branches')
        self.load_branches()
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage("تم تحديث بيانات الفروع تلقائيًا.", 3000)
        elif hasattr(self, 'statusBar') and callable(self.statusBar):
            self.statusBar().showMessage("تم تحديث بيانات الفروع تلقائيًا.", 3000)

    def setup_branches_tab(self):
        """Set up the branches tab."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("إدارة الفروع")
        title.setFont(QFont(Theme.FONT_PRIMARY, int(Theme.FONT_SIZE_TITLE[:-2]), QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                margin-bottom: 20px;
            }}
        """)
        layout.addWidget(title)
        
        # Branches table
        self.branches_table = QTableWidget()
        self.branches_table.setStyleSheet(Theme.TABLE_STYLE)
        self.branches_table.setColumnCount(8)
        self.branches_table.setHorizontalHeaderLabels([
            "رمز الفرع", 
            "اسم الفرع", 
            "الموقع", 
            "المحافظة", 
            "عدد الموظفين",
            "الرصيد (ل.س)",
            "الرصيد ($)",
            "الضريبة (%)"
        ])
        
        # Set table properties
        self.branches_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.branches_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.branches_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branches_table.horizontalHeader().setFixedHeight(40)
        self.branches_table.verticalHeader().setDefaultSectionSize(40)
        self.branches_table.setAlternatingRowColors(True)
        
        # Set fixed column widths
        total_width = self.branches_table.viewport().width()
        column_widths = {
            0: 100,  # رمز الفرع
            1: 200,  # اسم الفرع
            2: 150,  # الموقع
            3: 120,  # المحافظة
            4: 100,  # عدد الموظفين
            5: 120,  # الرصيد (ل.س)
            6: 120,  # الرصيد ($)
            7: 100   # الضريبة (%)
        }
        
        # Apply fixed widths
        for col, width in column_widths.items():
            self.branches_table.setColumnWidth(col, width)
            
        # Prevent horizontal header from being resized
        self.branches_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        
        layout.addWidget(self.branches_table)
        
        # First row of buttons
        first_row_layout = QHBoxLayout()
        
        add_branch_button = ModernButton("إضافة فرع", color=Theme.SUCCESS)
        add_branch_button.clicked.connect(self.add_branch)
        first_row_layout.addWidget(add_branch_button)
        
        edit_branch_button = ModernButton("تعديل الفرع", color=Theme.ACCENT)
        edit_branch_button.clicked.connect(self.edit_branch)
        first_row_layout.addWidget(edit_branch_button)
        
        delete_branch_button = ModernButton("حذف الفرع", color=Theme.ERROR)
        delete_branch_button.clicked.connect(self.delete_branch)
        first_row_layout.addWidget(delete_branch_button)
        
        view_branch_button = ModernButton("عرض تفاصيل الفرع", color=Theme.WARNING)
        view_branch_button.clicked.connect(self.view_branch)
        first_row_layout.addWidget(view_branch_button)
        
        layout.addLayout(first_row_layout)
        
        # Second row of buttons
        second_row_layout = QHBoxLayout()
        
        allocate_button = ModernButton("تعيين رصيد", color=Theme.ACCENT)
        allocate_button.clicked.connect(self.allocate_funds)
        second_row_layout.addWidget(allocate_button)
        
        view_fund_history = ModernButton("سجل التمويل", color=Theme.SUCCESS)
        view_fund_history.clicked.connect(self.view_fund_history)
        second_row_layout.addWidget(view_fund_history)
        
        add_tax_button = ModernButton("إضافة ضريبة", color=Theme.PRIMARY)
        add_tax_button.clicked.connect(self.add_tax)
        second_row_layout.addWidget(add_tax_button)
        
        refresh_button = ModernButton("تحديث", color=Theme.ACCENT)
        refresh_button.clicked.connect(self.load_branches)
        second_row_layout.addWidget(refresh_button)
        
        layout.addLayout(second_row_layout)
        
        # Apply theme to tab
        self.branches_tab.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_PRIMARY};
                color: {Theme.TEXT_PRIMARY};
                font-family: {Theme.FONT_PRIMARY};
                font-size: {Theme.FONT_SIZE_NORMAL};
            }}
        """)
        
        self.branches_tab.setLayout(layout)
        
    def load_branches(self, force_refresh=False):
        """Load branches from the API with optimized performance using QThread."""
        try:
            if not force_refresh:
                cached_data = self.branch_cache.get('branches')
                if cached_data:
                    self._update_branches_table(cached_data)
                    return
            # استخدم worker لجلب البيانات في الخلفية
            self.branch_load_worker = BranchLoadWorker(API_BASE_URL, self.token)
            self.branch_load_worker.branches_loaded.connect(self._on_branches_loaded)
            self.branch_load_worker.error_occurred.connect(self._on_branches_error)
            self.branch_load_worker.start()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def _on_branches_loaded(self, branches):
        self.branch_cache.set('branches', branches)
        self._update_branches_table(branches)

    def _on_branches_error(self, msg):
        QMessageBox.warning(self, "خطأ", msg)

    def _update_branches_table(self, branches):
        """Update branches table with batched processing"""
        # Clear existing rows while preserving column widths
        self.branches_table.setRowCount(0)
        
        # Pre-allocate rows for better performance
        self.branches_table.setRowCount(len(branches))
        
        # Process branches in batches
        for i in range(0, len(branches), self._batch_size):
            batch = branches[i:i + self._batch_size]
            self._queue_update(lambda b=batch, start=i: self._process_branch_batch(b, start))
            
    def _process_branch_batch(self, batch, start_row):
        """Process a batch of branches"""
        for idx, branch in enumerate(batch):
            if not isinstance(branch, dict):
                continue
                
            row_position = start_row + idx
            
            # Get branch data with proper error handling
            branch_id = branch.get('id')
            
            # Use local tax cache if available
            if branch_id in self._local_tax_cache:
                tax_rate = self._local_tax_cache[branch_id]
            else:
                tax_rate = branch.get('tax_rate', 0)
                if tax_rate < 1 and tax_rate != 0:
                    tax_rate = tax_rate * 100
            
            items = [
                (str(branch.get('branch_id', '')), branch_id),
                (branch.get('name', ''), None),
                (branch.get('location', ''), None),
                (branch.get('governorate', ''), None),
                (str(branch.get('employee_count', 0)), None),
                (f"{branch.get('allocated_amount_syp', 0):,.2f}", None),
                (f"{branch.get('allocated_amount_usd', 0):,.2f}", None),
                (f"{float(tax_rate):.2f}%", None)
            ]
            
            # Batch set items for better performance
            for col, (display_value, user_role_data) in enumerate(items):
                item = QTableWidgetItem(display_value)
                if user_role_data is not None:
                    item.setData(Qt.ItemDataRole.UserRole, user_role_data)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.branches_table.setItem(row_position, col, item)
                
        # Update viewport after batch
        self.branches_table.viewport().update()

    def add_branch(self):
        """Open dialog to add a new branch."""
        dialog = AddBranchDialog(self.token, self)
        if dialog.exec() == 1:  # If dialog was accepted
            self.branch_cache.invalidate('branches')
            self.load_branches()  # Refresh the branches list
            self.load_branches_for_filter()  # Refresh branch filters
            self.load_dashboard_data()  # Refresh dashboard data
    
    def edit_branch(self):
        """Open dialog to edit the selected branch."""
        selected_rows = self.branches_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع للتعديل")
            return
        
        row = selected_rows[0].row()
        branch_id = self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{API_BASE_URL}/branches/{branch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                branch_data = response.json()
                dialog = EditBranchDialog(branch_data, self.token, self)
                if dialog.exec() == 1:  # If dialog was accepted
                    self.branch_cache.invalidate('branches')
                    self.load_branches()  # Refresh the branches list
                    self.load_branches_for_filter()  # Refresh branch filters
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل بيانات الفرع: رمز الحالة {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")
    
    def delete_branch(self):
        """Delete the selected branch."""
        selected_rows = self.branches_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع للحذف")
            return
        
        row = selected_rows[0].row()
        branch_id = self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        branch_name = self.branches_table.item(row, 1).text()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "تأكيد الحذف", 
            f"هل أنت متأكد من حذف الفرع '{branch_name}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                } if self.token else {}
                
                response = requests.delete(
                    f"{API_BASE_URL}/branches/{branch_id}/", 
                    headers=headers
                )
                
                if response.status_code == 204:
                    QMessageBox.information(self, "نجاح", "تم حذف الفرع بنجاح")
                    self.branch_cache.invalidate('branches')
                    self.load_branches()  # Refresh the branches list
                    self.load_branches_for_filter()  # Refresh branch filters
                    self.load_dashboard_data()  # Refresh dashboard data
                else:
                    # Try to get detailed error message
                    error_msg = f"فشل حذف الفرع: رمز الحالة {response.status_code}"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            error_msg = error_data["detail"]
                        elif "message" in error_data:
                            error_msg = error_data["message"]
                    except:
                        pass
                    
                    QMessageBox.warning(self, "خطأ", error_msg)
                    
            except requests.exceptions.RequestException as e:
                QMessageBox.warning(
                    self, 
                    "خطأ في الاتصال", 
                    f"تعذر الاتصال بالخادم: {str(e)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "خطأ غير متوقع", 
                    f"حدث خطأ غير متوقع: {str(e)}"
                )
    
    def view_branch(self):
        """View details of the selected branch."""
        selected_rows = self.branches_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع للعرض")
            return
        
        row = selected_rows[0].row()
        branch_id = self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{API_BASE_URL}/branches/{branch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                branch_data = response.json()
                
                # Create a dialog to display branch details
                dialog = QDialog(self)
                dialog.setWindowTitle(f"تفاصيل الفرع: {branch_data.get('name', '')}")
                dialog.setGeometry(150, 150, 600, 400)
                dialog.setStyleSheet(f"""
                    QDialog {{
                        background-color: {Theme.BG_PRIMARY};
                        font-family: {Theme.FONT_PRIMARY};
                    }}
                    QLabel {{
                        color: {Theme.TEXT_PRIMARY};
                    }}
                """)
                
                layout = QVBoxLayout()
                
                # Branch details
                details_group = ModernGroupBox("معلومات الفرع", Theme.ACCENT)
                details_layout = QFormLayout()
                
                details_layout.addRow("رمز الفرع:", QLabel(branch_data.get("branch_id", "")))
                details_layout.addRow("اسم الفرع:", QLabel(branch_data.get("name", "")))
                details_layout.addRow("الموقع:", QLabel(branch_data.get("location", "")))
                details_layout.addRow("المحافظة:", QLabel(branch_data.get("governorate", "")))
                
                details_group.setLayout(details_layout)
                layout.addWidget(details_group)
                
                # Branch employees
                employees_group = ModernGroupBox("موظفي الفرع", "#2ecc71")
                employees_layout = QVBoxLayout()
                
                employees_table = QTableWidget()
                employees_table.setColumnCount(3)
                employees_table.setHorizontalHeaderLabels(["اسم المستخدم", "الدور", "تاريخ الإنشاء"])
                employees_table.horizontalHeader().setStretchLastSection(True)
                employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                
                try:
                    headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                    response = requests.get(
                                f"{API_BASE_URL}/branches/{branch_id}/employees/", 
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        employees = response.json()
                        employees_table.setRowCount(len(employees))
                        
                        for i, employee in enumerate(employees):
                            employees_table.setItem(i, 0, QTableWidgetItem(employee.get("username", "")))
                            
                            # Map role to Arabic
                            role = employee.get("role", "")
                            role_arabic = "موظف"
                            if role == "director":
                                role_arabic = "مدير"
                            elif role == "branch_manager":
                                role_arabic = "مدير فرع"
                            
                            employees_table.setItem(i, 1, QTableWidgetItem(role_arabic))
                            employees_table.setItem(i, 2, QTableWidgetItem(employee.get("created_at", "")))
                except Exception as e:
                    print(f"Error loading branch employees: {e}")
                
                employees_layout.addWidget(employees_table)
                employees_group.setLayout(employees_layout)
                layout.addWidget(employees_group)
                
                # Branch statistics
                stats_group = ModernGroupBox("إحصائيات الفرع", "#e74c3c")
                stats_layout = QFormLayout()
                
                try:
                    headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                    
                    # Get employee stats
                    emp_response = requests.get(
                                f"{API_BASE_URL}/branches/{branch_id}/employees/stats/", 
                        headers=headers
                    )
                    if emp_response.status_code == 200:
                        emp_data = emp_response.json()
                        stats_layout.addRow("عدد الموظفين:", QLabel(str(emp_data.get("total", 0))))
                    
                    # Get transaction stats
                    trans_response = requests.get(
                                f"{API_BASE_URL}/branches/{branch_id}/transactions/stats/", 
                        headers=headers
                    )
                    if trans_response.status_code == 200:
                        trans_data = trans_response.json()
                        stats_layout.addRow("عدد التحويلات:", QLabel(str(trans_data.get("total", 0))))
                        stats_layout.addRow("إجمالي المبالغ:", QLabel(f"{trans_data.get('total_amount', 0):,.2f}"))
                except Exception as e:
                    print(f"Error loading branch statistics: {e}")
                
                stats_group.setLayout(stats_layout)
                layout.addWidget(stats_group)
                
                # Close button
                close_button = ModernButton("إغلاق", color=Theme.ERROR)
                close_button.clicked.connect(dialog.accept)
                layout.addWidget(close_button)
                
                dialog.setLayout(layout)
                dialog.exec()
            else:
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل بيانات الفرع: رمز الحالة {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")
        
    def load_branches_for_filter(self):
        """Load branches for filter dropdowns in all tabs."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = self.api_client.get_branches()
            
            if response.status_code == 200:
                response_data = response.json()
                branches = response_data.get("branches", [])
                
                # Clear and populate branch filter in Employees tab
                if hasattr(self, 'branch_filter'):
                    self.branch_filter.clear()
                    self.branch_filter.addItem("جميع الفروع", None)  # إضافة خيار "الكل"
                    
                    for branch in branches:
                        branch_id = branch.get("id")
                        branch_name = branch.get("name", "")
                        if branch_id and branch_name:
                            # تخزين الـ ID كبيانات مرفقة مع الاسم
                            self.branch_filter.addItem(branch_name, branch_id)
                
                # Clear and populate branch filter in Transactions tab
                if hasattr(self, 'transaction_branch_filter'):
                    self.transaction_branch_filter.clear()
                    self.transaction_branch_filter.addItem("جميع الفروع", None)
                    
                    for branch in branches:
                        branch_id = branch.get("id")
                        branch_name = branch.get("name", "")
                        if branch_id and branch_name:
                            self.transaction_branch_filter.addItem(branch_name, branch_id)
                
                # Clear and populate branch filter in Reports tab
                if hasattr(self, 'report_branch_filter'):
                    self.report_branch_filter.clear()
                    self.report_branch_filter.addItem("جميع الفروع", None)
                    
                    for branch in branches:
                        branch_id = branch.get("id")
                        branch_name = branch.get("name", "")
                        if branch_id and branch_name:
                            self.report_branch_filter.addItem(branch_name, branch_id)
                
                # Create branch_id_to_name mapping for future use
                self.branch_id_to_name = {}
                for branch in branches:
                    branch_id = branch.get("id")
                    branch_name = branch.get("name", "")
                    if branch_id and branch_name:
                        self.branch_id_to_name[branch_id] = branch_name
                            
        except Exception as e:
            print(f"Error loading branches: {e}")
            QMessageBox.warning(self, "خطأ", "تعذر تحميل قائمة الفروع")
            
    def load_branch_stats(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{API_BASE_URL}/branches/stats/", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                branches = data.get("branches", [])
                
                # Update branches count in dashboard
                self.branches_count.setText(str(data.get("total", 0)))
                
                if not branches:
                    self.transfers_bars.setText("لا توجد بيانات متاحة")
                    self.amounts_bars.setText("لا توجد بيانات متاحة")
                    return
                
                # Get top 3 branches for transfers
                top_transfers = sorted(
                    branches, 
                    key=lambda x: x['transactions_count'], 
                    reverse=True
                )[:3]

                # Get top 3 branches for amounts
                top_amounts = sorted(
                    branches, 
                    key=lambda x: x['total_amount'], 
                    reverse=True
                )[:3]

                # Prepare transfers HTML
                transfers_html = ["<table width='100%'>"]
                if top_transfers:
                    max_transfers = max(t['transactions_count'] for t in top_transfers)
                    for branch in top_transfers:
                        width = (branch['transactions_count'] / max_transfers * 80) if max_transfers != 0 else 0
                        transfers_html.append(
                            f"<tr>"
                            f"<td width='30%' align='right'>{branch['name']}</td>"
                            f"<td width='60%'><div style='background: #3498db; height: 20px; width: {width}%; "
                            f"border-radius: 10px; margin: 2px;'></div></td>"
                            f"<td width='10%' align='left'>{branch['transactions_count']}</td>"
                            f"</tr>"
                        )
                transfers_html.append("</table>")
                
                # Prepare amounts HTML
                amounts_html = ["<table width='100%'>"]
                if top_amounts:
                    max_amount = max(a['total_amount'] for a in top_amounts)
                    for branch in top_amounts:
                        width = (branch['total_amount'] / max_amount * 80) if max_amount != 0 else 0
                        amounts_html.append(
                            f"<tr>"
                            f"<td width='30%' align='right'>{branch['name']}</td>"
                            f"<td width='60%'><div style='background: #e74c3c; height: 20px; width: {width}%; "
                            f"border-radius: 10px; margin: 2px;'></div></td>"
                            f"<td width='10%' align='left'>{branch['total_amount']:,.2f}</td>"
                            f"</tr>"
                        )
                amounts_html.append("</table>")

                self.transfers_bars.setText("".join(transfers_html))
                self.amounts_bars.setText("".join(amounts_html))
            else:
                self.transfers_bars.setText("حدث خطأ في جلب البيانات")
                self.amounts_bars.setText("حدث خطأ في جلب البيانات")

        except Exception as e:
            print(f"Error loading branch stats: {e}")
            self.transfers_bars.setText("تعذر تحميل بيانات التحويلات")
            self.amounts_bars.setText("تعذر تحميل بيانات المبالغ")
            
            
    def view_fund_history(self):
        selected_rows = self.branches_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد فرع لعرض السجل")
            return
        
        row = selected_rows[0].row()
        branch_id = self.branches_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        branch_name = self.branches_table.item(row, 1).text()
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"سجل التمويل - {branch_name}")
        dialog.setGeometry(100, 100, 800, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        tab_widget = QTabWidget()
        
        # إنشاء تبويبات للعملات
        syp_tab = QWidget()
        usd_tab = QWidget()
        tab_widget.addTab(syp_tab, "السجلات بالليرة السورية")
        tab_widget.addTab(usd_tab, "السجلات بالدولار الأمريكي")
        
        # إنشاء الجداول
        syp_table = self.create_currency_table("SYP")
        usd_table = self.create_currency_table("USD")
        
        # تعبئة البيانات
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{API_BASE_URL}/branches/{branch_id}/funds-history",
                headers=headers
            )
            
            if response.status_code == 200:
                history = response.json()
                syp_records = [r for r in history if r.get("currency") == "SYP"]
                usd_records = [r for r in history if r.get("currency") == "USD"]
                
                self.populate_table(syp_table, syp_records, "ل.س")
                self.populate_table(usd_table, usd_records, "$")
                
        except Exception as e:
            QMessageBox.warning(dialog, "خطأ", f"خطأ في جلب البيانات: {str(e)}")
        
        # إضافة الجداول إلى التبويبات
        self.setup_tab(syp_tab, syp_table)
        self.setup_tab(usd_tab, usd_table)
        
        layout.addWidget(tab_widget)
        dialog.setLayout(layout)
        dialog.exec()

    def create_currency_table(self, currency):
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["التاريخ", "النوع", "المبلغ", "العملة", "الوصف"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def populate_table(self, table, records, currency_symbol):
        table.setRowCount(len(records))
        for row, record in enumerate(records):
            date_item = QTableWidgetItem(record.get("date", "غير معروف"))
            type_item = QTableWidgetItem({
                "allocation": "إيداع",
                "deduction": "خصم"
            }.get(record.get("type"), record.get("type")))
            amount_item = QTableWidgetItem(f"{record.get('amount', 0):,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            currency_item = QTableWidgetItem(currency_symbol)
            desc_item = QTableWidgetItem(record.get("description", ""))
            
            table.setItem(row, 0, date_item)
            table.setItem(row, 1, type_item)
            table.setItem(row, 2, amount_item)
            table.setItem(row, 3, currency_item)
            table.setItem(row, 4, desc_item)

    def setup_tab(self, tab, table):
        layout = QVBoxLayout()
        layout.addWidget(table)
        tab.setLayout(layout)

    def add_tax(self):
        """Add or update tax rate for a branch."""
        selected_row = self.branches_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار فرع من الجدول")
            return
        
        try:
            # Get branch data from the selected row
            branch_id = self.branches_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            current_tax_rate = float(self.branches_table.item(selected_row, 7).text().replace('%', ''))
            
            # Create tax management dialog with correct parameters
            dialog = TaxManagementDialog(
                branch_data={
                    "branch_id": branch_id,
                    "name": self.branches_table.item(selected_row, 1).text(),
                    "tax_rate": current_tax_rate
                },
                token=self.token,
                parent=self
            )
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    # Get the updated tax rate from the dialog
                    new_tax_rate = float(dialog.tax_rate_input.text())
                    
                    # Update the tax rate in the backend using the correct endpoint
                    response = requests.put(
                        f"{API_BASE_URL}/api/branches/{branch_id}/tax_rate/",
                        json={"tax_rate": new_tax_rate},
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
                    
                    if response.status_code == 200:
                        # Store the new tax rate in the local cache (temporary workaround)
                        self._local_tax_cache[branch_id] = new_tax_rate
                        # Update the tax rate in the branches table
                        tax_item = QTableWidgetItem(f"{new_tax_rate:.2f}%")
                        tax_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.branches_table.setItem(selected_row, 7, tax_item)
                        
                        QMessageBox.information(self, "نجاح", "تم تحديث نسبة الضريبة بنجاح")
                        # Invalidate cache before refreshing
                        self.branch_cache.invalidate('branches')
                        # Force refresh the branches table to ensure all data is up to date
                        self.load_branches(force_refresh=True)
                    else:
                        error_msg = "فشل في تحديث نسبة الضريبة"
                        try:
                            error_data = response.json()
                            if "detail" in error_data:
                                error_msg = f"{error_msg}: {error_data['detail']}"
                        except:
                            error_msg = f"{error_msg}: {response.status_code}"
                        
                        QMessageBox.warning(self, "تحذير", error_msg)
                        
                except ValueError as e:
                    QMessageBox.warning(self, "خطأ", "قيمة نسبة الضريبة غير صالحة")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"حدث خطأ غير متوقع: {str(e)}")
                    
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ في قراءة بيانات الفرع: {str(e)}")

    def closeEvent(self, event):
        if hasattr(self, 'branch_load_worker') and self.branch_load_worker.isRunning():
            self.branch_load_worker.quit()
            self.branch_load_worker.wait()
        super().closeEvent(event)

class BranchLoadWorker(QThread):
    branches_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_url, token):
        super().__init__()
        self.api_url = api_url
        self.token = token
    
    def run(self):
        import requests
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(
                f"{self.api_url}/branches/",
                headers=headers,
                params={
                    "include_tax": True,
                    "include_employee_count": True,
                    "include_balances": True
                }
            )
            if response.status_code == 200:
                response_data = response.json()
                branches = response_data.get('branches', []) if isinstance(response_data, dict) else response_data
                self.branches_loaded.emit(branches)
            else:
                error_msg = f"فشل في تحميل الفروع: رمز الحالة {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        error_msg = f"{error_msg}\n{error_data['detail']}"
                except:
                    pass
                self.error_occurred.emit(error_msg)
        except Exception as e:
            self.error_occurred.emit(str(e))