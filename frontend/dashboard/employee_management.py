from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QDialog
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from ui.user_management_improved import AddEmployeeDialog
import requests

class EmployeeManagementMixin:
    """Mixin handling all employee-related operations"""

    def load_employees(self, branch_id=None):
        """Load employees data."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Use /users/ endpoint instead of /employees/ to include branch managers
            url = f"{self.api_url}/users/"
            if branch_id:
                url += f"?branch_id={branch_id}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # For /users/ endpoint, the response is wrapped in a "users" key
                employees = response.json().get("users", [])
                self.employees_table.setRowCount(len(employees))
                
                for i, employee in enumerate(employees):
                    self.employees_table.setItem(i, 0, QTableWidgetItem(employee.get("username", "")))
                    
                    # Map role to Arabic
                    role = employee.get("role", "")
                    role_arabic = "موظف"
                    if role == "director":
                        role_arabic = "مدير"
                    elif role == "branch_manager":
                        role_arabic = "مدير فرع"
                    
                    self.employees_table.setItem(i, 1, QTableWidgetItem(role_arabic))
                    
                    # Get branch name
                    branch_id = employee.get("branch_id")
                    branch_name = "غير محدد"
                    if branch_id:
                        try:
                            branch_response = requests.get(
                                f"{self.api_url}/branches/{branch_id}", 
                                headers=headers
                            )
                            if branch_response.status_code == 200:
                                branch_data = branch_response.json()
                                branch_name = branch_data.get("name", "غير محدد")
                        except:
                            pass
                    
                    self.employees_table.setItem(i, 2, QTableWidgetItem(branch_name))
                    self.employees_table.setItem(i, 3, QTableWidgetItem(employee.get("created_at", "")))
                    
                    # Status (always active for now)
                    status_item = QTableWidgetItem("نشط")
                    status_item.setForeground(QColor("#27ae60"))
                    self.employees_table.setItem(i, 4, status_item)
                    
                    # Store the employee data in the first cell for later use
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
            # مسح الجدول قبل التحميل
            self.employees_table.setRowCount(0)
            
            # استخراج معايير التصفية
            branch_id = self.branch_filter.currentData()
            search_text = self.employee_search.text().strip().lower()

            # إعداد بارامترات الطلب
            params = {}
            if branch_id and branch_id != self.api_url and branch_id != "":  # تجنب إرسال branch_id إذا كان None (جميع الفروع)
                params["branch_id"] = branch_id

            # إرسال الطلب مع البارامترات
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            response = requests.get(f"{self.api_url}/users/", headers=headers, params=params)
            
            if response.status_code == 200:
                employees = response.json().get("users", [])
                
                # تطبيق البحث المحلي إذا كان هناك نص بحث
                if search_text:
                    filtered_employees = []
                    for emp in employees:
                        # Check username
                        if search_text in emp.get("username", "").lower():
                            filtered_employees.append(emp)
                            continue
                            
                        # Check ID
                        if search_text in str(emp.get("id", "")).lower():
                            filtered_employees.append(emp)
                            continue
                            
                        # Check role
                        if search_text in emp.get("role", "").lower():
                            filtered_employees.append(emp)
                            continue
                            
                        # Check branch name if available
                        branch_name = self.get_branch_name(emp.get("branch_id"))
                        if search_text in branch_name.lower():
                            filtered_employees.append(emp)
                            continue
                    
                    employees = filtered_employees

                # تعبئة الجدول بالبيانات المصفاة
                self.employees_table.setRowCount(len(employees))
                for i, emp in enumerate(employees):
                    username_item = QTableWidgetItem(emp.get("username", ""))
                    username_item.setData(Qt.ItemDataRole.UserRole, emp)  # Store employee data
                    self.employees_table.setItem(i, 0, username_item)
                    
                    # تحويل الدور إلى عربي
                    role_arabic = {
                        "employee": "موظف",
                        "branch_manager": "مدير فرع",
                        "director": "مدير النظام"
                    }.get(emp.get("role", ""), emp.get("role", ""))
                    self.employees_table.setItem(i, 1, QTableWidgetItem(role_arabic))
                    
                    # الحصول على اسم الفرع من الـ branch_id
                    branch_name = self.get_branch_name(emp.get("branch_id"))
                    self.employees_table.setItem(i, 2, QTableWidgetItem(branch_name))
                    
                    # تاريخ الإنشاء
                    self.employees_table.setItem(i, 3, QTableWidgetItem(emp.get("created_at", "")))
                    
                    # الحالة
                    status_item = QTableWidgetItem("نشط")
                    status_item.setForeground(QColor("#27ae60"))
                    self.employees_table.setItem(i, 4, status_item)

                # عرض رسالة إذا لم توجد نتائج
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