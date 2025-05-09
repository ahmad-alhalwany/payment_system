from PyQt6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QDialog, QProgressDialog,
    QLabel, QVBoxLayout, QWidget
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from ui.user_management_improved import AddEmployeeDialog
from dashboard.table_manager import OptimizedTableManager
import requests
import time
import weakref
from typing import Dict, List, Optional, Any
from functools import lru_cache

class EmployeeLoadWorker(QThread):
    """Worker thread for loading employee data"""
    data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, api_url: str, token: str, branch_id: Optional[int] = None):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.branch_id = branch_id
        self._is_cancelled = False
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل بيانات الموظفين...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            url = f"{self.api_url}/users/"
            if self.branch_id:
                url += f"?branch_id={self.branch_id}"
                
            response = requests.get(url, headers=headers, timeout=30)
            
            if self._is_cancelled:
                return
                
            if response.status_code == 200:
                data = response.json()
                employees = data.get("users", [])
                self.data_loaded.emit(employees)
            else:
                self.error_occurred.emit(f"فشل تحميل البيانات: {response.status_code}")
                
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))
                
    def cancel(self):
        self._is_cancelled = True

class EmployeeCache:
    """Cache manager for employee data"""
    _instance = None
    
    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._cache_duration = 300  # 5 minutes
        
    def get(self, key: str) -> Optional[List[Dict]]:
        """Get cached data if valid"""
        if key in self._cache:
            if time.time() - self._timestamps[key] < self._cache_duration:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None
        
    def set(self, key: str, data: List[Dict]):
        """Cache data with timestamp"""
        self._cache[key] = data
        self._timestamps[key] = time.time()
        
    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        self._timestamps.clear()

class EmployeeManagementMixin:
    """Mixin handling all employee-related operations"""

    def __init__(self):
        """Initialize cache and timestamps"""
        self._branches_cache_timestamp = 0
        self._employees_cache_timestamp = 0
        self._cache_duration = 300  # 5 minutes cache duration
        self.branch_id_to_name = {}
        self._employee_cache = EmployeeCache.getInstance()
        self._current_worker = None
        self._loading_widget = None
        self._table_manager = None
        
        # Initialize update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._process_updates)
        self._update_timer.setInterval(100)
        self._pending_updates = []
        
    def _show_loading(self, message: str = "جاري التحميل..."):
        """Show loading indicator"""
        if not self._loading_widget:
            self._loading_widget = QWidget(self)
            layout = QVBoxLayout(self._loading_widget)
            self._loading_label = QLabel(message)
            self._loading_label.setStyleSheet("""
                background-color: #fffbe6;
                color: #e67e22;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            """)
            self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._loading_label)
            self._loading_widget.setLayout(layout)
            self._loading_widget.setGeometry(0, 0, self.width(), 50)
            self._loading_widget.show()
            self._loading_widget.raise_()
            
    def _hide_loading(self):
        """Hide loading indicator"""
        if self._loading_widget:
            self._loading_widget.hide()
            self._loading_widget.deleteLater()
            self._loading_widget = None
            
    def _update_loading_message(self, message: str):
        """Update loading message"""
        if self._loading_widget and hasattr(self, '_loading_label'):
            self._loading_label.setText(message)

    @lru_cache(maxsize=100)
    def _get_branch_name(self, branch_id: int) -> str:
        """Get branch name from cached data with LRU caching"""
        return self.branch_id_to_name.get(branch_id, "غير محدد")

    def load_employees(self, branch_id: Optional[int] = None):
        """Load employees data with improved performance"""
        try:
            # Cancel any existing worker
            if self._current_worker and self._current_worker.isRunning():
                self._current_worker.cancel()
                self._current_worker.wait()
            
            # Check cache first
            cache_key = f"employees_{branch_id if branch_id else 'all'}"
            cached_data = self._employee_cache.get(cache_key)
            
            if cached_data:
                self._update_employees_table(cached_data)
                return
            
            # Show loading indicator
            self._show_loading("جاري تحميل بيانات الموظفين...")
            
            # Create and start worker
            self._current_worker = EmployeeLoadWorker(self.api_url, self.token, branch_id)
            self._current_worker.data_loaded.connect(self._handle_employee_data)
            self._current_worker.error_occurred.connect(self._handle_employee_error)
            self._current_worker.progress_updated.connect(self._update_loading_message)
            self._current_worker.finished.connect(self._hide_loading)
            self._current_worker.start()
            
        except Exception as e:
            self._hide_loading()
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل الموظفين: {str(e)}")

    def _handle_employee_data(self, employees: List[Dict]):
        """Handle loaded employee data"""
        try:
            # Cache the data
            cache_key = "employees_all"
            self._employee_cache.set(cache_key, employees)
            
            # Update table
            self._update_employees_table(employees)
            
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"خطأ في معالجة البيانات: {str(e)}")

    def _handle_employee_error(self, error_msg: str):
        """Handle employee loading error"""
        self._hide_loading()
        QMessageBox.warning(self, "خطأ", error_msg)

    def _update_employees_table(self, employees: List[Dict]):
        """Update the employees table with optimized table manager"""
        try:
            # Initialize table manager if needed
            if not self._table_manager:
                self._table_manager = OptimizedTableManager.get_instance(self.employees_table)
            
            # Prepare column mapping
            column_mapping = {
                0: ("username", None),
                1: ("role", lambda x: {
                    "employee": "موظف",
                    "branch_manager": "مدير فرع",
                    "director": "مدير النظام"
                }.get(x, x)),
                2: ("branch_id", lambda x: self._get_branch_name(x)),
                3: "created_at",
                4: ("is_active", lambda x: "نشط" if x else "غير نشط")
            }
            
            # Update table using optimized manager
            self._table_manager.set_data(employees, column_mapping)
            
            if not employees:
                self.show_no_results_message()
                
        except Exception as e:
            print(f"Error updating employees table: {e}")
            QMessageBox.warning(self, "خطأ", f"خطأ في تحديث الجدول: {str(e)}")

    def filter_employees(self):
        """Filter employees with improved performance"""
        try:
            # Get filter criteria
            branch_id = self.branch_filter.currentData()
            search_text = self.employee_search.text().strip().lower()
            
            # Get cached data
            cache_key = "employees_all"
            employees = self._employee_cache.get(cache_key)
            
            if not employees:
                # If no cache, load fresh data
                self.load_employees()
                return
            
            # Apply filters
            filtered_employees = []
            for emp in employees:
                if branch_id and emp.get("branch_id") != branch_id:
                    continue
                    
                if search_text and not self._matches_search(emp, search_text):
                    continue
                    
                filtered_employees.append(emp)
            
            # Update table with filtered data
            self._update_employees_table(filtered_employees)
            
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"خطأ في التصفية: {str(e)}")

    def _matches_search(self, employee: Dict, search_text: str) -> bool:
        """Check if employee matches search criteria"""
        searchable_fields = [
            str(employee.get("username", "")),
            str(employee.get("id", "")),
            str(employee.get("role", "")),
            self._get_branch_name(employee.get("branch_id"))
        ]
        return any(search_text in field.lower() for field in searchable_fields)

    def add_employee(self):
        """Open dialog to add a new employee."""
        dialog = AddEmployeeDialog(
            is_admin=True,
            branch_id=None,
            token=self.token,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Clear cache and reload
            self._employee_cache.clear()
            self.load_employees()
            if hasattr(self, 'load_dashboard_data'):
                self.load_dashboard_data()

    def edit_employee(self):
        """Edit selected employee with improved error handling"""
        employee_data = self._get_selected_employee()
        if not employee_data:
            return
            
        from ui.user_management_improved import EditEmployeeDialog
        dialog = EditEmployeeDialog(employee_data, self.token, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Clear cache and reload
            self._employee_cache.clear()
            self.load_employees()

    def delete_employee(self):
        """Delete employee with improved error handling"""
        employee_data = self._get_selected_employee()
        if not employee_data:
            return
            
        employee_id = employee_data.get("id")
        employee_name = employee_data.get("username", "")
        
        reply = QMessageBox.question(
            self, 
            "تأكيد الحذف", 
            f"هل أنت متأكد من حذف الموظف '{employee_name}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._perform_employee_deletion(employee_id)

    def _get_selected_employee(self) -> Optional[Dict]:
        """Get selected employee data safely"""
        try:
            selected_rows = self.employees_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف")
                return None
                
            row = selected_rows[0].row()
            employee_item = self.employees_table.item(row, 0)
            
            if not employee_item:
                QMessageBox.warning(self, "خطأ", "الخليّة المحددة غير موجودة")
                return None
                
            employee_data = employee_item.data(Qt.ItemDataRole.UserRole)
            
            if not isinstance(employee_data, dict) or "id" not in employee_data:
                QMessageBox.warning(self, "خطأ", "بيانات الموظف غير صالحة")
                return None
                
            return employee_data
            
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"خطأ في الحصول على بيانات الموظف: {str(e)}")
            return None

    def _perform_employee_deletion(self, employee_id: int):
        """Execute employee deletion with proper error handling"""
        try:
            self._show_loading("جاري حذف الموظف...")
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.delete(
                f"{self.api_url}/users/{employee_id}",
                headers=headers,
                timeout=30
            )
            
            self._hide_loading()
            
            if response.status_code in [200, 204]:
                QMessageBox.information(self, "نجاح", "تم الحذف بنجاح")
                # Clear cache and reload
                self._employee_cache.clear()
                self.load_employees()
                if hasattr(self, 'load_dashboard_data'):
                    self.load_dashboard_data()
            else:
                QMessageBox.warning(self, "خطأ", self._extract_error(response))
                
        except requests.exceptions.Timeout:
            self._hide_loading()
            QMessageBox.warning(self, "خطأ", "انتهت مهلة الاتصال")
        except requests.exceptions.RequestException as e:
            self._hide_loading()
            QMessageBox.warning(self, "خطأ في الاتصال", str(e))
        except Exception as e:
            self._hide_loading()
            QMessageBox.warning(self, "خطأ", f"خطأ غير متوقع: {str(e)}")

    def _extract_error(self, response) -> str:
        """Extract error message from response"""
        try:
            error_data = response.json()
            return error_data.get("detail", f"رمز الخطأ: {response.status_code}")
        except:
            return f"رمز الخطأ: {response.status_code}"

    def show_no_results_message(self):
        """Display no results message in the table"""
        self.employees_table.setRowCount(1)
        no_results = QTableWidgetItem("لا توجد نتائج")
        no_results.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.employees_table.setItem(0, 0, no_results)
        self.employees_table.setSpan(0, 0, 1, 5)

    def _process_updates(self):
        """Process pending updates"""
        if not self._pending_updates:
            self._update_timer.stop()
            return
            
        update_func = self._pending_updates.pop(0)
        update_func()
        
        if self._pending_updates:
            self._update_timer.start()

    def cleanup(self):
        """Clean up resources"""
        try:
            # Cancel any running worker
            if self._current_worker and self._current_worker.isRunning():
                self._current_worker.cancel()
                self._current_worker.wait()
            
            # Stop timers
            if self._update_timer.isActive():
                self._update_timer.stop()
            
            # Clear caches
            self._employee_cache.clear()
            
            # Clean up loading widget
            self._hide_loading()
            
            # Clean up table manager
            if self._table_manager:
                self._table_manager.cleanup()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")                                                