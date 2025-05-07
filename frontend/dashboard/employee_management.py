from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from ui.user_management_improved import AddEmployeeDialog
import requests
import time

class EmployeeManagementMixin:
    """Mixin handling all employee-related operations"""

    def __init__(self):
        """Initialize cache and timestamps"""
        self._branches_cache_timestamp = 0
        self._employees_cache_timestamp = 0
        self._cache_duration = 300  # 5 minutes cache duration
        self.branch_id_to_name = {}

    def _fetch_and_cache_branches(self):
        """Fetch all branches once and cache their names for fast lookup."""
        current_time = time.time()
        
        # Check if cache is still valid
        if (hasattr(self, 'branch_id_to_name') and self.branch_id_to_name and 
            current_time - self._branches_cache_timestamp < self._cache_duration):
            return  # Use cached data if still valid
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            if response.status_code == 200:
                branches = response.json().get("branches", [])
                self.branch_id_to_name = {b.get("id"): b.get("name", "غير محدد") for b in branches}
                self._branches_cache_timestamp = current_time
            else:
                self.branch_id_to_name = {}
        except Exception as e:
            print(f"Error fetching branches: {e}")
            self.branch_id_to_name = {}

    def load_employees(self, branch_id=None):
        """Load employees data with caching."""
        try:
            self._fetch_and_cache_branches()
            
            # Check cache first
            current_time = time.time()
            if (hasattr(self, '_employees_cache') and self._employees_cache and 
                current_time - self._employees_cache_timestamp < self._cache_duration):
                self._update_employees_table(self._employees_cache)
                return

            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            url = f"{self.api_url}/users/"
            if branch_id:
                url += f"?branch_id={branch_id}"
                
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                employees = response.json().get("users", [])
                # Update cache
                self._employees_cache = employees
                self._employees_cache_timestamp = current_time
                # Update table
                self._update_employees_table(employees)
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل الموظفين: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error loading employees: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل الموظفين: {str(e)}")

    def _update_employees_table(self, employees):
        """Update the employees table with the given data"""
        self.employees_table.setRowCount(len(employees))
        for i, employee in enumerate(employees):
            self._populate_employee_row(i, employee)
        if not employees:
            self.show_no_results_message()

    def _populate_employee_row(self, row, employee):
        """Helper to populate a single employee row"""
        # Username with data
        username_item = QTableWidgetItem(employee.get("username", ""))
        username_item.setData(Qt.ItemDataRole.UserRole, employee)
        self.employees_table.setItem(row, 0, username_item)
        
        # Role in Arabic
        role_arabic = {
            "employee": "موظف",
            "branch_manager": "مدير فرع",
            "director": "مدير النظام"
        }.get(employee.get("role", ""), employee.get("role", ""))
        self.employees_table.setItem(row, 1, QTableWidgetItem(role_arabic))
        
        # Branch name
        branch_name = self._get_branch_name(employee.get("branch_id"))
        self.employees_table.setItem(row, 2, QTableWidgetItem(branch_name))
        
        # Creation date
        self.employees_table.setItem(row, 3, QTableWidgetItem(employee.get("created_at", "")))
        
        # Status
        status_item = QTableWidgetItem("نشط")
        status_item.setForeground(QColor("#27ae60"))
        self.employees_table.setItem(row, 4, status_item)

    def filter_employees(self):
        """Filter employees based on branch and search criteria"""
        try:
            self._fetch_and_cache_branches()
            
            # Get filter criteria
            branch_id = self.branch_filter.currentData()
            search_text = self.employee_search.text().strip().lower()
            
            # امسح الكاش عند كل فلترة لضمان ظهور المدير عند اختيار "الكل"
            self._employees_cache = None
            
            # Prepare API parameters
            params = {}
            if branch_id and branch_id != self.api_url and branch_id != "":
                params["branch_id"] = branch_id
                
            # Fetch data
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/users/", headers=headers, params=params)
            
            if response.status_code == 200:
                employees = response.json().get("users", [])
                
                # Apply search filter locally if search text exists
                if search_text:
                    employees = [emp for emp in employees if self._matches_search(emp, search_text)]
                
                # Update table
                self._update_employees_table(employees)
                
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل البيانات: {response.status_code}")
                
        except Exception as e:
            print(f"Error in filter_employees: {e}")
            QMessageBox.warning(self, "خطأ", f"خطأ في التصفية: {str(e)}")

    def _matches_search(self, employee, search_text):
        """Check if employee matches search criteria"""
        return (search_text in employee.get("username", "").lower() or
                search_text in str(employee.get("id", "")).lower() or
                search_text in employee.get("role", "").lower() or
                search_text in self._get_branch_name(employee.get("branch_id")).lower())

    def _get_branch_name(self, branch_id):
        """Get branch name from cached data"""
        return self.branch_id_to_name.get(branch_id, "غير محدد")

    def add_employee(self):
        """Open dialog to add a new employee."""
        dialog = AddEmployeeDialog(
            is_admin=True,
            branch_id=None,
            token=self.token,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Clear cache and reload
            self._employees_cache = None
            self.load_employees()
            self.load_dashboard_data()

    def edit_employee(self):
        """Open dialog to edit the selected employee."""
        employee_data = self._get_selected_employee()
        if not employee_data:
            return
            
        from ui.user_management_improved import EditEmployeeDialog
        dialog = EditEmployeeDialog(employee_data, self.token, self)
        if dialog.exec() == 1:  # If dialog was accepted
            # Clear cache and reload
            self._employees_cache = None
            self.load_employees()

    def delete_employee(self):
        """Delete the selected employee."""
        employee_data = self._get_selected_employee()
        if not employee_data:
            return
            
        employee_id = employee_data.get("id")
        employee_name = employee_data.get("username", "")
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "تأكيد الحذف", 
            f"هل أنت متأكد من حذف الموظف '{employee_name}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._perform_employee_deletion(employee_id)

    def _get_selected_employee(self):
        """Get selected employee data"""
        selected_rows = self.employees_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف")
            return None
            
        employee_item = self.employees_table.item(selected_rows[0].row(), 0)
        if not employee_item:
            QMessageBox.warning(self, "خطأ", "الخليّة المحددة غير موجودة")
            return None
            
        employee_data = employee_item.data(Qt.ItemDataRole.UserRole)
        if not employee_data or not isinstance(employee_data, dict):
            QMessageBox.warning(self, "خطأ", "بيانات الموظف غير صالحة")
            return None
            
        if "id" not in employee_data or "username" not in employee_data:
            QMessageBox.warning(self, "خطأ", "بيانات الموظف ناقصة أو غير صحيحة")
            return None
            
        return employee_data

    def _perform_employee_deletion(self, employee_id):
        """Execute employee deletion API call"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.delete(f"{self.api_url}/users/{employee_id}", headers=headers)
            
            if response.status_code in [200, 204]:
                QMessageBox.information(self, "نجاح", "تم الحذف بنجاح")
                # Clear cache and reload
                self._employees_cache = None
                self.load_employees()
                self.load_dashboard_data()
            else:
                QMessageBox.warning(self, "خطأ", self._extract_error(response))
                
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر الحذف: {str(e)}")

    def _extract_error(self, response):
        """Extract error message from response"""
        try:
            return response.json().get("detail", f"رمز الخطأ: {response.status_code}")
        except:
            return f"رمز الخطأ: {response.status_code}"

    def show_no_results_message(self):
        """Display no results message in the table"""
        self.employees_table.setRowCount(1)
        no_results = QTableWidgetItem("لا توجد نتائج")
        no_results.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.employees_table.setItem(0, 0, no_results)
        self.employees_table.setSpan(0, 0, 1, 5)                                                