import requests
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QPushButton, QHBoxLayout
)
from ui.custom_widgets import ModernGroupBox, ModernButton
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QThread, pyqtSignal

class EmployeesWorker(QThread):
    finished = pyqtSignal(object, object)
    def __init__(self, api_url, branch_id, token, user_id):
        super().__init__()
        self.api_url = api_url
        self.branch_id = branch_id
        self.token = token
        self.user_id = user_id
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}/employees/",
                headers=headers
            )
            self.finished.emit(response, None)
        except Exception as e:
            self.finished.emit(None, str(e))

class EmployeesTabMixin:

    def setup_employees_tab(self):
        """Set up the employees management tab."""
        layout = QVBoxLayout()
        
        # Employees table
        employees_group = ModernGroupBox("قائمة الموظفين", "#2ecc71")
        employees_layout = QVBoxLayout()
        
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(5)
        self.employees_table.setHorizontalHeaderLabels([
            "اسم المستخدم", "الدور", "الحالة", "تاريخ الإنشاء", "الإجراءات"
        ])
        self.employees_table.horizontalHeader().setStretchLastSection(True)
        self.employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.employees_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                border: 1px solid #1a2530;
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
        employees_layout.addWidget(self.employees_table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        add_employee_button = ModernButton("إضافة موظف جديد", color="#2ecc71")
        add_employee_button.clicked.connect(self.add_employee)
        buttons_layout.addWidget(add_employee_button)
        
        refresh_button = ModernButton("تحديث البيانات", color="#3498db")
        refresh_button.clicked.connect(self.load_employees)
        buttons_layout.addWidget(refresh_button)
        
        employees_layout.addLayout(buttons_layout)
        employees_group.setLayout(employees_layout)
        layout.addWidget(employees_group)
        
        self.employees_tab.setLayout(layout)
        
        # لا تحميل تلقائي للبيانات هنا
        self._employees_loaded = False
        self._is_loading_employees = False
    
    def on_employees_tab_selected(self):
        """تحميل بيانات الموظفين عند فتح التبويب لأول مرة فقط (lazy load)"""
        if not getattr(self, '_employees_loaded', False):
            self.load_employees()
    
    def load_employees(self):
        """Load employees data for this branch with QThread and loading indicator"""
        if getattr(self, '_is_loading_employees', False):
            return  # منع التكرار
        self._is_loading_employees = True
        self.employees_table.setRowCount(1)
        loading_item = QTableWidgetItem("جاري التحميل ...")
        loading_item.setForeground(QColor("#2980b9"))
        self.employees_table.setItem(0, 0, loading_item)
        for col in range(1, 5):
            self.employees_table.setItem(0, col, QTableWidgetItem(""))
        self.employees_worker = EmployeesWorker(self.api_url, self.branch_id, self.token, self.user_id)
        self.employees_worker.finished.connect(self.on_employees_loaded)
        self.employees_worker.start()

    def on_employees_loaded(self, response, error):
        self._is_loading_employees = False
        if error:
            self.employees_table.setRowCount(1)
            error_item = QTableWidgetItem(f"فشل التحميل: {error}")
            error_item.setForeground(QColor("#e74c3c"))
            self.employees_table.setItem(0, 0, error_item)
            for col in range(1, 5):
                self.employees_table.setItem(0, col, QTableWidgetItem(""))
            self._employees_loaded = False
            return
        if response is None or response.status_code != 200:
            self.employees_table.setRowCount(1)
            error_item = QTableWidgetItem("فشل تحميل البيانات من الخادم")
            error_item.setForeground(QColor("#e74c3c"))
            self.employees_table.setItem(0, 0, error_item)
            for col in range(1, 5):
                self.employees_table.setItem(0, col, QTableWidgetItem(""))
            self._employees_loaded = False
            return
        employees = response.json()
        self.employees_table.setRowCount(len(employees))
        for row, employee in enumerate(employees):
            employee_id = employee.get("id")
            employee_role = employee.get("role", "employee")
            is_manager = employee_role == "branch_manager"
            is_current_user = str(employee_id) == str(self.user_id)
            username_item = QTableWidgetItem(employee.get("username", ""))
            self.employees_table.setItem(row, 0, username_item)
            role_text = "مدير فرع" if is_manager else "موظف"
            role_item = QTableWidgetItem(role_text)
            self.employees_table.setItem(row, 1, role_item)
            status_item = QTableWidgetItem("نشط")
            status_color = QColor("#27ae60") if employee.get("active", True) else QColor("#e74c3c")
            status_item.setForeground(status_color)
            self.employees_table.setItem(row, 2, status_item)
            date_item = QTableWidgetItem(employee.get("created_at", ""))
            self.employees_table.setItem(row, 3, date_item)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            edit_button = QPushButton("تعديل")
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border-radius: 3px;
                    padding: 3px;
                }
                QPushButton:disabled {
                    background-color: #95a5a6;
                }
                QPushButton:hover:!disabled {
                    background-color: #2980b9;
                }
            """)
            delete_button = QPushButton("حذف")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border-radius: 3px;
                    padding: 3px;
                }
                QPushButton:disabled {
                    background-color: #95a5a6;
                }
                QPushButton:hover:!disabled {
                    background-color: #c0392b;
                }
            """)
            if is_manager or is_current_user:
                edit_button.setEnabled(False)
                delete_button.setEnabled(False)
                edit_button.setToolTip("غير مسموح بتعديل المديرين أو حسابك الخاص")
                delete_button.setToolTip("غير مسموح بحذف المديرين أو حسابك الخاص")
            else:
                edit_button.clicked.connect(lambda _, e=employee: self.edit_employee(e))
                delete_button.clicked.connect(lambda _, e=employee: self.delete_employee(e))
            actions_layout.addWidget(edit_button)
            actions_layout.addWidget(delete_button)
            self.employees_table.setCellWidget(row, 4, actions_widget)
        self._employees_loaded = True
        
        # لا تحميل تلقائي للبيانات هنا
        self._employees_loaded = False
        self._is_loading_employees = False
    
    def on_employees_tab_selected(self):
        """تحميل بيانات الموظفين عند فتح التبويب لأول مرة فقط (lazy load)"""
        if not getattr(self, '_employees_loaded', False):
            self.load_employees()
    
    def load_employees(self):
        """Load employees data for this branch with security restrictions, with loading indicator and prevent duplicate loads"""
        if getattr(self, '_is_loading_employees', False):
            return  # منع التكرار
        self._is_loading_employees = True
        try:
            self.employees_table.setRowCount(1)
            loading_item = QTableWidgetItem("جاري التحميل ...")
            loading_item.setForeground(QColor("#2980b9"))
            self.employees_table.setItem(0, 0, loading_item)
            for col in range(1, 5):
                self.employees_table.setItem(0, col, QTableWidgetItem(""))
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.api_url}/branches/{self.branch_id}/employees/",
                headers=headers
            )
            
            if response.status_code == 200:
                employees = response.json()
                self.employees_table.setRowCount(len(employees))
                
                for row, employee in enumerate(employees):
                    # Employee ID and Role
                    employee_id = employee.get("id")
                    employee_role = employee.get("role", "employee")
                    is_manager = employee_role == "branch_manager"
                    is_current_user = str(employee_id) == str(self.user_id)

                    # Username
                    username_item = QTableWidgetItem(employee.get("username", ""))
                    self.employees_table.setItem(row, 0, username_item)
                    
                    # Role (display Arabic text)
                    role_text = "مدير فرع" if is_manager else "موظف"
                    role_item = QTableWidgetItem(role_text)
                    self.employees_table.setItem(row, 1, role_item)
                    
                    # Status
                    status_item = QTableWidgetItem("نشط")
                    status_color = QColor("#27ae60") if employee.get("active", True) else QColor("#e74c3c")
                    status_item.setForeground(status_color)
                    self.employees_table.setItem(row, 2, status_item)
                    
                    # Creation date
                    date_item = QTableWidgetItem(employee.get("created_at", ""))
                    self.employees_table.setItem(row, 3, date_item)
                    
                    # Actions
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout(actions_widget)
                    actions_layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Edit Button
                    edit_button = QPushButton("تعديل")
                    edit_button.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border-radius: 3px;
                            padding: 3px;
                        }
                        QPushButton:disabled {
                            background-color: #95a5a6;
                        }
                        QPushButton:hover:!disabled {
                            background-color: #2980b9;
                        }
                    """)
                    
                    # Delete Button
                    delete_button = QPushButton("حذف")
                    delete_button.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: white;
                            border-radius: 3px;
                            padding: 3px;
                        }
                        QPushButton:disabled {
                            background-color: #95a5a6;
                        }
                        QPushButton:hover:!disabled {
                            background-color: #c0392b;
                        }
                    """)
                    
                    # Disable actions for managers and current user
                    if is_manager or is_current_user:
                        edit_button.setEnabled(False)
                        delete_button.setEnabled(False)
                        edit_button.setToolTip("غير مسموح بتعديل المديرين أو حسابك الخاص")
                        delete_button.setToolTip("غير مسموح بحذف المديرين أو حسابك الخاص")
                    else:
                        edit_button.clicked.connect(lambda _, e=employee: self.edit_employee(e))
                        delete_button.clicked.connect(lambda _, e=employee: self.delete_employee(e))
                    
                    actions_layout.addWidget(edit_button)
                    actions_layout.addWidget(delete_button)
                    self.employees_table.setCellWidget(row, 4, actions_widget)
                self._employees_loaded = True
            else:
                self.load_placeholder_employees()
                QMessageBox.warning(self, "خطأ", f"فشل في تحميل البيانات: {response.status_code}")
                self._employees_loaded = False
        except Exception as e:
            print(f"Error loading employees: {e}")
            self.load_placeholder_employees()
            QMessageBox.critical(self, "خطأ", "تعذر الاتصال بالخادم")
            self._employees_loaded = False
        finally:
            self._is_loading_employees = False            