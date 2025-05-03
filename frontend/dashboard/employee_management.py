from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from ui.user_management_improved import AddEmployeeDialog
import requests

class EmployeeManagementMixin:
    """Mixin handling all employee-related operations"""

    def _fetch_and_cache_branches(self):
        """Fetch all branches once and cache their names for fast lookup."""
        if hasattr(self, 'branch_id_to_name') and self.branch_id_to_name:
            return  # Already cached
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/branches/", headers=headers)
            if response.status_code == 200:
                branches = response.json().get("branches", [])
                self.branch_id_to_name = {b.get("id"): b.get("name", "غير محدد") for b in branches}
            else:
                self.branch_id_to_name = {}
        except Exception as e:
            print(f"Error fetching branches: {e}")
            self.branch_id_to_name = {}

    def load_employees(self, branch_id=None):
        """Load employees data."""
        try:
            self._fetch_and_cache_branches()
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            url = f"{self.api_url}/users/"
            if branch_id:
                url += f"?branch_id={branch_id}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                employees = response.json().get("users", [])
                self.employees_table.setRowCount(len(employees))
                for i, employee in enumerate(employees):
                    self.employees_table.setItem(i, 0, QTableWidgetItem(employee.get("username", "")))
                    role = employee.get("role", "")
                    role_arabic = "موظف"
                    if role == "director":
                        role_arabic = "مدير"
                    elif role == "branch_manager":
                        role_arabic = "مدير فرع"
                    self.employees_table.setItem(i, 1, QTableWidgetItem(role_arabic))
                    branch_id = employee.get("branch_id")
                    branch_name = self.branch_id_to_name.get(branch_id, "غير محدد")
                    self.employees_table.setItem(i, 2, QTableWidgetItem(branch_name))
                    self.employees_table.setItem(i, 3, QTableWidgetItem(employee.get("created_at", "")))
                    status_item = QTableWidgetItem("نشط")
                    status_item.setForeground(QColor("#27ae60"))
                    self.employees_table.setItem(i, 4, status_item)
                    self.employees_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, employee)
            else:
                QMessageBox.warning(self, "خطأ", f"فشل تحميل الموظفين: رمز الحالة {response.status_code}")
        except Exception as e:
            print(f"Error loading employees: {e}")
            QMessageBox.warning(self, "خطأ", f"تعذر تحميل الموظفين: {str(e)}")
            
    def _populate_employee_row(self, row, employee):
        """Helper to populate a single employee row"""
        username_item = QTableWidgetItem(employee.get("username", ""))
        username_item.setData(Qt.ItemDataRole.UserRole, employee)
        self.employees_table.setItem(row, 0, username_item)
        
        role_arabic = {
            "employee": "موظف",
            "branch_manager": "مدير فرع",
            "director": "مدير النظام"
        }.get(employee.get("role", ""), employee.get("role", ""))
        
        self.employees_table.setItem(row, 1, QTableWidgetItem(role_arabic))
        self.employees_table.setItem(row, 2, QTableWidgetItem(self._get_branch_name(employee.get("branch_id"))))
        self.employees_table.setItem(row, 3, QTableWidgetItem(employee.get("created_at", "")))
        
        status_item = QTableWidgetItem("نشط")
        status_item.setForeground(QColor("#27ae60"))
        self.employees_table.setItem(row, 4, status_item)            
        
    def filter_employees(self):
        try:
            self._fetch_and_cache_branches()
            self.employees_table.setRowCount(0)
            branch_id = self.branch_filter.currentData()
            search_text = self.employee_search.text().strip().lower()
            params = {}
            if branch_id and branch_id != self.api_url and branch_id != "":
                params["branch_id"] = branch_id
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/users/", headers=headers, params=params)
            if response.status_code == 200:
                employees = response.json().get("users", [])
                if search_text:
                    filtered_employees = []
                    for emp in employees:
                        if search_text in emp.get("username", "").lower():
                            filtered_employees.append(emp)
                            continue
                        if search_text in str(emp.get("id", "")).lower():
                            filtered_employees.append(emp)
                            continue
                        if search_text in emp.get("role", "").lower():
                            filtered_employees.append(emp)
                            continue
                        branch_name = self.branch_id_to_name.get(emp.get("branch_id"), "غير محدد")
                        if search_text in branch_name.lower():
                            filtered_employees.append(emp)
                            continue
                    employees = filtered_employees
                self.employees_table.setRowCount(len(employees))
                for i, emp in enumerate(employees):
                    username_item = QTableWidgetItem(emp.get("username", ""))
                    username_item.setData(Qt.ItemDataRole.UserRole, emp)
                    self.employees_table.setItem(i, 0, username_item)
                    role_arabic = {
                        "employee": "موظف",
                        "branch_manager": "مدير فرع",
                        "director": "مدير النظام"
                    }.get(emp.get("role", ""), emp.get("role", ""))
                    self.employees_table.setItem(i, 1, QTableWidgetItem(role_arabic))
                    branch_name = self.branch_id_to_name.get(emp.get("branch_id"), "غير محدد")
                    self.employees_table.setItem(i, 2, QTableWidgetItem(branch_name))
                    self.employees_table.setItem(i, 3, QTableWidgetItem(emp.get("created_at", "")))
                    status_item = QTableWidgetItem("نشط")
                    status_item.setForeground(QColor("#27ae60"))
                    self.employees_table.setItem(i, 4, status_item)
                if not employees:
                    self.show_no_results_message()
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
            self.load_employees()
            self.load_dashboard_data()
    
    def edit_employee(self):
        """Open dialog to edit the selected employee."""
        selected_rows = self.employees_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف للتعديل")
            return
        
        row = selected_rows[0].row()
        
        # التحقق من وجود العنصر في الجدول
        employee_item = self.employees_table.item(row, 0)
        if not employee_item:
            QMessageBox.warning(self, "خطأ", "الخليّة المحددة غير موجودة")
            return
        
        # استرجاع بيانات الموظف مع التحقق من وجودها
        employee_data = employee_item.data(Qt.ItemDataRole.UserRole)
        if not employee_data or not isinstance(employee_data, dict):
            QMessageBox.warning(self, "خطأ", "بيانات الموظف غير صالحة")
            return
        
        # التحقق من وجود الحقول الأساسية
        if "id" not in employee_data or "username" not in employee_data:
            QMessageBox.warning(self, "خطأ", "بيانات الموظف ناقصة أو غير صحيحة")
            return
        
        # فتح نافذة التعديل
        from ui.user_management_improved import EditEmployeeDialog
        dialog = EditEmployeeDialog(employee_data, self.token, self)
        if dialog.exec() == 1:  # If dialog was accepted
            self.load_employees()  # Refresh the employees list
    
    def delete_employee(self):
        """Delete the selected employee."""
        selected_rows = self.employees_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف للحذف")
            return
        
        row = selected_rows[0].row()
        
        # التحقق من وجود العنصر في الجدول
        employee_item = self.employees_table.item(row, 0)
        if not employee_item:
            QMessageBox.warning(self, "خطأ", "الخليّة المحددة غير موجودة")
            return
        
        # استرجاع بيانات الموظف مع التحقق من وجودها
        employee_data = employee_item.data(Qt.ItemDataRole.UserRole)
        if not employee_data or not isinstance(employee_data, dict):
            QMessageBox.warning(self, "خطأ", "بيانات الموظف غير صالحة")
            return
        
        employee_id = employee_data.get("id")
        employee_name = employee_data.get("username", "")
        
        # تأكيد الحذف
        reply = QMessageBox.question(
            self, 
            "تأكيد الحذف", 
            f"هل أنت متأكد من حذف الموظف '{employee_name}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                response = requests.delete(f"{self.api_url}/users/{employee_id}", headers=headers)
                
                if response.status_code in [200, 204]:
                    QMessageBox.information(self, "نجاح", "تم حذف الموظف بنجاح")
                    self.load_employees()
                    self.load_dashboard_data()
                else:
                    error_msg = f"فشل حذف الموظف: رمز الحالة {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", error_msg)
                    except:
                        pass
                    QMessageBox.warning(self, "خطأ", error_msg)
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر حذف الموظف: {str(e)}")
                
    def _get_selected_employee(self):
        """Get selected employee data"""
        if not (rows := self.employees_table.selectionModel().selectedRows()):
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد موظف")
            return None
        return self.employees_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def _perform_employee_deletion(self, employee_id):
        """Execute employee deletion API call"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.delete(f"{self.api_url}/users/{employee_id}", headers=headers)
            
            if response.status_code in [200, 204]:
                QMessageBox.information(self, "نجاح", "تم الحذف بنجاح")
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